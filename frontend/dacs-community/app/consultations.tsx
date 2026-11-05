import { useEffect, useMemo, useState } from "react";
import { CreatedBy } from "./people-context";
import { BarChart3, CheckSquare, ClipboardList, Download, Eye, EyeOff, Lock, Plus, Trash2, Vote, X } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { bodyLabel, bodyLevel, leadershipBodies, meetingBodies, typeLabel, canOrganise, type MeetingAccess } from "@/lib/meetings";
import { friendlyError } from "@/lib/store";
import { consultationError, questionOptions, tallyConsultation, type ConsultationQuestion } from "@/lib/coordination";
import { answerConsultation, createConsultation, removeConsultation, subscribeAnswers, subscribeConsultations, subscribeOwnAnswer, updateConsultation, type Consultation, type ConsultationAnswer } from "@/lib/coordination-store";
import { downloadCsv } from "./workplan";

const audiences = [
  { id: "leadership", label: "Leadership", text: "Leads, Associate Leads, Secretariat and chairpersons" },
  { id: "core", label: "Core Group", text: "Leadership and appointed Core Group members" },
  { id: "broad", label: "Broad Group", text: "Every affiliated member of the body" },
] as const;
const kinds = [
  { id: "yesno", label: "Yes / No / Abstain" },
  { id: "choice", label: "One choice from a list" },
  { id: "text", label: "Short written answer" },
] as const;
const closes = (iso: string) => new Date(iso).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const isOpen = (c: Consultation) => c.status === "open" && Date.parse(c.deadline) > Date.now();
const newId = () => "q" + Math.random().toString(36).slice(2, 8);

/** Consultations visible to the member, with their own answers. Used by the list and the bell. */
export function useConsultations(access: MeetingAccess) {
  const [items, setItems] = useState<Consultation[]>([]);
  const [answered, setAnswered] = useState<Record<string, boolean>>({});
  const [error, setError] = useState("");
  const key = JSON.stringify(meetingBodies.map((b) => [b.id, bodyLevel(access, b.id)]));
  useEffect(() => {
    setItems([]);
    if (!access.uid || !access.profile) return;
    const scopes = meetingBodies
      .map((b) => { const l = bodyLevel(access, b.id); return { body: b.id, types: l >= 3 ? ["leadership", "core", "broad"] : l === 2 ? ["core", "broad"] : l === 1 ? ["broad"] : [] }; })
      .filter((s) => s.types.length);
    return subscribeConsultations(scopes, setItems, (e) => setError(friendlyError(e)));
  }, [access.uid, !!access.profile, key]);
  const openIds = items.filter(isOpen).map((c) => c.id).join();
  useEffect(() => {
    const stops = items.filter(isOpen).slice(0, 25).map((c) => subscribeOwnAnswer(c.id, (a) => setAnswered((x) => ({ ...x, [c.id]: !!a })), () => {}));
    return () => stops.forEach((s) => s());
  }, [openIds]);
  const pending = items.filter((c) => isOpen(c) && answered[c.id] === false);
  return { items, answered, pending, error };
}
export type ConsultationTools = ReturnType<typeof useConsultations>;

