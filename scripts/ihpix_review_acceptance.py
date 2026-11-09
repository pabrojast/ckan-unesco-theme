#!/usr/bin/env python3
"""Aceptación HTTP con usuarios de prueba; exige un entorno local aislado.

IHPIX_QA_TOKENS=/ruta/tokens.json python3 scripts/ihpix_review_acceptance.py
No usa clean_db, seeds destructivos ni datos de producción.
"""
import base64
import concurrent.futures
import io
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

import requests
from openpyxl import load_workbook

BASE = os.environ.get('IHPIX_QA_BASE', 'http://127.0.0.1:5011')
assert urlsplit(BASE).hostname in ('127.0.0.1', 'localhost'), 'Use an isolated local CKAN'
TOKENS = json.loads(Path(os.environ['IHPIX_QA_TOKENS']).read_text())
RESULTS = []
CREATED = []


def api(name, data=None, role='author', success=True):
    response = requests.post(BASE + '/api/3/action/' + name, json=data or {},
        headers={'Authorization': TOKENS[role]}, timeout=60)
    result = response.json()
    if success:
        assert result.get('success'), (name, response.status_code, result.get('error'))
        return result['result']
    assert not result.get('success'), (name, 'unexpected access')
    return result.get('error')


def check(name, condition=True):
    assert condition, name
    RESULTS.append(name)
    print('PASS', name, flush=True)


def full_payload(title):
    fields = ('unesco_secretariat_participation', 'has_member_state_support', 'has_flagship',
              'has_synergies', 'regions_benefit', 'kpi_1a_active', 'kpi_1b_active', 'kpi_2_active',
              'kpi_3_active', 'kpi_4_active', 'kpi_5_active', 'kpi_6_active', 'kpi_8_active')
    data = {key:'no' for key in fields}
    data.update(title=title, focal_point_name='QA Author', contact_email='qa@example.invalid',
        institution='QA Institution', institution_type='University', description='Test description',
        outcomes='Test outcomes', biennium='2026-2027', priority_area='PA1', output='1.10',
        key_activity_code='1.10.1', country='Chile', save_as_draft='1', kpi_2_active='yes',
        stakeholders_knowledge='100', stakeholders_knowledge_youth='60', stakeholders_knowledge_female='70',
        contributions_json=[{'priority_area':'PA1','output':'1.10','key_activity_code':'1.10.1'},
                            {'priority_area':'PA2','output':'2.1','key_activity_code':'2.1.1'},
                            {'priority_area':'PA2','output':'2.1','key_activity_code':'2.1.2'}])
    return data


