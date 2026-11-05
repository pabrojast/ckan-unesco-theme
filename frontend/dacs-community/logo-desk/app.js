// Frame guard: GitHub Pages cannot send X-Frame-Options, so refuse to run inside a frame from another origin.
(()=>{let foreign=false;try{foreign=window.top!==window.self&&window.top.location.origin!==location.origin;}catch{foreign=true;}if(foreign){document.documentElement.style.display='none';throw new Error('The logo desk cannot be embedded by another site.');}})();
/* DACS Logo Authorisation Platform - Firebase edition (free Spark plan).
   Firebase Authentication (email and password) and Cloud Firestore (live data).
   Each person's role is the document accounts/{uid}; firestore.rules reads it on every request,
   and only the Secretariat can write it. No Cloud Functions are needed. */
import {onAuthStateChanged,signOut} from 'firebase/auth';
import {collection,doc,setDoc,getDoc,deleteDoc,onSnapshot,query,where,limit} from 'firebase/firestore';
import {auth,db as fs,configured} from '../lib/firebase';
import {logoBodies,meetingBodies} from '../lib/meetings';
import {decadeGoals} from '../lib/decade-goals';
import {isUnescoSecretariat} from '../lib/member-roles';
const pathMap={requests:'logoRequests',contacts:'logoContacts',reports:'logoReports',reportCodes:'logoReportCodes',reportFiles:'logoReportFiles'};
const hubPath=p=>{const [first,...parts]=p.split('/');return [pathMap[first]||first,...parts].join('/');};
function reviewDoc(uid,key){return doc(fs,'logoReviews',uid+'__'+key);}
async function writeReviews(uid,d,merge=false){
 const before=(S.reviews.get(uid)||{}).opinions||{},incoming=d.opinions||{};
 for(const [key,o] of Object.entries(incoming))if(JSON.stringify(before[key])!==JSON.stringify(o))await setDoc(reviewDoc(uid,key),{...o,uid,key});
 if(!merge)for(const key of Object.keys(before))if(!(key in incoming))await deleteDoc(reviewDoc(uid,key));
}
/* A small adapter so the rest of the app reads like a document store: update() merges nested maps. */
const wrapDoc = (s) => ({ id: s.id, exists: s.exists(), data: () => s.data() });
const DB = {
  doc: (p) => { if(p.startsWith('reviews/')){const uid=p.slice(8);return {set:d=>writeReviews(uid,d),update:d=>writeReviews(uid,d,true),delete:()=>Promise.reject(new Error('Remove individual reviews.'))};}
    const ref = doc(fs, hubPath(p)); return {
    set: (d) => setDoc(ref, d), update: (d) => setDoc(ref, d, { merge: true }), delete: () => deleteDoc(ref), get: () => getDoc(ref).then(wrapDoc),
    onSnapshot: (n, e) => onSnapshot(ref, (s) => n(wrapDoc(s)), e) }; },
  collection: (p, ...w) => ({ onSnapshot: (n, e) => onSnapshot(w.length ? query(collection(fs, hubPath(p)), ...w,limit(500)) : query(collection(fs, hubPath(p)),limit(500)),
    (s) => n({ docs: s.docs.map((d) => ({ id: d.id, exists: true, data: () => d.data() })) }), e) })
};

/* ---------------- reference: methodology (draft, September 2026) and register "Reference" sheet ---------------- */
const CFG={
  wgs:{WG1:"Global Cryosphere Monitoring",WG2:"Actionable Cryosphere Projections",WG3:"Cryospheric Risk Management Solutions",WG4:"Adaptation to Cryosphere Loss",WG5:"Amplify the Impact of Cryospheric Science"},
  bodies:["WG1","WG2","WG3","WG4","WG5","SMC","ESC"],
  bodyName:{WG1:"Working Group 1",WG2:"Working Group 2",WG3:"Working Group 3",WG4:"Working Group 4",WG5:"Working Group 5",SMC:"Strategic Management Committee",ESC:"Executive Steering Committee"},
  ocs:{OC1:"Global Cryosphere Monitoring",OC2:"Actionable Cryosphere Projections",OC3:"Cryospheric Risk Management Solutions",OC4:"Adaptation to Cryosphere Loss",OC5:"Amplify the Impact of Cryospheric Science"},
  mgs:{"MG1.1":"Build a Global Cryosphere Monitoring Inventory","MG1.2":"Enhance Monitoring Capabilities","MG1.3":"Make Observations Actionable","MG2.1":"Cryosphere Modelling for Decision Making","MG2.2":"Inclusive Cryosphere Prediction","MG2.3":"Creation of a Decision and Outreach Toolkit","MG3.1":"Global Cryosphere Risk Assessment","MG3.2":"Cryosphere Loss Vulnerability Assessment","MG3.3":"Operationalise Cryosphere Risk Management Solutions","MG4.1":"Incorporating Cryosphere Loss into Adaptation Strategies","MG4.2":"Co-Develop Adaptation Strategies for those Living in and With the Cryosphere","MG4.3":"Establish the Global Cryosphere Adaptation Knowledge Hub","MG5.1":"Policy Integration and Engagement - Cryosphere Loss Prevention","MG5.2":"Global Cryosphere Outreach and Communication","MG5.3":"Education and Capacity Building"},
  levels:{
    "Level 1":{name:"Association",marks:"Decade logo alone",decides:"Secretariat, with the concurrence of the Working Group concerned",chain:["Secretariat","Working Group"],period:"The duration of the project, capped at the end of the current triennium, renewable by decision of the Secretariat."},
    "Level 2":{name:"Endorsement",marks:"Decade logo + UNESCO-IHP logo",decides:"Strategic Management Committee",chain:["Secretariat","Working Group","SMC"],period:"The duration of the project, capped at the end of the current triennium, renewable by decision of the SMC.",clearance:"UNESCO-IHP logo cleared under 34 C/Resolution 86 before the notice is issued."},
    "Level 3":{name:"Flagship",marks:"Decade logo + UNESCO logo",decides:"Executive Steering Committee, on the recommendation of the SMC",chain:["Secretariat","Working Group","SMC","ESC"],period:"Aligned with the triennium, reviewed at each Triennial Cryosphere Summit.",clearance:"UNESCO name and logo cleared under 34 C/Resolution 86 before any use begins."}},
  gates:[
    {k:"g1",t:"Commercial or promotional use",r:"Sponsor visibility on the same placement, lock-ups, co-branded material; the mark in advertising, on merchandise or promoting a sale; any use to attract revenue. A publication for sale, a broadcast, a ticketed event or cost-recovery fees remain eligible where the mark is not associated with a sponsor."},
    {k:"g2",t:"Geoengineering",r:"Scientifically uncertain and potentially extremely harmful geoengineering research and deployment."},
    {k:"g3",t:"Misinformation or misrepresentation",r:"Factual claims about the cryosphere that the science does not support, including over-stated timelines and thresholds."},
    {k:"g4",t:"Partisan, sectarian or religious purpose",r:"Also entertainment unrelated to the Decade, and any activity lacking required approvals, due diligence or compliance documentation."}],
  criteria:[
    {k:"c1",t:"Direct relevance to the framework of the Decade",w:.25,m:"Advances an overarching challenge and a declared main goal, or feeds the Cryosphere Intelligence Platform, the policy interface or a Summit product."},
    {k:"c2",t:"Scientific, educational, policy or public-interest value",w:.25,m:"The merit of the activity itself, not the standing of the applicant."},
    {k:"c3",t:"Inclusiveness and co-production of knowledge",w:.20,m:"Reaches Indigenous peoples and local communities, the Global South, youth, early-career researchers; knowledge co-produced rather than extracted."},
    {k:"c4",t:"Reputation and institutional requirements of UNESCO",w:.15,m:"Partners and sponsors, political exposure, accuracy of claims, consent and rights over persons filmed or quoted."},
    {k:"c5",t:"Quality of the visual and textual context of the logo",w:.10,m:"Official form, clear space, minimum size, no confusing lock-ups with sponsor marks."},
    {k:"c6",t:"Consistency with the terminology of the Synthesis document",w:.05,m:"Uses the vocabulary of the Decade correctly and claims only the main goals it serves."}],
  scale:["Fails","Poor","Weak","Acceptable","Strong","Exemplary"],
  bands:[{min:4,l:"Approve",t:"good"},{min:3,l:"Approve with conditions",t:"info"},{min:2,l:"Revert to applicant",t:"warn"},{min:0,l:"Refuse",t:"bad"}],
  stages:[
    {k:"received",l:"Received",who:"Secretariat"},{k:"screening",l:"Screening & assessment",who:"Secretariat"},{k:"applicant",l:"Awaiting applicant",who:"Applicant"},
    {k:"wg",l:"Working Group review",who:"Working Groups"},{k:"smc",l:"SMC",who:"SMC"},{k:"esc",l:"ESC",who:"ESC"},
    {k:"decided",l:"Decided",who:"Secretariat"},{k:"notified",l:"Notified",who:"Secretariat"},{k:"closed",l:"Closed",who:""}],
  decisions:["Pending","Approved","Approved with conditions","Refused","Withdrawn"],
  opinions:{wg:["Concur","Concur with conditions","Do not concur","Not for this Working Group"],smc2:["Endorse","Endorse with conditions","Do not endorse","Defer to next session"],smc3:["Recommend to the ESC","Recommend with conditions","Do not recommend","Defer to next session"],esc:["Designate as flagship","Designate with conditions","Do not designate","Defer"]},
  decisionMap:{"Endorse":"Approved","Endorse with conditions":"Approved with conditions","Do not endorse":"Refused","Designate as flagship":"Approved","Designate with conditions":"Approved with conditions","Do not designate":"Refused"},
  timeline:[["Registration and acknowledgement",5],["Screening",5],["Assessment",10],["Working Group referral",10],["Decision",5],["Notification",5]],
  target:40
};
CFG.mgs=Object.fromEntries(decadeGoals.map(g=>['MG'+g.id,g.title]));
for(const body of meetingBodies)if(!CFG.bodyName[body.id.toUpperCase()])CFG.bodyName[body.id.toUpperCase()]=body.label;
const STAGE_IDX=Object.fromEntries(CFG.stages.map((s,i)=>[s.k,i]));
const STATUS_OF={received:"1 - Received",screening:"2 - Screening",applicant:"4 - Awaiting applicant",wg:"3 - With WG",smc:"3 - With WG",esc:"3 - With WG",decided:"5 - Decided",notified:"6 - Notified",closed:"7 - Closed"};

/* ---------------- icons ---------------- */
const IC={
  overview:'<path d="M4 5h7v7H4zM13 5h7v4h-7zM13 11h7v8h-7zM4 14h7v5H4z"/>',
  pipeline:'<path d="M4 5h4v14H4zM10 5h4v9h-4zM16 5h4v6h-4z"/>',
  list:'<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
  people:'<path d="M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.5a3.5 3.5 0 0 1 0 6.5M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
  import:'<path d="M12 3v11M7.5 9.5 12 14l4.5-4.5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>',
  book:'<path d="M5 4.5A1.5 1.5 0 0 1 6.5 3H19v16H6.5A1.5 1.5 0 0 0 5 20.5zM5 20.5A1.5 1.5 0 0 0 6.5 22H19"/>',
  inbox:'<path d="M3 13l3-8h12l3 8v6H3zM3 13h5l1.5 2.5h5L16 13h5"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  chevron:'<path d="m15 18-6-6 6-6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  download:'<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 20h14"/>',
  report:'<path d="M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 15.5h5M10 8.5h2"/>',
  archive:'<path d="M4 7h16v3H4zM5 10v9h14v-9M10 14h4"/>',
  bell:'<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15zM10 20.5a2 2 0 0 0 4 0"/>',
  user:'<circle cx="12" cy="8" r="3.6"/><path d="M5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5"/>',
  shield:'<path d="M12 3 4.5 6v5.5c0 4.6 3.2 8.3 7.5 9.5 4.3-1.2 7.5-4.9 7.5-9.5V6z"/><path d="m8.8 12 2.2 2.2 4.2-4.4"/>',
  scale:'<path d="M12 4v16M7 20h10M5 8h14M5 8l-2.5 6a3 3 0 0 0 5 0zM19 8l-2.5 6a3 3 0 0 0 5 0zM12 4l-1.5 1.5M12 4l1.5 1.5"/>',
  users:'<circle cx="9" cy="8.5" r="3.2"/><path d="M3 19.5c.6-3.2 3-5 6-5s5.4 1.8 6 5"/><circle cx="17" cy="9" r="2.6"/><path d="M16.5 14.6c2.3.2 4 1.8 4.5 4.4"/>',
  check:'<circle cx="12" cy="12" r="9"/><path d="m7.8 12.3 2.9 2.9 5.6-6"/>',
  tick:'<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  alert:'<path d="M12 3.5 2.8 19.5h18.4z"/><path d="M12 10v4.2M12 17.2h.01"/>',
  pause:'<circle cx="12" cy="12" r="9"/><path d="M10 9v6M14 9v6"/>',
  send:'<path d="M4 12 20 4l-4.5 16-3.8-6.5z"/><path d="m11.7 13.5 3.8-4"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.8h.01"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>'
};
/* The process of a request in six steps, used across the platform. */
const STEPS=[
  {i:"inbox",l:"Received",d:"Registered and acknowledged"},
  {i:"shield",l:"Screening",d:"Four hard gates"},
  {i:"scale",l:"Assessment",d:"Level and six criteria"},
  {i:"users",l:"Opinions",d:"Working Groups, SMC, ESC"},
  {i:"check",l:"Decision",d:"Recorded with an expiry date"},
  {i:"bell",l:"Notification",d:"Applicant informed, then reports"}];
const STEP_OF={received:0,screening:1,applicant:1,wg:3,smc:3,esc:3,decided:4,notified:5,closed:5};
/* Colours of the five Overarching Challenges, as in the Hub. */
const OC_COLOR={1:"#8ed2ee",2:"#a0a9ff",3:"#f4bc83",4:"#82d8b7",5:"#e9a9d8"};
function processMap(here,opts){opts=opts||{};const paused=opts.paused;
  return`<ol class="pmap ${opts.compact?"compact":""}" aria-label="Steps of a request">${STEPS.map((x,i)=>{const st=here===undefined?"":i<here?"done":i===here?(paused?"paused":"now"):"";
    return`<li class="${st}"><span class="pm-node">${st==="done"?icon("tick"):icon(st==="paused"?"pause":x.i)}</span><span class="pm-text"><b>${x.l}</b>${opts.compact?"":`<small>${st==="paused"?"Waiting for the applicant":x.d}</small>`}</span></li>`}).join("")}</ol>`}
