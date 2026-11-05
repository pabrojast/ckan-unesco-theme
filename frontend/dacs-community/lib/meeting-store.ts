import {collection,doc,query,where,orderBy,limit,onSnapshot,setDoc,getDoc,updateDoc,deleteDoc,serverTimestamp,Timestamp,runTransaction} from 'firebase/firestore';
import {linkedGroups} from './decade-goals';
import {auth,db} from './firebase';
import {meetingBodies,bodyLevel,leadershipBodies,type MeetingAccess,type MeetingPoll,type PollResponse} from './meetings';
const iso=(v:any)=>v?.toDate?v.toDate().toISOString():v;
export const unpackMeeting=(d:any)=>{const x=d.data();if(x.timeZone){try{new Intl.DateTimeFormat('en',{timeZone:x.timeZone});}catch{x.timeZone='UTC';}}return {id:d.id,...Object.fromEntries(Object.entries(x).map(([k,v])=>[k,k==='slots'?(v as any[]).map(iso):iso(v)]))};};
export function subscribePolls(a:MeetingAccess,next:(x:MeetingPoll[],capped:boolean)=>void,error:(e:any)=>void){
  if(!db||!a.uid)return()=>{};
  const scopes=meetingBodies.map(b=>({body:b.id,types:bodyLevel(a,b.id)>=3?['leadership','core','broad']:bodyLevel(a,b.id)===2?['core','broad']:bodyLevel(a,b.id)===1?['broad']:[]})).filter(s=>s.types.length);
  const batches=new Map<string,MeetingPoll[]>(), caps=new Set<string>();
  if(!scopes.length)next([],false);
  const stops=scopes.map(s=>onSnapshot(query(collection(db!,'meetingPolls'),where('body','==',s.body),where('meetingType','in',s.types),orderBy('createdAt','desc'),limit(41)),snap=>{
    batches.set(s.body,snap.docs.slice(0,40).map(unpackMeeting) as MeetingPoll[]);if(snap.size>40)caps.add(s.body);else caps.delete(s.body);
    next([...batches.values()].flat().sort((x,y)=>y.createdAt.localeCompare(x.createdAt)),caps.size>0);
  },error));return()=>stops.forEach(s=>s());
}
export function subscribeOwnResponses(uid:string,next:(x:PollResponse[])=>void,error:(e:any)=>void){if(!db)return()=>{};return onSnapshot(query(collection(db,'pollResponses'),where('uid','==',uid),orderBy('updatedAt','desc'),limit(200)),s=>next(s.docs.map(unpackMeeting) as PollResponse[]),error);}
export function subscribeResponses(pollId:string,next:(x:PollResponse[])=>void,error:(e:any)=>void){if(!db)return()=>{};return onSnapshot(query(collection(db,'pollResponses'),where('pollId','==',pollId),limit(201)),s=>next(s.docs.map(unpackMeeting) as PollResponse[]),error);}
export async function savePoll(v:Omit<MeetingPoll,'id'|'owner'|'createdAt'|'updatedAt'|'selectedSlot'|'eventId'|'status'|'linkAccess'|'withdrawn'>&{linkAccess?:boolean}){
 if(!db||!auth?.currentUser)throw Error('Sign in to create a poll.');
 if(!v.title.trim()||!v.slots.length||v.slots.length>12||new Set(v.slots).size!==v.slots.length)throw Error('Enter a title and 1–12 different meeting times.');
 if(/^wg[1-5]$/.test(v.body)&&v.mgs.length&&!linkedGroups(v.mgs).includes(Number(v.body[2])))throw Error('Select a main goal of the organising Working Group.');
 if(v.slots.some(s=>Date.parse(s)<=Date.now())||Date.parse(v.deadline)<=Date.now()||Date.parse(v.deadline)>Math.min(...v.slots.map(Date.parse)))throw Error('The response deadline must come before every proposed time.');
 const ref=doc(collection(db,'meetingPolls'));
 await setDoc(ref,{...v,notes:String(v.notes||'').trim().slice(0,1000),withdrawn:[],linkAccess:v.linkAccess===true,title:v.title.trim(),slots:v.slots.map(s=>Timestamp.fromDate(new Date(s))),deadline:Timestamp.fromDate(new Date(v.deadline)),owner:auth.currentUser.uid,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),status:'open',selectedSlot:-1,eventId:''});return ref.id;
}
/**
 * Changes a published poll: title, details, response deadline, new times (added after the existing ones, so earlier
 * answers keep their meaning) and withdrawn times. Duration and audience stay as published.
 */
