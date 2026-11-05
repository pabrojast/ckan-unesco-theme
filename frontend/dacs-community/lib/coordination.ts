// Pure helpers for minutes and actions, work plans, the Secretariat dashboard, calendar files,
// consultations, the weekly digest and the members map. No Firebase imports: tested with node --test.
import { countryCentroids } from "./country-centroids.ts";

/* ---------- Calendar files ---------- */
export type IcsEvent = { id: string; title: string; description?: string; location?: string; startAt: string; endAt: string; url?: string };
const icsStamp = (iso: string) => new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
const icsText = (s: string) => s.replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
/** Folds content lines at 75 octets as required by RFC 5545. */
function fold(line: string) {
  const bytes = new TextEncoder().encode(line);
  if (bytes.length <= 75) return line;
  const parts: string[] = [];
  let current = "", size = 0;
  for (const ch of line) {
    const n = new TextEncoder().encode(ch).length;
    if (size + n > (parts.length ? 74 : 75)) {
      parts.push(current);
      current = "";
      size = 0;
    }
    current += ch;
    size += n;
  }
  parts.push(current);
  return parts.join("\r\n ");
}
export function buildIcs(events: IcsEvent[], now = new Date()) {
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//DACS Community//Decade calendar//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"];
  for (const e of events) {
    const description = [e.description || "", e.url ? "DACS Community: " + e.url : ""].filter(Boolean).join("\n\n");
    lines.push(
      "BEGIN:VEVENT",
      "UID:" + e.id + "@dacs-community",
      "DTSTAMP:" + icsStamp(now.toISOString()),
      "DTSTART:" + icsStamp(e.startAt),
      "DTEND:" + icsStamp(e.endAt),
      "SUMMARY:" + icsText(e.title),
    );
    if (description) lines.push("DESCRIPTION:" + icsText(description));
    if (e.location) lines.push("LOCATION:" + icsText(e.location));
    if (e.url) lines.push("URL:" + e.url);
    lines.push("END:VEVENT");
  }
  lines.push("END:VCALENDAR");
  return lines.map(fold).join("\r\n") + "\r\n";
}
const compact = (iso: string) => new Date(iso).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
export function googleCalendarUrl(e: IcsEvent) {
  const p = new URLSearchParams({ action: "TEMPLATE", text: e.title, dates: compact(e.startAt) + "/" + compact(e.endAt), details: [e.description || "", e.url || ""].filter(Boolean).join("\n\n"), location: e.location || "" });
  return "https://calendar.google.com/calendar/render?" + p.toString();
}
export function outlookCalendarUrl(e: IcsEvent) {
  const p = new URLSearchParams({ path: "/calendar/action/compose", rru: "addevent", subject: e.title, startdt: new Date(e.startAt).toISOString(), enddt: new Date(e.endAt).toISOString(), body: [e.description || "", e.url || ""].filter(Boolean).join("\n\n"), location: e.location || "" });
  return "https://outlook.office.com/calendar/0/deeplink/compose?" + p.toString();
}

