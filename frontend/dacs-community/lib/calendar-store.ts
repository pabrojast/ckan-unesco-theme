import {collection, doc, query, where, orderBy, limit, onSnapshot, Timestamp, serverTimestamp, getDoc, setDoc, updateDoc, deleteDoc, writeBatch} from 'firebase/firestore';
import {auth, db} from './firebase';
import {eventError, type CalendarEvent} from './calendar';
export function subscribeEvents(start: Date, end: Date, next: (events: CalendarEvent[], capped: boolean) => void, error: (e: unknown) => void) {
  if (!db || !auth?.currentUser) return () => {};
  // Two single-field queries need no composite index. At most 200 results each.
  // Events are limited to 31 days, shorter than the 42-day grid, so any event
  // overlapping the grid has at least one endpoint inside this expanded range.
  const batches: CalendarEvent[][] = [[],[]], capped = [false,false], ready = [false,false];
  const stops = (['startAt','endAt'] as const).map((field,i) => onSnapshot(query(collection(db!, 'events'), where(field,'>=',Timestamp.fromDate(start)), where(field,'<',Timestamp.fromDate(end)), orderBy(field), limit(201)), snapshot => {
    ready[i] = true; capped[i] = snapshot.size > 200;
    batches[i] = snapshot.docs.slice(0,200).map(d => {
      const v = d.data();
      try {new Intl.DateTimeFormat('en',{timeZone:v.timeZone});} catch {v.timeZone='UTC';}
      return {id:d.id,...v,startAt:v.startAt.toDate().toISOString(),endAt:v.endAt.toDate().toISOString()} as CalendarEvent;
    });
    if (ready.every(Boolean)) next([...new Map(batches.flat().map(e => [e.id,e])).values()].sort((a,b)=>a.startAt.localeCompare(b.startAt)), capped.some(Boolean));
  }, error));
  return () => stops.forEach(stop=>stop());
}
export async function saveEvent(event: Omit<CalendarEvent, 'id' | 'owner'>, id?: string, selectedSlot?:number) {
  if (!db || !auth?.currentUser) throw new Error('Sign in to add an event.');
  const clean = {...event, title:event.title.trim(), description:event.description.trim(), location:event.location.trim(), registrationUrl:event.registrationUrl.trim(), joinUrl:event.joinUrl.trim()};
  if(clean.meetingType&&clean.meetingType!=='public'&&/^wg[1-5]$/.test(clean.body||'')&&!clean.ocs.includes(Number(clean.body![2])))throw Error('Select a main goal of the organising Working Group.');
  const error = eventError(clean); if (error) throw new Error(error);
  const fields = {...clean, startAt:Timestamp.fromDate(new Date(clean.startAt)), endAt:Timestamp.fromDate(new Date(clean.endAt)), updatedAt:serverTimestamp()};
  const ref=id?doc(db,'events',id):doc(collection(db,'events'));
  const batch=writeBatch(db),meeting=clean.meetingType&&clean.meetingType!=='public';
  const data={...fields,body:clean.body||'',meetingType:clean.meetingType||'public',pollId:clean.pollId||'',registrationUrl:meeting?'':clean.registrationUrl,joinUrl:meeting?'':clean.joinUrl};
  if(id)batch.update(ref,data);else batch.set(ref,{...data,owner:auth.currentUser.uid,createdAt:serverTimestamp()});
  if(meeting)batch.set(doc(db,'events',ref.id,'meetingDetails','main'),{registrationUrl:clean.registrationUrl,joinUrl:clean.joinUrl,updatedAt:serverTimestamp()});
  if(!id&&clean.pollId&&selectedSlot!==undefined)batch.update(doc(db,'meetingPolls',clean.pollId),{status:'scheduled',selectedSlot,eventId:ref.id,updatedAt:serverTimestamp()});
  await batch.commit();return ref.id;
}
export async function removeEvent(id: string) {
  if (!db || !auth?.currentUser) throw new Error('Sign in to manage events.');
  const ref=doc(db,'events',id),snapshot=await getDoc(ref);
  const batch=writeBatch(db);batch.delete(ref);
  if(snapshot.exists()&&snapshot.data().pollId){const pollRef=doc(db,'meetingPolls',snapshot.data().pollId),poll=await getDoc(pollRef);if(poll.exists())batch.update(pollRef,{status:'closed',selectedSlot:-1,eventId:'',updatedAt:serverTimestamp()});}
  await batch.commit();
}