export async function updatePoll(p:MeetingPoll,v:{title:string;notes:string;deadline:string;added:string[];withdrawn:number[]}){
 if(!db)return;
 const title=v.title.trim().slice(0,160);if(!title)throw Error('Enter a title.');
 const slots=[...p.slots,...v.added.filter(s=>!p.slots.includes(s))];
 if(slots.length>24)throw Error('A poll can hold up to 24 times in total, including withdrawn ones.');
 const withdrawn=[...new Set(v.withdrawn)].filter(i=>i>=0&&i<slots.length).sort((a,b)=>a-b);
 const active=slots.filter((_,i)=>!withdrawn.includes(i));
 if(!active.length)throw Error('Keep at least one proposed time.');
 if(active.length>12)throw Error('Propose up to 12 times.');
 if(v.added.some(s=>Date.parse(s)<=Date.now()))throw Error('New times must be in the future.');
 const open=p.status==='open';
 if(open&&(Date.parse(v.deadline)<=Date.now()||Date.parse(v.deadline)>Math.min(...active.filter(s=>Date.parse(s)>Date.now()).map(Date.parse))))throw Error('Responses must close in the future and before the first upcoming proposed time.');
 await updateDoc(doc(db,'meetingPolls',p.id),{title,notes:v.notes.trim().slice(0,1000),deadline:Timestamp.fromDate(new Date(v.deadline)),
  ...(open?{slots:slots.map(s=>Timestamp.fromDate(new Date(s))),withdrawn}:{}),updatedAt:serverTimestamp()});
}
/** Live view of one poll by id (members of its audience, or anyone signed in when its link is open). */
export function subscribePoll(id:string,next:(p:MeetingPoll|null)=>void,error:(e:any)=>void){if(!db)return()=>{};return onSnapshot(doc(db,'meetingPolls',id),s=>next(s.exists()?unpackMeeting(s) as MeetingPoll:null),error);}
export async function setPollLink(id:string,linkAccess:boolean){if(!db)return;await updateDoc(doc(db,'meetingPolls',id),{linkAccess,updatedAt:serverTimestamp()});}
export async function fetchPoll(id:string){if(!db)return null;const s=await getDoc(doc(db,'meetingPolls',id));return s.exists()?unpackMeeting(s) as MeetingPoll:null;}
export async function ownProfileName(uid:string){if(!db)return null;try{const s=await getDoc(doc(db,'profiles',uid));return s.exists()?String(s.data().name||''):null;}catch{return null;}}
export async function respond(p:MeetingPoll,answers:string[],name:string,timeZone:string){if(!db||!auth?.currentUser)throw Error('Sign in to respond.');await setDoc(doc(db,'pollResponses',p.id+'_'+auth.currentUser.uid),{pollId:p.id,uid:auth.currentUser.uid,name,timeZone,answers,updatedAt:serverTimestamp()});}
export async function closePoll(id:string){if(!db)return;await updateDoc(doc(db,'meetingPolls',id),{status:'closed',updatedAt:serverTimestamp()});}
export async function deletePoll(id:string){if(!db)return;const ref=doc(db,'meetingPolls',id),s=await getDoc(ref);if(s.exists()&&s.data().status==='scheduled')throw Error('Remove the calendar meeting before deleting its poll.');await deleteDoc(ref);}
export function subscribeRhythms(a:MeetingAccess,next:(x:any[])=>void,error:(e:any)=>void){
 if(!db)return()=>{};const values=new Map<string,any>(),stops:(()=>void)[]=[];
 for(const b of leadershipBodies(a).filter(b=>['wg1','wg2','wg3','wg4','wg5','cfd','alliance'].includes(b.id))){
  const emit=()=>next([...values.values()]);values.set(b.id,{id:b.id,events:[],baseline:''});
  const ref=doc(db,'meetingClocks',b.id);
  runTransaction(db,async tx=>{const s=await tx.get(ref);if(!s.exists())tx.set(ref,{createdAt:serverTimestamp()});}).catch(error);
  stops.push(onSnapshot(ref,s=>{values.set(b.id,{...values.get(b.id),baseline:s.exists()?iso(s.data().createdAt):''});emit();},error));
  stops.push(onSnapshot(query(collection(db,'events'),where('body','==',b.id),orderBy('startAt','desc'),limit(60)),s=>{values.set(b.id,{...values.get(b.id),events:s.docs.map(unpackMeeting)});emit();},error));
 }return()=>stops.forEach(s=>s());
}
