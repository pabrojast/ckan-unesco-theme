import { useEffect, useMemo, useState } from "react";
import { CreatedBy } from "./people-context";
import { BookMarked, CalendarDays, Download, Lock, Pencil, Plus, Search, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { bodyLabel, bodyLevel, canOrganise, type MeetingAccess } from "@/lib/meetings";
import { friendlyError } from "@/lib/store";
import { fold } from "@/lib/discussion";
import { removeDecision, saveDecision, subscribeDecisions, type Decision } from "@/lib/coordination-store";
import { downloadCsv } from "./workplan";

const registerBodies = ["smc", "esc"] as const;
const longDate = (d: string) => new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

/** Searchable register of SMC and ESC decisions, with links to the minutes of the meeting that took them. */
export function DecisionRegister({ access, only, events, onOpenMeeting, compact = false, onOpenRegister }: {
  access: MeetingAccess;
  only?: string;
  events: any[];
  onOpenMeeting: (eventId: string) => void;
  compact?: boolean;
  onOpenRegister?: () => void;
}) {
  const bodies = only ? [only] : [...registerBodies];
  const [items, setItems] = useState<Decision[] | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [draft, setDraft] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const key = bodies.map((b) => b + bodyLevel(access, b)).join();
  useEffect(() => {
    setItems(null);
    return subscribeDecisions(bodies.map((b) => ({ body: b, member: bodyLevel(access, b) >= 1 })), setItems, (e) => setError(friendlyError(e)));
  }, [key]);
  const editable = bodies.filter((b) => canOrganise(access, b));
  const shown = useMemo(() => {
    const q = fold(search.trim());
    return (items || []).filter((d) => (!filter || d.body === filter) && (!q || fold([d.reference, d.title, d.text, d.date].join(" ")).includes(q)));
  }, [items, search, filter]);
  const meetingOf = (id: string) => events.find((e) => e.id === id);
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await saveDecision(draft);
      toast.success(draft.id ? "Decision updated." : "Decision recorded.");
      setDraft(null);
    } catch (err) {
      toast.error(friendlyError(err));
    } finally {
      setBusy(false);
    }
  }
  async function remove(d: Decision) {
    if (!window.confirm(`Delete decision ${d.reference || d.title} from the register?`)) return;
    try {
      await removeDecision(d.id);
      toast.success("Decision deleted.");
    } catch (err) {
      toast.error(friendlyError(err));
    }
  }
  function exportCsv() {
    downloadCsv("dacs-decision-register.csv", [["Body", "Date", "Reference", "Title", "Decision", "Shared with"], ...shown.map((d) => [d.body.toUpperCase(), d.date, d.reference, d.title, d.text, d.visibility === "community" ? "All members" : "Members of the body"])]);
  }
  const list = compact ? shown.slice(0, 5) : shown;
  const bodyEvents = (b: string) => events.filter((e) => e.body === b).sort((x, y) => y.startAt.localeCompare(x.startAt)).slice(0, 40);
  return (
    <section className={"decision-register" + (compact ? " compact" : "")}>
      {compact ? (
        <div className="subsection-title wp-title"><span>Decision register</span>
          <div className="row">
            {editable.length > 0 && <button className="btn small" onClick={() => setDraft({ body: editable[0], date: new Date().toISOString().slice(0, 10), reference: "", title: "", text: "", eventId: "", visibility: "body" })}><Plus size={14} /> Record a decision</button>}
            {onOpenRegister && <button className="btn small" onClick={onOpenRegister}>Full register</button>}
          </div>
        </div>
      ) : (
        <div className="hub-toolbar">
          <label className="search-wrap decision-search"><Search size={16} /><input aria-label="Search decisions" placeholder="Search by reference, title or text" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
          <div className="row">
            {!only && <div className="choice-row" role="group" aria-label="Body">{["", ...registerBodies].map((b) => <button key={b} className={"btn small" + (filter === b ? " active" : "")} onClick={() => setFilter(b)}>{b ? b.toUpperCase() : "All"}</button>)}</div>}
            <button className="btn" onClick={exportCsv} disabled={!shown.length}><Download size={15} /> Export CSV</button>
            {editable.length > 0 && <button className="btn primary" onClick={() => setDraft({ body: editable[0], date: new Date().toISOString().slice(0, 10), reference: "", title: "", text: "", eventId: "", visibility: "body" })}><Plus size={16} /> Record a decision</button>}
          </div>
        </div>
      )}
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!items && !error && <p className="micro">Loading the register…</p>}
      {items && !shown.length && (
        <div className="discussion-empty"><BookMarked size={24} /><p>{search ? "No decision matches your search." : "No decision recorded yet."}</p></div>
      )}
      <ol className="decision-list">
        {list.map((d) => {
          const meeting = meetingOf(d.eventId);
          return (
            <li key={d.id} className="decision">
              <div className="decision-meta">
                <span className={"decision-body " + d.body}>{d.body.toUpperCase()}</span>
                <time dateTime={d.date}>{longDate(d.date)}</time>
                {d.reference && <span className="decision-ref">{d.reference}</span>}
                <span className="micro decision-vis">{d.visibility === "community" ? <><Users size={12} /> All members</> : <><Lock size={12} /> {bodyLabel(d.body)} members</>}</span>
              </div>
              <h3>{d.title}</h3>
              <CreatedBy uid={d.createdBy} verb="Recorded by" />
              {d.text && <p>{d.text}</p>}
              <div className="decision-foot">
                {d.eventId && <button className="text-button" onClick={() => onOpenMeeting(d.eventId)}><CalendarDays size={14} /> {meeting ? `Minutes · ${meeting.title}` : "Open the meeting and its minutes"}</button>}
                {canOrganise(access, d.body) && (
                  <span className="action-tools">
                    <button type="button" className="msg-action" onClick={() => setDraft({ ...d })}><Pencil size={13} /> Edit</button>
                    <button type="button" className="msg-action remove" onClick={() => remove(d)}><Trash2 size={13} /> Delete</button>
                  </span>
                )}
              </div>
            </li>
          );
        })}
      </ol>
      {compact && shown.length > 5 && onOpenRegister && <button className="text-button arrow" onClick={onOpenRegister}>See all {shown.length} decisions</button>}
      <Dialog open={!!draft} onOpenChange={(v) => !v && setDraft(null)}>
        <DialogContent className="detail-content">
          <DialogTitle>{draft?.id ? "Edit decision" : "Record a decision"}</DialogTitle>
          <DialogDescription>Entries are kept in the register of the body. Link the meeting to give access to its minutes.</DialogDescription>
          {draft && (
            <form className="stack" onSubmit={save}>
              <div className="calendar-form-grid">
                <label className="field-label">Body<select disabled={!!draft.id} value={draft.body} onChange={(e) => setDraft({ ...draft, body: e.target.value, eventId: "" })}>{editable.map((b) => <option key={b} value={b}>{bodyLabel(b)}</option>)}</select></label>
                <label className="field-label">Date<input type="date" required value={draft.date} onChange={(e) => setDraft({ ...draft, date: e.target.value })} /></label>
              </div>
              <label className="field-label">Reference<input maxLength={60} placeholder="For example SMC/2026/03" value={draft.reference} onChange={(e) => setDraft({ ...draft, reference: e.target.value })} /></label>
              <label className="field-label">Title<input required maxLength={200} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} /></label>
              <label className="field-label">Text of the decision<textarea rows={5} maxLength={5000} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })} /></label>
              <label className="field-label">Meeting<select value={draft.eventId} onChange={(e) => setDraft({ ...draft, eventId: e.target.value })}><option value="">Not linked to a meeting</option>{bodyEvents(draft.body).map((e) => <option key={e.id} value={e.id}>{longDate(e.startAt.slice(0, 10))} · {e.title}</option>)}</select></label>
              <fieldset className="choice-row"><legend className="field-legend">Shared with</legend>
                {([["body", "Members of the " + draft.body.toUpperCase()], ["community", "All members of the Hub"]] as const).map(([v, l]) => (
                  <button type="button" key={v} className={"btn small" + (draft.visibility === v ? " active" : "")} aria-pressed={draft.visibility === v} onClick={() => setDraft({ ...draft, visibility: v })}>{l}</button>
                ))}
              </fieldset>
              <div className="toolbar"><button className="btn primary" disabled={busy}>{busy ? "Saving…" : "Save"}</button><button type="button" className="btn" onClick={() => setDraft(null)}>Cancel</button></div>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
