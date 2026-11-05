import {EventAttendance} from './event-attendance';
import {CreatedBy} from './people-context';
import {useEffect, useMemo, useState} from 'react';
import {CalendarDays, ChevronLeft, ChevronRight, Plus, ArrowUpRight, Pencil, Trash2, Clock3, Lock, Globe2, MapPin, Users, AlignLeft, Target, Paperclip} from 'lucide-react';
import {groups} from '@/lib/data';
import {eventAccent,accentStyle,eventTiming,durationLabel,groupColor} from '@/lib/event-style';
import {bodyTitle} from '@/lib/profile-options';
import {AttachmentList,AttachmentPicker,shareBody} from './attachments';
import {cleanAttachments,type Attachment} from '@/lib/files-store';
import {Dialog, DialogContent, DialogTitle, DialogDescription} from '@/components/ui/dialog';
import {challenges, mainGoals, localInput, timeCandidates, monthGrid, shiftMonth, gridRange, type CalendarEvent} from '@/lib/calendar';
import {subscribeEvents, saveEvent, removeEvent} from '@/lib/calendar-store';
import {friendlyError} from '@/lib/store';
import {challengeLabel,goalLabel,linkedGroups,isDecadeWide} from '@/lib/decade-goals';
import {GoalPicker,GoalLabels} from './goal-picker';
import {doc,getDoc} from 'firebase/firestore';
import {db} from '@/lib/firebase';
import {meetingTypes,bodyLabel,typeLabel,canOrganise,canAttend,leadershipBodies,type MeetingAccess,type MeetingSeed} from '@/lib/meetings';
import {MeetingAgenda} from './meeting-agenda';
import {MeetingMinutes,AddToCalendar} from './meeting-minutes';
import {toast} from 'sonner';
import {TimeZonePicker} from './time-zone-picker';
import {useTimeZone} from '@/hooks/use-time-zone';

