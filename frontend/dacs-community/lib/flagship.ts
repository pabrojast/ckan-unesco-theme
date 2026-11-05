// Flagship projects of the Working Groups (stored as work plan items: "deliverable" = flagship project,
// "milestone" = a step of a project, linked through `parent`). Pure helpers, no Firebase.
import { decadeGoals, overarchingChallenges } from "./decade-goals.ts";
import type { WorkItem } from "./coordination";

/**
 * "The Decade is split into three triennia. Each MG is assigned a 3-year block, marked by a triennial summit."
 * (Terms of Reference of Working Groups 1 to 5). Periods as set by the UNESCO Secretariat: 2026-2028, 2029-2031 and 2032-2034.
 */
export const triennia = [
  { n: 1, label: "First triennium", period: "2026–2028", from: 2026, to: 2028 },
  { n: 2, label: "Second triennium", period: "2029–2031", from: 2029, to: 2031 },
  { n: 3, label: "Third triennium", period: "2032–2034", from: 2032, to: 2034 },
];
export const trienniumOf = (mg: string) => Number(mg.split(".")[1]) || 1;

/**
 * Working Groups whose main goals run in parallel over the whole Decade rather than one per triennium: every main goal
 * is in focus in every triennium. Quoted from the Terms of Reference of Working Group 5.
 */
export const concurrentGoals: Record<number, { quote: string }> = {
  5: { quote: "All Main Goals of OC5 need to run in parallel" },
};
export const runsConcurrently = (wg: number) => !!concurrentGoals[wg];
/** The triennium under way (1 before the Decade's first triennium starts, 0 after the Decade ends). */
export function currentTriennium(now = new Date()) {
  const y = now.getUTCFullYear();
  if (y < triennia[0].from) return 1;
  return triennia.find((t) => y >= t.from && y <= t.to)?.n ?? 0;
}

/** End-of-Decade ambition of each Working Group, quoted from its Terms of Reference. */
export const wgVision: Record<number, string> = {
  1: "By the end of the Decade, this Working Group should achieve a global cryosphere observation framework as critical research infrastructure through coordination of existing and emerging observation systems, that maximises the value of existing and future investments, and provides the observational framework for modelling, hazard assessment, adaption planning and informed decision-making.",
  2: "By the end of the Decade, this Working Group will have established a coordinated and inclusive framework that strengthens the societal value of cryosphere modelling: improves transparency and accessibility of model outputs as well as interoperability and interpretability; and enables existing scientific capabilities to meaningfully inform concrete decisions, policy, planning, investment, and adaptation across relevant spatial and temporal scales.",
  3: "By the end of the Decade, this Working Group will create a coherent pathway from risk identification, through vulnerability understanding, to actionable solutions – supporting evidence-based, community-centred cryosphere risk management throughout the Decade.",
  4: "By the end of the Decade, this Working Group will develop evidence based, transformative, cryosphere adaption facilitated by a central knowledge hub.",
  5: "Over the course of the Decade, this Working Group is to make cryospheric science a clear, credible, and unavoidable driver of climate decision-making, greenhouse gas emissions reductions, including the accelerated phase-down of fossil fuel use, and long-term action through authoritative evidence and ethical clarity.",
};
export const challengeOf = (wg: number) => overarchingChallenges.find((c) => c.id === wg)!;
export const goalsOfGroup = (wg: number) => decadeGoals.filter((g) => g.oc === wg);

export const isProject = (i: Pick<WorkItem, "kind">) => i.kind === "deliverable";
export const projectsOf = (items: WorkItem[], body: string, mg?: string) =>
  items.filter((i) => i.body === body && isProject(i) && (!mg || i.mg === mg)).sort(byDue);
export const milestonesOf = (items: WorkItem[], projectId: string) =>
  items.filter((i) => i.kind === "milestone" && i.parent === projectId).sort(byDue);
/** Milestones recorded before projects existed, or whose project was deleted. */
export function looseMilestones(items: WorkItem[], body: string, mg: string) {
  const ids = new Set(items.filter(isProject).map((p) => p.id));
  return items.filter((i) => i.body === body && i.mg === mg && i.kind === "milestone" && (!i.parent || !ids.has(i.parent))).sort(byDue);
}
export function byDue(a: Pick<WorkItem, "due" | "title">, b: Pick<WorkItem, "due" | "title">) {
  return (a.due || "9999").localeCompare(b.due || "9999") || a.title.localeCompare(b.title);
}
/** Progress of a project measured by its completed milestones; null when it has no milestone yet. */
export function projectProgress(milestones: Pick<WorkItem, "status">[]) {
  if (!milestones.length) return null;
  const done = milestones.filter((m) => m.status === "done").length;
  return { done, total: milestones.length, percent: Math.round((done / milestones.length) * 100) };
}
