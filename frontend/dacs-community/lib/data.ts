import {activityGroups} from './decade-goals.ts';
export const groups = [
  {
    id: 1,
    title: "Global Cryosphere Monitoring",
    short: "Monitoring",
    color: "#8ed2ee",
    ink: "#205a75",
    description:
      "Bring together observations and monitoring expertise across the cryosphere.",
    goal: "Coordinate observations and assess monitoring gaps",
    skills: ["Glacier monitoring", "Remote sensing", "Data management"],
    icon: "Satellite",
  },
  {
    id: 2,
    title: "Actionable Cryosphere Projections",
    short: "Projections",
    color: "#a0a9ff",
    ink: "#434580",
    description:
      "Connect models and projections with the information decision-makers need.",
    goal: "Develop actionable projections and shared methods",
    skills: ["Climate modelling", "Hydrology", "Data analysis"],
    icon: "Chart",
  },
  {
    id: 3,
    title: "Cryospheric Risk Management Solutions",
    short: "Risk management",
    color: "#f4bc83",
    ink: "#81480e",
    description:
      "Connect hazard assessment, early warning and risk management practice.",
    goal: "Translate cryospheric risk evidence into practical solutions",
    skills: ["Risk assessment", "Early warning", "GIS"],
    icon: "Shield",
  },
  {
    id: 4,
    title: "Adaptation to Cryosphere Loss",
    short: "Adaptation",
    color: "#82d8b7",
    ink: "#25654b",
    description:
      "Connect cryosphere science, adaptation planning and community experience.",
    goal: "Incorporate cryosphere loss into adaptation strategies",
    skills: ["Adaptation planning", "Community engagement", "Water resources"],
    icon: "Leaf",
  },
  {
    id: 5,
    title: "Amplify the Impact of Cryospheric Science",
    short: "Amplify",
    color: "#e9a9d8",
    ink: "#804671",
    description:
      "Connect communication, education and policy to support the Decade’s impact.",
    goal: "Connect science, education and public engagement",
    skills: ["Science communication", "Education", "Policy analysis"],
    icon: "Megaphone",
  },
];
export const skills = [
  "Glacier monitoring",
  "Remote sensing",
  "Data management",
  "Climate modelling",
  "Hydrology",
  "Data analysis",
  "Risk assessment",
  "Early warning",
  "GIS",
  "Adaptation planning",
  "Community engagement",
  "Water resources",
  "Science communication",
  "Education",
  "Policy analysis",
  "Indigenous knowledge",
  "Climate finance",
  "Capacity development",
  "Project coordination",
];
export const regions = [
  "Africa",
  "Asia and the Pacific",
  "Western Europe and North America",
  "Eastern Europe",
  "Latin America and the Caribbean",
  "Arab States",
  "Global",
];
export const languages = [
  "English",
  "French",
  "Spanish",
  "Russian",
  "Arabic",
  "Chinese",
  "Portuguese",
  "Other",
];
export const normaliseRegion = (region:string) => region === "Europe and North America" ? "Western Europe and North America" : region;
export function match(person: any, op: any) {
  const shared = (op.skills || []).filter((s: string) =>
    person.skills?.includes(s),
  );
  const wg = activityGroups(op).some(wg=>person.wgs?.includes(wg));
  const region = op.region === "Global" || normaliseRegion(op.region) === normaliseRegion(person.region);
  const language = person.languages?.includes(op.language);
  const score = Math.round(
    (shared.length / Math.max(1, op.skills?.length || 0)) * 60 +
      (wg ? 20 : 0) +
      (region ? 10 : 0) +
      (language ? 10 : 0),
  );
  return { score, shared, wg, region, language };
}
