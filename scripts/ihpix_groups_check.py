"""Integración destructiva exclusivamente en la base local desechable de QA."""
import io,json,uuid,base64
from pathlib import Path
from urllib.parse import urlparse
from ckan.cli import load_config
from ckan.config.middleware import make_app
config=load_config('/qa/app.ini');connection=urlparse(config['sqlalchemy.url'])
assert connection.hostname=='ihpix-form-db' and connection.path=='/ihpix_form'
app=make_app(config)
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.theme_ejemplo import ihpix_groups as G,ihpix_group_store as D,ihpix_planning as P
from ckanext.theme_ejemplo.model import IhpixActivity,IhpixWorkingGroup,IhpixWorkingGroupMember
from werkzeug.datastructures import FileStorage
checks=[]
def check(name,value):
 assert value,name
 checks.append(name)
def ctx(name='author'):
 u=model.User.get('qa-form-'+name);return dict(user=u.name,auth_user_obj=u,model=model)
def call(name,data,actor='author'):return tk.get_action('ihpix_'+name)(ctx(actor),data)
def rejects(name,data,actor='author',exc=tk.NotAuthorized):
 try:call(name,data,actor)
 except exc:model.Session.rollback();return True
 raise AssertionError('Expected rejection: '+name)
def add(name,role='contributor'):
 return call('group_member_save',dict(group_id='oetwg-4',user_id=ctx(name)['user'],operation='manage',role=role),'admin')
def payload(**kw):
 d=dict(title='QA '+str(uuid.uuid4()),description='Future assessment',output='4.1',key_activity_code='4.1.1',periods={'2026-2027':'Pilot'},focal_point='Researcher',email='test@example.test',institution='Institute');d.update(kw);return d
# Algunos proveedores entregan AnonymousUser en vez de None.
from types import SimpleNamespace
for anonymous in (None,SimpleNamespace(),SimpleNamespace(state='deleted')):
 try:G.actor({'auth_user_obj':anonymous,'user':''})
 except tk.NotAuthorized:check('anonymous or inactive actor denied',True)
 else:raise AssertionError('Anonymous actor accepted')

