import { collection, doc, query, orderBy, limit, onSnapshot, writeBatch, serverTimestamp, updateDoc, deleteDoc } from 'firebase/firestore';
import { cleanAttachments, type Attachment } from './files-store';
import { auth, db } from './firebase';
import type { DiscussionMessage } from './discussion';
const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : v || '');
// Pending server timestamps are estimated so a new message sorts as the newest straight away.
const unpack = (d: any) => { const x = d.data({ serverTimestamps: 'estimate' }); return { id: d.id, ...x, createdAt: iso(x.createdAt), updatedAt: iso(x.updatedAt) }; };
export const DISCUSSION_LIMIT = 150;
export function subscribeDiscussion(space: string, next: (m: DiscussionMessage[], capped: boolean) => void, error: (e: any) => void) {
  if (!db) return () => {};
  return onSnapshot(query(collection(db, 'groupDiscussions', space, 'messages'), orderBy('createdAt', 'desc'), limit(DISCUSSION_LIMIT + 1)),
    (s) => next(s.docs.slice(0, DISCUSSION_LIMIT).map(unpack) as DiscussionMessage[], s.size > DISCUSSION_LIMIT), error);
}
/** Writes a message and one Hub notification per tagged member in a single batch. */
export async function postMessage(v: { space: string; parent: string; body: string; mentions: string[]; authorName: string; attachments?: Attachment[] }) {
  if (!db || !auth?.currentUser) throw Error('Sign in to take part in the discussion.');
  const uid = auth.currentUser.uid, body = v.body.trim();
  if (!body) throw Error('Write a message first.');
  const batch = writeBatch(db), ref = doc(collection(db, 'groupDiscussions', v.space, 'messages'));
  const mentions = [...new Set(v.mentions)].filter((m) => m !== uid).slice(0, 20);
  batch.set(ref, { space: v.space, parent: v.parent, author: uid, author_name: v.authorName, body, mentions, deleted: false, ...(v.attachments?.length ? { attachments: cleanAttachments(v.attachments) } : {}), createdAt: serverTimestamp(), updatedAt: serverTimestamp() });
  notify(batch, mentions, { space: v.space, messageId: ref.id, threadId: v.parent || ref.id, excerpt: body, fromName: v.authorName });
  await batch.commit();
  return ref.id;
}
export async function editMessage(m: DiscussionMessage, body: string, mentions: string[], authorName: string) {
  if (!db || !auth?.currentUser) throw Error('Sign in to edit.');
  const uid = auth.currentUser.uid, clean = [...new Set(mentions)].filter((x) => x !== uid).slice(0, 20);
  const batch = writeBatch(db);
  batch.update(doc(db, 'groupDiscussions', m.space, 'messages', m.id), { body: body.trim(), mentions: clean, updatedAt: serverTimestamp() });
  notify(batch, clean.filter((x) => !m.mentions.includes(x)), { space: m.space, messageId: m.id, threadId: m.parent || m.id, excerpt: body.trim(), fromName: authorName });
  await batch.commit();
}
function notify(batch: ReturnType<typeof writeBatch>, to: string[], n: { space: string; messageId: string; threadId: string; excerpt: string; fromName: string }) {
  for (const uid of to)
    batch.set(doc(collection(db!, 'inbox', uid, 'items')), { kind: 'mention', from: auth!.currentUser!.uid, from_name: n.fromName, space: n.space, messageId: n.messageId, threadId: n.threadId, excerpt: n.excerpt.slice(0, 200), read: false, createdAt: serverTimestamp() });
}
/** Topics with replies are kept as "removed" so the replies stay readable. */
export async function removeMessage(m: DiscussionMessage, hasReplies: boolean) {
  if (!db) return;
  const ref = doc(db, 'groupDiscussions', m.space, 'messages', m.id);
  if (hasReplies) await updateDoc(ref, { body: '', mentions: [], deleted: true, updatedAt: serverTimestamp() });
  else await deleteDoc(ref);
}
export type InboxItem = { id: string; kind: 'mention'; from: string; from_name: string; space: string; messageId: string; threadId: string; excerpt: string; read: boolean; createdAt: string };
export function subscribeInbox(uid: string, next: (items: InboxItem[]) => void, error: (e: any) => void) {
  if (!db || !uid) return () => {};
  return onSnapshot(query(collection(db, 'inbox', uid, 'items'), orderBy('createdAt', 'desc'), limit(30)), (s) => next(s.docs.map(unpack) as InboxItem[]), error);
}
export async function markRead(uid: string, ids: string[]) {
  if (!db || !ids.length) return;
  const batch = writeBatch(db);
  for (const id of ids.slice(0, 30)) batch.update(doc(db, 'inbox', uid, 'items', id), { read: true });
  await batch.commit();
}
