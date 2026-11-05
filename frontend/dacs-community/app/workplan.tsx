import { useMemo, useState } from "react";
import { CreatedBy } from "./people-context";
import { ArrowRight, Briefcase, CalendarClock, ChevronDown, Download, Flag, Pencil, Plus, Rocket, Trash2, Users } from "lucide-react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { groups } from "@/lib/data";
import { goalLabel } from "@/lib/decade-goals";
import { friendlyError } from "@/lib/store";
import { toCsv, workStatuses, type WorkItem } from "@/lib/coordination";
import { removeWorkItem, saveWorkItem } from "@/lib/coordination-store";
import { byDue, concurrentGoals, currentTriennium, goalsOfGroup, isProject, looseMilestones, milestonesOf, projectProgress, projectsOf, trienniumOf, triennia } from "@/lib/flagship";

const statusLabel = (s: string) => workStatuses.find((x) => x.id === s)?.label || s;
const statusClass = (s: string) => (s === "done" ? "green" : s === "delayed" ? "amber" : s === "in-progress" ? "blue" : "");
const monthText = (d: string) => (d ? new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : "");
const dayText = (d: string) => (d ? new Date(d + "T12:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "No date");
export function downloadCsv(name: string, rows: (string | number)[][]) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([toCsv(rows)], { type: "text/csv;charset=utf-8" }));
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
const activitiesOf = (activities: any[], projectId: string) => activities.filter((o) => o.project === projectId);

type Draft = Omit<WorkItem, "id" | "createdAt" | "updatedAt"> & { id?: string };
const blank = (wg: number, mg: string, kind: "deliverable" | "milestone" = "deliverable", parent = ""): Draft =>
  ({ body: "wg" + wg, kind, title: "", mg, due: "", status: "planned", lead: "", notes: "", parent });

async function confirmRemove(item: WorkItem, items: WorkItem[]) {
  const steps = isProject(item) ? milestonesOf(items, item.id).length : 0;
  if (!window.confirm(isProject(item) ? `Delete the flagship project “${item.title}”?${steps ? ` Its ${steps} ${steps === 1 ? "milestone stays" : "milestones stay"} listed under the main goal.` : ""}` : `Delete the milestone “${item.title}”?`)) return;
  try { await removeWorkItem(item.id); toast.success(isProject(item) ? "Flagship project deleted." : "Milestone deleted."); } catch (e) { toast.error(friendlyError(e)); }
}

/** Create or edit a flagship project or one of its milestones. */
function ItemDialog({ draft, setDraft, items }: { draft: Draft | null; setDraft: (d: Draft | null) => void; items: WorkItem[] }) {
  const [busy, setBusy] = useState(false);
  const wg = draft ? Number(String(draft.body).slice(2)) : 1;
  const project = draft?.kind === "deliverable";
  const projects = draft ? projectsOf(items, draft.body) : [];
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!draft) return;
    setBusy(true);
    try {
      await saveWorkItem(draft as any);
      toast.success(project ? (draft.id ? "Flagship project updated." : "Flagship project added.") : draft.id ? "Milestone updated." : "Milestone added.");
      setDraft(null);
    } catch (err) { toast.error(friendlyError(err)); } finally { setBusy(false); }
  }
  const g = groups[wg - 1];
  return (
    <Dialog open={!!draft} onOpenChange={(v) => !v && setDraft(null)}>
      <DialogContent className="detail-content fp-dialog" style={{ "--wg-color": g?.color, "--wg-ink": g?.ink } as React.CSSProperties}>
        <DialogTitle>{project ? <Rocket size={18} /> : <Flag size={18} />} {draft?.id ? (project ? "Edit the flagship project" : "Edit the milestone") : project ? "New flagship project" : "New milestone"}</DialogTitle>
        <DialogDescription>{project ? `A flagship project of WG${wg} towards one main goal. Activities open to all members can be linked to it.` : "A dated step towards a flagship project."}</DialogDescription>
        {draft && (
          <form className="fp-form" onSubmit={save}>
            {!draft.id && (
              <div className="segmented fp-kind" role="radiogroup" aria-label="Type">
                <button type="button" role="radio" aria-checked={project} className={project ? "on" : ""} onClick={() => setDraft({ ...draft, kind: "deliverable", parent: "" })}><Rocket size={14} /> Flagship project</button>
                <button type="button" role="radio" aria-checked={!project} className={!project ? "on" : ""} disabled={!projects.length} title={projects.length ? undefined : "Add a flagship project first"} onClick={() => setDraft({ ...draft, kind: "milestone", parent: projects.find((p) => p.mg === draft.mg)?.id || projects[0]?.id || "" })}><Flag size={14} /> Milestone</button>
              </div>
            )}
            <label className="field"><span>{project ? "Project title" : "Milestone"}</span><input required autoFocus maxLength={200} value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} placeholder={project ? "For example: Global cryosphere monitoring inventory" : "For example: first draft shared with the Core Group"} /></label>
            {project ? (
              <label className="field"><span>Main goal</span><select value={draft.mg} onChange={(e) => setDraft({ ...draft, mg: e.target.value })}>{goalsOfGroup(wg).map((x) => <option key={x.id} value={x.id}>{goalLabel(x.id)}</option>)}</select></label>
            ) : (
              <label className="field"><span>Flagship project</span><select required value={draft.parent || ""} onChange={(e) => { const p = projects.find((x) => x.id === e.target.value); setDraft({ ...draft, parent: e.target.value, mg: p?.mg || draft.mg }); }}>
                <option value="" disabled>Choose a project</option>
                {projects.map((p) => <option key={p.id} value={p.id}>MG{p.mg} · {p.title}</option>)}
              </select></label>
            )}
            {project && <label className="field"><span>Purpose and expected result</span><textarea maxLength={1000} rows={3} value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} placeholder="What the project will deliver for the main goal" /></label>}
            <div className="fp-form-row">
              <label className="field"><span>{project ? "Target date" : "Date"}</span><input type="date" value={draft.due} onChange={(e) => setDraft({ ...draft, due: e.target.value })} /></label>
              <label className="field"><span>Status</span><select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value as any })}>{workStatuses.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}</select></label>
            </div>
            <label className="field"><span>{project ? "Led by (person or team)" : "Responsible (optional)"}</span><input maxLength={160} value={draft.lead} onChange={(e) => setDraft({ ...draft, lead: e.target.value })} /></label>
            {!project && <label className="field"><span>Notes (optional)</span><textarea maxLength={1000} rows={2} value={draft.notes} onChange={(e) => setDraft({ ...draft, notes: e.target.value })} /></label>}
            <div className="toolbar fp-actions"><button type="button" className="btn" onClick={() => setDraft(null)}>Cancel</button><button className="btn primary" disabled={busy || (!project && !draft.parent)}>{busy ? "Saving…" : "Save"}</button></div>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Progress of a flagship project drawn as an ice core lying in its tray: one layer per milestone, in date order, from
 * the oldest on the left. Completed milestones are clear ice; the others are still to be drilled. A completed
 * project gets frosted ends.
 */
