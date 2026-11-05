import {useEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import Community from './community';
import {EmailAction} from './email-action';
import {AuthProvider,AuthGate,useMemberAuth} from './auth';
import {PollInvite} from './poll-invite';
import {pollIdFromPath} from '@/lib/meetings';
import {Toaster} from 'sonner';
import {AlertTriangle,Check,Snowflake,X} from 'lucide-react';
import '@fontsource-variable/source-sans-3';
import './globals.css';
import { appPath } from "@/lib/base";
function App(){const {user}=useMemberAuth();return <Community key={user?.uid||'guest'} signedIn={!!user}/>}
// Toasts follow the platform theme class rather than the operating system setting.
/** Toast icon with the melting ice edge drawn along the top of the notice (styled in globals.css). */
function GlacierMark({icon}:{icon:React.ReactNode}){
  return <><span className="glacier-mark">{icon}</span><span className="glacier-cap" aria-hidden="true"><i/><i/><i/></span><span className="glacier-water" aria-hidden="true"/></>;
}
function ThemedToaster(){
  const isDark=()=>document.documentElement.classList.contains('dark');
  const [dark,setDark]=useState(isDark);
  useEffect(()=>{const o=new MutationObserver(()=>setDark(isDark()));o.observe(document.documentElement,{attributes:true,attributeFilter:['class']});return()=>o.disconnect();},[]);
  return <Toaster theme={dark?'dark':'light'} closeButton position="top-right" offset={124} mobileOffset={{top:82,left:12,right:12}} toastOptions={{className:'dacs-toast'}}
    icons={{info:<GlacierMark icon={<Snowflake size={18}/>}/>,success:<GlacierMark icon={<Check size={18}/>}/>,warning:<GlacierMark icon={<AlertTriangle size={17}/>}/>,error:<GlacierMark icon={<X size={18}/>}/>}}/>;
}
const pollId=pollIdFromPath(appPath());
// IHP-WINS: account emails (password resets) are handled by IHP-WINS, not by this platform.
if(appPath()==="/auth/action")location.replace((window as any).__DACS__?.resetUrl||'/user/reset');
createRoot(document.getElementById('root')!).render(<AuthProvider>{appPath() === "/auth/action" ? <EmailAction/> : pollId ? <PollInvite pollId={pollId}/> : <AuthGate><App/></AuthGate>}<ThemedToaster/></AuthProvider>);
