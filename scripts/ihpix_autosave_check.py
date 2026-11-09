"""Comprueba guardados y permisos solamente en la base aislada ihpix_form.

Ejecutar dentro del contenedor QA con /qa/app.ini y los usuarios qa-form-*.
No admite DEV, producción ni otra base compartida.
"""
import json
import uuid

from ckan.cli import load_config
from ckan.config.middleware import make_app

config = load_config('/qa/app.ini')
from urllib.parse import urlparse
connection = urlparse(config['sqlalchemy.url'])
assert connection.hostname == 'ihpix-form-db' and connection.path == '/ihpix_form'
app = make_app(config)
import ckan.model as model
import ckan.plugins.toolkit as tk
effective_connection = urlparse(tk.config['sqlalchemy.url'])
assert effective_connection.hostname == 'ihpix-form-db' and effective_connection.path == '/ihpix_form'
from ckanext.theme_ejemplo import ihpix_forms as F, ihpix_service as V
from ckanext.theme_ejemplo.model import IhpixActivity, IhpixActivityLink, IhpixWorkingGroup

checks = []

def check(label, condition):
    assert condition, label
    checks.append(label)


def context(name='author'):
    user = model.User.get('qa-form-' + name)
    assert user
    return {'model': model, 'user': user.name, 'auth_user_obj': user}


def save(data, name='author'):
    return tk.get_action('ihpix_report_autosave')(context(name), data)


def denied(data, error, name='author'):
    try:
        save(data, name)
    except error:
        model.Session.rollback()
        return True
    raise AssertionError('Expected rejection: ' + str(error))


client = str(uuid.uuid4())
data = dict(client_draft_id=client, title='Isolated autosave permissions QA', links_json='[]')
first = save(data)
check('new draft created once', first['status'] == 'draft' and first['revision'] == 1)
retry = save(data)
check('lost first acknowledgement does not duplicate or revise', retry['id'] == first['id'] and retry['revision'] == 1)
other = save(data, 'other')
check('client identity scoped to author', other['id'] != first['id'])
data.update(id=first['id'], expected_revision=first['revision'], description='Second version')
changed = save(data)
check('answers update same draft', changed['id'] == first['id'] and changed['revision'] == 2)
check('retry outdated revision with identical answers is safe', save(data)['revision'] == 2)
check('another author cannot overwrite', denied(dict(data, title='Unauthorized'), tk.NotAuthorized, 'other'))
check('stale changed answers conflict', denied(dict(data, description='Stale edit'), V.RevisionConflict))
check('invalid fields do not overwrite', denied(dict(data, expected_revision=2, contact_email='bad'), tk.ValidationError))
check('unknown report is not recreated', denied(dict(data, id=str(uuid.uuid4())), tk.ObjectNotFound))
check('invalid creation identity fails', denied({'title':'Invalid', 'client_draft_id':'bad'}, tk.ValidationError))
links = [dict(link_type='other', target_kind='url', title='Source '+str(i), url='https://example.org/source/'+str(i)) for i in range(2)]
data.update(expected_revision=2, links_json=json.dumps(links))
linked = save(data)
check('attachments saved atomically', linked['revision'] == 3)
check('link retry preserves revision', save(data)['revision'] == 3)
link_ids = [link.id for link in IhpixActivityLink.get_by_activity(first['id'])]
data.update(expected_revision=3, description='Linked activity updated')
linked = save(data)
check('autosave preserves attachment identity', [link.id for link in IhpixActivityLink.get_by_activity(first['id'])] == link_ids)
row = model.Session.query(IhpixActivity).filter_by(id=first['id']).one()
row.status = 'rejected'
model.Session.commit()
data.update(expected_revision=linked['revision'], description='Returned report changes')
check('autosave preserves reviewer-returned status', save(data)['status'] == 'rejected')
for status in ('pending', 'published'):
    row = model.Session.query(IhpixActivity).filter_by(id=first['id']).one()
    row.status = status
    model.Session.commit()
    for actor in ('author', 'admin'):
        check(status+' cannot autosave as '+actor, denied(data, tk.NotAuthorized, actor))
row = model.Session.query(IhpixActivity).filter_by(id=first['id']).one()
row.status = 'draft'
model.Session.commit()
full = dict(data, expected_revision=row.revision, priority_area='PA2', output='2.1',
            focal_point_name='QA Author', contact_email='author@example.test',
            institution_type='University', institution='QA University', biennium='2024-2025',
            description='Full description', outcomes='Documented outcomes')
for gate in F.GATE_FIELDS_REQUIRED:
    full[gate] = 'no'
ready = save(full)
check('complete autosave remains private draft', ready['status'] == 'draft')
wg = IhpixWorkingGroup.get_by_output('2.1')
wg.status = 'archived'
model.Session.commit()
check('archived workspace rejects autosave', denied(full, tk.NotAuthorized))
wg = IhpixWorkingGroup.get_by_output('2.1')
wg.status = 'active'
model.Session.commit()
full['expected_revision'] = ready['revision']
submitted = tk.get_action('ihpix_report_update')(context(), full)
check('only explicit submission becomes pending', submitted['status'] == 'pending')
print(json.dumps({'checks':checks, 'count':len(checks)}, indent=2))
