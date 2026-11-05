// Firestore access for the mailing lists: mailingLists/{list}/entries/{uid}.
import { collection, doc, getDoc, getDocs, limit, query, setDoc, deleteDoc, serverTimestamp } from "firebase/firestore";
import { db } from "./firebase";
import { DECADE, entryChanges, mailingBodyIds, memberTiers, type MailingEntry } from "./mailing";

const lists = [...mailingBodyIds, DECADE];
const syncKey = (uid: string) => "dacs-mailing-v1-" + uid;

async function currentEntries(uid: string) {
  const snaps = await Promise.all(lists.map((l) => getDoc(doc(db!, "mailingLists", l, "entries", uid)).catch(() => null)));
  return Object.fromEntries(lists.map((l, i) => [l, snaps[i]?.exists() ? (snaps[i]!.data() as any) : undefined]));
}
async function apply(uid: string, current: Record<string, any>, wanted: Record<string, string>, email: string, name: string) {
  const { write, remove } = entryChanges(current, wanted, email, name);
  await Promise.all([
    ...write.map((w) => setDoc(doc(db!, "mailingLists", w.list, "entries", uid), { name: name.slice(0, 120), email, tier: w.tier, updatedAt: serverTimestamp() })),
    ...remove.map((l) => deleteDoc(doc(db!, "mailingLists", l, "entries", uid))),
  ]);
}

/**
 * Keeps the signed-in member's own entries up to date. Runs after sign-in; does nothing when the
 * member's email, name and groups are unchanged since the last run on this browser.
 */
export async function syncOwnEntries(me: { id: string; name: string; role: string; directWgs?: number[]; assignedBadgeIds?: string[]; admin?: boolean; wgs?: number[] }, email: string, governance: any[]) {
  if (!db || !me?.id || !email) return;
  const role = { role: me.role, wgs: me.directWgs || [], badges: me.assignedBadgeIds || [], admin: !!me.admin };
  const wanted: Record<string, string> = { ...memberTiers(me.id, role, governance, me), [DECADE]: "member" };
  const signature = JSON.stringify([email, me.name, wanted]);
  try { if (localStorage.getItem(syncKey(me.id)) === signature) return; } catch { /* storage unavailable */ }
  await apply(me.id, await currentEntries(me.id), wanted, email, me.name || email);
  try { localStorage.setItem(syncKey(me.id), signature); } catch { /* storage unavailable */ }
}

/**
 * UNESCO Secretariat: updates a member's entries after their role or appointments change.
 * The member's email comes from their existing entries; a member without entries is added at their next sign-in.
 */
export async function refreshMemberEntries(uid: string) {
  if (!db || !uid) return;
  const current = await currentEntries(uid);
  const known = Object.values(current).find((e: any) => e?.email) as any;
  if (!known) return;
  const [roleSnap, profileSnap, govSnap] = await Promise.all([
    getDoc(doc(db, "roles", uid)),
    getDoc(doc(db, "profiles", uid)),
    getDocs(collection(db, "governance")),
  ]);
  if (!profileSnap.exists()) return;
  const governance = govSnap.docs.map((d) => ({ id: d.id, ...d.data() }));
  const profile = profileSnap.data() as any;
  const wanted: Record<string, string> = { ...memberTiers(uid, roleSnap.exists() ? roleSnap.data() : {}, governance, profile), [DECADE]: "member" };
  await apply(uid, current, wanted, known.email, profile.name || known.name);
}

export async function loadList(list: string): Promise<MailingEntry[]> {
  if (!db) return [];
  const s = await getDocs(query(collection(db, "mailingLists", list, "entries"), limit(1000)));
  return s.docs.map((d) => ({ id: d.id, ...(d.data() as any) }));
}