function IceCore({ steps, complete, done }: { steps: WorkItem[]; complete: boolean; done: number }) {
  return (
    <div className="fp-progress" aria-label={`${done} of ${steps.length} milestones completed`}>
      <div className={"ice-core" + (complete ? " complete" : "")}>
        {steps.map((m, i) => (
          <span key={m.id} className={"core-layer " + m.status} style={{ "--i": i } as React.CSSProperties} title={`${m.title}${m.due ? " · " + dayText(m.due) : ""} · ${statusLabel(m.status)}`}>
            {m.status === "done" && <i className="core-bubbles" />}
          </span>
        ))}
      </div>
      <small>{done} of {steps.length} {steps.length === 1 ? "milestone" : "milestones"}{complete ? " · project completed" : ""}</small>
    </div>
  );
}

function ProjectCard({ p, items, activities, canEdit, onEdit, onAddMilestone, onOpenActivity }: { p: WorkItem; items: WorkItem[]; activities: any[]; canEdit: boolean; onEdit: (i: WorkItem) => void; onAddMilestone: () => void; onOpenActivity?: (o: any) => void }) {
  const [open, setOpen] = useState(false);
  const steps = milestonesOf(items, p.id), linked = activitiesOf(activities, p.id), progress = projectProgress(steps);
  return (
    <article className={"fp-card " + p.status}>
      <div className="fp-card-top">
        <span className={"pill " + statusClass(p.status)}>{statusLabel(p.status)}</span>
        {p.due && <span className="fp-target"><CalendarClock size={13} /> Target {monthText(p.due)}</span>}
      </div>
      <h4>{p.title}</h4>
      {p.notes && <p className="fp-desc">{p.notes}</p>}
      {p.lead && <p className="fp-lead"><Users size={13} /> Led by {p.lead}</p>}
      <CreatedBy uid={p.updatedBy} verb="Updated by" at={p.updatedAt?.slice(0, 10)} />
      {progress && <IceCore steps={steps} complete={p.status === "done"} done={progress.done} />}
      <div className="fp-card-foot">
        <button type="button" className="fp-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          <span><Flag size={13} /> {steps.length} {steps.length === 1 ? "milestone" : "milestones"}</span>
          <span><Briefcase size={13} /> {linked.length} {linked.length === 1 ? "activity" : "activities"}</span>
          <ChevronDown size={15} className={open ? "turned" : ""} />
        </button>
        {canEdit && <span className="fp-tools"><button type="button" className="icon-text" onClick={() => onEdit(p)} aria-label={"Edit " + p.title}><Pencil size={13} /></button><button type="button" className="icon-text danger" onClick={() => confirmRemove(p, items)} aria-label={"Delete " + p.title}><Trash2 size={13} /></button></span>}
      </div>
      {open && (
        <div className="fp-detail">
          <div className="fp-detail-head">Milestones{canEdit && <button type="button" className="text-button" onClick={onAddMilestone}><Plus size={13} /> Add</button>}</div>
          {steps.length ? (
            <ol className="fp-steps">{steps.map((m) => (
              <li key={m.id} className={m.status}>
                <span className="fp-dot" aria-hidden="true" />
                <span className="fp-step-text"><strong>{m.title}</strong><small>{dayText(m.due)} · {statusLabel(m.status)}{m.lead ? " · " + m.lead : ""}</small></span>
                {canEdit && <span className="fp-tools"><button type="button" className="icon-text" onClick={() => onEdit(m)} aria-label={"Edit " + m.title}><Pencil size={12} /></button><button type="button" className="icon-text danger" onClick={() => confirmRemove(m, items)} aria-label={"Delete " + m.title}><Trash2 size={12} /></button></span>}
              </li>))}
            </ol>
          ) : <p className="micro">No milestone yet.</p>}
          <div className="fp-detail-head">Activities open to members</div>
          {linked.length ? <div className="fp-activities">{linked.map((o) => <button type="button" key={o.id} className="fp-activity" onClick={() => onOpenActivity?.(o)}><Briefcase size={13} /><span>{o.title}</span><ArrowRight size={13} /></button>)}</div>
            : <p className="micro">No activity is linked yet. When proposing an activity, choose this project under “Part of a flagship project”.</p>}
        </div>
      )}
    </article>
  );
}

