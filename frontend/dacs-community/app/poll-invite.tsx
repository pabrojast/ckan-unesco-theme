import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarCheck, Check, Clock, LoaderCircle, Lock, Users } from "lucide-react";
import { toast } from "sonner";
import { useMemberAuth, AuthForm, ThemeSwitch, signOutMember } from "./auth";
import { PhotoBackdrop } from "./photo";
import { SlotCard, formatDeadline, timeLeft, slotParts } from "./poll-ui";
import { TimeZonePicker } from "./time-zone-picker";
import { useTimeZone } from "@/hooks/use-time-zone";
import { photos } from "@/lib/imagery";
import { bodyLabel, typeLabel, rankSlots, completeAnswers, activeSlots, padAnswers, answerIncomplete, type MeetingPoll, type PollResponse } from "@/lib/meetings";
import { subscribePoll, subscribeResponses, respond, ownProfileName } from "@/lib/meeting-store";
import { friendlyError } from "@/lib/store";
import { configured } from "@/lib/firebase";
import { asset, HOME } from "@/lib/base";

/**
 * Page opened by a shared poll link (/poll/<id>).
 * Invitees sign in or create an account on the page, then answer. A member profile is not required to vote.
 */
export function PollInvite({ pollId }: { pollId: string }) {
  const { user, initializing } = useMemberAuth();
  const [mode, setMode] = useState("register");
  return (
    <main className="invite-shell">
      <header className="invite-hero has-photo">
        <PhotoBackdrop photo={photos.icebergSky} eager />
        <div className="invite-hero-inner">
          <a href={HOME} className="invite-brand" aria-label="DACS Community">
            <img src={asset("/assets/decade-logo-white.webp")} alt="Decade of Action for Cryospheric Sciences 2025–2034" />
            <i aria-hidden="true" />
            <img src={asset("/assets/unesco-logo-white.webp")} alt="UNESCO" />
          </a>
          <div className="eyebrow">DACS Community · meeting poll</div>
        </div>
      </header>
      <section className="invite-card glass">
        {initializing ? (
          <div className="invite-loading" role="status"><LoaderCircle className="spinner" size={22} /> Loading…</div>
        ) : !user ? (
          <div className="invite-auth">
            <div>
              <h1>You are invited to give your availability</h1>
              <p className="lead">
                {mode === "register"
                  ? "Create an account to open the poll. You can vote straight away; your member profile can wait."
                  : "Sign in to open the poll and vote."}
              </p>
            </div>
            <ol className="invite-steps" aria-label="How it works">
              <li className="current"><span>1</span>{mode === "register" ? "Create an account" : "Sign in"}</li>
              <li><span>2</span>Choose your times</li>
              <li><span>3</span>Save</li>
            </ol>
            {configured ? (
              <AuthForm mode={mode} onModeChange={setMode} registeredMessage="Account created. You can now vote." />
            ) : (
              <p className="error-banner">Sign-in is unavailable until the Firebase web settings are configured.</p>
            )}
          </div>
        ) : (
          <PollVote pollId={pollId} uid={user.uid} email={user.email || ""} displayName={user.displayName || ""} />
        )}
      </section>
      <footer className="invite-foot">
        <span>Decade of Action for Cryospheric Sciences 2025–2034 · Secretariat hosted by UNESCO–IHP</span>
        <span className="entry-foot"><ThemeSwitch /></span>
      </footer>
    </main>
  );
}

