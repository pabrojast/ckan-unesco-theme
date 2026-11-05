// Applications to join the Broad Group of a Working Group: groupApplications/{body}_{uid}.
// The leadership of the group and the UNESCO Secretariat approve or decline them. Approval records the Broad Group
// badge on the member's role (roles/{uid}.badges), exactly as "Manage access & badges" does.
import { collection, doc, getDoc, limit, onSnapshot, query, serverTimestamp, setDoc, updateDoc, where, writeBatch, arrayUnion } from "firebase/firestore";
import { auth, db } from "./firebase";

export type Application = { id: string; uid: string; name: string; body: string; status: "pending" | "approved" | "declined"; createdAt: string; decidedBy: string; decidedAt: string };
/** Badge recording Broad Group membership of a body. */
export const memberBadge = (body: string) => (/^wg[1-5]$/.test(body) ? `${body}-member` : body);

const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : typeof v === "string" ? v : "");
const unpack = (s: any): Application => {
  const x = s.data({ serverTimestamps: "estimate" }) || {};
  return { id: s.id, uid: x.uid || "", name: x.name || "", body: x.body || "", status: x.status || "pending", createdAt: iso(x.createdAt), decidedBy: x.decidedBy || "", decidedAt: iso(x.decidedAt) };
};
type Stop = () => void;
const none: Stop = () => {};
const sortNew = (a: Application[]) => a.sort((x, y) => y.createdAt.localeCompare(x.createdAt));

export function subscribeOwnApplications(uid: string, next: (a: Application[]) => void, error: (e: any) => void): Stop {
  if (!db || !uid) return none;
  return onSnapshot(query(collection(db, "groupApplications"), where("uid", "==", uid), limit(20)), (s) => next(s.docs.map(unpack)), error);
}
/** Applications to one body, for its leadership. */
export function subscribeBodyApplications(body: string, next: (a: Application[]) => void, error: (e: any) => void): Stop {
  if (!db || !body) return none;
  return onSnapshot(query(collection(db, "groupApplications"), where("body", "==", body), limit(200)), (s) => next(sortNew(s.docs.map(unpack))), error);
}
/** Applications awaiting a decision in every body, for the UNESCO Secretariat. */
export function subscribePendingApplications(next: (a: Application[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(query(collection(db, "groupApplications"), where("status", "==", "pending"), limit(300)), (s) => next(sortNew(s.docs.map(unpack))), error);
}

/** Sends (or sends again after a decline) an application to the Broad Group of a body. */
export async function applyToGroup(body: string, name: string) {
  const uid = auth?.currentUser?.uid;
  if (!db || !uid) throw Error("Sign in first.");
  const ref = doc(db, "groupApplications", `${body}_${uid}`);
  // The member's earlier application to this group, if any (read with the rules of 3.25.1; treated as none if unreadable).
  const before = await getDoc(ref).catch(() => null);
  const status = before?.exists() ? before.data().status : "";
  if (status === "pending") return;
  if (status === "approved") throw Error("You are already a member of this Broad Group.");
  const fields = { name: name.slice(0, 120), status: "pending", createdAt: serverTimestamp(), decidedBy: "", decidedAt: null };
  if (status) await updateDoc(ref, fields);
  else await setDoc(ref, { uid, body, ...fields });
}

/** Approves an application (adding the Broad Group badge to the member's role) or declines it. */
export async function decideApplication(a: Application, approve: boolean) {
  const me = auth?.currentUser?.uid;
  if (!db || !me) throw Error("Sign in first.");
  const batch = writeBatch(db);
  if (approve) {
    const roleRef = doc(db, "roles", a.uid), role = await getDoc(roleRef);
    if (role.exists()) batch.update(roleRef, { badges: arrayUnion(memberBadge(a.body)) });
    else batch.set(roleRef, { admin: false, role: "member", wgs: [], badges: [memberBadge(a.body)] });
  }
  batch.update(doc(db, "groupApplications", a.id), { status: approve ? "approved" : "declined", decidedBy: me, decidedAt: serverTimestamp() });
  await batch.commit();
}
