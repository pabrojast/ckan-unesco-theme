import { useEffect, useMemo, useState } from "react";
import { Copy, Mail, RefreshCw, Users, ChevronDown, Globe2, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import { bodyLevel, meetingBodies, type MeetingAccess } from "@/lib/meetings";
import { DECADE, currentEntries, mailtoBatches, recipients, tierLabels, tierFromLevel, type MailingEntry, type Tier } from "@/lib/mailing";
import { loadList } from "@/lib/mailing-store";
import { accentStyle, eventAccent } from "@/lib/event-style";
import { bodyTitle } from "@/lib/profile-options";
import { friendlyError } from "@/lib/store";

/** Mailing lists of the bodies a member leads (lead, associate lead or secretariat). Core Group members do not see them. */
export const mailingAccess = (access: MeetingAccess) => meetingBodies.filter((b) => bodyLevel(access, b.id) >= 3);

export function MailingLists({ access, email, people }: { access: MeetingAccess; email: string; people: any[] }) {
  const bodies = useMemo(() => mailingAccess(access), [access]);
  const ids = useMemo(() => [...(access.admin ? [DECADE] : []), ...bodies.map((b) => b.id)], [access.admin, bodies]);
  const [lists, setLists] = useState<Record<string, MailingEntry[]>>({});
  const [error, setError] = useState(""), [busy, setBusy] = useState(false), [round, setRound] = useState(0);
  useEffect(() => {
    let live = true;
    setBusy(true); setError("");
    Promise.all(ids.map((id) => loadList(id).then((e) => [id, e] as const)))
      .then((pairs) => live && setLists(Object.fromEntries(pairs.map(([id, e]) => [id, currentEntries(id, e, people, access.governance)]))))
      .catch((e) => live && setError(friendlyError(e)))
      .finally(() => live && setBusy(false));
    return () => { live = false; };
  }, [ids.join(), round, people.length, access.governance]);
  const decade = lists[DECADE] || [];
  const missing = access.admin ? people.filter((p) => !decade.some((e) => e.id === p.id)) : [];
  if (!ids.length) return <p className="notice">Mailing lists are available to the leadership of each group (lead, associate leads and secretariat) and to the UNESCO Secretariat.</p>;
  return (
    <section className="mailing" aria-label="Mailing lists">
      <div className="mailing-intro">
        <div>
          <p>Each button opens a new message in your email program, addressed to you with the group in <b>Bcc</b>, so recipients do not see each other’s addresses. Use these lists for Decade coordination only.</p>
        </div>
        <button type="button" className="btn small" disabled={busy} onClick={() => setRound((n) => n + 1)}><RefreshCw size={14} /> {busy ? "Loading…" : "Refresh"}</button>
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {access.admin && (
        <article className="mailing-card decade ev">
          <header>
            <span className="mailing-icon"><Globe2 size={20} /></span>
            <div><h3>Decade-wide</h3><p className="micro">All registered members · UNESCO Secretariat only</p></div>
            <span className="pill"><ShieldCheck size={12} /> UNESCO Secretariat</span>
          </header>
          <ListRow label="All members" who="Every member registered on the platform" entries={recipients(decade, "member")} sender={email} subject="[DACS] " loading={busy && !lists[DECADE]} />
          {missing.length > 0 && !busy && (
            <p className="micro mailing-missing">{missing.length} of the {people.length} members loaded have not signed in since the lists were introduced and are not yet included: {missing.slice(0, 8).map((p) => p.name).join(", ")}{missing.length > 8 ? "…" : ""}.</p>
          )}
        </article>
      )}
      <div className="mailing-grid">
        {bodies.map((b) => {
          const entries = lists[b.id] || [], a = eventAccent({ body: b.id });
          const mine = tierFromLevel(bodyLevel({ ...access, admin: false, role: { ...(access.role || {}), role: access.role?.role === "unesco-secretariat" ? "member" : access.role?.role, badges: (access.role?.badges || []).filter((x: string) => x !== "unesco-secretariat") } }, b.id));
          const short = b.id.startsWith("wg") ? b.label : a.tag;
          return (
            <article key={b.id} className="mailing-card ev" style={accentStyle({ body: b.id })}>
              <header>
                <span className="mailing-icon"><Users size={19} /></span>
                <div><h3>{bodyTitle(b.id, b.label)}</h3><p className="micro">{entries.length} {entries.length === 1 ? "member" : "members"} on the list</p></div>
                {mine && <span className="ev-tag">You · {tierLabels[mine].label}</span>}
              </header>
              {(["leadership", "core", "broad"] as Tier[]).map((t) => (
                <ListRow key={t} label={tierLabels[t].label} who={tierLabels[t].who} entries={recipients(entries, t)} sender={email} subject={`[DACS · ${short} ${tierLabels[t].label}] `} loading={busy && !lists[b.id]} />
              ))}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ListRow({ label, who, entries, sender, subject, loading }: { label: string; who: string; entries: MailingEntry[]; sender: string; subject: string; loading: boolean }) {
  const [open, setOpen] = useState(false);
  const others = entries.filter((e) => e.email.toLowerCase() !== sender.toLowerCase());
  const links = mailtoBatches(sender, others.map((e) => e.email), subject);
  async function copy() {
    try { await navigator.clipboard.writeText(others.map((e) => e.email).join("; ")); toast.success(`${others.length} addresses copied.`); }
    catch { toast.error("Copying is not available in this browser."); }
  }
  return (
    <div className="mailing-row">
      <div className="mailing-row-text">
        <strong>{label}</strong>
        <span className="micro">{who}</span>
      </div>
      <span className="mailing-count" aria-label={`${others.length} recipients`}>{loading ? "…" : others.length}</span>
      <div className="mailing-buttons">
        {links.length <= 1 ? (
          <a className={"btn small primary" + (!others.length ? " disabled" : "")} aria-disabled={!others.length} href={others.length ? links[0] : undefined} onClick={(e) => !others.length && e.preventDefault()}><Mail size={14} /> Email in Bcc</a>
        ) : (
          links.map((href, i) => <a key={i} className="btn small primary" href={href} title="Large lists are split into several messages"><Mail size={14} /> Part {i + 1} of {links.length}</a>)
        )}
        <button type="button" className="btn small icon-only" disabled={!others.length} onClick={copy} title="Copy the addresses" aria-label={`Copy the ${label} addresses`}><Copy size={14} /></button>
        <button type="button" className={"btn small icon-only" + (open ? " on" : "")} disabled={!others.length} aria-expanded={open} onClick={() => setOpen(!open)} title="Show recipients" aria-label={`Show the ${label} recipients`}><ChevronDown size={14} /></button>
      </div>
      {open && <ul className="mailing-names">{others.map((e) => <li key={e.id}>{e.name}</li>)}</ul>}
    </div>
  );
}
