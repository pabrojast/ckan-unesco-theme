const positions = [
  { id: "member", label: "Member" },
  { id: "core", label: "Core Group" },
  { id: "lead", label: "Lead" },
  { id: "associate", label: "Associate Lead" },
  { id: "secretariat", label: "Secretariat" },
];
const committees = [
  { id: "cfd", label: "CFD" },
  { id: "smc", label: "SMC" },
  { id: "esc", label: "ESC" },
  { id: "alliance", label: "Alliance" },
  { id: "iac", label: "IAC" },
];
// Editorial access is separate from a person's official Decade appointments.
export const editorialBadgeIds = ["core", "lead", "associate", "secretariat"];
/** Default badge of a member who holds no badge or appointment from the UNESCO Secretariat or a Working Group. */
export const broadGroupBadge = { id: "interested-member", label: "Interested member", group: "Decade" };
export const badgeOptions = [
  ...[1, 2, 3, 4, 5].flatMap((n) =>
    positions.map((p) => ({
      id: `wg${n}-${p.id}`,
      label: `${p.id === "core" ? "Core Group member" : p.id === "member" ? "Broad Group member" : p.label} of WG${n}`,
      group: `WG${n}`,
    })),
  ),
  ...committees.flatMap((c) =>
    positions.map((p) => ({
      id: p.id === "member" ? c.id : `${c.id}-${p.id}`,
      label: `${c.id === "esc" && ["lead", "associate"].includes(p.id) ? "Co-chairperson"
        : c.id === "smc" && p.id === "lead" ? "Chairperson"
        : c.id === "smc" && p.id === "associate" ? "Vice-chairperson"
        : p.id === "core" ? "Core Group member" : p.label} of ${c.label}`,
      group: c.label,
    })),
  ),
  { id: "unesco-secretariat", label: "UNESCO Secretariat", group: "UNESCO" },
];
export const badgeIds = [...editorialBadgeIds, ...badgeOptions.map((b) => b.id)];
// A WG Secretariat appointment, a legacy admin flag or a badge alone is not
// a global editing grant. Keep this condition aligned with Firestore rules.
export function isUnescoSecretariat(role: any) {
  return role.role === "unesco-secretariat" && role.admin === true &&
    (role.badges || []).includes("unesco-secretariat");
}
/**
 * Badges shown under a member's name: only what the UNESCO Secretariat has assigned (in "Manage access & badges",
 * or by confirming a role declaration) and the Governance appointments. The Working Groups a member chose in their
 * profile are interests and never create a badge.
 */
export function assignedBadges(uid: string, role: any, governance: any[]) {
  const ids = new Set<string>(
    (role.badges || []).filter((id: string) => badgeOptions.some((b) => b.id === id)),
  );
  if (isUnescoSecretariat(role)) {
    ids.add("unesco-secretariat");
    ids.delete("secretariat");
  } else ids.delete("unesco-secretariat");
  for (const body of governance) {
    for (const [field, position] of [
      ["lead", "lead"],
      ["secretariat", "secretariat"],
      ["associateLeads", "associate"],
      ["core", "core"],
    ]) {
      const appointed =
        field === "lead"
          ? body.lead === uid
          : (body[field] || []).includes(uid);
      if (appointed) ids.add(`${body.id}-${position}`);
    }
  }
  const priority = (id: string) => id === "unesco-secretariat" ? 0
    : id === "lead" || id.endsWith("-lead") ? 1
    : id === "associate" || id.endsWith("-associate") ? 2
    : id === "secretariat" || id.endsWith("-secretariat") ? 3
    : id === "core" || id.endsWith("-core") ? 4 : 5;
  const badges = badgeOptions.filter((b) => ids.has(b.id))
    .sort((a, b) => priority(a.id) - priority(b.id));
  return badges.length ? [...new Map(badges.map((b) => [b.label, b])).values()] : [broadGroupBadge];
}
export function canSeeWorkspace(uid: string, role: any, governance: any[]) {
  if (
    isUnescoSecretariat(role) ||
    editorialBadgeIds.includes(role.role) ||
    (role.badges || []).some((id: string) => editorialBadgeIds.includes(id))
  )
    return true;
  return assignedBadges(uid, role, governance).some(
    (b) =>
      [
        "core",
        "lead",
        "associate",
        "secretariat",
        "unesco-secretariat",
      ].includes(b.id) || /-(core|lead|associate|secretariat)$/.test(b.id),
  );
}
