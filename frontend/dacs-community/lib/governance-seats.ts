export type AppointmentSeat = {
  field: "lead" | "associateLeads" | "secretariat" | "core";
  label: string;
  multiple: boolean;
};

export function appointmentSeats(id: string): AppointmentSeat[] {
  if (id === "esc") return [
    { field: "lead", label: "Co-chairperson 1", multiple: false },
    { field: "associateLeads", label: "Co-chairperson 2", multiple: false },
    { field: "secretariat", label: "Secretariat", multiple: false },
    { field: "core", label: "Committee members", multiple: true },
  ];
  if (id === "smc") return [
    { field: "lead", label: "Chairperson", multiple: false },
    { field: "associateLeads", label: "Vice-chairperson", multiple: false },
    { field: "secretariat", label: "Secretariat", multiple: false },
    { field: "core", label: "Committee members", multiple: true },
  ];
  return [
    { field: "lead", label: "Lead", multiple: false },
    { field: "secretariat", label: "Secretariat", multiple: true },
    { field: "associateLeads", label: "Associate Leads", multiple: true },
    { field: "core", label: "Core / committee members", multiple: true },
  ];
}

export function appointmentIds(body: any, seat: AppointmentSeat): string[] {
  return seat.field === "lead" ? (body.lead ? [body.lead] : []) : body[seat.field] || [];
}

// Use the existing fields so deployed appointments need no destructive migration.
export function committeeSeatError(id: string, body: any): string {
  if (!["esc", "smc"].includes(id)) return "";
  if ((body.secretariat || []).length > 1) return "Choose one Secretariat member.";
  if ((body.associateLeads || []).length > 1)
    return id === "esc" ? "Choose one person for the second co-chairperson seat." : "Choose one Vice-chairperson.";
  if (body.lead && (body.associateLeads || []).includes(body.lead))
    return id === "esc" ? "The two co-chairpersons must be different people." : "The Chairperson and Vice-chairperson must be different people.";
  return "";
}

// Appointment badges ("wg3-lead", "smc-core"…) ticked by the UNESCO Secretariat are stored as Governance appointments.
const positionFields = { lead: "lead", associate: "associateLeads", secretariat: "secretariat", core: "core" } as const;
type Position = keyof typeof positionFields;
const appointmentPattern = /^(wg[1-5]|cfd|smc|esc|alliance|iac)-(lead|associate|secretariat|core)$/;
export function appointmentBadge(id: string) {
  const m = appointmentPattern.exec(id);
  return m ? { body: m[1], position: m[2] as Position, field: positionFields[m[2] as Position] } : null;
}
export const isAppointmentBadge = (id: string) => appointmentPattern.test(id);
/** Seats held by one person only: every Lead, and the ESC and SMC Secretariat and second (co-/vice-) chair. */
export const singleSeat = (body: string, field: string) => field === "lead" || (["esc", "smc"].includes(body) && field !== "core");
const holds = (g: any, field: string, uid: string) => (field === "lead" ? g.lead === uid : (g[field] || []).includes(uid));
/**
 * Applies the appointment badges ticked for one member to the Governance records.
 * Returns the records that change. A single seat ticked for this member replaces its current holder.
 */
export function applyAppointments(uid: string, badges: string[], governance: any[], bodies: { id: string; title: string }[]) {
  const wanted = new Set(badges.filter(isAppointmentBadge));
  const changed: any[] = [];
  for (const base of bodies) {
    const current = governance.find((g) => g.id === base.id) || {};
    const g = {
      id: base.id,
      title: current.title || base.title,
      description: current.description || "",
      lead: current.lead || "",
      secretariat: [...(current.secretariat || [])],
      associateLeads: [...(current.associateLeads || [])],
      core: [...(current.core || [])],
    } as any;
    let dirty = false;
    for (const [position, field] of Object.entries(positionFields)) {
      const want = wanted.has(`${base.id}-${position}`), has = holds(g, field, uid);
      if (want === has) continue;
      dirty = true;
      if (field === "lead") g.lead = want ? uid : "";
      else if (!want) g[field] = g[field].filter((x: string) => x !== uid);
      else if (singleSeat(base.id, field)) g[field] = [uid];
      else if (g[field].length >= 20) throw Error(`${base.title}: at most 20 people per seat.`);
      else g[field] = [...g[field], uid];
    }
    if (!dirty) continue;
    const error = committeeSeatError(base.id, g);
    if (error) throw Error(error);
    changed.push(g);
  }
  return changed;
}