/** Flagship projects of one Working Group, under each main goal and its triennium. */
export function FlagshipProjects({ wg, items, activities, canEdit, onOpenActivity }: { wg: number; items: WorkItem[]; activities: any[]; canEdit: boolean; onOpenActivity?: (o: any) => void }) {
  const [draft, setDraft] = useState<Draft | null>(null);
  const body = "wg" + wg, now = currentTriennium();
  return (
    <section className="fp" style={{ "--wg-color": groups[wg - 1].color, "--wg-ink": groups[wg - 1].ink } as React.CSSProperties}>
      <div className="fp-goals">
        {goalsOfGroup(wg).map((g) => {
          const t = triennia[trienniumOf(g.id) - 1], list = projectsOf(items, body, g.id), loose = looseMilestones(items, body, g.id);
          // Working Group 5: the main goals run in parallel, each in focus in every triennium.
          const par = !!concurrentGoals[wg], period = triennia.find((x) => x.n === now)?.period;
          const when = par ? `Runs throughout the Decade · in focus in every triennium${period ? ` · current: ${period}` : ""}`
            : `${t.label}${t.period ? ` · ${t.period}` : ""}${t.n === now ? " · current focus" : ""}`;
          return (
            <section className={"fp-goal" + ((par ? now > 0 : t.n === now) ? " current" : "")} key={g.id}>
              <header>
                <span className={"fp-tri" + (par ? " all" : "")} aria-hidden="true">{par ? "T1–3" : `T${t.n}`}</span>
                <div><small>{when}</small><h3><span className="wp-mg">MG{g.id}</span>{g.title}</h3></div>
                {canEdit && <button type="button" className="btn small" onClick={() => setDraft(blank(wg, g.id))}><Plus size={14} /> Flagship project</button>}
              </header>
              {list.length ? <div className="fp-cards">{list.map((p) => <ProjectCard key={p.id} p={p} items={items} activities={activities} canEdit={canEdit} onEdit={(i) => setDraft(i)} onAddMilestone={() => setDraft(blank(wg, p.mg, "milestone", p.id))} onOpenActivity={onOpenActivity} />)}</div>
                : <p className="fp-empty">No flagship project recorded for this main goal yet.</p>}
              {loose.length > 0 && <div className="fp-loose"><span className="micro">Milestones not linked to a project</span><ul>{loose.map((m) => <li key={m.id}><Flag size={12} /> {m.title} <small>· {dayText(m.due)} · {statusLabel(m.status)}</small>{canEdit && <button type="button" className="text-button" onClick={() => setDraft(m)}>Link to a project</button>}</li>)}</ul></div>}
            </section>
          );
        })}
      </div>
      <ItemDialog draft={draft} setDraft={setDraft} items={items} />
    </section>
  );
}

