import { useState } from "react";
import { Check, ChevronDown, Inbox, UserCheck, X } from "lucide-react";
import { toast } from "sonner";
import { decideApplication, type Application } from "@/lib/applications";
import { bodyLabel } from "@/lib/meetings";
import { friendlyError } from "@/lib/store";
import { MemberAvatar } from "./member-avatar";

const when = (v: string) => (v ? new Date(v).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "");
const groupName = (b: string) => (/^wg[1-5]$/.test(b) ? `WG${b.slice(2)}` : bodyLabel(b));

function RequestRow({ a, people, onOpenProfile, onDecided, showBody }: { a: Application; people: any[]; onOpenProfile?: (p: any) => void; onDecided?: () => void; showBody?: boolean }) {
  const [busy, setBusy] = useState(false);
  const p = people.find((x) => x.id === a.uid);
  async function decide(approve: boolean) {
    setBusy(true);
    try {
      await decideApplication(a, approve);
      toast.success(approve ? `${a.name} is now a member of the ${groupName(a.body)} Broad Group.` : "Application declined.");
      onDecided?.();
    } catch (e) { toast.error(friendlyError(e)); } finally { setBusy(false); }
  }
  return (
    <article className={"request-row " + a.status}>
      <button type="button" className="request-person" onClick={() => p && onOpenProfile?.(p)} disabled={!p || !onOpenProfile}>
        <MemberAvatar name={a.name} uid={a.uid} hasPhoto={p?.hasPhoto} version={p?.updatedAt} />
        <span><strong>{a.name}</strong><small>{p?.headline || "Member"}{p?.organisation ? ` · ${p.organisation}` : ""}</small></span>
      </button>
      <span className="request-meta">{showBody && <span className="ev-tag">{groupName(a.body)}</span>}Applied {when(a.createdAt)}</span>
      {a.status === "pending" ? (
        <span className="request-actions">
          <button type="button" className="btn small primary" disabled={busy} onClick={() => decide(true)}><Check size={14} /> Approve</button>
          <button type="button" className="btn small" disabled={busy} onClick={() => decide(false)}><X size={14} /> Decline</button>
        </span>
      ) : <span className={"pill " + (a.status === "approved" ? "green" : "")}>{a.status === "approved" ? "Approved" : "Declined"} {when(a.decidedAt)}</span>}
    </article>
  );
}

/** Applications to the Broad Group of one Working Group, for its leadership. */
export function GroupRequests({ body, applications, people, onOpenProfile, onDecided }: { body: string; applications: Application[]; people: any[]; onOpenProfile?: (p: any) => void; onDecided?: () => void }) {
  const [history, setHistory] = useState(false);
  const pending = applications.filter((a) => a.status === "pending"), done = applications.filter((a) => a.status !== "pending");
  return (
    <section className="group-requests">
      <p className="wg-tab-intro">Members who applied to join the Broad Group of {groupName(body)}. Approving gives them the Broad Group badge, which adds them to the Broad Group mailing list. Only the leadership of the group and the UNESCO Secretariat see these requests.</p>
      {pending.length ? <div className="request-list">{pending.map((a) => <RequestRow key={a.id} a={a} people={people} onOpenProfile={onOpenProfile} onDecided={onDecided} />)}</div>
        : <div className="notif-empty"><span className="notif-empty-icon"><Inbox size={20} /></span><strong>No application is waiting</strong><p className="micro">New applications appear here and in your notifications.</p></div>}
      {done.length > 0 && (
        <div className="request-history">
          <button type="button" className="text-button" onClick={() => setHistory(!history)}><ChevronDown size={14} className={history ? "turned" : ""} /> Decisions already taken ({done.length})</button>
          {history && <div className="request-list">{done.map((a) => <RequestRow key={a.id} a={a} people={people} onOpenProfile={onOpenProfile} />)}</div>}
        </div>
      )}
    </section>
  );
}

/** Applications to every Broad Group awaiting a decision, for the UNESCO Secretariat (shown with the declared roles). */
export function PendingApplications({ applications, people, onOpenProfile, onDecided }: { applications: Application[]; people: any[]; onOpenProfile?: (p: any) => void; onDecided?: () => void }) {
  const [busy, setBusy] = useState(false);
  async function decideAll(approve: boolean) {
    const n = applications.length;
    if (!window.confirm(`${approve ? "Approve" : "Decline"} the ${n} applications listed?${approve ? " Each member receives the Broad Group badge of the group they applied to." : ""}`)) return;
    setBusy(true);
    let done = 0;
    try {
      for (const a of applications) { await decideApplication(a, approve); done++; }
      toast.success(`${done} ${done === 1 ? "application" : "applications"} ${approve ? "approved" : "declined"}.`);
      onDecided?.();
    } catch (e) { toast.error(`${done} of ${n} saved. ${friendlyError(e)}`); } finally { setBusy(false); }
  }
  return (
    <div className="pending-applications">
      <div className="pending-applications-head">
        <h3><UserCheck size={17} /> Applications to join a Broad Group {applications.length > 0 && <span className="pill blue">{applications.length} to review</span>}</h3>
        {applications.length > 1 && (
          <span className="request-bulk">
            <button type="button" className="btn small" disabled={busy} onClick={() => decideAll(true)}><Check size={14} /> Approve all</button>
            <button type="button" className="btn small danger-outline" disabled={busy} onClick={() => decideAll(false)}><X size={14} /> Decline all</button>
          </span>
        )}
      </div>
      <p className="micro">Sent from the “Apply to join the Broad Group” button of a Working Group page. The leadership of the group can also decide.</p>
      {applications.length ? <div className="request-list">{applications.map((a) => <RequestRow key={a.id} a={a} people={people} onOpenProfile={onOpenProfile} onDecided={onDecided} showBody />)}</div>
        : <p className="micro">No application is awaiting review.</p>}
    </div>
  );
}
