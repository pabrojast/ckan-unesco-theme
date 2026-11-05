import { useEffect, useMemo, useRef, useState } from "react";
import { CreatedBy } from "./people-context";
import { ArrowRight, Bell, Check, CheckCircle2, Circle, Clock, Flag, Plus, RotateCcw, Search, SquareKanban, Trash2, UserPlus, X } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { accentStyle, eventAccent } from "@/lib/event-style";
import { bodyLabel, bodyLevel, meetingBodies, type MeetingAccess } from "@/lib/meetings";
import { friendlyError } from "@/lib/store";
import { snowBurst } from "./fx";
import { createTask, markTaskSeen, moveTask, removeTask, saveTask, subscribeBodyTasks, type TaskDraft } from "@/lib/task-store";
import { dueLabel, dueState, isNewFor, localToday, MAX_ASSIGNEES, sortTasks, taskColumns, type Task, type TaskStatus } from "@/lib/tasks";
import { MemberAvatar } from "./member-avatar";

const fullName = (id: string) => ({ wg1: "WG1 · Monitoring", wg2: "WG2 · Projections", wg3: "WG3 · Risk management", wg4: "WG4 · Adaptation", wg5: "WG5 · Amplify" } as Record<string, string>)[id] || bodyLabel(id);

/** Name of a board: the Working Group tag, or the full name of the other bodies. */
export const boardLabel = (body: string) => (/^wg[1-5]$/.test(body) ? eventAccent({ body }).tag : bodyLabel(body));

/** Leadership and Core Group of a body: the people suggested first as assignees. */
export function bodyTeam(body: string, people: any[], governance: any[]) {
  const g = governance.find((x: any) => x.id === body) || {};
  const seats = new Set<string>([g.lead, ...(g.secretariat || []), ...(g.associateLeads || []), ...(g.core || [])].filter(Boolean));
  const n = /^wg([1-5])$/.exec(body)?.[1];
  return people.filter((p) => seats.has(p.id)
    || ["lead", "associate", "secretariat", "core"].some((pos) => (p.assignedBadgeIds || []).includes(`${body}-${pos}`))
    || (n && ["lead", "associate", "secretariat", "core"].includes(p.role) && (p.directWgs || []).includes(Number(n))));
}
/** Bodies whose task board the member can open (leadership and Core Group, and the UNESCO Secretariat). */
export const boardBodies = (access: MeetingAccess) => meetingBodies.filter((b) => bodyLevel(access, b.id) >= 2).map((b) => b.id);

function Avatars({ ids, people, max = 3 }: { ids: string[]; people: any[]; max?: number }) {
  const list = ids.map((id) => people.find((p) => p.id === id) || { id, name: "Former member" });
  return (
    <span className="task-avatars" title={list.map((p) => p.name).join(", ")}>
      {list.slice(0, max).map((p) => <MemberAvatar key={p.id} name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />)}
      {list.length > max && <span className="task-avatar-more">+{list.length - max}</span>}
    </span>
  );
}

