#!/usr/bin/env python3
"""Regresión sobre la instancia QA aislada; ver Testing.md."""
import sys,json,os,base64,io,uuid
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()));from ihpix_review_acceptance import api,check,full_payload
from openpyxl import load_workbook
import requests
fixtures=json.loads(Path(os.environ['IHPIX_QA_FIXTURES']).read_text())
users={r:api('user_show',{'id':'ihpix-review-'+r},role='admin')['id'] for r in ('author','collaborator')}
state=api('ihpix_working_group_show',{'id':'1.10'},role='collaborator').get('my_membership')
if not state or state['status']=='removed':state=api('ihpix_working_group_join',{'id':'1.10'},role='collaborator')
if state['status']=='pending':api('ihpix_working_group_member_process',{'membership_id':state['id'],'action':'approve'},role='admin')
private={'link_type':'dataset','target_kind':'package','target_id':fixtures['package'],'title':'PRIVATE QA DATASET','url':'https://example.invalid/private'}
payload=full_payload('Privacy QA '+uuid.uuid4().hex[:8]);payload['links_json']=[private];payload.update(has_member_state_support='yes',supporters_json=[{'country':'EG','types':['hosting']}])
a=api('ihpix_report_submit',payload);rid=a['id'];api('ihpix_report_collaborator_update',{'id':rid,'user_id':users['collaborator']})
shared=api('ihpix_report_show',{'id':rid},role='collaborator');check('private resource hidden from collaborator',not shared['links'])
form=shared['form'];form.update(id=rid,expected_revision=a['revision'],save_as_draft='1',links_json=[],title='Collaborator edited title')
a=api('ihpix_report_update',form,role='collaborator');check('save response hides private attachment',not a['links']);check('collaborator save preserves invisible private attachment',len(api('ihpix_report_show',{'id':rid})['links'])==1)
history=api('ihpix_report_collaboration_show',{'id':rid},role='collaborator');check('history does not reveal private resource title or ID','PRIVATE QA DATASET' not in json.dumps(history) and fixtures['package'] not in json.dumps(history))
# HTML conflict exposes current data through the shared controller.
from ihpix_review_acceptance import TOKENS,BASE
p=dict(form,expected_revision=1);p={k:json.dumps(v) if isinstance(v,(list,dict)) else v for k,v in p.items()}
r=requests.post(BASE+'/ihpix/report/'+rid+'/edit',data=p,headers={'Authorization':TOKENS['collaborator'],'X-Requested-With':'XMLHttpRequest'},timeout=60)
check('conflict response redacts private attachments',r.status_code==409 and fixtures['package'] not in r.text and 'PRIVATE QA DATASET' not in r.text)
task=api('ihpix_workspace_item_save',{'working_group_id':'1.10','kind':'task','title':'Assigned to collaborator','body':'Complete this task','assignee_id':users['collaborator']})
listed=api('ihpix_workspace_item_list',{'working_group_id':'1.10'},role='collaborator')['results'];item=next(x for x in listed if x['id']==task['id']);check('task assignee receives status-only capability',item['can_update_status'] and not item['can_edit'])
api('ihpix_workspace_item_save',{'working_group_id':'1.10','id':task['id'],'expected_revision':1,'status':'completed','_csrf_token':'transport-token'},role='collaborator');check('status-only task update accepts CSRF transport field')
# Pending report permits revocation and admin attachment editing keeps status.
a=api('ihpix_report_update',dict(payload,id=rid,expected_revision=a['revision'],save_as_draft=''));api('ihpix_report_collaborator_update',{'id':rid,'user_id':users['collaborator'],'revoke':True});api('ihpix_report_show',{'id':rid},role='collaborator',success=False);check('revoke works after submission')
link=api('ihpix_activity_link_create',{'activity_id':rid,'expected_revision':a['revision'],'link_type':'dataset','target_kind':'url','url':'https://example.org/public','title':'Public reference'},role='admin');check('admin attachment mutation retains pending status',api('ihpix_report_show',{'id':rid})['status']=='pending')
api('ihpix_report_review',{'id':rid,'action':'approve'},role='admin')
for filters in ({'country':'EG'},{'region':'Arab States'},{'output':'2.1'}):
 rows=api('ihpix_activity_list',dict(filters,limit=1000))['results'];check('published filter matches structured geography '+str(filters),rid in [x['id'] for x in rows])
legacy=api('ihpix_dashboard_stats',{'country':'EG'});progress=api('ihpix_progress_stats',{'scope':'overall','country':'EG'});check('dashboard country totals agree across both APIs',legacy['total_countries']==progress['overview']['member_states_impacted'] and any(x['name']=='Egypt' for x in legacy['by_country']));
geo=api('ihpix_geojson',{'output':'2.1'});chile=next(x['properties'] for x in geo['features'] if x['properties']['country']=='Chile');check('secondary PA is counted on country map',chile['pa2_count']>=1)
book=load_workbook(io.BytesIO(requests.get(BASE+'/ihpix/import/template.xlsx',headers={'Authorization':TOKENS['author']}).content));heads=[x.value for x in book['Activities'][1]];book['Activities'].append([{'row_ref':'A','title':'Bad reference '+uuid.uuid4().hex}.get(x,'') for x in heads]);book['Resources'].append(['A','dataset','package','does-not-exist','Unknown','','','']);b=io.BytesIO();book.save(b);preview=api('ihpix_import_preview',{'workbook':base64.b64encode(b.getvalue()).decode()});check('inaccessible import resource rejected with source cell',any(e['sheet']=='Resources' and e['cell']=='D2' for e in preview['preview']['errors']))
api('ihpix_report_delete',{'id':rid},role='admin');print('PRIVATE RESOURCE REGRESSIONS COMPLETE')
