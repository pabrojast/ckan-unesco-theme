"""Ejecuta el submit real: un input name=id no debe ocultar las filas elegidas."""
import pathlib
import shutil
import subprocess

import pytest


def test_selected_import_rows_reach_the_server_when_id_is_a_named_control():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is required for the browser-handler contract')
    source = pathlib.Path(__file__).parents[1] / 'public/js/ihpix-groups.js'
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
let submit,posted;
const row={dataset:{index:'0'},querySelector:s=>s==='[name=decision]'?{value:'new'}:null,
 querySelectorAll:()=>[{name:'title',value:'Synthetic plan'},{name:'period_2026-2027',value:'A workshop'}]};
// HTMLFormElement named access: <input name="id"> shadows the id property.
const form={id:{value:'batch-id'},dataset:{operation:'group_import_apply'},elements:{},
 getAttribute:key=>key==='id'?'ixg-import-apply':null,
 querySelectorAll:s=>s==='[data-index]'?[row]:[],setAttribute:()=>{},closest:()=>null,
 hasAttribute:()=>false,addEventListener:(_,fn)=>{submit=fn}};
const root={dataset:{api:'/group-api/__operation__'}},feedback={classList:{toggle:()=>{}}};
const document={readyState:'complete',getElementById:id=>({'ihpix-groups':root,'ixg-strings':{textContent:'{}'},'ixg-feedback':feedback}[id]||null),
 querySelectorAll:s=>s==='form[data-operation]'?[form]:[]};
class FormData {constructor(){this.values=new Map([['id','batch-id']]);} get(k){return this.values.get(k)} set(k,v){this.values.set(k,v)}}
const context={document,FormData,File:class {},location:{reload:()=>{}},fetch:async(_,opts)=>{posted=opts.body;return {ok:true,json:async()=>({success:true,result:{ids:['created-id']}})}}};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),context);
(async()=>{await submit({preventDefault:()=>{}});assert(posted,'submit must call the API');
const rows=JSON.parse(posted.get('rows')||'[]');assert.equal(rows.length,1,'selected rows must not disappear');
assert.equal(rows[0].decision,'new');assert.equal(rows[0].index,0);
assert.equal(rows[0].payload.title,'Synthetic plan');assert.equal(rows[0].payload.periods['2026-2027'],'A workshop');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    subprocess.run([node, '-e', script, str(source)], check=True, capture_output=True, text=True)