const formatDay = (day:string) => new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',weekday:'long',day:'numeric',month:'long',year:'numeric'}).format(new Date(day+'T12:00:00Z'));
const formatInstant = (value:string, zone:string) => new Intl.DateTimeFormat('en-GB',{timeZone:zone,day:'numeric',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',timeZoneName:'short'}).format(new Date(value));
type Draft = {attachments:Attachment[];saved:string[];title:string; description:string; start:string; end:string; startChoice:string; endChoice:string; location:string; registrationUrl:string; joinUrl:string; ocs:number[]; mgs:string[]; body:string; meetingType:string; pollId:string;selectedSlot?:number};

export function DecadeCalendar({uid, admin, canAdd, focusEvent, onSaved,access,meetingSeed,onOpenPolls,people=[]}:{uid:string;admin:boolean;canAdd:boolean;focusEvent?:CalendarEvent;onSaved?:()=>void;access:MeetingAccess;meetingSeed?:MeetingSeed;onOpenPolls:()=>void;people?:any[]}) {
  const leaders=leadershipBodies(access);
  const [dayOpen,setDayOpen]=useState(false);
  const {zone,setZone,automatic,useDevice}=useTimeZone(uid);
  const [now,setNow] = useState(Date.now);
  const today = localInput(new Date(now),zone).slice(0,10);
  const firstDay=focusEvent?localInput(focusEvent.startAt,zone).slice(0,10):today;
  const [month,setMonth] = useState(firstDay.slice(0,7));
  const [selectedDay,setSelectedDay] = useState(firstDay);
  const [events,setEvents] = useState<CalendarEvent[]>([]), [capped,setCapped] = useState(false);
  const [status,setStatus] = useState('Connecting…'), [error,setError] = useState(''), [retry,setRetry] = useState(0);
  const [filter,setFilter] = useState(''), [goalFilter,setGoalFilter] = useState('');
  const [selectedId,setSelectedId] = useState(focusEvent?.id || ''), [editing,setEditing] = useState<string|null>(null);
  const [draft,setDraft] = useState<Draft|null>(null), [formZone,setFormZone] = useState(zone), [saving,setSaving] = useState(false), [formError,setFormError] = useState(''), [confirmDelete,setConfirmDelete] = useState(false);
  const days = useMemo(()=>monthGrid(month),[month]);
  useEffect(()=>{
    let stop:undefined|(()=>void);
    const connect = () => {
      stop?.(); stop=undefined;
      if (document.visibilityState !== 'visible') {setStatus('Paused');return;}
      if (!navigator.onLine) {setStatus('Offline · saved view');return;}
      setStatus('Connecting…');setError('');
      const range=gridRange(days);
      stop=subscribeEvents(range.start,range.end,(items,full)=>{setEvents(items);setCapped(full);setStatus('Live updates');},e=>{setError(friendlyError(e));setStatus('Updates unavailable');});
    };
    connect();
    document.addEventListener('visibilitychange',connect);
    window.addEventListener('online',connect);window.addEventListener('offline',connect);
    const timer=window.setInterval(()=>setNow(Date.now()),60_000);
    return ()=>{stop?.();window.clearInterval(timer);document.removeEventListener('visibilitychange',connect);window.removeEventListener('online',connect);window.removeEventListener('offline',connect);};
  },[days,uid,retry]);
  const byDay=useMemo(()=>{
    const map=new Map<string,CalendarEvent[]>(days.map(d=>[d,[]]));
    for (const event of events) {
      if ((filter && !event.ocs.includes(Number(filter))) || (goalFilter && !event.mgs.includes(goalFilter))) continue;
      const first=localInput(event.startAt,zone).slice(0,10), last=localInput(new Date(Date.parse(event.endAt)-1),zone).slice(0,10);
      for (const day of days) if (first<=day && last>=day) map.get(day)!.push(event);
    }
    return map;
  },[events,days,zone,filter,goalFilter]);
  const selected=events.find(e=>e.id===selectedId);
  useEffect(()=>{setConfirmDelete(false);},[selectedId]);
  const changeMonth=(delta:number)=>{setMonth(current=>shiftMonth(current,delta));setSelectedId('');setDayOpen(false);};
  useEffect(()=>setSelectedDay(day=>day.slice(0,7)===month?day:month+'-01'),[month]);
  async function openForm(event?:CalendarEvent,seed?:MeetingSeed) {
    let privateLinks:any={};
    if(event?.body && db && canOrganise(access,event.body)){try{const s=await getDoc(doc(db,'events',event.id,'meetingDetails','main'));if(s.exists())privateLinks=s.data();}catch(e){toast.error(friendlyError(e));return;}}
    const z=event?.timeZone || zone;setFormZone(z);setEditing(event?.id || '');setFormError('');
    const start=event?localInput(event.startAt,z):seed?localInput(seed.startAt,z):selectedDay+'T09:00', end=event?localInput(event.endAt,z):seed?localInput(seed.endAt,z):selectedDay+'T10:00';
    setDraft({attachments:event?.attachments||[],saved:(event?.attachments||[]).map(a=>a.id),title:event?.title||seed?.title||'',body:event?.body||seed?.body||'',meetingType:event?.meetingType||seed?.meetingType||'public',pollId:event?.pollId||seed?.pollId||'',selectedSlot:seed?.selectedSlot,description:event?.description||'',start,end,startChoice:event?.startAt||'',endChoice:event?.endAt||'',location:event?.location||'',registrationUrl:privateLinks.registrationUrl||event?.registrationUrl||'',joinUrl:privateLinks.joinUrl||event?.joinUrl||'',ocs:event?.ocs||linkedGroups(seed?.mgs||[]),mgs:event?.mgs||seed?.mgs||[]});
    setSelectedId('');setDayOpen(false);
  }
  useEffect(()=>{if(meetingSeed){void openForm(undefined,meetingSeed);const day=localInput(meetingSeed.startAt,zone).slice(0,10);setMonth(day.slice(0,7));setSelectedDay(day);}},[meetingSeed]);
  function patch(values:Partial<Draft>) {setDraft(d=>d?{...d,...values}:d);setFormError('');}
  function changeFormZone(next:string){
    if(draft){
      if((timeCandidates(draft.start,formZone).length>1&&!draft.startChoice)||(timeCandidates(draft.end,formZone).length>1&&!draft.endChoice)){
        setFormError('Select the repeated-hour occurrence before changing the time zone.');return;
      }
      const resolve=(value:string,choice:string)=>{const options=timeCandidates(value,formZone);return options.length===1?options[0]:options.includes(choice)?choice:'';};
      const start=resolve(draft.start,draft.startChoice),end=resolve(draft.end,draft.endChoice);
      patch({start:start?localInput(start,next):draft.start,end:end?localInput(end,next):draft.end,startChoice:start,endChoice:end});
    }
    setFormZone(next);
  }
  const startOptions=draft?timeCandidates(draft.start,formZone):[], endOptions=draft?timeCandidates(draft.end,formZone):[];
  async function submit(e:React.FormEvent) {
    e.preventDefault();if (!draft) return;
    const resolve=(options:string[],choice:string)=>options.length===1?options[0]:options.includes(choice)?choice:'';
    const startAt=resolve(startOptions,draft.startChoice), endAt=resolve(endOptions,draft.endChoice);
    if (!startAt||!endAt) {setFormError('Choose valid times. For a repeated clock hour, select an occurrence.');return;}
    setSaving(true);setFormError('');
    try {
      await saveEvent({title:draft.title,description:draft.description,startAt,endAt,timeZone:formZone,location:draft.location,registrationUrl:draft.registrationUrl,joinUrl:draft.joinUrl,ocs:draft.ocs,mgs:draft.mgs,body:draft.body,meetingType:draft.meetingType,pollId:draft.pollId,attachments:cleanAttachments(draft.attachments)},editing||undefined,draft.selectedSlot);
      const day=localInput(startAt,zone).slice(0,10);setMonth(day.slice(0,7));setSelectedDay(day);setFilter('');setGoalFilter('');setDraft(null);setEditing(null);toast.success('Event saved.');onSaved?.();
    } catch(e) {setFormError(friendlyError(e));} finally {setSaving(false);}
  }
  async function deleteSelected() {
    if (!selected) return;setSaving(true);
    try {await removeEvent(selected.id);setSelectedId('');toast.success('Event removed.');onSaved?.();} catch(e) {toast.error(friendlyError(e));} finally {setSaving(false);}
  }
  const monthLabel=new Intl.DateTimeFormat('en-GB',{month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(month+'-01T12:00:00Z'));
  const dayEvents=byDay.get(selectedDay)||[];
  const monthEvents=useMemo(()=>{const seen=new Set<string>(),out:CalendarEvent[]=[];for(const [day,items] of byDay)if(day.slice(0,7)===month)for(const e of items)if(!seen.has(e.id)){seen.add(e.id);out.push(e);}return out.sort((a,b)=>a.startAt.localeCompare(b.startAt));},[byDay,month]);
  const comingUp=monthEvents.filter(e=>Date.parse(e.endAt)>now&&!dayEvents.includes(e)).slice(0,4);
  const open=(id:string)=>{setDayOpen(false);setSelectedId(id);};
  return <section className="decade-calendar" aria-label="Decade calendar">
    <div className="calendar-toolbar">
      <div className="calendar-zone"><TimeZonePicker label="Calendar time zone" value={zone} onChange={setZone} automatic={automatic} onAutomatic={useDevice}/><span className={"micro calendar-status "+(status==='Live updates'?'live':'')} role="status">{status}</span></div>
  <div className="calendar-filters"><label>Challenge<select aria-label="Challenge" value={filter} onChange={e=>{setFilter(e.target.value);setGoalFilter('');}}><option value="">All challenges</option>{challenges.map(n=><option key={n} value={n}>{challengeLabel(n)}</option>)}</select></label><label>Main goal<select aria-label="Main goal" value={goalFilter} onChange={e=>setGoalFilter(e.target.value)}><option value="">All main goals</option>{mainGoals.filter(m=>!filter||m.startsWith(filter+'.')).map(m=><option key={m} value={m}>{goalLabel(m)}</option>)}</select></label></div>
      <div className="toolbar calendar-actions">{leaders.length>0&&<button className="btn" onClick={onOpenPolls}><GlobeIcon/> Find a meeting time</button>}<button className="btn primary" disabled={!canAdd} onClick={()=>openForm()}><Plus size={16}/> Add event</button></div>
    </div>
    {error && <div className="error-banner" role="alert">{error} <button className="btn small" onClick={()=>setRetry(n=>n+1)}>Retry</button></div>}
    {capped && <p className="notice">This busy period exceeds the calendar’s display limit. Some events may be missing.</p>}
    <div className="calendar-layout">
      <div className="glass calendar-panel">
        <div className="calendar-month"><div><h2>{monthLabel}</h2><p className="micro">{monthEvents.length?`${monthEvents.length} ${monthEvents.length===1?'event':'events'} this month`:'No events this month'}{filter||goalFilter?' · filtered':''}</p></div><div className="row"><button type="button" className="btn calendar-arrow" aria-label="Previous month" title="Previous month" onClick={()=>changeMonth(-1)}><ChevronLeft size={20}/></button><button type="button" className="btn small" onClick={()=>{setMonth(today.slice(0,7));setSelectedDay(today);setSelectedId('');setDayOpen(false);}}>Today</button><button type="button" className="btn calendar-arrow" aria-label="Next month" title="Next month" onClick={()=>changeMonth(1)}><ChevronRight size={20}/></button></div></div>
        <div className="calendar-legend" role="group" aria-label="Show events by Working Group">
          <button type="button" className={'legend-chip all'+(!filter?' on':'')} aria-pressed={!filter} onClick={()=>{setFilter('');setGoalFilter('');}}>All</button>
          {groups.map(g=><button type="button" key={g.id} className={'legend-chip'+(filter===String(g.id)?' on':'')} aria-pressed={filter===String(g.id)} title={`Events linked to ${challengeLabel(g.id)}`} style={{'--ev':g.color,'--ev-ink':g.ink} as React.CSSProperties} onClick={()=>{setFilter(filter===String(g.id)?'':String(g.id));setGoalFilter('');}}><i/>WG{g.id} · {g.short}</button>)}
        </div>
        <div className="calendar-grid" role="group" aria-label={monthLabel}>
          {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'].map(d=><span key={d} className="calendar-weekday">{d}</span>)}
          {days.map((day,i)=>{const items=byDay.get(day)||[];return <button type="button" key={day} aria-label={`${formatDay(day)}, ${items.length} ${items.length===1?'event':'events'}`} aria-pressed={day===selectedDay} onClick={()=>{setSelectedDay(day);setSelectedId('');setDayOpen(true);}} className={`calendar-day ${day.slice(0,7)!==month?'outside':''} ${day===selectedDay?'selected':''} ${day===today?'today':''} ${i%7>4?'weekend':''} ${day<today?'before':''}`}><span className="calendar-number">{Number(day.slice(-2))}</span><span className="calendar-previews">{items.slice(0,items.length>3?2:3).map(event=><span key={event.id} className={'cal-chip ev'+(Date.parse(event.endAt)<=now?' done':'')} style={accentStyle(event)}>{localInput(event.startAt,zone).slice(0,10)===day&&<b>{localInput(event.startAt,zone).slice(11)}</b>}{event.title}</span>)}{items.length>3 && <span className="cal-more">+{items.length-2} more</span>}</span>{items.length>0&&<span className="calendar-dots" aria-hidden="true">{items.slice(0,3).map(e=><i key={e.id} className="ev" style={accentStyle(e)}/>)}</span>}</button>;})}
        </div>
        <p className="calendar-key micro"><span><i className="key-swatch wg"/>Working Group meetings and events use the Working Group’s colour</span><span><i className="key-swatch body"/>Other governing bodies use the colour of their space</span><span><i className="key-swatch multi"/>Events linked to several challenges show each colour</span></p>
      </div>
      <aside className="glass calendar-agenda" aria-label="Selected day events">
        <div className="agenda-day-head"><span className="agenda-day-num">{Number(selectedDay.slice(-2))}</span><div><h2>{new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',weekday:'long'}).format(new Date(selectedDay+'T12:00:00Z'))}</h2><p className="micro">{new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',month:'long',year:'numeric'}).format(new Date(selectedDay+'T12:00:00Z'))}{selectedDay===today?' · Today':''}</p></div></div>
        {!dayEvents.length?<div className="agenda-empty"><CalendarDays size={22}/><p>No events on this day.</p>{canAdd&&<button className="btn small" onClick={()=>openForm()}><Plus size={14}/> Add an event</button>}</div>:<div className="ev-list">{dayEvents.map(event=><EventCard key={event.id} event={event} zone={zone} now={now} onOpen={()=>open(event.id)}/>)}</div>}
        {comingUp.length>0&&<><h3 className="agenda-subhead">Coming up in {monthLabel.split(' ')[0]}</h3><div className="ev-list">{comingUp.map(event=><EventCard key={event.id} event={event} zone={zone} now={now} withDate onOpen={()=>open(event.id)}/>)}</div></>}
      </aside>
    </div>
    <Dialog open={dayOpen} onOpenChange={setDayOpen}><DialogContent className="detail-content"><DialogTitle>{formatDay(selectedDay)}</DialogTitle><DialogDescription>All displayed events on this date · {zone.replaceAll('_',' ')}</DialogDescription>{!dayEvents.length&&<div className="agenda-empty"><CalendarDays size={22}/><p>No events on this day.</p></div>}<div className="ev-list">{dayEvents.map(event=><EventCard key={event.id} event={event} zone={zone} now={now} onOpen={()=>open(event.id)}/>)}</div>{canAdd&&<button className="btn primary" onClick={()=>openForm()}><Plus size={16}/> Add an event on this date</button>}</DialogContent></Dialog>
    <Dialog open={!!selected} onOpenChange={v=>!v&&!saving&&setSelectedId('')}><DialogContent className="detail-content event-sheet ev" style={selected?accentStyle(selected):undefined}>{selected ? <EventSheet event={selected} zone={zone} now={now} access={access} people={people}
      footer={(admin||(selected.body?canOrganise(access,selected.body):selected.owner===uid)) && <div className="event-footer">{confirmDelete?<><span>Delete this event?</span><button className="btn danger" disabled={saving} onClick={deleteSelected}>{saving?'Deleting…':'Delete event'}</button><button className="btn" disabled={saving} onClick={()=>setConfirmDelete(false)}>Cancel</button></>:<><span className="micro">You can manage this event.</span><button className="btn" onClick={()=>openForm(selected)}><Pencil size={14}/> Edit</button><button className="btn" onClick={()=>setConfirmDelete(true)}><Trash2 size={14}/> Delete</button></>}</div>}/>:<><DialogTitle>Event</DialogTitle><DialogDescription/></>}</DialogContent></Dialog>
    <Dialog open={!!draft} onOpenChange={v=>!v&&!saving&&(setDraft(null),setEditing(null))}><DialogContent className="detail-content calendar-form"><DialogTitle>{editing?'Edit event':'Add event'}</DialogTitle><DialogDescription>Enter times in {formZone.replaceAll('_',' ')}. Every member will see their local time.</DialogDescription>{draft && <form onSubmit={submit}>
      <fieldset disabled={saving}>
      <TimeZonePicker label="Event time zone" value={formZone} onChange={changeFormZone}/>
      <div className="calendar-form-grid"><label>Meeting category<select aria-label="Meeting category" disabled={(!!editing&&!admin)||!!draft.pollId} value={draft.meetingType} onChange={e=>patch({meetingType:e.target.value,body:e.target.value==='public'?'':leaders[0]?.id||''})}><option value="public">Public event</option>{leaders.length>0&&meetingTypes.map(t=><option key={t.id} value={t.id}>{t.label}</option>)}</select></label>{draft.meetingType!=='public'&&<label>Organising body<select aria-label="Organising body" required disabled={(!!editing&&!admin)||!!draft.pollId} value={draft.body} onChange={e=>patch({body:e.target.value})}>{leaders.map(b=><option key={b.id} value={b.id}>{b.label}</option>)}</select></label>}</div>
      {draft.meetingType!=='public'&&<p className="micro">The calendar shows the meeting date and title to members. Joining links and the agenda are restricted to this meeting’s audience.</p>}
      <label>Event title<input required maxLength={160} value={draft.title} onChange={e=>patch({title:e.target.value})}/></label>
      <div className="calendar-form-grid">{(['start','end'] as const).map(field=>{const options=field==='start'?startOptions:endOptions,choice=field==='start'?'startChoice':'endChoice';return <div key={field}><label>{field==='start'?'Start':'End'}<input required disabled={!!draft.pollId&&!editing} type="datetime-local" value={draft[field]} onChange={e=>patch({[field]:e.target.value,[choice]:''})}/></label>{draft[field]&&!options.length && <p className="calendar-validation">This time does not exist in {formZone}.</p>}{options.length>1 && <label>Repeated hour<select required value={draft[choice]} onChange={e=>patch({[choice]:e.target.value})}><option value="">Choose an occurrence</option>{options.map(t=><option key={t} value={t}>{formatInstant(t,formZone)}</option>)}</select></label>}</div>;})}</div>
      <label>Description<textarea maxLength={3000} value={draft.description} onChange={e=>patch({description:e.target.value})}/></label>
      <label>Location / venue<input maxLength={300} value={draft.location} onChange={e=>patch({location:e.target.value})}/></label>
      <div className="calendar-form-grid"><label>Registration link<input type="url" maxLength={1000} placeholder="https://" value={draft.registrationUrl} onChange={e=>patch({registrationUrl:e.target.value})}/></label><label>Virtual meeting link<input type="url" maxLength={1000} placeholder="https://" value={draft.joinUrl} onChange={e=>patch({joinUrl:e.target.value})}/></label></div>
      <GoalPicker label="Contributes to main goals" value={draft.mgs} onChange={mgs=>patch({mgs,ocs:linkedGroups(mgs)})}/>
      {shareBody(access,draft.meetingType!=='public'?draft.body:'')!==null&&<AttachmentPicker value={draft.attachments} saved={draft.saved} onChange={attachments=>setDraft(d=>d?{...d,attachments}:d)} body={shareBody(access,draft.meetingType!=='public'?draft.body:'')||''} audience={draft.meetingType==='public'?'all':draft.meetingType as any}/>}
      {formError && <p className="error-banner" role="alert">{formError}</p>}<div className="toolbar"><button type="submit" className="btn primary">{saving?'Saving…':'Save event'}</button><button type="button" className="btn" onClick={()=>{setDraft(null);setEditing(null);}}>Cancel</button></div></fieldset>
    </form>}</DialogContent></Dialog>
  </section>;
}

function GlobeIcon(){return <CalendarDays size={16}/>;}

const timeOf=(value:string,zone:string)=>localInput(value,zone).slice(11);
const zoneAbbr=(value:string,zone:string)=>new Intl.DateTimeFormat('en-GB',{timeZone:zone,timeZoneName:'short'}).formatToParts(new Date(value)).find(p=>p.type==='timeZoneName')?.value||'';
function timeRange(e:CalendarEvent,zone:string){
  const a=localInput(e.startAt,zone),b=localInput(new Date(Date.parse(e.endAt)),zone);
  return a.slice(0,10)===b.slice(0,10)?`${a.slice(11)} – ${b.slice(11)} ${zoneAbbr(e.startAt,zone)}`:`${formatInstant(e.startAt,zone)} – ${formatInstant(e.endAt,zone)}`;
}
const audience=(e:CalendarEvent)=>{
  if(!e.body||!e.meetingType||e.meetingType==='public')return 'Open to all';
  const name=e.body.startsWith('wg')?`Working Group ${e.body.slice(2)}`:bodyLabel(e.body);
  return e.meetingType==='leadership'?`Leads, Associate Leads and Secretariat of ${name}`:e.meetingType==='core'?`Core Group and leadership of ${name}`:`All members of ${name}`;
};

/** One event in a list: coloured date tile, title, time and organising body. */
function EventCard({event,zone,now,onOpen,withDate}:{event:CalendarEvent;zone:string;now:number;onOpen:()=>void;withDate?:boolean}){
  const a=eventAccent(event),t=eventTiming(event.startAt,event.endAt,zone,now),day=localInput(event.startAt,zone).slice(0,10);
  const restricted=!!event.body&&!!event.meetingType&&event.meetingType!=='public';
  return <button type="button" className={'ev-card ev '+t.state} style={accentStyle(event)} onClick={onOpen}>
    {withDate?<span className="ev-date"><b>{Number(day.slice(-2))}</b><small>{new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',month:'short'}).format(new Date(day+'T12:00:00Z'))}</small></span>:<span className="ev-time"><b>{timeOf(event.startAt,zone)}</b><small>{durationLabel(event.startAt,event.endAt)}</small></span>}
    <span className="ev-main">
      <strong>{event.title}</strong>
      <span className="ev-meta"><Clock3 size={12}/>{timeRange(event,zone)}</span>
      <span className="ev-tags"><span className="ev-tag">{a.tag}</span><span className="ev-type">{restricted?<Lock size={11}/>:<Globe2 size={11}/>}{typeLabel(event.meetingType||'public')}</span>{t.state==='live'&&<span className="ev-live">Now</span>}</span>
    </span>
  </button>;
}

/** The page of one event or meeting. */
function EventSheet({event,zone,now,access,people,footer}:{event:CalendarEvent;zone:string;now:number;access:MeetingAccess;people:any[];footer:React.ReactNode}){
  const a=eventAccent(event),t=eventTiming(event.startAt,event.endAt,zone,now),day=localInput(event.startAt,zone).slice(0,10),d=new Date(day+'T12:00:00Z');
  const restricted=!!event.body&&!!event.meetingType&&event.meetingType!=='public';
  const fmt=(o:Intl.DateTimeFormatOptions)=>new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',...o}).format(d);
  const organiser=event.body?bodyTitle(event.body,bodyLabel(event.body)):'';
  return <>
    <header className="event-hero">
      <div className="event-date-tile" aria-hidden="true"><small className="m">{fmt({month:'short'})}</small><b>{Number(day.slice(-2))}</b><small className="w">{fmt({weekday:'short'})} · {fmt({year:'numeric'})}</small></div>
      <div className="event-hero-text">
        <div className="event-kicker"><span className="ev-tag">{a.tag}</span><span className="ev-type">{restricted?<Lock size={12}/>:<Globe2 size={12}/>}{typeLabel(event.meetingType||'public')}</span><span className={'ev-timing '+t.state}>{t.state==='live'&&<i/>}{t.label}</span></div>
        <DialogTitle>{event.title}</DialogTitle>
        <DialogDescription>{organiser||'Decade event'} · Times in {zone.replaceAll('_',' ')}</DialogDescription>
        <CreatedBy uid={event.owner} verb="Added by"/>
      </div>
    </header>
    <div className="event-facts">
      <div className="fact"><span className="fact-icon"><Clock3 size={17}/></span><div><span className="fact-label">When</span><strong>{fmt({weekday:'long',day:'numeric',month:'long'})}</strong><span>{timeRange(event,zone)}{durationLabel(event.startAt,event.endAt)?` · ${durationLabel(event.startAt,event.endAt)}`:''}</span>{event.timeZone!==zone&&<span className="micro">Organiser time: {formatInstant(event.startAt,event.timeZone)}</span>}</div></div>
      <div className="fact"><span className="fact-icon"><MapPin size={17}/></span><div><span className="fact-label">Where</span><strong>{event.location||'To be confirmed'}</strong>{event.joinUrl&&<span>Online link available</span>}</div></div>
      <div className="fact"><span className="fact-icon"><Users size={17}/></span><div><span className="fact-label">Who</span><strong>{audience(event)}</strong>{restricted?<span>Invitation only</span>:<span>Public event</span>}</div></div>
    </div>
    {(event.registrationUrl||event.joinUrl)&&<div className="toolbar event-links">{event.registrationUrl && <a className="btn primary" href={event.registrationUrl} target="_blank" rel="noopener noreferrer">Register <ArrowUpRight size={15}/></a>}{event.joinUrl && <a className="btn" href={event.joinUrl} target="_blank" rel="noopener noreferrer">Join online <ArrowUpRight size={15}/></a>}</div>}
    <EventAttendance event={event} access={access} people={people} canSee={!restricted||canAttend(access,event.body||'',event.meetingType||'public')}/>
    {event.description && <section className="event-section"><h3><AlignLeft size={16}/> About</h3><p className="calendar-description">{event.description}</p></section>}
    {!!event.attachments?.length&&(!restricted||canAttend(access,event.body||'',event.meetingType||'public'))&&<section className="event-section"><h3><Paperclip size={16}/> Documents</h3><AttachmentList items={event.attachments}/></section>}
    {(event.ocs.length>0||event.mgs.length>0)&&<section className="event-section"><h3><Target size={16}/> Contributes to</h3><div className="oc-chips">{event.ocs.map(n=><span className="oc-chip" key={n} style={{'--wg-color':groupColor(n).color} as React.CSSProperties}>{challengeLabel(n)}</span>)}</div><GoalLabels value={event.mgs}/></section>}
    <AddToCalendar event={event}/>
    <MeetingAgenda event={event} access={access}/>
    <MeetingMinutes event={event} access={access} people={people}/>
    {footer}
  </>;
}
