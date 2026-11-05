import { useState, type ReactNode } from "react";
import { Check, CircleHelp, X, Copy, Link2, Mail, Share2, Lock } from "lucide-react";
import { toast } from "sonner";
import { bodyLabel, pollInvitation, pollLink, type MeetingPoll } from "@/lib/meetings";
import { setPollLink } from "@/lib/meeting-store";
import { friendlyError } from "@/lib/store";
import { appUrl } from "@/lib/base";

export const formatDeadline = (iso: string, zone: string) =>
  new Intl.DateTimeFormat("en-GB", { timeZone: zone, weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZoneName: "short" }).format(new Date(iso));

export function timeLeft(iso: string, now = Date.now()) {
  const ms = Date.parse(iso) - now;
  if (ms <= 0) return "closed";
  const hours = Math.floor(ms / 3600000);
  if (hours < 1) return "less than an hour left";
  if (hours < 48) return hours + (hours === 1 ? " hour left" : " hours left");
  const days = Math.floor(hours / 24);
  return days + " days left";
}

export function slotParts(iso: string, minutes: number, zone: string) {
  const d = new Date(iso), end = new Date(Date.parse(iso) + minutes * 60000);
  const part = (o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-GB", { timeZone: zone, ...o }).format(d);
  const hm = (x: Date) => new Intl.DateTimeFormat("en-GB", { timeZone: zone, hour: "2-digit", minute: "2-digit" }).format(x);
  const tz = new Intl.DateTimeFormat("en-GB", { timeZone: zone, timeZoneName: "short" }).formatToParts(d).find((p) => p.type === "timeZoneName")?.value || "";
  return {
    weekday: part({ weekday: "short" }),
    day: part({ day: "numeric" }),
    month: part({ month: "short" }),
    long: part({ weekday: "long", day: "numeric", month: "long" }),
    range: `${hm(d)}–${hm(end)} ${tz}`,
  };
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const t = document.createElement("textarea");
    t.value = text;
    t.setAttribute("readonly", "");
    t.style.position = "fixed";
    t.style.opacity = "0";
    document.body.appendChild(t);
    t.select();
    let ok = false;
    try {
      ok = document.execCommand("copy");
    } catch {}
    t.remove();
    return ok;
  }
}

/** Link, copy, email and native share for a poll. Organisers can switch link access on or off. */
export function SharePoll({ poll, zone, canManage }: { poll: MeetingPoll; zone: string; canManage: boolean }) {
  const [copied, setCopied] = useState(""),
    [busy, setBusy] = useState(false);
  const link = pollLink(appUrl(), poll.id);
  const invitation = pollInvitation(poll, link, zone);
  const canShare = typeof navigator !== "undefined" && typeof navigator.share === "function";
  async function copy(kind: "link" | "message") {
    const ok = await copyText(kind === "link" ? link : invitation.text);
    if (ok) {
      setCopied(kind);
      window.setTimeout(() => setCopied(""), 2200);
    } else toast.error("Copy is not available in this browser. Select the link and copy it.");
  }
  async function toggle(on: boolean) {
    setBusy(true);
    try {
      await setPollLink(poll.id, on);
      toast.success(on ? "Link sharing is on." : "Link sharing is off. The link no longer opens this poll.");
    } catch (e) {
      toast.error(friendlyError(e));
    } finally {
      setBusy(false);
    }
  }
  if (!poll.linkAccess)
    return canManage ? (
      <div className="share-box off">
        <Lock size={20} />
        <div>
          <strong>Link sharing is off</strong>
          <p>Only invited participants of {bodyLabel(poll.body)} can open this poll.</p>
        </div>
        <button className="btn" disabled={busy} onClick={() => toggle(true)}>
          <Link2 size={15} /> Turn on link sharing
        </button>
      </div>
    ) : null;
  return (
    <div className="share-box">
      <div className="share-head">
        <span className="share-icon"><Link2 size={18} /></span>
        <div>
          <strong>Share this poll</strong>
          <p>Anyone with the link signs in or creates an account, then votes. Times appear in each person’s time zone.</p>
        </div>
      </div>
      <div className="share-row">
        <input readOnly value={link} aria-label="Poll link" onFocus={(e) => e.target.select()} />
        <button type="button" className={"btn primary" + (copied === "link" ? " copied" : "")} onClick={() => copy("link")}>
          {copied === "link" ? <Check size={16} /> : <Copy size={16} />}
          {copied === "link" ? "Copied" : "Copy link"}
        </button>
      </div>
      <div className="share-actions">
        <a className="btn small" href={invitation.mailto}>
          <Mail size={14} /> Email the invitation
        </a>
        <button type="button" className="btn small" onClick={() => copy("message")}>
          {copied === "message" ? <Check size={14} /> : <Copy size={14} />}
          {copied === "message" ? "Invitation copied" : "Copy invitation text"}
        </button>
        {canShare && (
          <button
            type="button"
            className="btn small"
            onClick={() => navigator.share({ title: invitation.subject, text: invitation.subject, url: link }).catch(() => {})}
          >
            <Share2 size={14} /> Share…
          </button>
        )}
        {canManage && (
          <button type="button" className="text-button danger share-off" disabled={busy} onClick={() => toggle(false)}>
            Turn off link
          </button>
        )}
      </div>
    </div>
  );
}

