"""Flujo real de membresías: requiere CKAN y una BD PostgreSQL de pruebas."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import re

import pytest
from sqlalchemy.exc import IntegrityError

pytest.importorskip('ckan')

from ckan import model
from ckan.plugins import toolkit
from ckan.tests import factories
from ckanext.theme_ejemplo import initiative_membership as membership
from ckanext.theme_ejemplo.model import (
    InitiativeMembershipRequest, init_initiative_memberships_db)

try:
    from ckanext.pages.db import Page
except ImportError:
    Page = None

pytestmark = [pytest.mark.ckan_config('ckan.plugins', 'activity theme_ejemplo'),
              pytest.mark.usefixtures('clean_db', 'with_plugins')]


def call(operation, user=None, **data):
    return toolkit.get_action('initiative_membership_request_' + operation)(
        {'user': user['name'] if user else ''}, data)


@pytest.fixture
def actors(app, monkeypatch):
    init_initiative_memberships_db()
    # clean_db puede borrar tablas del tema después de cargar el plugin.
    # Recrearlas evita depender del orden de ejecución de las pruebas web.
    model.meta.metadata.create_all(model.meta.engine)
    # Si Pages está instalado, la portada AI consulta su esquema real.
    if Page is not None:
        Page.__table__.create(model.meta.engine, checkfirst=True)
    model.Session.query(InitiativeMembershipRequest).delete()
    model.Session.commit()
    mails = []
    monkeypatch.setattr('ckan.lib.mailer.mail_user',
                        lambda user, subject, body: mails.append((user.id, subject, body)))
    # Aislar los helpers de login del plugin Citizen Science, ajeno a esta prueba.
    for name in ('csunesco_login_return_url', 'csunesco_login_url'):
        monkeypatch.setitem(toolkit.h, name, lambda: None)
    admin = factories.User()
    user = factories.User()
    outsider = factories.User()
    group = factories.Group(users=[{'name': admin['name'], 'capacity': 'admin'}])
    other = factories.Group(users=[{'name': outsider['name'], 'capacity': 'admin'}])
    return dict(admin=admin, user=user, outsider=outsider, group=group,
                other=other, mails=mails, sysadmin=factories.Sysadmin())


@pytest.mark.parametrize('role', ['member', 'editor', 'admin'])
def test_approve_adds_real_member_with_selected_role(actors, role):
    a = actors
    req = call('create', a['user'], group_id=a['group']['name'], message='Interested', role='admin')
    assert req['role'] == 'member'
    assert req['status'] == 'pending'
    assert call('count', a['admin'])['count'] == 1
    assert call('count', a['outsider'])['count'] == 0
    assert call('count', a['sysadmin'])['count'] == 1
    result = call('process', a['admin'], group_id=a['group']['id'],
                  id=req['id'], action='approve', role=role)
    assert result['status'] == 'approved'
    assert result['handled_by'] == a['admin']['id']
    assert membership._member(a['user']['id'], a['group']['id']).capacity == role
    assert call('count', a['admin'])['count'] == 0
    assert call('list', a['admin'], group_id=a['group']['id'], status='approved')['count'] == 1


def test_duplicate_existing_member_and_rejected_retry(actors):
    a = actors
    req = call('create', a['user'], group_id=a['group']['id'])
    with pytest.raises(toolkit.ValidationError):
        call('create', a['user'], group_id=a['group']['id'])
    model.Session.rollback()
    call('process', a['admin'], group_id=a['group']['id'],
         id=req['id'], action='reject', admin_note='Please explain your interest')
    assert membership._member(a['user']['id'], a['group']['id']) is None
    replacement = call('create', a['user'], group_id=a['group']['id'])
    assert replacement['id'] != req['id']
    with pytest.raises(toolkit.ValidationError):
        call('create', a['admin'], group_id=a['group']['id'])


def test_unauthorized_actors_and_cross_initiative_request(actors):
    a = actors
    with pytest.raises(toolkit.NotAuthorized):
        call('create', group_id=a['group']['id'])
    req = call('create', a['user'], group_id=a['group']['id'])
    for actor in (None, a['user'], a['outsider']):
        with pytest.raises(toolkit.NotAuthorized):
            call('list', actor, group_id=a['group']['id'])
        with pytest.raises(toolkit.NotAuthorized):
            call('process', actor, group_id=a['group']['id'], id=req['id'], action='approve')
    with pytest.raises(toolkit.NotAuthorized):
        call('process', a['outsider'], group_id=a['other']['id'], id=req['id'], action='approve')
    assert membership._pending(a['user']['id'], a['group']['id'])


def test_editor_cannot_review_and_invalid_role_is_rejected(actors):
    a = actors
    toolkit.get_action('member_create')({'ignore_auth': True}, {
        'id': a['group']['id'], 'object': a['outsider']['id'],
        'object_type': 'user', 'capacity': 'editor'})
    req = call('create', a['user'], group_id=a['group']['id'])
    with pytest.raises(toolkit.NotAuthorized):
        call('process', a['outsider'], group_id=a['group']['id'], id=req['id'], action='approve')
    with pytest.raises(toolkit.ValidationError):
        call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='approve', role='owner')


def test_preserves_membership_granted_elsewhere_and_rejects_second_decision(actors):
    a = actors
    req = call('create', a['user'], group_id=a['group']['id'])
    toolkit.get_action('member_create')({'ignore_auth': True}, {
        'id': a['group']['id'], 'object': a['user']['id'],
        'object_type': 'user', 'capacity': 'admin'})
    result = call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='approve')
    assert result['role'] == 'admin'
    assert membership._member(a['user']['id'], a['group']['id']).capacity == 'admin'
    with pytest.raises(toolkit.ValidationError):
        call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='reject')


def test_excludes_organizations_member_states_deleted_groups_and_users(actors):
    a = actors
    organization = factories.Organization()
    parent = factories.Group(name='member-states')
    country = factories.Group()
    toolkit.get_action('member_create')({'ignore_auth': True}, {
        'id': parent['id'], 'object': country['id'], 'object_type': 'group', 'capacity': 'public'})
    inactive = factories.Group(state='deleted')
    for target in (organization, parent, country, inactive):
        with pytest.raises(toolkit.ObjectNotFound):
            call('create', a['user'], group_id=target['id'])
    req = call('create', a['user'], group_id=a['group']['id'])
    model.User.get(a['user']['id']).state = 'deleted'
    model.Session.commit()
    with pytest.raises(toolkit.ValidationError):
        call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='approve')
    assert membership._pending(a['user']['id'], a['group']['id'])


def test_membership_failure_does_not_approve_request(actors, monkeypatch):
    a = actors
    req = call('create', a['user'], group_id=a['group']['id'])
    original = toolkit.get_action
    def fail(context, data):
        original('member_create')(context, data)
        raise RuntimeError('simulated member creation failure')
    monkeypatch.setattr(toolkit, 'get_action', lambda name: fail if name == 'member_create' else original(name))
    with pytest.raises(RuntimeError):
        call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='approve')
    assert membership._pending(a['user']['id'], a['group']['id'])
    assert membership._member(a['user']['id'], a['group']['id']) is None


def test_email_notifications_and_failure_do_not_lose_decision(actors, app, monkeypatch):
    a = actors
    with app.flask_app.test_request_context('/'):
        req = call('create', a['user'], group_id=a['group']['id'], message='Hydrology')
        assert any(user_id == a['admin']['id'] and 'Hydrology' in body
                   for user_id, subject, body in a['mails'])
        result = call('process', a['sysadmin'], group_id=a['group']['id'],
                      id=req['id'], action='reject', admin_note='Try later')
        assert any(user_id == a['user']['id'] and 'Try later' in body
                   for user_id, subject, body in a['mails'])
        monkeypatch.setattr('ckan.lib.mailer.mail_user',
                            lambda *args: (_ for _ in ()).throw(RuntimeError('SMTP unavailable')))
        req = call('create', a['user'], group_id=a['group']['id'])
        result = call('process', a['sysadmin'], group_id=a['group']['id'], id=req['id'], action='approve')
        assert result['status'] == 'approved'


@pytest.mark.parametrize('operation', ['create', 'process'])
def test_concurrent_requests_or_decisions_have_one_winner(actors, monkeypatch, operation):
    a = actors
    monkeypatch.setattr(membership, '_after_change', lambda *args, **kwargs: None)
    req = call('create', a['user'], group_id=a['group']['id']) if operation == 'process' else None
    barrier = Barrier(2)
    def worker():
        try:
            barrier.wait(timeout=10)
            if operation == 'create':
                call('create', a['user'], group_id=a['group']['id'])
            else:
                call('process', a['admin'], group_id=a['group']['id'], id=req['id'], action='approve')
            return 'ok'
        except toolkit.ValidationError:
            return 'duplicate'
        finally:
            model.Session.rollback()
            model.Session.remove()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(results) == ['duplicate', 'ok']
    model.Session.expire_all()
    assert model.Session.query(InitiativeMembershipRequest).filter_by(
        group_id=a['group']['id'], user_id=a['user']['id']).count() == 1


def test_schema_initialization_is_idempotent(actors):
    req = call('create', actors['user'], group_id=actors['group']['id'])
    init_initiative_memberships_db()
    init_initiative_memberships_db()
    assert model.Session.query(InitiativeMembershipRequest).get(req['id']).status == 'pending'


def test_database_rejects_duplicate_pending_rows(actors):
    req = call('create', actors['user'], group_id=actors['group']['id'])
    model.Session.add(InitiativeMembershipRequest(actors['user']['id'], actors['group']['id']))
    with pytest.raises(IntegrityError):
        model.Session.commit()
    model.Session.rollback()
    assert model.Session.query(InitiativeMembershipRequest).get(req['id']).status == 'pending'


def test_sysadmin_can_review_orphan_initiative_and_cache_is_invalidated(actors, app, monkeypatch):
    group = factories.Group(users=[])
    # CKAN puede agregar al creador como admin aunque users esté vacío.
    model.Session.query(model.Member).filter_by(
        group_id=group['id'], table_name='user').delete()
    model.Session.commit()
    invalidated = []
    monkeypatch.setattr('ckanext.theme_ejemplo.approvals.invalidate',
                        lambda user_id=None: invalidated.append(user_id))
    with app.flask_app.test_request_context('/'):
        req = call('create', actors['user'], group_id=group['id'])
        assert actors['sysadmin']['id'] in invalidated
        assert any(user_id == actors['sysadmin']['id'] for user_id, _, _ in actors['mails'])
        assert call('count', actors['sysadmin'])['count'] == 1
        assert call('count', actors['admin'])['count'] == 0
        invalidated.clear()
        call('process', actors['sysadmin'], group_id=group['id'], id=req['id'], action='approve')
        assert actors['sysadmin']['id'] in invalidated


def test_deleted_initiative_cannot_be_approved(actors):
    req = call('create', actors['user'], group_id=actors['group']['id'])
    model.Group.get(actors['group']['id']).state = 'deleted'
    model.Session.commit()
    with pytest.raises(toolkit.ObjectNotFound):
        call('process', actors['sysadmin'], group_id=actors['group']['id'],
             id=req['id'], action='approve')
    assert model.Session.query(InitiativeMembershipRequest).get(req['id']).status == 'pending'


def _headers(user):
    token = factories.APIToken(user=user['name'])['token']
    return {toolkit.config['apikey_header_name']: token}


def _csrf(response):
    body = response.data.decode()
    field = toolkit.config['WTF_CSRF_FIELD_NAME']
    match = re.search(r'name="' + re.escape(field) + r'"[^>]*value="([^"]+)"', body)
    assert match, body[:500]
    return {field: match.group(1)}


def test_web_form_csrf_pending_review_and_history(actors, app):
    a = actors
    group = a['group']
    url = '/group/{}/request-membership'.format(group['name'])
    client = app.test_client()
    headers = _headers(a['user'])
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'private, no-store'
    token = _csrf(response)
    assert client.post(url, data={'message': 'Hydrology'}, headers=headers).status_code == 400
    response = client.post(url, data=dict(token, message='Hydrology <script>alert(1)</script>'), headers=headers,
                           follow_redirects=False)
    assert response.status_code == 302
    pending = client.get('/group/' + group['name'], headers=headers)
    assert pending.status_code == 200
    assert b'Request Pending' in pending.data
    review_url = '/group/{}/membership-requests'.format(group['name'])
    assert client.get(review_url, headers=headers).status_code == 403
    admin_headers = _headers(a['admin'])
    response = client.get(review_url, headers=admin_headers)
    assert response.status_code == 200
    assert b'Hydrology' in response.data
    assert b'&lt;script&gt;' in response.data
    assert b'Hydrology <script>' not in response.data
    assert b'Initiative membership requests' in response.data
    assert (review_url + '?tab=history').encode() in response.data
    token = _csrf(response)
    req = membership._pending(a['user']['id'], group['id'])
    data = {'request_id': req.id, 'action': 'approve', 'role': 'editor'}
    assert client.post(review_url, data=data, headers=admin_headers).status_code == 400
    response = client.post(review_url, data=dict(data, **token), headers=admin_headers,
                           follow_redirects=False)
    assert response.status_code == 302
    history = client.get(review_url + '?tab=history', headers=admin_headers)
    assert history.status_code == 200
    assert b'Approved' in history.data
    members = client.get('/group/{}/members'.format(group['name']))
    assert members.status_code == 200
    assert a['user']['name'].encode() in members.data


def test_visitor_login_return_and_ai_water_portal(actors, app):
    a = actors
    group = factories.Group(name='artificial-intelligence-for-water-management',
                            users=[{'name': a['admin']['name'], 'capacity': 'admin'}])
    url = '/group/{}/request-membership'.format(group['name'])
    response = app.get(url, follow_redirects=False)
    assert response.status_code == 302
    assert 'came_from=' in response.location
    response = app.get('/group/' + group['name'], headers=_headers(a['user']))
    assert response.status_code == 200
    assert url.encode() in response.data
    response = app.get('/group/{}/membership-requests'.format(group['name']),
                       headers=_headers(a['admin']))
    assert response.status_code == 200
    assert b'aiw-subnav' in response.data


def test_organization_dashboard_keeps_its_routes(actors, app):
    organization = factories.Organization(users=[
        {'name': actors['admin']['name'], 'capacity': 'admin'}])
    url = '/organization/{}/membership-requests'.format(organization['name'])
    response = app.get(url, headers=_headers(actors['sysadmin']))
    assert response.status_code == 200
    assert (url + '?tab=history').encode() in response.data
    assert b'/group/' + organization['name'].encode() + b'/membership-requests' not in response.data
