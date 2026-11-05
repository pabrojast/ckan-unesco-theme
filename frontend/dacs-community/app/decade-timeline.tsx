import { useEffect, useMemo, useRef, useState } from "react";
import { BookMarked, CalendarDays, ChevronLeft, ChevronRight, LocateFixed } from "lucide-react";
import { subscribeDecisions, type Decision } from "@/lib/coordination-store";
import { triennia } from "@/lib/flagship";
import { bodyLevel, type MeetingAccess } from "@/lib/meetings";
import { eventAccent } from "@/lib/event-style";
import type { CalendarEvent } from "@/lib/calendar";

const START = Date.UTC(2025, 0, 1), END = Date.UTC(2035, 0, 1), YEAR_PX = 480;
const WIDTH = 10 * YEAR_PX;
const x = (t: number) => ((t - START) / (END - START)) * WIDTH;
const day = (v: string) => new Date(v).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

type Item = { id: string; kind: "event" | "decision"; t: number; title: string; sub: string; color: string; onOpen: () => void };

/**
 * The Decade from 2025 to 2034 as a horizontal timeline: the three triennia as layers of ice, a marker for today, and the
 * events of the calendar (above) and the decisions of the register (below), placed at their dates.
 */
export function DecadeTimeline({ access, events, onOpenEvent, onOpenDecisions }: { access: MeetingAccess; events: CalendarEvent[]; onOpenEvent: (id: string) => void; onOpenDecisions: () => void }) {
  const [decisions, setDecisions] = useState<Decision[]>([]);
  useEffect(() => subscribeDecisions(["smc", "esc"].map((b) => ({ body: b, member: bodyLevel(access, b) >= 1 })), setDecisions, () => setDecisions([])), [access.uid]);
  const scroller = useRef<HTMLDivElement>(null), [openGroup, setOpenGroup] = useState("");
  const now = Date.now(), nowX = x(Math.min(END, Math.max(START, now)));
  const items = useMemo(() => {
    const out: Item[] = [];
    for (const e of events) {
      const t = Date.parse(e.startAt);
      if (t >= START && t < END) out.push({ id: "e" + e.id, kind: "event", t, title: e.title, sub: day(e.startAt), color: eventAccent(e as any).color, onOpen: () => onOpenEvent(e.id) });
    }
    for (const d of decisions) {
      const t = Date.parse(d.date + "T12:00:00Z");
      if (t >= START && t < END) out.push({ id: "d" + d.id, kind: "decision", t, title: `${d.reference ? d.reference + " · " : ""}${d.title}`, sub: `${d.body.toUpperCase()} · ${day(d.date + "T12:00:00Z")}`, color: d.body === "esc" ? "#0a6eb4" : "#00afd0", onOpen: onOpenDecisions });
    }
    // Items closer than a label's width are gathered in one marker, which opens the list; markers alternate over three rows.
    const groups: { id: string; kind: Item["kind"]; px: number; items: Item[] }[] = [];
    for (const kind of ["event", "decision"] as const) {
      let cur: (typeof groups)[number] | null = null;
      for (const it of out.filter((o) => o.kind === kind).sort((a, b) => a.t - b.t)) {
        const px = x(it.t);
        if (cur && px - cur.px < 46) cur.items.push(it);
        else { cur = { id: it.id, kind, px, items: [it] }; groups.push(cur); }
      }
    }
    const lastEnd: Record<string, number[]> = { event: [-1e9, -1e9, -1e9], decision: [-1e9, -1e9, -1e9] };
    return groups.sort((a, b) => a.px - b.px).map((g) => {
      const ends = lastEnd[g.kind];
      let row = ends.findIndex((e) => e < g.px - 6);
      if (row < 0) row = ends.indexOf(Math.min(...ends));
      ends[row] = g.px + 180;
      return { ...g, row };
    });
  }, [events, decisions]);

  // Open on today; items appear one after the other, from today outwards (see .tl-item in globals.css).
  useEffect(() => { const el = scroller.current; if (el) el.scrollLeft = Math.max(0, nowX - el.clientWidth * 0.35); }, []);
  const by = (px: number) => scroller.current?.scrollBy({ left: px, behavior: "smooth" });
  const today = () => { const el = scroller.current; if (el) el.scrollTo({ left: Math.max(0, nowX - el.clientWidth * 0.35), behavior: "smooth" }); };
  // Turn the mouse wheel into horizontal travel.
  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const wheel = (e: WheelEvent) => { if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) { el.scrollLeft += e.deltaY; e.preventDefault(); } };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => el.removeEventListener("wheel", wheel);
  }, []);
  const layers = [{ n: 0, label: "Start of the Decade", period: "2025", from: 2025, to: 2025 }, ...triennia.map((t) => ({ n: t.n, label: t.label, period: t.period, from: t.from, to: t.to }))];
  return (
    <section className="glass panel decade-timeline">
      <div className="tl-head">
        <div><h2>The Decade, 2025 to 2034</h2><p className="micro">Events of the calendar above the line, decisions of the SMC and the ESC below. Scroll sideways or use the arrows.</p></div>
        <div className="tl-tools">
          <span className="tl-legend"><i className="ev" /> Events <i className="dc" /> Decisions</span>
          <button type="button" className="btn small" onClick={() => by(-YEAR_PX * 1.5)} aria-label="Earlier"><ChevronLeft size={16} /></button>
          <button type="button" className="btn small" onClick={today}><LocateFixed size={15} /> Today</button>
          <button type="button" className="btn small" onClick={() => by(YEAR_PX * 1.5)} aria-label="Later"><ChevronRight size={16} /></button>
        </div>
      </div>
      <div className="tl-scroller" ref={scroller} tabIndex={0} aria-label="Timeline of the Decade, scroll sideways">
        <div className="tl-track" style={{ width: WIDTH }}>
          <div className="tl-layers" aria-hidden="true">
            {layers.map((l) => (
              <div key={l.n} className={"tl-layer l" + l.n + (now >= Date.UTC(l.from, 0, 1) && now < Date.UTC(l.to + 1, 0, 1) ? " current" : "")} style={{ left: x(Date.UTC(l.from, 0, 1)), width: x(Date.UTC(l.to + 1, 0, 1)) - x(Date.UTC(l.from, 0, 1)) }}>
                <span><b>{l.label}</b>{l.period}</span>
              </div>
            ))}
          </div>
          <div className="tl-axis">{Array.from({ length: 11 }, (_, i) => <span key={i} style={{ left: i * YEAR_PX }}>{2025 + i < 2035 ? 2025 + i : ""}</span>)}</div>
          {now >= START && now < END && <div className="tl-now" style={{ left: nowX }}><span>Today</span><i className="tl-now-snow" /></div>}
          {items.map((g) => {
            const one = g.items[0], many = g.items.length > 1, isOpen = openGroup === g.id;
            return (
              <div key={g.id} className={`tl-item ${g.kind} row${g.row}` + (isOpen ? " open" : "")} style={{ left: g.px, "--c": one.color, "--d": Math.min(20, Math.round(Math.abs(g.px - nowX) / 120)) } as React.CSSProperties}>
                <button type="button" className="tl-hit" onClick={() => (many ? setOpenGroup(isOpen ? "" : g.id) : one.onOpen())} aria-expanded={many ? isOpen : undefined}
                  title={many ? `${g.items.length} ${g.kind === "event" ? "events" : "decisions"}` : `${one.title} · ${one.sub}`}>
                  <span className="tl-pin">{g.kind === "event" ? <CalendarDays size={12} /> : <BookMarked size={12} />}{many && <em>{g.items.length}</em>}</span>
                  <span className="tl-label"><b>{many ? `${g.items.length} ${g.kind === "event" ? "events" : "decisions"}` : one.title}</b><small>{many ? `${g.items[0].sub.split(" · ").pop()} to ${g.items[g.items.length - 1].sub.split(" · ").pop()}` : one.sub}</small></span>
                </button>
                {isOpen && (
                  <div className="tl-pop">{g.items.map((it) => (
                    <button key={it.id} type="button" onClick={() => { setOpenGroup(""); it.onOpen(); }} style={{ "--c": it.color } as React.CSSProperties}><i /><span><b>{it.title}</b><small>{it.sub}</small></span></button>
                  ))}</div>
                )}
              </div>
            );
          })}
          {!items.length && <p className="tl-empty micro" style={{ left: nowX + 20 }}>Events and decisions appear here as they are added to the calendar and the register.</p>}
        </div>
      </div>
    </section>
  );
}
