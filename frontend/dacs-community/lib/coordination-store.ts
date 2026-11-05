// Firestore access for minutes, actions, work plans, decisions, consultations and the Secretariat dashboard.
// Queries use equality filters only and sort in the browser, so no new Firestore index is needed.
import { collection, doc, query, where, limit, onSnapshot, getDoc, getDocs, setDoc, updateDoc, deleteDoc, serverTimestamp, Timestamp } from "firebase/firestore";
import { auth, db } from "./firebase";
import type { ActionItem, WorkItem, ConsultationQuestion } from "./coordination";
const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : v || "");
const unpack = (d: any) => {
  const x = d.data({ serverTimestamps: "estimate" });
  return { id: d.id, ...Object.fromEntries(Object.entries(x).map(([k, v]) => [k, (v as any)?.toDate ? iso(v) : v])) } as any;
};
const uid = () => {
  if (!db || !auth?.currentUser) throw Error("Sign in first.");
  return auth.currentUser.uid;
};
type Stop = () => void;
const none: Stop = () => {};

/* ---------- Minutes ---------- */
export type Minutes = { summary: string; decisions: string; updatedBy: string; updatedAt: string };
export function subscribeMinutes(eventId: string, next: (m: Minutes | null) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(doc(db, "events", eventId, "meetingNotes", "minutes"), (s) => next(s.exists() ? (unpack(s) as Minutes) : null), error);
}
export async function saveMinutes(eventId: string, summary: string, decisions: string) {
  const me = uid();
  await setDoc(doc(db!, "events", eventId, "meetingNotes", "minutes"), { summary: summary.trim(), decisions: decisions.trim(), updatedBy: me, updatedAt: serverTimestamp() });
}

