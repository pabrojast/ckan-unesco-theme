import {isUnescoSecretariat} from './member-roles.ts';
import {localInput} from './calendar.ts';
export const meetingBodies = [
  ...[1,2,3,4,5].map(n=>({id:`wg${n}`,label:`WG${n}`})),
  {id:'cfd',label:'Cryosphere Finance Dialogue'}, {id:'alliance',label:'Alliance for the Cryosphere'},
  {id:'smc',label:'Strategic Management Committee'}, {id:'esc',label:'Executive Steering Committee'}, {id:'iac',label:'Indigenous Advisory Committee'},
];
export const meetingTypes = [{id:'leadership',label:'Leadership Meeting'},{id:'core',label:'Core Group Meeting'},{id:'broad',label:'Broad Group Meeting'}] as const;
export type MeetingType = 'leadership'|'core'|'broad';
export type MeetingAccess = {uid:string;role:any;governance:any[];profile:any;admin:boolean};
export const bodyLabel=(id:string)=>meetingBodies.find(b=>b.id===id)?.label||id;
export const typeLabel=(id:string)=>meetingTypes.find(t=>t.id===id)?.label||'Public event';
export function bodyLevel(a:MeetingAccess,id:string):number {
  if(a.admin || isUnescoSecretariat(a.role||{}))return 3;
  if(!a.uid || !meetingBodies.some(b=>b.id===id))return 0;
  const r=a.role||{}, badges=r.badges||[], g=a.governance.find(g=>g.id===id)||{};
  if(g.lead===a.uid || [...(g.secretariat||[]),...(g.associateLeads||[])].includes(a.uid) || ['lead','associate','secretariat'].some(p=>badges.includes(`${id}-${p}`)) ||
    (/^wg[1-5]$/.test(id)&&['lead','associate','secretariat'].includes(r.role)&&(r.wgs||[]).includes(Number(id[2]))))return 3;
  if((g.core||[]).includes(a.uid)||badges.includes(`${id}-core`)||(/^wg[1-5]$/.test(id)&&r.role==='core'&&(r.wgs||[]).includes(Number(id[2]))))return 2;
  return badges.includes(id)||badges.includes(`${id}-member`)||(/^wg[1-5]$/.test(id)&&(a.profile?.wgs||[]).includes(Number(id[2])))?1:0;
}
export const canAttend=(a:MeetingAccess,body:string,type:string)=>type==='public'||bodyLevel(a,body)>=(type==='leadership'?3:type==='core'?2:1);
export const canOrganise=(a:MeetingAccess,body:string)=>bodyLevel(a,body)>=3;
export const canEditAgenda=(a:MeetingAccess,body:string,type:string)=>bodyLevel(a,body)>=(type==='leadership'?3:2);
export const leadershipBodies=(a:MeetingAccess)=>meetingBodies.filter(b=>canOrganise(a,b.id));
/** Bodies whose logo requests a member may review: granted one by one by the UNESCO Secretariat (roles/{uid}.logoReview), never by an appointment. */
export const logoReviewOptions=['wg1','wg2','wg3','wg4','wg5','smc','esc'];
export const logoBodies=(a:Pick<MeetingAccess,'role'>)=>((a.role||{}).logoReview||[]).filter((b:string)=>logoReviewOptions.includes(b)) as string[];
export const canReviewLogo=(a:MeetingAccess)=>!!a.uid&&(a.admin||isUnescoSecretariat(a.role||{})||logoBodies(a).length>0);
export type MeetingPoll={id:string;owner:string;title:string;body:string;meetingType:MeetingType;mgs:string[];durationMinutes:number;slots:string[];deadline:string;status:'open'|'closed'|'scheduled';selectedSlot:number;eventId:string;createdAt:string;updatedAt:string;linkAccess?:boolean;notes?:string;withdrawn?:number[]};
export type PollResponse={id:string;pollId:string;uid:string;name:string;timeZone:string;answers:string[];updatedAt:string};
export type MeetingSeed={title:string;body:string;meetingType:MeetingType;mgs:string[];startAt:string;endAt:string;pollId?:string;selectedSlot?:number};
export function meetingReminder(events:any[],baseline:string,now=Date.now(),openPoll=false) {
  if(openPoll || events.some(e=>Date.parse(e.endAt)>now))return null;
  const past=events.map(e=>Date.parse(e.endAt)).filter(t=>Number.isFinite(t)&&t<=now);
  const last=past.length?Math.max(...past):Date.parse(baseline);
  if(!Number.isFinite(last))return null;
  const days=Math.floor((now-last)/86400000);
  return days>=21?{days,urgent:days>=28,last:new Date(last).toISOString()}:null;
}
export function zoneHour(instant:string,zone:string){return Number(localInput(instant,zone).slice(11,13));}
export function outsideWorkingHours(start:string,durationMinutes:number,zone:string){const first=localInput(start,zone),last=localInput(new Date(Date.parse(start)+durationMinutes*60000),zone);return first.slice(0,10)!==last.slice(0,10)||first.slice(11)<'08:00'||last.slice(11)>'19:00';}
/** Proposed times still on offer (the organiser may withdraw some after publication), in chronological order with their original index. */
export const activeSlots=(poll:Pick<MeetingPoll,'slots'|'withdrawn'>)=>poll.slots.map((start,index)=>({start,index})).filter(x=>!(poll.withdrawn||[]).includes(x.index)).sort((a,b)=>a.start.localeCompare(b.start));
/** One answer per proposed time: blanks (and times added after an earlier answer) become null. */
export const padAnswers=(answers:(string|null|undefined)[]|undefined,n:number)=>Array.from({length:n},(_,i)=>answers?.[i]??null);
/** True when times were added after the member answered, so their availability is incomplete. */
export const answerIncomplete=(poll:Pick<MeetingPoll,'slots'|'withdrawn'>,r?:Pick<PollResponse,'answers'>)=>!!r&&activeSlots(poll).some(x=>x.index>=r.answers.length);
export function rankSlots(poll:MeetingPoll,responses:PollResponse[]){return activeSlots(poll).map(({start:startAt,index})=>{
  const yes=responses.filter(r=>r.answers[index]==='yes').length, maybe=responses.filter(r=>r.answers[index]==='if-needed').length;
  const outside=responses.filter(r=>outsideWorkingHours(startAt,poll.durationMinutes||60,r.timeZone)).length;
  return {index,startAt,yes,maybe,outside,score:yes+maybe*.5};
}).sort((a,b)=>b.score-a.score||a.outside-b.outside||a.startAt.localeCompare(b.startAt));}

