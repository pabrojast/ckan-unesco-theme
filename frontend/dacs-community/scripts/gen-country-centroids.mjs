import {readFileSync,writeFileSync} from 'node:fs';
import {feature} from 'topojson-client';
import {geoCentroid,geoArea} from 'd3-geo';
const topo=JSON.parse(readFileSync('node_modules/world-atlas/countries-50m.json','utf8'));
const fc=feature(topo,topo.objects.countries);
const out={};
for(const f of fc.features){
  const name=f.properties?.name; if(!name)continue;
  let g=f.geometry; if(!g)continue;
  if(g.type==='MultiPolygon'){let best=null,area=-1;for(const c of g.coordinates){const p={type:'Polygon',coordinates:c};const a=geoArea(p);if(a>area){area=a;best=p;}}g=best;}
  const [lon,lat]=geoCentroid({type:'Feature',geometry:g});
  out[name]=[Math.round(lon*10)/10,Math.round(lat*10)/10];
}
const lines=Object.keys(out).sort().map(k=>`  ${JSON.stringify(k)}: [${out[k][0]}, ${out[k][1]}],`);
writeFileSync(process.argv[2],`// Approximate centre of each country (largest land area), derived from Natural Earth 1:50m data (world-atlas package).
// Used to place member counts on the map. Generated file.
export const countryCentroids: Record<string, [number, number]> = {
${lines.join('\n')}
};
`);
console.log(Object.keys(out).length);
