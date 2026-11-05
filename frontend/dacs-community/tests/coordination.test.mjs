import test from 'node:test';
import assert from 'node:assert/strict';
import {buildIcs,googleCalendarUrl,tally,toCsv,workingDays,logoDeadlines,actionState,sortActions,workProgress,tallyConsultation,consultationError,buildDigest,countryKey,countryPoints} from '../lib/coordination.ts';
test('calendar files follow RFC 5545 with escaping, UTC times and folded lines',()=>{
  const ics=buildIcs([{id:'e1',title:'SMC meeting; agenda, part 1',description:'Line one\nLine two '+'x'.repeat(90),location:'UNESCO HQ, Paris',startAt:'2026-11-03T13:00:00.000Z',endAt:'2026-11-03T15:00:00.000Z',url:'https://example.org/'}],new Date('2026-10-13T10:00:00Z'));
  assert.match(ics,/^BEGIN:VCALENDAR\r\n/);assert.match(ics,/DTSTART:20261103T130000Z\r\n/);assert.match(ics,/DTEND:20261103T150000Z\r\n/);
  assert.ok(ics.includes('SUMMARY:SMC meeting\\; agenda\\, part 1\r\n'));assert.ok(ics.includes('LOCATION:UNESCO HQ\\, Paris'));
  for(const line of ics.split('\r\n'))assert.ok(new TextEncoder().encode(line).length<=75,line);
  assert.match(googleCalendarUrl({id:'e1',title:'T',startAt:'2026-11-03T13:00:00Z',endAt:'2026-11-03T15:00:00Z'}),/dates=20261103T130000Z%2F20261103T150000Z/);
});
test('tallies, CSV and working days',()=>{
  assert.deepEqual(tally([{g:'Woman'},{g:'Man'},{g:'Woman'},{}],x=>x.g,['Woman','Man']),[['Woman',2],['Man',1],['Not stated',1]]);
  assert.equal(toCsv([['a','b,c'],['=1+1','say "hi"']]),'﻿a,"b,c"\r\n\'=1+1,"say ""hi"""\r\n');
  assert.equal(workingDays('2026-10-09',new Date('2026-10-13T12:00:00Z')),2); // Fri to Tue: Mon, Tue
  const rows=logoDeadlines([{id:'a',receivedAt:'2026-08-01',stage:'wg'},{id:'b',receivedAt:'2026-08-01',stage:'applicant'},{id:'c',receivedAt:'2026-09-01',stage:'screening'},{id:'d',receivedAt:'2026-01-01',stage:'closed'}],new Date('2026-10-13T12:00:00Z'));
  assert.deepEqual(rows.map(r=>[r.id,r.state]),[['a','late'],['b','paused'],['c','near']]);
});
test('action states and order',()=>{
  assert.equal(actionState({status:'open',due:'2026-10-01'},'2026-10-13'),'overdue');
  assert.equal(actionState({status:'open',due:'2026-10-18'},'2026-10-13'),'soon');
  assert.equal(actionState({status:'open',due:'2026-11-30'},'2026-10-13'),'open');
  assert.equal(actionState({status:'done',due:'2026-10-01'},'2026-10-13'),'done');
  assert.deepEqual(sortActions([{title:'b',status:'done',due:'2026-01-01'},{title:'c',status:'open',due:''},{title:'a',status:'open',due:'2026-10-20'}]).map(a=>a.title),['a','c','b']);
  assert.deepEqual(workProgress([{status:'done'},{status:'delayed'},{status:'planned'},{status:'done'}]),{total:4,done:2,delayed:1,inProgress:0,percent:50});
});
test('consultation validation and results',()=>{
  const qs=[{id:'q1',kind:'yesno',label:'Approve?',options:[]},{id:'q2',kind:'choice',label:'Venue',options:['Paris','Geneva']},{id:'q3',kind:'text',label:'Comments',options:[]}];
  assert.equal(consultationError({title:'',questions:qs,deadline:'2099-01-01'}),'Enter a title.');
  assert.match(consultationError({title:'T',questions:[{id:'q',kind:'choice',label:'X',options:['A']}],deadline:'2099-01-01'}),/two to eight/);
  assert.equal(consultationError({title:'T',questions:qs,deadline:'2099-01-01T00:00'}),'');
  const r=tallyConsultation(qs,[{answers:{q1:'Yes',q2:'Paris',q3:'Fine'}},{answers:{q1:'No',q2:'Paris'}},{answers:{q1:'Yes'}}]);
  assert.deepEqual(r[0].counts,[['Yes',2],['No',1],['Abstain',0]]);assert.deepEqual(r[1].counts,[['Paris',2],['Geneva',0]]);assert.deepEqual(r[2].texts,['Fine']);
});
test('digest lists the period and escapes HTML',()=>{
  const d=buildDigest({since:new Date('2026-10-06T00:00:00Z'),until:new Date('2026-10-13T00:00:00Z'),appUrl:'https://cryohub-eb898.web.app',groupLabel:n=>'WG'+n,
    people:[{name:'A <b>',createdAt:'2026-10-08T10:00:00Z',organisation:'Org'},{name:'Old',createdAt:'2026-01-01T00:00:00Z'}],
    posts:[{title:'News 1',author_name:'X',wg:2,createdAt:'2026-10-10T00:00:00Z'}],
    events:[{title:'SMC',startAt:'2026-10-20T13:00:00Z'},{title:'Far',startAt:'2026-12-20T13:00:00Z'}],
    opportunities:[{title:'Call',status:'open',wg:4,deadline:'2026-11-01'},{title:'Closed',status:'closed',wg:1}]});
  assert.deepEqual(d.counts,{members:1,news:1,upcoming:1,calls:1});
  assert.match(d.text,/NEW MEMBERS\n• A <b> — Org/);assert.match(d.html,/A &lt;b&gt;/);assert.doesNotMatch(d.html,/A <b>/);
});
test('countries typed in profiles are placed on the map',()=>{
  assert.equal(countryKey('France'),'France');assert.equal(countryKey('  united states '),'United States of America');
  assert.equal(countryKey('Viet Nam'),'Vietnam');assert.equal(countryKey('Côte d’Ivoire')||countryKey("Cote d'Ivoire"),"Côte d'Ivoire");
  assert.equal(countryKey('Atlantis'),'');
  const r=countryPoints([{country:'France'},{country:'france'},{country:'Peru'},{country:''},{country:'Atlantis'}]);
  assert.deepEqual(r.points.map(p=>[p.country,p.count]),[['France',2],['Peru',1]]);assert.deepEqual(r.unplaced,[['Atlantis',1],['Not stated',1]]);
});
