"""Integración exclusiva de QA: calendario, permisos y paso al reporte."""
import json,uuid
from ckan.cli import load_config
from ckan.config.middleware import make_app
config=load_config('/qa/app.ini');assert 'ihpix-form-db/ihpix_form' in config['sqlalchemy.url'];make_app(config)
import ckan.model as m
import ckan.plugins.toolkit as tk
from ckanext.theme_ejemplo import ihpix_groups as G,ihpix_group_store as D,ihpix_calendar as C
from ckanext.theme_ejemplo.model import IhpixActivity
checks=[]
def check(name,v):assert v,name;checks.append(name)
def call(op,data,who='author'):
 u=m.User.get('qa-form-'+who);return tk.get_action('ihpix_'+op)({'user':u.name,'auth_user_obj':u,'model':m},data)
p=call('plan_save',dict(group_id='oetwg-4',request_id=str(uuid.uuid4()),payload=dict(title='Calendar QA',description='Plan only',output='4.1',key_activity_code='4.1.1',focal_point='Author',email='qa@example.test',institution='QA institute',periods={'2026-2027':'Pilot','2028-2029':'Follow-up'},additional_outputs=['4.2'],planned_start='2026-11-09',planned_end='2026-11-13')))
check('draft dates saved',p['payload']['planned_start']=='2026-11-09')
g=call('group_show',dict(group_id='oetwg-4'),'other');check('private draft absent from observer calendar',p['id'] not in [e['id'] for e in C.month_view(g['plans'],g['items'],'2026-11')['events']])
p=call('plan_transition',dict(id=p['id'],expected_revision=p['revision'],operation='submit'));p=call('plan_transition',dict(id=p['id'],expected_revision=p['revision'],operation='approve'),'admin')
g=call('group_show',dict(group_id='oetwg-4'),'other');check('approved schedule visible',p['id'] in [e['id'] for e in C.month_view(g['plans'],g['items'],'2026-11')['events']])
try:call('plan_report_create',dict(id=p['id'],request_id=str(uuid.uuid4())))
except tk.ValidationError:check('ambiguous biennium requires choice',True)
else:raise AssertionError('ambiguous period accepted')
shared_request=str(uuid.uuid4())
def report(b):return call('plan_report_create',dict(id=p['id'],request_id=shared_request,biennium=b))
r=report('2026-2027');r2=call('plan_report_create',dict(id=p['id'],request_id=str(uuid.uuid4()),biennium='2026-2027'));check('different clicks resume same draft',r['id']==r2['id'])
a=IhpixActivity.get(r['id']);check('selected period and context copied',a.biennium=='2026-2027' and a.institution=='QA institute');check('actual dates and results remain empty',not a.start_date and not a.end_date and not a.outcomes and not a.description)
check('additional outputs copied into linked report',{c['output'] for c in json.loads(a.contributions_json)}=={'4.1','4.2'})
r3=report('2028-2029');check('another period gets separate report',r['id']!=r3['id'])
p=call('plan_save',dict(group_id='oetwg-4',id=p['id'],expected_revision=p['revision'],payload=dict(p['payload'],planned_start='2026-12-01',planned_end='2026-12-03')))
g=call('group_show',dict(group_id='oetwg-4'),'other');events=C.month_view(g['plans'],g['items'],'2026-11')['events'];check('pending revision does not replace approved calendar',next(e for e in events if e['id']==p['id'])['start']=='2026-11-09')
from pathlib import Path
Path('/qa/calendar-fixture.json').write_text(json.dumps(dict(plan=p['id'],report=r['id'])))
# Filas idénticas se consolidan conservando ambas procedencias.
import io,base64
from openpyxl import Workbook
book=Workbook();sheet=book.active;sheet.title='4.1';sheet.append(['Proposed activities']);sheet.append(['Key activity 1. Research']);title='Duplicate source '+str(uuid.uuid4());sheet.append([title]);sheet.append([title]);buf=io.BytesIO();book.save(buf)
batch=call('group_import_preview',dict(group_id='oetwg-4',kind='plans',filename='duplicates.xlsx',workbook=base64.b64encode(buf.getvalue()).decode()),'admin')
result=call('group_import_apply',dict(id=batch['id'],rows=[dict(index=i,decision='new') for i in range(2)]),'admin')
check('duplicate source rows produce one plan',len(set(result['ids']))==1)
origin=json.loads(D.row(D.plans,result['ids'][0])['origin']);check('both original rows remain attached',len(origin['sources'])==2 and {r['row'] for r in origin['sources']}=={3,4})
print(json.dumps(dict(passed=len(checks),checks=checks)))
