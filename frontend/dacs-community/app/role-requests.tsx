import { useEffect, useState } from "react";
import { Check, Clock3, UserCheck, X } from "lucide-react";
import { toast } from "sonner";
import { accentStyle, eventAccent } from "@/lib/event-style";
import { bodyTitle } from "@/lib/profile-options";
import { isAppointmentBadge, singleSeat } from "@/lib/governance-seats";
import { friendlyError } from "@/lib/store";
import { assignable, badgeFor, claimStatus, claimValues, recordDecisions, requestBodies, roleName, subscribePendingRequests, type Claim, type Decision, type RoleRequest } from "@/lib/role-requests";
import { MemberAvatar } from "./member-avatar";
import { PendingApplications } from "./group-requests";
import type { Application } from "@/lib/applications";

const bodyName = (id: string) => bodyTitle(id, id.toUpperCase());

/** Registration step: the member declares the groups they belong to and their role in each. */
export function RoleDeclaration({ claims, note, request, onChange, onNote }: { claims: Record<string, Claim>; note: string; request: RoleRequest | null; onChange: (c: Record<string, Claim>) => void; onNote: (n: string) => void }) {
  const set = (body: string, v: string) => {
    const next = { ...claims };
    if (v) next[body] = v as Claim; else delete next[body];
    onChange(next);
  };
  const count = Object.keys(claims).length;
  return (
    <div className="role-declaration">
      <p className="micro">Select each group you already belong to and your role in it. If you are unsure of your role, or wish to join a group, say so here. The UNESCO Secretariat will confirm, adjust or decline each answer; until then you take part as a member of the community.</p>
      <div className="role-rows">
        {requestBodies.map((b) => {
          const value = claims[b] || "", status = request && request.claims[b] === value && value ? claimStatus(request, b) : null;
          return (
            <label key={b} className={"role-row ev" + (value ? " on" : "")} style={accentStyle({ body: b })}>
              <span className="role-row-name"><i />{bodyName(b)}</span>
              <select value={value} onChange={(e) => set(b, e.target.value)} aria-label={"Your role in " + bodyName(b)}>
                <option value="">Not part of this group</option>
                {claimValues.map((c) => <option key={c} value={c}>{roleName(b, c)}</option>)}
              </select>
              {status && <span className={"claim-status " + status.state}>{status.state === "confirmed" ? <Check size={12} /> : status.state === "declined" ? <X size={12} /> : <Clock3 size={12} />}{status.label}</span>}
            </label>
          );
        })}
      </div>
      <p className="micro role-summary">{count ? `${count} ${count === 1 ? "group" : "groups"} selected.` : "No group selected: you take part as a member of the community, without a role in a group."}</p>
      <div className="field full">
        <label htmlFor="role-note">Note to the UNESCO Secretariat (optional)</label>
        <textarea id="role-note" maxLength={1000} value={note} placeholder="For example, the meeting or decision through which you were appointed." onChange={(e) => onNote(e.target.value)} />
      </div>
    </div>
  );
}

type Mutate = (body: any, success: string) => Promise<boolean>;

/** Quick decision for a declared role: the role itself, or Broad Group membership for "I wish to apply"; none when unsure. */
function quickRole(claim: string): Decision | "" {
  if (assignable.includes(claim as Decision)) return claim as Decision;
  return claim === "apply" ? "member" : "";
}
const bodyShort = (b: string) => eventAccent({ body: b }).tag;

