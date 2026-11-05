import { skills, languages } from "./data";

export const categoryKinds = [
  "skills",
  "languages",
  "careerStages",
  "genders",
  "educationLevels",
  "cryosphereTypes",
  "contributionTypes",
] as const;
export type CategoryKind = (typeof categoryKinds)[number];
export const defaults: Record<CategoryKind, string[]> = {
  skills,
  languages,
  contributionTypes: ["Scientific review", "Case study", "Data contribution", "Training", "Communication", "Project support"],
  careerStages: [
    "Student",
    "Early-career professional",
    "Mid-career professional",
    "Senior professional",
    "Retired",
    "Prefer not to say",
  ],
  genders: ["Woman", "Man", "Non-binary", "Prefer not to say"],
  educationLevels: [
    "Secondary education",
    "Vocational qualification",
    "Bachelor’s degree",
    "Master’s degree",
    "Doctorate",
    "Prefer not to say",
  ],
  cryosphereTypes: [
    "Mountain glaciers",
    "Ice sheets",
    "Sea ice",
    "Snow",
    "Permafrost",
    "Lake and river ice",
    "All cryosphere components",
  ],
};
export const blankProfile = {
  name: "",
  headline: "",
  organisation: "",
  country: "",
  region: "",
  languages: [] as string[],
  skills: [] as string[],
  wgs: [] as number[],
  bio: "",
  motivation: "",
  contribution: "",
  availability: "2–4 hours / month",
  sentiment: "",
  feedback: "",
  website: "",
  visibility: "community",
  contactConsent: false,
  contact: "",
  consent: false,
  careerStage: "Prefer not to say",
  gender: "Prefer not to say",
  showBackground: false,
  educationLevel: "Prefer not to say",
  cryosphereTypes: [] as string[],
  hasPhoto: false,
  onboardingVersion: 2,
};
export const normaliseLabel = (value: string) =>
  value
    .normalize("NFKC")
    .trim()
    .replace(/\s+/g, " ")
    .replace(/[\u0000-\u001f\u007f]/g, "");
export function optionsFor(
  kind: CategoryKind,
  records: any[] = [],
  selected: string[] = [],
) {
  const labels = [
    ...defaults[kind],
    ...records
      .filter((r) => r.kind === kind && r.enabled !== false)
      .map((r) => r.label),
    ...selected,
  ];
  const seen = new Set<string>();
  return labels.filter((s) => {
    const key = normaliseLabel(s).toLocaleLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
// Full official names of the Decade bodies, used wherever a body is listed.
const wgNames = ["Global Cryosphere Monitoring", "Actionable Cryosphere Projections", "Cryospheric Risk Management Solutions", "Adaptation to Cryosphere Loss", "Amplify the Impact of Cryospheric Science"];
export const bodies = [
  ...[1, 2, 3, 4, 5].map((n) => ({
    id: "wg" + n,
    title: `Working Group ${n} · ${wgNames[n - 1]}`,
  })),
  { id: "cfd", title: "Cryosphere Finance Dialogue" },
  { id: "smc", title: "Strategic Management Committee" },
  { id: "esc", title: "Executive Steering Committee" },
  { id: "alliance", title: "Alliance for the Cryosphere" },
  { id: "iac", title: "Indigenous Advisory Committee" },
];
export const emptyBody = {
  lead: "",
  secretariat: [] as string[],
  associateLeads: [] as string[],
  core: [] as string[],
  description: "",
};

// Every body is shown under its full official name, whatever title was stored earlier.
export function bodyTitle(id: string, title: string) {
  return bodies.find((b) => b.id === id)?.title || title;
}