// Shareable poll links: /poll/<id>. The id is Firestore's random document id.
export function pollIdFromPath(pathname:string){const m=/^\/poll\/([A-Za-z0-9_-]{1,128})\/?$/.exec(pathname);return m?m[1]:null;}
export const pollLink=(origin:string,id:string)=>`${origin.replace(/\/$/,'')}/poll/${encodeURIComponent(id)}`;
export function pollInvitation(poll:{title:string;body:string;meetingType:string;durationMinutes:number;deadline:string},link:string,zone:string){
  const deadline=new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'long',day:'numeric',month:'long',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(new Date(poll.deadline));
  const subject=`Meeting poll: ${poll.title}`;
  const text=`Dear colleagues,\n\nPlease indicate your availability for "${poll.title}" (${bodyLabel(poll.body)}, ${typeLabel(poll.meetingType)}, ${poll.durationMinutes} minutes) by ${deadline}.\n\nOpen the poll: ${link}\n\nIf you do not yet have an account on DACS Community, you can create one from this link and then vote. Times are shown in your own time zone.\n\nWith thanks,`;
  return {subject,text,mailto:`mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(text)}`};
}
/** Unanswered times are recorded as unavailable. */
export const completeAnswers=(answers:(string|null|undefined)[])=>answers.map(a=>a==='yes'||a==='if-needed'?a:'no');