/* ---------- Counting, CSV and dates ---------- */
export function tally<T>(items: T[], key: (item: T) => string | string[] | undefined, order: string[] = []) {
  const counts = new Map<string, number>();
  for (const item of items) {
    const raw = key(item);
    const values = Array.isArray(raw) ? raw : [raw];
    for (const v of new Set(values.map((x) => (x || "").trim() || "Not stated"))) counts.set(v, (counts.get(v) || 0) + 1);
  }
  const rank = (k: string) => (order.includes(k) ? order.indexOf(k) : order.length);
  return [...counts.entries()].sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1] || a[0].localeCompare(b[0]));
}
export function toCsv(rows: (string | number | null | undefined)[][]) {
  const cell = (v: string | number | null | undefined) => {
    const s = v === null || v === undefined ? "" : String(v);
    const safe = /^[=+\-@\t\r]/.test(s) ? "'" + s : s; // keep spreadsheet formulas from running
    return /[",\n\r;]/.test(safe) ? '"' + safe.replace(/"/g, '""') + '"' : safe;
  };
  return "\ufeff" + rows.map((r) => r.map(cell).join(",")).join("\r\n") + "\r\n";
}
export const ymd = (d: Date) => d.toISOString().slice(0, 10);
/** Working days (Monday to Friday) after `from` up to `to`, as counted by the logo review desk. */
export function workingDays(from: string, to = new Date()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(from || "")) return null;
  const d = new Date(from + "T00:00:00Z"), end = new Date(ymd(to) + "T00:00:00Z");
  let n = 0;
  while (d < end) {
    d.setUTCDate(d.getUTCDate() + 1);
    const w = d.getUTCDay();
    if (w !== 0 && w !== 6) n++;
  }
  return n;
}
export const daysBetween = (fromIso: string, to = Date.now()) => Math.floor((to - Date.parse(fromIso)) / 86400000);
/** Open logo requests and their position against the 40 working-day target (Level 1 only, outside "awaiting applicant"). */
export function logoDeadlines(requests: any[], now = new Date(), target = 40, warnFrom = 30) {
  return requests
    .filter((r) => !["decided", "notified", "closed"].includes(r.stage))
    .map((r) => {
      const days = workingDays(r.receivedAt, now);
      const level = r.assess?.level || "";
      const counted = r.stage !== "applicant" && level !== "Level 2" && level !== "Level 3" && days !== null;
      return { id: r.id, title: r.sub?.title || r.id, organisation: r.sub?.organisation || "", stage: r.stage || "", receivedAt: r.receivedAt || "", days, counted,
        state: !counted ? "paused" : (days as number) > target ? "late" : (days as number) >= warnFrom ? "near" : "ok" };
    })
    .sort((a, b) => (b.days || 0) - (a.days || 0));
}

/* ---------- Actions ---------- */
export type ActionItem = { id: string; eventId: string; body: string; meetingType: string; title: string; owner: string; owner_name: string; due: string; status: "open" | "done"; createdBy: string; createdAt: string; updatedAt: string };
export function actionState(a: Pick<ActionItem, "status" | "due">, today = ymd(new Date())) {
  if (a.status === "done") return "done";
  if (!a.due) return "open";
  if (a.due < today) return "overdue";
  const soon = new Date(today + "T00:00:00Z");
  soon.setUTCDate(soon.getUTCDate() + 7);
  return a.due <= ymd(soon) ? "soon" : "open";
}
export const sortActions = (items: ActionItem[]) =>
  [...items].sort((a, b) => Number(a.status === "done") - Number(b.status === "done") || (a.due || "9999").localeCompare(b.due || "9999") || a.title.localeCompare(b.title));

/* ---------- Work plans ---------- */
export type WorkItem = { id: string; body: string; kind: "deliverable" | "milestone"; title: string; mg: string; due: string; status: "planned" | "in-progress" | "done" | "delayed"; lead: string; notes: string; updatedAt: string; createdAt: string; parent?: string; updatedBy?: string };
export const workStatuses = [
  { id: "planned", label: "Planned" },
  { id: "in-progress", label: "In progress" },
  { id: "delayed", label: "Delayed" },
  { id: "done", label: "Completed" },
] as const;
export function workProgress(items: Pick<WorkItem, "status">[]) {
  const total = items.length, done = items.filter((i) => i.status === "done").length;
  return { total, done, delayed: items.filter((i) => i.status === "delayed").length, inProgress: items.filter((i) => i.status === "in-progress").length, percent: total ? Math.round((done / total) * 100) : 0 };
}

/* ---------- Consultations ---------- */
export type ConsultationQuestion = { id: string; kind: "yesno" | "choice" | "text"; label: string; options: string[] };
export const yesNoOptions = ["Yes", "No", "Abstain"];
export function questionOptions(q: ConsultationQuestion) {
  return q.kind === "yesno" ? yesNoOptions : q.kind === "choice" ? q.options : [];
}
export function tallyConsultation(questions: ConsultationQuestion[], answers: { answers: Record<string, string> }[]) {
  return questions.map((q) => {
    const given = answers.map((a) => (a.answers || {})[q.id]).filter((v) => typeof v === "string" && v.trim() !== "");
    if (q.kind === "text") return { question: q, total: given.length, counts: [] as [string, number][], texts: given };
    const options = questionOptions(q);
    return { question: q, total: given.length, counts: options.map((o) => [o, given.filter((v) => v === o).length] as [string, number]), texts: [] as string[] };
  });
}
export function consultationError(v: { title: string; questions: ConsultationQuestion[]; deadline: string }) {
  if (!v.title.trim()) return "Enter a title.";
  if (!v.questions.length || v.questions.length > 10) return "Add between one and ten questions.";
  for (const [i, q] of v.questions.entries()) {
    if (!q.label.trim()) return `Write question ${i + 1}.`;
    if (q.kind === "choice" && (q.options.filter((o) => o.trim()).length < 2 || q.options.length > 8)) return `Question ${i + 1} needs two to eight options.`;
    if (q.kind === "choice" && new Set(q.options.map((o) => o.trim())).size !== q.options.length) return `Question ${i + 1} has a repeated option.`;
  }
  if (!Number.isFinite(Date.parse(v.deadline)) || Date.parse(v.deadline) <= Date.now()) return "Choose a closing date in the future.";
  return "";
}

