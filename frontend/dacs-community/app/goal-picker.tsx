import {useState} from 'react';
import {ChevronDown, Check} from 'lucide-react';
import {decadeGoals, overarchingChallenges, goalLabel, challengeLabel, linkedGroups,allGoalIds,isDecadeWide} from '@/lib/decade-goals';
import {groups} from '@/lib/data';

export function GoalPicker({value=[],onChange,label='Main goals supported'}:{value:string[];onChange:(value:string[])=>void;label?:string}) {
  const [expanded,setExpanded]=useState<number|null>(()=>linkedGroups(value)[0] || 1);
  return <fieldset className="goal-picker"><legend>{label}</legend>
    <label className="decade-wide-choice"><input type="checkbox" checked={isDecadeWide(value)} onChange={e=>onChange(e.target.checked?[...allGoalIds]:[])}/><span><strong>Decade-wide</strong><small>All 5 overarching challenges and all 15 main goals</small></span></label>
    {overarchingChallenges.map(oc=>{
      const group=groups.find(g=>g.id===oc.id)!;
      const count=value.filter(m=>m.startsWith(oc.id+'.')).length;
      return <div className={'goal-picker-group '+(count?'chosen':'')} key={oc.id} style={{'--wg-color':group.color} as React.CSSProperties}>
        <button type="button" className="goal-picker-heading" aria-expanded={expanded===oc.id} onClick={()=>setExpanded(expanded===oc.id?null:oc.id)}>
          <span>{challengeLabel(oc.id)}</span><span className="goal-picker-count">{count>0 && <><Check size={14}/> {count} selected · WG{oc.id}</>}<ChevronDown size={16}/></span>
        </button>
        {expanded===oc.id && <div className="goal-picker-options">{decadeGoals.filter(g=>g.oc===oc.id).map(g=><label key={g.id}>
          <input type="checkbox" checked={value.includes(g.id)} onChange={e=>onChange(e.target.checked?[...value,g.id].sort():value.filter(m=>m!==g.id))}/><span>{goalLabel(g.id)}</span>
        </label>)}</div>}
      </div>;
    })}
    <p className="micro">Selecting a main goal selects its parent OC and Working Group.</p>
    <div className="goal-selection">{isDecadeWide(value)?<span className="pill">Decade-wide · all OCs and MGs</span>:value.map(m=><span className="tag" key={m} title={goalLabel(m)}>MG{m}</span>)}</div>
  </fieldset>;
}
export function GoalLabels({value=[]}:{value?:string[]}) {
  if(isDecadeWide(value))return <div className="goal-labels"><span>Decade-wide · all 5 OCs and all 15 MGs</span></div>;
  return value.length ? <div className="goal-labels">{value.map(m=><span key={m}>{goalLabel(m)}</span>)}</div>:null;
}
