// Drop-in replacement for the parts of "firebase/firestore" the DACS Community app uses.
// Documents live in IHP-WINS (CKAN's PostgreSQL); every read and write is checked on the server by the
// same security rules the Firebase version used (ckanext/theme_ejemplo/community_data/dacs.rules).
// Live listeners (onSnapshot) are served by polling, and refresh at once after this browser writes.

import { defaultTransport, FirestoreError } from "./transport.js";

export { FirestoreError };

const POLL_MS = 20000;

// ---------------------------------------------------------------------------
// Timestamp and field values
// ---------------------------------------------------------------------------

export class Timestamp {
  constructor(seconds, nanoseconds) {
    this.seconds = seconds;
    this.nanoseconds = nanoseconds;
  }
  static fromMillis(ms) {
    const m = Math.floor(Number(ms));
    const seconds = Math.floor(m / 1000);
    return new Timestamp(seconds, (m - seconds * 1000) * 1e6);
  }
  static fromDate(d) { return Timestamp.fromMillis(d.getTime()); }
  static now() { return Timestamp.fromMillis(Date.now()); }
  toMillis() { return this.seconds * 1000 + Math.floor(this.nanoseconds / 1e6); }
  toDate() { return new Date(this.toMillis()); }
  isEqual(o) { return o instanceof Timestamp && o.seconds === this.seconds && o.nanoseconds === this.nanoseconds; }
  valueOf() { return String(this.seconds + 1e12).padStart(14, "0") + "." + String(this.nanoseconds).padStart(9, "0"); }
  toString() { return `Timestamp(seconds=${this.seconds}, nanoseconds=${this.nanoseconds})`; }
  toJSON() { return { seconds: this.seconds, nanoseconds: this.nanoseconds }; }
}

class FieldValue {
  constructor(kind, value) { this.kind = kind; this.value = value; }
  isEqual(o) { return o instanceof FieldValue && o.kind === this.kind; }
}
export const serverTimestamp = () => new FieldValue("serverTimestamp");
export const arrayUnion = (...v) => new FieldValue("arrayUnion", v);
export const arrayRemove = (...v) => new FieldValue("arrayRemove", v);
export const deleteField = () => new FieldValue("delete");
export const increment = (n) => new FieldValue("increment", n);

function encode(v, top = true) {
  if (v instanceof Timestamp) return { $ts: v.toMillis() };
  if (v instanceof Date) return { $ts: v.getTime() };
  if (v instanceof FieldValue) {
    if (!top && v.kind !== "serverTimestamp") throw new FirestoreError("invalid-argument", "Field values cannot be nested in arrays.");
    return v.value === undefined ? { $sv: v.kind } : { $sv: v.kind, v: Array.isArray(v.value) ? v.value.map((x) => encode(x, false)) : v.value };
  }
  if (Array.isArray(v)) return v.map((x) => encode(x, false));
  if (v instanceof DocumentReference) throw new FirestoreError("invalid-argument", "Document references are not supported.");
  if (v && typeof v === "object") {
    const out = {};
    for (const [k, x] of Object.entries(v)) if (x !== undefined) out[k] = encode(x, top);
    return out;
  }
  if (typeof v === "number" && !Number.isFinite(v)) throw new FirestoreError("invalid-argument", "Numbers must be finite.");
  return v;
}

function decode(v) {
  if (Array.isArray(v)) return v.map(decode);
  if (v && typeof v === "object") {
    const keys = Object.keys(v);
    if (keys.length === 1 && keys[0] === "$ts") return Timestamp.fromMillis(v.$ts);
    const out = {};
    for (const k of keys) out[k] = decode(v[k]);
    return out;
  }
  return v;
}

// ---------------------------------------------------------------------------
// Database, references and queries
// ---------------------------------------------------------------------------

export class Firestore {
  constructor(transport) {
    this.type = "firestore";
    this.transport = transport;
    this._listeners = new Set();
    this._timer = null;
    this._refreshSoon = null;
    this._visibilityHooked = false;
  }
}