/* ---------- Weekly digest ---------- */
export type DigestInput = { since: Date; until: Date; people: any[]; posts: any[]; events: any[]; opportunities: any[]; appUrl: string; groupLabel: (wg: number) => string };
const fmt = (iso: string) => new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
export function buildDigest(v: DigestInput) {
  const inRange = (iso: string) => Date.parse(iso) >= v.since.getTime() && Date.parse(iso) <= v.until.getTime();
  const ahead = new Date(v.until.getTime() + 21 * 86400000);
  const members = v.people.filter((p) => p.createdAt && inRange(p.createdAt)).sort((a, b) => a.name.localeCompare(b.name));
  const news = v.posts.filter((p) => (p.createdAt || p.created_at) && inRange(p.createdAt || p.created_at)).sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
  const upcoming = v.events.filter((e) => Date.parse(e.startAt) > v.until.getTime() - 86400000 && Date.parse(e.startAt) <= ahead.getTime()).sort((a, b) => a.startAt.localeCompare(b.startAt));
  const calls = v.opportunities.filter((o) => o.status === "open").sort((a, b) => String(b.createdAt).localeCompare(String(a.createdAt)));
  const period = `${fmt(v.since.toISOString())} – ${fmt(v.until.toISOString())}`;
  const sections: { title: string; items: { line: string; detail?: string }[] }[] = [
    { title: "New members", items: members.map((p) => ({ line: p.name, detail: [p.headline, p.organisation, p.country].filter(Boolean).join(" · ") })) },
    { title: "News", items: news.map((p) => ({ line: p.title || String(p.body || "").slice(0, 90), detail: `${p.author_name}${p.wg ? " · " + v.groupLabel(p.wg) : ""}` })) },
    { title: "Upcoming meetings and events (next three weeks)", items: upcoming.map((e) => ({ line: e.title, detail: `${new Date(e.startAt).toLocaleString("en-GB", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", timeZone: "UTC" })} UTC${e.location ? " · " + e.location : ""}` })) },
    { title: "Open calls for contributions", items: calls.map((o) => ({ line: o.title, detail: `${v.groupLabel(o.wg)}${o.deadline ? " · deadline " + fmt(o.deadline + "T00:00:00Z") : ""}` })) },
  ];
  const text = [
    "DACS Community · Weekly digest",
    period,
    "",
    ...sections.flatMap((s) => [s.title.toUpperCase(), ...(s.items.length ? s.items.map((i) => "• " + i.line + (i.detail ? " — " + i.detail : "")) : ["• None this period"]), ""]),
    "Open the DACS Community: " + v.appUrl,
  ].join("\n");
  const html = `<div style="font-family:'Myriad Pro',Myriad,'Segoe UI',Arial,sans-serif;color:#16202e;line-height:1.5;max-width:640px">`
    + `<p style="margin:0;font-size:12px;font-weight:700;letter-spacing:1.4px;text-transform:uppercase;color:#0a6eb4">DACS Community · Weekly digest</p>`
    + `<p style="margin:2px 0 16px;color:#5a6a7c">${esc(period)}</p>`
    + sections.map((s) => `<h3 style="margin:18px 0 6px;font-size:16px;color:#0b2a4a">${esc(s.title)}</h3>`
      + (s.items.length ? `<ul style="margin:0;padding-left:20px">${s.items.map((i) => `<li style="margin:0 0 4px"><strong>${esc(i.line)}</strong>${i.detail ? ` <span style="color:#5a6a7c">— ${esc(i.detail)}</span>` : ""}</li>`).join("")}</ul>` : `<p style="margin:0;color:#5a6a7c">None this period.</p>`)).join("")
    + `<p style="margin:20px 0 0"><a href="${esc(v.appUrl)}" style="color:#0a6eb4">Open the DACS Community</a></p></div>`;
  return { text, html, counts: { members: members.length, news: news.length, upcoming: upcoming.length, calls: calls.length } };
}