function TaskCard({ t, people, me, today, canEdit, onOpen, onMove, dragging, freezing = false }: { t: Task; people: any[]; me: string; today: string; canEdit: boolean; onOpen: () => void; onMove: (s: TaskStatus) => void; dragging: (id: string | null) => void; freezing?: boolean }) {
  const state = dueState(t, today), mine = t.assignees.includes(me), fresh = isNewFor(t, me);
  const canMove = canEdit || mine;
  return (
    <article data-task={t.id} className={`task-card ${t.status} due-${state}${fresh ? " fresh" : ""}${freezing ? " freezing" : ""}`} draggable={canMove}
      onDragStart={(e) => { e.dataTransfer.setData("text/plain", t.id); e.dataTransfer.effectAllowed = "move"; dragging(t.id); }} onDragEnd={() => dragging(null)}>
      <button type="button" className="task-check" disabled={!canMove} aria-label={t.status === "done" ? "Reopen the task" : "Mark the task as done"}
        onClick={() => onMove(t.status === "done" ? "todo" : "done")}>{t.status === "done" ? <CheckCircle2 size={19} /> : <Circle size={19} />}</button>
      <button type="button" className="task-main" onClick={onOpen}>
        <span className="task-title">{t.priority === "high" && <Flag size={13} className="task-flag" aria-label="High priority" />}{t.title}</span>
        {t.notes && <span className="task-notes">{t.notes}</span>}
        <CreatedBy uid={t.createdBy} verb="Added by" compact />
        <span className="task-meta">
          {t.due && <span className={"task-due " + state}><Clock size={12} />{t.status === "done" ? new Date(t.due + "T12:00:00Z").toLocaleDateString("en-GB", { timeZone: "UTC", day: "numeric", month: "short" }) : dueLabel(t.due, today)}</span>}
          {fresh && <span className="task-new">New for you</span>}
          <span className="spacer" />
          {t.assignees.length > 0 ? <Avatars ids={t.assignees} people={people} /> : <span className="task-unassigned">Unassigned</span>}
        </span>
      </button>
      {canMove && t.status !== "done" && (
        <button type="button" className="task-step" onClick={() => onMove(t.status === "todo" ? "doing" : "done")}>
          {t.status === "todo" ? <>Start <ArrowRight size={13} /></> : <>Done <Check size={13} /></>}
        </button>
      )}
      {canMove && t.status === "done" && <button type="button" className="task-step" onClick={() => onMove("doing")}><RotateCcw size={12} /> Reopen</button>}
    </article>
  );
}

function AssigneePicker({ value, onChange, people, team }: { value: string[]; onChange: (v: string[]) => void; people: any[]; team: any[] }) {
  const [open, setOpen] = useState(false), [q, setQ] = useState("");
  const teamIds = new Set(team.map((p) => p.id));
  const matches = people.filter((p) => !value.includes(p.id) && (!q.trim() ? teamIds.has(p.id) : String(p.name).toLowerCase().includes(q.trim().toLowerCase())))
    .sort((a, b) => Number(teamIds.has(b.id)) - Number(teamIds.has(a.id)) || String(a.name).localeCompare(b.name)).slice(0, 8);
  return (
    <div className="assignee-picker">
      <div className="assignee-chips">
        {value.map((id) => { const p = people.find((x) => x.id === id) || { id, name: "Former member" }; return (
          <span className="assignee-chip" key={id}><MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />{p.name}
            <button type="button" aria-label={"Remove " + p.name} onClick={() => onChange(value.filter((x) => x !== id))}><X size={13} /></button></span>); })}
        {value.length < MAX_ASSIGNEES && <button type="button" className={"assignee-add" + (open ? " on" : "")} onClick={() => setOpen(!open)}><UserPlus size={14} /> {value.length ? "Add" : "Assign people"}</button>}
      </div>
      {open && value.length < MAX_ASSIGNEES && (
        <div className="assignee-pop">
          <label className="assignee-search"><Search size={15} /><input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search any member by name" aria-label="Search a member to assign" /></label>
          <div className="assignee-options">
            {!q.trim() && <span className="assignee-group">{matches.length ? "Leadership and Core Group" : "Type a name to find any member"}</span>}
            {matches.map((p) => (
              <button type="button" key={p.id} className="assignee-option" onClick={() => { onChange([...value, p.id]); setQ(""); }}>
                <MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} /><span><strong>{p.name}</strong><small>{p.headline || "Member"}</small></span><Plus size={15} />
              </button>
            ))}
            {q.trim() && !matches.length && <span className="micro">No member matches “{q.trim()}”.</span>}
          </div>
        </div>
      )}
    </div>
  );
}