export function Consultations({ access, tools, focusId }: { access: MeetingAccess; tools: ConsultationTools; focusId?: string }) {
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState(focusId || "");
  const [filter, setFilter] = useState("");
  useEffect(() => { if (focusId) setSelected(focusId); }, [focusId]);
  const leaders = leadershipBodies(access);
  const shown = tools.items.filter((c) => !filter || c.body === filter);
  const current = tools.items.find((c) => c.id === selected);
  return (
    <section className="consultations">
      <div className="hub-toolbar">
        <label className="meeting-filter">Show consultations for<select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="">All my affiliations</option>{meetingBodies.filter((b) => bodyLevel(access, b.id) > 0).map((b) => <option key={b.id} value={b.id}>{b.label}</option>)}</select></label>
        {leaders.length > 0 && <button className="btn primary" onClick={() => setCreating(true)}><Plus size={16} /> Start a consultation</button>}
      </div>
      {tools.error && <p className="error-banner" role="alert">{tools.error}</p>}
      <div className="cards cols2">
        {shown.map((c) => {
          const open = isOpen(c), done = tools.answered[c.id];
          return (
            <article className="glass op-card poll-card clickable-card" key={c.id}>
              <div className="card-tags"><span className="pill blue">{bodyLabel(c.body)}</span><span className="pill">{typeLabel(c.audience)}</span><span className={"pill " + (open ? "green" : "")}>{open ? "Open" : "Closed"}</span>{c.resultsVisible && <span className="pill">Results shared</span>}</div>
              <h3>{c.title}</h3>
              <CreatedBy uid={c.owner} at={c.createdAt} />
              <div className="op-meta"><span><ClipboardList size={14} />{c.questions.length} {c.questions.length === 1 ? "question" : "questions"}</span></div>
              <p className="micro">{open ? `Closes ${closes(c.deadline)}` : `Closed ${closes(c.deadline)}`}</p>
              <div className="card-footer">
                <span>{done ? <><CheckSquare size={13} />You have answered</> : open ? "Your answer is awaited" : ""}</span>
                <button className="btn small stretch" onClick={() => setSelected(c.id)}>{open && !done ? "Answer" : "Open"}</button>
              </div>
            </article>
          );
        })}
      </div>
      {!tools.items.length && !tools.error && (
        <div className="glass empty-state"><Vote size={30} /><h3>No consultations yet</h3><p>{leaders.length ? "Ask your group a yes/no question or run a short survey, for example to approve a document before a meeting." : "Consultations from your groups appear here."}</p>{leaders.length > 0 && <button className="btn primary" onClick={() => setCreating(true)}><Plus size={16} /> Start a consultation</button>}</div>
      )}
      {current && <ConsultationDetail c={current} access={access} answered={!!tools.answered[current.id]} onClose={() => setSelected("")} />}
      <Composer open={creating} onClose={() => setCreating(false)} access={access} onCreated={(id) => { setCreating(false); setSelected(id); }} />
    </section>
  );
}