/** UNESCO Secretariat: roles declared by members, to confirm, adjust or decline. */
export function RoleRequestsPanel({ data, mutate, saving, onOpenProfile, applications = [], onDecided }: { data: any; mutate: Mutate; saving: boolean; onOpenProfile?: (p: any) => void; applications?: Application[]; onDecided?: () => void }) {
  const [requests, setRequests] = useState<RoleRequest[]>([]), [error, setError] = useState(""), [body, setBody] = useState("");
  useEffect(() => subscribePendingRequests(setRequests, (e) => setError(friendlyError(e))), []);
  const open = (r: RoleRequest) => Object.keys(r.claims).filter((b) => !(b in r.decisions));
  const roles = requests.reduce((n, r) => n + open(r).length, 0);
  const counts = requestBodies.map((b) => [b, requests.filter((r) => open(r).includes(b)).length] as const).filter(([, n]) => n > 0);
  const shown = body ? requests.filter((r) => open(r).includes(body)) : requests;
  return (
    <section className="glass panel role-requests" aria-labelledby="role-requests-title">
      <div className="role-requests-head">
        <h2 id="role-requests-title"><UserCheck size={19} /> Declared roles and applications {requests.length + applications.length > 0 && <span className="pill blue">{requests.length + applications.length} to review</span>}</h2>
        <p className="micro">A confirmed role is recorded as the member’s badge or Governance appointment, and can be adjusted later in “Manage access & badges”.</p>
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      <PendingApplications applications={applications} people={data.people} onOpenProfile={onOpenProfile} onDecided={onDecided} />
      <div className="role-requests-bar">
        <h3 className="role-requests-sub"><UserCheck size={17} /> Roles declared at registration {roles > 0 && <span className="pill blue">{roles} {roles === 1 ? "role" : "roles"} · {requests.length} {requests.length === 1 ? "member" : "members"}</span>}</h3>
        {counts.length > 1 && (
          <div className="role-filter" role="group" aria-label="Show the roles declared in">
            <button type="button" className={"news-filter" + (!body ? " on" : "")} aria-pressed={!body} onClick={() => setBody("")}>All</button>
            {counts.map(([b, n]) => <button key={b} type="button" className={"news-filter" + (body === b ? " on" : "")} aria-pressed={body === b} onClick={() => setBody(body === b ? "" : b)}>{bodyShort(b)} <em>{n}</em></button>)}
          </div>
        )}
      </div>
      {!requests.length && !error && <p className="micro">No role declared at registration is awaiting review.</p>}
      {shown.map((r) => <RequestCard key={r.id + r.updatedAt} request={r} data={data} mutate={mutate} saving={saving} onOpenProfile={onOpenProfile} />)}
    </section>
  );
}