/* Who takes part in each level, as a chain of chips. */
function chainChips(L){return`<span class="chain">${L.chain.map((c,i)=>`${i?`<span class="chain-arrow">${icon("arrow")}</span>`:""}<span class="chain-chip ${i===L.chain.length-1?"last":""}">${esc(c)}</span>`).join("")}</span>`}
const more=(text)=>`<details class="more"><summary aria-label="More information">${icon("info")}</summary><p>${esc(text)}</p></details>`;
const icon=(n)=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[n]}</svg>`;

/* ---------------- state ---------------- */
const S={db:null,user:null,dl:null,uid:null,me:null,isAdmin:false,canWrite:null,ready:false,offline:false,
  requests:new Map(),contacts:new Map(),reports:new Map(),codes:new Map(),reviews:new Map(),accounts:new Map(),account:null,claims:null,accountsReady:false,subs:[],editSub:false,profiles:{},
  view:"overview",sel:null,tab:"submission",preview:null,q:"",stageFilter:"",pending:null,sheet:null,deferred:false};
const $=(s,r=document)=>r.querySelector(s);
const esc=(v)=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const ymd=(d)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const today=()=>ymd(new Date());
const nowIso=()=>new Date().toISOString();
const fmtD=(d)=>{if(!d)return"";const x=new Date(d.length===10?d+"T00:00:00":d);return isNaN(x)?d:x.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"})};
const fmtDT=(d)=>{if(!d)return"";const x=new Date(d);return isNaN(x)?d:x.toLocaleString("en-GB",{day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"})};
const pill=(t,tone,dot)=>t?`<span class="pill ${tone?"t-"+tone:""}">${dot?"<i></i>":""}${esc(t)}</span>`:"";
function toast(msg,err){const t=document.createElement("div");t.className="toast glass"+(err?" err":"");t.setAttribute("role","status");t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),err?6000:2800)}
function store(k,v){try{localStorage.setItem("dacs-desk-"+k,JSON.stringify(v))}catch(e){}}
function recall(k,d){try{const v=localStorage.getItem("dacs-desk-"+k);return v?JSON.parse(v):d}catch(e){return d}}

/* ---------------- calculations (identical to the register formulas) ---------------- */
function gateOutcome(r){const g=Object.values((r.screen||{}).gates||{});if(g.length<4||g.some(v=>!v))return"";if(g.includes("Yes"))return"BLOCK";if(g.includes("To verify"))return"HOLD";return"PASS"}
function score(r){if(gateOutcome(r)==="BLOCK")return null;const sc=(r.assess||{}).scores||{};const v=CFG.criteria.map(c=>sc[c.k]);if(v.some(x=>x===null||x===undefined||x===""))return null;const tw=CFG.criteria.reduce((s,c)=>s+c.w,0);return Math.round(CFG.criteria.reduce((s,c)=>s+Number(sc[c.k])*c.w,0)/tw*100)/100}
function reco(r){const g=gateOutcome(r);if(g==="BLOCK")return{l:"Refuse – hard gate",t:"bad"};const s=score(r);if(s===null)return null;if(g==="HOLD")return{l:"Revert – gate to verify",t:"warn"};const b=CFG.bands.find(b=>s>=b.min);return{l:b.l,t:b.t}}
function scored(r){const sc=(r.assess||{}).scores||{};return CFG.criteria.filter(c=>sc[c.k]!==null&&sc[c.k]!==undefined&&sc[c.k]!=="").length}
function workdays(a,b){if(!a)return null;let d=new Date(a+"T00:00:00"),e=b?new Date(b+"T00:00:00"):new Date(),n=0;while(d<e){d.setDate(d.getDate()+1);const w=d.getDay();if(w&&w!==6)n++}return n}
function addWd(a,n){const d=new Date(a+"T00:00:00");let k=0;while(k<n){d.setDate(d.getDate()+1);const w=d.getDay();if(w&&w!==6)k++}return ymd(d)}
const isOpen=(r)=>!["decided","notified","closed"].includes(r.stage);
function allOpinions(){const out=[];S.reviews.forEach((doc,uid)=>Object.entries((doc&&doc.opinions)||{}).forEach(([key,o])=>{if(o&&o.ref)out.push({uid,key,...o})}));return out}
function opinionsFor(ref){return allOpinions().filter(o=>o.ref===ref).sort((a,b)=>String(b.updatedAt).localeCompare(String(a.updatedAt)))}
function bodyStatus(r,body){const ops=opinionsFor(r.ref).filter(o=>o.body===body);if(ops.some(o=>o.status==="submitted"))return"done";if(ops.length)return"draft";return""}
function optionsFor(body,level){if(!["SMC","ESC"].includes(body))return CFG.opinions.wg;if(body==="SMC")return level==="Level 3"?CFG.opinions.smc3:CFG.opinions.smc2;return CFG.opinions.esc}

/* ---------------- identity and role ---------------- */
function roleNow(){
  if(S.preview)return S.preview;
  if(S.claims)return S.claims;
  return{role:"none",body:""};
}
const isSec=()=>roleNow().role==="secretariat";
function roleLabel(r){r=r||roleNow();return r.role==="secretariat"?"UNESCO Secretariat":r.role==="wg"?r.body+" reviewer":r.role==="smc"?"SMC reviewer":r.role==="esc"?"ESC reviewer":"No role yet"}
async function names(){}
const nm=(id)=>id?((S.accounts.get(id)||{}).email||(id===S.uid?S.account:"")):"";
const av=()=>"";

/* ---------------- the person at the keyboard ----------------
   Several people can share one login (for example a Working Group leadership). Each one gives their name once
   on this device; it is recorded with every review, assessment and change they make. */
const actorKey=()=>"actor-"+(S.uid||"");
const actor=()=>S.actor||"";
function who(){const a=actor(),l=(S.claims||{}).label||"";return a&&l&&a!==l?`${a} (${l})`:(a||l)}
function askActor(){if(S.sheet==="actor")return;const l=(S.claims||{}).label||"";const personal=l&&!/leadership|members|secretariat/i.test(l);const cur=actor()||(personal?l:"");
  openSheet(`<h2>Who is working on this account?</h2><p class="muted" style="margin-top:6px;font-size:13.5px">Your name is recorded with every review, assessment and change you make. Several people may use the <b>${esc(l||S.account||"")}</b> login: each gives their own name.</p>
  <form id="actorForm" class="stack" style="gap:14px;margin-top:16px"><label class="field"><span>Your full name</span><input class="input" id="actorName" value="${esc(cur)}" required maxlength="80" autocomplete="name" placeholder="First name and family name"></label>
  <div class="row" style="justify-content:flex-end">${actor()?`<button type="button" class="btn" data-act="closesheet">Cancel</button>`:""}<button type="submit" class="btn primary">Continue</button></div></form>`,"actor")}
function setActor(n){S.actor=n;store(actorKey(),n);closeSheet();render();maybeShowTasks()}

/* ---------------- writes ---------------- */
const queues={};
function queued(path,fn){const p=(queues[path]||Promise.resolve()).then(fn,fn);queues[path]=p.catch(()=>{});return p}
function deepMerge(a,b){for(const k in b){if(b[k]&&typeof b[k]==="object"&&!Array.isArray(b[k])){a[k]=deepMerge(a[k]&&typeof a[k]==="object"?a[k]:{},b[k])}else a[k]=b[k]}return a}
function writeErr(e){console.error(e);if(e&&(e.code==="permission-denied"||e.code==="invalid_argument")){toast("This change was not saved: your role does not allow it.",true)}else if(e&&e.code==="quota_exceeded")toast("The register is full. Ask the Secretariat to archive closed requests.",true);else toast("The change could not be saved. Check your connection and try again.",true)}
async function saveReq(ref,patch,what){
  if(!S.db)return;if(!actor()){askActor();return}const r=S.requests.get(ref);
  const body=JSON.parse(JSON.stringify(patch));body.updatedAt=nowIso();
  if(isSec()&&(body.screen||body.assess||body.consult)){const cur=((r&&r.assess)||{}).assessors||[];body.assess=Object.assign(body.assess||{},{assessedBy:actor(),assessedAt:nowIso(),assessors:[...new Set([...cur,actor()])]})}
  if(isSec()&&body.decision&&body.decision.final!==undefined)body.decision.recordedBy=actor();
  if(what){const h=(r&&r.history)||[];body.history=[...h,{at:nowIso(),by:S.uid||"",who:who(),what}].slice(-200)}
  return queued("requests/"+ref,()=>S.db.doc("requests/"+ref).update(body)).catch(writeErr);
}
const pendingText={};
function saveLater(ref,patch,label){const k=ref;pendingText[k]=pendingText[k]||{patch:{},label,timer:null};deepMerge(pendingText[k].patch,patch);clearTimeout(pendingText[k].timer);pendingText[k].timer=setTimeout(()=>{const p=pendingText[k];delete pendingText[k];saveReq(ref,p.patch,p.label)},700)}
function flushText(){Object.keys(pendingText).forEach(k=>{const p=pendingText[k];clearTimeout(p.timer);delete pendingText[k];saveReq(k,p.patch,p.label)})}
const newOpKey=(ref,body)=>ref+"__"+body+"__"+Date.now().toString(36)+Math.random().toString(36).slice(2,6);
/* The review being edited in the side panel: an existing key, "new" for a blank form, or null to choose automatically. */
function currentOp(r){if(!r)return null;const ops=myOps(r.ref);
  if(S.opKey&&S.opKey!=="new"){const o=ops.find(x=>x.key===S.opKey);return o||{key:S.opKey,reviewer:actor()}}
  if(S.opKey==="new")return{key:null,reviewer:actor()};
  const d=ops.find(x=>x.status!=="submitted");if(d)return d;
  return ops.length?null:{key:null,reviewer:actor()};
}
function ensureKey(ref){const c=currentOp(S.requests.get(ref));if(c&&c.key)return c.key;const k=newOpKey(ref,roleNow().body);S.opKey=k;return k}
async function saveOpinion(ref,patch,key){
  if(!S.db||!S.uid)return;if(!actor()){askActor();return}
  const rl=roleNow(),body=rl.body;key=key||ensureKey(ref);const path="reviews/"+S.uid;
  return queued(path,async()=>{const cur=S.reviews.get(S.uid);const prev=(cur&&cur.opinions&&cur.opinions[key])||{};
    const o=Object.assign({reviewer:actor(),createdAt:nowIso()},prev,patch,{ref,body,account:S.account,label:rl.label||body,updatedAt:nowIso()});
    if(!cur)await S.db.doc(path).set({opinions:{[key]:o}});else await S.db.doc(path).update({opinions:{[key]:o}});}).catch(writeErr);
}
const pendingOp={};
function opinionLater(ref,key,patch){pendingOp[key]=Object.assign(pendingOp[key]||{},patch);clearTimeout(pendingOp[key+"_t"]);pendingOp[key+"_t"]=setTimeout(()=>{const p=pendingOp[key];delete pendingOp[key];saveOpinion(ref,Object.assign({status:"draft"},p),key)},700)}
function flushOp(key){if(!pendingOp[key])return{};const p=pendingOp[key];clearTimeout(pendingOp[key+"_t"]);delete pendingOp[key];return p}

/* ---------------- connect ---------------- */
function unsubAll(){S.subs.forEach((u)=>{try{u()}catch(e){}});S.subs=[]}
async function connect(){
 if(!configured){S.offline=true;return render();}S.db=DB;
 onAuthStateChanged(auth,user=>{
  if(S.roleSub){S.roleSub();S.roleSub=null;}unsubAll();clearReviews();S.requests.clear();S.reviews.clear();S.contacts.clear();S.accounts.clear();S.reports.clear();S.codes.clear();S.preview=null;S.ready=false;
  if(!user){S.account=null;S.uid=null;S.claims=null;S.ready=true;render();return;}
  S.uid=user.uid;S.account=user.email;let r={},gov=[],profile={},roleReady=false,govReady=false,key='';
  const refresh=()=>{
   if(!roleReady||!govReady)return;
   const admin=user.platformAdmin===true||isUnescoSecretariat(r);
   const access={uid:user.uid,role:r,governance:gov,profile,admin};S.allowedBodies=logoBodies(access).map(b=>b.toUpperCase());
   const chosen=S.allowedBodies.includes(S.activeBody)?S.activeBody:S.allowedBodies[0]||'';
   const c={role:admin?'secretariat':chosen==='SMC'?'smc':chosen==='ESC'?'esc':chosen?'wg':'none',body:admin?'Secretariat':chosen,label:profile.name||user.displayName||user.email};
   S.claims=c;S.actor=c.label;S.me={name:c.label};const next=c.role+'|'+c.body;
   if(key===next){schedule();return;}key=next;S.tasksShown=false;S.gotReq=false;S.gotRev=false;unsubAll();clearReviews();S.requests.clear();S.reviews.clear();S.contacts.clear();S.accounts.clear();S.reports.clear();S.codes.clear();S.sel=null;S.preview=null;startData(c.role);
  };
  S.changeBody=b=>{flushText();S.activeBody=b;refresh();};
  const fail=e=>{console.error(e);S.claims={role:'none',body:'',label:user.email};S.ready=true;render();};
  const stops=[onSnapshot(doc(fs,'roles',user.uid),d=>{r=d.exists()?d.data():{};roleReady=true;refresh();},fail),onSnapshot(query(collection(fs,'governance'),limit(10)),s=>{gov=s.docs.map(d=>({id:d.id,...d.data()}));govReady=true;refresh();},fail),onSnapshot(doc(fs,'profiles',user.uid),d=>{profile=d.exists()?d.data():{};refresh();},fail)];S.roleSub=()=>stops.forEach(s=>s());
 });
}
let reviewStops=[],reviewKey='';const reviewBatches=new Map();
function clearReviews(){reviewStops.forEach(s=>s());reviewStops=[];reviewBatches.clear();reviewKey='';}
function subscribeReviews(refs,admin){
 const key=admin?'all':refs.sort().join('|');if(key===reviewKey&&reviewStops.length)return;clearReviews();reviewKey=key;
 const scopes=admin?[[]]:Array.from({length:Math.ceil(refs.length/5)},(_,i)=>refs.slice(i*5,i*5+5));
 if(!scopes.length){S.reviews.clear();S.gotRev=true;return;}
 reviewStops=scopes.map((ids,i)=>onSnapshot(query(collection(fs,'logoReviews'),...(admin?[]:[where('ref','in',ids)]),limit(500)),s=>{
  reviewBatches.set(i,s.docs.map(d=>d.data()));const grouped=new Map();for(const batch of reviewBatches.values())for(const x of batch){const {uid,key,...o}=x;if(!grouped.has(uid))grouped.set(uid,{opinions:{}});grouped.get(uid).opinions[key]=o;}S.reviews=grouped;S.gotRev=true;schedule();afterFirst();
 },e=>{console.error(e);toast('Reviews could not be loaded.',true);}));
}
function startData(role){
 const err=e=>{console.error(e);toast('Access to this part of the register was refused.',true);};
 if(role==='none'){S.ready=true;S.view='welcome';render();return;}
 const reqQuery=role==='secretariat'?DB.collection('requests'):DB.collection('requests',where('assigned.bodies','array-contains',S.claims.body));
 S.subs.push(reqQuery.onSnapshot(s=>{S.requests=new Map(s.docs.map(d=>[d.id,{ref:d.id,...d.data()}]));S.ready=true;S.gotReq=true;subscribeReviews([...S.requests.keys()],role==='secretariat');schedule();afterFirst();},err));
 S.arch={};
 if(role==='secretariat'){
  S.subs.push(onSnapshot(query(collection(fs,'profiles'),limit(200)),s=>{S.accounts=new Map(s.docs.map(d=>[d.id,{label:d.data().name,email:d.data().contact||'',body:''}]));schedule();},err));
  for(const [col,field] of [['reports','reports'],['reportCodes','codes'],['contacts','contacts']])S.subs.push(DB.collection(col).onSnapshot(s=>{S[field]=new Map(s.docs.map(d=>[d.id,{id:d.id,...d.data()}]));schedule();},err));
  const saved=recall('view',null);S.view=saved?.view||'overview';
 }else S.view='mine';render();
}
function afterFirst(){if(!S.gotReq||!S.gotRev)return;maybeShowTasks()}
function schedule(){if(!S.account&&document.getElementById("loginForm")&&S.accountsReady)return;if(S.sheet==="tasks"&&document.querySelector(".sheet")){const y=document.querySelector(".sheet").scrollTop;tasksSheet();document.querySelector(".sheet").scrollTop=y}const a=document.activeElement;if(a&&a.closest&&a.closest("#view")&&a.matches("input[type=text],input[type=search],input[type=date],textarea")){S.deferred=true;const cur=S.sel&&currentOp(S.requests.get(S.sel));const submit=document.querySelector('#composer [data-act="submit"]');if(submit)submit.disabled=!!S.preview||!cur?.opinion||cur.status==='submitted';document.querySelectorAll('#composer [data-op]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.op===cur?.opinion)));return}render()}
document.addEventListener("focusout",()=>{setTimeout(()=>{if(S.deferred){const a=document.activeElement;if(!(a&&a.matches&&a.matches("input,textarea"))){S.deferred=false;render()}}},350)});

/* ---------------- shell ---------------- */
function navItems(){
  const r=roleNow().role;
  if(r==="secretariat")return[["overview","Overview","overview"],["pipeline","Pipeline","pipeline"],["requests","All requests","list",S.requests.size],["archive","Decision history","archive",archive().length],["reports","Activity reports","report",newReports().length||undefined],["import","Add requests","import"],["method","Methodology","book"]];
  if(r==="none")return[["welcome","Restricted access","inbox"]];
  return[["mine","My dossiers","inbox",mine().length],["archive","Decision history","archive",archive().length],["method","Methodology","book"]];
}
function renderShell(){
  const items=navItems();const cur=S.sel?"":S.view;
  $("#nav").innerHTML=items.map(([k,l,i,n])=>`<button type="button" data-go="${k}" ${cur===k?'aria-current="page"':""}>${icon(i)}<span>${l}</span>${n!==undefined?`<span class="count num">${n}</span>`:""}</button>`).join("");
  $("#compactNav").innerHTML=$("#nav").innerHTML;
  $("#compactSection").innerHTML=`<option value="" disabled ${!cur?"selected":""}>Choose a section</option>`+items.map(([k,l])=>`<option value="${k}" ${cur===k?"selected":""}>${l}</option>`).join("");
  const SHORT={overview:"Overview",pipeline:"Pipeline",requests:"All",accounts:"Accounts",import:"Add",method:"Guide",mine:"Dossiers",welcome:"Welcome",archive:"History",reports:"Reports"};
  $("#tabbar").innerHTML=items.map(([k,l,i])=>`<button type="button" data-go="${k}" ${cur===k?'aria-current="page"':""}>${icon(i)}<span>${SHORT[k]||l}</span></button>`).join("");
  const me=S.me;
  const nt=S.account&&roleNow().role!=="none"&&!S.preview?tasks().length:0;const bell=(cls)=>S.account&&roleNow().role!=="none"?`<button type="button" class="bell ${cls||""} ${nt?"has":""}" data-act="tasks" aria-label="${nt} pending tasks">${icon("bell")}${cls==="wide"?`<span>${nt?"Pending tasks":"No pending task"}</span>`:""}${nt?`<b class="num">${nt}</b>`:""}</button>`:"";
  $("#bellBox").innerHTML=bell("wide");
  $("#me").innerHTML=me?`<div class="who"><b>${esc(actor()||(S.claims||{}).label||"You")}</b><span>${actor()&&actor()!==(S.claims||{}).label?esc((S.claims||{}).label||"")+" · ":""}${esc(S.account||"")}</span></div><button class="btn sm" data-act="logout" style="margin-left:auto">Sign out</button>`:"";
  $("#topMe").innerHTML=`${!isSec()&&(S.allowedBodies||[]).length>1?`<label>Review as <select id="hubBody">${S.allowedBodies.map(b=>`<option value="${b}" ${b===S.claims.body?'selected':''}>${b}</option>`).join('')}</select></label>`:''}${bell("")}<span class="pill t-info">${esc(roleLabel())}</span><button class="btn sm" data-theme-btn type="button">${document.documentElement.classList.contains("light")?"Dark":"Bright"}</button><button class="btn sm" data-act="logout">Sign out</button>`;
  $("#previewBox").innerHTML=S.claims&&S.claims.role==="secretariat"?`<div class="preview"><label for="previewSel">See the platform as</label><select id="previewSel" class="input">${[["","Secretariat (you)"],...CFG.bodies.map(b=>[b,b+" reviewer"])].map(([v,l])=>`<option value="${v}" ${((S.preview&&S.preview.body)||"")===v?"selected":""}>${l}</option>`).join("")}</select></div>`:"";
  $("#compactTools").innerHTML=bell("")+$("#previewBox").innerHTML.replaceAll("previewSel","compactPreviewSel");
}
function render(){
  renderShell();
  const v=$("#view");const y=window.scrollY;
  if(S.offline){v.innerHTML=`<div class="glass card"><h2>Firebase is not configured</h2><p class="sub">Fill in <code>public/firebase-config.js</code> with the web app configuration of your Firebase project (Firebase console → Project settings → Your apps), then deploy again.</p></div>`;return}
  if(!S.ready){v.innerHTML=`<div class="glass card empty">Connecting to the register…</div>`;return}
  document.body.classList.toggle("signed-out",!S.account);
  if(!S.account){v.innerHTML=`<div class="glass card"><h2>Sign in through the Cryosphere Hub</h2><a class="btn primary" href="/" target="_top">Open the Hub</a></div>`;return}
  const r=roleNow().role;
  if(S.sel&&canSee(S.sel))v.innerHTML=viewDetail(reqAny(S.sel));
  else{S.sel=null;
    const valid=navItems().map(x=>x[0]);if(!valid.includes(S.view))S.view=valid[0];
    v.innerHTML=({reports:viewReports,archive:viewArchive,overview:viewOverview,pipeline:viewPipeline,requests:viewRequests,import:viewImport,method:viewMethod,mine:viewMine,welcome:viewWelcome})[S.view]();
    renderShell();}
  store("view",{view:S.view,sel:S.sel,tab:S.tab});
  window.scrollTo(0,y);
  afterRender();
}
function go(view){flushText();S.from=null;S.view=view;S.sel=null;window.scrollTo(0,0);render()}
function open(ref,tab){flushText();if(S.sel!==ref)S.opKey=null;if(!S.sel)S.from=S.view;S.sel=ref;S.tab=tab||(isSec()?"submission":"submission");window.scrollTo(0,0);render()}
function head(eyebrow,title,sub,actions){return`<div class="head"><div><div class="eyebrow">${eyebrow}</div><h1 class="title">${title}</h1>${sub?`<p class="sub">${sub}</p>`:""}</div>${actions?`<div class="row">${actions}</div>`:""}</div>`}
function accessBanner(){return""}
function previewBanner(){return accessBanner()+(S.preview?`<div class="banner info">You are seeing the platform as <b>${esc(roleLabel())}</b>. Inputs are disabled in this preview. Choose "Secretariat (you)" in the side bar to return.</div>`:"")}

/* ---------------- decision history (visible to every profile) ---------------- */
const ARCH=["decided","notified","closed"];
function archive(){if(isSec())return[...S.requests.values()].filter(r=>ARCH.includes(r.stage));const m=new Map();Object.values(S.arch||{}).forEach(x=>x.forEach((v,k)=>m.set(k,v)));mine().filter(r=>ARCH.includes(r.stage)).forEach(r=>m.set(r.ref,r));return[...m.values()]}
function reqAny(ref){return S.requests.get(ref)||archive().find(r=>r.ref===ref)||null}
function canSee(ref){if(isSec())return S.requests.has(ref);return mine().some(x=>x.ref===ref)||archive().some(x=>x.ref===ref)}
function viewArchive(){
  const q=S.q.trim().toLowerCase();
  const rows=archive().filter(r=>!q||[r.ref,r.sub.title,r.sub.organisation,r.sub.country,(r.decision||{}).final].join(" ").toLowerCase().includes(q)).sort((a,b)=>String((b.decision||{}).date||"").localeCompare(String((a.decision||{}).date||""))||b.formId-a.formId);
  const tone=(f)=>/^Approved/.test(f||"")?"good":/Refused/.test(f||"")?"bad":"";
  return previewBanner()+head("All profiles","Decision history",`Requests fully reviewed and decided. ${rows.length} decision${rows.length===1?"":"s"} recorded. Open a request to read its assessment, the reviews given and the decision.`,`<div class="search">${icon("search")}<input class="input" type="search" id="q" placeholder="Search title, organisation, decision" value="${esc(S.q)}" aria-label="Search the decision history"></div>`)+
  `<div class="glass table-wrap"><table><thead><tr><th>Request</th><th>Level</th><th>Decision</th><th>Decided on</th><th>Authorised until</th><th>Reviews</th><th>Status</th></tr></thead><tbody>
  ${rows.map(r=>{const d=r.decision||{},n=opinionsFor(r.ref).filter(o=>o.status==="submitted").length;return`<tr class="click" data-open="${esc(r.ref)}"><td><div class="t">${esc(r.sub.title)}</div><div class="o">${esc(r.ref)} · ${esc(r.sub.organisation)}${r.sub.country?" · "+esc(r.sub.country):""}</div></td>
    <td>${esc((r.assess||{}).level||"–")}</td><td>${d.final&&d.final!=="Pending"?pill(d.final,tone(d.final)):"–"}</td><td class="num">${d.date?fmtD(d.date):"–"}</td><td class="num">${d.until?fmtD(d.until):"–"}</td><td class="num">${n||"–"}</td><td>${pill(CFG.stages[STAGE_IDX[r.stage]].l,"")}</td></tr>`}).join("")||`<tr><td colspan="7" class="empty">No request has been decided yet. Requests appear here once the decision is recorded.</td></tr>`}
  </tbody></table></div>`;
}
function decisionSummary(r){const d=r.decision||{};
  return`<div class="glass card"><div class="card-head"><h3>Decision</h3>${d.final&&d.final!=="Pending"?pill(d.final,/^Approved/.test(d.final)?"good":/Refused/.test(d.final)?"bad":""):pill("Pending","")}</div>
  <div class="kv">${[["Decided on",d.date?fmtD(d.date):"–"],["Authorised from",d.from?fmtD(d.from):"–"],["Authorised until",d.until?fmtD(d.until):"–"],["Recorded by",d.recordedBy||"–"]].map(([k,v])=>`<div><span>${k}</span><b>${esc(v)}</b></div>`).join("")}</div>
  ${d.conditions?`<p class="muted" style="font-size:13px;margin-top:10px"><b>Conditions:</b> ${esc(d.conditions)}</p>`:""}</div>`}

/* ---------------- activity reports from applicants ---------------- */
const tsIso=(x)=>!x?"":typeof x==="string"?x:x.toDate?x.toDate().toISOString():x.seconds?new Date(x.seconds*1000).toISOString():"";
const approved=(r)=>/^Approved/.test((r.decision||{}).final||"");
function reportsFor(ref){return[...S.reports.values()].filter(x=>x.ref===ref).sort((a,b)=>tsIso(b.submittedAt).localeCompare(tsIso(a.submittedAt)))}
function newReports(){return isSec()&&!S.preview?[...S.reports.values()].filter(x=>!(x.review||{}).status):[]}
const reportUrl=(ref,code)=>`${new URL('report.html',location.href).href.split('?')[0]}?ref=${encodeURIComponent(ref)}&code=${encodeURIComponent(code)}`;
function makeCode(){const A="ABCDEFGHJKMNPQRSTUVWXYZ23456789",a=new Uint32Array(10);crypto.getRandomValues(a);const c=[...a].map(n=>A[n%A.length]).join("");return c.slice(0,4)+"-"+c.slice(4,8)+"-"+c.slice(8)}
function applicantMessage(r,code){const c=S.contacts.get(r.ref)||{},rp=r.reporting||{};
  return`Dear ${c.applicant||"colleague"},