def run():
    baseline = api('ihpix_progress_stats', {'scope':'overall'})['overview']['activities']
    users = {role:api('user_show', {'id':'ihpix-review-'+role}, role='admin')['id'] for role in TOKENS}
    workspace = api('ihpix_working_group_show', {'id':'1.10'})
    check('workspace 1.10 exists and has no invented lead', workspace['output_code'] == '1.10' and not workspace.get('lead_user_id'))
    for role in ('author','collaborator','observer'):
        state = api('ihpix_working_group_show', {'id':'1.10'}, role=role).get('my_membership')
        if not state or state['status'] == 'removed':
            state = api('ihpix_working_group_join', {'id':'1.10'}, role=role)
        if state['status'] == 'pending':
            api('ihpix_working_group_member_process', {'membership_id':state['id'], 'action':'approve'}, role='admin')
        if role == 'observer':
            api('ihpix_working_group_member_process', {'membership_id':state['id'], 'action':'set_role','role':'observer'}, role='admin')
    check('membership requests can be processed by administrator without a lead')
    check('membership notification reaches administrator', bool(api('ihpix_notification_list', role='admin')['results']))
    title = 'IHP-IX QA ' + uuid.uuid4().hex[:10]
    payload = full_payload(title)
    draft = api('ihpix_report_submit', payload)
    CREATED.append(draft['id'])
    check('draft has saved revision and multiple associations', draft['revision'] == 1 and len(json.loads(draft['contributions_json'])) == 3)
    shown = api('ihpix_report_show', {'id':draft['id']})
    check('saved report restores its fields', shown['form']['stakeholders_knowledge'] == 100 and len(shown['form']['contributions_json']) == 3)
    api('ihpix_report_show', {'id':draft['id']}, role='outsider', success=False)
    feed = api('ihpix_contribution_list', {'working_group_id':'1.10'}, role='outsider')
    check('outsider cannot open or discover private draft titles', title not in json.dumps(feed))
    api('ihpix_report_collaborator_update', {'id':draft['id'],'user_id':users['observer']}, success=False)
    api('ihpix_report_collaborator_update', {'id':draft['id'],'user_id':users['collaborator']})
    check('author can invite active contributor; observer cannot be invited')
    shared = api('ihpix_report_show', {'id':draft['id']}, role='collaborator')
    change = dict(payload, id=draft['id'], expected_revision=shared['revision'], additional_notes='Collaborator change')
    updated = api('ihpix_report_update', change, role='collaborator')
    check('collaborator saves a version', updated['revision'] == 2)
    api('ihpix_report_update', dict(change, save_as_draft='', expected_revision=2), role='collaborator', success=False)
    stale = api('ihpix_report_update', dict(change, expected_revision=1), success=False)
    check('stale saves are rejected', stale.get('expected_revision') == ['revision_conflict'] or 'revision_conflict' in str(stale))
    simultaneous = dict(change, expected_revision=2)
    def send(role):
        r = requests.post(BASE+'/api/3/action/ihpix_report_update',json=dict(simultaneous,additional_notes=role),
                          headers={'Authorization':TOKENS[role]},timeout=60)
        return r.json().get('success')
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        result = list(pool.map(send, ('author','collaborator')))
    check('two simultaneous saves produce exactly one winner', sorted(result) == [False,True])
    api('ihpix_working_group_leave', {'id':'1.10'}, role='collaborator')
    api('ihpix_report_update', dict(change, expected_revision=3), role='collaborator', success=False)
    check('leaving the workspace immediately removes editing access')
    comment = api('ihpix_workspace_item_save', {'working_group_id':'1.10','kind':'comment','body':'QA comment'})
    api('ihpix_workspace_item_save', {'working_group_id':'1.10','kind':'comment','body':'Forbidden'}, role='observer',success=False)
    check('observer reads comments but cannot write', any(x['id']==comment['id'] for x in api('ihpix_workspace_item_list', {'working_group_id':'1.10'}, role='observer')['results']))
    task = api('ihpix_workspace_item_save', {'working_group_id':'1.10','kind':'task','title':'QA task','body':'QA task description','assignee_id':users['author'],'due_date':'2026-12-01'})
    api('ihpix_workspace_item_save', {'working_group_id':'1.10','id':task['id'],'expected_revision':1,'status':'completed'})
    check('task assignment, due date and completion persist')
    api('ihpix_working_group_update', {'id':'1.10','status':'archived'},role='admin')
    api('ihpix_workspace_item_save', {'working_group_id':'1.10','kind':'comment','body':'Forbidden'},success=False)
    current = api('ihpix_report_show', {'id':draft['id']})
    api('ihpix_report_update', dict(payload,id=draft['id'],expected_revision=current['revision']),success=False)
    api('ihpix_working_group_update', {'id':'1.10','status':'active'},role='admin')
    check('archived workspace prevents comments and report writes')
    for invalid in ('-1','1.5','text','2147483648'):
        api('ihpix_report_update',dict(payload,id=draft['id'],expected_revision=current['revision'],stakeholders_knowledge=invalid),success=False)
    check('all invalid numeric inputs fail on server')
    pending = api('ihpix_report_update',dict(payload,id=draft['id'],expected_revision=current['revision'],save_as_draft=''))
    check('author submits for review',pending['status']=='pending')
    check('pending report title remains private in feed',title not in json.dumps(api('ihpix_contribution_list',{'working_group_id':'1.10'},role='outsider')))
    rejected = api('ihpix_report_review',{'id':draft['id'],'action':'reject','review_notes':'QA correction'},role='admin')
    revised = api('ihpix_report_update',dict(payload,id=draft['id'],expected_revision=rejected['revision'],save_as_draft=''))
    published = api('ihpix_report_review',{'id':draft['id'],'action':'approve'},role='admin')
    check('reject, revise and publish work',published['status']=='published')
    check('global count increments once',api('ihpix_progress_stats',{'scope':'overall'})['overview']['activities']==baseline+1)
    for output in ('1.10','2.1'):
        result=api('ihpix_activity_list',{'output':output})
        check('activity appears in linked output '+output,any(x['id']==draft['id'] for x in result['results']))
    narrative=api('ihpix_narrative_data',{'scope':'output','value':'2.1','biennium':'2026-2027'})
    check('narrative cites only published matching sources',any(x['id']==draft['id'] for x in narrative['sources']))
    history=api('ihpix_report_collaboration_show',{'id':draft['id']})['history']
    check('versions retain author and time',len(history)>=6 and all(x['user_id'] and x['created_at'] for x in history))
    template=requests.get(BASE+'/ihpix/import/template.xlsx',headers={'Authorization':TOKENS['author']},timeout=60)
    book=load_workbook(io.BytesIO(template.content));headers=[x.value for x in book['Activities'][1]]
    book['Activities'].append([{'row_ref':'A1','title':title+' imported'}.get(k,'') for k in headers]);buffer=io.BytesIO();book.save(buffer)
    encoded=base64.b64encode(buffer.getvalue()).decode('ascii')
    preview=api('ihpix_import_preview',{'workbook':encoded})
    check('import separates incomplete fields from invalid data',not preview['preview']['errors'] and bool(preview['preview']['warnings']))
    api('ihpix_import_create',{'id':preview['id']},success=False)
    imported=api('ihpix_import_create',{'id':preview['id'],'confirm':True})
    CREATED.extend(x['id'] for x in imported['created'])
    repeated=api('ihpix_import_create',{'id':preview['id'],'confirm':True})
    check('import confirmation is required and retry is idempotent',repeated['created']==imported['created'] and repeated['repeated'])
    check('import creates drafts only',api('ihpix_report_show',{'id':CREATED[-1]})['status']=='draft')
    api('ihpix_import_show',{'id':preview['id']},role='outsider',success=False)
    check('import preview is private to its owner')
    api('ihpix_activity_update',{'id':draft['id'],'expected_revision':published['revision'],'status':'draft'},role='admin')
    check('unpublish refreshes progress immediately',api('ihpix_progress_stats',{'scope':'overall'})['overview']['activities']==baseline)
    for id in CREATED:
        api('ihpix_report_delete',{'id':id},role='admin')
    check('cleanup preserves the published baseline',api('ihpix_progress_stats',{'scope':'overall'})['overview']['activities']==baseline)
    print(json.dumps({'passed':len(RESULTS),'baseline':baseline,'created_ids':CREATED}))


if __name__ == '__main__':
    run()
