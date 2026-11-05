import {useEffect,useState} from 'react';
import {detectTimeZone,validTimeZone} from '@/lib/calendar';

const changeEvent='dacs-time-zone-change';
const key=(uid:string)=>'dacs-time-zone:'+uid;
function saved(uid:string){try{const v=localStorage.getItem(key(uid))||'';return validTimeZone(v)?v:'';}catch{return '';}}
export function useTimeZone(uid:string){
  const [choice,setChoice]=useState(()=>saved(uid)),[device,setDevice]=useState(detectTimeZone);
  useEffect(()=>{
    setChoice(saved(uid));
    const refresh=()=>setDevice(detectTimeZone());
    const sync=(e:Event)=>{const d=(e as CustomEvent).detail;if(d?.uid===uid)setChoice(d.value);};
    const storage=(e:StorageEvent)=>{if(e.key===key(uid))setChoice(saved(uid));};
    const timer=setInterval(refresh,60_000);
    window.addEventListener(changeEvent,sync);window.addEventListener('storage',storage);document.addEventListener('visibilitychange',refresh);
    return()=>{clearInterval(timer);window.removeEventListener(changeEvent,sync);window.removeEventListener('storage',storage);document.removeEventListener('visibilitychange',refresh);};
  },[uid]);
  function select(value:string){
    if(value&&!validTimeZone(value))return;
    setChoice(value);try{if(value)localStorage.setItem(key(uid),value);else localStorage.removeItem(key(uid));}catch{}
    window.dispatchEvent(new CustomEvent(changeEvent,{detail:{uid,value}}));
  }
  return {zone:choice||device,automatic:!choice,setZone:select,useDevice:()=>select('')};
}