let defaultDb = null;
export function getFirestore() {
  if (!defaultDb) defaultDb = new Firestore(defaultTransport);
  return defaultDb;
}
export const initializeFirestore = () => getFirestore();
export function connectFirestoreEmulator() {}
/** Used by the test harness to act as different users. */
export function createFirestore(transport) { return new Firestore(transport); }

const AUTO_ID_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
function autoId() {
  const bytes = new Uint8Array(20);
  globalThis.crypto.getRandomValues(bytes);
  let id = "";
  for (const b of bytes) id += AUTO_ID_CHARS[b % AUTO_ID_CHARS.length];
  return id;
}

function segmentsOf(parts) {
  const segs = [];
  for (const p of parts) {
    if (typeof p !== "string" || !p) throw new FirestoreError("invalid-argument", "Path segments must be non-empty strings.");
    for (const s of p.split("/")) if (s) segs.push(s);
  }
  return segs;
}

export class DocumentReference {
  constructor(firestore, path) {
    this.type = "document";
    this.firestore = firestore;
    this.path = path;
    this.id = path.split("/").pop();
  }
  get parent() { return new CollectionReference(this.firestore, this.path.split("/").slice(0, -1).join("/")); }
  withConverter() { return this; }
}

export class Query {
  constructor(firestore, path, constraints = []) {
    this.type = "query";
    this.firestore = firestore;
    this._path = path;
    this._constraints = constraints;
  }
  withConverter() { return this; }
}

export class CollectionReference extends Query {
  constructor(firestore, path) {
    super(firestore, path, []);
    this.type = "collection";
    this.path = path;
    this.id = path.split("/").pop();
  }
  get parent() {
    const segs = this.path.split("/");
    return segs.length > 1 ? new DocumentReference(this.firestore, segs.slice(0, -1).join("/")) : null;
  }
}

function baseOf(parent) {
  if (parent instanceof Firestore) return { db: parent, prefix: [] };
  if (parent instanceof DocumentReference || parent instanceof CollectionReference) return { db: parent.firestore, prefix: parent.path.split("/") };
  throw new FirestoreError("invalid-argument", "Expected a Firestore instance or a reference.");
}

export function collection(parent, ...parts) {
  const { db, prefix } = baseOf(parent);
  const segs = [...prefix, ...segmentsOf(parts)];
  if (segs.length % 2 !== 1) throw new FirestoreError("invalid-argument", "Invalid collection reference: " + segs.join("/"));
  return new CollectionReference(db, segs.join("/"));
}

export function doc(parent, ...parts) {
  const { db, prefix } = baseOf(parent);
  let segs = [...prefix, ...segmentsOf(parts)];
  if (parent instanceof CollectionReference && parts.length === 0) segs = [...segs, autoId()];
  if (segs.length % 2 !== 0) throw new FirestoreError("invalid-argument", "Invalid document reference: " + segs.join("/"));
  return new DocumentReference(db, segs.join("/"));
}

export const where = (field, op, value) => ({ type: "where", field: String(field), op, value });
export const orderBy = (field, direction = "asc") => ({ type: "orderBy", field: String(field), direction });
export const limit = (n) => ({ type: "limit", n });
export const documentId = () => "__name__";

export function query(base, ...constraints) {
  if (!(base instanceof Query)) throw new FirestoreError("invalid-argument", "query() expects a collection or a query.");
  return new Query(base.firestore, base._path, [...base._constraints, ...constraints.filter(Boolean)]);
}

function target(ref) {
  if (ref instanceof DocumentReference) return { kind: "doc", path: ref.path };
  if (ref instanceof Query) {
    const t = { kind: "query", collection: ref._path, where: [], orderBy: [], limit: null };
    for (const c of ref._constraints) {
      if (c.type === "where") t.where.push([c.field, c.op, encode(c.value, false)]);
      else if (c.type === "orderBy") t.orderBy.push([c.field, c.direction === "desc" ? "desc" : "asc"]);
      else if (c.type === "limit") t.limit = c.n;
    }
    return t;
  }
  throw new FirestoreError("invalid-argument", "Expected a document reference or a query.");
}

// ---------------------------------------------------------------------------
// Snapshots
// ---------------------------------------------------------------------------

const META = Object.freeze({ hasPendingWrites: false, fromCache: false });