const choices = [
  { value: "yes", label: "Available", Icon: Check },
  { value: "if-needed", label: "If needed", Icon: CircleHelp },
  { value: "no", label: "Unavailable", Icon: X },
] as const;

export function VoteChoices({
  value,
  onChange,
  disabled,
  label,
}: {
  value?: string | null;
  onChange: (v: string) => void;
  disabled?: boolean;
  label: string;
}) {
  return (
    <div className="vote-choices" role="radiogroup" aria-label={label}>
      {choices.map(({ value: v, label: text, Icon }) => (
        <button
          key={v}
          type="button"
          role="radio"
          aria-checked={value === v}
          disabled={disabled}
          className={"vote-choice " + v + (value === v ? " on" : "")}
          onClick={() => onChange(v)}
        >
          <Icon size={15} />
          {text}
        </button>
      ))}
    </div>
  );
}

/** One proposed time with the voter's choice and the live count. */
export function SlotCard({
  start,
  minutes,
  zone,
  answer,
  onAnswer,
  disabled,
  yes = 0,
  maybe = 0,
  total = 0,
  best = false,
  children,
}: {
  start: string;
  minutes: number;
  zone: string;
  answer?: string | null;
  onAnswer?: (v: string) => void;
  disabled?: boolean;
  yes?: number;
  maybe?: number;
  total?: number;
  best?: boolean;
  children?: ReactNode;
}) {
  const p = slotParts(start, minutes, zone);
  return (
    <article className={"slot-card" + (best ? " best" : "") + (best && total >= 2 ? " leading" : "") + (answer ? " answered " + answer : "")}>
      {total > 0 && (
        // Snow settles on each time in proportion to the members available, and keeps falling while it gathers answers.
        <div className="slot-snow" aria-hidden="true" style={{ "--fill": Math.min(1, (yes + maybe * 0.5) / total) } as React.CSSProperties}>
          <span className="slot-drift" />
          <span className="slot-flakes">{Array.from({ length: Math.min(8, yes + maybe) }, (_, i) => <i key={i} style={{ "--k": i } as React.CSSProperties} />)}</span>
        </div>
      )}
      <div className="slot-date" aria-hidden="true">
        <span>{p.weekday}</span>
        <b>{p.day}</b>
        <span>{p.month}</span>
      </div>
      <div className="slot-main">
        <div className="slot-title">
          <strong>{p.range}</strong>
          {best && <span className="pill green">Most available</span>}
        </div>
        <span className="sr-only">{p.long}</span>
        <div className="slot-count">
          {total ? `${yes} available · ${maybe} if needed · ${total} ${total === 1 ? "response" : "responses"}` : "No responses yet"}
        </div>
        {total > 0 && (
          <div className="slot-bar" aria-hidden="true">
            <i className="yes" style={{ width: (yes / total) * 100 + "%" }} />
            <i className="maybe" style={{ width: (maybe / total) * 100 + "%" }} />
          </div>
        )}
        {children}
      </div>
      {onAnswer && <VoteChoices value={answer} onChange={onAnswer} disabled={disabled} label={"Your availability on " + p.long + ", " + p.range} />}
    </article>
  );
}
