import {before,after,beforeEach,test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {initializeTestEnvironment,assertSucceeds,assertFails} from '@firebase/rules-unit-testing';
import {doc,setDoc,getDoc,getDocs,collection,query,where,updateDoc,deleteDoc,writeBatch,serverTimestamp,Timestamp} from 'firebase/firestore';
let env;
const calendarEvent=(extra={})=>({owner:'alice',title:'Cryosphere meeting',description:'',startAt:Timestamp.fromDate(new Date('2026-10-07T09:00:00Z')),endAt:Timestamp.fromDate(new Date('2026-10-07T10:00:00Z')),timeZone:'Europe/Paris',location:'Online',registrationUrl:'https://example.org/register',joinUrl:'https://example.org/join',ocs:[1,5],mgs:['1.1','5.3'],createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
const as=(uid,verified=true)=>env.authenticatedContext(uid,{email:uid+'@example.test',email_verified:verified}).firestore();
const profile=(extra={})=>({name:'Test member',headline:'Hydrologist',organisation:'Research institute',country:'France',region:'Europe and North America',languages:['English'],skills:['Hydrology'],wgs:[4],bio:'Research',motivation:'Contribute',contribution:'Review methods',availability:'2–4 hours / month',website:'',visibility:'community',contactConsent:false,contact:'',consent:true,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
const op=(extra={})=>({owner:'alice',wg:4,mgs:[String(extra.wg || 4)+'.1'],title:'Review adaptation evidence',description:'Help review hydrology methods.',skills:['Hydrology'],region:'Global',language:'English',commitment:'2–4 hours / month',deadline:'',type:'Scientific review',status:'pending',createdAt:serverTimestamp(),...extra});
async function seedRole(uid,role,wgs=[],admin=false){await env.withSecurityRulesDisabled(async c=>setDoc(doc(c.firestore(),'roles',uid),admin?{admin:true,role:'unesco-secretariat',wgs,badges:['unesco-secretariat']}:{admin:false,role,wgs}));}
async function seedMember(uid){await assertSucceeds(setDoc(doc(as(uid),'profiles',uid),profile()));}
before(async()=>{env=await initializeTestEnvironment({projectId:'demo-dacs-community',firestore:{rules:readFileSync(new URL('../../../ckanext/theme_ejemplo/community_data/dacs.rules',import.meta.url),'utf8')}})});
after(async()=>{await env.cleanup()});
beforeEach(async()=>{await env.clearFirestore();await seedRole('secretariat','member',[],true)});
test('signed-in accounts can create profiles without email verification; guests and other owners cannot',async()=>{await seedMember('alice');await assertSucceeds(setDoc(doc(as('bob',false),'profiles','bob'),profile()));await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(),'profiles','alice')));await assertFails(setDoc(doc(as('bob'),'profiles','alice'),profile()));});
test('private profile and feedback visibility are enforced',async()=>{await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice'),'privateProfiles','alice'),{sentiment:'Need support',feedback:'Private feedback',updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('bob'),'privateProfiles','alice')));await assertSucceeds(getDoc(doc(as('secretariat'),'privateProfiles','alice')));await assertSucceeds(updateDoc(doc(as('alice'),'profiles','alice'),{visibility:'private',updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('bob'),'profiles','alice')));await assertSucceeds(getDoc(doc(as('alice'),'profiles','alice')));await assertSucceeds(getDoc(doc(as('secretariat'),'profiles','alice')));});
test('directory query reads only community profiles',async()=>{await seedMember('alice');await assertSucceeds(setDoc(doc(as('carol'),'profiles','carol'),profile({visibility:'private'})));const result=await assertSucceeds(getDocs(query(collection(as('bob'),'profiles'),where('visibility','==','community'))));assert.equal(result.size,1);await assertFails(getDocs(collection(as('bob'),'profiles')));});
test('schema and contact consent prevent extra fields or foreign contact emails',async()=>{await assertFails(setDoc(doc(as('alice'),'profiles','alice'),profile({admin:true})));await assertFails(setDoc(doc(as('alice'),'profiles','alice'),profile({skills:[123]})));await assertFails(setDoc(doc(as('alice'),'profiles','alice'),profile({contactConsent:true,contact:'someoneelse@example.test'})));await assertSucceeds(setDoc(doc(as('alice'),'profiles','alice'),profile({contactConsent:true,contact:'alice@example.test'})));await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{name:'',updatedAt:serverTimestamp()}));});
test('members cannot self-assign roles; Secretariat can delegate editing access',async()=>{await assertFails(setDoc(doc(as('alice'),'roles','alice'),{admin:true,role:'lead',wgs:[4]}));await assertSucceeds(setDoc(doc(as('secretariat'),'roles','alice'),{admin:false,role:'core',wgs:[4]}));await assertFails(updateDoc(doc(as('alice'),'roles','alice'),{wgs:[1,2,3,4,5]}));await assertSucceeds(updateDoc(doc(as('secretariat'),'roles','alice'),{admin:true,role:'unesco-secretariat',badges:['unesco-secretariat']}));await assertFails(updateDoc(doc(as('bob'),'roles','alice'),{admin:false}));});
test('member activities start pending; only scoped managers publish',async()=>{await seedMember('alice');await seedRole('lead4','lead',[4]);await seedRole('lead1','lead',[1]);await assertFails(setDoc(doc(as('alice'),'opportunities','wrong'),op({status:'open'})));await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));await assertFails(getDoc(doc(as('bob'),'opportunities','activity')));await assertSucceeds(getDoc(doc(as('alice'),'opportunities','activity')));await assertFails(updateDoc(doc(as('lead1'),'opportunities','activity'),{status:'open'}));await assertSucceeds(updateDoc(doc(as('lead4'),'opportunities','activity'),{status:'open'}));await assertSucceeds(getDoc(doc(as('bob'),'opportunities','activity')));await assertFails(updateDoc(doc(as('lead4'),'opportunities','activity'),{wg:1,status:'closed'}));await assertFails(updateDoc(doc(as('lead4'),'opportunities','activity'),{owner:'lead4'}));});
test('scoped contribution query and status updates preserve identity and withdrawal',async()=>{await seedMember('alice');await seedRole('lead4','core',[4]);await seedRole('lead1','lead',[1]);await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'opportunities','activity'),op({status:'open'})));const p={opportunity_id:'activity',member_id:'alice',member_name:'Test member',opportunity_title:'Review adaptation evidence',wg:4,message:'I can review methods.',status:'Interested',createdAt:serverTimestamp(),updatedAt:serverTimestamp()};await assertFails(setDoc(doc(as('alice'),'contributions','random'),p));await assertSucceeds(setDoc(doc(as('alice'),'contributions','activity_alice'),p));await assertFails(setDoc(doc(as('alice'),'contributions','activity_alice'),p));await assertFails(getDoc(doc(as('bob'),'contributions','activity_alice')));await assertSucceeds(getDocs(query(collection(as('alice'),'contributions'),where('member_id','==','alice'))));await assertSucceeds(getDocs(query(collection(as('lead4'),'contributions'),where('wg','in',[4]))));await assertFails(updateDoc(doc(as('lead1'),'contributions','activity_alice'),{status:'Selected',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('alice'),'contributions','activity_alice'),{status:'Completed',updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(as('lead4'),'contributions','activity_alice'),{status:'Selected',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'contributions','activity_alice'),{member_id:'lead4',updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(as('alice'),'contributions','activity_alice'),{status:'Withdrawn',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'contributions','activity_alice'),{status:'Selected',updatedAt:serverTimestamp()}));});
test('author identity on posts and ownership of follows cannot be forged',async()=>{await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice'),'posts','post'),{author:'alice',author_name:'Test member',wg:4,body:'An update',createdAt:serverTimestamp()}));await assertFails(setDoc(doc(as('alice'),'posts','fake'),{author:'bob',author_name:'Test member',wg:4,body:'Fake',createdAt:serverTimestamp()}));await assertFails(setDoc(doc(as('alice'),'posts','wrongname'),{author:'alice',author_name:'Secretariat',wg:4,body:'Fake',createdAt:serverTimestamp()}));await assertSucceeds(setDoc(doc(as('alice'),'preferences','alice'),{wgs:[4,5]}));await assertFails(setDoc(doc(as('alice'),'preferences','bob'),{wgs:[4]}));await assertFails(setDoc(doc(as('alice'),'preferences','alice'),{wgs:[9]}));});

const owner=(verified=true)=>env.authenticatedContext('alexandre',{email:'alexandregermouty@gmail.com',email_verified:verified}).firestore();
test('verified Alexandre email receives Secretariat access without a role document',async()=>{await assertSucceeds(setDoc(doc(owner(),'roles','bob'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));await assertFails(setDoc(doc(owner(false),'roles','carol'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));await seedMember('alice');await assertSucceeds(updateDoc(doc(owner(),'profiles','alice'),{name:'Edited by Secretariat',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('carol',false),'profiles','alice'),{name:'Unverified ordinary member edit',updatedAt:serverTimestamp()}));});
test('custom categories are shared before profile creation, immutable for members, and retireable by Secretariat',async()=>{const id='a'.repeat(64),ref=doc(as('alice'),'categories',id);const category={kind:'skills',label:'Ice chemistry',normalized:'ice chemistry',enabled:true,createdBy:'alice',createdAt:serverTimestamp()};await assertSucceeds(setDoc(ref,category));const shared=await assertSucceeds(getDoc(doc(as('bob'),'categories',id)));assert.equal(shared.data().label,'Ice chemistry');await assertFails(updateDoc(ref,{label:'Changed'}));await assertFails(updateDoc(ref,{enabled:false}));await assertSucceeds(updateDoc(doc(owner(),'categories',id),{enabled:false}));await assertSucceeds(setDoc(doc(as('bob',false),'categories','b'.repeat(64)),{...category,createdBy:'bob'}));await assertFails(setDoc(doc(as('alice'),'categories','c'.repeat(64)),{...category,kind:'admin'}));});
test('new profile answers accept custom strings; gender remains private and list values are bounded',async()=>{await assertSucceeds(setDoc(doc(as('alice'),'profiles','alice'),profile({skills:['Ice chemistry'],languages:['Vietnamese'],careerStage:'Independent consultant',educationLevel:'Post-master diploma',cryosphereTypes:['Tropical glaciers'],hasPhoto:false,onboardingVersion:2})));await assertSucceeds(setDoc(doc(as('alice'),'privateProfiles','alice'),{gender:'Woman',sentiment:'Interested',feedback:'',updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('bob'),'privateProfiles','alice')));await assertSucceeds(getDoc(doc(owner(),'privateProfiles','alice')));await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{gender:'Woman',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{skills:['x'.repeat(101)],updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{skills:Array.from({length:21},(_,i)=>'Skill '+i),updatedAt:serverTimestamp()}));});
test('photos enforce ownership, size, image format and profile visibility',async()=>{const db=as('alice');const batch=writeBatch(db);batch.set(doc(db,'profiles','alice'),profile({hasPhoto:true,onboardingVersion:2}));batch.set(doc(db,'profilePhotos','alice'),{data:'data:image/jpeg;base64,AA==',updatedAt:serverTimestamp()});await assertSucceeds(batch.commit());await assertSucceeds(getDoc(doc(as('bob'),'profilePhotos','alice')));await assertFails(updateDoc(doc(as('bob'),'profilePhotos','alice'),{data:'data:image/jpeg;base64,AA==',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(db,'profilePhotos','alice'),{data:'data:image/svg+xml;base64,AA==',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(db,'profilePhotos','alice'),{data:'data:image/jpeg;base64,'+'a'.repeat(100000),updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(db,'profiles','alice'),{visibility:'private',updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('bob'),'profilePhotos','alice')));await assertSucceeds(getDoc(doc(owner(),'profilePhotos','alice')));});
const board=(extra={})=>({title:'Working Group 4',description:'Adaptation',lead:'lead4',secretariat:[],associateLeads:[],core:[],updatedAt:serverTimestamp(),...extra});
test('governance appointments grant group-scoped review access and can be revoked',async()=>{await seedMember('alice');await assertFails(setDoc(doc(as('alice'),'governance','wg4'),board({lead:'alice'})));await assertSucceeds(setDoc(doc(owner(),'governance','wg4'),board()));await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));await assertSucceeds(getDoc(doc(as('lead4'),'opportunities','activity')));await assertSucceeds(updateDoc(doc(as('lead4'),'opportunities','activity'),{status:'open'}));await assertFails(updateDoc(doc(as('lead1'),'opportunities','activity'),{status:'closed'}));await assertSucceeds(updateDoc(doc(owner(),'governance','wg4'),{lead:'',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'opportunities','activity'),{status:'closed'}));for(const id of ['wg1','wg2','wg3','wg5','cfd','smc','esc','alliance'])await assertSucceeds(setDoc(doc(owner(),'governance',id),board({title:id,lead:''})));await assertFails(setDoc(doc(owner(),'governance','other'),board()));});
test('Secretariat can correct and remove records; members cannot edit others or bypass schemas',async()=>{await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice'),'posts','post'),{author:'alice',author_name:'Test member',wg:4,body:'An update',createdAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('bob'),'posts','post'),{body:'Unauthorised'}));await assertSucceeds(updateDoc(doc(owner(),'posts','post'),{body:'Corrected update'}));await assertFails(updateDoc(doc(owner(),'posts','post'),{author:'bob'}));await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));await assertSucceeds(updateDoc(doc(owner(),'opportunities','activity'),{title:'Corrected activity',status:'open'}));await assertFails(updateDoc(doc(as('bob'),'opportunities','activity'),{title:'Bad edit'}));await assertFails(deleteDoc(doc(as('bob'),'profiles','alice')));await assertSucceeds(deleteDoc(doc(owner(),'posts','post')));await assertSucceeds(deleteDoc(doc(owner(),'opportunities','activity')));await assertSucceeds(deleteDoc(doc(owner(),'profiles','alice')));});
test('guests remain blocked; unverified members can read categories and governance',async()=>{for(const name of ['categories','governance','profilePhotos']) await assertFails(getDocs(collection(env.unauthenticatedContext().firestore(),name)));for(const name of ['categories','governance']) await assertSucceeds(getDocs(collection(as('bob',false),name)));});

test('maximum supported category selections and appointments remain writable',async()=>{const values=Array.from({length:20},(_,i)=>'Option '+i);await assertSucceeds(setDoc(doc(as('alice'),'profiles','alice'),profile({skills:values,languages:values,cryosphereTypes:values})));await assertSucceeds(setDoc(doc(owner(),'governance','wg4'),board({secretariat:values,associateLeads:values,core:values})));});

test('direct review grants do not depend on participation labels and appointments revoke independently',async()=>{await seedMember('alice');await seedRole('reviewer','member',[4]);await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));await assertSucceeds(updateDoc(doc(as('reviewer'),'opportunities','activity'),{status:'open'}));await assertSucceeds(setDoc(doc(owner(),'governance','wg4'),board({lead:'reviewer'})));await assertSucceeds(updateDoc(doc(owner(),'governance','wg4'),{lead:'',updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(as('reviewer'),'opportunities','activity'),{status:'closed'}));await assertSucceeds(updateDoc(doc(owner(),'roles','reviewer'),{wgs:[]}));await assertFails(updateDoc(doc(as('reviewer'),'opportunities','activity'),{status:'open'}));});

test('only Secretariat may assign official badges; member profiles cannot impersonate appointments',async()=>{
 await seedMember('alice');
 await assertFails(setDoc(doc(as('alice'),'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg1-lead','unesco-secretariat']}));
 await assertSucceeds(setDoc(doc(owner(),'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg1-member','iac']}));
 await assertFails(updateDoc(doc(as('alice'),'roles','alice'),{badges:['wg1-core']}));
 await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{badges:['unesco-secretariat'],updatedAt:serverTimestamp()}));
 const result=await assertSucceeds(getDoc(doc(as('bob'),'roles','alice')));assert.deepEqual(result.data().badges,['wg1-member','iac']);
});
test('badge schema accepts legacy records and rejects unknown or oversized badge assignments',async()=>{
 await assertSucceeds(setDoc(doc(owner(),'roles','alice'),{admin:false,role:'member',wgs:[]}));
 await assertSucceeds(updateDoc(doc(owner(),'roles','alice'),{badges:['wg1-member','wg1-lead','cfd','smc','esc','alliance','iac']}));
 await assertFails(updateDoc(doc(owner(),'roles','alice'),{badges:['superadmin']}));
 await assertFails(updateDoc(doc(owner(),'roles','alice'),{badges:[123]}));
 await assertFails(updateDoc(doc(owner(),'roles','alice'),{badges:Array(21).fill('wg1-member')}));
});
test('IAC appointments require Secretariat authority',async()=>{
 await assertFails(setDoc(doc(as('alice'),'governance','iac'),board({lead:'alice',title:'IAC'})));
 await assertSucceeds(setDoc(doc(owner(),'governance','iac'),board({lead:'alice',title:'IAC'})));
 await assertSucceeds(getDoc(doc(as('bob'),'governance','iac')));
});

test('WG Secretariats and bare legacy admin flags cannot edit globally or read private feedback',async()=>{
 await seedMember('alice');
 await assertSucceeds(setDoc(doc(as('alice'),'privateProfiles','alice'),{sentiment:'Private',feedback:'Private feedback',updatedAt:serverTimestamp()}));
 await seedRole('wgsecretariat','secretariat',[4]);
 await env.withSecurityRulesDisabled(async c=>setDoc(doc(c.firestore(),'roles','legacyadmin'),{admin:true,role:'secretariat',wgs:[],badges:[]}));
 for(const uid of ['wgsecretariat','legacyadmin']) {
  await assertFails(getDoc(doc(as(uid),'privateProfiles','alice')));
  await assertFails(updateDoc(doc(as(uid),'profiles','alice'),{name:'Bad global edit',updatedAt:serverTimestamp()}));
  await assertFails(setDoc(doc(as(uid),'roles','bob'),{admin:false,role:'member',wgs:[]}));
  await assertFails(setDoc(doc(as(uid),'governance','wg1'),board({title:'WG1'})));
 }
 await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));
 await assertSucceeds(updateDoc(doc(as('wgsecretariat'),'opportunities','activity'),{status:'open'}));
});
test('UNESCO designation, admin flag and official badge must agree',async()=>{
 for(const data of [
  {admin:true,role:'secretariat',wgs:[],badges:['unesco-secretariat']},
  {admin:true,role:'unesco-secretariat',wgs:[],badges:[]},
  {admin:false,role:'member',wgs:[],badges:['unesco-secretariat']},
  {admin:false,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']},
 ]) await assertFails(setDoc(doc(owner(),'roles','bob'),data));
 await assertSucceeds(setDoc(doc(owner(),'roles','bob'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));
});
test('explicit UNESCO Secretariat edits globally; removing designation revokes access immediately',async()=>{
 await seedMember('alice');
 await assertSucceeds(setDoc(doc(owner(),'roles','bob'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));
 await assertSucceeds(updateDoc(doc(as('bob'),'profiles','alice'),{name:'UNESCO edit',updatedAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(as('bob'),'governance','cfd'),board({title:'CFD',lead:''})));
 await assertSucceeds(setDoc(doc(owner(),'roles','bob'),{admin:false,role:'secretariat',wgs:[4],badges:['wg4-secretariat']}));
 await assertFails(updateDoc(doc(as('bob'),'profiles','alice'),{name:'Revoked edit',updatedAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('bob'),'governance','cfd'),board({title:'CFD',lead:''})));
});

test('bounded string lists reject converted values, mixed types and embedded newlines',async()=>{
 for(const skills of [[123],[true],[null],[{label:'Hydrology'}],['Hydrology',123],['Hydrology\nHidden'],[''],['x'.repeat(101)]])
  await assertFails(setDoc(doc(as('alice'),'profiles','alice'),profile({skills})));
 await assertSucceeds(setDoc(doc(as('alice'),'profiles','alice'),profile({skills:[],languages:[],cryosphereTypes:[]})));
 await assertSucceeds(updateDoc(doc(as('alice'),'profiles','alice'),{skills:['Ice chemistry','Glaciologie'],updatedAt:serverTimestamp()}));
});

test('unverified members complete onboarding and contribute without role escalation',async()=>{
 const db=as('newmember',false);
 const batch=writeBatch(db);
 batch.set(doc(db,'profiles','newmember'),profile({onboardingVersion:2,careerStage:'Early-career professional',educationLevel:'Master’s degree',cryosphereTypes:['Mountain glaciers'],hasPhoto:true}));
 batch.set(doc(db,'privateProfiles','newmember'),{gender:'Prefer not to say',sentiment:'Interested',feedback:'',updatedAt:serverTimestamp()});
 batch.set(doc(db,'profilePhotos','newmember'),{data:'data:image/jpeg;base64,AA==',updatedAt:serverTimestamp()});
 await assertSucceeds(batch.commit());
 await assertSucceeds(getDocs(query(collection(db,'profiles'),where('visibility','==','community'))));
 await assertSucceeds(setDoc(doc(db,'preferences','newmember'),{wgs:[5]}));
 await assertSucceeds(setDoc(doc(db,'posts','update'),{author:'newmember',author_name:'Test member',wg:5,body:'My first update',createdAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(db,'opportunities','proposal'),op({owner:'newmember',wg:5})));
 await assertFails(setDoc(doc(db,'roles','newmember'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));
 await assertFails(setDoc(doc(db,'governance','wg5'),board({title:'Amplify',lead:'newmember'})));
 await assertFails(setDoc(doc(owner(false),'roles','alexandre'),{admin:true,role:'unesco-secretariat',wgs:[],badges:['unesco-secretariat']}));
});
test('protected UNESCO roles work without verification; unverified WG Secretariats stay scoped',async()=>{
 await seedMember('alice');
 await assertSucceeds(setDoc(doc(as('alice'),'privateProfiles','alice'),{sentiment:'Private',feedback:'Private feedback',updatedAt:serverTimestamp()}));
 await seedRole('wgsecretariat','secretariat',[4]);
 await assertFails(getDoc(doc(as('wgsecretariat',false),'privateProfiles','alice')));
 await assertFails(updateDoc(doc(as('wgsecretariat',false),'profiles','alice'),{name:'Bad edit',updatedAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(as('alice'),'opportunities','activity'),op()));
 await assertSucceeds(updateDoc(doc(as('wgsecretariat',false),'opportunities','activity'),{status:'open'}));
 await assertSucceeds(getDoc(doc(as('secretariat',false),'privateProfiles','alice')));
 await assertSucceeds(updateDoc(doc(as('secretariat',false),'profiles','alice'),{name:'UNESCO edit',updatedAt:serverTimestamp()}));
});

test('ESC accepts two distinct co-chairpersons and one Secretariat; members cannot edit seats',async()=>{
 const value=board({title:'ESC',lead:'chair1',associateLeads:['chair2'],secretariat:['secretary'],core:['representative']});
 await assertSucceeds(setDoc(doc(owner(),'governance','esc'),value));
 await assertFails(updateDoc(doc(as('chair1'),'governance','esc'),{lead:'other',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(owner(),'governance','esc'),{associateLeads:['chair2','chair3'],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(owner(),'governance','esc'),{secretariat:['secretary','other'],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(owner(),'governance','esc'),{associateLeads:['chair1'],updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(owner(),'governance','esc'),{lead:'',associateLeads:[],secretariat:[],updatedAt:serverTimestamp()}));
});
test('SMC accepts one Chairperson, one Vice-chairperson and one Secretariat; WG seats remain plural',async()=>{
 await assertSucceeds(setDoc(doc(owner(),'governance','smc'),board({title:'SMC',lead:'chair',associateLeads:['vice'],secretariat:['secretary']})));
 await assertFails(updateDoc(doc(owner(),'governance','smc'),{associateLeads:['vice','other'],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(owner(),'governance','smc'),{secretariat:['secretary','other'],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(owner(),'governance','smc'),{associateLeads:['chair'],updatedAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(owner(),'governance','wg1'),board({title:'WG1',associateLeads:['associate1','associate2'],secretariat:['secretary1','secretary2']})));
});
test('calendar creation needs a profile and its true owner; signed-in members can read events',async()=>{
 await assertFails(setDoc(doc(as('alice'),'events','no-profile'),calendarEvent()));
 await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice',false),'events','meeting'),calendarEvent()));
 await assertSucceeds(getDoc(doc(as('bob'),'events','meeting')));
 await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(),'events','meeting')));
 await assertFails(setDoc(doc(as('alice'),'events','forged'),calendarEvent({owner:'bob'})));
});
test('calendar owner and UNESCO can edit or delete; WG Secretariat cannot edit another member’s event',async()=>{
 await seedMember('alice');await seedRole('wg-secretary','secretariat',[1,5]);
 await assertSucceeds(setDoc(doc(as('alice'),'events','meeting'),calendarEvent()));
 await assertFails(updateDoc(doc(as('bob'),'events','meeting'),{title:'Hijacked',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('wg-secretary'),'events','meeting'),{title:'Hijacked',updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('alice'),'events','meeting'),{title:'Updated by organiser',updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('secretariat'),'events','meeting'),{description:'Corrected',updatedAt:serverTimestamp()}));
 await assertFails(deleteDoc(doc(as('bob'),'events','meeting')));
 await assertFails(deleteDoc(doc(as('wg-secretary'),'events','meeting')));
 await assertSucceeds(deleteDoc(doc(as('secretariat'),'events','meeting')));
 await assertSucceeds(setDoc(doc(as('alice'),'events','own'),calendarEvent()));await assertSucceeds(deleteDoc(doc(as('alice'),'events','own')));
});
test('calendar ownership and creation time cannot be changed by the owner or UNESCO',async()=>{
 await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice'),'events','meeting'),calendarEvent()));
 for(const uid of ['alice','secretariat']) {
  await assertFails(updateDoc(doc(as(uid),'events','meeting'),{owner:'bob',updatedAt:serverTimestamp()}));
  await assertFails(updateDoc(doc(as(uid),'events','meeting'),{createdAt:Timestamp.fromMillis(1),updatedAt:serverTimestamp()}));
 }
});
test('calendar validates OC/MG associations, dates, field sizes and safe links',async()=>{
 await seedMember('alice');let i=0;
 for(const extra of [{ocs:[]},{ocs:[6]},{ocs:[1,1]},{mgs:[]},{mgs:['5.4']},{ocs:[1],mgs:['5.3']},{mgs:['1.1','1.1']},{joinUrl:'javascript:alert(1)'},{registrationUrl:'https://example.org/ bad'},{title:''},{title:'x'.repeat(161)},{extra:'field'},{startAt:'2026-10-07'},{endAt:Timestamp.fromDate(new Date('2026-10-07T08:00:00Z'))},{endAt:Timestamp.fromDate(new Date('2026-12-07T10:00:00Z'))},{updatedAt:Timestamp.fromMillis(1)}]) await assertFails(setDoc(doc(as('alice'),'events','bad'+i++),calendarEvent(extra)));
 await assertSucceeds(setDoc(doc(as('alice'),'events','all-goals'),calendarEvent({ocs:[1,2,3,4,5],mgs:['1.1','1.2','1.3','2.1','2.2','2.3','3.1','3.2','3.3','4.1','4.2','4.3','5.1','5.2','5.3']})));
});
test('both bounded calendar endpoint queries are permitted for signed-in members',async()=>{
 await seedMember('alice');await assertSucceeds(setDoc(doc(as('alice'),'events','meeting'),calendarEvent()));
 for(const field of ['startAt','endAt']) {const results=await assertSucceeds(getDocs(query(collection(as('bob'),'events'),where(field,'>=',Timestamp.fromDate(new Date('2026-10-01'))),where(field,'<',Timestamp.fromDate(new Date('2026-11-01'))))));assert.equal(results.size,1);}
});

test('new activity proposals accept named custom types and goals in several WGs',async()=>{
 await seedMember('alice');
 await assertSucceeds(setDoc(doc(as('alice'),'opportunities','cross-group'),op({wg:1,mgs:['1.1','4.2','5.3'],type:'Community science campaign',region:'Eastern Europe'})));
 await assertFails(getDoc(doc(as('bob'),'opportunities','cross-group')));
 await seedRole('lead1','lead',[1]);await seedRole('lead4','lead',[4]);
 await assertFails(updateDoc(doc(as('lead4'),'opportunities','cross-group'),{status:'open'}));
 await assertSucceeds(updateDoc(doc(as('lead1'),'opportunities','cross-group'),{status:'open'}));
 await assertSucceeds(getDoc(doc(as('bob'),'opportunities','cross-group')));
 await assertFails(updateDoc(doc(as('lead4'),'opportunities','cross-group'),{mgs:['4.1'],status:'closed'}));
});
test('activity goals and reviewing WG are validated; legacy records can still be reviewed',async()=>{
 await seedMember('alice');let i=0;
 for(const change of [{mgs:[]},{mgs:['4.4']},{mgs:['4.1','4.1']},{wg:2,mgs:['4.1']},{mgs:['admin']},{type:''},{type:'x'.repeat(101)}]) await assertFails(setDoc(doc(as('alice'),'opportunities','invalid'+i++),op(change)));
 const missing=op();delete missing.mgs;await assertFails(setDoc(doc(as('alice'),'opportunities','missing'),missing));
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'opportunities','legacy'),missing));
 await seedRole('lead4','lead',[4]);await assertSucceeds(updateDoc(doc(as('lead4'),'opportunities','legacy'),{status:'open'}));
 await assertSucceeds(updateDoc(doc(as('secretariat'),'opportunities','legacy'),{description:'Legacy data retained'}));
});
test('contribution type categories are shared with other members and protected from member edits',async()=>{
 const ref=doc(as('alice'),'categories','d'.repeat(64));
 await assertSucceeds(setDoc(ref,{kind:'contributionTypes',label:'Community science campaign',normalized:'community science campaign',enabled:true,createdBy:'alice',createdAt:serverTimestamp()}));
 assert.equal((await assertSucceeds(getDoc(doc(as('bob'),'categories','d'.repeat(64))))).data().label,'Community science campaign');
 await assertFails(updateDoc(ref,{label:'Changed'}));await assertFails(updateDoc(ref,{enabled:false}));
 await assertSucceeds(updateDoc(doc(as('secretariat'),'categories','d'.repeat(64)),{enabled:false}));
});
test('Eastern Europe and Western Europe/North America can be saved; legacy regions stay valid',async()=>{
 await seedMember('alice');
 for(const region of ['Eastern Europe','Western Europe and North America','Europe and North America']) {
  await assertSucceeds(updateDoc(doc(as('alice'),'profiles','alice'),{region,updatedAt:serverTimestamp()}));
  await assertSucceeds(setDoc(doc(as('alice'),'opportunities',region.replaceAll(' ','-')),op({region})));
 }
 await assertFails(updateDoc(doc(as('alice'),'profiles','alice'),{region:'Invented region',updatedAt:serverTimestamp()}));
});

// Integrated logo review, meeting audiences and news conversations.
const future=(days)=>Timestamp.fromMillis(Date.now()+days*86400000);
const poll=(extra={})=>({owner:'lead4',title:'WG4 coordination',body:'wg4',meetingType:'leadership',mgs:['4.1'],durationMinutes:60,slots:[future(7),future(8)],deadline:future(3),status:'open',selectedSlot:-1,eventId:'',createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
const response=(uid='lead4',extra={})=>({pollId:'p',uid,name:'Test member',timeZone:'Europe/Paris',answers:['yes','if-needed'],updatedAt:serverTimestamp(),...extra});
async function appointedBody(body='wg4'){await assertSucceeds(setDoc(doc(owner(),'governance',body),board({lead:'lead4',associateLeads:['associate'],secretariat:['wgsec'],core:['core4']})));}
async function meetingSetup(){for(const u of ['lead4','associate','wgsec','core4','broad4','outsider'])await seedMember(u);await appointedBody();await assertSucceeds(updateDoc(doc(as('outsider'),'profiles','outsider'),{wgs:[1],updatedAt:serverTimestamp()}));}
test('leadership, core and broad poll audiences are enforced at the database',async()=>{await meetingSetup();for(const type of ['leadership','core','broad'])await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls',type),poll({meetingType:type})));for(const u of ['lead4','associate','wgsec'])for(const t of ['leadership','core','broad'])await assertSucceeds(getDoc(doc(as(u),'meetingPolls',t)));await assertFails(getDoc(doc(as('core4'),'meetingPolls','leadership')));await assertSucceeds(getDoc(doc(as('core4'),'meetingPolls','core')));await assertSucceeds(getDoc(doc(as('broad4'),'meetingPolls','broad')));await assertFails(getDoc(doc(as('broad4'),'meetingPolls','core')));for(const t of ['leadership','core','broad'])await assertFails(getDoc(doc(as('outsider'),'meetingPolls',t)));await assertSucceeds(getDocs(query(collection(as('core4'),'meetingPolls'),where('body','==','wg4'),where('meetingType','in',['core','broad']))));await assertFails(getDocs(collection(as('broad4'),'meetingPolls')));});
test('only scoped leadership can create polls; direct review grants and broad interests confer no leadership',async()=>{await meetingSetup();await seedRole('broad4','member',[4]);for(const u of ['core4','broad4','outsider'])await assertFails(setDoc(doc(as(u),'meetingPolls',u),poll({owner:u})));await assertSucceeds(setDoc(doc(as('wgsec'),'meetingPolls','p'),poll({owner:'wgsec'})));await assertFails(updateDoc(doc(as('outsider'),'meetingPolls','p'),{title:'Impersonated',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('wgsec'),'meetingPolls','p'),{body:'wg1',updatedAt:serverTimestamp()}));});
test('protected leadership badges, CFD, Alliance and chair appointments grant the intended scope',async()=>{for(const u of ['badge','chair'])await seedMember(u);await assertSucceeds(setDoc(doc(owner(),'roles','badge'),{admin:false,role:'member',wgs:[],badges:['cfd-secretariat','alliance-associate','wg1-lead']}));for(const body of ['cfd','alliance','wg1'])await assertSucceeds(setDoc(doc(as('badge'),'meetingPolls',body),poll({owner:'badge',body,mgs:body==='wg1'?['1.1']:[]})));await assertFails(setDoc(doc(as('badge'),'meetingPolls','other'),poll({owner:'badge',body:'wg2',mgs:['2.1']})));await assertSucceeds(setDoc(doc(owner(),'governance','esc'),board({lead:'chair',associateLeads:[],secretariat:[]})));await assertSucceeds(setDoc(doc(as('chair'),'meetingPolls','esc'),poll({owner:'chair',body:'esc',mgs:[]})));});
test('poll response ownership, membership, shape and deadlines cannot be bypassed',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','p'),poll({meetingType:'core'})));await assertSucceeds(setDoc(doc(as('core4'),'pollResponses','p_core4'),response('core4')));await assertFails(setDoc(doc(as('broad4'),'pollResponses','p_broad4'),response('broad4')));await assertFails(setDoc(doc(as('lead4'),'pollResponses','p_core4'),response('core4')));await assertFails(setDoc(doc(as('core4'),'pollResponses','p_core4'),response('core4',{answers:['yes']})));await assertFails(setDoc(doc(as('core4'),'pollResponses','p_core4'),response('core4',{answers:['yes','unknown']})));await assertSucceeds(getDocs(query(collection(as('core4'),'pollResponses'),where('pollId','==','p'))));await assertFails(getDocs(query(collection(as('outsider'),'pollResponses'),where('pollId','==','p'))));await assertSucceeds(getDocs(query(collection(as('core4'),'pollResponses'),where('uid','==','core4'))));await assertSucceeds(updateDoc(doc(as('lead4'),'meetingPolls','p'),{status:'closed',updatedAt:serverTimestamp()}));await assertFails(setDoc(doc(as('core4'),'pollResponses','p_core4'),response('core4')));});
test('an open poll link lets signed-in people answer without an appointment; closed links and listing stay restricted',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','p'),poll({linkAccess:true})));await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','q'),poll()));await assertSucceeds(getDoc(doc(as('guest'),'meetingPolls','p')));await assertFails(getDoc(doc(as('guest'),'meetingPolls','q')));await assertFails(getDocs(query(collection(as('guest'),'meetingPolls'),where('body','==','wg4'),where('meetingType','in',['leadership']))));await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(),'meetingPolls','p')));await assertSucceeds(setDoc(doc(as('guest'),'pollResponses','p_guest'),response('guest',{name:'Invited expert'})));await assertFails(setDoc(doc(as('guest'),'pollResponses','q_guest'),response('guest',{pollId:'q',name:'Invited expert'})));await assertFails(setDoc(doc(as('guest'),'pollResponses','p_guest'),response('guest',{name:''})));await assertFails(setDoc(doc(as('outsider'),'pollResponses','p_outsider'),response('outsider',{name:'Someone else'})));await assertSucceeds(setDoc(doc(as('outsider'),'pollResponses','p_outsider'),response('outsider')));await assertSucceeds(getDocs(query(collection(as('guest'),'pollResponses'),where('pollId','==','p'))));await assertFails(getDocs(query(collection(as('guest'),'pollResponses'),where('pollId','==','q'))));await assertFails(setDoc(doc(as('lead4'),'meetingPolls','bad'),poll({linkAccess:'yes'})));await assertFails(updateDoc(doc(as('outsider'),'meetingPolls','p'),{linkAccess:false,updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(as('lead4'),'meetingPolls','p'),{linkAccess:false,updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('guest'),'meetingPolls','p')));await assertFails(setDoc(doc(as('guest'),'pollResponses','p_guest'),response('guest',{name:'Invited expert'})));});
test('proposed times stay stable after votes and malformed schedules are rejected',async()=>{await meetingSetup();for(const extra of [{slots:[]},{slots:[future(7),future(7)]},{slots:Array.from({length:13},(_,i)=>future(i+7))},{slots:[future(1)]},{durationMinutes:0},{mgs:['2.1']},{meetingType:'private'}])await assertFails(setDoc(doc(as('lead4'),'meetingPolls','bad'),poll(extra)));await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','p'),poll()));await assertFails(updateDoc(doc(as('lead4'),'meetingPolls','p'),{slots:[future(10)],updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'meetingPolls','p'),{durationMinutes:90,updatedAt:serverTimestamp()}));});
test('scheduling a poll requires a matching calendar event in the same atomic write',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','p'),poll()));await assertFails(updateDoc(doc(as('lead4'),'meetingPolls','p'),{status:'scheduled',selectedSlot:0,eventId:'missing',updatedAt:serverTimestamp()}));const p=(await getDoc(doc(as('lead4'),'meetingPolls','p'))).data();const batchDb=as('lead4'),batch=writeBatch(batchDb);batch.set(doc(batchDb,'events','meeting'),calendarEvent({owner:'lead4',body:'wg4',meetingType:'leadership',pollId:'p',ocs:[4],mgs:['4.1'],registrationUrl:'',joinUrl:'',startAt:p.slots[0],endAt:Timestamp.fromMillis(p.slots[0].toMillis()+3600000)}));batch.update(doc(batchDb,'meetingPolls','p'),{status:'scheduled',selectedSlot:0,eventId:'meeting',updatedAt:serverTimestamp()});await assertSucceeds(batch.commit());await assertSucceeds(getDoc(doc(as('outsider'),'events','meeting')));});
test('calendar meeting edits require current scoped leadership, not ownership alone',async()=>{await meetingSetup();const e=calendarEvent({owner:'lead4',body:'wg4',meetingType:'core',ocs:[4],mgs:['4.1'],registrationUrl:'',joinUrl:''});await assertSucceeds(setDoc(doc(as('lead4'),'events','meeting'),e));await assertSucceeds(updateDoc(doc(as('associate'),'events','meeting'),{title:'Shared edit',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('core4'),'events','meeting'),{title:'Bad edit',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('associate'),'events','meeting'),{meetingType:'broad',updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(owner(),'governance','wg4'),{lead:'',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'events','meeting'),{title:'Revoked edit',updatedAt:serverTimestamp()}));await assertFails(setDoc(doc(as('broad4'),'events','impersonated'),{...e,owner:'broad4'}));});
const agenda=(uid,extra={})=>({position:1,title:'Review next steps',durationMinutes:15,presenter:'Scientific lead',notes:'Discuss observations.',updatedBy:uid,updatedAt:serverTimestamp(),...extra});
test('private joining details and collaborative agenda respect the meeting category and body',async()=>{await meetingSetup();const e=calendarEvent({owner:'lead4',body:'wg4',meetingType:'core',ocs:[4],mgs:['4.1'],registrationUrl:'',joinUrl:''});const batchDb=as('lead4'),batch=writeBatch(batchDb);batch.set(doc(batchDb,'events','meeting'),e);batch.set(doc(batchDb,'events','meeting','meetingDetails','main'),{registrationUrl:'',joinUrl:'https://example.org/private',updatedAt:serverTimestamp()});await assertSucceeds(batch.commit());await assertSucceeds(getDoc(doc(as('core4'),'events','meeting','meetingDetails','main')));await assertFails(getDoc(doc(as('broad4'),'events','meeting','meetingDetails','main')));await assertSucceeds(setDoc(doc(as('core4'),'events','meeting','agenda','item'),agenda('core4')));await assertFails(setDoc(doc(as('broad4'),'events','meeting','agenda','bad'),agenda('broad4')));await assertFails(setDoc(doc(as('outsider'),'events','meeting','agenda','bad'),agenda('outsider')));await assertFails(setDoc(doc(as('core4'),'events','meeting','meetingDetails','main'),{registrationUrl:'',joinUrl:'https://bad.org',updatedAt:serverTimestamp()}));await assertSucceeds(setDoc(doc(as('lead4'),'events','leadership'),{...e,meetingType:'leadership'}));await assertFails(setDoc(doc(as('core4'),'events','leadership','agenda','item'),agenda('core4')));await assertFails(updateDoc(doc(as('lead4'),'events','meeting'),{joinUrl:'https://example.org/leaked',updatedAt:serverTimestamp()}));});
test('meeting clock starts once and cannot be changed to hide reminders',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(as('lead4'),'meetingClocks','wg4'),{createdAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('lead4'),'meetingClocks','wg4'),{createdAt:serverTimestamp()}));await assertFails(setDoc(doc(as('broad4'),'meetingClocks','wg1'),{createdAt:serverTimestamp()}));await assertFails(deleteDoc(doc(owner(),'meetingClocks','wg4')));});
const logoRequest=(bodies=['WG4'])=>({sub:{title:'Real applicant activity',organisation:'Institute'},assigned:{bodies,due:''},stage:'wg',screen:{},assess:{},decision:{final:'Pending'},history:[]});
const logoOpinion=(uid='lead4',extra={})=>({uid,key:'opinion',ref:'r',body:'WG4',reviewer:'Test member',createdAt:new Date().toISOString(),updatedAt:new Date().toISOString(),status:'draft',opinion:'Concur',text:'Fits the goal.',...extra});
test('logo register is restricted to assigned leadership and applicant contacts to UNESCO Secretariat',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(owner(),'logoRequests','r'),logoRequest()));await assertSucceeds(setDoc(doc(owner(),'logoContacts','r'),{applicant:'Applicant',email:'applicant@example.test'}));for(const u of ['lead4','associate','wgsec'])await assertSucceeds(getDoc(doc(as(u),'logoRequests','r')));for(const u of ['core4','broad4','outsider'])await assertFails(getDoc(doc(as(u),'logoRequests','r')));await assertSucceeds(getDocs(query(collection(as('lead4'),'logoRequests'),where('assigned.bodies','array-contains','WG4'))));await assertFails(getDocs(collection(as('lead4'),'logoRequests')));await assertFails(getDoc(doc(as('wgsec'),'logoContacts','r')));await assertFails(updateDoc(doc(as('wgsec'),'logoRequests','r'),{stage:'decided'}));await assertSucceeds(updateDoc(doc(owner(),'logoRequests','r'),{stage:'decided'}));});
test('logo reviewers can write only their own opinions for an assigned body',async()=>{await meetingSetup();await assertSucceeds(setDoc(doc(owner(),'logoRequests','r'),logoRequest()));await assertSucceeds(setDoc(doc(as('lead4'),'logoReviews','lead4__opinion'),logoOpinion()));await assertFails(setDoc(doc(as('associate'),'logoReviews','lead4__opinion'),logoOpinion()));await assertFails(setDoc(doc(as('core4'),'logoReviews','core4__opinion'),logoOpinion('core4')));await assertFails(setDoc(doc(as('lead4'),'logoReviews','lead4__other'),logoOpinion('lead4',{key:'other',body:'WG1'})));await assertSucceeds(getDocs(query(collection(as('wgsec'),'logoReviews'),where('ref','in',['r']))));await assertFails(getDocs(collection(as('broad4'),'logoReviews')));await assertSucceeds(updateDoc(doc(as('lead4'),'logoReviews','lead4__opinion'),{text:'Updated review',status:'submitted',updatedAt:new Date().toISOString()}));await assertSucceeds(updateDoc(doc(owner(),'logoRequests','r'),{assigned:{bodies:[],due:''}}));await assertFails(updateDoc(doc(as('lead4'),'logoReviews','lead4__opinion'),{text:'Revoked review',updatedAt:new Date().toISOString()}));});
test('logo access follows chairpersons and protected badges and ends on revocation',async()=>{await meetingSetup();await seedMember('chair');await assertSucceeds(setDoc(doc(owner(),'governance','smc'),board({lead:'chair',associateLeads:[],secretariat:[]})));await assertSucceeds(setDoc(doc(owner(),'logoRequests','smc'),logoRequest(['SMC'])));await assertSucceeds(getDoc(doc(as('chair'),'logoRequests','smc')));await assertSucceeds(updateDoc(doc(owner(),'governance','smc'),{lead:'',updatedAt:serverTimestamp()}));await assertFails(getDoc(doc(as('chair'),'logoRequests','smc')));await assertSucceeds(setDoc(doc(owner(),'roles','wgsec'),{admin:false,role:'member',wgs:[],badges:['cfd-secretariat']}));await assertSucceeds(setDoc(doc(owner(),'logoRequests','cfd'),logoRequest(['CFD'])));await assertSucceeds(getDoc(doc(as('wgsec'),'logoRequests','cfd')));});
test('applicant reporting retains code-protected submission and private review',async()=>{await assertSucceeds(setDoc(doc(owner(),'logoReportCodes','r'),{code:'VALID-CODE'}));const report={ref:'r',code:'VALID-CODE',type:'Progress update',name:'Applicant',email:'applicant@example.test',summary:'Activity progress',consent:true,submittedAt:serverTimestamp()};const guest=env.unauthenticatedContext().firestore();await assertFails(setDoc(doc(guest,'logoReports','bad'),{...report,code:'WRONG'}));await assertSucceeds(setDoc(doc(guest,'logoReports','report'),report));await assertFails(getDoc(doc(guest,'logoReports','report')));await assertFails(getDoc(doc(as('wgsec'),'logoReports','report')));await assertSucceeds(getDoc(doc(owner(),'logoReports','report')));});
test('news authors can edit their own posts; others can comment without impersonation',async()=>{await seedMember('alice');await seedMember('bob');const news={author:'alice',author_name:'Test member',wg:0,bodyId:'alliance',title:'Alliance update',body:'New result',url:'https://example.org',createdAt:serverTimestamp(),updatedAt:serverTimestamp()};await assertSucceeds(setDoc(doc(as('alice'),'posts','news'),news));await assertSucceeds(updateDoc(doc(as('alice'),'posts','news'),{title:'Revised update',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('bob'),'posts','news'),{body:'Bad edit',updatedAt:serverTimestamp()}));const comment={author:'bob',author_name:'Test member',body:'Thank you for sharing.',createdAt:serverTimestamp(),updatedAt:serverTimestamp()};await assertSucceeds(setDoc(doc(as('bob'),'posts','news','comments','comment'),comment));await assertFails(setDoc(doc(as('alice'),'posts','news','comments','fake'),comment));await assertSucceeds(updateDoc(doc(as('bob'),'posts','news','comments','comment'),{body:'Revised comment',updatedAt:serverTimestamp()}));await assertFails(updateDoc(doc(as('alice'),'posts','news','comments','comment'),{body:'Bad edit',updatedAt:serverTimestamp()}));await assertSucceeds(updateDoc(doc(owner(),'posts','news','comments','comment'),{body:'Moderated',updatedAt:serverTimestamp()}));await assertFails(setDoc(doc(as('bob'),'posts','missing','comments','comment'),comment));await assertFails(updateDoc(doc(as('alice'),'posts','news'),{url:'javascript:alert(1)',updatedAt:serverTimestamp()}));});

const wideGoals=['1.1','1.2','1.3','2.1','2.2','2.3','3.1','3.2','3.3','4.1','4.2','4.3','5.1','5.2','5.3'];
test('Decade-wide news, activities and events keep all official goals without widening edit rights',async()=>{
 await seedMember('alice');await seedMember('bob');
 const p={author:'alice',author_name:'Test member',wg:0,body:'Decade-wide update',mgs:wideGoals,createdAt:serverTimestamp()};
 await assertSucceeds(setDoc(doc(as('alice'),'posts','wide'),p));
 await assertFails(updateDoc(doc(as('bob'),'posts','wide'),{mgs:['4.1']}));
 for(const mgs of [['6.1'],['1.1','1.1'],[1.1],Array(16).fill('1.1')])await assertFails(updateDoc(doc(as('alice'),'posts','wide'),{mgs}));
 await assertSucceeds(setDoc(doc(as('alice'),'opportunities','wide'),op({mgs:wideGoals})));
 await assertSucceeds(setDoc(doc(as('alice'),'events','wide'),calendarEvent({ocs:[1,2,3,4,5],mgs:wideGoals})));
 await assertFails(updateDoc(doc(as('bob'),'events','wide'),{title:'Other member edit',updatedAt:serverTimestamp()}));
});

const message=(uid,extra={})=>({space:'wg4',parent:'',author:uid,author_name:'Test member',body:'Draft agenda for the next call',mentions:[],deleted:false,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
const mention=(from,extra={})=>({kind:'mention',from,from_name:'Test member',space:'wg4',messageId:'topic',threadId:'topic',excerpt:'Draft agenda',read:false,createdAt:serverTimestamp(),...extra});
test('Working Group discussions are open to members, keep author identity and limit moderation',async()=>{
 await meetingSetup();await seedMember('alice');await seedMember('bob');
 const topic=(db)=>doc(db,'groupDiscussions','wg4','messages','topic');
 await assertFails(setDoc(topic(as('nobody')),message('nobody')));
 await assertFails(setDoc(topic(as('alice')),message('bob')));
 await assertFails(setDoc(topic(as('alice')),message('alice',{author_name:'Someone else'})));
 await assertFails(setDoc(topic(as('alice')),message('alice',{space:'wg3'})));
 await assertFails(setDoc(doc(as('alice'),'groupDiscussions','smc','messages','x'),message('alice',{space:'smc'})));
 await assertFails(setDoc(topic(as('alice')),message('alice',{body:''})));
 await assertFails(setDoc(topic(as('alice')),message('alice',{mentions:['alice']})));
 await assertSucceeds(setDoc(topic(as('alice')),message('alice')));
 await assertFails(getDoc(topic(env.unauthenticatedContext().firestore())));
 await assertSucceeds(getDocs(collection(as('bob'),'groupDiscussions','wg4','messages')));
 await assertFails(setDoc(doc(as('bob'),'groupDiscussions','wg4','messages','r0'),message('bob',{parent:'missing'})));
 await assertSucceeds(setDoc(doc(as('bob'),'groupDiscussions','wg4','messages','reply'),message('bob',{parent:'topic',body:'Thank you'})));
 await assertFails(setDoc(doc(as('alice'),'groupDiscussions','wg4','messages','r2'),message('alice',{parent:'reply'})));
 await assertFails(updateDoc(topic(as('bob')),{body:'Edited by someone else',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(topic(as('alice')),{author_name:'Renamed',updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(topic(as('alice')),{body:'Revised agenda',mentions:['bob'],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(topic(as('core4')),{body:'',mentions:[],deleted:true,updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(topic(as('lead4')),{body:'',mentions:[],deleted:true,updatedAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('bob'),'groupDiscussions','wg4','messages','r3'),message('bob',{parent:'topic'})));
 await assertFails(deleteDoc(doc(as('alice'),'groupDiscussions','wg4','messages','reply')));
 await assertSucceeds(deleteDoc(doc(as('bob'),'groupDiscussions','wg4','messages','reply')));
 await assertSucceeds(deleteDoc(topic(owner())));
});
test('mention notifications reach only tagged people and stay private to the recipient',async()=>{
 await seedMember('alice');await seedMember('bob');await seedMember('carol');
 const db=as('alice');let batch=writeBatch(db);
 batch.set(doc(db,'groupDiscussions','wg4','messages','topic'),message('alice',{mentions:['bob']}));
 batch.set(doc(db,'inbox','bob','items','n1'),mention('alice'));
 await assertSucceeds(batch.commit());
 await assertFails(setDoc(doc(as('alice'),'inbox','carol','items','n2'),mention('alice')));
 await assertFails(setDoc(doc(as('carol'),'inbox','bob','items','n3'),mention('carol')));
 await assertFails(setDoc(doc(as('alice'),'inbox','bob','items','n4'),mention('alice',{from:'carol'})));
 batch=writeBatch(db);
 batch.set(doc(db,'groupDiscussions','wg4','messages','second'),message('alice'));
 batch.set(doc(db,'inbox','bob','items','n5'),mention('alice',{messageId:'second',threadId:'second'}));
 await assertFails(batch.commit());
 await assertSucceeds(getDocs(collection(as('bob'),'inbox','bob','items')));
 await assertFails(getDocs(collection(as('alice'),'inbox','bob','items')));
 await assertFails(updateDoc(doc(as('bob'),'inbox','bob','items','n1'),{excerpt:'Changed'}));
 await assertSucceeds(updateDoc(doc(as('bob'),'inbox','bob','items','n1'),{read:true}));
 await assertFails(deleteDoc(doc(as('alice'),'inbox','bob','items','n1')));
 await assertSucceeds(deleteDoc(doc(as('bob'),'inbox','bob','items','n1')));
});

// ===== Version 3.12 =====
async function seedMeeting(type='core'){await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'events','m'),calendarEvent({owner:'lead4',body:'wg4',meetingType:type,ocs:[4],mgs:['4.1']})));}
const action=(extra={})=>({eventId:'m',body:'wg4',meetingType:'core',title:'Share the draft work plan',owner:'broad4',owner_name:'Test member',due:'2026-11-01',status:'open',createdBy:'core4',createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
test('minutes and actions follow the meeting audience; owners tick only their own action',async()=>{
 await meetingSetup();await seedMeeting('core');
 const minutes={summary:'Agreed the outline.',decisions:'Outline adopted.',updatedBy:'core4',updatedAt:serverTimestamp()};
 await assertSucceeds(setDoc(doc(as('core4'),'events','m','meetingNotes','minutes'),minutes));
 await assertFails(setDoc(doc(as('broad4'),'events','m','meetingNotes','minutes'),{...minutes,updatedBy:'broad4'}));
 await assertFails(setDoc(doc(as('core4'),'events','m','meetingNotes','other'),minutes));
 await assertSucceeds(getDoc(doc(as('associate'),'events','m','meetingNotes','minutes')));
 await assertFails(getDoc(doc(as('broad4'),'events','m','meetingNotes','minutes')));
 await assertSucceeds(setDoc(doc(as('core4'),'actions','a'),action()));
 await assertFails(setDoc(doc(as('core4'),'actions','forged'),action({meetingType:'broad'})));
 await assertFails(setDoc(doc(as('broad4'),'actions','b'),action({createdBy:'broad4'})));
 await assertSucceeds(getDoc(doc(as('broad4'),'actions','a')));
 await assertFails(getDoc(doc(as('outsider'),'actions','a')));
 await assertSucceeds(updateDoc(doc(as('broad4'),'actions','a'),{status:'done',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('broad4'),'actions','a'),{title:'Changed',updatedAt:serverTimestamp()}));
 await assertSucceeds(getDocs(query(collection(as('broad4'),'actions'),where('owner','==','broad4'))));
 await assertSucceeds(getDocs(query(collection(as('core4'),'actions'),where('eventId','==','m'),where('body','==','wg4'),where('meetingType','==','core'))));
 await assertFails(deleteDoc(doc(as('broad4'),'actions','a')));await assertSucceeds(deleteDoc(doc(as('lead4'),'actions','a')));
});
const workItem=(uid,extra={})=>({body:'wg4',kind:'deliverable',title:'Adaptation knowledge hub',mg:'4.3',due:'2027-06-30',status:'planned',lead:'Sara Johansson',notes:'',updatedBy:uid,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
test('work plans are read by members and edited by the group leadership and Core Group',async()=>{
 await meetingSetup();
 await assertSucceeds(setDoc(doc(as('core4'),'workplanItems','w'),workItem('core4')));
 await assertFails(setDoc(doc(as('broad4'),'workplanItems','x'),workItem('broad4')));
 await assertFails(setDoc(doc(as('core4'),'workplanItems','y'),workItem('core4',{mg:'1.1'})));
 await assertFails(setDoc(doc(as('core4'),'workplanItems','z'),workItem('core4',{body:'wg1',mg:'1.1'})));
 await assertSucceeds(getDocs(collection(as('outsider'),'workplanItems')));
 await assertFails(getDocs(collection(env.unauthenticatedContext().firestore(),'workplanItems')));
 await assertSucceeds(updateDoc(doc(as('lead4'),'workplanItems','w'),{status:'in-progress',updatedBy:'lead4',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('core4'),'workplanItems','w'),{body:'wg1',updatedBy:'core4',updatedAt:serverTimestamp()}));
});
const decision=(uid,extra={})=>({body:'smc',date:'2026-10-01',reference:'SMC/2026/03',title:'Work plans adopted',text:'The SMC adopted the work plans.',eventId:'',visibility:'body',createdBy:uid,createdAt:serverTimestamp(),updatedBy:uid,updatedAt:serverTimestamp(),...extra});
test('the decision register is written by SMC or ESC leadership and read by members of the body',async()=>{
 for(const u of ['chair','smcmember','other'])await seedMember(u);
 await assertSucceeds(setDoc(doc(owner(),'governance','smc'),board({title:'SMC',lead:'chair',core:['smcmember']})));
 await assertSucceeds(setDoc(doc(as('chair'),'decisions','d'),decision('chair')));
 await assertSucceeds(setDoc(doc(as('chair'),'decisions','public'),decision('chair',{visibility:'community'})));
 await assertFails(setDoc(doc(as('smcmember'),'decisions','x'),decision('smcmember')));
 await assertFails(setDoc(doc(as('chair'),'decisions','esc'),decision('chair',{body:'esc'})));
 await assertSucceeds(getDoc(doc(as('smcmember'),'decisions','d')));
 await assertFails(getDoc(doc(as('other'),'decisions','d')));
 await assertSucceeds(getDoc(doc(as('other'),'decisions','public')));
 await assertSucceeds(getDocs(query(collection(as('other'),'decisions'),where('body','==','smc'),where('visibility','==','community'))));
 await assertFails(getDocs(query(collection(as('other'),'decisions'),where('body','==','smc'))));
});
const consultation=(extra={})=>({owner:'lead4',body:'wg4',audience:'broad',title:'Approve the work plan',description:'',questions:[{id:'q1',kind:'yesno',label:'Approve?',options:[]}],deadline:future(5),status:'open',resultsVisible:false,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),...extra});
test('consultations: leadership creates, the audience answers under its own name, results stay with organisers until shared',async()=>{
 await meetingSetup();
 await assertSucceeds(setDoc(doc(as('lead4'),'consultations','c'),consultation()));
 await assertFails(setDoc(doc(as('core4'),'consultations','x'),consultation({owner:'core4'})));
 await assertSucceeds(getDoc(doc(as('broad4'),'consultations','c')));
 await assertFails(getDoc(doc(as('outsider'),'consultations','c')));
 const answer={name:'Test member',answers:{q1:'Yes'},updatedAt:serverTimestamp()};
 await assertSucceeds(setDoc(doc(as('broad4'),'consultations','c','answers','broad4'),answer));
 await assertFails(setDoc(doc(as('broad4'),'consultations','c','answers','core4'),answer));
 await assertFails(setDoc(doc(as('outsider'),'consultations','c','answers','outsider'),answer));
 await assertFails(setDoc(doc(as('core4'),'consultations','c','answers','core4'),{...answer,name:'Someone else'}));
 await assertFails(getDocs(collection(as('core4'),'consultations','c','answers')));
 await assertSucceeds(getDocs(collection(as('lead4'),'consultations','c','answers')));
 await assertSucceeds(updateDoc(doc(as('lead4'),'consultations','c'),{resultsVisible:true,updatedAt:serverTimestamp()}));
 await assertSucceeds(getDocs(collection(as('core4'),'consultations','c','answers')));
 await assertFails(updateDoc(doc(as('lead4'),'consultations','c'),{questions:[],updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('lead4'),'consultations','c'),{status:'closed',updatedAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('core4'),'consultations','c','answers','core4'),answer));
});

test('public events: organiser writes minutes and actions, every member reads them',async()=>{
 await seedMember('alice');await seedMember('bob');
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'events','pub'),calendarEvent({owner:'alice'})));
 const minutes={summary:'Webinar held.',decisions:'',updatedBy:'alice',updatedAt:serverTimestamp()};
 await assertSucceeds(setDoc(doc(as('alice'),'events','pub','meetingNotes','minutes'),minutes));
 await assertFails(setDoc(doc(as('bob'),'events','pub','meetingNotes','minutes'),{...minutes,updatedBy:'bob'}));
 await assertSucceeds(getDoc(doc(as('bob'),'events','pub','meetingNotes','minutes')));
 const act={eventId:'pub',body:'',meetingType:'public',title:'Share the recording',owner:'bob',owner_name:'Test member',due:'',status:'open',createdBy:'alice',createdAt:serverTimestamp(),updatedAt:serverTimestamp()};
 await assertSucceeds(setDoc(doc(as('alice'),'actions','pa'),act));
 await assertFails(setDoc(doc(as('bob'),'actions','pb'),{...act,createdBy:'bob'}));
 await assertSucceeds(getDocs(query(collection(as('bob'),'actions'),where('eventId','==','pub'),where('body','==',''),where('meetingType','==','public'))));
 await assertSucceeds(updateDoc(doc(as('bob'),'actions','pa'),{status:'done',updatedAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(owner(),'events','pub','meetingNotes','minutes'),{...minutes,updatedBy:'alexandre'}));
});
test('membership totals are published by the Secretariat and read by members',async()=>{
 await seedMember('alice');
 const stats={total:3,gender:{Woman:2,Man:1},careerStage:{'Mid-career professional':3},updatedAt:serverTimestamp()};
 await assertFails(setDoc(doc(as('alice'),'communityStats','members'),stats));
 await assertSucceeds(setDoc(doc(owner(),'communityStats','members'),stats));
 await assertFails(setDoc(doc(owner(),'communityStats','other'),stats));
 await assertSucceeds(getDoc(doc(as('alice'),'communityStats','members')));
 await assertFails(getDoc(doc(as('nobody'),'communityStats','members')));
});

const entry=(uid,tier,extra={})=>({name:'Member '+uid,email:uid+'@example.test',tier,updatedAt:serverTimestamp(),...extra});
test('mailing lists: members add only their own email at a tier they hold; only the leadership reads their body',async()=>{
 await assertSucceeds(setDoc(doc(owner(),'governance','wg4'),board({lead:'lead4',core:['core4']})));
 for(const uid of ['alice','lead4','core4','bob'])await seedMember(uid);
 // alice selected WG4 in her profile (wgs:[4]) but has no Broad Group badge: she is not on the Broad Group list.
 await assertFails(setDoc(doc(as('alice'),'mailingLists','wg4','entries','alice'),entry('alice','broad')));
 // Once the UNESCO Secretariat gives her the WG4 Broad Group badge, she can add her own email; never another tier or address.
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg4-member']}));
 await assertSucceeds(setDoc(doc(as('alice'),'mailingLists','wg4','entries','alice'),entry('alice','broad')));
 await assertFails(setDoc(doc(as('alice'),'mailingLists','wg4','entries','alice'),entry('alice','leadership')));
 await assertFails(setDoc(doc(as('alice'),'mailingLists','wg4','entries','alice'),entry('alice','broad',{email:'someone@else.test'})));
 await assertFails(setDoc(doc(as('alice'),'mailingLists','wg4','entries','bob'),entry('bob','broad')));
 await assertFails(setDoc(doc(as('alice'),'mailingLists','wg1','entries','alice'),entry('alice','broad')));
 await assertSucceeds(setDoc(doc(as('lead4'),'mailingLists','wg4','entries','lead4'),entry('lead4','leadership')));
 await assertSucceeds(setDoc(doc(as('core4'),'mailingLists','wg4','entries','core4'),entry('core4','core')));
 await assertSucceeds(setDoc(doc(as('alice'),'mailingLists','decade','entries','alice'),entry('alice','member')));
 await assertFails(setDoc(doc(as('alice'),'mailingLists','decade','entries','alice'),entry('alice','broad')));
 // Reading
 const list=await assertSucceeds(getDocs(collection(as('lead4'),'mailingLists','wg4','entries')));assert.equal(list.size,3);
 await assertFails(getDocs(collection(as('core4'),'mailingLists','wg4','entries')));
 await assertSucceeds(getDoc(doc(as('core4'),'mailingLists','wg4','entries','core4')));
 await assertFails(getDocs(collection(as('alice'),'mailingLists','wg4','entries')));
 await assertSucceeds(getDoc(doc(as('alice'),'mailingLists','wg4','entries','alice')));
 await assertFails(getDocs(collection(as('lead4'),'mailingLists','decade','entries')));
 await assertSucceeds(getDocs(collection(owner(),'mailingLists','decade','entries')));
 await assertSucceeds(deleteDoc(doc(as('alice'),'mailingLists','wg4','entries','alice')));
 await assertFails(deleteDoc(doc(as('alice'),'mailingLists','wg4','entries','lead4')));
});
const declaration=(extra={})=>({name:'Test member',claims:{wg4:'lead',smc:'apply'},note:'',decisions:{},status:'pending',updatedAt:serverTimestamp(),...extra});
test('declared roles: members declare and edit their own, only the Secretariat decides',async()=>{
 await seedMember('alice');
 await assertSucceeds(setDoc(doc(as('alice'),'roleRequests','alice'),declaration()));
 await assertFails(setDoc(doc(as('alice'),'roleRequests','bob'),declaration()));
 await assertFails(setDoc(doc(as('bob'),'roleRequests','bob'),declaration({decisions:{wg4:'lead'}})));
 await assertFails(setDoc(doc(as('bob'),'roleRequests','bob'),declaration({claims:{wg9:'lead'}})));
 await assertFails(setDoc(doc(as('bob'),'roleRequests','bob'),declaration({claims:{wg4:'boss'}})));
 await assertFails(getDoc(doc(as('bob'),'roleRequests','alice')));
 await assertSucceeds(getDocs(query(collection(owner(),'roleRequests'),where('status','==','pending'))));
 await assertFails(getDocs(query(collection(as('bob'),'roleRequests'),where('status','==','pending'))));
 await assertSucceeds(setDoc(doc(owner(),'roleRequests','alice'),declaration({decisions:{wg4:'associate',smc:'declined'},status:'reviewed',reviewedAt:serverTimestamp()})));
 // The member cannot mark the request reviewed or forge decisions, but can change a role (which clears the decisions).
 await assertFails(updateDoc(doc(as('alice'),'roleRequests','alice'),{status:'reviewed',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('alice'),'roleRequests','alice'),{status:'pending',decisions:{wg4:'lead',smc:'declined'},updatedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('alice'),'roleRequests','alice'),{claims:{wg4:'core'},decisions:{},status:'pending',updatedAt:serverTimestamp()}));
 await assertSucceeds(deleteDoc(doc(as('alice'),'roleRequests','alice')));
});

const chatDoc=(a,b,names,extra={})=>({members:[a,b].sort(),names,createdAt:serverTimestamp(),updatedAt:serverTimestamp(),lastMessage:{text:'Hello',from:extra.from||a,at:serverTimestamp()},lastRead:{[extra.from||a]:serverTimestamp()},...extra.fields});
test('private messages: only the two members read and write; the owner and appointed moderators read and moderate',async()=>{
 for(const uid of ['alice','bob','carol','dave'])await seedMember(uid);
 const id='alice_bob',names={alice:'Test member',bob:'Test member'};
 const db=as('alice');const batch=writeBatch(db);
 batch.set(doc(db,'chats',id),chatDoc('alice','bob',names));
 batch.set(doc(db,'chats',id,'messages','m1'),{from:'alice',text:'Hello',createdAt:serverTimestamp()});
 await assertSucceeds(batch.commit());
 await assertFails(setDoc(doc(as('carol'),'chats','alice_bob2'),chatDoc('alice','bob',names)));
 await assertFails(setDoc(doc(as('carol'),'chats',id,'messages','m2'),{from:'carol',text:'Hi',createdAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('bob'),'chats',id,'messages','m3'),{from:'alice',text:'Forged',createdAt:serverTimestamp()}));
 await assertSucceeds(getDoc(doc(as('bob'),'chats',id)));
 await assertSucceeds(getDocs(query(collection(as('bob'),'chats'),where('members','array-contains','bob'))));
 await assertSucceeds(getDocs(collection(as('bob'),'chats',id,'messages')));
 await assertFails(getDoc(doc(as('carol'),'chats',id)));
 await assertFails(getDocs(collection(as('carol'),'chats',id,'messages')));
 await assertSucceeds(updateDoc(doc(as('bob'),'chats',id),{'lastRead.bob':serverTimestamp()}));
 await assertFails(updateDoc(doc(as('bob'),'chats',id),{'lastRead.alice':serverTimestamp()}));
 await assertFails(updateDoc(doc(as('bob'),'chats',id,'messages','m1'),{text:'Edited'}));
 // Moderators: the owner account, and members it appoints.
 await assertSucceeds(getDocs(collection(owner(),'chats')));
 await assertFails(getDocs(collection(as('secretariat'),'chats')));
 await assertFails(setDoc(doc(as('secretariat'),'config','chatMonitors'),{uids:['carol'],updatedAt:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(owner(),'config','chatMonitors'),{uids:['carol'],updatedAt:serverTimestamp()}));
 await assertSucceeds(getDocs(collection(as('carol'),'chats',id,'messages')));
 await assertSucceeds(updateDoc(doc(as('carol'),'chats',id,'messages','m1'),{text:'',removed:true,removedBy:'carol'}));
 await assertFails(deleteDoc(doc(as('carol'),'chats',id,'messages','m1')));
 // Reports
 await assertSucceeds(setDoc(doc(as('bob'),'chatReports','r1'),{chatId:id,messageId:'m1',reporter:'bob',reporterName:'Test member',reason:'Spam',status:'open',createdAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('dave'),'chatReports','r2'),{chatId:id,messageId:'',reporter:'dave',reporterName:'Test member',reason:'Not my conversation',status:'open',createdAt:serverTimestamp()}));
 await assertSucceeds(getDoc(doc(as('bob'),'chatReports','r1')));
 await assertFails(getDoc(doc(as('alice'),'chatReports','r1')));
 await assertSucceeds(getDocs(collection(as('carol'),'chatReports')));
 await assertFails(updateDoc(doc(as('bob'),'chatReports','r1'),{status:'resolved',resolution:'',resolvedBy:'bob',resolvedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('carol'),'chatReports','r1'),{status:'resolved',resolution:'Warned the member',resolvedBy:'carol',resolvedAt:serverTimestamp()}));
});
test('shared files: leadership of a body and the Secretariat upload; members read; meeting files follow the audience',async()=>{
 await assertSucceeds(setDoc(doc(owner(),'governance','wg4'),board({lead:'lead4'})));
 for(const uid of ['alice','lead4'])await seedMember(uid);
 const meta=(extra={})=>({name:'Agenda.pdf',type:'pdf',size:1000,chunks:1,body:'wg4',audience:'all',uploadedBy:'lead4',createdAt:serverTimestamp(),...extra});
 await assertSucceeds(setDoc(doc(as('lead4'),'files','f1'),meta()));
 await assertSucceeds(setDoc(doc(as('lead4'),'files','f1','chunks','0'),{data:'JVBERi0xLjEK'}));
 await assertFails(setDoc(doc(as('lead4'),'files','f1','chunks','1'),{data:'AAAA'}));
 await assertFails(setDoc(doc(as('alice'),'files','f2'),meta({uploadedBy:'alice'})));
 await assertFails(setDoc(doc(as('lead4'),'files','f3'),meta({type:'exe'})));
 await assertFails(setDoc(doc(as('lead4'),'files','f4'),meta({body:'wg1'})));
 await assertSucceeds(getDoc(doc(as('alice'),'files','f1','chunks','0')));
 await assertSucceeds(setDoc(doc(as('lead4'),'files','f5'),meta({audience:'leadership'})));
 await assertSucceeds(setDoc(doc(as('lead4'),'files','f5','chunks','0'),{data:'AAAA'}));
 await assertFails(getDoc(doc(as('alice'),'files','f5','chunks','0')));
 await assertSucceeds(getDoc(doc(as('lead4'),'files','f5','chunks','0')));
 // Attachments on content: only the leadership of the named body or the Secretariat.
 const att={id:'f1',name:'Agenda.pdf',type:'pdf',size:1000,body:'wg4'};
 await assertSucceeds(setDoc(doc(as('lead4'),'posts','p1'),{author:'lead4',author_name:'Test member',wg:4,body:'News',createdAt:serverTimestamp(),attachments:[att]}));
 await assertFails(setDoc(doc(as('alice'),'posts','p2'),{author:'alice',author_name:'Test member',wg:4,body:'News',createdAt:serverTimestamp(),attachments:[att]}));
 await assertSucceeds(updateDoc(doc(as('lead4'),'posts','p1'),{body:'Edited news',updatedAt:serverTimestamp()}));
});
test('the welcome video flag is stored with the member preferences',async()=>{
 await assertSucceeds(setDoc(doc(as('alice'),'preferences','alice'),{wgs:[4],welcomeSeen:true}));
 await assertFails(setDoc(doc(as('alice'),'preferences','alice'),{wgs:[4],welcomeSeen:'yes'}));
});
test('group conversations: the creator manages members, members write and leave, outsiders cannot read',async()=>{
 for(const uid of ['alice','bob','carol','dave'])await seedMember(uid);
 const group=(extra={})=>({kind:'group',title:'Team',createdBy:'alice',members:['alice','bob','carol'],names:{alice:'A',bob:'B',carol:'C'},createdAt:serverTimestamp(),updatedAt:serverTimestamp(),lastMessage:{text:'',from:'alice',at:serverTimestamp()},lastRead:{alice:serverTimestamp()},...extra});
 await assertFails(setDoc(doc(as('alice'),'chats','g0'),group({members:['alice','bob'],names:{alice:'A',bob:'B'}})));
 await assertFails(setDoc(doc(as('alice'),'chats','gx'),group({createdBy:'bob'})));
 await assertSucceeds(setDoc(doc(as('alice'),'chats','g1'),group()));
 await assertSucceeds(setDoc(doc(as('carol'),'chats','g1','messages','m1'),{from:'carol',text:'Hi all',createdAt:serverTimestamp()}));
 await assertFails(getDocs(collection(as('dave'),'chats','g1','messages')));
 await assertFails(updateDoc(doc(as('bob'),'chats','g1'),{members:['alice','bob','carol','dave'],names:{alice:'A',bob:'B',carol:'C',dave:'D'},title:'Team'}));
 await assertSucceeds(updateDoc(doc(as('alice'),'chats','g1'),{members:['alice','bob','carol','dave'],names:{alice:'A',bob:'B',carol:'C',dave:'D'},title:'Team plus'}));
 await assertSucceeds(getDocs(collection(as('dave'),'chats','g1','messages')));
 await assertSucceeds(updateDoc(doc(as('bob'),'chats','g1'),{members:['alice','carol','dave'],names:{alice:'A',carol:'C',dave:'D'}}));
 await assertFails(updateDoc(doc(as('carol'),'chats','g1'),{members:['alice','carol'],names:{alice:'A',carol:'C'}}));
});
test('gender and feeling about the Decade appear on a profile only when the member chooses to show them',async()=>{
 await assertSucceeds(setDoc(doc(as('alice'),'profiles','alice'),profile({showBackground:true,publicGender:'Woman',publicSentiment:'Enthusiastic and ready to contribute'})));
 await assertFails(setDoc(doc(as('bob'),'profiles','bob'),profile({showBackground:false,publicGender:'Man'})));
});
test('banned members lose access; only the UNESCO Secretariat bans and unbans',async()=>{
 for(const uid of ['alice','bob'])await seedMember(uid);
 const names={alice:'Test member',bob:'Test member'};
 await assertFails(setDoc(doc(as('bob'),'bans','alice'),{by:'bob',at:serverTimestamp()}));
 await assertSucceeds(setDoc(doc(owner(),'bans','alice'),{by:'alexandre',at:serverTimestamp()}));
 const db=as('alice');const batch=writeBatch(db);
 batch.set(doc(db,'chats','alice_bob'),chatDoc('alice','bob',names));
 batch.set(doc(db,'chats','alice_bob','messages','m1'),{from:'alice',text:'Hello',createdAt:serverTimestamp()});
 await assertFails(batch.commit());
 await assertFails(setDoc(doc(as('alice'),'posts','p'),{author:'alice',author_name:'Test member',wg:4,body:'News',createdAt:serverTimestamp()}));
 await assertSucceeds(getDoc(doc(as('bob'),'bans','alice')));
 await assertSucceeds(deleteDoc(doc(owner(),'bans','alice')));
 const db2=as('alice');const b2=writeBatch(db2);
 b2.set(doc(db2,'chats','alice_bob'),chatDoc('alice','bob',names));
 b2.set(doc(db2,'chats','alice_bob','messages','m1'),{from:'alice',text:'Hello',createdAt:serverTimestamp()});
 await assertSucceeds(b2.commit());
});

test('task boards: the Core Group writes, assignees read and move their own tasks, others are kept out',async()=>{
 for(const u of ['lead4','core4','alice','outsider']) await seedMember(u);
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'governance','wg4'),board({lead:'lead4',core:['core4']})));
 const task=(extra={})=>({body:'wg4',title:'Draft the agenda',notes:'',status:'todo',priority:'normal',assignees:['alice'],seenBy:[],due:'2026-11-02',createdBy:'core4',createdAt:serverTimestamp(),updatedBy:'core4',updatedAt:serverTimestamp(),...extra});
 await assertSucceeds(setDoc(doc(as('core4'),'tasks','t1'),task()));
 await assertFails(setDoc(doc(as('alice'),'tasks','t2'),task({createdBy:'alice',updatedBy:'alice'})));
 await assertSucceeds(getDocs(query(collection(as('lead4'),'tasks'),where('body','==','wg4'))));
 await assertFails(getDocs(query(collection(as('outsider'),'tasks'),where('body','==','wg4'))));
 await assertSucceeds(getDocs(query(collection(as('alice'),'tasks'),where('assignees','array-contains','alice'))));
 await assertSucceeds(updateDoc(doc(as('alice'),'tasks','t1'),{status:'doing',seenBy:['alice'],updatedBy:'alice',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('alice'),'tasks','t1'),{title:'Changed',updatedBy:'alice',updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('alice'),'tasks','t1'),{assignees:['alice','outsider'],updatedBy:'alice',updatedAt:serverTimestamp()}));
 await assertFails(deleteDoc(doc(as('alice'),'tasks','t1')));
 await assertSucceeds(deleteDoc(doc(as('lead4'),'tasks','t1')));
});

test('event sign-ups: members record their own attendance under their profile name until the event ends',async()=>{
 await seedMember('alice');await seedMember('bob');
 const later=(h)=>Timestamp.fromDate(new Date(Date.now()+h*3600000));
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'events','ev'),calendarEvent({startAt:later(24),endAt:later(25)})));
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'events','old'),calendarEvent()));
 await assertSucceeds(setDoc(doc(as('alice'),'events','ev','attendance','alice'),{name:'Test member',mode:'in-person',at:serverTimestamp()}));
 await assertFails(setDoc(doc(as('alice'),'events','ev','attendance','bob'),{name:'Test member',mode:'online',at:serverTimestamp()}));
 await assertFails(setDoc(doc(as('bob'),'events','ev','attendance','bob'),{name:'Someone else',mode:'online',at:serverTimestamp()}));
 await assertFails(setDoc(doc(as('bob'),'events','old','attendance','bob'),{name:'Test member',mode:'online',at:serverTimestamp()}));
 await assertSucceeds(getDocs(collection(as('bob'),'events','ev','attendance')));
 await assertFails(deleteDoc(doc(as('bob'),'events','ev','attendance','alice')));
 await assertSucceeds(deleteDoc(doc(as('alice'),'events','ev','attendance','alice')));
});

test('organisers edit an open poll: new times are appended, earlier ones are withdrawn, never replaced',async()=>{
 await meetingSetup();await assertSucceeds(setDoc(doc(as('lead4'),'meetingPolls','p'),poll()));
 const ref=doc(as('lead4'),'meetingPolls','p'),current=(await getDoc(ref)).data();
 await assertSucceeds(updateDoc(ref,{title:'WG4 coordination, November',notes:'Agenda to follow.',slots:[...current.slots,future(9)],withdrawn:[0],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(ref,{slots:[future(9)],withdrawn:[],updatedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('broad4'),'meetingPolls','p'),{title:'Hijacked',updatedAt:serverTimestamp()}));
});

test('flagship projects: milestones name their project, and activities can be linked by the group managers',async()=>{
 await meetingSetup();
 await assertSucceeds(setDoc(doc(as('core4'),'workplanItems','p'),workItem('core4')));
 await assertSucceeds(setDoc(doc(as('core4'),'workplanItems','m'),workItem('core4',{kind:'milestone',title:'Prototype online',parent:'p'})));
 await assertFails(setDoc(doc(as('core4'),'workplanItems','n'),workItem('core4',{kind:'milestone',parent:'x'.repeat(129)})));
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'opportunities','o'),op({owner:'broad4',status:'open'})));
 await seedRole('lead4','lead',[4]);
 await assertSucceeds(updateDoc(doc(as('lead4'),'opportunities','o'),{project:'p'}));
 await assertFails(updateDoc(doc(as('broad4'),'opportunities','o'),{project:''}));
 await assertSucceeds(setDoc(doc(as('broad4'),'opportunities','o2'),op({owner:'broad4',status:'pending',project:'p'})));
});

test('activities: the person who proposed one edits or deletes it; the Working Group and status stay with the managers',async()=>{
 await seedMember('alice');await seedMember('bob');
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'opportunities','a'),op({owner:'alice',status:'open'})));
 await assertSucceeds(updateDoc(doc(as('alice'),'opportunities','a'),{title:'Review adaptation evidence, second round',description:'Updated scope.'}));
 await assertFails(updateDoc(doc(as('alice'),'opportunities','a'),{status:'closed'}));
 await assertFails(updateDoc(doc(as('alice'),'opportunities','a'),{wg:1,mgs:['1.1']}));
 await assertFails(updateDoc(doc(as('bob'),'opportunities','a'),{title:'Not mine'}));
 await assertFails(deleteDoc(doc(as('bob'),'opportunities','a')));
 await assertSucceeds(deleteDoc(doc(as('alice'),'opportunities','a')));
});

test('Broad Group applications: members apply once, the leadership of the group or the Secretariat decides, and approval adds only that badge',async()=>{
 await seedMember('alice');await seedMember('bob');await seedMember('lead1');await seedMember('lead4');await seedRole('lead1','lead',[1]);await seedRole('lead4','lead',[4]);
 const app={uid:'alice',name:'Test member',body:'wg1',status:'pending',createdAt:serverTimestamp(),decidedBy:'',decidedAt:null};
 // Before applying, the app looks up the member's own application, which does not exist yet.
 await assertSucceeds(getDoc(doc(as('alice'),'groupApplications','wg1_alice')));
 await assertFails(getDoc(doc(as('alice'),'groupApplications','wg1_bob')));
 await assertFails(setDoc(doc(as('alice'),'groupApplications','wg1_bob'),app));
 await assertFails(setDoc(doc(as('alice'),'groupApplications','wg1_alice'),{...app,status:'approved'}));
 await assertFails(setDoc(doc(as('alice'),'groupApplications','wg1_alice'),{...app,name:'Someone else'}));
 await assertSucceeds(setDoc(doc(as('alice'),'groupApplications','wg1_alice'),app));
 await assertSucceeds(getDoc(doc(as('alice'),'groupApplications','wg1_alice')));
 await assertFails(getDoc(doc(as('bob'),'groupApplications','wg1_alice')));
 await assertFails(getDoc(doc(as('lead4'),'groupApplications','wg1_alice')));
 await assertSucceeds(getDocs(query(collection(as('lead1'),'groupApplications'),where('body','==','wg1'))));
 await assertFails(getDocs(query(collection(as('lead4'),'groupApplications'),where('body','==','wg1'))));
 await assertSucceeds(getDocs(query(collection(as('secretariat'),'groupApplications'),where('status','==','pending'))));
 // The member cannot decide; another group's lead cannot decide or give the badge.
 await assertFails(updateDoc(doc(as('alice'),'groupApplications','wg1_alice'),{status:'approved',decidedBy:'alice',decidedAt:serverTimestamp()}));
 await assertFails(updateDoc(doc(as('lead4'),'groupApplications','wg1_alice'),{status:'approved',decidedBy:'lead4',decidedAt:serverTimestamp()}));
 await assertFails(setDoc(doc(as('lead4'),'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg1-member']}));
 // The WG1 lead approves: creates the role with the WG1 Broad Group badge only.
 await assertFails(setDoc(doc(as('lead1'),'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg1-core']}));
 await assertFails(setDoc(doc(as('lead1'),'roles','alice'),{admin:false,role:'core',wgs:[],badges:['wg1-member']}));
 const db=as('lead1'),batch=writeBatch(db);
 batch.set(doc(db,'roles','alice'),{admin:false,role:'member',wgs:[],badges:['wg1-member']});
 batch.update(doc(db,'groupApplications','wg1_alice'),{status:'approved',decidedBy:'lead1',decidedAt:serverTimestamp()});
 await assertSucceeds(batch.commit());
 // Leaders change only the Broad Group badge of their own group on an existing role.
 await env.withSecurityRulesDisabled(c=>setDoc(doc(c.firestore(),'roles','bob'),{admin:false,role:'member',wgs:[],badges:['wg4-member']}));
 await assertSucceeds(updateDoc(doc(as('lead1'),'roles','bob'),{badges:['wg4-member','wg1-member']}));
 await assertFails(updateDoc(doc(as('lead1'),'roles','bob'),{badges:['wg1-member']}));
 await assertFails(updateDoc(doc(as('lead1'),'roles','bob'),{badges:['wg4-member','wg1-member','wg1-lead']}));
 await assertFails(updateDoc(doc(as('lead1'),'roles','bob'),{role:'core'}));
 // A declined member may apply again; a pending application cannot be reset by its author.
 await assertSucceeds(setDoc(doc(as('bob'),'groupApplications','wg3_bob'),{...app,uid:'bob',body:'wg3'}));
 await assertFails(updateDoc(doc(as('bob'),'groupApplications','wg3_bob'),{name:'Test member',status:'pending',createdAt:serverTimestamp(),decidedBy:'',decidedAt:null}));
 await assertSucceeds(updateDoc(doc(as('secretariat'),'groupApplications','wg3_bob'),{status:'declined',decidedBy:'secretariat',decidedAt:serverTimestamp()}));
 await assertSucceeds(updateDoc(doc(as('bob'),'groupApplications','wg3_bob'),{name:'Test member',status:'pending',createdAt:serverTimestamp(),decidedBy:'',decidedAt:null}));
});