function fieldAt(data, field) {
  let cur = data;
  for (const part of String(field).split(".")) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = cur[part];
  }
  return cur;
}

export class DocumentSnapshot {
  constructor(ref, raw) {
    this.ref = ref;
    this.id = ref.id;
    this.metadata = META;
    this._raw = raw;
    this._version = raw && raw.version ? raw.version : 0;
  }
  exists() { return !!(this._raw && this._raw.exists !== false && this._raw.data !== undefined); }
  data() { return this.exists() ? decode(this._raw.data) : undefined; }
  get(field) { return this.exists() ? fieldAt(this.data(), field) : undefined; }
}

export class QuerySnapshot {
  constructor(q, docs) {
    this.query = q;
    this.docs = docs;
    this.size = docs.length;
    this.empty = docs.length === 0;
    this.metadata = META;
  }
  forEach(cb, thisArg) { this.docs.forEach(cb, thisArg); }
  docChanges() { return this.docs.map((d, i) => ({ type: "added", doc: d, oldIndex: -1, newIndex: i })); }
}

function snapshotFor(ref, result) {
  if (result && result.error) throw new FirestoreError(result.error.code, result.error.message);
  if (ref instanceof DocumentReference) return new DocumentSnapshot(ref, result);
  const docs = (result.docs || []).map((d) => new DocumentSnapshot(new DocumentReference(ref.firestore, d.path), { exists: true, ...d }));
  return new QuerySnapshot(ref, docs);
}

async function readTargets(db, refs) {
  const res = await db.transport.post("read", { targets: refs.map(target) });
  return res.results || [];
}

export async function getDoc(ref) {
  const [r] = await readTargets(ref.firestore, [ref]);
  return snapshotFor(ref, r);
}
export async function getDocs(q) {
  const [r] = await readTargets(q.firestore, [q]);
  return snapshotFor(q, r);
}
export const getDocFromServer = getDoc;
export const getDocsFromServer = getDocs;
export const getDocFromCache = getDoc;

// ---------------------------------------------------------------------------
// Writes, batches and transactions
// ---------------------------------------------------------------------------

function updateData(args) {
  if (args.length === 1 && args[0] && typeof args[0] === "object") return encode(args[0]);
  const out = {};
  for (let i = 0; i + 1 < args.length; i += 2) out[String(args[i])] = encode(args[i + 1]);
  return out;
}

async function commitWrites(db, writes, preconditions = []) {
  const res = await db.transport.post("commit", { writes, preconditions });
  refreshListenersSoon(db);
  return res;
}

export function setDoc(ref, data, options) {
  return commitWrites(ref.firestore, [{ op: "set", path: ref.path, data: encode(data), merge: !!(options && (options.merge || options.mergeFields)) }]).then(() => undefined);
}
export function updateDoc(ref, ...args) {
  return commitWrites(ref.firestore, [{ op: "update", path: ref.path, data: updateData(args) }]).then(() => undefined);
}
export function deleteDoc(ref) {
  return commitWrites(ref.firestore, [{ op: "delete", path: ref.path }]).then(() => undefined);
}
export async function addDoc(coll, data) {
  const ref = doc(coll);
  await setDoc(ref, data);
  return ref;
}

export class WriteBatch {
  constructor(db) { this._db = db; this._writes = []; this._done = false; }
  set(ref, data, options) { this._writes.push({ op: "set", path: ref.path, data: encode(data), merge: !!(options && (options.merge || options.mergeFields)) }); return this; }
  update(ref, ...args) { this._writes.push({ op: "update", path: ref.path, data: updateData(args) }); return this; }
  delete(ref) { this._writes.push({ op: "delete", path: ref.path }); return this; }
  async commit() {
    if (this._done) throw new FirestoreError("failed-precondition", "A write batch can only be committed once.");
    this._done = true;
    if (!this._writes.length) return;
    await commitWrites(this._db, this._writes);
  }
}
export const writeBatch = (db) => new WriteBatch(db);