const emptyDraft = (status: TaskStatus = "todo"): TaskDraft => ({ title: "", notes: "", status, priority: "normal", assignees: [], due: "" });
const plusDays = (ymd: string, n: number) => { const d = new Date(ymd + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };

function TaskDialog({ open, task, body, people, team, me, canEdit, canDelete, onClose }: { open: boolean; task: Task | null; body: string; people: any[]; team: any[]; me: string; canEdit: boolean; canDelete: boolean; onClose: () => void }) {
  const [d, setD] = useState<TaskDraft>(emptyDraft()), [busy, setBusy] = useState(false), [error, setError] = useState("");
  useEffect(() => {
    if (!open) return;
    setError("");
    setD(task ? { title: task.title, notes: task.notes, status: task.status, priority: task.priority, assignees: task.assignees, due: task.due } : emptyDraft());
    if (task) void markTaskSeen(task).catch(() => {});
  }, [open, task?.id]);
  const mineOnly = !!task && !canEdit, today = localToday();
  async function save() {
    setBusy(true); setError("");
    try {
      if (mineOnly) { if (d.status !== task!.status) await moveTask(task!, d.status); }
      else if (task) await saveTask(task, d); else await createTask(body, d);
      toast.success(task ? "Task saved." : d.assignees.filter((x) => x !== me).length ? "Task created. The people assigned are notified." : "Task created.");
      onClose();
    } catch (e) { setError(friendlyError(e)); } finally { setBusy(false); }
  }
  const creator = task ? people.find((p) => p.id === task.createdBy)?.name : "";
  const state = dueState({ due: d.due, status: d.status }, today);
  return (
    <Dialog open={open} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="detail-content task-dialog" style={accentStyle({ body })}>
        <div className="task-dialog-head">
          <span className="ev-tag">{boardLabel(body)}</span>
          <span className="micro">{task ? `Task board · created by ${creator || "a member"}` : "New task"}</span>
        </div>
        <DialogTitle className="sr-only">{task ? task.title : "New task"}</DialogTitle>
        <DialogDescription className="sr-only">{fullName(body)} task board</DialogDescription>
        {mineOnly ? (
          <div className="task-read">
            <h2>{task!.priority === "high" && <Flag size={16} className="task-flag" />}{task!.title}</h2>
            {task!.notes && <p className="task-notes-full">{task!.notes}</p>}
          </div>
        ) : (
          <div className="task-compose">
            <input className="task-title-input" autoFocus maxLength={200} value={d.title} onChange={(e) => setD({ ...d, title: e.target.value })} placeholder="What needs to be done?" aria-label="Task" />
            <textarea className="task-notes-input" rows={3} maxLength={3000} value={d.notes} onChange={(e) => setD({ ...d, notes: e.target.value })} placeholder="Add details: context, links, expected result (optional)" aria-label="Details" />
          </div>
        )}
        <div className="task-props">
          <div className="task-prop">
            <span className="task-prop-label">Status</span>
            <div className="segmented status-seg" role="radiogroup" aria-label="Status">
              {taskColumns.map((c) => <button type="button" role="radio" key={c.id} aria-checked={d.status === c.id} className={d.status === c.id ? "on" : ""} onClick={() => setD({ ...d, status: c.id })}><i className={"task-dot " + c.id} />{c.label}</button>)}
            </div>
          </div>
          {mineOnly ? (
            <>
              <div className="task-prop"><span className="task-prop-label">Deadline</span><span className={"task-due " + dueState(task!, today)}><Clock size={12} />{task!.due ? dueLabel(task!.due, today) : "No deadline"}</span></div>
              <div className="task-prop"><span className="task-prop-label">Assigned to</span><Avatars ids={task!.assignees} people={people} max={6} /><span className="micro">{task!.assignees.map((id) => people.find((p) => p.id === id)?.name || "a former member").join(", ")}</span></div>
            </>
          ) : (
            <>
              <div className="task-prop">
                <span className="task-prop-label">Priority</span>
                <div className="segmented" role="radiogroup" aria-label="Priority">
                  <button type="button" role="radio" aria-checked={d.priority === "normal"} className={d.priority === "normal" ? "on" : ""} onClick={() => setD({ ...d, priority: "normal" })}>Normal</button>
                  <button type="button" role="radio" aria-checked={d.priority === "high"} className={d.priority === "high" ? "on high" : ""} onClick={() => setD({ ...d, priority: "high" })}><Flag size={13} /> High</button>
                </div>
              </div>
              <div className="task-prop">
                <span className="task-prop-label">Deadline</span>
                <div className="task-deadline">
                  <input type="date" value={d.due} onChange={(e) => setD({ ...d, due: e.target.value })} aria-label="Deadline" />
                  <div className="task-quick-dates">
                    {[["Today", 0], ["Tomorrow", 1], ["In a week", 7], ["In two weeks", 14]].map(([l, n]) => <button type="button" key={l as string} className={d.due === plusDays(today, n as number) ? "on" : ""} onClick={() => setD({ ...d, due: plusDays(today, n as number) })}>{l}</button>)}
                    {d.due && <button type="button" onClick={() => setD({ ...d, due: "" })}>No deadline</button>}
                  </div>
                  {d.due && <span className={"task-due " + state}><Clock size={12} />{dueLabel(d.due, today)}</span>}
                </div>
              </div>
              <div className="task-prop top">
                <span className="task-prop-label">Assigned to</span>
                <AssigneePicker value={d.assignees} onChange={(assignees) => setD({ ...d, assignees })} people={people} team={team} />
              </div>
            </>
          )}
        </div>
        {!mineOnly && d.assignees.some((x) => x !== me) && <p className="micro task-notice"><Bell size={13} /> The people assigned receive a notification, and a reminder when the deadline is close.</p>}
        {error && <p className="error-banner" role="alert">{error}</p>}
        <div className="toolbar task-actions">
          {task && canDelete && <button type="button" className="text-button danger" disabled={busy} onClick={async () => { if (!window.confirm("Delete this task?")) return; try { await removeTask(task); toast.success("Task deleted."); onClose(); } catch (e) { setError(friendlyError(e)); } }}><Trash2 size={14} /> Delete</button>}
          <span className="spacer" />
          <button type="button" className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button type="button" className="btn primary" disabled={busy || (!mineOnly && !d.title.trim())} onClick={save}>{busy ? "Saving…" : task ? "Save" : "Create the task"}</button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/** The task board of one body: three columns, quick add, drag and drop, and assignment with deadlines. */
export function TaskBoard({ body, access, people, governance, compact = false }: { body: string; access: MeetingAccess; people: any[]; governance: any[]; compact?: boolean }) {
  const [tasks, setTasks] = useState<Task[] | null>(null), [error, setError] = useState("");
  const [open, setOpen] = useState<{ task: Task | null } | null>(null), [filter, setFilter] = useState<"all" | "mine" | "week">("all");
  const [quick, setQuick] = useState(""), [drag, setDrag] = useState<string | null>(null), [over, setOver] = useState<TaskStatus | null>(null), [showDone, setShowDone] = useState(false);
  const me = access.uid, level = bodyLevel(access, body), canEdit = level >= 2, canDeleteAll = level >= 3;
  const today = localToday();
  useEffect(() => { setTasks(null); return subscribeBodyTasks(body, setTasks, (e) => setError(friendlyError(e))); }, [body]);
  const team = useMemo(() => bodyTeam(body, people, governance), [body, people, governance]);
  const live = tasks?.find((t) => t.id === open?.task?.id) || open?.task || null;
  const weekEnd = useMemo(() => { const d = new Date(today + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + 7); return d.toISOString().slice(0, 10); }, [today]);
  const shown = (tasks || []).filter((t) => filter === "all" || (filter === "mine" ? t.assignees.includes(me) : t.status !== "done" && !!t.due && t.due <= weekEnd));
  const quickRef = useRef<HTMLInputElement>(null);
  async function addQuick() {
    const title = quick.trim();
    if (!title) return;
    try { await createTask(body, { ...emptyDraft(), title }); setQuick(""); quickRef.current?.focus(); } catch (e) { toast.error(friendlyError(e)); }
  }
  // A completed task frosts over; clearing the last open task of the board sends an aurora across its header.
  const [frozen, setFrozen] = useState(""), [aurora, setAurora] = useState(false);
  async function move(t: Task, status: TaskStatus) {
    if (t.status === status) return;
    const lastOpen = status === "done" && (tasks || []).filter((x) => x.status !== "done").length === 1;
    try {
      await moveTask(t, status);
      if (status === "done") {
        toast.success(lastOpen ? "Task completed. The board is clear." : "Task completed.");
        setFrozen(t.id); window.setTimeout(() => setFrozen((f) => (f === t.id ? "" : f)), 1600);
        window.setTimeout(() => {
          const r = document.querySelector(`[data-task="${t.id}"]`)?.getBoundingClientRect();
          if (r) snowBurst(["#8ed2ee", "#dff3fb"], { origin: { x: r.left + r.width / 2, y: r.top + r.height / 2 }, count: 18, duration: 1500 });
        }, 120);
        if (lastOpen) { setAurora(true); window.setTimeout(() => setAurora(false), 3600); }
      }
    } catch (e) { toast.error(friendlyError(e)); }
  }
  const counts = { open: (tasks || []).filter((t) => t.status !== "done").length, overdue: (tasks || []).filter((t) => dueState(t, today) === "overdue").length };
  return (
    <section className={"task-board" + (compact ? " compact" : "")} style={accentStyle({ body })} aria-label={`Task board of ${fullName(body)}`}>
      <header className={"task-board-head" + (aurora ? " aurora" : "")}>
        <div>
          <h3><SquareKanban size={18} /> Task board <span className="ev-tag">{boardLabel(body)}</span></h3>
          <p className="micro">Visible to the leadership and Core Group of {fullName(body)}. People assigned to a task see it under Task boards and receive a notification.</p>
        </div>
        <div className="task-board-tools">
          <span className="pill">{counts.open} open</span>
          {counts.overdue > 0 && <span className="pill amber">{counts.overdue} overdue</span>}
          <div className="segmented" role="group" aria-label="Filter the tasks">
            {([["all", "All"], ["mine", "Assigned to me"], ["week", "Due this week"]] as const).map(([id, label]) =>
              <button type="button" key={id} className={filter === id ? "on" : ""} aria-pressed={filter === id} onClick={() => setFilter(id)}>{label}</button>)}
          </div>
          {canEdit && <button type="button" className="btn primary small" onClick={() => setOpen({ task: null })}><Plus size={15} /> New task</button>}
        </div>
      </header>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!tasks && !error && <p className="micro">Loading the tasks…</p>}
      {tasks && (
        <div className="task-columns">
          {taskColumns.map((c) => {
            const list = sortTasks(shown.filter((t) => t.status === c.id));
            const visibleList = c.id === "done" && !showDone ? list.slice(0, 5) : list;
            return (
              <div key={c.id} className={`task-column col-${c.id}` + (over === c.id && drag ? " drop" : "")}
                onDragOver={(e) => { if (drag) { e.preventDefault(); setOver(c.id); } }} onDragLeave={() => setOver(null)}
                onDrop={(e) => { e.preventDefault(); setOver(null); const t = tasks.find((x) => x.id === e.dataTransfer.getData("text/plain")); if (t) void move(t, c.id); }}>
                <div className="task-column-head"><span className={"task-dot " + c.id} />{c.label}<span className="task-count">{list.length}</span></div>
                {c.id === "todo" && canEdit && (
                  <form className="task-quick" onSubmit={(e) => { e.preventDefault(); void addQuick(); }}>
                    <Plus size={15} /><input ref={quickRef} value={quick} maxLength={200} onChange={(e) => setQuick(e.target.value)} placeholder="Add a task and press Enter" aria-label="Add a task" />
                  </form>
                )}
                <div className="task-list">
                  {visibleList.map((t) => <TaskCard key={t.id} t={t} people={people} me={me} today={today} canEdit={canEdit} onOpen={() => setOpen({ task: t })} onMove={(s) => void move(t, s)} dragging={setDrag} freezing={frozen === t.id} />)}
                  {!list.length && <p className="task-empty">{filter === "all" ? c.empty : "No task matches this filter."}</p>}
                  {c.id === "done" && list.length > 5 && <button type="button" className="text-button" onClick={() => setShowDone(!showDone)}>{showDone ? "Show fewer" : `Show all ${list.length}`}</button>}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <TaskDialog open={!!open} task={live} body={body} people={people} team={team} me={me} canEdit={canEdit}
        canDelete={canDeleteAll || (!!live && live.createdBy === me && canEdit)} onClose={() => setOpen(null)} />
    </section>
  );
}

/** Task boards page: the tasks assigned to the member across bodies, and the boards they can open. */
export function TaskBoards({ access, people, governance, myTasks, focus }: { access: MeetingAccess; people: any[]; governance: any[]; myTasks: Task[]; focus?: string }) {
  const bodies = boardBodies(access);
  const [tab, setTab] = useState<string>(focus || (myTasks.some((t) => t.status !== "done") || !bodies.length ? "mine" : bodies[0]));
  useEffect(() => { if (focus) setTab(focus); }, [focus]);
  const [open, setOpen] = useState<Task | null>(null);
  const today = localToday();
  const mine = sortTasks(myTasks.filter((t) => t.status !== "done"));
  const live = myTasks.find((t) => t.id === open?.id) || open;
  return (
    <section className="task-boards">
      <div className="task-tabs" role="tablist" aria-label="Task boards">
        <button role="tab" aria-selected={tab === "mine"} className={tab === "mine" ? "on" : ""} onClick={() => setTab("mine")}>Assigned to me{mine.length > 0 && <span className="nav-count">{mine.length}</span>}</button>
        {bodies.map((b) => <button role="tab" key={b} aria-selected={tab === b} className={tab === b ? "on" : ""} style={accentStyle({ body: b })} onClick={() => setTab(b)}><i className="task-tab-dot" />{boardLabel(b)}</button>)}
      </div>
      {tab === "mine" ? (
        <div className="glass panel my-tasks">
          {!mine.length && <div className="notif-empty"><span className="notif-empty-icon"><Check size={22} /></span><strong>No open task assigned to you</strong><p className="micro">When someone assigns you a task, it appears here and in your notifications.</p></div>}
          {mine.map((t) => {
            const state = dueState(t, today);
            return (
              <button type="button" key={t.id} className={`my-task due-${state}${isNewFor(t, access.uid) ? " fresh" : ""}`} style={accentStyle({ body: t.body })} onClick={() => setOpen(t)}>
                <span className="ev-tag">{boardLabel(t.body)}</span>
                <span className="my-task-text"><strong>{t.priority === "high" && <Flag size={13} className="task-flag" />}{t.title}</strong><small>{t.status === "doing" ? "In progress" : "To do"}{t.due ? " · " + dueLabel(t.due, today) : ""}</small></span>
                {isNewFor(t, access.uid) && <span className="task-new">New</span>}
                <ArrowRight size={16} />
              </button>
            );
          })}
        </div>
      ) : (
        <TaskBoard body={tab} access={access} people={people} governance={governance} />
      )}
      <TaskDialog open={!!open} task={live || null} body={live?.body || ""} people={people} team={live ? bodyTeam(live.body, people, governance) : []} me={access.uid}
        canEdit={!!live && bodyLevel(access, live.body) >= 2} canDelete={!!live && bodyLevel(access, live.body) >= 3} onClose={() => setOpen(null)} />
    </section>
  );
}