/** Flagship projects of the five Working Groups, for the SMC, the Secretariat and every member. */
export function FlagshipOverview({ items, activities, canEdit, onOpenGroup, onOpenActivity, error }: { items: WorkItem[] | null; activities: any[]; canEdit: (wg: number) => boolean; onOpenGroup: (wg: number) => void; onOpenActivity?: (o: any) => void; error?: string }) {
  const [wg, setWg] = useState(1);
  const list = items || [];
  const counts = useMemo(() => groups.map((g) => ({ id: g.id, projects: projectsOf(list, "wg" + g.id).length, done: projectsOf(list, "wg" + g.id).filter((p) => p.status === "done").length })), [list]);
  function exportCsv() {
    const title = (id?: string) => list.find((i) => i.id === id)?.title || "";
    downloadCsv("dacs-flagship-projects.csv", [
      ["Working Group", "Main goal", "Type", "Title", "Flagship project", "Target or due date", "Status", "Led by / responsible", "Description or notes", "Linked activities"],
      ...[...list].sort((a, b) => a.body.localeCompare(b.body) || a.mg.localeCompare(b.mg) || byDue(a, b)).map((i) => [
        i.body.toUpperCase(), "MG" + i.mg, isProject(i) ? "Flagship project" : "Milestone", i.title, isProject(i) ? "" : title(i.parent), i.due, statusLabel(i.status), i.lead, i.notes,
        isProject(i) ? activitiesOf(activities, i.id).map((o) => o.title).join("; ") : "",
      ]),
    ]);
  }
  const g = groups[wg - 1];
  return (
    <section className="fp-overview">
      <div className="fp-switch" role="tablist" aria-label="Working Groups">
        {groups.map((x, i) => (
          <button key={x.id} role="tab" aria-selected={wg === x.id} className={wg === x.id ? "on" : ""} style={{ "--wg-color": x.color, "--wg-ink": x.ink } as React.CSSProperties} onClick={() => setWg(x.id)}>
            <span className="fp-switch-badge">WG{x.id}</span><span className="fp-switch-text"><strong>{x.short}</strong><small>{counts[i].projects} {counts[i].projects === 1 ? "project" : "projects"}{counts[i].done ? ` · ${counts[i].done} completed` : ""}</small></span>
          </button>
        ))}
      </div>
      <div className="fp-overview-bar">
        <h2>{g.title}</h2>
        <div className="row"><button className="btn small" onClick={() => onOpenGroup(wg)}>Open the group <ArrowRight size={14} /></button><button className="btn small" onClick={exportCsv} disabled={!list.length}><Download size={14} /> Export CSV</button></div>
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!items && !error ? <p className="micro">Loading the flagship projects…</p> : <FlagshipProjects wg={wg} items={list} activities={activities} canEdit={canEdit(wg)} onOpenActivity={onOpenActivity} />}
    </section>
  );
}
