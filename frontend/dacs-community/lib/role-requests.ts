// Firestore access for the roles declared by members at registration: roleRequests/{uid}.
import { collection, deleteDoc, doc, getDoc, onSnapshot, query, setDoc, where, limit, serverTimestamp } from "firebase/firestore";
import { db } from "./firebase";
import { nextRequest, type Claim, type Decision, type RoleRequest } from "./role-claims";
export * from "./role-claims";

const unpack = (s: any): RoleRequest => {
  const x = s.data({ serverTimestamps: "estimate" }) || {};
  const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : v || "");
  return { id: s.id, name: x.name || "", claims: x.claims || {}, note: x.note || "", decisions: x.decisions || {}, status: x.status || "pending", updatedAt: iso(x.updatedAt), reviewedAt: iso(x.reviewedAt) };
};

export async function getOwnRequest(uid: string): Promise<RoleRequest | null> {
  if (!db || !uid) return null;
  const s = await getDoc(doc(db, "roleRequests", uid));
  return s.exists() ? unpack(s) : null;
}
export function subscribeOwnRequest(uid: string, next: (r: RoleRequest | null) => void, error: (e: any) => void) {
  if (!db || !uid) return () => {};
  return onSnapshot(doc(db, "roleRequests", uid), (s) => next(s.exists() ? unpack(s) : null), error);
}
/** Saves a member's declaration; returns false when nothing changed. */
export async function saveOwnRequest(uid: string, name: string, claims: Record<string, Claim>, note: string) {
  if (!db) return false;
  const ref = doc(db, "roleRequests", uid);
  const s = await getDoc(ref);
  const prev = s.exists() ? unpack(s) : null;
  const next = nextRequest(prev, claims, note);
  if (!next) return false;
  if (!Object.keys(claims).length && !note) { if (prev) await deleteDoc(ref); return true; }
  await setDoc(ref, { name: name.slice(0, 120), ...next, ...(prev?.reviewedAt ? { reviewedAt: s.data()!.reviewedAt } : {}), updatedAt: serverTimestamp() });
  return true;
}

/** UNESCO Secretariat: requests awaiting a decision. */
export function subscribePendingRequests(next: (r: RoleRequest[]) => void, error: (e: any) => void) {
  if (!db) return () => {};
  return onSnapshot(query(collection(db, "roleRequests"), where("status", "==", "pending"), limit(200)), (s) => next(s.docs.map(unpack).sort((a, b) => a.updatedAt.localeCompare(b.updatedAt))), error);
}
export async function recordDecisions(r: RoleRequest, decisions: Record<string, Decision>) {
  const all = { ...r.decisions, ...decisions };
  const status = Object.keys(r.claims).every((b) => b in all) ? "reviewed" : "pending";
  await setDoc(doc(db!, "roleRequests", r.id), { name: r.name, claims: r.claims, note: r.note, decisions: all, status, updatedAt: serverTimestamp(), reviewedAt: serverTimestamp() });
}
