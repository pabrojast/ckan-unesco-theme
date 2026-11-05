import test from 'node:test';
import assert from 'node:assert/strict';
import {dueState,dueLabel,isNewFor,sortTasks,nextSeenBy} from '../lib/tasks.ts';
import {activeSlots,padAnswers,answerIncomplete,rankSlots,completeAnswers} from '../lib/meetings.ts';

const t=(o)=>({id:'x',body:'wg1',title:'T',notes:'',status:'todo',priority:'normal',assignees:[],seenBy:[],due:'',createdBy:'a',createdAt:'2026-10-01T00:00:00Z',updatedBy:'a',updatedAt:'2026-10-01T00:00:00Z',...o});

test('deadlines are overdue before today, close from today to two days ahead, and ignored once done',()=>{
 assert.equal(dueState(t({due:'2026-10-18'}),'2026-10-19'),'overdue');
 assert.equal(dueState(t({due:'2026-10-19'}),'2026-10-19'),'soon');
 assert.equal(dueState(t({due:'2026-10-21'}),'2026-10-19'),'soon');
 assert.equal(dueState(t({due:'2026-10-22'}),'2026-10-19'),'later');
 assert.equal(dueState(t({due:'2026-10-01',status:'done'}),'2026-10-19'),'none');
 assert.equal(dueLabel('2026-10-20','2026-10-19'),'Due tomorrow');
 assert.equal(dueLabel('2026-10-16','2026-10-19'),'3 days overdue');
});

test('a task is new for an assignee until they open it, and re-assigning notifies again',()=>{
 assert.equal(isNewFor(t({assignees:['u1']}),'u1'),true);
 assert.equal(isNewFor(t({assignees:['u1'],seenBy:['u1']}),'u1'),false);
 assert.equal(isNewFor(t({assignees:['u1'],status:'done'}),'u1'),false);
 const before=t({assignees:['u1','u2'],seenBy:['u1','u2']});
 assert.deepEqual(nextSeenBy(before,['u1','u3'],'u9'),['u1']);
 assert.deepEqual(nextSeenBy(t({assignees:['u2'],seenBy:['u2']}),['u1'],'u9'),[]);
 assert.deepEqual(nextSeenBy(null,['u1','u9'],'u9'),['u9']);
});

test('tasks sort by priority, then nearest deadline, with completed tasks newest first',()=>{
 const ids=sortTasks([t({id:'a',due:'2026-11-01'}),t({id:'b',priority:'high'}),t({id:'c',due:'2026-10-20'}),t({id:'d'})]).map(x=>x.id);
 assert.deepEqual(ids,['b','c','a','d']);
 assert.deepEqual(sortTasks([t({id:'a',status:'done',updatedAt:'2026-10-01'}),t({id:'b',status:'done',updatedAt:'2026-10-05'})]).map(x=>x.id),['b','a']);
});

test('poll times added after publication keep earlier answers aligned, and withdrawn times are left out',()=>{
 const poll={id:'p',slots:['2026-11-03T09:00:00.000Z','2026-11-04T09:00:00.000Z','2026-11-02T09:00:00.000Z'],withdrawn:[1],durationMinutes:60,status:'open'};
 assert.deepEqual(activeSlots(poll).map(x=>x.index),[2,0]);
 assert.deepEqual(padAnswers(['yes','no'],3),['yes','no',null]);
 assert.equal(answerIncomplete(poll,{answers:['yes','no']}),true);
 assert.equal(answerIncomplete(poll,{answers:['yes','no','if-needed']}),false);
 const ranked=rankSlots(poll,[{answers:['yes','yes'],timeZone:'UTC'},{answers:['yes','no','yes'],timeZone:'UTC'}]);
 assert.deepEqual(ranked.map(r=>[r.index,r.yes]),[[0,2],[2,1]]);
 assert.deepEqual(completeAnswers(padAnswers(['yes'],3)),['yes','no','no']);
});

import {trienniumOf,projectsOf,milestonesOf,looseMilestones,projectProgress,goalsOfGroup} from '../lib/flagship.ts';
test('flagship projects group by main goal and triennium, with milestones and progress',()=>{
 const w=(o)=>({id:'x',body:'wg4',kind:'deliverable',title:'T',mg:'4.1',due:'',status:'planned',lead:'',notes:'',createdAt:'',updatedAt:'',...o});
 const items=[w({id:'p1',due:'2027-01-01'}),w({id:'p2',mg:'4.2'}),w({id:'m1',kind:'milestone',parent:'p1',status:'done'}),w({id:'m2',kind:'milestone',parent:'p1'}),w({id:'m3',kind:'milestone',parent:'gone'})];
 assert.deepEqual(goalsOfGroup(4).map(g=>[g.id,trienniumOf(g.id)]),[['4.1',1],['4.2',2],['4.3',3]]);
 assert.deepEqual(projectsOf(items,'wg4','4.1').map(p=>p.id),['p1']);
 assert.deepEqual(milestonesOf(items,'p1').map(m=>m.id).sort(),['m1','m2']);
 assert.deepEqual(looseMilestones(items,'wg4','4.1').map(m=>m.id),['m3']);
 assert.deepEqual(projectProgress(milestonesOf(items,'p1')),{done:1,total:2,percent:50});
 assert.equal(projectProgress([]),null);
});
