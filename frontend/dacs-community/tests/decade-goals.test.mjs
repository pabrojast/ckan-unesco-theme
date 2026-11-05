import test from 'node:test';
import assert from 'node:assert/strict';
import {linkedGroups,activityGroups,validGoalSelection,goalLabel,challengeLabel,decadeGoals,allGoalIds,isDecadeWide} from '../lib/decade-goals.ts';
import {regions,normaliseRegion,match} from '../lib/data.ts';
test('goals select parent challenges across WGs without selecting unrelated goals',()=>{
 const selected=['1.3','4.2','5.3'];assert.deepEqual(linkedGroups(selected),[1,4,5]);assert.deepEqual(selected,['1.3','4.2','5.3']);
 assert.deepEqual(linkedGroups(['5.2','5.3']),[5]);assert.deepEqual(linkedGroups([]),[]);
});
test('activities appear in each contributing WG; records without goals retain their primary WG',()=>{
 assert.deepEqual(activityGroups({wg:4,mgs:['1.1','4.3','5.2']}),[1,4,5]);
 assert.deepEqual(activityGroups({wg:3}),[3]);assert.deepEqual(activityGroups({wg:1,mgs:['1.1','1.2']}),[1]);
});
test('goal selections reject duplicate, unknown and malformed values',()=>{
 assert.equal(validGoalSelection(decadeGoals.map(g=>g.id)),true);
 for(const value of [['1.1','1.1'],['5.4'],['6.1'],[1.1],'1.1',null]) assert.equal(validGoalSelection(value),false);
 assert.match(goalLabel('4.3'),/Establish a Global Cryosphere Adaptation Knowledge Hub/);
 assert.match(challengeLabel(5),/Amplify the Impact of Cryospheric Science/);
});
test('legacy region labels normalise to the new label without losing matching',()=>{
 assert.equal(normaliseRegion('Europe and North America'),'Western Europe and North America');
 assert.ok(regions.includes('Eastern Europe'));assert.ok(!regions.includes('Europe and North America'));
 const person={skills:[],wgs:[5],region:'Europe and North America',languages:['English']};
 const activity={skills:[],wg:1,mgs:['1.1','5.3'],region:'Western Europe and North America',language:'English'};
 assert.equal(match(person,activity).region,true);assert.equal(match(person,activity).wg,true);
 assert.equal(match({...person,region:'Eastern Europe'},activity).region,false);
});

test('Decade-wide selects every official goal and routes contributions to all five WGs',()=>{
 assert.equal(allGoalIds.length,15);assert.equal(isDecadeWide([...allGoalIds]),true);
 assert.deepEqual(linkedGroups(allGoalIds),[1,2,3,4,5]);
 assert.deepEqual(activityGroups({wg:4,mgs:allGoalIds}),[1,2,3,4,5]);
 assert.equal(isDecadeWide(allGoalIds.slice(1)),false);assert.equal(isDecadeWide([...allGoalIds.slice(1),'5.3']),false);
});
test('Working Group 5 runs its three main goals in parallel; triennia are 2026-2028, 2029-2031 and 2032-2034',async()=>{
  const {concurrentGoals,runsConcurrently,goalsOfGroup,triennia,currentTriennium}=await import('../lib/flagship.ts');
  assert.equal(runsConcurrently(5),true);
  for(const wg of [1,2,3,4]) assert.equal(runsConcurrently(wg),false);
  assert.equal(goalsOfGroup(5).length,3);
  assert.deepEqual(triennia.map((t)=>t.period),['2026–2028','2029–2031','2032–2034']);
  for(const [y,n] of [[2025,1],[2026,1],[2028,1],[2029,2],[2031,2],[2032,3],[2034,3],[2035,0]]) assert.equal(currentTriennium(new Date(Date.UTC(y,5,1))),n);
  assert.match(concurrentGoals[5].quote,/run in parallel/);
});
