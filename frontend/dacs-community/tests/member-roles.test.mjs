import test from 'node:test';
import assert from 'node:assert/strict';
import {assignedBadges,canSeeWorkspace,isUnescoSecretariat,broadGroupBadge} from '../lib/member-roles.ts';
const member={role:'member',admin:false,wgs:[],badges:[]};
const board=(id,extra={})=>({id,lead:'',secretariat:[],associateLeads:[],core:[],...extra});
test('self-selected WG interests and ordinary membership badges do not reveal private links',()=>{
 for(const badges of [[],['wg1-member'],['cfd','smc','esc','alliance','iac'],['invented-lead']]) assert.equal(canSeeWorkspace('member',{...member,wgs:[1,2,3,4,5],badges},[]),false);
 assert.deepEqual(assignedBadges('member',member,[board('wg1',{lead:'other'})]),[broadGroupBadge]);
});
test('protected core, leadership and Secretariat roles reveal workspace links',()=>{
 for(const role of ['core','lead','associate','secretariat']) assert.equal(canSeeWorkspace('member',{...member,role},[]),true);
 assert.equal(canSeeWorkspace('member',{...member,admin:true},[]),false);
 assert.equal(canSeeWorkspace('member',{...member,admin:true,role:'unesco-secretariat',badges:['unesco-secretariat']},[]),true);
 for(const badge of ['core','lead','associate','secretariat','wg1-core','wg2-lead','wg3-associate','wg4-secretariat']) assert.equal(canSeeWorkspace('member',{...member,badges:[badge]},[]),true);
});
test('governance appointments produce exact badges and links; removing them revokes that access',()=>{
 for(const id of ['wg1','wg2','wg3','wg4','wg5','cfd','smc','esc','alliance','iac']){
  for(const [field,position] of [['lead','lead'],['secretariat','secretariat'],['associateLeads','associate'],['core','core']]){
   const b=board(id,{[field]:field==='lead'?'member':['member']});
   assert.equal(assignedBadges('member',member,[b])[0].id,id+'-'+position);
   assert.equal(canSeeWorkspace('member',member,[b]),true);
   assert.equal(canSeeWorkspace('member',member,[board(id)]),false);
  }
 }
});
test('manual badges and appointments deduplicate without using profile interests',()=>{
 const badges=assignedBadges('member',{...member,badges:['wg1-lead','iac']},[board('wg1',{lead:'member'})]);
 assert.deepEqual(badges.map(b=>b.id),['wg1-lead','iac']);
});
test('editorial access and review scopes grant no public appointment badge',()=>{
 const role={...member,role:'associate',wgs:[2,4]};
 assert.deepEqual(assignedBadges('member',role,[]),[broadGroupBadge]);
 assert.equal(canSeeWorkspace('member',role,[]),true);
});

test('only explicit UNESCO Secretariat designation grants full editing',()=>{
 const unesco={...member,role:'unesco-secretariat',admin:true,badges:['unesco-secretariat']};
 assert.equal(isUnescoSecretariat(unesco),true);
 for(const role of [{...member,admin:true},{...unesco,admin:false},{...unesco,role:'secretariat'},{...unesco,badges:[]},{...member,role:'secretariat',wgs:[4]}]) assert.equal(isUnescoSecretariat(role),false);
});
test('UNESCO badge appears once and remains distinct from a WG Secretariat appointment',()=>{
 const badges=assignedBadges('member',{...member,role:'unesco-secretariat',admin:true,badges:['unesco-secretariat','unesco-secretariat','secretariat','wg4-secretariat']},[board('wg4',{secretariat:['member']})]);
 assert.deepEqual(badges.map(b=>b.id),['unesco-secretariat','wg4-secretariat']);
 assert.deepEqual(assignedBadges('member',{...member,badges:['unesco-secretariat']},[]),[broadGroupBadge]);
});

test('profile badges name the actual role and body, with leadership first on compact cards',()=>{
 const badges=assignedBadges('member',{...member,badges:['wg1-member','wg2-member','wg3-member','lead']},[board('wg1',{lead:'member'}),board('wg3',{secretariat:['member']}),board('wg5',{associateLeads:['member']})]);
 assert.deepEqual(badges.slice(0,3).map(b=>b.label),['Lead of WG1','Associate Lead of WG5','Secretariat of WG3']);
 assert.equal(badges.some(b=>b.id==='lead'),false);
 assert.equal(badges.find(b=>b.id==='wg2-member').label,'Broad Group member of WG2');
 assert.equal(assignedBadges('member',member,[board('cfd',{lead:'member'})])[0].label,'Lead of CFD');
});

test('new members are interested members until a protected official assignment is made',()=>{
 assert.deepEqual(assignedBadges('newmember',{...member,wgs:[1,2,3,4,5]},[]),[broadGroupBadge]);
 assert.equal(canSeeWorkspace('newmember',member,[]),false);
 for(const role of ['core','lead','associate','secretariat']) {
  const access={...member,role,wgs:[1,3],badges:[role]};
  assert.deepEqual(assignedBadges('member',access,[]),[broadGroupBadge]);
  assert.equal(canSeeWorkspace('member',access,[]),true);
 }
 assert.deepEqual(assignedBadges('member',{...member,role:'secretariat',badges:['secretariat','wg1-secretariat']},[board('wg1',{secretariat:['member']})]).map(b=>b.label),['Secretariat of WG1']);
 assert.deepEqual(assignedBadges('member',{...member,badges:['wg3-core']},[]).map(b=>b.label),['Core Group member of WG3']);
});
test('ESC and SMC badges use committee chair titles and remain distinct from UNESCO access',()=>{
 assert.equal(assignedBadges('a',member,[board('esc',{lead:'a',associateLeads:['b'],secretariat:['c']})])[0].label,'Co-chairperson of ESC');
 assert.equal(assignedBadges('b',member,[board('esc',{lead:'a',associateLeads:['b'],secretariat:['c']})])[0].label,'Co-chairperson of ESC');
 assert.equal(assignedBadges('a',member,[board('smc',{lead:'a',associateLeads:['b'],secretariat:['c']})])[0].label,'Chairperson of SMC');
 assert.equal(assignedBadges('b',member,[board('smc',{lead:'a',associateLeads:['b'],secretariat:['c']})])[0].label,'Vice-chairperson of SMC');
 assert.equal(assignedBadges('c',member,[board('smc',{lead:'a',associateLeads:['b'],secretariat:['c']})])[0].label,'Secretariat of SMC');
 assert.equal(isUnescoSecretariat({...member,role:'secretariat',badges:['esc-secretariat','smc-secretariat']}),false);
 assert.equal(assignedBadges('a',{...member,badges:['esc-lead','esc-associate']},[]).length,1);
});

test('Working Groups chosen in the profile never create a badge; only assigned Broad Group badges show',()=>{
 assert.deepEqual(assignedBadges('member',{...member,wgs:[1,5]},[]),[broadGroupBadge]);
 const ids=assignedBadges('member',{...member,badges:['wg1-member']},[board('wg4',{core:['member']})]).map(b=>b.id);
 assert.deepEqual(ids,['wg4-core','wg1-member']);
});
