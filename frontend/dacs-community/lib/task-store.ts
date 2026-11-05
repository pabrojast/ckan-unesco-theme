// Firestore access for task boards (tasks/{id}) and event sign-ups (events/{id}/attendance/{uid}).
import { collection, deleteDoc, doc, onSnapshot, query, serverTimestamp, setDoc, updateDoc, where, limit } from "firebase/firestore";
import { auth, db } from "./firebase";
import { MAX_ASSIGNEES, nextSeenBy, type Task, type TaskStatus } from "./tasks";

const iso = (v: any) => (v?.toDate ? v.toDate().toISOString() : typeof v === "string" ? v : "");
const unpack = (s: any): any => {
  const x = s.data({ serverTimestamps: "estimate" }) || {};
  const out: any = { id: s.id };
  for (const [k, v] of Object.entries(x)) out[k] = (v as any)?.toDate ? iso(v) : v;
  return out;
};
const asTask = (s: any): Task => {
  const t = unpack(s);
  return { notes: "", priority: "normal", assignees: [], seenBy: [], due: "", status: "todo", ...t };
};
type Stop = () => void;
const none: Stop = () => {};
const uid = () => auth?.currentUser?.uid || "";

export function subscribeBodyTasks(body: string, next: (t: Task[]) => void, error: (e: any) => void): Stop {
  if (!db || !body) return none;
  return onSnapshot(query(collection(db, "tasks"), where("body", "==", body), limit(400)), (s) => next(s.docs.map(asTask)), error);
}
export function subscribeMyTasks(me: string, next: (t: Task[]) => void, error: (e: any) => void): Stop {
  if (!db || !me) return none;
  return onSnapshot(query(collection(db, "tasks"), where("assignees", "array-contains", me), limit(300)), (s) => next(s.docs.map(asTask)), error);
}

export type TaskDraft = { title: string; notes: string; status: TaskStatus; priority: "normal" | "high"; assignees: string[]; due: string };
export async function createTask(body: string, d: TaskDraft) {
  const me = uid();
  if (!db || !me) throw Error("Sign in first.");
  const title = d.title.trim().slice(0, 200);
  if (!title) throw Error("Give the task a title.");
  const assignees = [...new Set(d.assignees)].slice(0, MAX_ASSIGNEES);
  await setDoc(doc(collection(db, "tasks")), {
    body, title, notes: d.notes.trim().slice(0, 3000), status: d.status, priority: d.priority, assignees,
    seenBy: nextSeenBy(null, assignees, me), due: d.due || "", createdBy: me, createdAt: serverTimestamp(), updatedBy: me, updatedAt: serverTimestamp(),
  });
}
export async function saveTask(before: Task, d: TaskDraft) {
  const me = uid();
  const title = d.title.trim().slice(0, 200);
  if (!title) throw Error("Give the task a title.");
  const assignees = [...new Set(d.assignees)].slice(0, MAX_ASSIGNEES);
  await updateDoc(doc(db!, "tasks", before.id), {
    title, notes: d.notes.trim().slice(0, 3000), status: d.status, priority: d.priority, assignees,
    seenBy: nextSeenBy(before, assignees, me), due: d.due || "", updatedBy: me, updatedAt: serverTimestamp(),
  });
}
/** Moves a task to another column. Assignees may do this on their own tasks. */
export async function moveTask(t: Task, status: TaskStatus) {
  await updateDoc(doc(db!, "tasks", t.id), { status, updatedBy: uid(), updatedAt: serverTimestamp() });
}
/** Records that an assignee has opened the task, which clears their "new task" notification. */
export async function markTaskSeen(t: Task) {
  const me = uid();
  if (!db || !me || !t.assignees.includes(me) || t.seenBy.includes(me)) return;
  await updateDoc(doc(db, "tasks", t.id), { seenBy: [...t.seenBy, me].slice(0, MAX_ASSIGNEES), updatedBy: me, updatedAt: serverTimestamp() });
}
export async function removeTask(t: Task) { await deleteDoc(doc(db!, "tasks", t.id)); }

/* ---------- Event sign-ups ---------- */
export type Attendance = { id: string; name: string; mode: "in-person" | "online"; at: string };
export function subscribeAttendance(eventId: string, next: (a: Attendance[]) => void, error: (e: any) => void): Stop {
  if (!db || !eventId) return none;
  return onSnapshot(query(collection(db, "events", eventId, "attendance"), limit(500)), (s) => next(s.docs.map(unpack) as Attendance[]), error);
}
export async function attend(eventId: string, name: string, mode: Attendance["mode"]) {
  const me = uid();
  if (!db || !me) throw Error("Sign in first.");
  await setDoc(doc(db, "events", eventId, "attendance", me), { name: name.slice(0, 120), mode, at: serverTimestamp() });
}
export async function cancelAttendance(eventId: string, member = uid()) {
  await deleteDoc(doc(db!, "events", eventId, "attendance", member));
}
