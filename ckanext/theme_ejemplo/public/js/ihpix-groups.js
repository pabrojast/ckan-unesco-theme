/* Planificación: guardado serializado, recuperación local y decisiones explícitas. */
(function () {
 'use strict';
 function init() {
 const root=document.getElementById('ihpix-groups');if(!root)return;
 const S=JSON.parse(document.getElementById('ixg-strings').textContent),feedback=document.getElementById('ixg-feedback');
 function notice(text,error){feedback.hidden=false;feedback.textContent=text;feedback.classList.toggle('ixg-error',!!error);}
 async function post(operation,body){
  let response,data;
  const url=root.dataset.api.replace('__operation__',operation);
  if(body.get('file') instanceof File){
   const widget=window.IhpixForms.get(document.querySelector('form[data-operation="'+operation+'"] [data-ihpix-upload]'));
   response=await window.IhpixForms.upload(url,body,{onProgress:value=>{if(widget)widget.setProgress(value);}});data=response.data;
   if(widget)widget.setProgress(null);
  }else{response=await fetch(url,{method:'POST',body,headers:{'X-Requested-With':'XMLHttpRequest'}});try{data=await response.json();}catch(_){throw {message:S.network};}}
  if(!response.ok||!data||!data.success)throw {message:data&&data.error||Object.values(data&&data.errors||{}).join(' · ')||S.network,fields:data&&data.errors||{},status:response.status};
  return data.result;
 }
 function formErrors(form,error){
  form.querySelectorAll('[data-error-for]').forEach(e=>e.textContent='');form.querySelectorAll('[aria-invalid]').forEach(e=>e.removeAttribute('aria-invalid'));
  for(const [key,value] of Object.entries(error.fields||{})){
   const box=Array.from(form.querySelectorAll('[data-error-for]')).find(e=>e.dataset.errorFor===key);if(box)box.textContent=String(value);
   const input=form.elements[key];if(input&&input.setAttribute)input.setAttribute('aria-invalid','true');
  }
  const box=form.querySelector('[data-form-error]');if(box)box.textContent=error.message||S.network;
  notice(error.message||S.network,true);
 }
 function busy(form,value){form.querySelectorAll('button').forEach(b=>b.disabled=value);form.setAttribute('aria-busy',String(value));const modal=form.closest('.ixf-modal');if(modal){modal.toggleAttribute('data-static',value);modal.querySelectorAll('[data-ihpix-modal-close]').forEach(b=>b.disabled=value);}}
 let editor=null;
 const planForm=document.getElementById('ixg-plan-form');
 if(planForm){
  const config=JSON.parse(document.getElementById('ixg-plan-config').textContent),status=document.getElementById('ixg-save-status'),reload=document.getElementById('ixg-plan-reload');
  let id=planForm.dataset.id,revision=Number(planForm.dataset.revision),requestId=planForm.dataset.requestId,flight=null,timer=null,conflict=false,unsafe=false,invalid=false,leaving=false,step='1';
  let key='ihpix-plan:'+root.dataset.user+':'+(id||'new:'+planForm.dataset.group);
  function read(){const data={};['title','description','output','key_activity_code','focal_point','email','institution','partners','member_state','planned_start','planned_end'].forEach(k=>data[k]=planForm.elements[k].value);data.periods={};config.biennia.forEach(b=>data.periods[b]=planForm.elements['period_'+b].value);['additional_outputs','associated_groups'].forEach(k=>data[k]=Array.from(planForm.elements[k].selectedOptions).map(o=>o.value));data.links=JSON.parse(planForm.elements.links.value||'[]');return data;}
  function options(selected){const field=planForm.elements.key_activity_code;field.replaceChildren(new Option('—',''));(config.keyActivities[planForm.elements.output.value]||[]).forEach(k=>field.add(new Option(k.code+' · '+k.title,k.code)));field.value=selected||'';}
  options(planForm.elements.key_activity_code.dataset.selected);
  function restore(data){Object.keys(data).forEach(k=>{const field=planForm.elements[k];if(field&&!['periods','links','additional_outputs','associated_groups','key_activity_code'].includes(k))field.value=data[k]||'';});options(data.key_activity_code);config.biennia.forEach(b=>planForm.elements['period_'+b].value=(data.periods||{})[b]||'');['additional_outputs','associated_groups'].forEach(k=>Array.from(planForm.elements[k].options).forEach(o=>o.selected=(data[k]||[]).includes(o.value)));planForm.elements.links.value=JSON.stringify(data.links||[]);}
  let saved=JSON.stringify(read());
  try{const local=JSON.parse(localStorage.getItem(key)||'null');if(local&&JSON.stringify(local.payload)!==saved){if(!id||Number(local.revision)===revision){restore(local.payload);requestId=local.requestId||requestId;if(!id&&local.id){id=local.id;revision=local.revision;}notice(S.restore);}else{conflict=true;reload.hidden=false;const recovery=document.getElementById('ixg-recovered-draft');recovery.hidden=false;recovery.querySelector('div').textContent=[local.payload.title,local.payload.description,...config.biennia.map(b=>b+': '+((local.payload.periods||{})[b]||'—'))].join('\n\n');notice(S.conflict,true);}}}catch(_){/* El servidor sigue disponible si falla el almacenamiento local. */}
  function localSave(){try{localStorage.setItem(key,JSON.stringify({payload:read(),revision,id,requestId}));unsafe=false;return true;}catch(_){unsafe=true;return false;}}
  function dirty(){return JSON.stringify(read())!==saved;}
  async function flush(){
   clearTimeout(timer);if(flight){await flight;if(dirty())return flush();return {id,revision};}
   if(conflict)throw {message:S.conflict};
   const payload=read();invalid=false;localSave();if(!payload.title.trim()){status.textContent=unsafe?S.unsafe:S.local;throw {message:S.required,fields:{title:S.required}};}
   if(!dirty()&&id)return {id,revision};
   status.textContent=S.saving;const raw=JSON.stringify(payload),body=new FormData();body.set('group_id',planForm.dataset.group);body.set('request_id',requestId);body.set('payload',raw);body.set('expected_revision',String(revision));if(id)body.set('id',id);const csrf=planForm.elements._csrf_token;if(csrf)body.set('_csrf_token',csrf.value);
   flight=post('plan_save',body).then(result=>{
    const oldKey=key;id=result.id;revision=result.revision;saved=raw;key='ihpix-plan:'+root.dataset.user+':'+id;
    if(oldKey!==key){try{localStorage.removeItem(oldKey);}catch(_){}}
    localSave();unsafe=false;status.textContent=S.saved;status.dataset.state='server';
    history.replaceState(null,'',planForm.dataset.editUrl.replace('__id__',encodeURIComponent(id))+'#step-'+step);
    document.querySelectorAll('form[data-plan-attachment] [name=plan_id]').forEach(e=>e.value=id);
    document.querySelectorAll('form[data-operation=plan_transition] [name=expected_revision]').forEach(e=>e.value=String(revision));
    return result;
   }).catch(error=>{if(error.status===400)invalid=true;if(error.status===409){conflict=true;reload.hidden=false;status.textContent=S.conflict;}else status.textContent=unsafe?S.unsafe:S.local;formErrors(planForm,error);throw error;}).finally(()=>{flight=null;if(dirty()&&!conflict&&!invalid)timer=setTimeout(()=>flush().catch(()=>{}),4000);});
   return flight;
  }
  function changes(){localSave();status.textContent=unsafe?S.unsafe:S.local;status.dataset.state='local';clearTimeout(timer);timer=setTimeout(()=>flush().catch(()=>{}),900);}
  planForm.addEventListener('input',e=>{if(!e.target.name.startsWith('reference_'))changes();});
  planForm.addEventListener('change',e=>{if(e.target.name==='output')options('');if(!e.target.name.startsWith('reference_'))changes();});
  function references(){const list=document.getElementById('ixg-references');list.replaceChildren();read().links.forEach((link,index)=>{const li=document.createElement('li'),a=document.createElement('a'),button=document.createElement('button');a.textContent=link.title||link.url;a.href=link.url;a.rel='noopener';button.type='button';button.className='btn';button.textContent='×';button.setAttribute('aria-label','Remove '+(link.title||''));button.onclick=()=>{const links=read().links;links.splice(index,1);planForm.elements.links.value=JSON.stringify(links);references();changes();};li.append(a,' ',button);list.append(li);});}
  window.ihpixLinks={add(link){const links=read().links;if(links.some(l=>l.url===link.url))return false;links.push(link);planForm.elements.links.value=JSON.stringify(links);references();changes();return true;}};
  references();document.getElementById('ixg-add-reference').onclick=()=>{const url=planForm.elements.reference_url.value.trim();if(!/^https?:\/\/\S+$/i.test(url)){notice(S.required,true);return;}window.ihpixLinks.add({title:planForm.elements.reference_title.value.trim()||url,url,target_kind:'url',link_type:'other'});planForm.elements.reference_title.value='';planForm.elements.reference_url.value='';};
  function summary(){const box=document.getElementById('ixg-plan-summary');box.replaceChildren();const p=read();[p.title,p.description,p.output+' · '+p.key_activity_code,p.focal_point+' · '+p.institution,(p.planned_start||'—')+' → '+(p.planned_end||'—'),...config.biennia.map(b=>b+': '+(p.periods[b]||'—'))].forEach(text=>{const el=document.createElement('p');el.className='ixg-preserve';el.textContent=text;box.append(el);});}
  function go(target){step=['1','2','3'].includes(target)?target:'1';document.querySelectorAll('[data-plan-panel]').forEach(el=>el.hidden=el.dataset.planPanel!==step);document.querySelectorAll('.ixg-steps [data-plan-step]').forEach(el=>el.toggleAttribute('aria-current',el.dataset.planStep===step));if(step==='3')summary();history.replaceState(null,'','#step-'+step);}
  document.querySelectorAll('[data-plan-step]').forEach(el=>el.onclick=()=>go(el.dataset.planStep));go(location.hash.replace('#step-',''));
  document.getElementById('ixg-plan-save').onclick=()=>flush().catch(e=>formErrors(planForm,e));
  reload.onclick=()=>{leaving=true;try{localStorage.removeItem(key);}catch(_){}location.reload();};
  planForm.addEventListener('submit',async event=>{event.preventDefault();busy(planForm,true);try{await flush();const body=new FormData();body.set('id',id);body.set('expected_revision',String(revision));body.set('operation','submit');if(planForm.elements._csrf_token)body.set('_csrf_token',planForm.elements._csrf_token.value);await post('plan_transition',body);try{localStorage.removeItem(key);}catch(_){}location.reload();}catch(error){go('1');formErrors(planForm,error);}finally{busy(planForm,false);}});
  document.querySelector('[data-open-plan-document]').onclick=async()=>{try{await flush();window.IhpixForms.Modal.open('#ixg-document-modal');}catch(e){go('1');formErrors(planForm,e);}};
  window.addEventListener('beforeunload',e=>{if(!leaving&&(dirty()||flight)){localSave();e.preventDefault();e.returnValue=S.leave;}});
  document.addEventListener('click',async e=>{const a=e.target.closest('a[href]');if(!a||a.target==='_blank'||a.hash&&a.pathname===location.pathname||!(dirty()||flight))return;if(a.origin!==location.origin)return;e.preventDefault();try{await flush();location.href=a.href;}catch(_){notice(S.unsafe,true);}},true);
  editor={flush,getId:()=>id,setRevision:r=>{revision=r;localSave();document.querySelectorAll('form[data-operation=plan_transition] [name=expected_revision]').forEach(e=>e.value=String(r));}};if(dirty()&&!conflict)changes();
 }
 document.querySelectorAll('[data-replace-document]').forEach(button=>button.onclick=()=>{const modal=document.getElementById('ixg-document-modal'),form=modal.querySelector('form');form.elements.replaces_id.value=button.dataset.replaceDocument;form.elements.plan_id.value=button.dataset.planId;form.elements.category.value=button.dataset.category;form.elements.title.value=button.dataset.title;window.IhpixForms.Modal.open(modal);});
 document.querySelectorAll('form[data-operation]').forEach(form=>form.addEventListener('submit',async event=>{
  event.preventDefault();if(form.dataset.busy)return;form.dataset.busy='1';busy(form,true);
  try{
   if(editor)await editor.flush();
   const body=new FormData(form);if(event.submitter&&event.submitter.name)body.set(event.submitter.name,event.submitter.value);
   if(form.elements.outputs){const outputs=Array.from(form.querySelectorAll('[name=outputs]')).flatMap(el=>el.tagName==='SELECT'?Array.from(el.selectedOptions).map(o=>o.value):(el.checked?[el.value]:[]));body.set('outputs',JSON.stringify(outputs));}
   if(form.hasAttribute('data-contact-form')){const payload={};['name','email','institution','job_title','country','region','language','role'].forEach(k=>payload[k]=form.elements[k].value);body.set('payload',JSON.stringify(payload));}
   if(form.id==='ixg-import-apply'){
    const rows=Array.from(form.querySelectorAll('[data-index]')).map(row=>{const decision=row.querySelector('[name=decision]').value,payload={},periods={};row.querySelectorAll('[data-import-fields] [name]').forEach(el=>{if(el.name.startsWith('period_'))periods[el.name.slice(7)]=el.value;else payload[el.name]=el.value;});if(Object.keys(periods).length)payload.periods=periods;const target=row.querySelector('[name=target_id]');return {index:Number(row.dataset.index),decision,payload,target_id:target?target.value:'',expected_revision:target?Number(target.selectedOptions[0].dataset.revision):0};});body.set('rows',JSON.stringify(rows));
   }
   const result=await post(form.dataset.operation,body);if(editor&&result.plan_revision)editor.setRevision(result.plan_revision);notice(S.done);
   if(form.dataset.importRedirect)location.href=form.dataset.importRedirect.replace('__id__',encodeURIComponent(result.id));
   else if(form.dataset.reportRedirect)location.href=form.dataset.reportRedirect.replace('__id__',encodeURIComponent(result.id));
   else if(form.hasAttribute('data-plan-attachment')){
    const p=document.createElement('p'),a=document.createElement('a');a.href=location.pathname.split('/plans/')[0]+'/documents/'+result.id;a.textContent=form.elements.title.value||form.elements.file.files[0].name;p.append(a);document.getElementById('ixg-plan-documents').append(p);window.IhpixForms.Modal.close(form.closest('.ixf-modal'));form.reset();form.elements.plan_id.value=editor.getId();window.IhpixForms.refresh(form);
   }else location.reload();
  }catch(error){formErrors(form,error);}finally{busy(form,false);delete form.dataset.busy;}
 }));
 document.querySelectorAll('.ixg-plan-table').forEach(table=>{const labels=Array.from(table.querySelectorAll('th')).map(el=>el.textContent);table.querySelectorAll('tbody tr').forEach(row=>Array.from(row.cells).forEach((cell,i)=>cell.dataset.label=labels[i]||''));});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
