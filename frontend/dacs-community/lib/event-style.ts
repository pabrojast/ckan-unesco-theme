// Colours of calendar events and meetings.
// A Working Group meeting takes its Working Group's colour. A meeting of another governing body takes the
// colour of its space under Governance. A public event takes the colour of the Working Group of its
// Overarching Challenge; an event linked to several challenges shows their colours side by side.
import { groups } from "./data.ts";
import { bodySpaces } from "./body-spaces.ts";
import { localInput } from "./calendar.ts";
import type { CSSProperties } from "react";

export type EventAccent = { color: string; ink: string; stripe: string; stripeV?: string; tag: string };
const brand = { color: "#0a6eb4", ink: "#0a5a94" };

export function groupColor(n: number) {
  const g = groups.find((x) => x.id === n);
  return g ? { color: g.color, ink: g.ink } : brand;
}

export function eventAccent(e: { body?: string; ocs?: number[] }): EventAccent {
  const body = e.body || "";
  const wg = /^wg([1-5])$/.exec(body);
  if (wg) {
    const n = Number(wg[1]), g = groups[n - 1];
    return { color: g.color, ink: g.ink, stripe: g.color, tag: `WG${n} · ${g.short}` };
  }
  const space = body ? bodySpaces.find((b) => b.id === body) : undefined;
  if (space) return { color: space.color, ink: space.color, stripe: space.color, tag: space.short };
  const ocs = [...new Set(e.ocs || [])].filter((n) => n >= 1 && n <= 5).sort();
  if (ocs.length === 1) {
    const g = groups[ocs[0] - 1];
    return { color: g.color, ink: g.ink, stripe: g.color, tag: `OC${ocs[0]} · ${g.short}` };
  }
  if (ocs.length > 1) {
    const stops = ocs.map((n, i) => `${groups[n - 1].color} ${(i / ocs.length) * 100}% ${((i + 1) / ocs.length) * 100}%`);
    return { ...brand, stripe: `linear-gradient(90deg, ${stops.join(", ")})`, stripeV: `linear-gradient(180deg, ${stops.join(", ")})`, tag: ocs.length === 5 ? "Decade-wide" : ocs.map((n) => `OC${n}`).join(" · ") };
  }
  return { ...brand, stripe: brand.color, tag: "Decade event" };
}

/** CSS custom properties for an element showing an event. */
export const accentStyle = (e: { body?: string; ocs?: number[] }) => {
  const a = eventAccent(e);
  return { "--ev": a.color, "--ev-ink": a.ink, "--ev-stripe": a.stripe, "--ev-stripe-v": a.stripeV || a.stripe } as CSSProperties;
};

/** Relative status of an event at a given time. */
export function eventTiming(startAt: string, endAt: string, zone: string, now = Date.now()) {
  const s = Date.parse(startAt), e = Date.parse(endAt);
  if (now >= s && now < e) return { state: "live" as const, label: "Happening now" };
  if (now >= e) return { state: "past" as const, label: "Past" };
  const day = (t: number) => Date.parse(localInput(new Date(t), zone).slice(0, 10) + "T00:00:00Z");
  const days = Math.round((day(s) - day(now)) / 86400000);
  if (days <= 0) return { state: "soon" as const, label: "Today" };
  if (days === 1) return { state: "soon" as const, label: "Tomorrow" };
  return { state: "upcoming" as const, label: `In ${days} days` };
}

export function durationLabel(startAt: string, endAt: string) {
  const m = Math.round((Date.parse(endAt) - Date.parse(startAt)) / 60000);
  if (!Number.isFinite(m) || m <= 0) return "";
  if (m < 60) return `${m} min`;
  if (m % 60 === 0) return m / 60 === 1 ? "1 hour" : m >= 1440 && m % 1440 === 0 ? `${m / 1440} day${m === 1440 ? "" : "s"}` : `${m / 60} hours`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}
