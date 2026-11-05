import {useId,useMemo,useState} from 'react';
import {Check,ChevronDown,Globe,Search} from 'lucide-react';
import {timeZoneOptions} from '@/lib/calendar';
import {Dialog,DialogContent,DialogTitle,DialogDescription} from '@/components/ui/dialog';

export function TimeZonePicker({value,onChange,label='Time zone',automatic,onAutomatic,disabled=false}:{value:string;onChange:(v:string)=>void;label?:string;automatic?:boolean;onAutomatic?:()=>void;disabled?:boolean}){
 const [open,setOpen]=useState(false),[search,setSearch]=useState('');const id=useId();
 const options=useMemo(()=>[...new Set([value,...timeZoneOptions()])].sort(),[value]);
 const filtered=options.filter(z=>z.replaceAll('_',' ').toLowerCase().includes(search.trim().replaceAll('_',' ').toLowerCase()));
 return <div className="timezone-picker"><span id={id} className="timezone-label">{label}</span><button type="button" disabled={disabled} className="timezone-trigger" aria-label={label} aria-haspopup="dialog" aria-expanded={open} onClick={()=>{setSearch('');setOpen(true);}}><Globe size={16}/><span>{value.replaceAll('_',' ')}{automatic&&<small>Device time zone</small>}</span><ChevronDown size={17}/></button><Dialog open={open} onOpenChange={setOpen}><DialogContent className="detail-content timezone-menu"><DialogTitle>{label}</DialogTitle><DialogDescription>Search by city or region. Times convert from the same saved instant.</DialogDescription><label className="timezone-search"><span><Search size={15}/> Find a time zone</span><input type="search" value={search} onChange={e=>setSearch(e.target.value)} placeholder="Paris, Tokyo, New York…"/></label>{onAutomatic&&<button type="button" className="btn" onClick={()=>{onAutomatic();setOpen(false);}}>Use device time zone</button>}<div className="timezone-options" role="group" aria-label="Time zone choices">{filtered.map(z=><button type="button" key={z} aria-pressed={z===value} onClick={()=>{onChange(z);setOpen(false);}}><span>{z.replaceAll('_',' ')}</span>{z===value&&<Check size={16}/>}</button>)}{!filtered.length&&<p className="micro">No matching time zone. Try a nearby city or UTC.</p>}</div></DialogContent></Dialog></div>;
}
