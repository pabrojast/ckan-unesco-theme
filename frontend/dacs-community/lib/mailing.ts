// Mailing lists of the bodies of the Decade.
// Each member keeps one entry (name, sign-in email, tier) in the list of every body they belong to, and one in the
// Decade-wide list. Leadership and Core Group members of a body read that body's list; only the UNESCO Secretariat
// reads the Decade-wide list. The tiers are nested: Core Group includes leadership, Broad Group includes everyone.
import { bodyLevel, meetingBodies } from "./meetings.ts";

export type Tier = "leadership" | "core" | "broad";
export type MailingEntry = { id: string; name: string; email: string; tier: Tier | "member" };
export const DECADE = "decade";
export const mailingBodyIds = meetingBodies.map((b) => b.id);
export const tierRank: Record<string, number> = { leadership: 3, core: 2, broad: 1, member: 1 };
export const tierLabels: Record<Tier, { label: string; who: string }> = {
  leadership: { label: "Leadership", who: "Leads, Associate Leads and Secretariat" },
  core: { label: "Core Group", who: "Leadership and Core Group" },
  broad: { label: "Broad Group", who: "Leadership, Core Group and Broad Group" },
};

export const tierFromLevel = (level: number): Tier | null => (level >= 3 ? "leadership" : level === 2 ? "core" : level === 1 ? "broad" : null);

/**
 * The tier a person holds in each body, from their role and badges and the Governance appointments.
 * Broad Group lists hold only members certified by the UNESCO Secretariat with the Broad Group badge of the body:
 * the Working Groups a member selected in their profile are interests and do not count.
 * The UNESCO Secretariat's global access is left out, so a UNESCO officer appears only in the bodies they belong to.
 */
export function memberTiers(uid: string, role: any, governance: any[], profile: any): Record<string, Tier> {
  const own = {
    ...(role || {}),
    role: role?.role === "unesco-secretariat" ? "member" : role?.role || "member",
    admin: false,
    badges: (role?.badges || []).filter((b: string) => b !== "unesco-secretariat"),
  };
  const access = { uid, role: own, governance: governance || [], profile: { ...(profile || {}), wgs: [] }, admin: false };
  const out: Record<string, Tier> = {};
  for (const id of mailingBodyIds) {
    const t = tierFromLevel(bodyLevel(access, id));
    if (t) out[id] = t;
  }
  return out;
}

/** Entries reached by one tier of a list: Leadership ⊂ Core Group ⊂ Broad Group. */
export function recipients(entries: MailingEntry[], tier: Tier | "member") {
  const min = tierRank[tier];
  const seen = new Set<string>();
  return entries
    .filter((e) => (tierRank[e.tier] || 0) >= min && /.+@.+\..+/.test(e.email))
    .filter((e) => { const k = e.email.trim().toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; })
    .sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * mailto links with the sender in "To" and everyone else in "Bcc".
 * Email programs reject very long links, so large lists are split into several messages.
 */
export function mailtoBatches(sender: string, emails: string[], subject: string, maxLength = 1900): string[] {
  const self = sender.trim().toLowerCase();
  const list = [...new Set(emails.map((e) => e.trim()).filter((e) => e && e.toLowerCase() !== self))];
  const head = `mailto:${encodeURIComponent(sender)}?subject=${encodeURIComponent(subject)}&bcc=`;
  const out: string[] = [];
  let batch: string[] = [];
  const url = (b: string[]) => head + b.map(encodeURIComponent).join(",");
  for (const e of list) {
    if (batch.length && url([...batch, e]).length > maxLength) { out.push(url(batch)); batch = []; }
    batch.push(e);
  }
  if (batch.length) out.push(url(batch));
  return out;
}

/** Changes needed to bring one member's entries in line with their tiers: lists to write and lists to remove. */
export function entryChanges(current: Record<string, { tier: string; email: string; name: string } | undefined>, wanted: Record<string, string>, email: string, name: string) {
  const write: { list: string; tier: string }[] = [], remove: string[] = [];
  for (const list of [...mailingBodyIds, DECADE]) {
    const want = wanted[list], have = current[list];
    if (want && (!have || have.tier !== want || have.email !== email || have.name !== name)) write.push({ list, tier: want });
    if (!want && have) remove.push(list);
  }
  return { write, remove };
}

/**
 * Entries of a body's list checked against each person's current role: entries of people who no longer hold a
 * tier in the body (for example interested members without the Broad Group badge, or removed members) are left out,
 * and the tier shown is the current one.
 */
export function currentEntries(list: string, entries: MailingEntry[], people: any[], governance: any[]): MailingEntry[] {
  if (list === DECADE) return entries;
  return entries.flatMap((e) => {
    const p = people.find((x) => x.id === e.id);
    if (!p) return [];
    const tier = memberTiers(p.id, { role: p.role, wgs: p.directWgs || [], badges: p.assignedBadgeIds || [] }, governance, p)[list];
    return tier ? [{ ...e, tier }] : [];
  });
}