class Transaction {
  constructor(db) { this._db = db; this._writes = []; this._reads = new Map(); }
  async get(ref) {
    const [r] = await readTargets(this._db, [ref]);
    const snap = snapshotFor(ref, r);
    this._reads.set(ref.path, snap._version);
    return snap;
  }
  set(ref, data, options) { this._writes.push({ op: "set", path: ref.path, data: encode(data), merge: !!(options && options.merge) }); return this; }
  update(ref, ...args) { this._writes.push({ op: "update", path: ref.path, data: updateData(args) }); return this; }
  delete(ref) { this._writes.push({ op: "delete", path: ref.path }); return this; }
}

export async function runTransaction(db, fn, options) {
  const attempts = (options && options.maxAttempts) || 5;
  let lastError;
  for (let i = 0; i < attempts; i++) {
    const tx = new Transaction(db);
    const result = await fn(tx);
    if (!tx._writes.length) return result;
    try {
      await commitWrites(db, tx._writes, [...tx._reads].map(([path, version]) => ({ path, version })));
      return result;
    } catch (e) {
      lastError = e;
      if (e && e.code === "aborted") continue;
      throw e;
    }
  }
  throw lastError;
}

// ---------------------------------------------------------------------------
// Live listeners (polling)
// ---------------------------------------------------------------------------

function sameJson(a, b) { return JSON.stringify(a) === JSON.stringify(b); }

function hidden() { return typeof document !== "undefined" && document.visibilityState === "hidden"; }

async function pollAll(db) {
  const listeners = [...db._listeners].filter((l) => !l.closed);
  if (!listeners.length || hidden()) return;
  let results;
  try {
    results = await readTargets(db, listeners.map((l) => l.ref));
  } catch (e) {
    for (const l of listeners) if (!l.closed && !l.everDelivered) l.error(e);
    return;
  }
  listeners.forEach((l, i) => deliver(l, results[i]));
}

function deliver(l, result) {
  if (l.closed) return;
  if (result && result.error) {
    if (!l.lastError || l.lastError.code !== result.error.code) {
      l.lastError = result.error;
      l.error(new FirestoreError(result.error.code, result.error.message));
    }
    return;
  }
  l.lastError = null;
  if (l.everDelivered && sameJson(result, l.last)) return;
  l.last = result;
  l.everDelivered = true;
  let snap;
  try { snap = snapshotFor(l.ref, result); } catch (e) { l.error(e); return; }
  try { l.next(snap); } catch (e) { console.error(e); }
}

function ensureTimer(db) {
  if (db._timer || typeof setInterval === "undefined") return;
  db._timer = setInterval(() => { void pollAll(db); }, POLL_MS);
  if (!db._visibilityHooked && typeof document !== "undefined") {
    db._visibilityHooked = true;
    document.addEventListener("visibilitychange", () => { if (!hidden()) void pollAll(db); });
    if (typeof window !== "undefined") window.addEventListener("online", () => void pollAll(db));
  }
}

function refreshListenersSoon(db) {
  if (!db._listeners.size || db._refreshSoon) return;
  db._refreshSoon = setTimeout(() => { db._refreshSoon = null; void pollAll(db); }, 60);
}

export function onSnapshot(ref, ...args) {
  let a = args;
  if (a[0] && typeof a[0] === "object" && !("next" in a[0]) && typeof a[0] !== "function") a = a.slice(1); // options
  let next, error;
  if (a[0] && typeof a[0] === "object") ({ next, error } = a[0]);
  else [next, error] = a;
  const db = ref.firestore;
  const listener = {
    ref, closed: false, everDelivered: false, last: null, lastError: null,
    next: next || (() => {}),
    error: error || ((e) => console.error(e)),
  };
  db._listeners.add(listener);
  ensureTimer(db);
  readTargets(db, [ref]).then(([r]) => deliver(listener, r), (e) => { if (!listener.closed) listener.error(e); });
  return () => {
    listener.closed = true;
    db._listeners.delete(listener);
    if (!db._listeners.size && db._timer) { clearInterval(db._timer); db._timer = null; }
  };
}

export const onSnapshotsInSync = () => () => {};
export const enableIndexedDbPersistence = async () => {};
export const disableNetwork = async () => {};
export const enableNetwork = async () => {};
