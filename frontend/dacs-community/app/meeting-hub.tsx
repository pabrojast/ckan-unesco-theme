import {useEffect,useMemo,useRef,useState} from 'react';
import {CreatedBy} from './people-context';
import {accentStyle,eventAccent} from '@/lib/event-style';
import {collection,doc,onSnapshot,query,limit} from 'firebase/firestore';
import {Bell,Plus,CalendarDays,Check,Clock,Link2,Copy,Users,ChevronLeft,ArrowRight,Trash2,Info,Pencil,AtSign,ClipboardCheck,MessageCircle,Newspaper,Briefcase,CheckCheck,SquareKanban} from 'lucide-react';
import {actionState,sortActions,type ActionItem} from '@/lib/coordination';
import {MemberAvatar} from './member-avatar';
import {timeAgo} from '@/lib/discussion';
import type {InboxItem} from '@/lib/discussion-store';
import {db,auth,isPlatformOwner} from '@/lib/firebase';
import {isUnescoSecretariat} from '@/lib/member-roles';
import {meetingBodies,bodyLabel,typeLabel,bodyLevel,leadershipBodies,canOrganise,meetingReminder,rankSlots,outsideWorkingHours,pollLink,completeAnswers,activeSlots,padAnswers,answerIncomplete,type MeetingAccess,type MeetingPoll,type PollResponse,type MeetingSeed} from '@/lib/meetings';
import {subscribePolls,subscribeOwnResponses,subscribeResponses,subscribeRhythms,savePoll,updatePoll,respond,closePoll,deletePoll,fetchPoll} from '@/lib/meeting-store';
import {localInput,timeCandidates} from '@/lib/calendar';
import {friendlyError} from '@/lib/store';
import {GoalPicker,GoalLabels} from './goal-picker';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';
import {toast} from 'sonner';
import {TimeZonePicker} from './time-zone-picker';
import {useTimeZone} from '@/hooks/use-time-zone';
import {SharePoll,SlotCard,formatDeadline,timeLeft,slotParts} from './poll-ui';
import {SlotPicker} from './slot-picker';
import { appUrl } from "@/lib/base";
export function useMeetingAccess(uid:string,profile:any):MeetingAccess {
 const [role,setRole]=useState<any>({}),[governance,setGovernance]=useState<any[]>([]);
 useEffect(()=>{if(!db||!uid)return;const r=onSnapshot(doc(db,'roles',uid),s=>setRole(s.exists()?s.data():{}),()=>setRole({}));const g=onSnapshot(query(collection(db,'governance'),limit(10)),s=>setGovernance(s.docs.map(d=>({id:d.id,...d.data()}))),()=>setGovernance([]));return()=>{r();g();};},[uid]);
 const owner=isPlatformOwner(auth?.currentUser);
 return useMemo(()=>({uid,role,governance,profile,admin:owner||isUnescoSecretariat(role)}),[uid,role,governance,profile,owner]);
}
export function useMeetingTools(access:MeetingAccess){
 const [polls,setPolls]=useState<MeetingPoll[]>([]),[shared,setShared]=useState<MeetingPoll[]>([]),[responses,setResponses]=useState<PollResponse[]>([]),[rhythms,setRhythms]=useState<any[]>([]),[capped,setCapped]=useState(false),[error,setError]=useState(''),[now,setNow]=useState(Date.now);
 const key=JSON.stringify(meetingBodies.map(b=>[b.id,bodyLevel(access,b.id)]));
 useEffect(()=>{setPolls([]);setRhythms([]);setError('');if(!access.uid||!access.profile)return;const fail=(e:any)=>setError(friendlyError(e));const p=subscribePolls(access,(x,c)=>{setPolls(x);setCapped(c);},fail),r=subscribeOwnResponses(access.uid,setResponses,fail),m=subscribeRhythms(access,setRhythms,fail);return()=>{p();r();m();};},[key,access.uid,!!access.profile]);
 useEffect(()=>{const t=setInterval(()=>setNow(Date.now()),60_000);return()=>clearInterval(t);},[]);
 // Polls answered through a shared link are outside the member's own audiences: load them by id.
 const tried=useRef(new Set<string>());
 useEffect(()=>{const missing=responses.map(r=>r.pollId).filter(id=>!polls.some(p=>p.id===id)&&!tried.current.has(id)).slice(0,20);if(!missing.length)return;missing.forEach(id=>tried.current.add(id));Promise.all(missing.map(id=>fetchPoll(id).catch(()=>null))).then(found=>{const ok=found.filter(Boolean) as MeetingPoll[];if(ok.length)setShared(s=>[...s.filter(x=>!ok.some(o=>o.id===x.id)),...ok]);});},[responses,polls]);
 const all=useMemo(()=>[...polls,...shared.filter(s=>!polls.some(p=>p.id===s.id))].sort((x,y)=>String(y.createdAt).localeCompare(String(x.createdAt))),[polls,shared]);
 const pending=polls.filter(p=>{const r=responses.find(x=>x.pollId===p.id);return p.status==='open'&&Date.parse(p.deadline)>now&&(!r||answerIncomplete(p,r));});
 const reminders=rhythms.map(r=>({...r,reminder:meetingReminder(r.events,r.baseline,now,polls.some(p=>p.body===r.id&&p.status==='open'&&Date.parse(p.deadline)>now))})).filter(r=>r.reminder);
 return {polls:all,sharedIds:shared.filter(s=>!polls.some(p=>p.id===s.id)).map(s=>s.id),responses,pending,reminders,capped,error};
}
export type MeetingTools=ReturnType<typeof useMeetingTools>;
const stamp=(v:string,zone:string)=>new Intl.DateTimeFormat('en-GB',{timeZone:zone,weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(new Date(v));
/** Hub notifications: mentions in Working Group discussions and meeting actions. */
export type NotifMessage={id:string;title:string;text:string;when:string;unread:boolean;group:boolean;uid?:string};
export type NotifTask={id:string;key:string;title:string;sub:string;state:'new'|'soon'|'overdue';body:string};
export type NotifUpdate={id:string;kind:'news'|'event'|'activity';title:string;sub:string;stamp:string;tag?:string;style?:React.CSSProperties;open:()=>void};
export function MeetingNotifications({tools,onPoll,onCreate,mentions=[],spaceLabel=(s:string)=>s,onMention,onReadAll,actions=[],onAction,consultations=[],onConsultation,messages=[],onMessage,onReadMessages,updates=[],tasks=[],onTask}:{tools:MeetingTools;onPoll:(id:string)=>void;onCreate:(body:string)=>void;mentions?:InboxItem[];spaceLabel?:(space:string)=>string;onMention?:(item:InboxItem)=>void;onReadAll?:()=>void;actions?:ActionItem[];onAction?:(a:ActionItem)=>void;consultations?:{id:string;title:string;body:string;deadline:string}[];onConsultation?:(id:string)=>void;messages?:NotifMessage[];onMessage?:(id:string)=>void;onReadMessages?:(ids:string[])=>void;updates?:NotifUpdate[];tasks?:NotifTask[];onTask?:(id:string)=>void}){
 // A notification leaves the list once it has been opened, once the member has dealt with it (message read, mention read,
 // poll or consultation answered, action completed), or, for group updates, once it has been seen in an earlier visit to the list.
 const uid=auth?.currentUser?.uid||'';
 const [open,setOpen]=useState(false);
 const seenKey='dacs-bell-seen-'+uid,doneKey='dacs-bell-dismissed-'+uid;
 const [seen,setSeen]=useState(()=>{try{return localStorage.getItem(seenKey)||'';}catch{return '';}});
 const [dismissed,setDismissed]=useState<string[]>(()=>{try{return JSON.parse(localStorage.getItem(doneKey)||'[]');}catch{return [];}});
 const dismiss=(...keys:string[])=>setDismissed(d=>{const next=[...d.filter(k=>!keys.includes(k)),...keys].slice(-400);try{localStorage.setItem(doneKey,JSON.stringify(next));}catch{}return next;});
 const shown=(k:string)=>!dismissed.includes(k);
 const close=(v:boolean)=>{setOpen(v);if(!v){const now=new Date().toISOString();setSeen(now);try{localStorage.setItem(seenKey,now);}catch{}}};
 const msgKey=(m:NotifMessage)=>'m:'+m.id+':'+m.when,actKey=(a:ActionItem)=>'a:'+a.id+':'+actionState(a),remKey=(r:{id:string;reminder:{urgent:boolean}})=>'r:'+r.id+':'+(r.reminder.urgent?'u':'n');
 const liveMessages=messages.filter(m=>m.unread&&shown(msgKey(m)));
 const liveMentions=mentions.filter(m=>!m.read&&shown('n:'+m.id));
 const liveActions=sortActions(actions.filter(a=>a.status==='open'&&shown(actKey(a))));
 const pollKey=(p:MeetingPoll)=>'p:'+p.id+(p.slots.length>1?':'+p.slots.length:''),livePolls=tools.pending.filter(p=>shown(pollKey(p))),liveConsultations=consultations.filter(c=>shown('c:'+c.id)),liveReminders=tools.reminders.filter(r=>shown(remKey(r)));
 const liveUpdates=updates.filter(u=>(!seen||u.stamp>seen)&&shown('u:'+u.id));
 const liveTasks=tasks.filter(t=>shown(t.key));
 const meetingCount=livePolls.length+liveConsultations.length+liveReminders.length;
 const count=liveTasks.length+liveMessages.length+liveMentions.length+liveActions.filter(a=>['overdue','soon'].includes(actionState(a))).length+meetingCount+liveUpdates.length;
 const total=liveTasks.length+liveMessages.length+liveMentions.length+liveActions.length+meetingCount+liveUpdates.length;
 const go=(key:string,run:()=>void)=>{dismiss(key);close(false);run();};
 const clearAll=()=>{dismiss(...liveTasks.map(t=>t.key),...liveMessages.map(msgKey),...liveMentions.map(m=>'n:'+m.id),...liveActions.map(actKey),...livePolls.map(pollKey),...liveConsultations.map(c=>'c:'+c.id),...liveReminders.map(remKey),...liveUpdates.map(u=>'u:'+u.id));if(liveMentions.length)onReadAll?.();if(liveMessages.length)onReadMessages?.(liveMessages.map(m=>m.id));};
 // Meeting reminders open a pop-up at sign-in (community.tsx); this message covers polls awaiting an answer.
 useEffect(()=>{const n=tools.pending.length;if(!n)return;const ids=tools.pending.map(p=>p.id).sort().join('|');let seen='';try{seen=sessionStorage.getItem('dacs-meeting-notice-'+uid)||'';}catch{}if(seen!==ids){try{sessionStorage.setItem('dacs-meeting-notice-'+uid,ids);}catch{}toast.info(`${n} meeting poll${n===1?' is':'s are'} awaiting your availability.`,{description:'Open the bell to answer.'});}},[tools.pending]);
 return <><button className="btn small meeting-bell" aria-label={`Notifications, ${count} waiting`} title="Notifications" onClick={()=>setOpen(true)}><Bell size={17}/>{count>0&&<span className="nav-count">{count>99?'99+':count}</span>}</button>
 <Dialog open={open} onOpenChange={close}><DialogContent className="detail-content notifications-dialog"><DialogTitle>Notifications</DialogTitle><DialogDescription>New tasks and close deadlines, messages, mentions, actions, meetings and consultations, and what is new in the Working Groups you follow. A notification leaves this list once you have opened it or dealt with it.</DialogDescription>
  {total>0&&<div className="notif-toolbar"><span className="micro">{total} {total===1?'notification':'notifications'}</span><button className="text-button" onClick={clearAll}><CheckCheck size={15}/> Clear all</button></div>}
  {total===0&&<div className="notif-empty"><span className="notif-empty-icon"><Check size={22}/></span><strong>You are all caught up</strong><p className="micro">New messages, mentions, polls and Working Group updates will appear here.</p></div>}
  {liveTasks.length>0&&<section className="notif-section" aria-labelledby="notif-tasks">
   <div className="notif-head"><h3 id="notif-tasks"><SquareKanban size={15}/> Tasks<span className="pill blue">{liveTasks.length}</span></h3></div>
   <div className="mention-list">{liveTasks.slice(0,8).map(t=><button className={'mention-item unread task-notif '+t.state} key={t.key} style={accentStyle({body:t.body})} onClick={()=>go(t.key,()=>onTask?.(t.id))}>
    <span className="notif-icon"><SquareKanban size={16}/></span>
    <span className="mention-text"><span className="update-kind">{t.state==='new'?'Assigned to you':t.state==='overdue'?'Overdue':'Deadline close'}</span><strong>{t.title}</strong><small>{t.sub} · Open the task</small></span>
    {t.state==='overdue'?<span className="pill amber">Overdue</span>:t.state==='soon'?<span className="pill blue">Due soon</span>:<span className="unread-dot" aria-label="New"/>}
   </button>)}</div>
  </section>}
  {liveMessages.length>0&&<section className="notif-section" aria-labelledby="notif-messages">
   <div className="notif-head"><h3 id="notif-messages"><MessageCircle size={15}/> Messages<span className="pill blue">{liveMessages.length} unread</span></h3></div>
   <div className="mention-list">{liveMessages.slice(0,6).map(m=><button className="mention-item unread" key={m.id} onClick={()=>go(msgKey(m),()=>onMessage?.(m.id))}>
    {m.group?<span className="notif-icon"><Users size={16}/></span>:<MemberAvatar name={m.title} uid={m.uid}/>}
    <span className="mention-text"><strong>{m.title}</strong><small className="mention-excerpt">{m.text}</small><small>{timeAgo(m.when)} · Open the conversation</small></span>
    <span className="unread-dot" aria-label="Unread"/>
   </button>)}</div>
  </section>}
  {liveMentions.length>0&&<section className="notif-section" aria-labelledby="notif-mentions">
   <div className="notif-head"><h3 id="notif-mentions"><AtSign size={15}/> Mentions<span className="pill blue">{liveMentions.length} unread</span></h3>{onReadAll&&<button className="text-button" onClick={onReadAll}>Mark all as read</button>}</div>
   <div className="mention-list">{liveMentions.slice(0,15).map(m=><button className="mention-item unread" key={m.id} onClick={()=>go('n:'+m.id,()=>onMention?.(m))}>
    <MemberAvatar name={m.from_name} uid={m.from}/>
    <span className="mention-text"><span><strong>{m.from_name}</strong> mentioned you in <strong>{spaceLabel(m.space)}</strong></span><small className="mention-excerpt">{m.excerpt}</small><small>{timeAgo(m.createdAt)} · Open to reply</small></span>
    <span className="unread-dot" aria-label="Unread"/>
   </button>)}</div>
  </section>}
  {liveActions.length>0&&<section className="notif-section" aria-labelledby="notif-actions">
   <div className="notif-head"><h3 id="notif-actions"><ClipboardCheck size={15}/> Your actions<span className="pill blue">{liveActions.length} open</span></h3></div>
   <div className="mention-list">{liveActions.slice(0,8).map(a=><button className={'mention-item'+(['overdue','soon'].includes(actionState(a))?' unread':'')} key={a.id} onClick={()=>go(actKey(a),()=>onAction?.(a))}>
    <span className="notif-icon"><ClipboardCheck size={16}/></span>
    <span className="mention-text"><strong>{a.title}</strong><small>{bodyLabel(a.body)}{a.due?' · due '+new Date(a.due+'T12:00:00Z').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):''} · Open the meeting</small></span>
    {actionState(a)==='overdue'?<span className="pill amber">Overdue</span>:actionState(a)==='soon'?<span className="pill blue">Due soon</span>:<span/>}
   </button>)}</div>
  </section>}
  {meetingCount>0&&<section className="notif-section" aria-labelledby="notif-meetings">
   <div className="notif-head"><h3 id="notif-meetings"><CalendarDays size={15}/> Meetings and consultations<span className="pill blue">{meetingCount}</span></h3></div>
   {livePolls.map(p=><button className="calendar-event" key={p.id} onClick={()=>go(pollKey(p),()=>onPoll(p.id))}><strong>{p.title}</strong><span>{bodyLabel(p.body)} · {typeLabel(p.meetingType)}</span><span>{tools.responses.some(r=>r.pollId===p.id)?'New times were added · complete your availability':'Choose your available times'}</span></button>)}
   {liveConsultations.map(c=><button className="calendar-event" key={c.id} onClick={()=>go('c:'+c.id,()=>onConsultation?.(c.id))}><strong>{c.title}</strong><span>{bodyLabel(c.body)} · Consultation</span><span>Your answer is awaited · closes {new Date(c.deadline).toLocaleDateString('en-GB',{day:'numeric',month:'short'})}</span></button>)}
   {liveReminders.map(r=><div className={`meeting-reminder ${r.reminder.urgent?'urgent':''}`} key={r.id}><strong>{bodyLabel(r.id)} · {r.reminder.days} days without a meeting</strong><p>{r.reminder.urgent?'Four weeks have passed.':'It is time to plan the next meeting.'}</p><button className="btn primary" onClick={()=>go(remKey(r),()=>onCreate(r.id))}>Start a scheduling poll</button></div>)}
  </section>}
  {liveUpdates.length>0&&<section className="notif-section" aria-labelledby="notif-updates">
   <div className="notif-head"><h3 id="notif-updates"><Newspaper size={15}/> In the groups you follow<span className="pill blue">{liveUpdates.length} new</span></h3></div>
   <div className="mention-list">{liveUpdates.slice(0,12).map(u=><button className="mention-item update ev unread" key={u.id} style={u.style} onClick={()=>go('u:'+u.id,u.open)}>
    <span className={'notif-icon kind-'+u.kind}>{u.kind==='news'?<Newspaper size={16}/>:u.kind==='event'?<CalendarDays size={16}/>:<Briefcase size={16}/>}</span>
    <span className="mention-text"><span className="update-kind">{u.kind==='news'?'News':u.kind==='event'?'Upcoming event':'New activity'}{u.tag&&<span className="ev-tag">{u.tag}</span>}</span><strong>{u.title}</strong><small>{u.sub}</small></span>
    <span className="unread-dot" aria-label="New"/>
   </button>)}</div>
  </section>}
 </DialogContent></Dialog></>;
}
async function copyLink(id:string){const link=pollLink(appUrl(),id);try{await navigator.clipboard.writeText(link);toast.success('Poll link copied.');}catch{toast.info(link);}}
export function MeetingHub({access,tools,focusId,createBody,onSchedule}:{access:MeetingAccess;tools:MeetingTools;focusId?:string;createBody?:string;onSchedule:(s:MeetingSeed)=>void}){
 const leaders=leadershipBodies(access);const {zone}=useTimeZone(access.uid);
 const [selected,setSelected]=useState(focusId||''),[creating,setCreating]=useState(!!createBody),[filter,setFilter]=useState('');
 useEffect(()=>{if(focusId)setSelected(focusId);},[focusId]);useEffect(()=>{if(createBody)setCreating(true);},[createBody]);
 const poll=tools.polls.find(p=>p.id===selected);
 const answered=(id:string)=>tools.responses.some(r=>r.pollId===id);
 const visible=tools.polls.filter(p=>!filter||p.body===filter);
 return <section className="meeting-hub">
  <div className="hub-toolbar">
   <label className="meeting-filter">Show polls for<select aria-label="Body" value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All my affiliations</option>{meetingBodies.filter(b=>bodyLevel(access,b.id)>0).map(b=><option key={b.id} value={b.id}>{b.label}</option>)}</select></label>
   {leaders.length>0&&<button className="btn primary" onClick={()=>setCreating(true)}><Plus size={16}/> Create a scheduling poll</button>}
  </div>
  {tools.error&&<p className="error-banner" role="alert">{tools.error}</p>}
  {tools.capped&&<p className="notice">Showing the latest 40 polls per body.</p>}
  {tools.reminders.map(r=><div className={`meeting-reminder ${r.reminder.urgent?'urgent':''}`} key={r.id}><strong>{bodyLabel(r.id)}: {r.reminder.days} days without a meeting</strong><button className="btn" onClick={()=>{setFilter(r.id);setCreating(true);}}>Plan a meeting</button></div>)}
  <div className="cards cols2">{visible.map(p=>{const open=p.status==='open'&&Date.parse(p.deadline)>Date.now();return <article className="glass op-card poll-card clickable-card ev" key={p.id} style={accentStyle({body:p.body})}>
   <div className="card-tags"><span className="ev-tag">{eventAccent({body:p.body}).tag}</span><span className="pill">{typeLabel(p.meetingType)}</span><span className={'pill '+(open?'green':p.status==='scheduled'?'blue':'')}>{p.status==='open'&&!open?'Response period ended':p.status==='open'?'Open':p.status==='scheduled'?'Scheduled':'Closed'}</span>{tools.sharedIds.includes(p.id)&&<span className="pill amber">Shared with you</span>}</div>
   <h3>{p.title}</h3>
   <CreatedBy uid={p.owner} at={p.createdAt}/>
   <div className="op-meta"><span><CalendarDays size={14}/>{p.slots.length} proposed {p.slots.length===1?'time':'times'}</span><span><Clock size={14}/>{p.durationMinutes} minutes</span>{p.linkAccess&&<span><Link2 size={14}/>Link sharing on</span>}</div>
   <p className="micro">{open?`Reply by ${stamp(p.deadline,zone)} · ${timeLeft(p.deadline)}`:`Closed ${stamp(p.deadline,zone)}`}</p>
   <div className="card-footer"><span>{answered(p.id)?<><Check size={13}/>You have answered</>:open?'Your answer is awaited':''}</span><div className="row">{p.linkAccess&&<button className="btn small icon" aria-label={'Copy the link to '+p.title} title="Copy poll link" onClick={()=>copyLink(p.id)}><Copy size={14}/></button>}<button className="btn small stretch" onClick={()=>setSelected(p.id)}>{p.status==='scheduled'?'View results':answered(p.id)||!open?'Open poll':'Vote'} <ArrowRight size={14}/></button></div></div>
  </article>;})}</div>
  {!tools.polls.length&&!tools.error&&<div className="glass empty-state"><CalendarDays size={30}/><h3>No meeting polls yet</h3><p>{leaders.length?'Create a scheduling poll: propose a few times, share the link, and pick the time that suits most people.':'A poll appears here when an organiser invites your group or shares a poll link with you.'}</p>{leaders.length>0&&<button className="btn primary" onClick={()=>setCreating(true)}><Plus size={16}/> Create a scheduling poll</button>}</div>}
  {poll&&<PollDetail poll={poll} access={access} ownResponse={tools.responses.find(r=>r.pollId===poll.id)} onClose={()=>setSelected('')} onSchedule={s=>{setSelected('');onSchedule(s);}}/>}
  <PollComposer open={creating} onClose={()=>setCreating(false)} access={access} initialBody={createBody||filter} polls={tools.polls} onOpenPoll={id=>{setCreating(false);setSelected(id);}}/>
 </section>;
}

const audiences=[
 {id:'leadership',label:'Leadership',text:'Leads, Associate Leads, Secretariat and chairpersons'},
 {id:'core',label:'Core Group',text:'Leadership and appointed Core Group members'},
 {id:'broad',label:'Broad Group',text:'Every affiliated member of the body'},
] as const;
const durations=[30,45,60,90,120];
const timeChips=['08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00'];
const deadlineModes=[{id:'auto',label:'Automatic'},{id:'2',label:'In 2 days'},{id:'3',label:'In 3 days'},{id:'7',label:'In 1 week'},{id:'custom',label:'Choose a date'}] as const;
type Draft={title:string;notes:string;body:string;meetingType:'leadership'|'core'|'broad';durationMinutes:number;mgs:string[];slots:string[];linkAccess:boolean};
const quarter=(t:number)=>Math.ceil(t/900000)*900000;
const durationLabel=(d:number)=>d<60?d+' min':d%60?`${Math.floor(d/60)} h ${d%60}`:`${d/60} h`;

/** Guided poll creation in three steps: meeting, proposed times, review and publish; then share. */
function PollComposer({open,onClose,access,initialBody,polls,onOpenPoll}:{open:boolean;onClose:()=>void;access:MeetingAccess;initialBody?:string;polls:MeetingPoll[];onOpenPoll:(id:string)=>void}){
 const leaders=leadershipBodies(access);const {zone:preferredZone}=useTimeZone(access.uid);
 const [zone,setZone]=useState(preferredZone),[step,setStep]=useState(0),[draft,setDraft]=useState<Draft|null>(null);
 const [otherDuration,setOtherDuration]=useState(false);
 const [deadlineMode,setDeadlineMode]=useState<string>('auto'),[customDeadline,setCustomDeadline]=useState('');
 const [saving,setSaving]=useState(false),[error,setError]=useState(''),[createdId,setCreatedId]=useState('');
 useEffect(()=>{if(open){setZone(preferredZone);setStep(0);setError('');setCreatedId('');setOtherDuration(false);setDeadlineMode('auto');setCustomDeadline('');
  const body=leaders.some(b=>b.id===initialBody)?initialBody!:leaders[0]?.id||'';
  setDraft({title:'',notes:'',body,meetingType:'leadership',durationMinutes:60,mgs:[],slots:[],linkAccess:true});}},[open]);
 if(!draft)return null;
 const d=draft;
 const patch=(v:Partial<Draft>)=>{setDraft({...d,...v});setError('');};
 const sorted=[...d.slots].sort();
 const first=sorted.length?Date.parse(sorted[0]):NaN;
 function deadline():string{
  if(deadlineMode==='custom'){const c=timeCandidates(customDeadline,zone);return c.length===1?c[0]:'';}
  const days=deadlineMode==='auto'?3:Number(deadlineMode);let t=Date.now()+days*86400000;
  if(deadlineMode==='auto'&&Number.isFinite(first))t=Math.min(t,first-2*3600000);
  return new Date(quarter(t)).toISOString();
 }
 const due=deadline();
 const deadlineProblem=!sorted.length?'':!due?'Choose a valid response deadline.':Date.parse(due)<=Date.now()+5*60000?'The first proposed time is too soon to collect answers. Choose later times or another deadline.':Date.parse(due)>=first?'Responses must close before the first proposed time.':'';
 function changeZone(next:string){const c=timeCandidates(customDeadline,zone);if(c.length===1)setCustomDeadline(localInput(c[0],next));setZone(next);}
 const grouped=sorted.reduce((m,s)=>{const k=localInput(s,zone).slice(0,10);(m[k]=m[k]||[]).push(s);return m;},{} as Record<string,string[]>);
 const canNext=step===0?!!d.title.trim()&&!!d.body&&d.durationMinutes>=15&&d.durationMinutes<=480:step===1?sorted.length>0&&!deadlineProblem:true;
 async function publish(){setSaving(true);setError('');try{const id=await savePoll({title:d.title,notes:d.notes,body:d.body,meetingType:d.meetingType,durationMinutes:d.durationMinutes,mgs:d.mgs,slots:sorted,deadline:due,linkAccess:d.linkAccess});setCreatedId(id);setStep(3);toast.success('Poll published.');}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 const created:MeetingPoll|undefined=createdId?(polls.find(p=>p.id===createdId)||{id:createdId,owner:access.uid,title:d.title.trim(),body:d.body,meetingType:d.meetingType,mgs:d.mgs,durationMinutes:d.durationMinutes,slots:sorted,deadline:due,status:'open',selectedSlot:-1,eventId:'',createdAt:'',updatedAt:'',linkAccess:d.linkAccess,notes:d.notes}):undefined;
 const steps=['Meeting','Proposed times','Review and publish'];
 return <Dialog open={open} onOpenChange={v=>!v&&!saving&&onClose()}><DialogContent className="detail-content composer-dialog">
  <DialogTitle>{step===3?'Your poll is ready to share':'Create a scheduling poll'}</DialogTitle>
  <DialogDescription>{step===3?'Send the link to the people you want to invite. Eligible members also receive a Hub notification.':'Propose a few times, share one link, and see which time suits most people.'}</DialogDescription>
  {step<3&&<ol className="composer-steps" aria-label="Poll creation steps">{steps.map((s,i)=><li key={s} className={i===step?'current':i<step?'done':''} aria-current={i===step?'step':undefined}><span>{i<step?<Check size={14}/>:i+1}</span>{s}</li>)}</ol>}
  {step===0&&<div className="composer-step" key="s0">
   <label className="field"><span>Meeting title</span><input autoFocus required maxLength={160} placeholder="For example: WG4 Core Group meeting, November" value={d.title} onChange={e=>patch({title:e.target.value})}/></label>
   <label className="field"><span>Details <small className="micro">(optional)</small></span><textarea rows={2} maxLength={1000} placeholder="Purpose of the meeting, agenda items, or anything participants should know" value={d.notes} onChange={e=>patch({notes:e.target.value})}/></label>
   {leaders.length>1?<label className="field"><span>Organising body</span><select aria-label="Organising body" value={d.body} onChange={e=>patch({body:e.target.value,mgs:[]})}>{leaders.map(b=><option key={b.id} value={b.id}>{b.label}</option>)}</select></label>:<p className="micro">Organising body: <b>{bodyLabel(d.body)}</b></p>}
   <fieldset className="choice-cards"><legend>Who is notified in the Hub</legend>{audiences.map(a=><label key={a.id} className={'choice-card'+(d.meetingType===a.id?' on':'')}><input type="radio" name="audience" checked={d.meetingType===a.id} onChange={()=>patch({meetingType:a.id})}/><span><strong>{a.label}</strong><small>{a.text}</small></span></label>)}</fieldset>
   <fieldset className="chip-field"><legend>Duration</legend><div className="chip-row">{durations.map(x=><button type="button" key={x} className={'chip'+(!otherDuration&&d.durationMinutes===x?' on':'')} aria-pressed={!otherDuration&&d.durationMinutes===x} onClick={()=>{setOtherDuration(false);patch({durationMinutes:x});}}>{durationLabel(x)}</button>)}<button type="button" className={'chip'+(otherDuration?' on':'')} aria-pressed={otherDuration} onClick={()=>setOtherDuration(true)}>Other</button>{otherDuration&&<label className="inline-number"><input type="number" min={15} max={480} step={15} value={d.durationMinutes} onChange={e=>patch({durationMinutes:Number(e.target.value)})} aria-label="Duration in minutes"/> minutes</label>}</div></fieldset>
   <details className="composer-more"><summary>Link the meeting to main goals <span className="micro">(optional)</span></summary><GoalPicker label="Main goals discussed" value={d.mgs} onChange={mgs=>patch({mgs})}/></details>
  </div>}
  {step===1&&<div className="composer-step" key="s1">
   <TimeZonePicker label="Time zone of the proposed times" value={zone} onChange={changeZone}/>
   <SlotPicker zone={zone} slots={d.slots} max={12} onChange={slots=>setDraft({...d,slots})} onError={setError}/>
   <div className="proposed-list" aria-live="polite">
    <div className="proposed-head"><strong>Proposed times</strong><span className="micro">{sorted.length} of 12 · {durationLabel(d.durationMinutes)} each</span></div>
    {!sorted.length&&<p className="micro">Select days in the calendar, then click the start times to propose on each of them.</p>}
    {Object.entries(grouped).map(([k,list])=><div className="proposed-day" key={k}><span>{slotParts(list[0],d.durationMinutes,zone).long}<button type="button" className="text-button micro" onClick={()=>patch({slots:d.slots.filter(x=>!list.includes(x))})}>Remove this day</button></span><div className="chip-row">{list.map(s=><span className="chip on removable" key={s}>{slotParts(s,d.durationMinutes,zone).range}<button type="button" aria-label={'Remove '+stamp(s,zone)} onClick={()=>patch({slots:d.slots.filter(x=>x!==s)})}>×</button></span>)}</div></div>)}
   </div>
   {sorted.length>0&&<fieldset className="chip-field"><legend>Responses close</legend><div className="chip-row">{deadlineModes.map(m=><button type="button" key={m.id} className={'chip'+(deadlineMode===m.id?' on':'')} aria-pressed={deadlineMode===m.id} onClick={()=>{setDeadlineMode(m.id);setError('');if(m.id==='custom'&&!customDeadline&&due)setCustomDeadline(localInput(due,zone));}}>{m.label}</button>)}</div>
    {deadlineMode==='custom'&&<input type="datetime-local" aria-label="Response deadline" value={customDeadline} onChange={e=>setCustomDeadline(e.target.value)}/>}
    {due&&!deadlineProblem&&<p className="micro">Responses close <b>{formatDeadline(due,zone)}</b>{deadlineMode==='auto'?'. Automatic: three days from now, or two hours before the first time if that is sooner.':'.'}</p>}
    {deadlineProblem&&<p className="calendar-validation">{deadlineProblem}</p>}
   </fieldset>}
  </div>}
  {step===2&&<div className="composer-step" key="s2">
   <dl className="review-list">
    <div><dt>Meeting</dt><dd>{d.title}</dd></div>
    {d.notes.trim()&&<div><dt>Details</dt><dd className="pre-line">{d.notes.trim()}</dd></div>}
    <div><dt>Organiser</dt><dd>{bodyLabel(d.body)} · {typeLabel(d.meetingType)} · {durationLabel(d.durationMinutes)}</dd></div>
    <div><dt>Proposed times</dt><dd><ul>{sorted.map(s=><li key={s}>{slotParts(s,d.durationMinutes,zone).long}, {slotParts(s,d.durationMinutes,zone).range}</li>)}</ul></dd></div>
    <div><dt>Responses close</dt><dd>{formatDeadline(due,zone)}</dd></div>
    {d.mgs.length>0&&<div><dt>Main goals</dt><dd><GoalLabels value={d.mgs}/></dd></div>}
   </dl>
   <label className={'switch-card'+(d.linkAccess?' on':'')}><input type="checkbox" checked={d.linkAccess} onChange={e=>patch({linkAccess:e.target.checked})}/><span className="switch" aria-hidden="true"/><span><strong>Anyone with the link can vote</strong><small>People who open the link sign in or create an account, then answer. They do not need an appointment in {bodyLabel(d.body)}. You can turn the link off at any time.</small></span></label>
   <p className="notice"><span><Info size={15} style={{display:'inline',verticalAlign:'-2px',marginRight:6}}/>{typeLabel(d.meetingType)} participants of {bodyLabel(d.body)} also receive a Hub notification. After publication, you can still edit the title, the details and the deadline, add times and withdraw times. The duration and audience stay as published.</span></p>
  </div>}
  {step===3&&created&&<div className="composer-step composer-done" key="s3">
   <div className="done-mark" aria-hidden="true"><Check size={28}/></div>
   <SharePoll poll={created} zone={zone} canManage/>
   {!created.linkAccess&&<p className="micro">Only invited {bodyLabel(created.body)} participants can open this poll, from the Hub.</p>}
  </div>}
  {error&&<p className="error-banner" role="alert">{error}</p>}
  <div className="composer-actions">
   {step>0&&step<3&&<button type="button" className="btn" disabled={saving} onClick={()=>{setStep(step-1);setError('');}}><ChevronLeft size={16}/> Back</button>}
   <span className="spacer"/>
   {step<2&&<button type="button" className="btn primary" disabled={!canNext} onClick={()=>{setStep(step+1);setError('');}}>Continue <ArrowRight size={16}/></button>}
   {step===2&&<button type="button" className="btn primary" disabled={saving} onClick={publish}>{saving?'Publishing…':'Publish poll'}</button>}
   {step===3&&<><button type="button" className="btn" onClick={()=>onOpenPoll(createdId)}>Open the poll</button><button type="button" className="btn primary" onClick={onClose}>Done</button></>}
  </div>
 </DialogContent></Dialog>;
}

function PollDetail({poll,access,ownResponse,onClose,onSchedule}:{poll:MeetingPoll;access:MeetingAccess;ownResponse?:PollResponse;onClose:()=>void;onSchedule:(s:MeetingSeed)=>void}){
 const {zone,setZone,automatic,useDevice}=useTimeZone(access.uid);const [responses,setResponses]=useState<PollResponse[]>([]),[answers,setAnswers]=useState<(string|null)[]>(poll.slots.map(()=>null)),[dirty,setDirty]=useState(false),[saving,setSaving]=useState(false),[error,setError]=useState(''),[compareZone,setCompareZone]=useState('Asia/Tokyo'),[editing,setEditing]=useState(false);
 const own=ownResponse||responses.find(r=>r.uid===access.uid),ranked=rankSlots(poll,responses.slice(0,200)),organiser=canOrganise(access,poll.body),canVote=poll.status==='open'&&Date.parse(poll.deadline)>Date.now();
 const active=activeSlots(poll),n=poll.slots.length;
 useEffect(()=>subscribeResponses(poll.id,setResponses,e=>setError(friendlyError(e))),[poll.id]);useEffect(()=>{if(own&&!dirty)setAnswers(padAnswers(own.answers,n));else if(!dirty)setAnswers(a=>padAnswers(a,n));},[own,dirty,n]);
 const zones=[...new Set([zone,'UTC',compareZone,...responses.map(r=>r.timeZone)])].filter(z=>{try{new Intl.DateTimeFormat('en',{timeZone:z});return true;}catch{return false;}}).slice(0,8);
 const answeredCount=active.filter(x=>answers[x.index]).length,best=responses.length?ranked[0]?.index:-1;
 async function vote(){setSaving(true);setError('');try{await respond(poll,completeAnswers(padAnswers(answers,n).map((v,i)=>(poll.withdrawn||[]).includes(i)?null:v)),access.profile.name,zone);setDirty(false);toast.success('Availability saved.');}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 async function close(){setSaving(true);try{await closePoll(poll.id);toast.success('Poll closed.');}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 const set=(index:number,v:string)=>{setAnswers(padAnswers(answers,n).map((x,i)=>i===index?v:x));setDirty(true);};
 const setAll=(v:string|null)=>{setAnswers(padAnswers(answers,n).map((x,i)=>active.some(a=>a.index===i)?v:x));setDirty(true);};
 const incomplete=canVote&&answerIncomplete(poll,own);
 return <Dialog open onOpenChange={v=>!v&&!saving&&onClose()}><DialogContent className="detail-content poll-dialog"><DialogTitle>{poll.title}</DialogTitle><DialogDescription>{bodyLabel(poll.body)} · {typeLabel(poll.meetingType)} · {poll.durationMinutes} minutes</DialogDescription><CreatedBy uid={poll.owner} at={poll.createdAt}/>
  <div className="poll-meta-row"><span className={'pill '+(canVote?'green':poll.status==='scheduled'?'blue':'')}>{canVote?'Open':poll.status==='scheduled'?'Scheduled':'Closed'}</span><span className="micro"><Clock size={13}/> {canVote?`Responses close ${formatDeadline(poll.deadline,zone)} · ${timeLeft(poll.deadline)}`:`Closed ${formatDeadline(poll.deadline,zone)}`}</span><span className="micro"><Users size={13}/> {Math.min(responses.length,200)} {responses.length===1?'response':'responses'}</span>{organiser&&<button type="button" className="btn small poll-edit-btn" onClick={()=>setEditing(true)}><Pencil size={14}/> Edit the poll</button>}</div>
  {poll.notes&&<p className="poll-notes">{poll.notes}</p>}
  {incomplete&&<p className="notice poll-incomplete"><span><Info size={15} style={{display:'inline',verticalAlign:'-2px',marginRight:6}}/>New times were proposed after your answer. Please give your availability for them and save again.</span></p>}
  <SharePoll poll={poll} zone={zone} canManage={organiser}/>
  <div className="calendar-form-grid"><TimeZonePicker label="Your time zone" value={zone} onChange={setZone} automatic={automatic} onAutomatic={useDevice}/><TimeZonePicker label="Compare another time zone" value={compareZone} onChange={setCompareZone}/></div>
  {canVote&&<div className="vote-helper"><span>{answeredCount} of {active.length} answered. Times left blank are recorded as unavailable.</span><button type="button" className="text-button" onClick={()=>setAll('yes')}>Available for all</button><button type="button" className="text-button" onClick={()=>setAll(null)}>Clear</button></div>}
  <div className="poll-slots">{active.map(({start:s,index})=>{const summary=ranked.find(r=>r.index===index)!;return <SlotCard key={s} start={s} minutes={poll.durationMinutes} zone={zone} answer={answers[index]} onAnswer={canVote?v=>set(index,v):undefined} disabled={saving} yes={summary.yes} maybe={summary.maybe} total={Math.min(responses.length,200)} best={best===index}>
   <div className="timezone-chips">{zones.map(z=><span className={outsideWorkingHours(s,poll.durationMinutes,z)?'outside-hours':''} key={z}>{z.replaceAll('_',' ')}<b>{localInput(s,z).replace('T',' · ')}</b>{outsideWorkingHours(s,poll.durationMinutes,z)&&<small>Outside 08:00–19:00</small>}</span>)}</div>
   {summary.outside>0&&<p className="micro">{summary.outside} participant time {summary.outside===1?'zone is':'zones are'} outside 08:00–19:00 at this time.</p>}
   {responses.some(r=>index>=r.answers.length)&&<p className="micro">Added after {responses.filter(r=>index>=r.answers.length).length} of the responses.</p>}
   {organiser&&poll.status!=='scheduled'&&<button className="btn small primary schedule-btn" disabled={saving||Date.parse(s)<=Date.now()} onClick={()=>onSchedule({title:poll.title,body:poll.body,meetingType:poll.meetingType,mgs:poll.mgs,startAt:s,endAt:new Date(Date.parse(s)+poll.durationMinutes*60000).toISOString(),pollId:poll.id,selectedSlot:index})}><CalendarDays size={14}/> Schedule this time</button>}
  </SlotCard>;})}</div>
  <p className="micro">No single time suits every time zone. Compare local hours and rotate inconvenient slots between meetings.</p><GoalLabels value={poll.mgs}/>
  {responses.length>0&&<details><summary>{Math.min(responses.length,200)} participant responses{responses.length>200?' · display limit reached':''}</summary><div className="response-list">{responses.slice(0,200).map(r=><p key={r.id}><strong>{r.name}</strong> · {r.timeZone}<br/>{active.map(({start,index})=>{const v=r.answers[index];const sp=slotParts(start,poll.durationMinutes,zone);return `${sp.weekday} ${sp.day} ${sp.month} ${sp.range.split("–")[0]}: ${v===undefined?'not answered yet':v==='yes'?'available':v==='if-needed'?'if needed':'unavailable'}`;}).join(' · ')}</p>)}</div></details>}
  {poll.status==='scheduled'&&<p className="notice"><span><Check size={15} style={{display:'inline',verticalAlign:'-2px'}}/> Meeting published in the Calendar.</span></p>}
  {error&&<p className="error-banner" role="alert">{error}</p>}
  <div className="poll-actions">{canVote&&<button className="btn primary" disabled={saving} onClick={vote}>{saving?'Saving…':own?'Update my availability':'Save my availability'}</button>}{organiser&&poll.status==='open'&&<button className="btn" disabled={saving} onClick={close}>Close poll</button>}{access.admin&&<button className="btn" disabled={saving||poll.status==='scheduled'} title={poll.status==='scheduled'?'Remove its calendar meeting before deleting this poll.':undefined} onClick={async()=>{if(!confirm('Delete this poll?'))return;try{await deletePoll(poll.id);onClose();}catch(e){setError(friendlyError(e));}}}><Trash2 size={14}/> Delete poll</button>}<span className="spacer"/><button className="btn" onClick={onClose}>Close</button></div>
  {editing&&<PollEditor poll={poll} zone={zone} responses={responses.length} onClose={()=>setEditing(false)}/>}
 </DialogContent></Dialog>;
}

/** Organisers edit a published poll: title, details, deadline, new times and withdrawn times. */
function PollEditor({poll,zone,responses,onClose}:{poll:MeetingPoll;zone:string;responses:number;onClose:()=>void}){
 const [title,setTitle]=useState(poll.title),[notes,setNotes]=useState(poll.notes||''),[added,setAdded]=useState<string[]>([]),[withdrawn,setWithdrawn]=useState<number[]>(poll.withdrawn||[]);
 const [deadline,setDeadline]=useState(localInput(poll.deadline,zone)),[saving,setSaving]=useState(false),[error,setError]=useState(''),[adding,setAdding]=useState(false);
 const open=poll.status==='open';
 const existing=poll.slots.map((start,index)=>({start,index})).sort((a,b)=>a.start.localeCompare(b.start));
 const activeCount=existing.filter(x=>!withdrawn.includes(x.index)).length+added.length;
 const due=(()=>{const c=timeCandidates(deadline,zone);return c[0]||'';})();
 const upcoming=[...existing.filter(x=>!withdrawn.includes(x.index)).map(x=>x.start),...added].filter(x=>Date.parse(x)>Date.now()).sort()[0];
 const deadlineProblem=open&&due&&upcoming&&Date.parse(due)>=Date.parse(upcoming);
 const fixDeadline=()=>{const t=Math.max(Date.now()+15*60000,Date.parse(upcoming!)-2*3600000);setDeadline(localInput(new Date(Math.ceil(t/900000)*900000).toISOString(),zone));};
 async function save(){setSaving(true);setError('');try{await updatePoll(poll,{title,notes,deadline:due||poll.deadline,added:[...added].sort(),withdrawn});toast.success(added.length&&responses?'Poll updated. Members who already answered are asked to complete their availability.':'Poll updated.');onClose();}catch(e){setError(friendlyError(e));}finally{setSaving(false);}}
 return <Dialog open onOpenChange={v=>!v&&!saving&&onClose()}><DialogContent className="detail-content composer-dialog poll-editor">
  <DialogTitle><Pencil size={18}/> Edit the poll</DialogTitle>
  <DialogDescription>{bodyLabel(poll.body)} · {typeLabel(poll.meetingType)} · {durationLabel(poll.durationMinutes)} each. Times are shown in {zone.replaceAll('_',' ')}.</DialogDescription>
  <label className="field"><span>Meeting title</span><input maxLength={160} value={title} onChange={e=>setTitle(e.target.value)}/></label>
  <label className="field"><span>Details <small className="micro">(optional)</small></span><textarea rows={3} maxLength={1000} value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Purpose of the meeting, agenda items, or anything participants should know"/></label>
  <label className="field"><span>Responses close</span><input type="datetime-local" value={deadline} onChange={e=>setDeadline(e.target.value)}/>{due&&<small className="micro">{formatDeadline(due,zone)}</small>}</label>
  {deadlineProblem&&<p className="calendar-validation">Responses must close before the first proposed time ({formatDeadline(upcoming!,zone)}). <button type="button" className="text-button" onClick={fixDeadline}>Close two hours before it</button></p>}
  {open?<>
   <div className="proposed-list">
    <div className="proposed-head"><strong>Proposed times</strong><span className="micro">{activeCount} of 12 active</span></div>
    {existing.map(({start,index})=>{const off=withdrawn.includes(index),p=slotParts(start,poll.durationMinutes,zone);return <div className={'edit-slot'+(off?' off':'')} key={start}><span><b>{p.long}</b> · {p.range}</span>{off?<button type="button" className="text-button" onClick={()=>setWithdrawn(withdrawn.filter(i=>i!==index))}>Restore</button>:<button type="button" className="text-button danger" disabled={activeCount<=1} onClick={()=>setWithdrawn([...withdrawn,index])}>Withdraw</button>}</div>;})}
    {[...added].sort().map(s=>{const p=slotParts(s,poll.durationMinutes,zone);return <div className="edit-slot new" key={s}><span><b>{p.long}</b> · {p.range}<span className="pill green">New</span></span><button type="button" className="text-button" onClick={()=>setAdded(added.filter(x=>x!==s))}>Remove</button></div>;})}
    <p className="micro">Withdrawn times disappear from the poll; answers already given to the other times are kept.{responses>0?' Members who already answered are asked to give their availability for new times.':''}</p>
   </div>
   {adding?<SlotPicker zone={zone} slots={added} locked={poll.slots.filter((_,i)=>!withdrawn.includes(i))} max={12} onChange={setAdded} onError={setError}/>:<button type="button" className="btn" onClick={()=>setAdding(true)}><Plus size={15}/> Add times</button>}
  </>:<p className="micro">The poll is {poll.status==='scheduled'?'scheduled':'closed'}: its times can no longer change.</p>}
  {error&&<p className="error-banner" role="alert">{error}</p>}
  <div className="composer-actions"><button type="button" className="btn" disabled={saving} onClick={onClose}>Cancel</button><span className="spacer"/><button type="button" className="btn primary" disabled={saving||!title.trim()||!!deadlineProblem} onClick={save}>{saving?'Saving…':'Save the changes'}</button></div>
 </DialogContent></Dialog>;
}
