import { useEffect, useMemo, useState } from "react";
import { Check, ChevronLeft, ChevronRight, Plus, X } from "lucide-react";
import { localInput, timeCandidates } from "@/lib/calendar";

const timeChips = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00"];
const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const addDays = (ymd: string, n: number) => { const d = new Date(ymd + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const monthOf = (ymd: string) => ymd.slice(0, 7);
const shiftMonth = (ym: string, n: number) => { const d = new Date(ym + "-15T12:00:00Z"); d.setUTCMonth(d.getUTCMonth() + n); return d.toISOString().slice(0, 7); };
const dayLabel = (ymd: string, o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("en-GB", { timeZone: "UTC", ...o }).format(new Date(ymd + "T12:00:00Z"));

/** The instant of a clock time on a day in a time zone, or "" when it does not exist or repeats (clock changes). */
function instant(day: string, time: string, zone: string) { const c = timeCandidates(`${day}T${time}`, zone); return c.length === 1 ? c[0] : ""; }

/**
 * Choose several days in a month view, then the start times: each time is proposed on every selected day.
 * `slots` are the times proposed in this picker; `locked` are times that already exist (shown on the calendar, not removable here).
 */
export function SlotPicker({ zone, slots, onChange, max, locked = [], onError }: { zone: string; slots: string[]; onChange: (s: string[]) => void; max: number; locked?: string[]; onError: (m: string) => void }) {
  const today = localInput(new Date(), zone).slice(0, 10);
  const [days, setDays] = useState<string[]>(() => [addDays(today, 1)]);
  const [month, setMonth] = useState(monthOf(addDays(today, 1)));
  const [custom, setCustom] = useState("");
  useEffect(() => { setDays((d) => d.filter((x) => x >= today)); }, [zone]);
  const all = [...locked, ...slots];
  const dayOf = (s: string) => localInput(s, zone).slice(0, 10);
  const usedDays = useMemo(() => new Set(all.map(dayOf)), [all.join("|"), zone]);
  const sorted = [...days].sort();

  // Month grid starting on Monday.
  const first = month + "-01", offset = (new Date(first + "T12:00:00Z").getUTCDay() + 6) % 7;
  const cells = Array.from({ length: 42 }, (_, i) => addDays(first, i - offset));
  const rows = cells.slice(35).every((c) => monthOf(c) !== month) ? cells.slice(0, 35) : cells;

  function toggleDay(d: string) { onError(""); setDays(days.includes(d) ? days.filter((x) => x !== d) : [...days, d]); }
  function chipState(time: string) {
    const at = sorted.map((d) => instant(d, time, zone)).filter(Boolean);
    const on = at.filter((s) => all.includes(s)).length;
    return { at, state: !at.length ? "none" : on === 0 ? "off" : on === at.length ? "on" : "some" };
  }
  function apply(time: string) {
    onError("");
    if (!sorted.length) { onError("Select at least one day in the calendar first."); return; }
    const { at, state } = chipState(time);
    if (state === "on") { onChange(slots.filter((s) => !at.includes(s))); return; }
    const future = at.filter((s) => Date.parse(s) > Date.now() && !all.includes(s));
    const skipped = sorted.length - at.length;
    const room = max - (locked.length + slots.length);
    if (future.length > room) { onError(room <= 0 ? `A poll can propose up to ${max} times.` : `Only ${room} more ${room === 1 ? "time fits" : "times fit"} (up to ${max}). Select fewer days.`); return; }
    onChange([...slots, ...future]);
    if (skipped > 0) onError(`${time} does not exist or repeats on ${skipped === 1 ? "one of the selected days" : skipped + " of the selected days"} because of a clock change. Use another time for ${skipped === 1 ? "that day" : "those days"}.`);
  }
  function addCustom() { if (/^\d{2}:\d{2}$/.test(custom)) { apply(custom); setCustom(""); } }
  function quick(kind: "week" | "next") {
    onError("");
    const start = kind === "week" ? addDays(today, 1) : addDays(today, 7 - ((new Date(today + "T12:00:00Z").getUTCDay() + 6) % 7));
    const picked: string[] = [];
    for (let i = 0; picked.length < 5 && i < 14; i++) { const d = addDays(start, i), wd = new Date(d + "T12:00:00Z").getUTCDay(); if (wd !== 0 && wd !== 6) picked.push(d); }
    setDays(picked); setMonth(monthOf(picked[0]));
  }
  const customState = /^\d{2}:\d{2}$/.test(custom) ? chipState(custom).state : "none";

  return (
    <div className="slot-picker multi">
      <div className="mini-cal" aria-label="Days to propose">
        <div className="mini-cal-head">
          <button type="button" className="icon-btn" aria-label="Previous month" disabled={month <= monthOf(today)} onClick={() => setMonth(shiftMonth(month, -1))}><ChevronLeft size={16} /></button>
          <strong>{dayLabel(first, { month: "long", year: "numeric" })}</strong>
          <button type="button" className="icon-btn" aria-label="Next month" onClick={() => setMonth(shiftMonth(month, 1))}><ChevronRight size={16} /></button>
        </div>
        <div className="mini-cal-grid" role="grid">
          {weekdays.map((w) => <span key={w} className="mini-cal-wd" aria-hidden="true">{w.slice(0, 2)}</span>)}
          {rows.map((d) => {
            const past = d < today, sel = days.includes(d), other = monthOf(d) !== month;
            return (
              <button type="button" key={d} disabled={past} aria-pressed={sel} aria-label={dayLabel(d, { weekday: "long", day: "numeric", month: "long" }) + (sel ? ", selected" : "")}
                className={"mini-cal-day" + (sel ? " on" : "") + (other ? " other" : "") + (d === today ? " today" : "") + (usedDays.has(d) ? " used" : "")} onClick={() => toggleDay(d)}>
                {Number(d.slice(-2))}
              </button>
            );
          })}
        </div>
        <div className="mini-cal-quick">
          <button type="button" className="text-button" onClick={() => quick("week")}>Next 5 working days</button>
          <button type="button" className="text-button" onClick={() => quick("next")}>Next week, Monday to Friday</button>
          {days.length > 0 && <button type="button" className="text-button" onClick={() => setDays([])}>Clear</button>}
        </div>
      </div>
      <div className="field slot-times">
        <span>{sorted.length === 0 ? "Select one or more days" : sorted.length === 1 ? `Start times on ${dayLabel(sorted[0], { weekday: "long", day: "numeric", month: "long" })}` : `Start times on each of the ${sorted.length} selected days`}</span>
        {sorted.length > 1 && <div className="selected-days">{sorted.map((d) => <span className="chip on removable small" key={d}>{dayLabel(d, { weekday: "short", day: "numeric", month: "short" })}<button type="button" aria-label={"Unselect " + d} onClick={() => toggleDay(d)}><X size={12} /></button></span>)}</div>}
        <div className="time-chips">
          {timeChips.map((t) => {
            const { state } = chipState(t);
            const allPast = sorted.length > 0 && sorted.every((d) => { const a = instant(d, t, zone); return !a || Date.parse(a) <= Date.now(); });
            return (
              <button type="button" key={t} disabled={!sorted.length || allPast} className={"chip time" + (state === "on" ? " on" : state === "some" ? " some" : "")} aria-pressed={state === "on"} onClick={() => apply(t)}
                title={state === "some" ? "Proposed on some of the selected days. Select to add it to all of them." : undefined}>
                {state === "on" && <Check size={13} />}{t}
              </button>
            );
          })}
        </div>
        <div className="custom-time"><span className="micro">Another time</span><input type="time" aria-label="Another start time" value={custom} onChange={(e) => setCustom(e.target.value)} /><button type="button" className="btn small" disabled={!custom || !sorted.length || customState === "on"} onClick={addCustom}><Plus size={14} /> Add{sorted.length > 1 ? " to each day" : ""}</button></div>
        <p className="micro">Select several days in the calendar, then click a time to propose it on every selected day. Click it again to remove it from those days.</p>
      </div>
    </div>
  );
}
