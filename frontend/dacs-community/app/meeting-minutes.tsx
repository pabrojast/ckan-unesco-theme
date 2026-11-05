import { useEffect, useState } from "react";
import { CalendarPlus, Check, ClipboardCheck, Download, Pencil, Plus, Trash2, UserRound } from "lucide-react";
import { toast } from "sonner";
import { canAttend, canEditAgenda, type MeetingAccess } from "@/lib/meetings";
import type { CalendarEvent } from "@/lib/calendar";
import { friendlyError } from "@/lib/store";
import { actionState, buildIcs, googleCalendarUrl, outlookCalendarUrl, sortActions, type ActionItem } from "@/lib/coordination";
import { removeAction, saveAction, saveMinutes, setActionStatus, subscribeMeetingActions, subscribeMinutes, type Minutes } from "@/lib/coordination-store";
import { appUrl } from "@/lib/base";

const dueLabel = (due: string) => (due ? new Date(due + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "No due date");
export function ActionStateChip({ action }: { action: Pick<ActionItem, "status" | "due"> }) {
  const s = actionState(action);
  return s === "overdue" ? <span className="pill amber">Overdue</span> : s === "soon" ? <span className="pill blue">Due soon</span> : s === "done" ? <span className="pill green">Done</span> : null;
}

/** Download an .ics file, or open Google Calendar or Outlook on the web with the event filled in. */
export function AddToCalendar({ event }: { event: CalendarEvent }) {
  const item = { id: event.id, title: event.title, description: event.description, location: event.location, startAt: event.startAt, endAt: event.endAt, url: appUrl() };
  function download() {
    const blob = new Blob([buildIcs([item])], { type: "text/calendar;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = (event.title.replace(/[^\p{L}\p{N} _-]+/gu, "").trim().slice(0, 60) || "event") + ".ics";
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  }
  return (
    <div className="add-to-calendar" role="group" aria-label="Add to your calendar">
      <span className="micro"><CalendarPlus size={14} /> Add to your calendar</span>
      <button type="button" className="btn small" onClick={download}><Download size={14} /> Outlook / Apple (.ics)</button>
      <a className="btn small" href={googleCalendarUrl(item)} target="_blank" rel="noopener noreferrer">Google</a>
      <a className="btn small" href={outlookCalendarUrl(item)} target="_blank" rel="noopener noreferrer">Outlook on the web</a>
    </div>
  );
}

/** Minutes and action items of a meeting, for its audience. Agenda editors write them. */
export function MeetingMinutes({ event, access, people }: { event: CalendarEvent; access: MeetingAccess; people: any[] }) {
  const isPublic = !event.body || !event.meetingType || event.meetingType === "public";
  const body = isPublic ? "" : event.body || "", type = isPublic ? "public" : event.meetingType || "public";
  // Public events: everyone signed in reads; the organiser and the UNESCO Secretariat write. Meetings follow their audience.
  const attend = isPublic ? !!access.uid : canAttend(access, body, type);
  const edit = attend && (isPublic ? access.admin || event.owner === access.uid : canEditAgenda(access, body, type));
  const [minutes, setMinutes] = useState<Minutes | null>(null);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [draft, setDraft] = useState<{ summary: string; decisions: string } | null>(null);
  const [action, setAction] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    setMinutes(null);
    setActions([]);
    setDraft(null);
    setAction(null);
    if (!attend) return;
    const fail = (e: any) => setError(friendlyError(e));
    const a = subscribeMinutes(event.id, setMinutes, fail);
    const b = subscribeMeetingActions({ id: event.id, body, meetingType: type }, setActions, fail);
    return () => { a(); b(); };
  }, [event.id, attend]);
  if (!attend) return null;
  const past = Date.parse(event.startAt) <= Date.now();
  async function run(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError("");
    try {
      await fn();
      toast.success(done);
      return true;
    } catch (e) {
      setError(friendlyError(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  const me = access.uid;
  return (
    <section className="meeting-minutes">
      <div className="minutes-head">
        <h3><ClipboardCheck size={17} /> Minutes and actions</h3>
        {edit && !draft && (
          <button className="btn small" onClick={() => setDraft({ summary: minutes?.summary || "", decisions: minutes?.decisions || "" })}>
            <Pencil size={14} /> {minutes ? "Edit minutes" : "Write the minutes"}
          </button>
        )}
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {draft ? (
        <form className="stack" onSubmit={async (e) => { e.preventDefault(); if (await run(() => saveMinutes(event.id, draft.summary, draft.decisions), "Minutes saved.")) setDraft(null); }}>
          <label className="field-label">Summary of the discussion<textarea rows={6} maxLength={20000} value={draft.summary} onChange={(e) => setDraft({ ...draft, summary: e.target.value })} /></label>
          <label className="field-label">Decisions and conclusions<textarea rows={4} maxLength={10000} value={draft.decisions} onChange={(e) => setDraft({ ...draft, decisions: e.target.value })} /></label>
          <div className="toolbar"><button className="btn primary" disabled={busy}>Save minutes</button><button type="button" className="btn" onClick={() => setDraft(null)}>Cancel</button></div>
        </form>
      ) : minutes && (minutes.summary || minutes.decisions) ? (
        <div className="minutes-text">
          {minutes.summary && <><h4>Summary</h4><p>{minutes.summary}</p></>}
          {minutes.decisions && <><h4>Decisions</h4><p>{minutes.decisions}</p></>}
          <p className="micro">Updated {new Date(minutes.updatedAt).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short" })}</p>
        </div>
      ) : (
        <p className="micro">{past ? (edit ? "This meeting has taken place. Record its minutes and action items." : "No minutes have been recorded for this meeting yet.") : "Minutes and action items can be recorded during or after the meeting."}</p>
      )}
      <div className="actions-head">
        <h4>Action items {actions.length > 0 && <span className="pill">{actions.filter((a) => a.status === "open").length} open</span>}</h4>
        {edit && !action && <button className="btn small" onClick={() => setAction({ title: "", owner: "", due: "" })}><Plus size={14} /> Add an action</button>}
      </div>
      {action && (
        <form className="action-form" onSubmit={async (e) => {
          e.preventDefault();
          const person = people.find((p) => p.id === action.owner);
          if (await run(() => saveAction({ ...action, eventId: event.id, body, meetingType: type, owner_name: person?.name || "" }), action.id ? "Action updated." : "Action added.")) setAction(null);
        }}>
          <label className="field-label wide">Action<input required maxLength={300} value={action.title} onChange={(e) => setAction({ ...action, title: e.target.value })} placeholder="What needs to be done" /></label>
          <label className="field-label">Responsible<select value={action.owner} onChange={(e) => setAction({ ...action, owner: e.target.value })}><option value="">Not assigned</option>{[...people].sort((a, b) => a.name.localeCompare(b.name)).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <label className="field-label">Due date<input type="date" value={action.due} onChange={(e) => setAction({ ...action, due: e.target.value })} /></label>
          <div className="toolbar wide"><button className="btn primary" disabled={busy}>{action.id ? "Save action" : "Add action"}</button><button type="button" className="btn" onClick={() => setAction(null)}>Cancel</button></div>
        </form>
      )}
      {!actions.length && !action && <p className="micro">No action items yet.</p>}
      <ul className="action-list">
        {sortActions(actions).map((a) => {
          const mine = a.owner === me;
          return (
            <li key={a.id} className={"action-row " + actionState(a)}>
              <button type="button" className={"action-check" + (a.status === "done" ? " done" : "")} disabled={busy || !(edit || mine)} aria-pressed={a.status === "done"}
                aria-label={(a.status === "done" ? "Reopen: " : "Mark as done: ") + a.title}
                onClick={() => run(() => setActionStatus(a.id, a.status === "done" ? "open" : "done"), a.status === "done" ? "Action reopened." : "Action marked as done.")}>
                {a.status === "done" && <Check size={14} />}
              </button>
              <div className="action-text">
                <strong>{a.title}</strong>
                <span className="micro"><UserRound size={12} /> {a.owner_name || "Not assigned"}{mine ? " (you)" : ""} · {dueLabel(a.due)}</span>
              </div>
              <ActionStateChip action={a} />
              {edit && (
                <span className="action-tools">
                  <button type="button" className="msg-action" onClick={() => setAction({ id: a.id, title: a.title, owner: a.owner, due: a.due, status: a.status })}><Pencil size={13} /> Edit</button>
                  <button type="button" className="msg-action remove" onClick={() => window.confirm("Delete this action?") && run(() => removeAction(a.id), "Action deleted.")}><Trash2 size={13} /> Delete</button>
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