Thank you for carrying the logo of the Decade of Action for Cryospheric Sciences (2025–2034) for "${r.sub.title}".

To help the Secretariat follow the activities using the logo and compile the reporting of the Decade, please report on your activity on the following page:
${reportUrl(r.ref,code)}

Request reference: ${r.ref}
Reporting code: ${code}
${rp.progressDue?`\nPlease send a progress update by ${fmtD(rp.progressDue)}`:""}${rp.finalDue?`${rp.progressDue?" and":"\nPlease send"} a final report by ${fmtD(rp.finalDue)}`:""}${rp.progressDue||rp.finalDue?".\n":""}
The page accepts a short narrative, figures on reach, links to outputs and one attachment. You may submit as many progress updates as needed.

With best regards,
${actor()||"The Secretariat"}
UNESCO Secretariat of the Decade of Action for Cryospheric Sciences
cryosphere@unesco.org`}
function reportHTML(x,full){const rv=x.review||{};
  const fig=[["People reached",x.people],["Events, publications or products",x.outputs],["Countries",x.countries]].filter(([,v])=>v!==null&&v!==undefined&&v!=="");
  return`<details class="rep" ${full?"open":""}><summary><span class="rep-t"><b>${esc(x.type)}</b>${x.periodFrom||x.periodTo?` · ${fmtD(x.periodFrom)||"…"} – ${fmtD(x.periodTo)||"…"}`:""}<small>Received ${fmtDT(tsIso(x.submittedAt))} · ${esc(x.name)}, ${esc(x.organisation||"")}</small></span><span class="rep-s">${pill(x.status||"",/Completed/.test(x.status)?"good":/delayed|Postponed/.test(x.status)?"warn":/Cancelled/.test(x.status)?"bad":"")}${rv.status?pill("Reviewed","good"):pill("New","info")}</span></summary>
  <div class="rep-b">
    ${fig.length?`<div class="kv kv3">${fig.map(([k,v])=>`<div><span>${k}</span><b>${esc(v)}</b></div>`).join("")}</div>`:""}
    <div class="rep-sec"><h4>Summary of what was done</h4><p>${esc(x.summary)}</p></div>
    ${x.outcomes?`<div class="rep-sec"><h4>Outcomes and results</h4><p>${esc(x.outcomes)}</p></div>`:""}
    ${x.logoUse?`<div class="rep-sec"><h4>Where the logo was used</h4><p>${esc(x.logoUse)}</p></div>`:""}
    ${(x.mgs||[]).length||x.contribution?`<div class="rep-sec"><h4>Contribution to the main goals</h4>${(x.mgs||[]).length?`<div class="chips" style="margin:4px 0 6px">${x.mgs.map(m=>`<span class="chip" aria-pressed="true" title="${esc(CFG.mgs[m]||"")}">${esc(m)}</span>`).join("")}</div>`:""}${x.contribution?`<p>${esc(x.contribution)}</p>`:""}</div>`:""}
    ${(x.links||[]).length?`<div class="rep-sec"><h4>Links</h4><ul class="links">${x.links.filter(l=>typeof l==="string"&&/^https?:\/\/[^\s]+$/.test(l)).map(l=>`<li><a href="${esc(l)}" target="_blank" rel="noopener noreferrer">${esc(l)}</a></li>`).join("")}</ul></div>`:""}
    <p class="muted" style="font-size:12.5px">Reported by ${esc(x.name)} · <a href="mailto:${esc(x.email)}">${esc(x.email)}</a></p>
    <div class="row">${x.fileName?`<button class="btn sm" data-act="repfile" data-id="${esc(x.id)}">${icon("download")}${esc(x.fileName)} · ${Math.max(1,Math.round((x.fileSize||0)/1024))} KB</button>`:""}
      ${S.preview?"":rv.status?`<span class="muted" style="font-size:12.5px">Reviewed by ${esc(rv.by||"")} · ${fmtDT(rv.at)}</span><button class="btn sm" data-act="repunreview" data-id="${esc(x.id)}">Mark as new</button>`:`<button class="btn sm primary" data-act="repreview" data-id="${esc(x.id)}">Mark as reviewed</button>`}
      ${S.preview?"":`<button class="btn sm danger" data-act="repdel" data-id="${esc(x.id)}">Delete</button>`}</div>
  </div></details>`}
function tabReporting(r,ro){const code=(S.codes.get(r.ref)||{}).code,rs=reportsFor(r.ref),c=S.codes.get(r.ref)||{};
  return`<div class="glass card"><div class="card-head"><h2>Reporting by the applicant</h2>${code?pill("Code issued","good"):approved(r)?pill("Code to issue","warn"):pill("After authorisation","")}</div>
  <p class="sub" style="font-size:14px">Authorised applicants report on their activity on a public page, without an account: progress updates while it runs, a final report at the end. Each request has its own reporting code, which you send with the authorisation.</p>
  ${code?`<div class="codebox"><div><span>Reporting code</span><b class="mono">${esc(code)}</b></div><div><span>Reporting page for this request</span><a class="mono" href="${esc(reportUrl(r.ref,code))}" target="_blank" rel="noopener">${esc(reportUrl(r.ref,code))}</a></div></div>
    <p class="muted" style="font-size:12.5px;margin-top:8px">Issued ${c.createdAt?fmtDT(c.createdAt):""}${c.createdBy?" by "+esc(c.createdBy):""}.</p>
    ${ro?"":`<div class="row" style="margin-top:12px"><button class="btn primary" data-act="repmsg" data-ref="${esc(r.ref)}">Copy the message to the applicant</button><button class="btn" data-act="replink" data-ref="${esc(r.ref)}">Copy the link</button><button class="btn danger" data-act="repcode" data-ref="${esc(r.ref)}" data-replace="1">Replace the code</button></div>`}`
   :ro?"":`<div class="row" style="margin-top:12px"><button class="btn primary" data-act="repcode" data-ref="${esc(r.ref)}">Issue a reporting code</button>${approved(r)?"":`<span class="muted" style="font-size:12.5px">Usually issued once the use of the logo is approved.</span>`}</div>`}
  <div class="grid g2" style="margin-top:16px">${fld(r,"reporting.progressDue","Progress update expected by","date",{},ro)}${fld(r,"reporting.finalDue","Final report expected by","date",{hint:(r.decision||{}).until?"Authorisation ends "+fmtD(r.decision.until)+".":""},ro)}</div></div>
  <div class="glass card"><div class="card-head"><h2>Reports received</h2><span class="muted num">${rs.length}</span></div>
  ${rs.length?`<div class="stack" style="gap:10px">${rs.map((x,i)=>reportHTML(x,i===0)).join("")}</div>`:`<p class="empty">No report yet.${code?" Reports sent through the reporting page appear here at once.":""}</p>`}</div>`}
function viewReports(){
  const q=S.q.trim().toLowerCase();const all=[...S.reports.values()];
  const rows=all.filter(x=>{const r=S.requests.get(x.ref);return!q||[x.ref,x.name,x.organisation,x.type,x.status,r&&r.sub.title].join(" ").toLowerCase().includes(q)}).sort((a,b)=>tsIso(b.submittedAt).localeCompare(tsIso(a.submittedAt)));
  const last={};[...all].sort((a,b)=>tsIso(a.submittedAt).localeCompare(tsIso(b.submittedAt))).forEach(x=>{last[x.ref]=x});const latest=Object.values(last);const sum=(k)=>latest.reduce((n,x)=>n+(Number(x[k])||0),0);
  const countries=new Set(latest.flatMap(x=>String(x.countries||"").split(/[,;]/).map(c=>c.trim().toLowerCase()).filter(Boolean)));
  const acts=new Set(all.map(x=>x.ref));
  return head("UNESCO Secretariat","Activity reports",`Progress updates and final reports sent by authorised applicants through the public reporting page. Figures are as reported by the applicants.`,`<div class="search">${icon("search")}<input class="input" type="search" id="q" placeholder="Search reports" value="${esc(S.q)}" aria-label="Search reports"></div><button class="btn" data-act="repexport">${icon("download")}Download for Decade reporting</button>`)+
  `<div class="grid g4">
    <div class="glass stat"><div class="l">Reports received</div><div class="v num">${all.length}</div><div class="s">${acts.size} activit${acts.size===1?"y":"ies"} · ${all.filter(x=>x.type==="Final report").length} final</div></div>
    <div class="glass stat"><div class="l">People reached</div><div class="v num">${sum("people").toLocaleString("en-GB")}</div><div class="s">latest report of each activity</div></div>
    <div class="glass stat"><div class="l">Events, publications, products</div><div class="v num">${sum("outputs").toLocaleString("en-GB")}</div><div class="s">latest report of each activity</div></div>
    <div class="glass stat"><div class="l">Countries</div><div class="v num">${countries.size}</div><div class="s">named in the latest reports</div></div>
  </div>
  <div class="glass table-wrap"><table><thead><tr><th>Activity</th><th>Report</th><th>Received</th><th>Status of the activity</th><th>People</th><th>Outputs</th><th>Review</th></tr></thead><tbody>
  ${rows.map(x=>{const r=S.requests.get(x.ref);return`<tr class="click" data-open="${esc(x.ref)}" data-tab="reporting"><td><div class="t">${esc(r?r.sub.title:x.ref)}</div><div class="o">${esc(x.ref)} · ${esc(x.organisation||"")}</div></td><td>${esc(x.type)}<div class="o">${x.periodFrom||x.periodTo?`${fmtD(x.periodFrom)||"…"} – ${fmtD(x.periodTo)||"…"}`:""}</div></td><td class="num">${fmtD(tsIso(x.submittedAt).slice(0,10))}</td><td>${esc(x.status||"")}</td><td class="num">${x.people??"–"}</td><td class="num">${x.outputs??"–"}</td><td>${(x.review||{}).status?pill("Reviewed","good"):pill("New","info")}</td></tr>`}).join("")||`<tr><td colspan="7" class="empty">No report yet. Issue a reporting code from the Reporting tab of an authorised request, then send it to the applicant.</td></tr>`}
  </tbody></table></div>
  <p class="muted" style="font-size:12.5px">Totals use the latest report of each activity, so successive updates are not counted twice. The download lists every report and marks the latest one of each activity.</p>`;
}
async function exportReports(){
  try{const X=await loadXLSX();const all=[...S.reports.values()].sort((a,b)=>a.ref.localeCompare(b.ref)||tsIso(a.submittedAt).localeCompare(tsIso(b.submittedAt)));
    const latest={};all.forEach(x=>{latest[x.ref]=x.id});
    const rows=all.map(x=>{const r=S.requests.get(x.ref)||{sub:{}},d=r.decision||{};return{"Ref. no.":x.ref,"Activity title":r.sub.title,"Organisation":x.organisation||r.sub.organisation,"Country (request)":r.sub.country,"Level":(r.assess||{}).level,"Decision":d.final,"Authorised until":d.until,
      "Report type":x.type,"Latest report for this activity":latest[x.ref]===x.id?"Yes":"No","Received":tsIso(x.submittedAt).slice(0,10),"Period from":x.periodFrom,"Period to":x.periodTo,"Status of the activity":x.status,
      "People reached":x.people,"Events, publications or products":x.outputs,"Countries":x.countries,"Main goals":(x.mgs||[]).join("; "),"Contribution to the main goals":x.contribution,
      "Summary":x.summary,"Outcomes and results":x.outcomes,"Where the logo was used":x.logoUse,"Links":(x.links||[]).join("\n"),"Attachment":x.fileName,"Reported by":x.name,"E-mail":x.email,"Reviewed by":(x.review||{}).by||""}});
    const wb=X.utils.book_new();X.utils.book_append_sheet(wb,X.utils.json_to_sheet(rows),"Activity reports");
    const data=new Uint8Array(X.write(wb,{type:"array",bookType:"xlsx"}));
    const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([data],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));a.download="DACS-logo-activity-reports-"+today()+".xlsx";document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);
  }catch(e){console.error(e);toast("The reports could not be downloaded.",true)}
}
async function copyText(txt,ok){try{await navigator.clipboard.writeText(txt);toast(ok)}catch(e){openSheet(`<h2>Copy this text</h2><textarea class="input" rows="14" style="margin-top:12px;width:100%" readonly>${esc(txt)}</textarea><div class="row" style="justify-content:flex-end;margin-top:12px"><button class="btn primary" data-act="closesheet">Done</button></div>`,"copy")}}

/* ---------------- pending tasks ---------------- */
const TASK_GROUPS={sec:["Overdue","Screen and assess","Opinions received","Decide and notify","Activity reports"],rev:["Overdue","To review","Drafts to finish"]};
function tasks(){const out=[],role=roleNow(),t=today();
  if(role.role==="secretariat"){S.requests.forEach(r=>{const bs=(r.assigned||{}).bodies||[],due=(r.assigned||{}).due,g=gateOutcome(r);
    const add=(why,tone,tab,group)=>out.push({r,why,tone,tab,group});
    if(r.stage==="received")add("New request to screen","info","screening","Screen and assess");
    if(r.stage==="screening"&&g==="HOLD")add("Hard gate to verify with the applicant","warn","screening","Screen and assess");
    if(r.stage==="screening"&&g!=="HOLD"&&g!=="BLOCK"&&scored(r)<6)add(`Assessment to complete · ${scored(r)}/6 criteria scored`,"info","assessment","Screen and assess");
    if(r.stage==="screening"&&!bs.length&&(r.consult||[]).length&&g==="PASS"&&scored(r)===6)add("Ready to send to "+r.consult.join(", "),"info","assessment","Screen and assess");
    if(r.stage==="wg"){const w=bs.filter(b=>/^WG/.test(b));if(w.length&&w.every(b=>bodyStatus(r,b)==="done"))add("All Working Group opinions in","good","reviews","Opinions received")}
    if(r.stage==="smc"&&bodyStatus(r,"SMC")==="done")add("SMC input received","good","reviews","Opinions received");
    if(r.stage==="esc"&&bodyStatus(r,"ESC")==="done")add("ESC decision received","good","reviews","Opinions received");
    if(["wg","smc","esc"].includes(r.stage)&&due&&due<t){const late=bs.filter(b=>bodyStatus(r,b)!=="done");if(late.length)add(`Reply overdue since ${fmtD(due)} · ${late.join(", ")}`,"bad","reviews","Overdue")}
    if(approved(r)&&ARCH.includes(r.stage)&&!S.codes.has(r.ref))add("Authorised · issue the reporting code","info","reporting","Activity reports");
    {const rp=r.reporting||{},rs=reportsFor(r.ref);
     if(rp.finalDue&&rp.finalDue<t&&!rs.some(x=>x.type==="Final report"))add(`Final report overdue since ${fmtD(rp.finalDue)}`,"bad","reporting","Overdue");
     else if(rp.progressDue&&rp.progressDue<t&&!rs.length)add(`Progress update overdue since ${fmtD(rp.progressDue)}`,"warn","reporting","Overdue");}
    reportsFor(r.ref).filter(x=>!(x.review||{}).status).forEach(x=>add(`New ${x.type.toLowerCase()} received from ${x.name}`,"good","reporting","Activity reports"));
    if(r.stage==="decided"&&(r.decision||{}).notified!=="Yes")add("Decision recorded · notify the applicant","info","decision","Decide and notify");
  })}
  else if(role.role!=="none"){mine().filter(isOpen).forEach(r=>{const st=myState(r.ref),due=(r.assigned||{}).due;const late=due&&due<t;const hasDraft=myOps(r.ref).some(o=>o.status!=="submitted");
    if(st==="todo")out.push({r,why:due?`Opinion to give · reply by ${fmtD(due)}`:"Opinion to give",tone:late?"bad":"info",tab:"submission",group:late?"Overdue":"To review"});
    else if(hasDraft)out.push({r,why:"Draft review not submitted",tone:late?"bad":"warn",tab:"submission",group:late?"Overdue":"Drafts to finish"});
  })}
  return out;
}
function taskRows(list,attr){return list.map(x=>`<button type="button" class="task t-${x.tone}" ${attr}="${esc(x.r.ref)}" data-tab="${x.tab}"><i class="dot"></i><span class="tk-main"><b>${esc(x.why)}</b><span>${esc(x.r.sub.title)} · ${esc(x.r.ref)}</span></span><span class="tk-go">${icon("chevron")}</span></button>`).join("")}
function groupedTasks(attr){const ts=tasks(),groups=TASK_GROUPS[isSec()?"sec":"rev"];
  return groups.map(g=>{const l=ts.filter(x=>x.group===g);return l.length?`<div class="tgroup"><div class="tg-head"><span>${g}</span><span class="num">${l.length}</span></div>${taskRows(l,attr)}</div>`:""}).join("")}
function tasksCard(){if(S.preview)return"";const n=tasks().length;
  return`<div class="glass card tasks-card"><div class="card-head"><h2>${icon("bell")}Your pending tasks</h2>${n?`<span class="badge num">${n}</span>`:pill("All clear","good")}</div>
  ${n?`<p class="muted" style="font-size:13px;margin:-4px 0 8px">Select a task to open the request at the right place.</p>${groupedTasks("data-open")}`:`<p class="empty">Nothing is waiting for you${actor()?", "+esc(actor().split(" ")[0]):""}.</p>`}</div>`}
function tasksSheet(){const n=tasks().length;
  openSheet(`<div class="card-head"><h2>${n?`${n} pending task${n>1?"s":""}`:"No pending task"}</h2><button class="btn sm" data-act="closesheet">Close</button></div>
  ${actor()?`<p class="muted" style="font-size:13.5px;margin-bottom:10px">Welcome, ${esc(actor())}. Select a task to open it.</p>`:""}
  ${n?groupedTasks("data-task"):`<p class="empty">Nothing is waiting for you at the moment.</p>`}`,"tasks")}
function maybeShowTasks(){if(S.tasksShown||!S.gotReq||!S.gotRev||!actor()||S.sheet||S.preview)return;const r=roleNow().role;if(r==="none")return;S.tasksShown=true;if(tasks().length)tasksSheet()}

/* ---------------- Secretariat: overview ---------------- */
function viewOverview(){
  const all=[...S.requests.values()];const open=all.filter(isOpen);
  const withRev=all.filter(r=>["wg","smc","esc"].includes(r.stage)).length;
  const hold=all.filter(r=>r.stage==="applicant").length;
  const late=open.filter(r=>r.stage!=="applicant"&&(workdays(r.receivedAt)||0)>CFG.target&&(r.assess||{}).level!=="Level 2"&&(r.assess||{}).level!=="Level 3").length;
  const flow=CFG.stages.map(s=>{const n=all.filter(r=>r.stage===s.k).length;return`<button type="button" class="${n?"has":""}" data-flow="${s.k}"><b class="num">${n}</b><span>${s.l}</span></button>`}).join("");
  const act=[];
  all.forEach(r=>{
    if(r.stage==="received")act.push([r,"New request to screen","info"]);
    if(r.stage==="wg"){const bs=(r.assigned||{}).bodies||[];const done=bs.filter(b=>/^WG/.test(b)&&bodyStatus(r,b)==="done");if(bs.some(b=>/^WG/.test(b))&&done.length===bs.filter(b=>/^WG/.test(b)).length)act.push([r,"All Working Group opinions in","good"])}
    if(r.stage==="smc"&&bodyStatus(r,"SMC")==="done")act.push([r,"SMC input received","good"]);
    if(r.stage==="esc"&&bodyStatus(r,"ESC")==="done")act.push([r,"ESC decision received","good"]);
    if(r.stage==="screening"&&!((r.assigned||{}).bodies||[]).length&&(r.consult||[]).length&&gateOutcome(r)==="PASS")act.push([r,"Ready to send to "+r.consult.join(", "),"info"]);
    if(r.stage==="screening"&&gateOutcome(r)==="HOLD")act.push([r,"Hard gate to verify with the applicant","warn"]);
  });
  const feed=allOpinions();
  feed.sort((a,b)=>String(b.updatedAt).localeCompare(String(a.updatedAt)));
  return previewBanner()+head("UNESCO Secretariat","Overview",`Requests to use the logo of the Decade, live.`,`<button class="btn tint" data-act="newreq">${icon("plus")}New request</button><button class="btn primary" data-go="pipeline">Open pipeline</button>`)+
  `<div class="grid g4">
    <div class="glass stat"><div class="l">Open requests</div><div class="v num">${open.length}</div><div class="s">of ${all.length} received</div></div>
    <div class="glass stat"><div class="l">With reviewers</div><div class="v num">${withRev}</div><div class="s">Working Groups, SMC or ESC</div></div>
    <div class="glass stat"><div class="l">Awaiting applicant</div><div class="v num">${hold}</div><div class="s">timeline suspended</div></div>
    <div class="glass stat"><div class="l">Beyond 40 working days</div><div class="v num" style="color:${late?"var(--bad)":"inherit"}">${late}</div><div class="s">open Level 1 requests</div></div>
  </div>
  <div class="glass card"><div class="card-head"><h2>Where requests stand</h2><span class="muted" style="font-size:13px">Select a stage to open it</span></div><div class="flow">${flow}</div></div>
  <div class="grid g1">
    <div class="glass card feed"><div class="card-head"><h2>Reviewer activity</h2><span class="live"><i></i>Live</span></div>
      <div class="list">${feed.length?feed.slice(0,10).map(f=>{const r=S.requests.get(f.ref);return`<button type="button" class="item" data-open="${esc(f.ref)}" data-tab="reviews"><img src="${esc(av(f.uid))}" alt=""><span class="it-title">${f.reviewer?esc(f.reviewer)+" · ":""}${esc(f.label||f.body)} ${f.status==="submitted"?"submitted":"is drafting"} ${f.opinion?"<b>"+esc(f.opinion)+"</b>":"an opinion"}</span><span class="it-meta">${esc(r?r.sub.title:f.ref)} · ${fmtDT(f.updatedAt)}</span><span class="it-side">${f.status==="submitted"?pill("Submitted","good"):pill("Draft","warn")}</span></button>`}).join(""):`<p class="empty">Opinions from the Working Groups, the SMC and the ESC appear here as they are written.</p>`}</div></div>
  </div>`;
}

/* ---------------- Secretariat: pipeline ---------------- */
function tile(r){
  const s=score(r),g=gateOutcome(r),bs=((r.assigned||{}).bodies)||[];
  return`<button type="button" class="tile ${(r.decision||{}).final==="Refused"?"refused":""}" draggable="true" data-open="${esc(r.ref)}" data-drag="${esc(r.ref)}">
    <span class="ref">${esc(r.ref)}${approved(r)?`<i class="mini-seal" title="Authorised">${icon("tick")}</i>`:""}</span><span class="t">${esc(r.sub.title)}</span><span class="o">${esc(r.sub.organisation)}${r.sub.country?" · "+esc(r.sub.country):""}</span>
    <span class="foot">${(r.assess||{}).level?pill(r.assess.level.replace("Level ","L"),""):""}${g==="HOLD"?pill("Gate","warn"):g==="BLOCK"?pill("Gate","bad"):""}${s!==null?`<span class="pill num">${s.toFixed(2)}</span>`:""}
    ${bs.length?`<span class="dots" title="${esc(bs.map(b=>b+": "+(bodyStatus(r,b)==="done"?"submitted":bodyStatus(r,b)==="draft"?"drafting":"waiting")).join(", "))}">${bs.map(b=>`<i class="${bodyStatus(r,b)}"></i>`).join("")}</span>`:""}</span></button>`;
}
function viewPipeline(){
  const all=[...S.requests.values()].filter(filterQ);
  return head("UNESCO Secretariat","Pipeline","Drag a card to move it; open it to work on it.",`<div class="search">${icon("search")}<input class="input" type="search" id="q" placeholder="Search requests" value="${esc(S.q)}" aria-label="Search requests"></div><button class="btn tint" data-act="newreq">${icon("plus")}New request</button>`)+
  `<div class="board" id="board">${CFG.stages.map(s=>{const rs=all.filter(r=>r.stage===s.k).sort((a,b)=>a.formId-b.formId);return`<section class="col" data-col="${s.k}" aria-label="${esc(s.l)}"><div class="col-head"><b>${esc(s.l)}</b><span class="num">${rs.length}</span></div>${rs.map(tile).join("")||`<p class="muted" style="font-size:12.5px;padding:4px 6px">No request</p>`}</section>`}).join("")}</div>`;
}
function filterQ(r){const q=S.q.trim().toLowerCase();return!q||[r.ref,r.sub.title,r.sub.organisation,r.sub.country,r.sub.typeOfUse].join(" ").toLowerCase().includes(q)}

/* ---------------- Secretariat: all requests ---------------- */
function viewRequests(){
  const rows=[...S.requests.values()].filter(filterQ).filter(r=>!S.stageFilter||r.stage===S.stageFilter).sort((a,b)=>a.formId-b.formId);
  return head("UNESCO Secretariat","All requests",`${S.requests.size} requests in the register.`,`<button class="btn" data-act="export">${icon("download")}Download summary</button><button class="btn tint" data-act="newreq">${icon("plus")}New request</button>`)+
  `<div class="row"><div class="search">${icon("search")}<input class="input" type="search" id="q" placeholder="Search title, organisation, country" value="${esc(S.q)}" aria-label="Search"></div>
   <select class="input" id="stageFilter" style="width:auto" aria-label="Stage"><option value="">All stages</option>${CFG.stages.map(s=>`<option value="${s.k}" ${S.stageFilter===s.k?"selected":""}>${esc(s.l)}</option>`).join("")}</select></div>
  <div class="glass table-wrap"><table><thead><tr><th>Request</th><th>Stage</th><th>Level</th><th>Gates</th><th>Score</th><th>First screening</th><th>Reviewers</th><th>Decision</th><th>Working days</th></tr></thead><tbody>
  ${rows.map(r=>{const g=gateOutcome(r),s=score(r),rc=reco(r),bs=((r.assigned||{}).bodies)||[],wd=workdays(r.receivedAt,["decided","notified","closed"].includes(r.stage)?(r.decision||{}).date||null:null);
    return`<tr class="click" data-open="${esc(r.ref)}"><td><div class="t">${esc(r.sub.title)}</div><div class="o">${esc(r.ref)} · ${esc(r.sub.organisation)}</div></td>
    <td>${pill(CFG.stages[STAGE_IDX[r.stage]||0].l,r.stage==="applicant"?"warn":["decided","notified","closed"].includes(r.stage)?"good":"info")}</td>
    <td>${esc((r.assess||{}).level||"–")}</td><td>${g?pill(g,g==="PASS"?"good":g==="HOLD"?"warn":"bad"):"–"}</td><td class="num">${s!==null?s.toFixed(2):"–"}</td><td>${rc?pill(rc.l,rc.t):"–"}</td>
    <td>${bs.length?`<span class="dots" style="margin:0">${bs.map(b=>`<i class="${bodyStatus(r,b)}" title="${b}"></i>`).join("")}</span> <span class="o">${bs.join(", ")}</span>`:"–"}</td>
    <td>${esc((r.decision||{}).final||"Pending")}</td><td class="num">${wd!==null?wd:"–"}</td></tr>`}).join("")||`<tr><td colspan="9" class="empty">No request matches.</td></tr>`}
  </tbody></table></div>`;
}

/* ---------------- reviewers ---------------- */
function mine(){const b=roleNow().body;if(!b||roleNow().role==="secretariat")return[];return[...S.requests.values()].filter(r=>(((r.assigned||{}).bodies)||[]).includes(b)).sort((a,b2)=>a.formId-b2.formId)}
function myOps(ref){if(S.preview)return[];const d=S.reviews.get(S.uid),b=roleNow().body;return Object.entries((d&&d.opinions)||{}).filter(([,o])=>o&&o.ref===ref&&o.body===b).map(([key,o])=>Object.assign({key,uid:S.uid},o)).sort((a,c)=>String(a.createdAt||a.updatedAt).localeCompare(String(c.createdAt||c.updatedAt)))}
function myState(ref){const ops=myOps(ref);return ops.some(o=>o.status==="submitted")?"done":ops.length?"draft":"todo"}
function viewMine(){
  const rs=mine(),role=roleNow();
  const todo=rs.filter(r=>myState(r.ref)!=="done"&&isOpen(r));
  return previewBanner()+tasksCard()+head(esc(CFG.bodyName[role.body]||role.body),"My dossiers",`Read the assessment, then give your ${role.role==="wg"?"opinion":role.role==="smc"?"decision or recommendation":"decision"}.`)+
  `<div class="glass card pmap-card"><div class="card-head"><h2>Your part in the process</h2>${pill("Step 4 · Opinions","info")}</div>${processMap(3)}</div>`+
  `<div class="grid g3"><div class="glass stat"><div class="l">Assigned</div><div class="v num">${rs.length}</div></div><div class="glass stat"><div class="l">Waiting for you</div><div class="v num" style="color:${todo.length?"var(--accent)":"inherit"}">${todo.length}</div></div><div class="glass stat"><div class="l">Submitted</div><div class="v num">${rs.length-todo.length}</div></div></div>
  <div class="glass card"><div class="list">${rs.length?rs.map(r=>{const ops=myOps(r.ref),st=myState(r.ref),n=ops.filter(o=>o.status==="submitted").length,due=(r.assigned||{}).due;return`<button type="button" class="item" data-open="${esc(r.ref)}"><span class="it-title">${esc(r.sub.title)}</span><span class="it-meta">${esc(r.ref)} · ${esc(r.sub.organisation)} · ${esc((r.assess||{}).level||"")}${due?" · reply by "+fmtD(due):""}</span><span class="it-side">${st==="done"?pill(n+" review"+(n>1?"s":"")+" submitted","good"):""}${ops.some(o=>o.status!=="submitted")?pill("Draft","warn"):""}${st==="todo"?pill("To do",due&&due<today()?"bad":"info"):""}</span></button>`}).join(""):`<p class="empty">No dossier is assigned to ${esc(role.body)} at the moment.</p>`}</div></div>`;
}
function viewWelcome(){
  return head("Logo Authorisation Platform","Welcome",`You are signed in as ${esc(S.account||"")}, but this account has no role yet.`)+
  `<div class="glass card"><h2>What happens next</h2><p class="sub" style="margin-top:8px">Logo review access is granted by the UNESCO Secretariat, member by member, for Working Groups 1 to 5, the SMC or the ESC. Appointments in Governance do not grant it. Ask the UNESCO Secretariat at cryosphere@unesco.org if you need it.</p><div class="row" style="margin-top:16px"><button class="btn" data-act="logout">Sign out</button></div></div>`;
}

/* ---------------- detail ---------------- */
function viewDetail(r){
  const sec=isSec(),ro=!sec||!!S.preview,role=roleNow();
  const idx=STAGE_IDX[r.stage]||0;const lvl=(r.assess||{}).level;
  const assigned=!sec&&mine().some(x=>x.ref===r.ref),decided=ARCH.includes(r.stage);
  const tabs=sec?[["submission","Submission"],["screening","Screening"],["assessment","Assessment"],["reviews","Reviews"],["decision","Decision"],["reporting","Reporting"],["history","History"]]:[["submission","Submission"],["assessment","Assessment"],["reviews",decided?"Reviews":"Opinions"],...(decided?[["decision","Decision"]]:[])];
  if(!tabs.some(t=>t[0]===S.tab))S.tab=tabs[0][0];
  const next=nextStep(r);
  return`${previewBanner()}<div class="glass dhead ${(r.decision||{}).final==="Refused"?"refused":""}">
    <div class="dtop"><div><button type="button" class="back" data-go="${S.from==="archive"?"archive":sec?"pipeline":"mine"}">${icon("chevron").replace('<svg','<svg style="width:18px;height:18px"')}${S.from==="archive"?"Decision history":sec?"Pipeline":"My dossiers"}</button>
      <h1 class="dtitle">${esc(r.sub.title)}</h1><p class="dmeta">${esc(r.ref)} · ${esc(r.sub.organisation)}${r.sub.country?" · "+esc(r.sub.country):""}${r.sub.typeOfUse?" · "+esc(r.sub.typeOfUse):""} · received ${fmtD(r.receivedAt)}</p></div>
      ${sec&&!S.preview?`<div class="row" style="align-items:flex-end"><label class="field" style="min-width:200px"><span>Stage</span><select class="input" id="stageSel">${CFG.stages.map(s=>`<option value="${s.k}" ${s.k===r.stage?"selected":""}>${esc(s.l)}</option>`).join("")}</select></label>${next?`<button class="btn primary" data-act="next" data-ref="${esc(r.ref)}">${esc(next.l)}</button>`:""}<button class="btn danger" data-act="delreq" data-ref="${esc(r.ref)}">Delete</button></div>`:`<div>${pill(CFG.stages[idx].l,"info")}</div>`}</div>
    ${processMap(STEP_OF[r.stage]??0,{compact:true,paused:r.stage==="applicant"})}
    <div class="tabs" role="tablist">${tabs.map(([k,l])=>{const b=tabBadge(k,r);return`<button type="button" role="tab" data-tab="${k}" aria-pressed="${S.tab===k}">${icon(TAB_ICON[k]||"list")}<span>${l}</span>${b}</button>`}).join("")}</div>
  </div>
  <div class="dgrid"><div class="stack">${({submission:tabSubmission,screening:tabScreening,assessment:tabAssessment,reviews:tabReviews,decision:tabDecision,reporting:tabReporting,history:tabHistory})[S.tab](r,ro)}</div>
  <aside class="stack stick">${sealCard(r)}${sec?assignCard(r,ro):assigned&&!decided?composer(r):decisionSummary(r)}${scoreCard(r)}${timelineCard(r)}</aside></div>`;
}
/* A seal with the logo of the Decade on decided requests; it is stamped when the decision is recorded in this session. */
function seal(r,size){const d=r.decision||{},ok=/^Approved/.test(d.final||""),no=d.final==="Refused";if(!ok&&!no)return"";
  const fresh=S.stamp===r.ref&&Date.now()-(S.stampAt||0)<2500,ring=(ok?(d.final==="Approved"?"AUTHORISED":"AUTHORISED WITH CONDITIONS"):"REFUSED")+" · DECADE OF ACTION FOR CRYOSPHERIC SCIENCES · ";
  return`<div class="seal ${ok?"ok":"no"} ${size||""} ${fresh?"stamp":""}" role="img" aria-label="${ok?"Authorised":"Refused"}${d.date?" on "+fmtD(d.date):""}"><svg viewBox="0 0 120 120" aria-hidden="true"><defs><path id="seal-${esc(r.ref)}" d="M60,60 m-45,0 a45,45 0 1,1 90,0 a45,45 0 1,1 -90,0"/></defs><circle cx="60" cy="60" r="57" class="s-out"/><circle cx="60" cy="60" r="36" class="s-in"/><text class="s-ring"><textPath href="#seal-${esc(r.ref)}" textLength="276">${ring}</textPath></text></svg><span class="s-core"><img src="assets/img/favicon.png" alt=""><small>${esc(d.date?fmtD(d.date):"")}</small></span></div>`}
function sealCard(r){const d=r.decision||{},s=seal(r);if(!s)return"";const ok=/^Approved/.test(d.final||"");
  return`<div class="glass card seal-card ${ok?"ok":"no"}">${s}<div><h3>${esc(d.final)}</h3><p class="muted" style="font-size:13px">${d.until?`Authorised until ${fmtD(d.until)}`:ok?"Set an expiry date in Decision.":"The applicant is informed of the refusal."}</p></div></div>`}
const TAB_ICON={submission:"report",screening:"shield",assessment:"scale",reviews:"users",decision:"check",reporting:"bell",history:"archive"};
/* A small state mark on each tab: done, to look at, or a count. */
function tabBadge(k,r){
  if(k==="screening"){const g=gateOutcome(r);return g==="PASS"?`<i class="tb good">${icon("tick")}</i>`:g?`<i class="tb ${g==="BLOCK"?"bad":"warn"}">!</i>`:""}
  if(k==="assessment"){const n=scored(r);return n===6?`<i class="tb good">${icon("tick")}</i>`:n?`<i class="tb num">${n}/6</i>`:""}
  if(k==="reviews"){const n=opinionsFor(r.ref).filter(o=>o.status==="submitted").length;return n?`<i class="tb num">${n}</i>`:""}
  if(k==="decision"){const d=(r.decision||{}).final;return d&&d!=="Pending"?`<i class="tb ${/^Approved/.test(d)?"good":"bad"}">${icon("tick")}</i>`:""}
  return"";
}
function nextStep(r){
  const lvl=(r.assess||{}).level,bs=((r.assigned||{}).bodies)||[];
  switch(r.stage){
    case"received":return{l:"Start screening",to:"screening"};
    case"screening":return(r.consult||[]).length?{l:"Send to "+r.consult.join(", "),to:"wg",assign:r.consult}:lvl==="Level 2"||lvl==="Level 3"?{l:"Send to SMC",to:"smc",assign:["SMC"]}:{l:"Record decision",to:"decided"};
    case"applicant":return{l:"Applicant replied",to:"screening"};
    case"wg":return lvl==="Level 2"||lvl==="Level 3"?{l:"Send to SMC",to:"smc",assign:["SMC"]}:{l:"Record decision",to:"decided"};
    case"smc":return lvl==="Level 3"?{l:"Send to ESC",to:"esc",assign:["ESC"]}:{l:"Record decision",to:"decided"};
    case"esc":return{l:"Record decision",to:"decided"};
    case"decided":return{l:"Mark notified",to:"notified"};
    case"notified":return{l:"Close",to:"closed"};
  }return null;
}
async function moveStage(ref,to,assign){
  const r=S.requests.get(ref);if(!r||r.stage===to&&!assign)return;
  const patch={stage:to};let what=`Moved to ${CFG.stages[STAGE_IDX[to]].l}`;
  if(assign&&assign.length){const bs=[...new Set([...(((r.assigned||{}).bodies)||[]),...assign])];patch.assigned={bodies:bs,due:((r.assigned||{}).due)||addWd(today(),10)};what+=`; assigned to ${assign.join(", ")}`;if(to==="wg")patch.wgSentAt=today()}
  if(to==="decided"&&(!r.decision||r.decision.final==="Pending")){S.tab="decision"}
  if(to==="notified")patch.decision={notified:"Yes"};
  await saveReq(ref,patch,what);toast(what+".");
}
function tabSubmission(r,ro){const s=r.sub,c=S.contacts.get(r.ref);
  if(S.editSub&&isSec()&&!ro)return subEditor(r,c);
  return`<div class="glass card"><div class="card-head"><h2>Submission</h2>${isSec()&&!ro?`<button class="btn sm tint" data-act="editsub">Edit submission</button>`:`<span class="muted" style="font-size:13px">as sent by the applicant</span>`}</div>
  <dl class="kv">${isSec()&&c?`<dt>Applicant</dt><dd>${esc(c.applicant)}${c.email?` · <span style="user-select:all">${esc(c.email)}</span>`:""}</dd>`:""}
  <dt>Level requested</dt><dd>${esc(s.levelRequested||"Not stated")}</dd><dt>Main goals declared</dt><dd>${esc(s.mgsDeclared)}</dd><dt>Where the logo will appear</dt><dd>${esc(s.placements)}</dd>
  <dt>Start of use</dt><dd>${fmtD(s.startOfUse)}</dd><dt>Link</dt><dd>${/^https?:\/\//.test(s.url||"")?`<a href="${esc(s.url.split(/\s/)[0])}" target="_blank" rel="noopener noreferrer">${esc(s.url)}</a>`:esc(s.url)||"–"}</dd>
  <dt>Non-commercial</dt><dd>${esc(s.nonCommercial)}</dd><dt>Reuse limitation</dt><dd>${esc(s.reuseLimitation)||"None stated"}</dd><dt>Standards</dt><dd>${esc(s.standards)}</dd><dt>Accuracy</dt><dd>${esc(s.accuracy)}</dd></dl></div>
  <div class="glass card"><h3>Description</h3><div class="quote" style="margin-top:10px">${esc(s.description)}</div><h3 style="margin-top:18px">Contribution to the Decade</h3><div class="quote" style="margin-top:10px">${esc(s.link)}</div></div>`}
function subEditor(r,c){const T=(p,l,t,o)=>fld(r,p,l,t||"text",o||{},false);c=c||{};
  return`<div class="glass card"><div class="card-head"><h2>Edit submission</h2><button class="btn sm primary" data-act="editsub">Done</button></div>
  <div class="grid g2">${T("sub.title","Activity title")}${T("sub.organisation","Organisation")}${T("sub.country","Country")}${T("sub.typeOfUse","Type of use")}
  <label class="field"><span>Applicant</span><input class="input" type="text" data-contact="applicant" value="${esc(c.applicant||"")}"></label><label class="field"><span>Applicant email</span><input class="input" type="text" data-contact="email" value="${esc(c.email||"")}"></label>
  ${T("sub.levelRequested","Level requested","select",{list:["Not stated","Level 1","Level 2","Level 3"],blank:false})}${T("receivedAt","Date received","date")}
  ${T("sub.mgsDeclared","Main goals declared")}${T("sub.placements","Where the logo will appear")}${T("sub.startOfUse","Start of use","date")}${T("sub.url","Link")}
  ${T("sub.nonCommercial","Non-commercial")}${T("sub.reuseLimitation","Reuse limitation")}</div>
  <div class="stack" style="gap:16px;margin-top:16px">${T("sub.description","Description","textarea",{rows:6})}${T("sub.link","Contribution to the Decade","textarea",{rows:4})}</div>
  <div class="row" style="margin-top:22px;padding-top:18px;border-top:1px solid var(--line)"><span class="muted" style="font-size:13px">Changes are saved as you type.</span><span class="spacer"></span><button class="btn danger" data-act="delreq" data-ref="${esc(r.ref)}">Delete this request</button></div></div>`}
function seg(attr,key,opts,val,ro,cls){return`<div class="seg ${cls||""}" role="group">${opts.map(o=>`<button type="button" ${attr}="${key}" data-v="${esc(o)}" aria-pressed="${String(val)===String(o)}" ${ro?"disabled":""}>${esc(o)}</button>`).join("")}</div>`}
function fld(r,path,label,type,opt,ro){const v=path.split(".").reduce((a,k)=>a==null?a:a[k],r)??"";const dis=ro?"disabled":"";
  if(type==="select")return`<label class="field"><span>${label}</span><select class="input" data-bind="${path}" ${dis}>${(opt.blank===false?"":`<option value="">–</option>`)+opt.list.map(o=>`<option ${o===v?"selected":""}>${esc(o)}</option>`).join("")}</select>${opt.hint?`<small>${opt.hint}</small>`:""}</label>`;
  if(type==="textarea")return`<label class="field"><span>${label}</span><textarea class="input" data-bind="${path}" rows="${opt.rows||4}" ${dis}>${esc(v)}</textarea>${opt.hint?`<small>${opt.hint}</small>`:""}</label>`;
  return`<label class="field"><span>${label}</span><input class="input" type="${type}" data-bind="${path}" value="${esc(v)}" ${dis}>${opt&&opt.hint?`<small>${opt.hint}</small>`:""}</label>`}
function assessedBy(r){const a=r.assess||{};const names=[...new Set([...(a.assessors||[]),...((r.follow||{}).reviewerName?[r.follow.reviewerName]:[])])];
  return`<div class="assessor">${icon("user")}<span>${names.length?`Assessed by <b>${names.map(esc).join(", ")}</b>${a.assessedBy?` · last change by ${esc(a.assessedBy)}${a.assessedAt?", "+fmtDT(a.assessedAt):""}`:""}`:"No assessment recorded yet. Your name is recorded with your first change."}</span></div>`}
function tabScreening(r,ro){const g=gateOutcome(r),sc=r.screen||{};
  const V={PASS:["good","shield","All gates cleared","The assessment can go ahead."],HOLD:["warn","pause","A gate is to verify","The assessment is suspended until the applicant replies."],BLOCK:["bad","alert","A gate is triggered","The request is refused, whatever its merits."]}[g]||["","shield","Gates not yet checked","Answer the four questions below."];
  return`<div class="glass card"><div class="verdict ${V[0]}"><span class="v-icon">${icon(V[1])}</span><span><b>${V[2]}</b><small>${V[3]}</small></span></div>
  ${assessedBy(r)}<div class="grid g3">${fld(r,"screen.acknowledged","Acknowledged","select",{list:["Yes","No"]},ro)}${fld(r,"screen.completeness","Submission complete?","select",{list:["Complete","Partial","Incomplete"],hint:"Including the signed commitment letter"},ro)}</div></div>
  <div class="glass card"><div class="card-head"><h2>Hard gates</h2><span class="legend"><span class="lg good">No</span><span class="lg warn">To verify · suspends</span><span class="lg bad">Yes · refuses</span></span></div>
  ${CFG.gates.map((x,i)=>{const v=(sc.gates||{})[x.k];return`<div class="gate ${v==="No"?"is-good":v==="Yes"?"is-bad":v==="To verify"?"is-warn":""}"><span class="gate-n num">${i+1}</span><div class="gate-t"><b>${esc(x.t)}</b>${more(x.r)}</div>${seg("data-gate",x.k,["No","To verify","Yes"],v,ro,"seg-gate")}</div>`}).join("")}</div>`}
function tabAssessment(r,ro){const a=r.assess||{},L=CFG.levels[a.level],decl=(r.sub.mgsDeclared||"").match(/MG[1-5]\.[1-3]/g)||[];const sec=isSec();
  const asked=r.sub.levelRequested&&r.sub.levelRequested!=="Not stated"?r.sub.levelRequested:"";
  return`<div class="glass card"><div class="card-head"><h2>Level</h2>${asked?`<span class="muted" style="font-size:13px">Requested: ${esc(asked)} · not binding</span>`:""}</div>${assessedBy(r)}
  <div class="levels">${Object.entries(CFG.levels).map(([k,X])=>`<button type="button" class="level-card ${a.level===k?"on":""}" data-level="${k}" aria-pressed="${a.level===k}" ${ro?"disabled":""}><span class="lv-n">${k.replace("Level ","")}</span><span class="lv-name">${esc(X.name)}${asked===k?` <em>requested</em>`:""}</span><span class="lv-marks">${esc(X.marks)}</span>${chainChips(X)}</button>`).join("")}</div>
  ${L?`<p class="muted lv-note">${esc(L.period)}${L.clearance?" "+esc(L.clearance):""}</p>`:""}
  </div>
  <div class="glass card"><div class="card-head"><h2>Main goals</h2><span class="muted" style="font-size:13px">${decl.length?`Declared: ${decl.join(", ")}`:"None declared by the applicant"}</span></div>
  <div style="max-width:340px;margin-bottom:14px">${fld(r,"assess.primaryOC","Primary overarching challenge","select",{list:Object.keys(CFG.ocs)},ro)}</div>
  <div class="mg-grid">${[1,2,3,4,5].map(n=>`<div class="mg-row" style="--oc:${OC_COLOR[n]}"><span class="mg-oc">OC${n}</span>${[1,2,3].map(m=>{const k=`MG${n}.${m}`;return`<button type="button" class="chip mg-chip" data-mg="${k}" aria-pressed="${(a.mgs||[]).includes(k)}" title="${esc(CFG.mgs[k])}" ${ro?"disabled":""}>${k}${decl.includes(k)?`<i class="decl" title="Declared by the applicant"></i>`:""}</button>`}).join("")}</div>`).join("")}</div>
  ${sec?`<h3 style="margin-top:18px">Working Groups to consult</h3><div class="chips" style="margin-top:10px">${Object.keys(CFG.wgs).map(k=>`<button type="button" class="chip" data-consult="${k}" aria-pressed="${(r.consult||[]).includes(k)}" title="${esc(CFG.wgs[k])}" ${ro?"disabled":""}>${k}</button>`).join("")}</div><div class="suggest muted"><span>Suggested from the main goals: <b>${[...new Set((a.mgs||[]).map(m=>"WG"+m[2]))].join(", ")||"none yet"}</b></span>${more("MG5.2 and MG5.3 alone: consult WG5 only if borderline, high-profile, or a gate is on hold.")}</div>`:""}</div>
  <div class="glass card"><div class="card-head"><h2>Six weighted criteria</h2><span class="legend">${CFG.scale.map((x,i)=>i===1?"":`<span class="lg"><b class="num">${i}</b> ${x.toLowerCase()}</span>`).join("")}</span></div>
  ${CFG.criteria.map((c,i)=>{const v=(a.scores||{})[c.k];return`<div class="crit ${v!==undefined&&v!==null&&v!==""?"scored":""}"><span class="crit-n num">${i+1}</span><div class="crit-t"><b>${esc(c.t)}</b><span class="wbar-wrap" title="Weight in the score"><span class="wbar"><i style="width:${c.w*400}%"></i></span><em class="num">${Math.round(c.w*100)}%</em></span>${more(c.m)}</div>${seg("data-score",c.k,[0,1,2,3,4,5],v,ro,"score")}</div>`}).join("")}
  <div style="margin-top:14px">${fld(r,"assess.notes","Secretariat notes","textarea",{rows:6,hint:sec?"Reasoning, and the reason for any departure from the band.":""},ro)}</div></div>`}
function opinionHTML(o){const t=/not|Do not/i.test(o.opinion||"")?"bad":/conditions/i.test(o.opinion||"")?"info":/Defer|Not for/i.test(o.opinion||"")?"":"good";
  return`<div class="op"><div class="op-head">${av(o.uid)?`<img src="${esc(av(o.uid))}" alt="">`:""}<b>${esc(o.reviewer||o.label||o.body)}</b><span class="muted">${esc(o.reviewer?(o.label||o.body):nm(o.uid))}</span>${o.opinion?pill(o.opinion,t):""}${o.status==="submitted"?pill("Submitted "+fmtDT(o.submittedAt||o.updatedAt),"",false):`<span class="live"><i></i>Drafting · ${fmtDT(o.updatedAt)}</span>`}</div>${o.text?`<p>${esc(o.text)}</p>`:""}${o.conditions?`<p class="muted"><b>Conditions proposed:</b> ${esc(o.conditions)}</p>`:""}${isSec()&&!S.preview?`<div><button type="button" class="x" data-act="delop" data-uid="${esc(o.uid)}" data-key="${esc(o.key)}">Delete this opinion</button></div>`:""}</div>`}
function tabReviews(r,ro){const sec=isSec(),dec=ARCH.includes(r.stage);let ops=opinionsFor(r.ref);if(!sec)ops=ops.filter(o=>o.status==="submitted"&&(dec||o.uid!==S.uid));
  const bs=((r.assigned||{}).bodies)||[];
  return`<div class="glass card"><div class="card-head"><h2>${sec?"Opinions and decisions":dec?"Reviews given":"Opinions of other bodies"}</h2><span class="live"><i></i>Live</span></div>
  ${sec&&bs.length?`<div class="chips" style="margin-bottom:14px">${bs.map(b=>{const st=bodyStatus(r,b);return pill(b+": "+(st==="done"?"submitted":st==="draft"?"drafting":"waiting"),st==="done"?"good":st==="draft"?"warn":"")}).join("")}</div>`:""}
  <div class="stack" style="gap:10px">${ops.length?ops.map(opinionHTML).join(""):`<p class="empty">${sec?"No opinion yet. Assign the request to a body from the panel on the right.":dec?"No review was recorded for this request.":"No other body has submitted an opinion yet."}</p>`}</div>
  ${sec&&!ro?applyBox(r,ops):""}</div>`}
function applyBox(r,ops){const lvl=(r.assess||{}).level;const body=lvl==="Level 2"?"SMC":lvl==="Level 3"?"ESC":null;if(!body)return"";const o=ops.find(x=>x.body===body&&x.status==="submitted"&&CFG.decisionMap[x.opinion]);if(!o)return"";
  return`<div class="banner info" style="margin-top:14px">At ${esc(lvl)} the ${body} decides. ${esc(o.reviewer?o.reviewer+" ("+(o.label||o.body)+")":(o.label||o.body))} submitted <b>${esc(o.opinion)}</b>. <button class="btn sm primary" data-act="apply" data-ref="${esc(r.ref)}" data-uid="${esc(o.uid)}" data-key="${esc(o.key)}" style="margin-left:6px">Record as final decision</button></div>`}
function tabDecision(r,ro){const d=r.decision||{},L=CFG.levels[(r.assess||{}).level];const rc=reco(r);
  const warn=[];if(/^Approved/.test(d.final)&&!d.until)warn.push("Set an expiry date: no authorisation is open-ended.");if(/^Approved/.test(d.final)&&gateOutcome(r)!=="PASS")warn.push("The hard gates have not all been cleared.");if(d.from&&d.until&&d.until<d.from)warn.push("The authorisation ends before it starts.");
  if(rc&&d.final&&d.final!=="Pending"&&!((d.final==="Approved"&&rc.l==="Approve")||(d.final==="Approved with conditions"&&rc.l==="Approve with conditions")||(d.final==="Refused"&&/^Refuse/.test(rc.l))||d.final==="Withdrawn"))warn.push("This decision departs from the band of the weighted score: record the reason in the Secretariat notes.");
  return`<div class="glass card"><div class="card-head"><h2>Decision</h2>${L?`<span class="muted" style="font-size:13px">decided by ${esc(L.decides)}</span>`:""}</div>${d.recordedBy?`<div class="assessor">${icon("user")}<span>Decision recorded by <b>${esc(d.recordedBy)}</b></span></div>`:""}
  <div class="grid g3">${fld(r,"decision.final","Final decision","select",{list:CFG.decisions,blank:false},ro)}${fld(r,"decision.date","Decision date","date",{},ro)}${fld(r,"decision.notified","Applicant notified","select",{list:["Yes","No"]},ro)}${fld(r,"decision.from","Authorised from","date",{},ro)}${fld(r,"decision.until","Authorised until","date",{hint:"No authorisation is open-ended."},ro)}</div>
  ${warn.map(w=>`<div class="banner" style="margin-top:12px">${esc(w)}</div>`).join("")}
  <div style="margin-top:14px">${fld(r,"decision.conditions","Conditions attached","textarea",{rows:4,hint:r.sub.reuseLimitation?"The applicant asked to limit reuse: copy the limitation here.":""},ro)}</div></div>
  <div class="glass card"><h2>Follow-up</h2><div class="grid g2" style="margin-top:12px">${fld(r,"follow.owner","Owner","text",{},ro)}${fld(r,"follow.nextReview","Next review date","date",{},ro)}</div><div style="margin-top:12px">${fld(r,"follow.action","Follow-up action","textarea",{rows:3},ro)}</div></div>`}
function tabHistory(r,ro){const h=(r.history||[]).map((x,i)=>[x,i]).reverse();const can=isSec()&&!ro;
  return`<div class="glass card"><div class="card-head"><h2>History</h2>${can&&h.length?`<button class="btn sm danger" data-act="clearhist" data-ref="${esc(r.ref)}">Clear history</button>`:""}</div><ul class="hist">${h.map(([x,i])=>`<li><time>${fmtDT(x.at)}</time><span>${x.who?`<b>${esc(x.who)}</b> · `:x.by&&nm(x.by)?`<b>${esc(nm(x.by))}</b> · `:""}${esc(x.what)}</span>${can?`<button type="button" class="x" data-act="delhist" data-ref="${esc(r.ref)}" data-i="${i}" aria-label="Delete this entry">Delete</button>`:"<span></span>"}</li>`).join("")||"<li><span>No entry.</span></li>"}</ul></div>`}
function assignCard(r,ro){const bs=((r.assigned||{}).bodies)||[];const members=(b)=>[];
  return`<div class="glass card"><div class="card-head"><h3>Assigned to</h3>${bs.length?`<span class="muted num" style="font-size:12.5px">${bs.length} bod${bs.length>1?"ies":"y"}</span>`:""}</div>
  <div class="chips">${CFG.bodies.map(b=>`<button type="button" class="chip" data-assign="${b}" aria-pressed="${bs.includes(b)}" ${ro?"disabled":""}>${b}</button>`).join("")}</div>
  <p class="muted" style="font-size:12.5px;margin-top:10px">${bs.length?bs.map(b=>{const ms=members(b);return`${b}: ${ms.length?ms.map(esc).join(", "):"Hub reviewers"}`}).join("<br>"):"Assigned bodies see this request in their dossiers and can give their opinion live."}</p>
  <div style="margin-top:12px">${fld(r,"assigned.due","Reply requested by","date",{},ro)}</div></div>`}
function composer(r){const role=roleNow(),lvl=(r.assess||{}).level,dis=S.preview?"disabled":"";
  const title=role.role==="wg"?role.body+" opinions":role.role==="smc"?(lvl==="Level 3"?"SMC recommendations":"SMC decisions"):"ESC decisions";
  const guide=role.role==="wg"?(lvl==="Level 1"?"At Level 1 the Secretariat decides, with the concurrence of your Working Group.":"A written opinion on the claimed contribution to the main goals is required."):role.role==="smc"?"The SMC relies on the assessment of the Secretariat and the opinion of the Working Group.":"The ESC decides on the flagship designation, on the recommendation of the SMC.";
  const ops=myOps(r.ref),cur=currentOp(r),nSub=ops.filter(o=>o.status==="submitted").length;
  const list=ops.length?`<div class="myops">${ops.map(o=>`<button type="button" class="myop ${cur&&cur.key===o.key?"on":""}" data-act="editop" data-key="${esc(o.key)}"><span><b>${esc(o.reviewer||"Name not given")}</b><small>${o.status==="submitted"?"Submitted "+fmtDT(o.submittedAt||o.updatedAt):"Draft · "+fmtDT(o.updatedAt)}</small></span>${o.opinion?pill(o.opinion,o.status==="submitted"?"good":"warn"):pill("No opinion yet","")}</button>`).join("")}</div>`:"";
  let ed="";
  if(cur){const sub=cur.status==="submitted",lock=dis||(sub?"disabled":"");
    ed=`<div class="stack" id="composer" data-key="${esc(cur.key||"")}" style="gap:12px;margin-top:14px">
    <div class="card-head" style="margin:0"><h3 style="font-size:15px">${cur.key?(sub?"Submitted review":"Review in progress"):"New review"}</h3>${sub?pill("Submitted","good"):cur.key?pill("Draft · saved","warn"):""}</div>
    <label class="field"><span>Reviewer name <em class="req">required</em></span><input class="input" id="opRev" data-optext="reviewer" value="${esc(cur.reviewer||"")}" ${lock} maxlength="80" placeholder="Name of the person giving this review"></label>
    <div class="opts" role="group" aria-label="Opinion">${optionsFor(role.body,lvl).map(x=>`<button type="button" data-op="${esc(x)}" aria-pressed="${cur.opinion===x}" ${lock}>${esc(x)}</button>`).join("")}</div>
    <label class="field"><span>Written opinion</span><textarea class="input" id="opText" data-optext="text" rows="6" ${lock} placeholder="Reasons, in particular on the main goals retained">${esc(cur.text||"")}</textarea></label>
    <label class="field"><span>Conditions proposed</span><textarea class="input" id="opCond" data-optext="conditions" rows="2" ${lock}>${esc(cur.conditions||"")}</textarea></label>
    <div class="row">${sub?`<button class="btn" data-act="reopen" data-key="${esc(cur.key)}" ${dis}>Edit this review</button><span class="muted" style="font-size:12.5px">Submitted ${fmtDT(cur.submittedAt)}</span>`:`<button class="btn primary" data-act="submit" data-ref="${esc(r.ref)}" ${dis||(cur.opinion?"":"disabled")}>Submit to the Secretariat</button>${cur.key?`<button class="btn" data-act="discardop" data-key="${esc(cur.key)}" ${dis}>Discard draft</button>`:""}<span class="muted" style="font-size:12.5px">${cur.opinion?"Drafts are saved as you type.":"Choose an opinion to submit."}</span>`}</div></div>`;}
  const canAdd=!(cur&&!cur.key);
  return`<div class="glass card" style="border:1.5px solid var(--accent)"><div class="card-head"><h3>${esc(title)}</h3>${nSub?pill(nSub+" submitted","good"):ops.length?pill("Draft","warn"):pill("To do","info")}</div>
  <p class="muted" style="font-size:13px">${esc(guide)}</p>
  ${list}${ed}
  ${canAdd?`<button class="btn tint" data-act="newop" style="margin-top:14px;width:100%" ${dis}>${icon("plus")}Add ${ops.length?"another":"a"} review</button>`:""}</div>`}
function scoreCard(r){const s=score(r),g=gateOutcome(r),rc=reco(r),n=scored(r);
  return`<div class="glass card"><div class="card-head"><h3>Weighted score</h3><span class="muted num" style="font-size:12.5px">${n}/6 scored</span></div>
  <div class="score"><b class="num">${g==="BLOCK"?"–":s!==null?s.toFixed(2):"–"}</b><span>/ 5</span></div>
  <div class="meter" aria-hidden="true"><i></i><i></i><i></i><i></i>${s!==null?`<em style="left:${s/5*100}%"></em>`:""}</div><div class="scale num"><span>0</span><span>2</span><span>3</span><span>4</span><span>5</span></div>
  <div class="bands-mini"><span class="t-bad">Refuse</span><span class="t-warn">Revert</span><span class="t-info">Conditions</span><span class="t-good">Approve</span></div>
  <div style="margin-top:12px">${rc?pill(rc.l,rc.t,true):`<span class="muted" style="font-size:13px">${n?`${6-n} criteria left to score.`:"Score the six criteria."}</span>`}</div>
  <p class="muted" style="font-size:12px;margin-top:8px">A recommendation, not a decision.</p></div>`}
function timelineCard(r){if(!r.receivedAt)return"";const wd=workdays(r.receivedAt,["decided","notified","closed"].includes(r.stage)?(r.decision||{}).date||null:null);const t=today();let cum=0;
  const lvl1=(r.assess||{}).level!=="Level 2"&&(r.assess||{}).level!=="Level 3";
  const state=!isOpen(r)?pill("Decided",""):r.stage==="applicant"?pill("Suspended","warn"):lvl1&&wd>CFG.target?pill("Beyond target","bad"):lvl1&&wd>CFG.target-10?pill("Due soon","warn"):pill("On track","good");
  return`<div class="glass card"><div class="card-head"><h3>Timeline</h3>${state}</div><p style="font-size:14px"><b class="num">${wd}</b> working days since receipt${lvl1?` · target ${CFG.target}`:""}</p>
  <ul class="steps" style="margin-top:10px">${CFG.timeline.map(([l,d])=>{cum+=d;const due=addWd(r.receivedAt,cum);return`<li class="${due<=t?"past":""}"><i></i><span>${l}</span><span>${fmtD(due)}</span></li>`}).join("")}</ul></div>`}

/* ---------------- sign-in and accounts ---------------- */
function confirmSheet(title,text,act,data){openSheet(`<h2>${esc(title)}</h2><p class="sub" style="margin-top:8px">${text}</p><div class="row" style="justify-content:flex-end;margin-top:20px"><button class="btn" data-act="closesheet">Cancel</button><button class="btn primary" style="background:var(--bad);box-shadow:none" data-act="${act}" ${Object.entries(data||{}).map(([k,v])=>`data-${k}="${esc(v)}"`).join(" ")}>Delete</button></div>`,"confirm")}
async function removeOpinion(uid,key){const doc=S.reviews.get(uid);if(!doc)return;const ops=Object.assign({},doc.opinions||{});delete ops[key];await queued("reviews/"+uid,()=>S.db.doc("reviews/"+uid).set(Object.assign({},doc,{opinions:ops}))).catch(writeErr)}
async function deleteRequest(ref){
  const affected=[];S.reviews.forEach((doc,uid)=>{Object.entries((doc&&doc.opinions)||{}).forEach(([k,o])=>{if(o&&o.ref===ref)affected.push([uid,k])})});
  try{await queued("requests/"+ref,()=>S.db.doc("requests/"+ref).delete());await queued("contacts/"+ref,()=>S.db.doc("contacts/"+ref).delete());
    for(const [uid,k] of affected)await removeOpinion(uid,k);toast(ref+" deleted.");}catch(e){writeErr(e)}
}

/* ---------------- import & new request ---------------- */
function viewImport(){
  const p=S.pending;
  return head("UNESCO Secretariat","Add requests","Add the new responses of the Microsoft Form “Carry the Decade’s identity”, or enter a request by hand.",`<button class="btn tint" data-act="newreq">${icon("plus")}Enter a request by hand</button>`)+
  `<div class="glass card"><h2>Import the Form responses</h2><p class="sub" style="margin-top:6px">In Microsoft Forms, open <b>Responses → Open results in Excel</b>, download the workbook, then choose it here. Responses already in the register are recognised by their ID and left unchanged.</p>
  <div class="row" style="margin-top:14px"><label class="btn primary" for="formFile">${icon("import")}Choose the Excel file</label><input type="file" id="formFile" accept=".xlsx,.xls,.csv" class="sr"><span class="muted" style="font-size:13px" id="fileNote"></span></div>
  ${p?`<div class="table-wrap" style="margin-top:16px"><table><thead><tr><th>Form ID</th><th>Activity</th><th>Organisation</th><th>Received</th><th>In the register</th></tr></thead><tbody>${p.rows.map(x=>`<tr><td class="num">${x.formId}</td><td class="t">${esc(x.sub.title)}</td><td>${esc(x.sub.organisation)}</td><td class="num">${fmtD(x.receivedAt)}</td><td>${x.exists?pill("Already registered",""):pill("New","info")}</td></tr>`).join("")}</tbody></table></div>
  <div class="row" style="margin-top:14px"><button class="btn primary" data-act="doimport" ${p.rows.some(x=>!x.exists)?"":"disabled"}>Add ${p.rows.filter(x=>!x.exists).length} new request${p.rows.filter(x=>!x.exists).length===1?"":"s"}</button><button class="btn" data-act="cancelimport">Cancel</button></div>`:""}</div>
  <div class="glass card"><h2>Load a register file</h2><p class="sub" style="margin-top:6px">To move a whole register, with assessments, history and applicant details, choose a register file (<code>register.json</code>). Requests already in the register are left unchanged.</p>
  <div class="row" style="margin-top:14px"><label class="btn" for="regFile">${icon("import")}Choose the register file</label><input type="file" id="regFile" accept=".json,application/json" class="sr"><span class="muted" style="font-size:13px" id="regNote"></span></div></div>`;
}
const FORM_COLS={"ID":"id","Completion time":"completed","First name":"first","Family name":"family","Email address":"email","Organisation":"organisation","Country":"country","Which level are you applying for?":"level","Type of use":"typeOfUse","Activity title":"title","Description of the activity":"description","How does the activity contribute to the Decade?":"link","Which main goal(s) does your activity contribute to?":"mgsDeclared","Link to the activity or to the material":"url","Where will the logo appear?":"placements","Starting date of intended use":"startOfUse","Is the use non-commercial?":"nonCommercial","Do you wish to place any limitation on the reuse of your material?":"reuseLimitation","Agreement to the Logo usage standards":"standards","Accuracy, geoengineering and misinformation":"accuracy"};
function loadXLSX(){return window.XLSX?Promise.resolve(window.XLSX):new Promise((ok,ko)=>{const s=document.createElement("script");s.src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js";s.onload=()=>ok(window.XLSX);s.onerror=()=>ko(new Error("The Excel reader could not be loaded."));document.head.appendChild(s)})}
const clean=(v)=>String(v??"").replace(/ /g," ").trim();
const isoDate=(v)=>{if(!v)return"";if(v instanceof Date)return ymd(v);const s=clean(v);const m=s.match(/^(\d{4})-(\d{2})-(\d{2})/);if(m)return m[0];const m2=s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{2,4})/);if(m2){const y=m2[3].length===2?"20"+m2[3]:m2[3];return`${y}-${m2[1].padStart(2,"0")}-${m2[2].padStart(2,"0")}`}const d=new Date(s);return isNaN(d)?"":d.toISOString().slice(0,10)};
function refOf(id){return"DACS-LOGO-2026-"+String(id).padStart(3,"0")}
function blankReq(formId,sub,receivedAt){return{ref:refOf(formId),formId,receivedAt,sub,stage:"received",screen:{acknowledged:"No",completeness:"",gates:{g1:"",g2:"",g3:"",g4:""}},assess:{level:"",primaryOC:"",mgs:[],scores:{c1:null,c2:null,c3:null,c4:null,c5:null,c6:null},notes:""},consult:[],assigned:{bodies:[],due:""},decision:{final:"Pending",date:"",conditions:"",from:"",until:"",notified:""},follow:{action:"",owner:"",nextReview:"",reviewerName:""},history:[],updatedAt:nowIso()}}
async function readForm(file){
  const X=await loadXLSX();const wb=X.read(await file.arrayBuffer(),{type:"array",cellDates:true});const ws=wb.Sheets[wb.SheetNames[0]];
  const rows=X.utils.sheet_to_json(ws,{defval:"",raw:true});
  const out=[];rows.forEach(row=>{const o={};Object.keys(row).forEach(h=>{const k=FORM_COLS[clean(h)];if(k)o[k]=row[h]});const id=parseInt(clean(o.id),10);if(!id)return;
    const lvl=clean(o.level);const sub={organisation:clean(o.organisation),country:clean(o.country),levelRequested:/^Level [123]/.test(lvl)?lvl.slice(0,7):"Not stated",typeOfUse:clean(o.typeOfUse),title:clean(o.title),description:clean(o.description),link:clean(o.link),mgsDeclared:clean(o.mgsDeclared).split(";").map(x=>x.trim()).filter(Boolean).join("; "),placements:clean(o.placements),startOfUse:isoDate(o.startOfUse),url:clean(o.url),nonCommercial:clean(o.nonCommercial),reuseLimitation:clean(o.reuseLimitation),standards:clean(o.standards),accuracy:clean(o.accuracy)};
    out.push({formId:id,receivedAt:isoDate(o.completed),sub,contact:{applicant:(clean(o.first)+" "+clean(o.family)).trim(),email:clean(o.email)},exists:S.requests.has(refOf(id))})});
  if(!out.length)throw new Error("No Form response found. Choose the workbook exported from Microsoft Forms (it has an “ID” column).");
  return out.sort((a,b)=>a.formId-b.formId);
}
async function loadRegister(d){
  if(!d||typeof d.requests!=="object")throw new Error("format");let req=0,con=0,skip=0;
  for(const [ref,r] of Object.entries(d.requests)){if(S.requests.has(ref)){skip++;continue}const x=Object.assign({},r);delete x.ref;
    await S.db.doc("requests/"+ref).set(x);req++;
    const c=d.contacts&&d.contacts[ref];if(c){await S.db.doc("contacts/"+ref).set(c);con++}}
  return{req,con,skip};
}
async function createReq(x){
  const r=blankReq(x.formId,x.sub,x.receivedAt);r.history=[{at:nowIso(),by:S.uid||"",who:who(),what:x.how||"Added from the Form responses"}];
  await queued("requests/"+r.ref,()=>S.db.doc("requests/"+r.ref).set(r));
  if(x.contact&&(x.contact.applicant||x.contact.email))await queued("contacts/"+r.ref,()=>S.db.doc("contacts/"+r.ref).set(x.contact));
  return r.ref;
}
function newReqSheet(){
  const next=Math.max(0,...[...S.requests.values()].map(r=>r.formId||0))+1;
  openSheet(`<h2>New request</h2><p class="muted" style="margin-top:4px;font-size:13.5px">For a request received outside the Form. It gets the reference ${refOf(next)}.</p>
  <form id="newForm" class="stack" style="gap:12px;margin-top:16px">
    <div class="grid g2"><label class="field"><span>Activity title</span><input class="input" id="nf_title" required></label><label class="field"><span>Organisation</span><input class="input" id="nf_org" required></label>
    <label class="field"><span>Country</span><input class="input" id="nf_country"></label><label class="field"><span>Type of use</span><select class="input" id="nf_type">${["Publication","Website","Project","Event","Film","Course","Other"].map(x=>`<option>${x}</option>`).join("")}</select></label>
    <label class="field"><span>Applicant name</span><input class="input" id="nf_app"></label><label class="field"><span>Applicant email</span><input class="input" id="nf_email" type="email"></label>
    <label class="field"><span>Level requested</span><select class="input" id="nf_level"><option>Not stated</option><option>Level 1</option><option>Level 2</option><option>Level 3</option></select></label><label class="field"><span>Date received</span><input class="input" id="nf_date" type="date" value="${today()}"></label></div>
    <label class="field"><span>Description</span><textarea class="input" id="nf_desc" rows="4"></textarea></label>
    <label class="field"><span>Contribution to the Decade</span><textarea class="input" id="nf_link" rows="3"></textarea></label>
    <div class="grid g2"><label class="field"><span>Main goals declared</span><input class="input" id="nf_mgs" placeholder="e.g. MG1.1; MG5.3"></label><label class="field"><span>Where the logo will appear</span><input class="input" id="nf_place"></label>
    <label class="field"><span>Link</span><input class="input" id="nf_url" type="url"></label><label class="field"><span>Start of use</span><input class="input" id="nf_start" type="date"></label></div>
    <div class="row" style="justify-content:flex-end;margin-top:6px"><button type="button" class="btn" data-act="closesheet">Cancel</button><button type="submit" class="btn primary">Add to the register</button></div>
  </form>`,next);
}
function openSheet(html,data){S.sheet=data;$("#layer").innerHTML=`<div class="scrim" data-scrim="1"><div class="sheet glass" role="dialog" aria-modal="true">${html}</div></div>`;const f=$("#layer input");f&&f.focus()}
function closeSheet(){S.sheet=null;$("#layer").innerHTML=""}

/* ---------------- methodology ---------------- */
function viewMethod(){
  const bands=[[0,2,"bad","Refuse"],[2,3,"warn","Revert to applicant"],[3,4,"info","Approve with conditions"],[4,5,"good","Approve"]];
  return previewBanner()+head("Reference","Methodology","How a request to use the logo of the Decade is handled (draft, September 2026).")+
  `<div class="glass card pmap-card"><div class="card-head"><h2>Six steps</h2><span class="muted" style="font-size:13px">Target: ${CFG.target} working days at Level 1</span></div>${processMap()}</div>
  <div class="card-head" style="margin:6px 4px 0"><h2>Three levels</h2></div>
  <div class="grid g3">${Object.entries(CFG.levels).map(([k,L])=>`<div class="glass card level-ref"><span class="lv-n big">${k.replace("Level ","")}</span><div class="eyebrow">${k} · ${L.name}</div><h3>${L.marks}</h3>${chainChips(L)}<p class="lv-who">${icon("check")}<span>Decided by <b>${L.decides}</b></span></p>${more(L.period+(L.clearance?" "+L.clearance:""))}</div>`).join("")}</div>
  <div class="grid g2">
  <div class="glass card"><div class="card-head"><h2>Four hard gates</h2><span class="legend"><span class="lg warn">To verify · suspends</span><span class="lg bad">Yes · refuses</span></span></div>
    <div class="gate-tiles">${CFG.gates.map((g,i)=>`<div class="gate-tile"><span class="gate-n num">${i+1}</span><b>${g.t}</b>${more(g.r)}</div>`).join("")}</div></div>
  <div class="glass card"><div class="card-head"><h2>Six criteria</h2><span class="muted" style="font-size:13px">Scored 0 to 5, weighted</span></div>
    <div class="weights" aria-hidden="true">${CFG.criteria.map((c,i)=>`<span style="flex:${c.w}" class="w${i+1}" title="${esc(c.t)} · ${Math.round(c.w*100)}%"><b class="num">${Math.round(c.w*100)}%</b></span>`).join("")}</div>
    <div class="crit-ref">${CFG.criteria.map((c,i)=>`<div class="crit-line"><i class="w${i+1}"></i><span class="crit-t"><b>${c.t}</b>${more(c.m)}</span><span class="num muted">${Math.round(c.w*100)}%</span></div>`).join("")}</div>
    <h3 style="margin:18px 0 8px">From the weighted score to the recommendation</h3>
    <div class="band-scale">${bands.map(([f,t,tone,l])=>`<span class="t-${tone}" style="flex:${t-f}"><b>${l}</b><small class="num">${f===0?"below 2":t===5?"4 and above":f.toFixed(0)+" to "+t.toFixed(0)}</small></span>`).join("")}</div>
  </div></div>`;
}

/* ---------------- export ---------------- */
async function exportSummary(){
  try{const X=await loadXLSX();
    const rows=[...S.requests.values()].sort((a,b)=>a.formId-b.formId).map(r=>{const rc=reco(r),o={"Ref. no.":r.ref,"Form ID":r.formId,"Received":r.receivedAt,"Activity title":r.sub.title,"Organisation":r.sub.organisation,"Country":r.sub.country,"Type of use":r.sub.typeOfUse,"Stage":CFG.stages[STAGE_IDX[r.stage]||0].l,"Register status":STATUS_OF[r.stage],"Level retained":(r.assess||{}).level,"MGs retained":((r.assess||{}).mgs||[]).join("; "),"Gate outcome":gateOutcome(r)};
      CFG.criteria.forEach((c,i)=>o[(i+1)+". "+c.t]=((r.assess||{}).scores||{})[c.k]);o["Weighted score"]=score(r);o["First screening result"]=rc?rc.l:"";o["Assigned to"]=(((r.assigned||{}).bodies)||[]).join(", ");
      o["Opinions"]=opinionsFor(r.ref).filter(x=>x.status==="submitted").map(x=>x.body+(x.reviewer?" ("+x.reviewer+")":"")+": "+x.opinion).join(" | ");o["Final decision"]=(r.decision||{}).final;o["Decision date"]=(r.decision||{}).date;o["Authorised until"]=(r.decision||{}).until;return o});
    const wb=X.utils.book_new();X.utils.book_append_sheet(wb,X.utils.json_to_sheet(rows),"Requests");
    const data=new Uint8Array(X.write(wb,{type:"array",bookType:"xlsx"}));
    const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([data],{type:"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}));a.download="DACS-logo-requests-"+today()+".xlsx";document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500);
  }catch(e){console.error(e);if(e&&e.code!=="cancelled")toast("The summary could not be downloaded.",true)}
}

/* ---------------- events ---------------- */
document.addEventListener("click",async(e)=>{
  const t=e.target.closest("[data-task],[data-go],[data-open],[data-tab],[data-act],[data-gate],[data-score],[data-mg],[data-consult],[data-assign],[data-op],[data-flow],[data-addmember],[data-scrim],[data-level]");if(!t)return;
  if(t.dataset.scrim&&e.target===t){if(S.sheet==="actor"&&!actor())return;closeSheet();return}
  if(t.dataset.task){closeSheet();S.opKey=null;open(t.dataset.task,t.dataset.tab);return}
  if(t.dataset.go){go(t.dataset.go);return}
  if(t.dataset.flow){S.q="";go("pipeline");setTimeout(()=>{const c=document.querySelector(`[data-col="${t.dataset.flow}"]`);c&&c.scrollIntoView({behavior:"smooth",inline:"start",block:"nearest"})},50);return}
  if(t.dataset.open&&!t.closest(".sheet")){if(t.classList.contains("tile")&&t.dataset.dragged){delete t.dataset.dragged;return}open(t.dataset.open,t.dataset.tab);return}
  if(t.dataset.tab&&!t.dataset.open){flushText();S.tab=t.dataset.tab;render();return}
  const r=S.sel&&S.requests.get(S.sel);const ro=!isSec()||!!S.preview;
  if(r&&!ro){
    if(t.dataset.gate){const k=t.dataset.gate,v=t.dataset.v,cur=((r.screen||{}).gates||{})[k];const nv=cur===v?"":v;const g=Object.assign({},(r.screen||{}).gates,{[k]:nv});await saveReq(r.ref,{screen:{gates:g}},`Gate ${k.slice(1)}: ${nv||"cleared"}`);return}
    if(t.dataset.score){const k=t.dataset.score,v=Number(t.dataset.v),cur=((r.assess||{}).scores||{})[k];const nv=cur===v?null:v;await saveReq(r.ref,{assess:{scores:{[k]:nv}}},`Criterion ${k.slice(1)} scored ${nv??"–"}`);return}
    if(t.dataset.level){const v=t.dataset.level;if((r.assess||{}).level===v)return;await saveReq(r.ref,{assess:{level:v}},`Level retained: ${v}`);return}
    if(t.dataset.mg){const k=t.dataset.mg,cur=(r.assess||{}).mgs||[];const nv=cur.includes(k)?cur.filter(x=>x!==k):[...cur,k].sort();await saveReq(r.ref,{assess:{mgs:nv}},`Main goals retained: ${nv.join(", ")||"none"}`);return}
    if(t.dataset.consult){const k=t.dataset.consult,cur=r.consult||[];const nv=cur.includes(k)?cur.filter(x=>x!==k):[...cur,k].sort();await saveReq(r.ref,{consult:nv},`Working Groups to consult: ${nv.join(", ")||"none"}`);return}
    if(t.dataset.assign){const k=t.dataset.assign,cur=((r.assigned||{}).bodies)||[];const nv=cur.includes(k)?cur.filter(x=>x!==k):[...cur,k];await saveReq(r.ref,{assigned:{bodies:nv,due:((r.assigned||{}).due)||(nv.length?addWd(today(),10):"")}},cur.includes(k)?`Unassigned from ${k}`:`Assigned to ${k}`);return}
  }
  if(t.dataset.op&&r&&!S.preview){const key=ensureKey(r.ref);const rv=$("#opRev");const extra=rv&&clean(rv.value)?{reviewer:clean(rv.value)}:{};await saveOpinion(r.ref,Object.assign(flushOp(key),extra,{opinion:t.dataset.op,status:"draft"}),key);return}
  switch(t.dataset.act){
    case"next":{const n=nextStep(S.requests.get(t.dataset.ref));if(n)await moveStage(t.dataset.ref,n.to,n.assign);return}
    case"submit":{const rv=clean(($("#opRev")||{}).value||"");if(!rv){toast("Enter the name of the reviewer before submitting.",true);$("#opRev")&&$("#opRev").focus();return}
      const key=ensureKey(S.sel);flushOp(key);const txt=$("#opText"),cd=$("#opCond");await saveOpinion(S.sel,{reviewer:rv,text:txt?txt.value:"",conditions:cd?cd.value:"",status:"submitted",submittedAt:nowIso()},key);S.opKey=null;toast("Review by "+rv+" sent to the Secretariat.");render();return}
    case"reopen":S.opKey=t.dataset.key;await saveOpinion(S.sel,{status:"draft"},t.dataset.key);return;
    case"newop":{flushText();S.opKey="new";render();const f=$("#opRev");f&&!f.value&&f.focus();return}
    case"editop":S.opKey=t.dataset.key;render();return;
    case"discardop":confirmSheet("Discard this draft?","The draft review is deleted. Submitted reviews are not affected.","dodiscardop",{key:t.dataset.key});return;
    case"dodiscardop":closeSheet();flushOp(t.dataset.key);await removeOpinion(S.uid,t.dataset.key);S.opKey=null;render();return;
    case"tasks":tasksSheet();return;
    case"actor":askActor();return;
    case"apply":{const rr=S.requests.get(t.dataset.ref);S.stamp=rr&&rr.ref;S.stampAt=Date.now();const o=opinionsFor(rr.ref).find(x=>x.uid===t.dataset.uid&&x.key===t.dataset.key);if(!o)return;await saveReq(rr.ref,{decision:{final:CFG.decisionMap[o.opinion],date:today(),conditions:[rr.decision.conditions,o.conditions].filter(Boolean).join("\n")},stage:"decided"},`Final decision recorded from ${o.body}${o.reviewer?" ("+o.reviewer+")":""}: ${CFG.decisionMap[o.opinion]}`);toast("Decision recorded.");return}
    case"logout":flushText();S.preview=null;S.sel=null;await signOut(auth);return;
    case"editsub":S.editSub=!S.editSub;flushText();render();return;
    case"delreq":confirmSheet("Delete this request?",`${esc(t.dataset.ref)} will be removed from the register, with its applicant details and every opinion given on it. This cannot be undone.`,"dodelreq",{ref:t.dataset.ref});return;
    case"dodelreq":closeSheet();S.sel=null;S.editSub=false;await deleteRequest(t.dataset.ref);go("pipeline");return;
    case"delop":confirmSheet("Delete this opinion?","The opinion is removed for everyone. The reviewer can write a new one.","dodelop",{uid:t.dataset.uid,key:t.dataset.key});return;
    case"dodelop":closeSheet();await removeOpinion(t.dataset.uid,t.dataset.key);toast("Opinion deleted.");return;
    case"delhist":{const rr=S.requests.get(t.dataset.ref);const i=Number(t.dataset.i);const h=(rr.history||[]).filter((_,k)=>k!==i);await queued("requests/"+rr.ref,()=>S.db.doc("requests/"+rr.ref).update({history:h})).catch(writeErr);return}
    case"clearhist":confirmSheet("Clear the history?","Every entry in the history of this request is removed.","doclearhist",{ref:t.dataset.ref});return;
    case"doclearhist":closeSheet();await queued("requests/"+t.dataset.ref,()=>S.db.doc("requests/"+t.dataset.ref).update({history:[]})).catch(writeErr);toast("History cleared.");return;
    case"newreq":newReqSheet();return;
    case"closesheet":closeSheet();return;
    case"export":exportSummary();return;
    case"repexport":exportReports();return;
    case"repcode":{const ref=t.dataset.ref;if(t.dataset.replace&&!t.dataset.ok){confirmSheet("Replace the reporting code?","The current code stops working at once. Send the new code to the applicant.","repcode",{ref,replace:"1",ok:"1"});const b=document.querySelector('.sheet [data-act="repcode"]');b&&(b.textContent="Replace");return}
      closeSheet();if(!actor()){askActor();return}const code=makeCode();try{await S.db.doc("reportCodes/"+ref).set({code,createdAt:nowIso(),createdBy:actor()});await saveReq(ref,{reporting:{codeIssued:today()}},t.dataset.replace?"Reporting code replaced":"Reporting code issued");toast("Reporting code issued.")}catch(e){writeErr(e)}return}
    case"replink":{const ref=t.dataset.ref,c=(S.codes.get(ref)||{}).code;if(c)copyText(reportUrl(ref,c),"Link copied.");return}
    case"repmsg":{const ref=t.dataset.ref,c=(S.codes.get(ref)||{}).code,rr=S.requests.get(ref);if(c&&rr)copyText(applicantMessage(rr,c),"Message copied: paste it in your e-mail to the applicant.");return}
    case"repreview":{if(!actor()){askActor();return}try{await S.db.doc("reports/"+t.dataset.id).update({review:{status:"reviewed",by:actor(),at:nowIso()}})}catch(e){writeErr(e)}return}
    case"repunreview":try{await S.db.doc("reports/"+t.dataset.id).update({review:{status:"",by:"",at:""}})}catch(e){writeErr(e)}return;
    case"repdel":confirmSheet("Delete this report?","The report and its attachment are removed from the platform.","repdodel",{id:t.dataset.id});return;
    case"repdodel":closeSheet();try{const x=S.reports.get(t.dataset.id);if(x&&x.fileName)await S.db.doc("reportFiles/"+t.dataset.id).delete();await S.db.doc("reports/"+t.dataset.id).delete();toast("Report deleted.")}catch(e){writeErr(e)}return;
    case"repfile":{t.disabled=true;try{const d=await S.db.doc("reportFiles/"+t.dataset.id).get();if(!d.exists){toast("The attachment was not found.",true)}else{const f=d.data();const bin=atob(f.data);const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);
      const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([u],{type:f.type||"application/octet-stream"}));a.download=f.name||"attachment";document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},800)}}catch(e){writeErr(e)}t.disabled=false;return}
    case"cancelimport":S.pending=null;render();return;
    case"doimport":{const rows=S.pending.rows.filter(x=>!x.exists);t.disabled=true;let n=0;for(const x of rows){try{await createReq(x);n++}catch(err){writeErr(err);break}}S.pending=null;toast(`${n} request${n===1?"":"s"} added to the register.`);go("pipeline");return}
  }
});
document.addEventListener("input",(e)=>{const t=e.target;
  if(t.id==="q"){S.q=t.value;clearTimeout(t._d);t._d=setTimeout(()=>{render();const q=$("#q");if(q){q.focus();q.setSelectionRange(q.value.length,q.value.length)}},220);return}
  if(t.dataset.contact&&S.sel&&isSec()&&!S.preview){const ref=S.sel,f=t.dataset.contact,val=t.value;clearTimeout(t._c);t._c=setTimeout(()=>{const cur=S.contacts.get(ref)||{};queued("contacts/"+ref,()=>S.db.doc("contacts/"+ref).set(Object.assign({},cur,{[f]:val}))).catch(writeErr)},700);return}
  const r=S.sel&&S.requests.get(S.sel);
  if(t.dataset.optext&&r&&!S.preview){opinionLater(r.ref,ensureKey(r.ref),{[t.dataset.optext]:t.value});return}
  if(t.dataset.bind&&r&&isSec()&&!S.preview&&(t.tagName==="TEXTAREA"||t.type==="text")){const path=t.dataset.bind.split(".");const patch={};path.reduce((o,k,i)=>i===path.length-1?(o[k]=t.value):(o[k]={}),patch);saveLater(r.ref,patch,`${t.closest("label").querySelector("span").textContent} edited`)}
});
document.addEventListener("change",async(e)=>{const t=e.target;
  if(t.id==="previewSel"||t.id==="compactPreviewSel"){S.preview=t.value?{role:t.value==="SMC"?"smc":t.value==="ESC"?"esc":"wg",body:t.value}:null;S.sel=null;S.view=S.preview?"mine":"overview";render();return}
  if(t.id==="stageFilter"){S.stageFilter=t.value;render();return}
  if(t.id==="regFile"&&t.files[0]){const note=$("#regNote");note.textContent="Loading…";try{const n=await loadRegister(JSON.parse(await t.files[0].text()));note.textContent="";toast(`${n.req} request${n.req===1?"":"s"} and ${n.con} applicant record${n.con===1?"":"s"} loaded${n.skip?`; ${n.skip} already in the register`:""}.`);go("pipeline")}catch(err){console.error(err);note.textContent="";toast(err&&err.code?"This file could not be loaded: your role does not allow it.":"This is not a register file.",true)}t.value="";return}
  if(t.id==="formFile"&&t.files[0]){const note=$("#fileNote");note.textContent="Reading "+t.files[0].name+"…";try{S.pending={rows:await readForm(t.files[0])};render()}catch(err){note.textContent="";toast(err.message||"The file could not be read.",true)}return}
  const r=S.sel&&S.requests.get(S.sel);
  if(t.id==="stageSel"&&r){await moveStage(r.ref,t.value);return}
  if(t.dataset.bind==="decision.final"&&r&&/^(Approved|Refused)/.test(t.value)){S.stamp=r.ref;S.stampAt=Date.now()}
  if(t.dataset.bind&&r&&isSec()&&!S.preview&&(t.tagName==="SELECT"||t.type==="date")){const path=t.dataset.bind.split(".");const patch={};path.reduce((o,k,i)=>i===path.length-1?(o[k]=t.value):(o[k]={}),patch);await saveReq(r.ref,patch,`${t.closest("label").querySelector("span").textContent}: ${t.value||"cleared"}`)}
});
document.addEventListener("submit",async(e)=>{
  if(e.target.id==="actorForm"){e.preventDefault();const n=clean($("#actorName").value);if(n.length<2){toast("Enter your name.",true);return}setActor(n);return}
  if(e.target.id!=="newForm")return;e.preventDefault();const v=(id)=>clean($("#"+id).value);const next=S.sheet;
  const sub={organisation:v("nf_org"),country:v("nf_country"),levelRequested:v("nf_level"),typeOfUse:v("nf_type"),title:v("nf_title"),description:v("nf_desc"),link:v("nf_link"),mgsDeclared:v("nf_mgs"),placements:v("nf_place"),startOfUse:v("nf_start"),url:v("nf_url"),nonCommercial:"",reuseLimitation:"",standards:"",accuracy:""};
  try{const ref=await createReq({formId:next,receivedAt:v("nf_date")||today(),sub,contact:{applicant:v("nf_app"),email:v("nf_email")},how:"Entered by hand"});closeSheet();toast("Request added.");open(ref)}catch(err){writeErr(err)}});
document.addEventListener("keydown",(e)=>{if(e.key==="Escape"&&S.sheet!==null&&!(S.sheet==="actor"&&!actor()))closeSheet()});
/* drag and drop on the pipeline */
document.addEventListener("dragstart",(e)=>{const t=e.target.closest&&e.target.closest("[data-drag]");if(!t||!isSec()||S.preview)return;t.classList.add("dragging");e.dataTransfer.setData("text/plain",t.dataset.drag);e.dataTransfer.effectAllowed="move"});
document.addEventListener("dragend",(e)=>{const t=e.target.closest&&e.target.closest("[data-drag]");if(t){t.classList.remove("dragging");t.dataset.dragged="1";setTimeout(()=>delete t.dataset.dragged,50)}document.querySelectorAll(".col.drop").forEach(c=>c.classList.remove("drop"))});
document.addEventListener("dragover",(e)=>{const c=e.target.closest&&e.target.closest("[data-col]");if(!c)return;e.preventDefault();document.querySelectorAll(".col.drop").forEach(x=>x!==c&&x.classList.remove("drop"));c.classList.add("drop")});
document.addEventListener("drop",async(e)=>{const c=e.target.closest&&e.target.closest("[data-col]");if(!c)return;e.preventDefault();c.classList.remove("drop");const ref=e.dataTransfer.getData("text/plain");const r=S.requests.get(ref);if(r&&r.stage!==c.dataset.col)await moveStage(ref,c.dataset.col)});
function afterRender(){}
/* theme */
function applyTheme(t){document.documentElement.classList.toggle("light",t==="light");document.querySelectorAll("[data-theme-btn]").forEach(b=>{b.textContent=t==="light"?"Dark":"Bright";b.setAttribute("aria-label",t==="light"?"Switch to the dark theme":"Switch to the bright theme")})}
applyTheme(recall("theme","dark"));
document.addEventListener("click",(e)=>{if(e.target.closest("[data-theme-btn]")){const t=document.documentElement.classList.contains("light")?"dark":"light";store("theme",t);applyTheme(t)}});

renderShell();connect();

document.addEventListener('change',e=>{if(e.target.id==='compactSection'){document.querySelector('#nav [data-go="'+e.target.value+'"]').click();return;}if(e.target.id==='hubBody')S.changeBody?.(e.target.value);});
if(window.parent!==window){document.body.classList.add('embedded');}
window.addEventListener('message',e=>{if(e.origin===location.origin&&e.data?.type==='dacs-theme')applyTheme(e.data.light?'light':'dark');});
