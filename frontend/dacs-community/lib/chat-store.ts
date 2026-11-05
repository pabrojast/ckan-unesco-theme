// Private conversations between two members: chats/{a_b}/messages/{id}.
// Moderators (the owner account and the people it appoints in config/chatMonitors) can read every conversation,
// remove a message and handle reports (chatReports).
import { collection, doc, getDoc, limit, onSnapshot, orderBy, query, serverTimestamp, setDoc, updateDoc, where, writeBatch } from "firebase/firestore";
import { auth, db, isPlatformOwner } from "./firebase";

// IHP-WINS: the owner is a platform administrator of the community (IHP-WINS sysadmin or group admin).
export type Chat = { id: string; kind?: "group"; title?: string; createdBy?: string; members: string[]; names: Record<string, string>; updatedAt: string; createdAt: string; lastMessage: { text: string; from: string; at: string }; lastRead: Record<string, string> };
export type ChatMessage = { id: string; from: string; text: string; createdAt: string; removed?: boolean; removedBy?: string };
export type ChatReport = { id: string; chatId: string; messageId: string; reporter: string; reporterName: string; reason: string; status: "open" | "resolved"; createdAt: string; resolution?: string; resolvedBy?: string; resolvedAt?: string };

const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : typeof v === "string" ? v : "");
const unpack = (s: any) => {
  const x = s.data({ serverTimestamps: "estimate" }) || {};
  const out: any = { id: s.id };
  for (const [k, v] of Object.entries(x)) out[k] = (v as any)?.toDate ? iso(v) : v;
  if (x.lastMessage) out.lastMessage = { ...x.lastMessage, at: iso(x.lastMessage.at) };
  if (x.lastRead) out.lastRead = Object.fromEntries(Object.entries(x.lastRead).map(([k, v]) => [k, iso(v)]));
  return out;
};
type Stop = () => void;
const none: Stop = () => {};

export const chatIdFor = (a: string, b: string) => [a, b].sort().join("_");
export const otherMember = (c: Pick<Chat, "members">, me: string) => c.members.find((m) => m !== me) || me;
export const isGroup = (c?: Pick<Chat, "kind"> | null) => c?.kind === "group";
export const MAX_GROUP = 30;
export const preview = (text: string) => text.replace(/\s+/g, " ").trim().slice(0, 200);
/** A conversation is unread when its last message came from the other person after the member last opened it. */
export const isUnread = (c: Chat, me: string) => !!c.lastMessage && c.lastMessage.from !== me && (!c.lastRead?.[me] || c.lastRead[me] < c.updatedAt);

export function subscribeMyChats(uid: string, next: (c: Chat[]) => void, error: (e: any) => void): Stop {
  if (!db || !uid) return none;
  return onSnapshot(query(collection(db, "chats"), where("members", "array-contains", uid), limit(200)),
    (s) => next(s.docs.map(unpack).sort((a: Chat, b: Chat) => b.updatedAt.localeCompare(a.updatedAt))), error);
}
/**
 * Listens to the messages of a conversation. A new conversation appears on the page (from the local write) a moment
 * before the database has saved it, and a listener opened in that moment is refused because the conversation does not
 * exist yet on the server. Refusals are therefore retried quietly for a few seconds before an error is shown.
 */
export function subscribeMessages(chatId: string, next: (m: ChatMessage[]) => void, error: (e: any) => void): Stop {
  if (!db || !chatId) return none;
  let stop: Stop = none, timer: ReturnType<typeof setTimeout> | undefined, attempt = 0, closed = false;
  const open = () => {
    stop = onSnapshot(query(collection(db!, "chats", chatId, "messages"), orderBy("createdAt", "desc"), limit(300)),
      (s) => { attempt = 0; next(s.docs.map(unpack).reverse()); },
      (e) => {
        if (closed) return;
        if (e?.code === "permission-denied" && attempt < 6) { attempt += 1; timer = setTimeout(open, 400 * attempt); return; }
        error(e);
      });
  };
  open();
  return () => { closed = true; if (timer) clearTimeout(timer); stop(); };
}

