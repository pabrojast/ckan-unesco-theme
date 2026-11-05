import { useState } from "react";
import { ArrowRight, Briefcase, CalendarDays, ChevronRight, Layers, MessageSquare, Plus, Quote, Rocket, SquareKanban, UserCheck, UserPlus, Users } from "lucide-react";
import { groups } from "@/lib/data";
import type { WorkItem } from "@/lib/coordination";
import { challengeOf, concurrentGoals, currentTriennium, goalsOfGroup, projectsOf, trienniumOf, triennia, wgVision } from "@/lib/flagship";
import { FlagshipProjects } from "./workplan";

export type WgTab = "overview" | "projects" | "activities" | "members" | "discussion" | "tasks" | "requests";

/** Main goals that run in parallel throughout the Decade, all in focus in every triennium (Working Group 5). */
function ConcurrentGoals({ wg, items, onOpenProjects }: { wg: number; items: WorkItem[]; onOpenProjects: () => void }) {
  const c = concurrentGoals[wg], now = currentTriennium(), current = triennia.find((t) => t.n === now);
  return (
    <div className="wg-parallel">
      <div className="wg-parallel-head" aria-hidden="true">
        <span />
        <span className="wg-parallel-cols">{triennia.map((t) => <span key={t.n} className={t.n === now ? "current" : ""}><b>{t.label}</b><small>{t.period}</small></span>)}</span>
      </div>
      <ol>
        {goalsOfGroup(wg).map((g) => {
          const n = projectsOf(items, "wg" + wg, g.id).length;
          return (
            <li key={g.id} className="focus">
              <button type="button" onClick={onOpenProjects}>
                <span className="wg-parallel-goal"><span className="wp-mg">MG{g.id}</span><strong>{g.title}</strong>
                  <small><Rocket size={12} /> {n ? `${n} flagship ${n === 1 ? "project" : "projects"}` : "No flagship project yet"}</small></span>
                <span className="wg-parallel-bar" aria-label={`Runs throughout the Decade, in focus in each triennium${current ? `, including the current one (${current.period})` : ""}`}>
                  {triennia.map((t) => <span key={t.n} data-t={t.period} className={"seg" + (t.n === now ? " lit" : "")}>{t.n === now ? <b>In focus · {t.period}</b> : <i>In focus · {t.period}</i>}</span>)}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      <p className="wg-parallel-note"><Quote size={14} aria-hidden="true" /><span>The three main goals run concurrently: each of them is in focus in all three triennia of the Decade. “{c.quote}.”<cite>Terms of Reference of Working Group {wg}</cite></span></p>
    </div>
  );
}

/** The Overarching Challenge of the group, its end-of-Decade ambition and its three main goals across the three triennia. */
export function WgMission({ wg, items, onOpenProjects }: { wg: number; items: WorkItem[]; onOpenProjects: () => void }) {
  const oc = challengeOf(wg), now = currentTriennium(), [more, setMore] = useState(false);
  const vision = wgVision[wg] || "";
  return (
    <section className="wg-mission" aria-label={`Overarching Challenge ${wg}`}>
      <div className="wg-oc">
        <span className="wg-oc-badge" aria-hidden="true"><small>OC</small>{wg}</span>
        <div>
          <span className="wg-oc-kicker">Overarching Challenge {wg}</span>
          <h2>{oc.title}</h2>
          <p>{concurrentGoals[wg] ? "Addressed by three main goals that run concurrently: all three are in focus in each triennium of the Decade." : "Addressed by three main goals, one for each triennium of the Decade."}</p>
        </div>
      </div>
      {vision && (
        <blockquote className={"wg-vision" + (more ? " open" : "")}>
          <Quote size={18} aria-hidden="true" />
          <p>“{vision}”</p>
          <footer><cite>Terms of Reference of Working Group {wg}</cite>{vision.length > 190 && <button type="button" className="text-button" onClick={() => setMore(!more)}>{more ? "Show less" : "Read in full"}</button>}</footer>
        </blockquote>
      )}
      {concurrentGoals[wg] ? <ConcurrentGoals wg={wg} items={items} onOpenProjects={onOpenProjects} /> : <ol className="wg-path">
        {goalsOfGroup(wg).map((g) => {
          const t = triennia[trienniumOf(g.id) - 1], n = projectsOf(items, "wg" + wg, g.id).length;
          return (
            <li key={g.id} className={t.n === now ? "current" : t.n < now ? "past" : ""}>
              <button type="button" onClick={onOpenProjects}>
                <span className="wg-path-node" aria-hidden="true">{t.n}</span>
                <span className="wg-path-when">{t.label}{t.period ? ` · ${t.period}` : ""}{t.n === now && <b>Current focus</b>}</span>
                <span className="wg-path-goal"><span className="wp-mg">MG{g.id}</span>{g.title}</span>
                <span className="wg-path-count"><Rocket size={13} /> {n ? `${n} flagship ${n === 1 ? "project" : "projects"}` : "No flagship project yet"} <ChevronRight size={14} /></span>
              </button>
            </li>
          );
        })}
      </ol>}
    </section>
  );
}

/** How the work is organised: flagship projects, activities and the task board. */
function HowWeWork({ projects, activities, core, onTab }: { projects: number; activities: number; core: boolean; onTab: (t: WgTab) => void }) {
  return (
    <div className="how-we-work">
      <button type="button" className="hww-card projects" onClick={() => onTab("projects")}>
        <span className="hww-icon"><Rocket size={19} /></span>
        <span className="hww-text"><strong>Flagship projects <em>{projects}</em></strong><small>The strategic projects the Working Group leads to achieve each main goal.</small></span>
        <ArrowRight size={15} />
      </button>
      <button type="button" className="hww-card activities" onClick={() => onTab("activities")}>
        <span className="hww-icon"><Briefcase size={19} /></span>
        <span className="hww-text"><strong>Activities <em>{activities}</em></strong><small>Concrete contributions open to every member, often part of a flagship project.</small></span>
        <ArrowRight size={15} />
      </button>
      {core && (
        <button type="button" className="hww-card tasks" onClick={() => onTab("tasks")}>
          <span className="hww-icon"><SquareKanban size={19} /></span>
          <span className="hww-text"><strong>Task board</strong><small>Day-to-day coordination of the leadership and Core Group.</small></span>
          <ArrowRight size={15} />
        </button>
      )}
    </div>
  );
}

type Props = {
  wg: number; tab: WgTab; onTab: (t: WgTab) => void; items: WorkItem[]; activities: any[]; members: any[]; broadMembers: any[]; interested: any[]; events: any[]; posts: any[];
  broadStatus: string; onApply: () => void;
  leads: boolean; requests: React.ReactNode; pendingRequests: number;
  core: boolean; signedIn: boolean;
  appointments: React.ReactNode; tor: React.ReactNode; discussion: React.ReactNode; taskBoard: React.ReactNode;
  opCard: (o: any) => React.ReactNode; memberCard: (p: any) => React.ReactNode; eventCard: (e: any) => React.ReactNode; postCard: (p: any) => React.ReactNode;
  onOpenActivity: (o: any) => void; onPropose: () => void; onOpenEvent: (e: any) => void;
};

/** The page of one Working Group: its mission, then tabs for each kind of content. */
export function WorkingGroupPage(p: Props) {
  const g = groups[p.wg - 1];
  const projects = projectsOf(p.items, "wg" + p.wg).length;
  const upcoming = p.events.filter((e) => Date.parse(e.endAt) >= Date.now()).sort((a, b) => Date.parse(a.startAt) - Date.parse(b.startAt));
  const tabs: { id: WgTab; label: string; icon: any; count?: number; alert?: boolean }[] = [
    { id: "overview", label: "Overview", icon: Layers },
    { id: "projects", label: "Flagship projects", icon: Rocket, count: projects },
    { id: "activities", label: "Activities", icon: Briefcase, count: p.activities.length },
    { id: "members", label: "Members", icon: Users, count: p.members.length + p.broadMembers.length + p.interested.length },
    { id: "discussion", label: "Discussion", icon: MessageSquare },
    ...(p.core ? [{ id: "tasks" as WgTab, label: "Task board", icon: SquareKanban }] : []),
    ...(p.leads ? [{ id: "requests" as WgTab, label: "Membership requests", icon: UserCheck, count: p.pendingRequests || undefined, alert: p.pendingRequests > 0 }] : []),
  ];
  return (
    <div className="wg-page" style={{ "--wg-color": g.color, "--wg-ink": g.ink } as React.CSSProperties}>
      <WgMission wg={p.wg} items={p.items} onOpenProjects={() => p.onTab("projects")} />
      <nav className="wg-tabs" role="tablist" aria-label={`Sections of Working Group ${p.wg}`}>
        {tabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={p.tab === t.id} className={p.tab === t.id ? "on" : ""} onClick={() => p.onTab(t.id)}>
            <t.icon size={16} />{t.label}{t.count !== undefined && <span className={"wg-tab-count" + (t.alert ? " alert" : "")}>{t.count}</span>}
          </button>
        ))}
      </nav>
      <section className="glass wg-panel" role="tabpanel">
        {p.tab === "overview" && (
          <div className="wg-overview">
            <HowWeWork projects={projects} activities={p.activities.length} core={p.core} onTab={p.onTab} />
            <div className="wg-overview-grid">
              <div className="wg-block">
                <h3 className="wg-block-title">Appointments</h3>
                {p.appointments}
              </div>
              <div className="wg-side">
                {p.tor}
                <div className="wg-block">
                  <h3 className="wg-block-title"><CalendarDays size={16} /> Upcoming events</h3>
                  {upcoming.length ? <div className="wg-events">{upcoming.slice(0, 4).map((e) => {
                    const d = new Date(e.startAt);
                    return (
                      <button type="button" key={e.id} className="wg-event" onClick={() => p.onOpenEvent(e)}>
                        <span className="wg-event-date"><small>{d.toLocaleDateString("en-GB", { month: "short" })}</small><b>{d.getDate()}</b></span>
                        <span className="wg-event-text"><strong>{e.title}</strong><small>{d.toLocaleDateString("en-GB", { weekday: "short" })} · {d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}{e.location ? " · " + e.location : ""}</small></span>
                        <ChevronRight size={15} />
                      </button>
                    );
                  })}</div> : <p className="micro">No upcoming event for this group.</p>}
                </div>
              </div>
            </div>
            {p.posts.length > 0 && <div className="wg-block"><h3 className="wg-block-title">Latest news</h3><div className="stack" style={{ gap: 14 }}>{p.posts.slice(0, 3).map(p.postCard)}</div></div>}
          </div>
        )}
        {p.tab === "projects" && (
          <div className="wg-tab-body">
            <p className="wg-tab-intro">Flagship projects are the strategic projects of Working Group {p.wg}, led by its leadership and Core Group, for each main goal. Activities open to every member can be linked to a project.</p>
            {p.signedIn ? <FlagshipProjects wg={p.wg} items={p.items} activities={p.activities} canEdit={p.core} onOpenActivity={p.onOpenActivity} /> : <p className="micro">Sign in to see the flagship projects.</p>}
          </div>
        )}
        {p.tab === "activities" && (
          <div className="wg-tab-body">
            <div className="wg-tab-bar"><p className="wg-tab-intro">Activities are concrete contributions open to every member: answer an open call, or propose an activity of your own. The Working Group reviews proposals before they are published.</p><button type="button" className="btn primary small" onClick={p.onPropose}><Plus size={15} /> Propose an activity</button></div>
            {p.activities.length ? <div className="op-grid">{p.activities.map(p.opCard)}</div> : <p className="micro">No activity published for this group yet.</p>}
          </div>
        )}
        {p.tab === "members" && (
          <div className="wg-tab-body wg-members">
            <section className="wg-member-group">
              <header><span className="wg-member-dot core" /><div><h3>Leadership and Core Group <em>{p.members.length}</em></h3><p className="micro">Appointed by the Decade bodies and recorded by the UNESCO Secretariat.</p></div></header>
              {p.members.length ? <div className="member-grid">{p.members.map(p.memberCard)}</div> : <p className="micro">No appointment recorded yet.</p>}
            </section>
            <section className="wg-member-group">
              <header><span className="wg-member-dot broad" /><div><h3>Broad Group <em>{p.broadMembers.length}</em></h3><p className="micro">Members confirmed by the leadership of the group or the UNESCO Secretariat, with the Broad Group badge of Working Group {p.wg}. They receive the Broad Group emails.</p></div>
                {p.signedIn && p.broadStatus !== "member" && (p.broadStatus === "pending" ? <span className="pill amber">Your application is being reviewed</span> : <button type="button" className="btn small" onClick={p.onApply}><UserPlus size={14} /> {p.broadStatus === "declined" ? "Apply again" : "Apply to join"}</button>)}
              </header>
              {p.broadMembers.length ? <div className="member-grid">{p.broadMembers.map(p.memberCard)}</div> : <p className="micro">No member has been confirmed in the Broad Group yet.</p>}
            </section>
            <section className="wg-member-group interested">
              <header><span className="wg-member-dot interested" /><div><h3>Interested members <em>{p.interested.length}</em></h3><p className="micro">Members who selected Working Group {p.wg} in their profile and are not confirmed in the Broad Group. They can follow the group and apply to join it.</p></div></header>
              {p.interested.length ? <div className="member-grid">{p.interested.map(p.memberCard)}</div> : <p className="micro">No other member has selected this group.</p>}
            </section>
          </div>
        )}
        {p.tab === "discussion" && <div className="wg-tab-body wg-discussion">{p.discussion}</div>}
        {p.tab === "tasks" && p.core && <div className="wg-tab-body">{p.taskBoard}</div>}
        {p.tab === "requests" && p.leads && <div className="wg-tab-body">{p.requests}</div>}
      </section>
    </div>
  );
}
