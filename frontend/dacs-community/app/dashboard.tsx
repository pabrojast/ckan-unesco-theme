import { useEffect, useMemo, useState } from "react";
import { BadgeCheck, CalendarClock, ClipboardCopy, Download, FileText, Globe2, Hourglass, Mail, RefreshCw, UserPlus, Users } from "lucide-react";
import { toast } from "sonner";
import { appUrl } from "@/lib/base";
import { groups, regions } from "@/lib/data";
import { meetingBodies, bodyLabel } from "@/lib/meetings";
import { optionsFor } from "@/lib/profile-options";
import { friendlyError } from "@/lib/store";
import { buildDigest, daysBetween, logoDeadlines, tally } from "@/lib/coordination";
import { loadDashboard, publishMemberStats } from "@/lib/coordination-store";
import { MembersMap } from "./members-map";
import { downloadCsv } from "./workplan";

type Row = [string, number];
function Bars({ title, rows, total, csv, note }: { title: string; rows: Row[]; total: number; csv: string; note?: string }) {
  const max = Math.max(1, ...rows.map((r) => r[1]));
  return (
    <section className="glass dash-card">
      <div className="dash-card-head"><h3>{title}</h3><button className="btn small icon" title="Download CSV" aria-label={"Download " + title + " as CSV"} onClick={() => downloadCsv(csv, [[title, "Members", "Share"], ...rows.map(([k, n]) => [k, n, total ? Math.round((n / total) * 1000) / 10 + "%" : ""])])}><Download size={14} /></button></div>
      <ul className="dash-bars">
        {rows.map(([k, n]) => (
          <li key={k}><span className="dash-label">{k}</span><span className="dash-track"><span style={{ width: (n / max) * 100 + "%" }} /></span><b>{n}</b><span className="dash-share">{total ? Math.round((n / total) * 100) + "%" : ""}</span></li>
        ))}
      </ul>
      {note && <p className="micro">{note}</p>}
    </section>
  );
}
const fmtDate = (iso: string) => (iso ? new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "—");