function Composer({ open, onClose, access, onCreated }: { open: boolean; onClose: () => void; access: MeetingAccess; onCreated: (id: string) => void }) {
  const leaders = leadershipBodies(access);
  const blank = () => ({ body: leaders[0]?.id || "", audience: "broad", title: "", description: "", deadline: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10) + "T17:00", questions: [{ id: newId(), kind: "yesno", label: "", options: [] }] as ConsultationQuestion[] });
  const [v, setV] = useState(blank);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { if (open) { setV(blank()); setError(""); } }, [open]);
  const q = (i: number, patch: Partial<ConsultationQuestion>) => setV({ ...v, questions: v.questions.map((x, k) => (k === i ? { ...x, ...patch } : x)) });
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const err = consultationError(v);
    if (err) return setError(err);
    setBusy(true);
    try {
      const id = await createConsultation(v);
      toast.success("Consultation published. Members of the audience see it in the bell.");
      onCreated(id);
    } catch (x) {
      setError(friendlyError(x));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog open={open} onOpenChange={(o) => !o && !busy && onClose()}>
      <DialogContent className="detail-content composer-dialog">
        <DialogTitle>Start a consultation</DialogTitle>
        <DialogDescription>A yes/no vote or a short survey for one of your groups. Answers are recorded under each member's profile name.</DialogDescription>
        <form className="stack" onSubmit={submit}>
          <div className="calendar-form-grid">
            <label className="field-label">Organising body<select value={v.body} onChange={(e) => setV({ ...v, body: e.target.value })}>{leaders.map((b) => <option key={b.id} value={b.id}>{b.label}</option>)}</select></label>
            <label className="field-label">Closes on<input type="datetime-local" required value={v.deadline} onChange={(e) => setV({ ...v, deadline: e.target.value })} /></label>
          </div>
          <fieldset className="choice-cards">
            <legend className="field-legend">Who is consulted</legend>
            {audiences.map((a) => (
              <label key={a.id} className={"choice-card" + (v.audience === a.id ? " on" : "")}>
                <input type="radio" name="audience" checked={v.audience === a.id} onChange={() => setV({ ...v, audience: a.id })} />
                <span><strong>{a.label}</strong><small>{a.text}</small></span>
              </label>
            ))}
          </fieldset>
          <label className="field-label">Title<input required maxLength={160} value={v.title} placeholder="For example: Approval of the draft work plan" onChange={(e) => setV({ ...v, title: e.target.value })} /></label>
          <label className="field-label">Context (optional)<textarea rows={3} maxLength={3000} value={v.description} onChange={(e) => setV({ ...v, description: e.target.value })} placeholder="Background, document reference or link" /></label>
          <div className="question-list">
            {v.questions.map((x, i) => (
              <div className="question-edit" key={x.id}>
                <div className="question-edit-head">
                  <span className="wp-mg">Q{i + 1}</span>
                  <select aria-label={`Type of question ${i + 1}`} value={x.kind} onChange={(e) => q(i, { kind: e.target.value as any, options: e.target.value === "choice" ? (x.options.length ? x.options : ["", ""]) : [] })}>{kinds.map((k) => <option key={k.id} value={k.id}>{k.label}</option>)}</select>
                  {v.questions.length > 1 && <button type="button" className="msg-action remove" onClick={() => setV({ ...v, questions: v.questions.filter((_, k) => k !== i) })}><Trash2 size={13} /> Remove</button>}
                </div>
                <input aria-label={`Question ${i + 1}`} maxLength={300} required value={x.label} placeholder="Question" onChange={(e) => q(i, { label: e.target.value })} />
                {x.kind === "choice" && (
                  <div className="option-edit">
                    {x.options.map((o, k) => (
                      <div className="row" key={k}>
                        <input aria-label={`Option ${k + 1}`} maxLength={120} value={o} placeholder={`Option ${k + 1}`} onChange={(e) => q(i, { options: x.options.map((y, m) => (m === k ? e.target.value : y)) })} />
                        {x.options.length > 2 && <button type="button" className="btn small icon" aria-label={`Remove option ${k + 1}`} onClick={() => q(i, { options: x.options.filter((_, m) => m !== k) })}><X size={14} /></button>}
                      </div>
                    ))}
                    {x.options.length < 8 && <button type="button" className="text-button" onClick={() => q(i, { options: [...x.options, ""] })}><Plus size={14} /> Add an option</button>}
                  </div>
                )}
              </div>
            ))}
            {v.questions.length < 10 && <button type="button" className="btn small" onClick={() => setV({ ...v, questions: [...v.questions, { id: newId(), kind: "choice", label: "", options: ["", ""] }] })}><Plus size={14} /> Add a question</button>}
          </div>
          {error && <p className="error-banner" role="alert">{error}</p>}
          <div className="toolbar"><button className="btn primary" disabled={busy}>{busy ? "Publishing…" : "Publish the consultation"}</button><button type="button" className="btn" onClick={onClose}>Cancel</button></div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ConsultationDetail({ c, access, answered, onClose }: { c: Consultation; access: MeetingAccess; answered: boolean; onClose: () => void }) {
  const organiser = canOrganise(access, c.body);
  const open = isOpen(c);
  const [own, setOwn] = useState<ConsultationAnswer | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<ConsultationAnswer[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => subscribeOwnAnswer(c.id, (a) => { setOwn(a); if (a) setDraft(a.answers); }, () => {}), [c.id]);
  const canSeeResults = organiser || c.resultsVisible;
  useEffect(() => { setAnswers(null); if (!canSeeResults) return; return subscribeAnswers(c.id, setAnswers, (e) => setError(friendlyError(e))); }, [c.id, canSeeResults]);
  const results = useMemo(() => (answers ? tallyConsultation(c.questions, answers) : []), [answers, c.questions]);
  async function run(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError("");
    try { await fn(); toast.success(done); } catch (e) { setError(friendlyError(e)); } finally { setBusy(false); }
  }
  const name = access.profile?.name || "";
  function exportCsv() {
    downloadCsv("consultation-" + c.id + ".csv", [["Name", ...c.questions.map((q, i) => `Q${i + 1} ${q.label}`), "Answered on"], ...(answers || []).map((a) => [a.name, ...c.questions.map((q) => a.answers?.[q.id] || ""), a.updatedAt.slice(0, 16).replace("T", " ")])]);
  }
  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="detail-content consultation-dialog">
        <DialogTitle>{c.title}</DialogTitle>
        <DialogDescription>{bodyLabel(c.body)} · {typeLabel(c.audience)} · {open ? `closes ${closes(c.deadline)}` : `closed ${closes(c.deadline)}`}</DialogDescription>
        <CreatedBy uid={c.owner} at={c.createdAt} />
        {c.description && <p className="calendar-description">{c.description}</p>}
        {error && <p className="error-banner" role="alert">{error}</p>}
        {open ? (
          <form className="stack consultation-form" onSubmit={(e) => { e.preventDefault(); void run(() => answerConsultation(c.id, name, draft), own ? "Your answers were updated." : "Thank you. Your answers were recorded."); }}>
            {c.questions.map((q, i) => (
              <fieldset key={q.id} className="question-answer">
                <legend><span className="wp-mg">Q{i + 1}</span> {q.label}</legend>
                {q.kind === "text" ? (
                  <textarea rows={3} maxLength={2000} value={draft[q.id] || ""} onChange={(e) => setDraft({ ...draft, [q.id]: e.target.value })} />
                ) : (
                  <div className="answer-options">
                    {questionOptions(q).map((o) => (
                      <label key={o} className={"answer-option" + (draft[q.id] === o ? " selected" : "")}>
                        <input type="radio" name={q.id} checked={draft[q.id] === o} onChange={() => setDraft({ ...draft, [q.id]: o })} />{o}
                      </label>
                    ))}
                  </div>
                )}
              </fieldset>
            ))}
            <div className="toolbar"><button className="btn primary" disabled={busy || !Object.values(draft).some((x) => x && x.trim())}>{own ? "Update my answers" : "Submit my answers"}</button>{(own || answered) && <span className="micro">You can change your answers until the consultation closes.</span>}</div>
          </form>
        ) : own ? <p className="notice">You answered this consultation.</p> : <p className="micro">This consultation is closed.</p>}
        <section className="consultation-results">
          <div className="minutes-head">
            <h3><BarChart3 size={17} /> Results {answers && <span className="pill">{answers.length} {answers.length === 1 ? "response" : "responses"}</span>}</h3>
            {organiser && (
              <div className="row">
                <button className="btn small" disabled={busy} onClick={() => run(() => updateConsultation(c.id, { resultsVisible: !c.resultsVisible }), c.resultsVisible ? "Results hidden from participants." : "Results shared with participants.")}>{c.resultsVisible ? <><EyeOff size={14} /> Hide results</> : <><Eye size={14} /> Share results</>}</button>
                {c.status === "open" && <button className="btn small" disabled={busy} onClick={() => run(() => updateConsultation(c.id, { status: "closed" }), "Consultation closed.")}>Close now</button>}
                <button className="btn small" disabled={!answers?.length} onClick={exportCsv}><Download size={14} /> CSV</button>
                <button className="btn small" disabled={busy} onClick={() => window.confirm("Delete this consultation and its answers?") && run(async () => { await removeConsultation(c.id); onClose(); }, "Consultation deleted.")}><Trash2 size={14} /></button>
              </div>
            )}
          </div>
          {!canSeeResults ? (
            <p className="micro"><Lock size={13} /> The organisers will share the results.</p>
          ) : !answers ? <p className="micro">Loading…</p> : results.map((r, i) => (
            <div className="result-block" key={r.question.id}>
              <h4><span className="wp-mg">Q{i + 1}</span> {r.question.label} <span className="micro">· {r.total} {r.total === 1 ? "answer" : "answers"}</span></h4>
              {r.question.kind === "text" ? (
                r.texts.length ? <ul className="result-texts">{r.texts.map((t, k) => <li key={k}>{t}</li>)}</ul> : <p className="micro">No written answer.</p>
              ) : (
                r.counts.map(([o, n]) => (
                  <div className="result-bar" key={o}>
                    <span className="result-label">{o}</span>
                    <span className="result-track"><span style={{ width: (r.total ? (n / r.total) * 100 : 0) + "%" }} /></span>
                    <span className="result-count">{n}{r.total ? ` · ${Math.round((n / r.total) * 100)}%` : ""}</span>
                  </div>
                ))
              )}
            </div>
          ))}
          {organiser && answers && answers.length > 0 && <p className="micro">Respondents: {answers.map((a) => a.name).sort().join(", ")}</p>}
        </section>
      </DialogContent>
    </Dialog>
  );
}
