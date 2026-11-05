import test from 'node:test';
import assert from 'node:assert/strict';
import {applyAppointments,isAppointmentBadge,appointmentBadge} from '../lib/governance-seats.ts';
const bodies=[{id:'wg3',title:'Working Group 3'},{id:'smc',title:'SMC'},{id:'esc',title:'ESC'}];
test('appointment badges are recognised; membership badges are not',()=>{
  assert.equal(isAppointmentBadge('wg3-lead'),true);assert.equal(isAppointmentBadge('wg3-member'),false);assert.equal(isAppointmentBadge('cfd'),false);
  assert.deepEqual(appointmentBadge('smc-associate'),{body:'smc',position:'associate',field:'associateLeads'});
});
test('ticking a role adds the member to the matching Governance seat',()=>{
  const out=applyAppointments('ana',['wg3-core','wg3-member'],[{id:'wg3',title:'Working Group 3',lead:'bo',secretariat:[],associateLeads:[],core:['cy']}],bodies);
  assert.equal(out.length,1);assert.deepEqual(out[0].core,['cy','ana']);assert.equal(out[0].lead,'bo');
});
test('a single seat is replaced and unticking removes the member',()=>{
  const gov=[{id:'wg3',lead:'bo',secretariat:['ana'],associateLeads:[],core:[]},{id:'smc',lead:'',secretariat:['zed'],associateLeads:[],core:[]}];
  const out=applyAppointments('ana',['wg3-lead','smc-secretariat'],gov,bodies);
  const wg3=out.find(g=>g.id==='wg3'),smc=out.find(g=>g.id==='smc');
  assert.equal(wg3.lead,'ana');assert.deepEqual(wg3.secretariat,[]);assert.deepEqual(smc.secretariat,['ana']);
  assert.deepEqual(applyAppointments('ana',[],[{id:'wg3',lead:'ana',secretariat:[],associateLeads:[],core:['ana']}],bodies)[0],{id:'wg3',title:'Working Group 3',description:'',lead:'',secretariat:[],associateLeads:[],core:[]});
});
test('unchanged records are not rewritten and committee seat rules hold',()=>{
  assert.deepEqual(applyAppointments('ana',['wg3-core'],[{id:'wg3',lead:'',secretariat:[],associateLeads:[],core:['ana']}],bodies),[]);
  assert.throws(()=>applyAppointments('ana',['esc-lead','esc-associate'],[],bodies),/different people/);
});
