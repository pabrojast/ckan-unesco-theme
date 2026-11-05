import { groups } from "@/lib/data";

const nodes = [
  {id:'unesco',x:150,y:30,w:185,h:150,lines:['UNESCO–IHP','UNESCO Secretariat','Host and support'],kind:'host'},
  {id:'esc',x:390,y:30,w:235,h:66,lines:['Executive Steering','Committee'],kind:'management'},
  {id:'smc',x:390,y:135,w:235,h:66,lines:['Strategic Management','Committee'],kind:'management'},
  {id:'liaison',x:755,y:135,w:205,h:66,lines:['Liaison to other','initiatives'],kind:'liaison'},
  {id:'iac',x:25,y:280,w:205,h:70,lines:['Indigenous Advisory','Committee'],kind:'advisory'},
  {id:'alliance',x:265,y:280,w:205,h:70,lines:['Alliance for the','Cryosphere'],kind:'strategy'},
  {id:'cfd',x:505,y:280,w:205,h:70,lines:['Cryosphere Finance','Dialogue'],kind:'strategy'},
  {id:'working-groups',x:755,y:280,w:205,h:70,lines:['Working Groups'],kind:'strategy'},
  ...[1,2,3,4,5].map((n)=>({id:'wg'+n,x:70+(n-1)*180,y:420,w:140,h:62,lines:['WG'+n,groups[n-1].short],kind:'working'})),
  {id:'partners',x:285,y:550,w:440,h:60,lines:['Implementing partners'],kind:'partners'},
];
export function GovernanceChart({selected,onSelect}:{selected:string;onSelect:(id:string)=>void}) {
  const interactive=(id:string)=>!['liaison','working-groups','partners'].includes(id);
  return <section className="glass governance-chart-panel" aria-label="Decade governance model">
    <div className="governance-chart-scroll">
      <svg viewBox="0 0 1000 635" className="governance-chart" role="group" aria-labelledby="governance-chart-title governance-chart-desc">
        <title id="governance-chart-title">Governance of the Cryosphere Decade</title>
        <desc id="governance-chart-desc">UNESCO–IHP hosts the Secretariat and supports management. The Strategic Management Committee reports to the Executive Steering Committee and IHP, coordinates five Working Groups and receives reports from the Cryosphere Finance Dialogue. Indigenous advice, the Alliance and liaison support the Decade. Partners deliver through the Working Groups. Select a body to see its appointments.</desc>
        <defs><marker id="liaison-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="currentColor"/></marker></defs>
        <g className="governance-lines" fill="none" strokeWidth="2">
          <path d="M335 105 H355 V63 H390 M355 105 V168 H390 M507.5 96 V135"/>
          <path d="M645 168 H735" markerStart="url(#liaison-arrow)" markerEnd="url(#liaison-arrow)"/>
          <path d="M410 201 V250 H127.5 V280" strokeDasharray="7 6"/>
          <path d="M442 201 V250 H367.5 V280 M557 201 V250 H607.5 V280 M590 201 V230 H857.5 V280"/>
          <path d="M857.5 350 V385 H140 V420 M320 385 V420 M500 385 V420 M680 385 V420 M860 385 V420"/>
          <path d="M140 482 V520 H860 V482 M320 482 V520 M500 482 V550 M680 482 V520"/>
        </g>
        {nodes.map(n=><g key={n.id} className={'governance-node '+n.kind+(selected===n.id?' selected':'')}
          style={n.kind==='working'?{'--wg-color':groups[Number(n.id.slice(2))-1].color,'--wg-ink':groups[Number(n.id.slice(2))-1].ink} as React.CSSProperties:undefined}
          role={interactive(n.id)?'button':'group'} tabIndex={interactive(n.id)?0:undefined}
          aria-label={n.lines.join(' · ')} aria-pressed={interactive(n.id)?selected===n.id:undefined}
          onClick={()=>interactive(n.id)&&onSelect(n.id)}
          onKeyDown={e=>{if(interactive(n.id)&&['Enter',' '].includes(e.key)){e.preventDefault();onSelect(n.id)}}}>
          <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="14"/>
          <text textAnchor="middle" x={n.x+n.w/2} y={n.y+n.h/2-(n.lines.length-1)*10+5}>
            {n.lines.map((line,i)=><tspan key={line} x={n.x+n.w/2} dy={i===0?0:20} className={n.kind==='working'&&i===1||n.kind==='host'&&i===2?'node-subtitle':''}>{line}</tspan>)}
          </text>
        </g>)}
      </svg>
    </div>
    <p className="micro chart-caption">Select a body to view appointments. DACS synthesis, pp. 14–15. Dashed outline: IAC role and placement subject to consultation.</p>
  </section>;
}
