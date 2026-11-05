import { Briefcase, Calendar, Check, Clock, Globe, Languages, Pencil, Rocket, Search, Sparkles, Trash2, UserRound } from "lucide-react";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { activityGroups } from "@/lib/decade-goals";
import { groups } from "@/lib/data";
import type { WorkItem } from "@/lib/coordination";
import { AttachmentList } from "./attachments";
import { GoalLabels } from "./goal-picker";
import { MemberAvatar } from "./member-avatar";

const day = (s: string) => new Date(s + (s.length === 10 ? "T12:00:00Z" : "")).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
const statusOf = (s: string) => (s === "open" ? { cls: "open", label: "Open call" } : s === "pending" ? { cls: "pending", label: "Awaiting review by the Working Group" } : { cls: "closed", label: "Closed" });

type Props = {
  op: any | null; onClose: () => void; people: any[]; me: any; projects: WorkItem[]; projectTitle: string;
  match: { score: number; shared: string[] } | null; applied: boolean; canManage: boolean; canEdit: boolean;
  onApply: () => void; onFind: () => void; onToggleStatus: () => void; onEdit: () => void; onDelete: () => void; onLink: (project: string) => void;
};

/** One activity: what is asked, who proposed it, how it contributes, and what the member can do. */
export function ActivityDetail(p: Props) {
  const o = p.op, wg = o ? groups[o.wg - 1] : null;
  const owner = o ? p.people.find((x) => x.id === o.owner) : null;
  const st = o ? statusOf(o.status) : null;
  return (
    <Dialog open={!!o} onOpenChange={(v) => !v && p.onClose()}>
      <DialogContent className="detail-content activity-dialog" style={wg ? ({ "--wg-color": wg.color, "--wg-ink": wg.ink } as React.CSSProperties) : undefined}>
        {o && wg && st && (
          <>
            <header className="activity-hero">
              <div className="activity-kicker">
                {activityGroups(o).map((n) => <span key={n} className="activity-wg" style={{ "--wg-color": groups[n - 1].color, "--wg-ink": groups[n - 1].ink } as React.CSSProperties}>WG{n} · {groups[n - 1].short}</span>)}
                <span className={"activity-status " + st.cls}>{st.cls === "open" && <i />}{st.label}</span>
              </div>
              <DialogTitle>{o.title}</DialogTitle>
              <DialogDescription asChild>
                <div className="activity-by">
                  <MemberAvatar name={owner?.name || "Member"} uid={o.owner} hasPhoto={owner?.hasPhoto} version={owner?.updatedAt} />
                  <span>Proposed by <b>{owner?.name || "a member"}</b>{o.createdAt ? ` · ${day(String(o.createdAt).slice(0, 10))}` : ""} · {o.type}</span>
                </div>
              </DialogDescription>
            </header>

            <div className="activity-facts">
              <span><Clock size={15} /><small>Time</small>{o.commitment}</span>
              <span><Globe size={15} /><small>Region</small>{o.region}</span>
              <span><Languages size={15} /><small>Language</small>{o.language}</span>
              <span><Calendar size={15} /><small>Deadline</small>{o.deadline ? day(o.deadline) : "None"}</span>
            </div>

            <section className="activity-section">
              <h3><Briefcase size={15} /> What is asked</h3>
              <p className="activity-text">{o.description}</p>
              <AttachmentList items={o.attachments} />
            </section>

            {o.skills?.length > 0 && (
              <section className="activity-section">
                <h3><Sparkles size={15} /> Expertise requested</h3>
                <div className="tags">{o.skills.map((s: string) => <span className={"tag" + (p.match?.shared.includes(s) ? " matched" : "")} key={s}>{p.match?.shared.includes(s) && <Check size={12} />}{s}</span>)}</div>
              </section>
            )}

            <section className="activity-section">
              <h3><Rocket size={15} /> Contributes to</h3>
              <GoalLabels value={o.mgs} />
              {p.canManage && p.projects.length ? (
                <label className="activity-project">Part of a flagship project
                  <select value={p.projects.some((x) => x.id === o.project) ? o.project : ""} onChange={(e) => p.onLink(e.target.value)}>
                    <option value="">Not linked</option>
                    {p.projects.map((x) => <option key={x.id} value={x.id}>MG{x.mg} · {x.title}</option>)}
                  </select>
                </label>
              ) : p.projectTitle ? <p className="activity-project"><Rocket size={14} /> Part of the flagship project <b>{p.projectTitle}</b></p> : null}
            </section>

            {p.me && p.match && (
              <div className="activity-match">
                <span className="activity-score" style={{ "--score": p.match.score } as React.CSSProperties}><b>{p.match.score}%</b></span>
                <span><strong>Your profile match</strong><small>{p.match.shared.length ? `Shared expertise: ${p.match.shared.join(", ")}` : "No shared expertise recorded in your profile yet."}</small></span>
              </div>
            )}

            <div className="activity-actions">
              {o.status === "open"
                ? <button className="btn primary" disabled={p.applied} onClick={p.onApply}>{p.applied ? <><Check size={15} /> Interest recorded</> : "Record my interest"}</button>
                : null}
              <button className="btn" onClick={p.onFind}><Search size={15} /> Find contributors</button>
              {p.canManage && <button className="btn" onClick={p.onToggleStatus}>{o.status === "open" ? "Close the activity" : "Approve and open"}</button>}
              <span className="spacer" />
              {p.canEdit && <button className="btn small" onClick={p.onEdit}><Pencil size={14} /> Edit</button>}
              {p.canEdit && <button className="btn small ban-button" onClick={p.onDelete}><Trash2 size={14} /> Delete</button>}
            </div>
            {p.canEdit && p.me?.id === o.owner && !p.canManage && <p className="micro activity-owner-note"><UserRound size={13} /> You proposed this activity: you can edit or delete it. Its Working Group and status are set by the Working Group.</p>}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