/* ---------- Members map ---------- */
const countryAliases: Record<string, string> = {
  "usa": "United States of America", "us": "United States of America", "united states": "United States of America", "u.s.a.": "United States of America",
  "uk": "United Kingdom", "great britain": "United Kingdom", "england": "United Kingdom", "scotland": "United Kingdom", "wales": "United Kingdom",
  "russian federation": "Russia", "viet nam": "Vietnam", "republic of korea": "South Korea", "korea": "South Korea", "korea, republic of": "South Korea",
  "democratic people's republic of korea": "North Korea", "ivory coast": "Côte d'Ivoire", "cote d'ivoire": "Côte d'Ivoire",
  "democratic republic of the congo": "Dem. Rep. Congo", "dr congo": "Dem. Rep. Congo", "drc": "Dem. Rep. Congo", "congo": "Congo", "republic of the congo": "Congo",
  "bolivia (plurinational state of)": "Bolivia", "venezuela (bolivarian republic of)": "Venezuela", "iran (islamic republic of)": "Iran",
  "united republic of tanzania": "Tanzania", "lao people's democratic republic": "Laos", "lao pdr": "Laos", "syrian arab republic": "Syria",
  "republic of moldova": "Moldova", "czech republic": "Czechia", "türkiye": "Turkey", "turkiye": "Turkey", "bosnia and herzegovina": "Bosnia and Herz.",
  "central african republic": "Central African Rep.", "dominican republic": "Dominican Rep.", "south sudan": "S. Sudan", "equatorial guinea": "Eq. Guinea",
  "eswatini": "eSwatini", "swaziland": "eSwatini", "north macedonia": "Macedonia", "solomon islands": "Solomon Is.", "marshall islands": "Marshall Is.",
  "cabo verde": "Cabo Verde", "cape verde": "Cabo Verde", "timor-leste": "Timor-Leste", "east timor": "Timor-Leste", "brunei darussalam": "Brunei",
  "micronesia (federated states of)": "Micronesia", "holy see": "Vatican", "state of palestine": "Palestine", "palestine": "Palestine",
  "hong kong": "Hong Kong", "the netherlands": "Netherlands", "holland": "Netherlands", "the gambia": "Gambia", "the bahamas": "Bahamas",
  "kyrgyz republic": "Kyrgyzstan", "slovak republic": "Slovakia", "antigua and barbuda": "Antigua and Barb.", "saint kitts and nevis": "St. Kitts and Nevis",
  "saint vincent and the grenadines": "St. Vin. and Gren.", "sao tome and principe": "São Tomé and Principe", "são tomé and príncipe": "São Tomé and Principe",
};
const normal = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/\s+/g, " ").trim();
const byNormal = new Map(Object.keys(countryCentroids).map((k) => [normal(k), k]));
/** Map name for a country typed in a profile, or "" when it cannot be placed. */
export function countryKey(country: string) {
  const n = normal(country || "");
  if (!n) return "";
  const alias = countryAliases[n] || Object.entries(countryAliases).find(([k]) => normal(k) === n)?.[1];
  if (alias && countryCentroids[alias]) return alias;
  return byNormal.get(n) || "";
}
export function countryPoints(people: { country?: string }[]) {
  const points = new Map<string, { country: string; coords: [number, number]; count: number; labels: Set<string> }>();
  const unplaced = new Map<string, number>();
  for (const p of people) {
    const key = countryKey(p.country || "");
    if (!key) {
      const label = (p.country || "").trim() || "Not stated";
      unplaced.set(label, (unplaced.get(label) || 0) + 1);
      continue;
    }
    const pt = points.get(key) || { country: key, coords: countryCentroids[key], count: 0, labels: new Set<string>() };
    pt.count++;
    pt.labels.add((p.country || "").trim());
    points.set(key, pt);
  }
  return {
    points: [...points.values()].map((p) => ({ country: p.country, label: [...p.labels][0] || p.country, coords: p.coords, count: p.count })).sort((a, b) => b.count - a.count),
    unplaced: [...unplaced.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])),
  };
}
