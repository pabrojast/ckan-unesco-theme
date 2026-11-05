import test from 'node:test';
import assert from 'node:assert/strict';
import {localInput,timeCandidates,eventError,monthGrid,shiftMonth,gridRange,occursOn,timeZoneOptions,validTimeZone} from '../lib/calendar.ts';
const event={id:'event',owner:'alice',title:'Meeting',description:'',startAt:'2026-10-08T00:30:00.000Z',endAt:'2026-10-08T01:30:00.000Z',timeZone:'Europe/Paris',location:'',registrationUrl:'https://example.org/register',joinUrl:'https://example.org/meeting',ocs:[1,5],mgs:['1.1','5.3']};
test('one instant appears on each visitor’s local date, including fractional offsets',()=>{
 assert.equal(localInput(event.startAt,'America/Los_Angeles'),'2026-10-07T17:30');
 assert.equal(localInput(event.startAt,'Asia/Kathmandu'),'2026-10-08T06:15');
 assert.equal(occursOn(event,'2026-10-07','America/Los_Angeles'),true);
 assert.equal(occursOn(event,'2026-10-08','Europe/Paris'),true);
 assert.equal(occursOn(event,'2026-10-08','America/Los_Angeles'),false);
});
test('DST gaps are rejected and repeated hours offer both actual instants',()=>{
 assert.deepEqual(timeCandidates('2026-03-29T02:30','Europe/Paris'),[]);
 assert.deepEqual(timeCandidates('2026-10-25T02:30','Europe/Paris'),['2026-10-25T00:30:00.000Z','2026-10-25T01:30:00.000Z']);
 assert.deepEqual(timeCandidates('2026-10-07T18:15','Asia/Kathmandu'),['2026-10-07T12:30:00.000Z']);
 assert.deepEqual(timeCandidates('2026-02-30T09:00','UTC'),[]);
});
test('midnight endings exclude the following day; multi-day events appear throughout',()=>{
 const e={...event,startAt:'2026-10-07T12:00:00Z',endAt:'2026-10-09T00:00:00Z'};
 assert.equal(occursOn(e,'2026-10-07','UTC'),true);assert.equal(occursOn(e,'2026-10-08','UTC'),true);assert.equal(occursOn(e,'2026-10-09','UTC'),false);
});
test('calendar grid spans six Monday-based weeks and crosses years correctly',()=>{
 const days=monthGrid('2026-10'); assert.equal(days.length,42);assert.equal(days[0],'2026-09-28');assert.equal(days.at(-1),'2026-11-08');
 assert.equal(shiftMonth('2026-12',1),'2027-01');assert.equal(shiftMonth('2026-01',-1),'2025-12');
 const range=gridRange(days);assert.ok(range.start<new Date(days[0]+'T00:00:00Z'));assert.ok(range.end>new Date(days.at(-1)+'T23:59:00Z'));
});
test('event validation rejects unsafe links, unrelated goals and reversed dates',()=>{
 assert.equal(eventError(event),'');
 for (const change of [{joinUrl:'javascript:alert(1)'},{ocs:[1],mgs:['5.3']},{mgs:[]},{ocs:[]},{mgs:['1.1','1.1']},{startAt:event.endAt,endAt:event.startAt},{timeZone:'Invented/Zone'},{endAt:'2027-10-09T00:00:00Z'}]) assert.ok(eventError({...event,...change}));
});

test('timezone choices cover cities and fractional offsets without accepting arbitrary input',()=>{
 const zones=timeZoneOptions();for(const z of ['UTC','Europe/Paris','Asia/Tokyo','America/New_York','Asia/Kolkata'])assert.ok(zones.includes(z));
 assert.ok(zones.length>300);assert.equal(new Set(zones).size,zones.length);
 assert.equal(validTimeZone('Asia/Kathmandu'),true);assert.equal(validTimeZone('Invented/Zone'),false);assert.equal(validTimeZone(''),false);
});