function RequestCard({ request: r, data, mutate, saving, onOpenProfile }: { request: RoleRequest; data: any; mutate: Mutate; saving: boolean; onOpenProfile?: (p: any) => void }) {
  const person = data.people.find((p: any) => p.id === r.id);
  const held: string[] = person ? [...new Set<string>([...(person.assignedBadgeIds || []), ...(person.membershipBadges || []).map((b: any) => b.id)])] : [];
  const current = (b: string) => (person?.membershipBadges || []).filter((x: any) => x.id === b || x.id.startsWith(b + "-")).map((x: any) => x.label).join(", ");
  const open = Object.keys(r.claims).filter((b) => !(b in r.decisions));
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const chosen = Object.entries(choice).filter(([b, v]) => v && open.includes(b)) as [string, Decision][];
  const confirmable = open.filter((b) => quickRole(r.claims[b]));
  const set = (b: string, v: string) => setChoice((c) => ({ ...c, [b]: c[b] === v ? "" : v }));
  async function save(decisions: [string, Decision][]) {
    if (!person) { toast.error("This member’s profile is not loaded. Search for the member in the list below first."); return; }
    setBusy(true);
    try {
      const add = decisions.filter(([, d]) => d !== "declined").map(([b, d]) => badgeFor(b, d)).filter(Boolean);
      if (add.length) {
        const current = [...new Set<string>([...(person.assignedBadgeIds || []), ...(person.membershipBadges || []).map((b: any) => b.id).filter(isAppointmentBadge)])];
        const ok = await mutate({ action: "role", id: r.id, role: person.role || "member", wgs: person.directWgs || [], badges: [...new Set([...current, ...add])] }, "Decisions saved and roles recorded.");
        if (!ok) return;
      }
      await recordDecisions(r, Object.fromEntries(decisions));
      if (!add.length) toast.success(decisions.length === 1 ? "Decision saved." : `${decisions.length} decisions saved.`);
      setChoice({});
    } catch (e) {
      toast.error(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }
  function declineAll() {
    if (!open.length) return;
    if (!window.confirm(`Decline the ${open.length === 1 ? "role" : open.length + " roles"} declared by ${r.name}? The member keeps taking part as a member of the community.`)) return;
    void save(open.map((b) => [b, "declined"]));
  }
  return (
    <article className="request-card">
      <header>
        <MemberAvatar name={r.name} uid={r.id} hasPhoto={person?.hasPhoto} version={person?.updatedAt} />
        <div>
          <strong>{person && onOpenProfile ? <button type="button" className="text-button" onClick={() => onOpenProfile(person)}>{r.name}</button> : r.name}</strong>
          <span className="micro">{person?.headline || person?.organisation || ""}{r.updatedAt ? ` · Updated ${new Date(r.updatedAt).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}` : ""}</span>
        </div>
        {open.length > 1 && (
          <span className="request-bulk">
            {confirmable.length > 0 && <button type="button" className="btn small" disabled={busy || saving} onClick={() => setChoice(Object.fromEntries(confirmable.map((b) => [b, quickRole(r.claims[b])])))}><Check size={14} /> Confirm all as declared</button>}
            <button type="button" className="btn small danger-outline" disabled={busy || saving} onClick={declineAll}><X size={14} /> Decline all {open.length}</button>
          </span>
        )}
      </header>
      {r.note && <blockquote className="request-note">{r.note}</blockquote>}
      <div className="request-claims">
        {Object.keys(r.claims).map((b) => {
          const decided = r.decisions[b], value = choice[b] || "", quick = quickRole(r.claims[b]);
          const g = data.governance?.find((x: any) => x.id === b);
          const seatField = value === "lead" ? "lead" : value === "associate" ? "associateLeads" : value === "secretariat" ? "secretariat" : "";
          const holder = seatField && singleSeat(b, seatField) ? (seatField === "lead" ? g?.lead : (g?.[seatField] || [])[0]) : "";
          const holderName = holder && holder !== r.id ? data.people.find((p: any) => p.id === holder)?.name || "another member" : "";
          const other = value && value !== quick && value !== "declined";
          return (
            <div key={b} className={"claim-row ev" + (value === "declined" ? " to-decline" : value ? " to-confirm" : "")} style={accentStyle({ body: b })}>
              <span className="ev-tag">{bodyShort(b)}</span>
              <span className="claim-asked"><span className="micro">Declared</span><strong>{roleName(b, r.claims[b])}</strong>{held.includes(badgeFor(b, r.claims[b])) ? <span className="micro">Already recorded</span> : current(b) && <span className="micro">Currently: {current(b)}</span>}</span>
              {decided ? (
                <span className={"claim-status " + (decided === "declined" ? "declined" : "confirmed")}>{decided === "declined" ? "Declined" : `Confirmed as ${roleName(b, decided)}`}</span>
              ) : (
                <div className="claim-decision">
                  <div className="claim-choices" role="group" aria-label={`Decision for ${r.name} in ${bodyName(b)}`}>
                    {quick && <button type="button" className={"claim-choice confirm" + (value === quick ? " on" : "")} aria-pressed={value === quick} onClick={() => set(b, quick)}><Check size={14} /> {quick === r.claims[b] ? "Confirm" : b.startsWith("wg") ? `Accept as ${roleName(b, quick)}` : "Accept as member"}</button>}
                    <button type="button" className={"claim-choice decline" + (value === "declined" ? " on" : "")} aria-pressed={value === "declined"} onClick={() => set(b, "declined")}><X size={14} /> Decline</button>
                    <select className={"claim-other" + (other ? " on" : "")} value={other ? value : ""} onChange={(e) => setChoice((c) => ({ ...c, [b]: e.target.value }))} aria-label={`Assign another role to ${r.name} in ${bodyName(b)}`}>
                      <option value="">{quick ? "Other role…" : "Assign a role…"}</option>
                      {assignable.filter((d) => d !== quick).map((d) => <option key={d} value={d}>{roleName(b, d)}</option>)}
                    </select>
                  </div>
                  {holderName && <span className="micro warn">Replaces the current holder, {holderName}.</span>}
                </div>
              )}
            </div>
          );
        })}
      </div>
      {open.length > 0 && (
        <div className="toolbar request-save">
          <button type="button" className="btn primary small" disabled={busy || saving || !chosen.length} onClick={() => save(chosen)}>{busy ? "Saving…" : chosen.length ? `Save ${chosen.length} ${chosen.length === 1 ? "decision" : "decisions"}` : "Choose a decision for each role"}</button>
          {chosen.length > 0 && <button type="button" className="text-button" disabled={busy} onClick={() => setChoice({})}>Clear</button>}
          {chosen.length > 0 && chosen.length < open.length && <span className="micro">{open.length - chosen.length} left for later</span>}
        </div>
      )}
    </article>
  );
}
