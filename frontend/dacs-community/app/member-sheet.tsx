import type { CSSProperties, ReactNode } from "react";
import { ArrowUpRight, BookOpen, Briefcase, Clock3, Globe2, GraduationCap, Languages, Lock, Mail, MapPin, MessageCircle, Mountain, Sparkles, Target, UserRound } from "lucide-react";
import { DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { groups } from "@/lib/data";
import { MemberAvatar } from "./member-avatar";
import { MemberBadges } from "./member-badges";

const brand = { color: "#0a6eb4", ink: "#0a5a94" };
const day = (s: string) => (s ? new Date(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) : "");

/** Colour of a member's page: their first appointment in a Working Group, otherwise their first Working Group interest. */
export function memberAccent(p: any) {
  const appointed = (p.membershipBadges || []).map((b: any) => /^wg([1-5])-/.exec(b.id)?.[1]).find(Boolean);
  const n = Number(appointed || (p.wgs || [])[0] || 0);
  const g = groups.find((x) => x.id === n);
  return g ? { color: g.color, ink: g.ink } : brand;
}

/** The page of one member: header in their Working Group colour, summary cards and sections. */
export function MemberSheet({ person: p, contributions = [], canMessage = false, onMessage, onClose }: { person: any; contributions?: any[]; canMessage?: boolean; onMessage?: () => void; onClose?: () => void }) {
  const website = p.website && /^https?:\/\//i.test(p.website) ? p.website : "";
  const career = [p.careerStage, p.educationLevel].filter((v) => v && v !== "Prefer not to say");
  const shown = p.showBackground === true && (p.publicGender || p.publicSentiment);
  // Answers the member keeps private stay visible to the UNESCO Secretariat only.
  const privateGender = !shown && p.gender, privateSentiment = !shown && p.sentiment;
  const privateInfo = privateGender || privateSentiment || p.feedback;
  const record = contributions.filter((c) => c.member_id === p.id);
  return (
    <>
      <header className="member-hero">
        <div className="member-hero-avatar"><MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} large /></div>
        <div className="member-hero-text">
          <DialogTitle>{p.name}</DialogTitle>
          <DialogDescription>{p.headline || "Member of the DACS community"}</DialogDescription>
          <div className="member-hero-meta">
            {p.organisation && <span><Briefcase size={13} />{p.organisation}</span>}
            {p.country && <span><MapPin size={13} />{p.country}</span>}
            {p.region && <span><Globe2 size={13} />{p.region}</span>}
          </div>
        </div>
      </header>
      <MemberBadges badges={p.membershipBadges} />
      {(canMessage || website || p.contact) && (
        <div className="member-actions">
          {canMessage && onMessage && <button type="button" className="btn primary" onClick={() => { onMessage(); onClose?.(); }}><MessageCircle size={15} /> Send a message</button>}
          {p.contact && <a className="btn" href={"mailto:" + p.contact}><Mail size={15} /> {p.contact}</a>}
          {website && <a className="btn" href={website} target="_blank" rel="noopener noreferrer">Professional profile <ArrowUpRight size={14} /></a>}
        </div>
      )}
      <div className="member-facts">
        <Fact icon={<Target size={17} />} label="Working Group interests">
          {(p.wgs || []).length ? (
            <div className="oc-chips">{(p.wgs || []).map((n: number) => { const g = groups.find((x) => x.id === n); return g ? <span key={n} className="oc-chip" style={{ "--wg-color": g.color } as CSSProperties}>WG{n} · {g.short}</span> : null; })}</div>
          ) : <strong>Across the Decade</strong>}
        </Fact>
        <Fact icon={<Clock3 size={17} />} label="Availability"><strong>{p.availability || "Not specified"}</strong></Fact>
        <Fact icon={<Languages size={17} />} label="Languages"><strong>{(p.languages || []).join(", ") || "Not specified"}</strong></Fact>
        <Fact icon={<GraduationCap size={17} />} label="Career"><strong>{career.join(" · ") || "Not specified"}</strong></Fact>
      </div>
      {(p.skills || []).length > 0 && (
        <section className="event-section">
          <h3><Sparkles size={16} /> Expertise</h3>
          <div className="member-tags">{p.skills.map((s: string) => <span key={s}>{s}</span>)}</div>
        </section>
      )}
      {(p.cryosphereTypes || []).length > 0 && (
        <section className="event-section">
          <h3><Mountain size={16} /> Cryosphere focus</h3>
          <div className="member-tags soft">{p.cryosphereTypes.map((s: string) => <span key={s}>{s}</span>)}</div>
        </section>
      )}
      {[["About", p.bio, <UserRound size={16} key="a" />], ["Why I joined", p.motivation, <BookOpen size={16} key="b" />], ["Potential contributions", p.contribution, <Briefcase size={16} key="c" />]].map(([title, text, icon]) =>
        text ? (
          <section className="event-section" key={title as string}>
            <h3>{icon} {title}</h3>
            <p className="calendar-description">{text as string}</p>
          </section>
        ) : null,
      )}
      {shown && (
        <section className="member-background">
          {p.publicGender && <p><span>Gender</span>{p.publicGender}</p>}
          {p.publicSentiment && <p><span>Feeling about the Decade</span>{p.publicSentiment}</p>}
        </section>
      )}
      {privateInfo && (
        <section className="member-private">
          <h3><Lock size={15} /> Visible to the UNESCO Secretariat only</h3>
          {privateGender && <p><span>Gender</span>{privateGender}</p>}
          {privateSentiment && <p><span>Feeling about the Decade</span>{privateSentiment}</p>}
          {p.feedback && <p><span>Support that would help</span>{p.feedback}</p>}
        </section>
      )}
      <footer className="member-record">
        <span className="micro">Profile created {day(p.createdAt)} · Updated {day(p.updatedAt)}</span>
        {record.length > 0 && (
          <ul>{record.map((c) => <li key={c.id}><strong>{c.opportunity_title}</strong><span className="micro">{c.status} · {day(c.createdAt)}</span></li>)}</ul>
        )}
      </footer>
    </>
  );
}

function Fact({ icon, label, children }: { icon: ReactNode; label: string; children: ReactNode }) {
  return (
    <div className="fact">
      <span className="fact-icon">{icon}</span>
      <div><span className="fact-label">{label}</span>{children}</div>
    </div>
  );
}

/** CSS colour variables for the dialog that shows a member. */
export const memberStyle = (p: any) => { const a = memberAccent(p); return { "--ev": a.color, "--ev-ink": a.ink, "--ev-stripe": a.color, "--ev-stripe-v": a.color } as CSSProperties; };
