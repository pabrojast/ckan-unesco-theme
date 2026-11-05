// Roles declared by members at registration (pure logic; Firestore access is in role-requests.ts).
// The UNESCO Secretariat confirms, adjusts or declines each declared role; a confirmed role is recorded as the
// member's badge or Governance appointment.
export type Claim = "lead" | "associate" | "secretariat" | "core" | "member" | "unsure" | "apply";
export type Decision = "lead" | "associate" | "secretariat" | "core" | "member" | "declined";
export type RoleRequest = { id: string; name: string; claims: Record<string, Claim>; note: string; decisions: Record<string, Decision>; status: "pending" | "reviewed"; updatedAt: string; reviewedAt?: string };

export const requestBodies = ["wg1", "wg2", "wg3", "wg4", "wg5", "smc", "esc", "cfd", "alliance", "iac"];
export const claimValues: Claim[] = ["lead", "associate", "secretariat", "core", "member", "unsure", "apply"];
export const assignable: Decision[] = ["lead", "associate", "secretariat", "core", "member"];

/** Name of a role in a body; the committees use their own titles for the first two seats. */
export function roleName(body: string, role: string) {
  if (role === "lead") return body === "esc" ? "Co-chairperson" : body === "smc" ? "Chairperson" : "Lead";
  if (role === "associate") return body === "esc" ? "Co-chairperson (second seat)" : body === "smc" ? "Vice-chairperson" : "Associate Lead";
  if (role === "secretariat") return "Secretariat";
  if (role === "core") return body.startsWith("wg") ? "Core Group member" : "Committee member";
  if (role === "member") return "Broad Group member";
  if (role === "unsure") return "Unsure of my role";
  if (role === "apply") return "None yet · I wish to apply";
  if (role === "declined") return "Declined";
  return role;
}

/** Badge that records a confirmed role. Committee membership uses the committee's own badge id. */
export function badgeFor(body: string, role: string) {
  if (!assignable.includes(role as Decision)) return "";
  if (role === "member") return body.startsWith("wg") ? `${body}-member` : body;
  return `${body}-${role}`;
}

export function cleanClaims(v: any): Record<string, Claim> {
  const out: Record<string, Claim> = {};
  for (const b of requestBodies) if (claimValues.includes(v?.[b])) out[b] = v[b];
  return out;
}
const same = (a: Record<string, string>, b: Record<string, string>) => {
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every((k) => a[k] === b[k]);
};

/**
 * The record a member's new declaration produces, or null when nothing changed.
 * Earlier decisions are kept unless the member changed a role that was already decided.
 */
export function nextRequest(prev: Pick<RoleRequest, "claims" | "note" | "decisions"> | null, claims: Record<string, Claim>, note: string) {
  const before = prev?.claims || {}, decisions = prev?.decisions || {};
  if (prev && same(before, claims) && (prev.note || "") === note) return null;
  if (!prev && !Object.keys(claims).length && !note) return null;
  const changed = [...new Set([...Object.keys(before), ...Object.keys(claims)])].filter((b) => before[b] !== claims[b]);
  return { claims, note, decisions: changed.some((b) => b in decisions) ? {} : decisions, status: "pending" as const };
}

/** Status of one declared role for display. */
export function claimStatus(r: Pick<RoleRequest, "claims" | "decisions">, body: string) {
  const d = r.decisions?.[body];
  if (!d) return { state: "pending", label: "Awaiting confirmation" };
  if (d === "declined") return { state: "declined", label: "Declined by the UNESCO Secretariat" };
  return { state: "confirmed", label: d === r.claims[body] ? "Confirmed" : `Confirmed as ${roleName(body, d)}` };
}