/** Secretariat dashboard: membership, meeting rhythm, pending reviews, logo deadlines, members map and weekly digest. */
export function SecretariatDashboard({ data, categories, onOpenPending, onOpenLogo }: { data: any; categories: any[]; onOpenPending: () => void; onOpenLogo: () => void }) {
  const [raw, setRaw] = useState<any>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [digestDays, setDigestDays] = useState(7);
  async function load() {
    setLoading(true);
    setError("");
    try { const d = await loadDashboard(); setRaw(d); void publishMemberStats(d.profiles, d.privateProfiles).catch(() => {}); } catch (e) { setError(friendlyError(e)); } finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, []);
  const profiles: any[] = raw?.profiles || [];
  const genderById = useMemo(() => new Map<string, string>((raw?.privateProfiles || []).map((p: any) => [p.id, p.gender || ""])), [raw]);
  const genderOf = (id: string) => genderById.get(id) || "";
  const total = profiles.length;
  const since30 = Date.now() - 30 * 86400000;
  const newMembers = profiles.filter((p) => Date.parse(p.createdAt) >= since30).length;
  const byGroup: Row[] = groups.map((g) => [`WG${g.id} · ${g.short}`, profiles.filter((p) => (p.wgs || []).includes(g.id)).length]);
  const byRegion = tally(profiles, (p) => p.region, regions) as Row[];
  const byGender = tally(profiles, (p) => genderOf(p.id), optionsFor("genders", categories)) as Row[];
  const byStage = tally(profiles, (p) => p.careerStage, optionsFor("careerStages", categories)) as Row[];
  const pending = (data.opportunities || []).filter((o: any) => o.status === "pending");
  const logo = logoDeadlines(raw?.logoRequests || []);
  const near = logo.filter((r) => r.state === "near"), late = logo.filter((r) => r.state === "late");
  const rhythm = meetingBodies.map((b) => {
    const meetings = (raw?.events || []).filter((e: any) => e.body === b.id && e.meetingType && e.meetingType !== "public");
    const past = meetings.filter((e: any) => Date.parse(e.endAt) <= Date.now()).sort((a: any, z: any) => z.startAt.localeCompare(a.startAt));
    const next = meetings.filter((e: any) => Date.parse(e.endAt) > Date.now()).sort((a: any, z: any) => a.startAt.localeCompare(z.startAt));
    const days = past[0] ? daysBetween(past[0].endAt) : null;
    return { id: b.id, label: bodyLabel(b.id), last: past[0]?.startAt || "", days, next: next[0]?.startAt || "", count: past.length };
  });
  function exportRhythm() {
    downloadCsv("dacs-meeting-rhythm.csv", [["Body", "Last meeting", "Days since", "Next meeting", "Meetings in the last 13 months"], ...rhythm.map((r) => [r.label, r.last.slice(0, 10), r.days ?? "", r.next.slice(0, 10), r.count])]);
  }
  function exportSummary() {
    downloadCsv("dacs-community-summary.csv", [
      ["Indicator", "Category", "Value"],
      ["Registered members", "", total], ["New members (last 30 days)", "", newMembers],
      ...byGroup.map(([k, n]) => ["Members by Working Group interest", k, n]),
      ...byRegion.map(([k, n]) => ["Members by region", k, n]),
      ...byGender.map(([k, n]) => ["Members by gender (totals only)", k, n]),
      ...byStage.map(([k, n]) => ["Members by professional experience", k, n]),
      ["Activities awaiting review", "", pending.length],
      ["Open logo requests", "", logo.length], ["Logo requests at 30–40 working days", "", near.length], ["Logo requests beyond 40 working days", "", late.length],
      ...rhythm.map((r) => ["Days since last meeting", r.label, r.days ?? "No meeting recorded"]),
    ]);
  }
  const digest = useMemo(() => buildDigest({
    since: new Date(Date.now() - digestDays * 86400000), until: new Date(), people: profiles.filter((p) => p.visibility === "community"), posts: data.posts || [],
    events: (raw?.events || []).filter((e: any) => !e.meetingType || e.meetingType === "public" || e.body), opportunities: data.opportunities || [],
    appUrl: appUrl().replace(/\/$/, ""), groupLabel: (wg: number) => (wg ? `WG${wg}` : "Decade-wide"),
  }), [raw, digestDays, data.posts, data.opportunities]);
  async function copyDigest(rich: boolean) {
    try {
      if (rich && "ClipboardItem" in window) await navigator.clipboard.write([new ClipboardItem({ "text/html": new Blob([digest.html], { type: "text/html" }), "text/plain": new Blob([digest.text], { type: "text/plain" }) })]);
      else await navigator.clipboard.writeText(digest.text);
      toast.success(rich ? "Digest copied. Paste it into a new Outlook message." : "Plain-text digest copied.");
    } catch { toast.info("Copying was blocked by the browser. Select the preview text and copy it."); }
  }
  const tiles = [
    { icon: Users, label: "Registered members", value: total, sub: `${profiles.filter((p) => p.visibility === "community").length} visible in the directory` },
    { icon: UserPlus, label: "New in 30 days", value: newMembers, sub: "profiles created" },
    { icon: Hourglass, label: "Activities awaiting review", value: pending.length, sub: "proposed by members", action: onOpenPending },
    { icon: BadgeCheck, label: "Logo requests near or past 40 days", value: near.length + late.length, sub: `${late.length} beyond · ${near.length} at 30–40 working days`, action: onOpenLogo, warn: late.length > 0 },
  ];
  return (
    <div className="dashboard">
      <div className="hub-toolbar">
        <p className="micro">Figures cover every registered profile, including private ones. Gender appears only as totals.</p>
        <div className="row">
          <button className="btn" onClick={load} disabled={loading}><RefreshCw size={15} /> {loading ? "Updating…" : "Update"}</button>
          <button className="btn primary" onClick={exportSummary} disabled={!raw}><Download size={15} /> Summary report (CSV)</button>
        </div>
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      <div className="stats dash-tiles">
        {tiles.map((t) => (
          <button key={t.label} className={"glass stat dash-tile" + (t.warn ? " warn" : "")} onClick={t.action} disabled={!t.action}>
            <span className="stat-icon"><t.icon size={20} /></span>
            <span><strong>{raw ? t.value : "…"}</strong><span>{t.label}</span><small>{t.sub}</small></span>
          </button>
        ))}
      </div>
      <div className="dash-grid">
        <Bars title="Working Group interest" rows={byGroup} total={total} csv="dacs-members-by-working-group.csv" note="A member can select several groups." />
        <Bars title="Region" rows={byRegion} total={total} csv="dacs-members-by-region.csv" />
        <Bars title="Gender" rows={byGender} total={total} csv="dacs-members-by-gender.csv" note="Private answers, shown as totals only." />
        <Bars title="Professional experience" rows={byStage} total={total} csv="dacs-members-by-professional-experience.csv" />
      </div>
      <section className="glass dash-card">
        <div className="dash-card-head"><h3><CalendarClock size={17} /> Meeting rhythm</h3><button className="btn small" onClick={exportRhythm}><Download size={14} /> CSV</button></div>
        <div className="table-scroll">
          <table className="dash-table">
            <thead><tr><th>Body</th><th>Last meeting</th><th>Days since</th><th>Next meeting</th><th>Meetings in 13 months</th></tr></thead>
            <tbody>{rhythm.map((r) => (
              <tr key={r.id}><td>{r.label}</td><td>{fmtDate(r.last)}</td><td><span className={"pill " + (r.days === null ? "" : r.days >= 28 ? "amber" : r.days >= 21 ? "blue" : "green")}>{r.days === null ? "None recorded" : r.days + " days"}</span></td><td>{fmtDate(r.next)}</td><td>{r.count}</td></tr>
            ))}</tbody>
          </table>
        </div>
        <p className="micro">Meetings are calendar entries of a body (Leadership, Core Group or Broad Group). Groups are reminded after 21 days.</p>
      </section>
      <div className="dash-grid two">
        <section className="glass dash-card">
          <div className="dash-card-head"><h3><Hourglass size={17} /> Activities awaiting review</h3>{pending.length > 0 && <button className="btn small" onClick={onOpenPending}>Open</button>}</div>
          {pending.length ? <ul className="dash-list">{pending.slice(0, 8).map((o: any) => <li key={o.id}><strong>{o.title}</strong><span className="micro">WG{o.wg} · waiting {daysBetween(o.createdAt)} days</span></li>)}</ul> : <p className="micro">Nothing is waiting for review.</p>}
        </section>
        <section className="glass dash-card">
          <div className="dash-card-head"><h3><BadgeCheck size={17} /> Logo requests and the 40 working-day target</h3><button className="btn small" onClick={onOpenLogo}>Open the desk</button></div>
          {[...late, ...near].length ? (
            <ul className="dash-list">{[...late, ...near].slice(0, 8).map((r) => <li key={r.id}><strong>{r.title}</strong><span className="micro">{r.organisation ? r.organisation + " · " : ""}received {fmtDate(r.receivedAt)} · <span className={"pill " + (r.state === "late" ? "amber" : "blue")}>{r.days} working days</span></span></li>)}</ul>
          ) : <p className="micro">{logo.length ? `${logo.length} open requests, all within 30 working days.` : "No open logo request."}</p>}
          <p className="micro">Counted as in the logo desk: Level 1 requests, Monday to Friday, excluding time awaiting the applicant.</p>
        </section>
      </div>
      <section className="glass dash-card">
        <div className="dash-card-head"><h3><Globe2 size={17} /> Members around the world</h3></div>
        <MembersMap people={profiles} genderOf={genderOf} categories={categories} />
      </section>
      <section className="glass dash-card digest">
        <div className="dash-card-head">
          <h3><Mail size={17} /> Weekly digest</h3>
          <div className="row">
            <label className="meeting-filter">Period<select value={digestDays} onChange={(e) => setDigestDays(Number(e.target.value))}><option value={7}>Last 7 days</option><option value={14}>Last 14 days</option><option value={31}>Last month</option></select></label>
            <button className="btn primary" onClick={() => copyDigest(true)} disabled={!raw}><ClipboardCopy size={15} /> Copy for email</button>
            <button className="btn" onClick={() => copyDigest(false)} disabled={!raw}><FileText size={15} /> Copy as text</button>
          </div>
        </div>
        <p className="micro">New members ({digest.counts.members}), news ({digest.counts.news}), meetings and events in the next three weeks ({digest.counts.upcoming}) and open calls ({digest.counts.calls}). Paste it into an email to the community; only members visible in the directory are named.</p>
        <div className="digest-preview" dangerouslySetInnerHTML={{ __html: digest.html }} />
      </section>
    </div>
  );
}
