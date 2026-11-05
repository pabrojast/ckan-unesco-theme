// Official titles: Synthesis of the DACS 2025–2034, pp. 8–12.
export const overarchingChallenges = [
  {id:1, title:'Global Cryosphere Monitoring'},
  {id:2, title:'Actionable Cryosphere Projections'},
  {id:3, title:'Cryospheric Risk Management Solutions'},
  {id:4, title:'Adaptation to Cryosphere Loss'},
  {id:5, title:'Amplify the Impact of Cryospheric Science'},
];
export const decadeGoals = [
  {id:'1.1', oc:1, title:'Build a Global Cryosphere Monitoring Inventory'},
  {id:'1.2', oc:1, title:'Enhance Monitoring Capabilities'},
  {id:'1.3', oc:1, title:'Make Observations Actionable'},
  {id:'2.1', oc:2, title:'Cryosphere Modelling for Decision Making'},
  {id:'2.2', oc:2, title:'Inclusive Cryosphere Prediction'},
  {id:'2.3', oc:2, title:'Creation of a Decision and Outreach Toolkit'},
  {id:'3.1', oc:3, title:'Global Cryosphere Risk Assessment'},
  {id:'3.2', oc:3, title:'Cryosphere Loss Vulnerability Assessment'},
  {id:'3.3', oc:3, title:'Operationalise Cryosphere Risk Management Solutions'},
  {id:'4.1', oc:4, title:'Incorporating Cryosphere Loss into Adaptation Strategies'},
  {id:'4.2', oc:4, title:'Co-Develop Adaptation Strategies for those Living in and with the Cryosphere'},
  {id:'4.3', oc:4, title:'Establish a Global Cryosphere Adaptation Knowledge Hub'},
  {id:'5.1', oc:5, title:'Policy Integration and Engagement / Cryosphere Loss Prevention'},
  {id:'5.2', oc:5, title:'Global Cryosphere Outreach and Communication'},
  {id:'5.3', oc:5, title:'Education and Capacity Building'},
];
export const challengeLabel = (id:number) => `OC${id} · ${overarchingChallenges.find(c=>c.id===id)?.title || ''}`;
export const goalLabel = (id:string) => `MG${id} · ${decadeGoals.find(g=>g.id===id)?.title || ''}`;
export const allGoalIds = decadeGoals.map(g=>g.id);
export function isDecadeWide(value:string[] = []) {
  return value.length===allGoalIds.length && allGoalIds.every(id=>value.includes(id));
}
export function linkedGroups(mgs:string[] = []) {
  return [...new Set(decadeGoals.filter(g=>mgs.includes(g.id)).map(g=>g.oc))].sort();
}
export function validGoalSelection(mgs:unknown): mgs is string[] {
  return Array.isArray(mgs) && mgs.length<=15 && new Set(mgs).size===mgs.length && mgs.every(id=>decadeGoals.some(g=>g.id===id));
}
// The primary reviewing group remains part of legacy activities without goals.
export function activityGroups(activity:{wg:number;mgs?:string[]}) {
  return [...new Set([activity.wg,...linkedGroups(activity.mgs)])].filter(n=>n>=1 && n<=5).sort();
}