add('author');add('other','observer')
published_before=model.Session.query(IhpixActivity).filter_by(status='published').count()
check('eight seeded groups',len(call('group_list',{})['results'])==8)
check('observer cannot create plan',rejects('plan_save',dict(group_id='oetwg-4',payload=payload(),request_id=str(uuid.uuid4())),'other'))
request=dict(group_id='oetwg-4',payload=payload(),request_id=str(uuid.uuid4()))
p=call('plan_save',request);id=p['id']
check('same request creates one plan',call('plan_save',request)['id']==id)
check('draft private to author and responsible',rejects('plan_show',{'id':id},'other'))
check('revision conflict preserves draft',rejects('plan_save',dict(request,id=id,payload=payload(),expected_revision=0),exc=tk.ValidationError))
check('missing id does not create a plan',rejects('plan_save',dict(request,id='missing'),exc=tk.ObjectNotFound))
def doc(name):return call('group_document_save',dict(group_id='oetwg-4',plan_id=id,category='planning',upload=FileStorage(io.BytesIO(name.encode()),filename=name+'.txt')))
d1=doc('first');p=call('plan_show',{'id':id})
check('draft attachment private',rejects('group_document_show',{'id':d1['id']},'other'))
p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='submit'))
check('observer reads submitted plan',call('plan_show',{'id':id},'other')['payload']['title']==p['payload']['title'])
check('submitted plan cannot change',rejects('plan_save',dict(request,id=id,payload=payload(),expected_revision=p['revision']),exc=tk.ValidationError))
check('contributor cannot approve',rejects('plan_transition',dict(id=id,expected_revision=p['revision'],operation='approve')))
p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='return',note='Add detail'),'admin')
check('returned reason preserved',p['review_status']=='returned' and p['review_note']=='Add detail')
p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='submit'))
p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='approve'),'admin')
agreed=p['payload']['title']
check('approved attachment visible',call('group_document_show',{'id':d1['id']},'other')['id']==d1['id'])
d2=doc('revision');p=call('plan_show',{'id':id})
check('new attachment opens draft revision',p['review_status']=='draft')
check('new attachment hidden until approval',rejects('group_document_show',{'id':d2['id']},'other'))
p=call('plan_save',dict(request,id=id,payload=dict(request['payload'],title='Changed draft'),expected_revision=p['revision']))
check('reader sees agreed snapshot',call('plan_show',{'id':id},'other')['payload']['title']==agreed)
request_report=dict(id=id,request_id=str(uuid.uuid4()))
r=call('plan_report_create',request_report)
check('report creation idempotent',call('plan_report_create',request_report)['id']==r['id'])
report=IhpixActivity.get(r['id'])
check('plan creates draft report without fabricated execution',report.status=='draft' and report.title==agreed and not report.description and not report.outcomes and not report.end_date and report.kpi_1a_active is None and not report.num_knowledge_products)
check('plan does not alter published report count',model.Session.query(IhpixActivity).filter_by(status='published').count()==published_before)
check('unrelated group not granted by output lead',not G.manager(ctx()['auth_user_obj'],'oetwg-4'))
contact=dict(group_id='oetwg-4',payload={'name':'Jane','email':'jane@example.test'},outputs=['4.1'])
c=call('group_contact_save',contact,'admin')
check('contact retry no duplicate',call('group_contact_save',contact,'admin')['id']==c['id'])
check('contact cannot grant account privileges',rejects('group_contact_save',dict(contact,user_id=ctx()['user']),'admin',tk.ValidationError))
item=call('group_item_save',dict(group_id='oetwg-4',kind='task',body='Follow up',assignee_id=ctx()['user']))
check('task update version conflict',rejects('group_item_save',dict(group_id='oetwg-4',id=item['id'],expected_revision=0,status='done'),exc=tk.ValidationError))
# Una vista previa no escribe actividades; se confirma sólo el fixture sintético.
from openpyxl import Workbook
book=Workbook();s=book.active;s.title='4.1';s.append(['Proposed activities']);s.append(['Key activity 1. Research']);s.append(['Imported QA '+str(uuid.uuid4()),None,None,'Pilot',None,'Jane','jane@example.test','Institute'])
buffer=io.BytesIO();book.save(buffer)
preview=dict(group_id='oetwg-4',kind='plans',filename='fixture.xlsx',workbook=base64.b64encode(buffer.getvalue()).decode())
batch=call('group_import_preview',preview,'admin');before=len(D.rows(D.plans))
check('preview does not create plans',len(D.rows(D.plans))==before)
check('preview retry same batch',call('group_import_preview',preview,'admin')['id']==batch['id'])
choice=dict(id=batch['id'],rows=[{'index':0,'decision':'new','payload':{}}]);result=call('group_import_apply',choice,'admin')
check('confirmation idempotent',call('group_import_apply',choice,'admin')==result and len(D.rows(D.plans))==before+1)
check('contacts and plans grant no memberships',len(D.rows(D.members))==2)
# El mismo título del reporte histórico se ofrece para conciliar, sin sobrescribirlo.
book=Workbook();s=book.active;s.title='4.1.';s.append(['Name of the Implemented Activity','Description of the Implemented Activity']);s.append([agreed,'Measured results']);buffer=io.BytesIO();book.save(buffer)
batch=call('group_import_preview',dict(preview,kind='execution',workbook=base64.b64encode(buffer.getvalue()).decode()),'admin')
check('legacy report matching detects existing report',r['id'] in batch['payload'][0]['match']['candidates'])
linked=call('group_import_apply',dict(id=batch['id'],rows=[{'index':0,'decision':'existing','target_id':r['id']}]),'admin')
check('matching does not overwrite report',linked['ids']==[r['id']] and not IhpixActivity.get(r['id']).description)
# La revocación y archivo se evalúan en cada operación.
call('group_member_save',dict(group_id='oetwg-4',operation='manage',user_id=ctx()['user'],status='removed'),'admin')
check('revoked author cannot read plan',rejects('plan_show',{'id':id}))
g=G.group('oetwg-4');call('group_update',dict(group_id=g['id'],expected_revision=g['revision'],status='archived'),'admin')
check('archived group prevents writes even for administrator',rejects('plan_save',dict(request,id=id,expected_revision=p['revision']),'admin'))
g=G.group('oetwg-4');call('group_update',dict(group_id=g['id'],expected_revision=g['revision'],status='active'),'admin');add('author')

# Un lead conserva permisos de su Output sin recibir un rol de grupo.
lead=model.User.get('qa-form-lead')
if not lead:
 lead=model.User(name='qa-form-lead',email='lead@example.test',password='qa-only-password',state='active');model.Session.add(lead);model.Session.commit()
wg=IhpixWorkingGroup.get_by_output('4.1')
member=IhpixWorkingGroupMember.get_membership(wg.id,lead.id)
if not member:model.Session.add(IhpixWorkingGroupMember(wg.id,lead.id,role='lead',status='active'));model.Session.commit()
add('author');add('other','observer')
p=call('plan_save',dict(group_id='oetwg-4',request_id=str(uuid.uuid4()),payload=payload()))
id=p['id'];doc=call('group_document_save',dict(group_id='oetwg-4',plan_id=id,category='other',upload=FileStorage(io.BytesIO(b'private'),filename='private.txt')))
p=call('plan_show',{'id':id});p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='submit'))
check('output lead without group membership reads submitted plan',call('plan_show',{'id':id},'lead')['id']==id)
check('output lead reads proposal attachment',call('group_document_show',{'id':doc['id']},'lead')['id']==doc['id'])
p=call('plan_transition',dict(id=id,expected_revision=p['revision'],operation='approve'),'lead')
check('output lead can approve only own output',p['review_status']=='approved')
check('output lead gains no group manager role',not G.manager(lead,'oetwg-4'))
check('output lead cannot read group contacts',not call('group_show',{'group_id':'oetwg-4'},'lead')['can_read'])
request=dict(group_id='oetwg-4',request_id=str(uuid.uuid4()),payload=payload(output='4.2',key_activity_code='4.2.1'))
other=call('plan_save',request)
check('lead cannot read unrelated output draft',rejects('plan_show',{'id':other['id']},'lead'))
Path('/qa/group-service-result.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2))
print('Passed',len(checks),'group service checks')
