// Task boards of the leadership and Core Groups (pure helpers, no Firebase).
export type TaskStatus = "todo" | "doing" | "done";
export type Task = {
  id: string; body: string; title: string; notes: string; status: TaskStatus; priority: "normal" | "high";
  assignees: string[]; seenBy: string[]; due: string; createdBy: string; createdAt: string; updatedBy: string; updatedAt: string;
};
export const taskColumns: { id: TaskStatus; label: string; empty: string }[] = [
  { id: "todo", label: "To do", empty: "Nothing waiting. Add a task above." },
  { id: "doing", label: "In progress", empty: "Drag a task here, or select “Start” on a card." },
  { id: "done", label: "Done", empty: "Completed tasks appear here." },
];
export const MAX_ASSIGNEES = 10;
export const SOON_DAYS = 2;

/** Today's date (YYYY-MM-DD) in the member's own time zone. */
export function localToday(now = Date.now(), zone?: string) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: zone, year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(now));
}
const dayNumber = (ymd: string) => Math.round(Date.parse(ymd + "T00:00:00Z") / 86400000);

/** How close a deadline is: overdue (before today), soon (today and the next two days), later, or none. */
export function dueState(t: Pick<Task, "due" | "status">, today: string): "overdue" | "soon" | "later" | "none" {
  if (!t.due || t.status === "done") return "none";
  const d = dayNumber(t.due) - dayNumber(today);
  return d < 0 ? "overdue" : d <= SOON_DAYS ? "soon" : "later";
}
export function dueLabel(due: string, today: string) {
  if (!due) return "";
  const d = dayNumber(due) - dayNumber(today);
  if (d === 0) return "Due today";
  if (d === 1) return "Due tomorrow";
  if (d === -1) return "Due yesterday";
  if (d < 0) return `${-d} days overdue`;
  if (d < 7) return `Due in ${d} days`;
  return "Due " + new Date(due + "T12:00:00Z").toLocaleDateString("en-GB", { timeZone: "UTC", day: "numeric", month: "short" });
}
/** A member has a new assignment until they open the task. */
export const isNewFor = (t: Pick<Task, "assignees" | "seenBy" | "status">, uid: string) =>
  t.status !== "done" && t.assignees.includes(uid) && !t.seenBy.includes(uid);

/** Order within a column: high priority first, then the nearest deadline, then the newest. Done: most recent first. */
export function sortTasks(list: Task[]) {
  return [...list].sort((a, b) => {
    if (a.status === "done" && b.status === "done") return b.updatedAt.localeCompare(a.updatedAt);
    if (a.priority !== b.priority) return a.priority === "high" ? -1 : 1;
    if (a.due !== b.due) return !a.due ? 1 : !b.due ? -1 : a.due.localeCompare(b.due);
    return b.createdAt.localeCompare(a.createdAt);
  });
}
/**
 * Who has already opened the task after saving a change of assignees: only people who were assigned before
 * and still are keep their "seen" mark, so a newly added (or re-added) person is notified.
 */
export function nextSeenBy(before: Pick<Task, "assignees" | "seenBy"> | null, assignees: string[], editor: string) {
  const kept = before ? before.seenBy.filter((u) => before.assignees.includes(u) && assignees.includes(u)) : [];
  return [...new Set([...kept, ...(assignees.includes(editor) ? [editor] : [])])].slice(0, MAX_ASSIGNEES);
}
