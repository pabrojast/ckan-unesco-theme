import { useEffect, useState } from "react";
import { Check, Download, Laptop, MapPin, UserCheck, Users, X } from "lucide-react";
import { toast } from "sonner";
import type { CalendarEvent } from "@/lib/calendar";
import { bodyLevel, type MeetingAccess } from "@/lib/meetings";
import { friendlyError } from "@/lib/store";
import { attend, cancelAttendance, subscribeAttendance, type Attendance } from "@/lib/task-store";
import { MemberAvatar } from "./member-avatar";

/** An event can be attended in person when it has a place that is not only "online". */
export const hasVenue = (e: Pick<CalendarEvent, "location">) => !!e.location?.trim() && !/^(online|virtual|en ligne|teams|zoom)\.?$/i.test(e.location.trim());

function csvCell(v: string) { return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; }

/** "I will attend" for members, and the list of people attending, with a CSV export for the organisers. */
export function EventAttendance({ event, access, people, canSee }: { event: CalendarEvent; access: MeetingAccess; people: any[]; canSee: boolean }) {
  const [list, setList] = useState<Attendance[] | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(""), [all, setAll] = useState(false);
  const me = access.uid, name = access.profile?.name || "";
  useEffect(() => { setList(null); setError(""); if (!canSee || !access.profile) return; return subscribeAttendance(event.id, setList, (e) => setError(friendlyError(e))); }, [event.id, canSee, !!access.profile]);
  if (!canSee || !access.profile) return null;
  const ended = Date.parse(event.endAt) <= Date.now();
  const mine = list?.find((a) => a.id === me);
  const venue = hasVenue(event), online = !!event.joinUrl || !venue || /online|hybrid|virtual/i.test(event.location || "");
  const organiser = access.admin || event.owner === me || (!!event.body && bodyLevel(access, event.body) >= 2);
  const inPerson = (list || []).filter((a) => a.mode === "in-person"), remote = (list || []).filter((a) => a.mode === "online");
  async function choose(mode: Attendance["mode"]) {
    setBusy(true); setError("");
    try { await attend(event.id, name, mode); toast.success(mode === "in-person" ? "You are registered to attend in person." : "You are registered to attend online."); }
    catch (e) { setError(friendlyError(e)); } finally { setBusy(false); }
  }
  async function cancel() {
    setBusy(true); setError("");
    try { await cancelAttendance(event.id); toast.success("Your sign-up has been cancelled."); } catch (e) { setError(friendlyError(e)); } finally { setBusy(false); }
  }
  function exportCsv() {
    const rows = [["Name", "Attendance", "Signed up (UTC)"], ...(list || []).sort((a, b) => a.name.localeCompare(b.name)).map((a) => [a.name, a.mode === "in-person" ? "In person" : "Online", a.at.slice(0, 16).replace("T", " ")])];
    const blob = new Blob(["﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `attendance-${event.title.replace(/[^\p{L}\p{N} _-]+/gu, "").trim().slice(0, 50) || event.id}.csv`; a.click(); URL.revokeObjectURL(a.href);
  }
  const person = (a: Attendance) => people.find((p) => p.id === a.id) || { id: a.id, name: a.name };
  const shown = all ? list || [] : (list || []).slice(0, 12);
  return (
    <section className="event-section attendance">
      <h3><UserCheck size={16} /> Attendance <span className="pill">{list?.length || 0}</span></h3>
      {!ended && (mine ? (
        <div className="attend-status">
          <span className="attend-yes"><Check size={16} /> You will attend {mine.mode === "in-person" ? "in person" : "online"}</span>
          {venue && online && <button type="button" className="text-button" disabled={busy} onClick={() => choose(mine.mode === "in-person" ? "online" : "in-person")}>Switch to {mine.mode === "in-person" ? "online" : "in person"}</button>}
          <button type="button" className="text-button danger" disabled={busy} onClick={cancel}><X size={13} /> Cancel my sign-up</button>
        </div>
      ) : (
        <div className="attend-choice">
          <span>Will you attend?</span>
          {venue && <button type="button" className="btn primary" disabled={busy} onClick={() => choose("in-person")}><MapPin size={15} /> I will attend in person</button>}
          {online && <button type="button" className={venue ? "btn" : "btn primary"} disabled={busy} onClick={() => choose("online")}><Laptop size={15} /> I will attend online</button>}
        </div>
      ))}
      {ended && <p className="micro">This event has ended. Sign-ups are closed.</p>}
      {error && <p className="error-banner" role="alert">{error}</p>}
      {list && list.length > 0 && (
        <>
          <p className="micro attend-split">{venue && online ? `${inPerson.length} in person · ${remote.length} online` : `${list.length} ${list.length === 1 ? "person" : "people"} signed up`}</p>
          <div className="attend-list">
            {shown.map((a) => { const p = person(a); return (
              <span className="attend-person" key={a.id} title={a.mode === "in-person" ? "In person" : "Online"}>
                <MemberAvatar name={p.name} uid={p.id} hasPhoto={p.hasPhoto} version={p.updatedAt} />
                <span>{a.name}<small>{a.mode === "in-person" ? <><MapPin size={11} /> In person</> : <><Laptop size={11} /> Online</>}</small></span>
              </span>); })}
          </div>
          {list.length > 12 && <button type="button" className="text-button" onClick={() => setAll(!all)}>{all ? "Show fewer" : `Show all ${list.length}`}</button>}
        </>
      )}
      {list && !list.length && <p className="micro"><Users size={13} /> Nobody has signed up yet.</p>}
      {organiser && list && list.length > 0 && <button type="button" className="btn small attend-export" onClick={exportCsv}><Download size={14} /> Attendance list (CSV)</button>}
    </section>
  );
}