test('logo review: access is granted member by member by the Secretariat, never by an appointment',async()=>{
 await seedMember('alice');await seedMember('lead1');await seedRole('lead1','lead',[1]);
 await env.withSecurityRulesDisabled(async c=>{const f=c.firestore();
  await setDoc(doc(f,'logoRequests','R1'),{assigned:{bodies:['WG1'],due:''},stage:'wg'});
  await setDoc(doc(f,'logoRequests','R2'),{assigned:{bodies:['SMC'],due:''},stage:'wg'});});
 // The lead of WG1 has no logo review access until the Secretariat grants it.
 await assertFails(getDoc(doc(as('lead1'),'logoRequests','R1')));
 // Members cannot grant it to themselves; the Secretariat can, for WG1 to WG5, SMC and ESC only.
 await assertFails(setDoc(doc(as('alice'),'roles','alice'),{admin:false,role:'member',wgs:[],logoReview:['wg1']}));
 await assertFails(setDoc(doc(owner(),'roles','alice'),{admin:false,role:'member',wgs:[],logoReview:['cfd']}));
 await assertSucceeds(setDoc(doc(owner(),'roles','alice'),{admin:false,role:'member',wgs:[],badges:[],logoReview:['wg1','smc']}));
 await assertSucceeds(getDoc(doc(as('alice'),'logoRequests','R1')));
 await assertSucceeds(getDoc(doc(as('alice'),'logoRequests','R2')));
 await assertSucceeds(getDocs(query(collection(as('alice'),'logoRequests'),where('assigned.bodies','array-contains','WG1'))));
 const op={uid:'alice',key:'R1__WG1',ref:'R1',body:'WG1',reviewer:'Test member',createdAt:'2026-10-20',updatedAt:'2026-10-20',opinion:'Favourable'};
 await assertSucceeds(setDoc(doc(as('alice'),'logoReviews','alice__R1__WG1'),op));
 await assertFails(setDoc(doc(as('alice'),'logoReviews','alice__R2__WG2'),{...op,key:'R2__WG2',ref:'R2',body:'WG2'}));
 // Leaders who change a Broad Group badge keep the member's logo review access.
 await assertSucceeds(updateDoc(doc(as('lead1'),'roles','alice'),{badges:['wg1-member']}));
 await assertFails(updateDoc(doc(as('lead1'),'roles','alice'),{logoReview:['wg1','wg2']}));
});