/** Sends a message, creating the conversation with its first message. */
export async function sendMessage(me: { id: string; name: string }, other: { id: string; name: string }, text: string) {
  const body = text.trim().slice(0, 4000);
  if (!db || !body) return;
  const id = chatIdFor(me.id, other.id), ref = doc(db, "chats", id);
  const exists = (await getDoc(ref)).exists();
  const batch = writeBatch(db);
  const last = { text: preview(body), from: me.id, at: serverTimestamp() };
  if (exists) batch.update(ref, { lastMessage: last, updatedAt: serverTimestamp(), [`lastRead.${me.id}`]: serverTimestamp() });
  else {
    const members = [me.id, other.id].sort();
    batch.set(ref, { members, names: { [me.id]: me.name, [other.id]: other.name }, createdAt: serverTimestamp(), updatedAt: serverTimestamp(), lastMessage: last, lastRead: { [me.id]: serverTimestamp() } });
  }
  batch.set(doc(collection(db, "chats", id, "messages")), { from: me.id, text: body, createdAt: serverTimestamp() });
  await batch.commit();
}
/** Sends a message to an existing conversation (direct or group). */
export async function sendToChat(chat: Chat, me: { id: string }, text: string) {
  const body = text.trim().slice(0, 4000);
  if (!db || !body) return;
  const batch = writeBatch(db), ref = doc(db, "chats", chat.id);
  batch.update(ref, { lastMessage: { text: preview(body), from: me.id, at: serverTimestamp() }, updatedAt: serverTimestamp(), [`lastRead.${me.id}`]: serverTimestamp() });
  batch.set(doc(collection(db, "chats", chat.id, "messages")), { from: me.id, text: body, createdAt: serverTimestamp() });
  await batch.commit();
}
/** Creates a group conversation with the member and the people chosen. */
export async function createGroup(me: { id: string; name: string }, people: { id: string; name: string }[], title: string) {
  if (!db) throw Error("Sign in first.");
  const all = [me, ...people.filter((p) => p.id !== me.id)].slice(0, MAX_GROUP);
  if (all.length < 3) throw Error("Choose at least two other members.");
  const ref = doc(collection(db, "chats"));
  await setDoc(ref, {
    kind: "group", title: title.trim().slice(0, 80) || "Group conversation", createdBy: me.id,
    members: all.map((p) => p.id), names: Object.fromEntries(all.map((p) => [p.id, p.name.slice(0, 120)])),
    createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
    lastMessage: { text: "", from: me.id, at: serverTimestamp() }, lastRead: { [me.id]: serverTimestamp() },
  });
  return ref.id;
}
/** The creator of a group renames it, or adds and removes members. */
export async function updateGroup(chat: Chat, title: string, people: { id: string; name: string }[]) {
  const members = [...new Set([chat.createdBy!, ...people.map((p) => p.id)])].slice(0, MAX_GROUP);
  const names = Object.fromEntries(members.map((id) => [id, (people.find((p) => p.id === id)?.name || chat.names[id] || "Member").slice(0, 120)]));
  await updateDoc(doc(db!, "chats", chat.id), { title: title.trim().slice(0, 80) || "Group conversation", members, names });
}
/** A member leaves a group conversation. */
export async function leaveGroup(chat: Chat, uid: string) {
  const members = chat.members.filter((m) => m !== uid);
  const names = Object.fromEntries(Object.entries(chat.names).filter(([k]) => k !== uid));
  const ref = doc(db!, "chats", chat.id);
  const snap = await getDoc(ref);
  const lastRead = Object.fromEntries(Object.entries((snap.data() as any)?.lastRead || {}).filter(([k]) => k !== uid));
  await updateDoc(ref, { members, names, lastRead });
}
export async function markRead(chatId: string, uid: string) {
  if (!db || !chatId || !uid) return;
  await updateDoc(doc(db, "chats", chatId), { [`lastRead.${uid}`]: serverTimestamp() });
}
export async function reportChat(chatId: string, messageId: string, reason: string, reporterName: string) {
  const uid = auth?.currentUser?.uid;
  if (!db || !uid) throw Error("Sign in first.");
  await setDoc(doc(collection(db, "chatReports")), { chatId, messageId, reporter: uid, reporterName, reason: reason.trim().slice(0, 1000), status: "open", createdAt: serverTimestamp() });
}

/* ---------- Moderation ---------- */
export function isOwnerAccount() {
  const u = auth?.currentUser;
  return isPlatformOwner(u);
}
export function subscribeMonitors(next: (uids: string[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(doc(db, "config", "chatMonitors"), (s) => next(s.exists() ? (s.data() as any).uids || [] : []), error);
}
export async function saveMonitors(uids: string[]) {
  await setDoc(doc(db!, "config", "chatMonitors"), { uids: [...new Set(uids)].slice(0, 20), updatedAt: serverTimestamp() });
}
export function subscribeAllChats(next: (c: Chat[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(query(collection(db, "chats"), limit(500)), (s) => next(s.docs.map(unpack).sort((a: Chat, b: Chat) => b.updatedAt.localeCompare(a.updatedAt))), error);
}
export function subscribeReports(next: (r: ChatReport[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(query(collection(db, "chatReports"), limit(300)), (s) => next(s.docs.map(unpack).sort((a: ChatReport, b: ChatReport) => b.createdAt.localeCompare(a.createdAt))), error);
}
export async function resolveReport(id: string, resolution: string) {
  const uid = auth?.currentUser?.uid;
  await updateDoc(doc(db!, "chatReports", id), { status: "resolved", resolution: resolution.trim().slice(0, 1000), resolvedBy: uid, resolvedAt: serverTimestamp() });
}
export async function removeMessage(chatId: string, messageId: string) {
  const uid = auth?.currentUser?.uid;
  await updateDoc(doc(db!, "chats", chatId, "messages", messageId), { text: "", removed: true, removedBy: uid });
}
