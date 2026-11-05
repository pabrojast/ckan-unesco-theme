import {useEffect,useRef,useState} from 'react';
import {Maximize2,Minimize2} from 'lucide-react';
import {canReviewLogo,type MeetingAccess} from '@/lib/meetings';
import { asset } from "@/lib/base";
/** Logo review desk, embedded unchanged. The Hub gives it the full page width, and a full-screen mode. */
export function LogoReview({access,light}:{access:MeetingAccess;light:boolean}){
 const frame=useRef<HTMLIFrameElement>(null);
 const [full,setFull]=useState(false);
 const theme=()=>frame.current?.contentWindow?.postMessage({type:'dacs-theme',light},window.location.origin);
 useEffect(()=>{theme();},[light]);
 useEffect(()=>{
  if(!full)return;
  const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setFull(false);};
  document.documentElement.classList.add('logo-full');window.addEventListener('keydown',key);
  return()=>{document.documentElement.classList.remove('logo-full');window.removeEventListener('keydown',key);};
 },[full]);
 if(!canReviewLogo(access))return null;
 return <section className={'logo-review'+(full?' full':'')} aria-label="Logo review desk">
  <div className="logo-review-bar">
   {(full||access.admin)&&<p className="micro">{full?<><strong>Logo review</strong> · Press Esc or use the button to leave full screen.</>:'UNESCO Secretariat · full register editing. Manage appointments in Hub Governance.'}</p>}
   <button type="button" className="btn small" onClick={()=>setFull(!full)} aria-pressed={full}>{full?<><Minimize2 size={15}/> Exit full screen</>:<><Maximize2 size={15}/> Full screen</>}</button>
  </div>
  <iframe ref={frame} src={asset("logo-desk/index.html")} title="DACS logo authorisation desk" className="logo-review-frame" onLoad={theme}/>
 </section>;
}