function PollVote({ pollId, uid, email, displayName }: { pollId: string; uid: string; email: string; displayName: string }) {
  const { zone, setZone, automatic, useDevice } = useTimeZone(uid);
  const [poll, setPoll] = useState<MeetingPoll | null | undefined>(undefined),
    [problem, setProblem] = useState(""),
    [responses, setResponses] = useState<PollResponse[]>([]),
    [profileName, setProfileName] = useState<string | null | undefined>(undefined),
    [name, setName] = useState(""),
    [answers, setAnswers] = useState<(string | null)[]>([]),
    [dirty, setDirty] = useState(false),
    [saving, setSaving] = useState(false),
    [saved, setSaved] = useState(false),
    [error, setError] = useState("");
  useEffect(() => subscribePoll(pollId, (p) => { setPoll(p); setProblem(""); }, (e) => { setPoll(null); setProblem(String(e?.code || "").includes("permission") ? "permission" : friendlyError(e)); }), [pollId]);
  useEffect(() => { ownProfileName(uid).then((n) => { setProfileName(n); if (n) setName(n); }); }, [uid]);
  useEffect(() => (poll ? subscribeResponses(pollId, setResponses, () => setResponses([])) : undefined), [pollId, !!poll]);
  const own = responses.find((r) => r.uid === uid);
  useEffect(() => {
    if (!poll) return;
    if (own && !dirty) {
      setAnswers(padAnswers(own.answers, poll.slots.length));
      if (!profileName) setName((n) => n || own.name);
    } else if (!dirty && answers.length !== poll.slots.length) setAnswers(poll.slots.map(() => null));
  }, [poll?.id, poll?.slots.length, own?.updatedAt, dirty]);
  useEffect(() => { if (profileName === null && !name) setName(displayName); }, [profileName]);
  const ranked = useMemo(() => (poll ? rankSlots(poll, responses.slice(0, 200)) : []), [poll, responses]);
  if (poll === undefined && !problem)
    return <div className="invite-loading" role="status"><LoaderCircle className="spinner" size={22} /> Opening the poll…</div>;
  if (!poll)
    return (
      <div className="invite-state">
        <span className="state-icon"><Lock size={24} /></span>
        <h1>This poll cannot be opened</h1>
        <p>
          {problem === "permission"
            ? "The organiser has not shared this poll by link, or has turned the link off. Ask the organiser for a new link."
            : problem || "The link may be incomplete, or the poll has been deleted. Check the link you received."}
        </p>
        <p className="micro">Signed in as {email}. <button className="text-button" onClick={signOutMember}>Use another account</button></p>
        <a className="btn primary" href={HOME}>Go to DACS Community <ArrowRight size={16} /></a>
      </div>
    );
  const open = poll.status === "open" && Date.parse(poll.deadline) > Date.now();
  const best = responses.length ? ranked[0]?.index : -1;
  const active = activeSlots(poll), n = poll.slots.length;
  const answered = active.filter((x) => answers[x.index]).length;
  const incomplete = open && answerIncomplete(poll, own);
  const member = !!profileName;
  const first = (member ? profileName! : name).split(" ")[0];
  async function save() {
    if (!poll) return;
    if (!name.trim()) { setError("Enter your name so the organiser knows who answered."); return; }
    setSaving(true); setError("");
    try {
      await respond(poll, completeAnswers(padAnswers(answers, n).map((v, i) => ((poll.withdrawn || []).includes(i) ? null : v))), member ? profileName! : name.trim(), zone);
      setDirty(false); setSaved(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
      toast.success("Your availability is saved.");
    } catch (e) { setError(friendlyError(e)); } finally { setSaving(false); }
  }
  const set = (i: number, v: string) => { setAnswers(padAnswers(answers, n).map((x, j) => (j === i ? v : x))); setDirty(true); };
  const setAll = (v: string | null) => { setAnswers(padAnswers(answers, n).map((x, j) => (active.some((a) => a.index === j) ? v : x))); setDirty(true); };
  const header = (
    <div className="invite-poll-head">
      <div className="eyebrow">{bodyLabel(poll.body)} · {typeLabel(poll.meetingType)}</div>
      <h1>{poll.title}</h1>
      {poll.notes && <p className="poll-notes">{poll.notes}</p>}
      <div className="poll-meta-row">
        <span className="micro"><Clock size={13} /> {poll.durationMinutes} minutes</span>
        <span className="micro"><Users size={13} /> {Math.min(responses.length, 200)} {responses.length === 1 ? "response" : "responses"}</span>
        <span className={"pill " + (open ? "green" : poll.status === "scheduled" ? "blue" : "")}>{open ? `Open · ${timeLeft(poll.deadline)}` : poll.status === "scheduled" ? "Scheduled" : "Closed"}</span>
      </div>
    </div>
  );
  if (poll.status === "scheduled") {
    const s = poll.slots[poll.selectedSlot];
    return (
      <div className="invite-vote">
        {header}
        <div className="invite-state compact">
          <span className="state-icon ok"><CalendarCheck size={24} /></span>
          <h2>The meeting has been scheduled</h2>
          {s && <p><b>{slotParts(s, poll.durationMinutes, zone).long}, {slotParts(s, poll.durationMinutes, zone).range}</b></p>}
          <p>The organiser will share the joining details with participants.</p>
          <a className="btn primary" href={HOME}>Go to DACS Community <ArrowRight size={16} /></a>
        </div>
      </div>
    );
  }
  if (saved && !dirty)
    return (
      <div className="invite-vote">
        {header}
        <div className="invite-state compact">
          <span className="state-icon ok pop"><Check size={26} /></span>
          <h2>Thank you{first ? ", " + first : ""}. Your availability is saved.</h2>
          <ul className="saved-answers">
            {active.map(({ start: s, index: i }) => {
              const v = completeAnswers(padAnswers(answers, n))[i];
              return <li key={s} className={v}><span>{slotParts(s, poll.durationMinutes, zone).long}, {slotParts(s, poll.durationMinutes, zone).range}</span><b>{v === "yes" ? "Available" : v === "if-needed" ? "If needed" : "Unavailable"}</b></li>;
            })}
          </ul>
          <p className="micro">You can change your answers until {formatDeadline(poll.deadline, zone)}.</p>
          <div className="row" style={{ justifyContent: "center" }}>
            <button className="btn" onClick={() => setSaved(false)}>Change my answers</button>
            <a className="btn primary" href={HOME}>{member ? "Open DACS Community" : "Join the community"} <ArrowRight size={16} /></a>
          </div>
          {!member && <p className="micro">Joining takes you to a short member profile so Working Groups can find your expertise. It is optional for voting.</p>}
        </div>
      </div>
    );
  return (
    <div className="invite-vote">
      {header}
      {incomplete && <div className="notice poll-incomplete"><span>New times were proposed after your answer. Please give your availability for them and save again.</span></div>}
      {!open ? (
        <div className="notice"><span>The response period ended on {formatDeadline(poll.deadline, zone)}. The results below are read-only.</span></div>
      ) : (
        <p className="invite-instructions">
          For each proposed time, choose <b>Available</b>, <b>If needed</b> or <b>Unavailable</b>, then save. Times are shown in your time zone.
        </p>
      )}
      <div className="invite-fields">
        {member ? (
          <p className="micro">Answering as <b>{profileName}</b> · {email}</p>
        ) : (
          <label className="field"><span>Your name</span><input value={name} maxLength={120} autoComplete="name" placeholder="First and last name" onChange={(e) => { setName(e.target.value); setDirty(true); }} disabled={!open} /><small>Shown to the organiser and participants with your answers.</small></label>
        )}
        <TimeZonePicker label="Your time zone" value={zone} onChange={setZone} automatic={automatic} onAutomatic={useDevice} />
      </div>
      {open && (
        <div className="vote-helper">
          <span>{answered} of {active.length} answered</span>
          <button type="button" className="text-button" onClick={() => setAll("yes")}>Available for all</button>
          <button type="button" className="text-button" onClick={() => setAll(null)}>Clear</button>
        </div>
      )}
      <div className="poll-slots">
        {active.map(({ start: s, index: i }) => {
          const r = ranked.find((x) => x.index === i);
          return <SlotCard key={s} start={s} minutes={poll.durationMinutes} zone={zone} answer={answers[i]} onAnswer={open ? (v) => set(i, v) : undefined} disabled={saving} yes={r?.yes} maybe={r?.maybe} total={Math.min(responses.length, 200)} best={best === i} />;
        })}
      </div>
      {error && <p className="error-banner" role="alert">{error}</p>}
      {open && (
        <div className="invite-save">
          <span className="micro">{answered < active.length ? "Times left blank are recorded as unavailable." : "All times answered."} Responses close {formatDeadline(poll.deadline, zone)}.</span>
          <button className="btn primary" disabled={saving} onClick={save}>
            {saving ? <LoaderCircle size={16} className="spinner" /> : <Check size={16} />}
            {own ? "Update my availability" : "Save my availability"}
          </button>
        </div>
      )}
      <p className="micro invite-account">Signed in as {email}. <button className="text-button" onClick={signOutMember}>Use another account</button></p>
    </div>
  );
}
