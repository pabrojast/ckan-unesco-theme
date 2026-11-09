"""Pruebas de integración sólo para CKAN desechable ihpix-form-db/ihpix_form."""
import io
import json
import uuid
from urllib.parse import urlparse
from unittest.mock import patch

from ckan.cli import load_config
from ckan.config.middleware import make_app

config = load_config('/qa/app.ini')
connection = urlparse(config['sqlalchemy.url'])
assert connection.hostname == 'ihpix-form-db' and connection.path == '/ihpix_form'
app = make_app(config)
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.pages.db import Page
from werkzeug.datastructures import FileStorage
connection = urlparse(tk.config['sqlalchemy.url'])
assert connection.hostname == 'ihpix-form-db' and connection.path == '/ihpix_form'
checks = []


def check(label, condition):
    assert condition, label
    checks.append(label)


def context(name='author'):
    user = model.User.get('qa-form-' + name)
    assert user
    return {'model': model, 'session': model.Session, 'user': user.name, 'auth_user_obj': user}


def payload(kind='dataset', **updates):
    org = model.Group.get('qa-form-institute')
    data = dict(kind=kind, title='Inline service QA', organization=org.id, description='Measured water data.',
                contact_email='qa@example.org', visibility='private', license_id='notspecified',
                dcat_type='http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset',
                topic='http://inspire.ec.europa.eu/metadata-codelist/TopicCategory/inlandWaters',
                source_kind='url', source_url='https://example.org/data.csv', request_id=str(uuid.uuid4()),
                start_date='2026-11-10', end_date='2026-11-11', event_format='online')
    data.update(updates)
    return data


def create(data, actor='author'):
    return tk.get_action('ihpix_resource_create')(context(actor), data)['link']


def denied(action, actor, values, error):
    try:
        tk.get_action(action)(context(actor), values)
    except error:
        model.Session.rollback()
        return True
    raise AssertionError('Expected rejection: '+action)


data = payload()
first = create(data)
repeat = create(data)
check('dataset retry reuses same dataset', first['target_id'] == repeat['target_id'])
pkg = tk.get_action('package_show')(context(), {'id':first['target_id']})
check('dataset retry keeps one URL resource', len(pkg['resources']) == 1 and pkg['resources'][0]['url'] == data['source_url'])
check('private choice maps to confidential sharing', pkg['private'] and pkg['access_level'] == 'confidential')
check('another user cannot read private dataset', denied('package_show', 'other', {'id':pkg['id']}, tk.NotAuthorized))
check('another user cannot create in organization', denied('ihpix_resource_create', 'other', data, tk.ValidationError))
check('unknown classification rejected', denied('ihpix_resource_create', 'author', payload(topic='invalid'), tk.ValidationError))
public = create(payload(visibility='public'))
pkg = tk.get_action('package_show')(context('other'), {'id':public['target_id']})
check('explicit public choice readable by another user', not pkg['private'] and pkg['access_level'] == 'public')
# Fallo real en la frontera con el almacenamiento: ocultar dataset vacío y reusar identidad.
failed = payload(source_kind='file')
failed['upload'] = FileStorage(io.BytesIO(b'x,y\n1,2\n'), filename='data.csv', content_type='text/csv')
original = tk.get_action

def failing_action(name):
    if name == 'resource_create':
        def failure(*args, **kwargs):
            raise RuntimeError('QA storage failure')
        return failure
    return original(name)

with patch.object(tk, 'get_action', side_effect=failing_action):
    check('storage failure is a recoverable form error', denied('ihpix_resource_create','author',failed,tk.ValidationError))
from ckanext.theme_ejemplo.ihpix_resources import content_identity
identity, _ = content_identity(context()['auth_user_obj'].id, 'dataset', failed['request_id'])
row = model.Package.get('ihpix-'+identity)
check('failed upload hides the empty dataset', row.state == 'deleted')
old_id = row.id
recovered = create(failed)
pkg = tk.get_action('package_show')(context(), {'id':recovered['target_id']})
check('retry recovers dataset and uploads once', pkg['id'] == old_id and pkg['state'] == 'active' and len(pkg['resources']) == 1)
for source in ('none', 'url'):
    event = payload('event', source_kind=source, source_url='https://example.org/agenda.pdf')
    link = create(event)
    check('event '+source+' retry reuses page', create(event)['target_id'] == link['target_id'])
    row = model.Session.query(Page).filter_by(name=link['target_id']).one()
    extras = json.loads(row.extras)
    check('event '+source+' stays pending and private', row.private and row.submission_status == 'pending')
    check('event '+source+' dates and format preserved', str(row.publish_date.date()) == '2026-11-10' and extras['event_end_date'].split('T')[0] == '2026-11-11' and extras['event_format'] == 'online')
    check('event '+source+' agenda preserved', extras.get('agenda_document', '') == (event['source_url'] if source == 'url' else ''))
# Los eventos enviados por admin tampoco omiten la revisión.
admin_event = create(payload('event', source_kind='none'), 'admin')
row = model.Session.query(Page).filter_by(name=admin_event['target_id']).one()
check('admin explicitly submitting event keeps review', row.private and row.submission_status == 'pending')
print(json.dumps({'checks':checks, 'count':len(checks)}, indent=2))