/* ---------- Actions ---------- */
export function subscribeMeetingActions(e: { id: string; body: string; meetingType: string }, next: (a: ActionItem[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(query(collection(db, "actions"), where("eventId", "==", e.id), where("body", "==", e.body), where("meetingType", "==", e.meetingType), limit(100)), (s) => next(s.docs.map(unpack)), error);
}
export function subscribeMyActions(owner: string, next: (a: ActionItem[]) => void, error: (e: any) => void): Stop {
  if (!db || !owner) return none;
  return onSnapshot(query(collection(db, "actions"), where("owner", "==", owner), limit(100)), (s) => next(s.docs.map(unpack)), error);
}
export async function saveAction(v: { id?: string; eventId: string; body: string; meetingType: string; title: string; owner: string; owner_name: string; due: string; status?: "open" | "done" }) {
  const me = uid();
  const fields = { title: v.title.trim(), owner: v.owner, owner_name: v.owner_name, due: v.due, status: v.status || "open", updatedAt: serverTimestamp() };
  if (!fields.title) throw Error("Describe the action.");
  if (v.id) await updateDoc(doc(db!, "actions", v.id), fields);
  else await setDoc(doc(collection(db!, "actions")), { ...fields, eventId: v.eventId, body: v.body, meetingType: v.meetingType, createdBy: me, createdAt: serverTimestamp() });
}
export async function setActionStatus(id: string, status: "open" | "done") {
  uid();
  await updateDoc(doc(db!, "actions", id), { status, updatedAt: serverTimestamp() });
}
export async function removeAction(id: string) {
  uid();
  await deleteDoc(doc(db!, "actions", id));
}
export async function fetchEvent(id: string) {
  if (!db || !id) return null;
  const s = await getDoc(doc(db, "events", id));
  if (!s.exists()) return null;
  const v = s.data();
  return { id: s.id, ...v, startAt: v.startAt.toDate().toISOString(), endAt: v.endAt.toDate().toISOString() } as any;
}

/* ---------- Work plans ---------- */
export function subscribeWorkplan(next: (items: WorkItem[]) => void, error: (e: any) => void, body?: string): Stop {
  if (!db) return none;
  const q = body ? query(collection(db, "workplanItems"), where("body", "==", body), limit(300)) : query(collection(db, "workplanItems"), limit(800));
  return onSnapshot(q, (s) => next(s.docs.map(unpack)), error);
}
export async function saveWorkItem(v: Omit<WorkItem, "createdAt" | "updatedAt"> & { id?: string }) {
  const me = uid();
  const id = v.id;
  const fields = { body: v.body, kind: v.kind, title: v.title.trim(), mg: v.mg, due: v.due, status: v.status, lead: v.lead.trim(), notes: v.notes.trim(), parent: v.kind === "milestone" ? String(v.parent || "") : "", updatedBy: me, updatedAt: serverTimestamp() };
  if (!fields.title) throw Error("Enter a title.");
  if (id) await updateDoc(doc(db!, "workplanItems", id), fields);
  else await setDoc(doc(collection(db!, "workplanItems")), { ...fields, createdAt: serverTimestamp() });
}
/** Links an activity to a flagship project of its Working Group, or removes the link (empty id). */
export async function linkActivity(activityId: string, project: string) {
  await updateDoc(doc(db!, "opportunities", activityId), { project: project.slice(0, 128) });
}
export async function removeWorkItem(id: string) {
  uid();
  await deleteDoc(doc(db!, "workplanItems", id));
}

/* ---------- Decisions ---------- */
export type Decision = { id: string; body: "smc" | "esc"; date: string; reference: string; title: string; text: string; eventId: string; visibility: "body" | "community"; createdBy: string; createdAt: string; updatedAt: string };
/** Members of the body see every entry; others see entries shared with the community. */
export function subscribeDecisions(scopes: { body: string; member: boolean }[], next: (d: Decision[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  const found = new Map<string, Decision[]>();
  const stops = scopes.map((s) =>
    onSnapshot(
      query(collection(db!, "decisions"), ...(s.member ? [where("body", "==", s.body)] : [where("body", "==", s.body), where("visibility", "==", "community")]), limit(300)),
      (snap) => {
        found.set(s.body, snap.docs.map(unpack));
        next([...found.values()].flat().sort((a, b) => b.date.localeCompare(a.date) || b.reference.localeCompare(a.reference)));
      },
      error,
    ),
  );
  return () => stops.forEach((s) => s());
}
export async function saveDecision(v: Omit<Decision, "id" | "createdBy" | "createdAt" | "updatedAt"> & { id?: string; createdBy?: string; createdAt?: string }) {
  const me = uid();
  const fields = { body: v.body, date: v.date, reference: v.reference.trim(), title: v.title.trim(), text: v.text.trim(), eventId: v.eventId, visibility: v.visibility, updatedBy: me, updatedAt: serverTimestamp() };
  if (!fields.title || !/^\d{4}-\d{2}-\d{2}$/.test(fields.date)) throw Error("Enter a date and a title.");
  if (v.id) await updateDoc(doc(db!, "decisions", v.id), fields);
  else await setDoc(doc(collection(db!, "decisions")), { ...fields, createdBy: me, createdAt: serverTimestamp() });
}
export async function removeDecision(id: string) {
  uid();
  await deleteDoc(doc(db!, "decisions", id));
}

/* ---------- Consultations ---------- */
export type Consultation = { id: string; owner: string; body: string; audience: "leadership" | "core" | "broad"; title: string; description: string; questions: ConsultationQuestion[]; deadline: string; status: "open" | "closed"; resultsVisible: boolean; createdAt: string; updatedAt: string };
export type ConsultationAnswer = { id: string; name: string; answers: Record<string, string>; updatedAt: string };
export function subscribeConsultations(scopes: { body: string; types: string[] }[], next: (c: Consultation[]) => void, error: (e: any) => void): Stop {
  if (!db || !scopes.length) {
    next([]);
    return none;
  }
  const found = new Map<string, Consultation[]>();
  const stops = scopes.map((s) =>
    onSnapshot(query(collection(db!, "consultations"), where("body", "==", s.body), where("audience", "in", s.types), limit(60)), (snap) => {
      found.set(s.body, snap.docs.map(unpack));
      next([...found.values()].flat().sort((a, b) => b.createdAt.localeCompare(a.createdAt)));
    }, error),
  );
  return () => stops.forEach((s) => s());
}
export async function createConsultation(v: { body: string; audience: string; title: string; description: string; questions: ConsultationQuestion[]; deadline: string }) {
  const me = uid();
  const ref = doc(collection(db!, "consultations"));
  await setDoc(ref, {
    owner: me, body: v.body, audience: v.audience, title: v.title.trim(), description: v.description.trim(),
    questions: v.questions.map((q) => ({ id: q.id, kind: q.kind, label: q.label.trim(), options: q.kind === "choice" ? q.options.map((o) => o.trim()) : [] })),
    deadline: Timestamp.fromDate(new Date(v.deadline)), status: "open", resultsVisible: false, createdAt: serverTimestamp(), updatedAt: serverTimestamp(),
  });
  return ref.id;
}
export async function updateConsultation(id: string, fields: Partial<{ status: "open" | "closed"; resultsVisible: boolean }>) {
  uid();
  await updateDoc(doc(db!, "consultations", id), { ...fields, updatedAt: serverTimestamp() });
}
export async function removeConsultation(id: string) {
  uid();
  await deleteDoc(doc(db!, "consultations", id));
}
export function subscribeOwnAnswer(id: string, next: (a: ConsultationAnswer | null) => void, error: (e: any) => void): Stop {
  if (!db || !auth?.currentUser) return none;
  return onSnapshot(doc(db, "consultations", id, "answers", auth.currentUser.uid), (s) => next(s.exists() ? unpack(s) : null), error);
}
export function subscribeAnswers(id: string, next: (a: ConsultationAnswer[]) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(query(collection(db, "consultations", id, "answers"), limit(500)), (s) => next(s.docs.map(unpack)), error);
}
export async function answerConsultation(id: string, name: string, answers: Record<string, string>) {
  const me = uid();
  const clean = Object.fromEntries(Object.entries(answers).map(([k, v]) => [k, String(v).trim().slice(0, 2000)]).filter(([, v]) => v));
  if (!Object.keys(clean).length) throw Error("Answer at least one question.");
  await setDoc(doc(db!, "consultations", id, "answers", me), { name, answers: clean, updatedAt: serverTimestamp() });
}

/* ---------- Secretariat dashboard ---------- */
/** All profiles, private gender answers and logo requests (UNESCO Secretariat only). */
export async function loadDashboard() {
  if (!db) return { profiles: [], privateProfiles: [], logoRequests: [], events: [] };
  const read = async (name: string, max: number) => (await getDocs(query(collection(db!, name), limit(max)))).docs.map(unpack);
  const since = Timestamp.fromDate(new Date(Date.now() - 400 * 86400000));
  const [profiles, privateProfiles, logoRequests, events] = await Promise.all([
    read("profiles", 2000),
    read("privateProfiles", 2000).catch(() => []),
    read("logoRequests", 1000).catch(() => []),
    getDocs(query(collection(db!, "events"), where("startAt", ">=", since), limit(1000))).then((s) =>
      s.docs.map((d) => {
        const v = d.data();
        return { id: d.id, ...v, startAt: v.startAt.toDate().toISOString(), endAt: v.endAt.toDate().toISOString() };
      }),
    ),
  ]);
  return { profiles, privateProfiles, logoRequests, events };
}

/* ---------- Published membership totals ---------- */
export type MemberStats = { total: number; gender: Record<string, number>; careerStage: Record<string, number>; updatedAt: string };
export function subscribeMemberStats(next: (s: MemberStats | null) => void, error: (e: any) => void): Stop {
  if (!db) return none;
  return onSnapshot(doc(db, "communityStats", "members"), (s) => next(s.exists() ? (unpack(s) as MemberStats) : null), error);
}
const countBy = (values: string[]) => values.reduce((m: Record<string, number>, v) => ((m[v || "Not stated"] = (m[v || "Not stated"] || 0) + 1), m), {});
/**
 * UNESCO Secretariat only: publishes membership totals (gender and professional experience, never per person)
 * so that every member can see the gender representation of the community.
 */
export async function publishMemberStats(profiles?: any[], privateProfiles?: any[]) {
  if (!db) return;
  const all = profiles || (await getDocs(query(collection(db, "profiles"), limit(2000)))).docs.map(unpack);
  const priv = privateProfiles || (await getDocs(query(collection(db, "privateProfiles"), limit(2000)))).docs.map(unpack);
  const genderById = new Map(priv.map((p: any) => [p.id, p.gender || ""]));
  const next = { total: all.length, gender: countBy(all.map((p: any) => String(genderById.get(p.id) || ""))), careerStage: countBy(all.map((p: any) => String(p.careerStage || ""))) };
  const ref = doc(db, "communityStats", "members");
  const current = await getDoc(ref).catch(() => null);
  const same = current?.exists() && JSON.stringify({ t: current.data().total, g: current.data().gender, c: current.data().careerStage }) === JSON.stringify({ t: next.total, g: next.gender, c: next.careerStage });
  if (!same) await setDoc(ref, { ...next, updatedAt: serverTimestamp() });
}
