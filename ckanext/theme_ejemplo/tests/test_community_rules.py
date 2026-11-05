# -*- coding: utf-8 -*-
"""Pruebas del intérprete de reglas y del almacén de la comunidad (sin CKAN).

Las pruebas completas de permisos están en frontend/dacs-community (npm run test:rules).
"""
import datetime
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from ckanext.theme_ejemplo.community_rules import RulesEngine
from ckanext.theme_ejemplo.community_store import ApiError, CommunityApi, DocumentStore

RULES = os.path.join(os.path.dirname(__file__), '..', 'community_data', 'dacs.rules')
NOW = datetime.datetime(2026, 11, 5, 12, 0, tzinfo=datetime.timezone.utc)


def member(uid, admin=False):
    return {'uid': uid, 'token': {'email': uid + '@example.test', 'email_verified': True,
                                  'platform_admin': admin}}


def profile(**extra):
    d = {'name': 'Test member', 'headline': 'Hydrologist', 'organisation': 'Institute',
         'country': 'France', 'region': 'Global', 'languages': ['English'], 'skills': ['Hydrology'],
         'wgs': [4], 'bio': 'Research', 'motivation': 'Contribute', 'contribution': 'Review',
         'availability': '2–4 hours / month', 'website': '', 'visibility': 'community',
         'contactConsent': False, 'contact': '', 'consent': True,
         'createdAt': {'$sv': 'serverTimestamp'}, 'updatedAt': {'$sv': 'serverTimestamp'}}
    d.update(extra)
    return d


@pytest.fixture
def api():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    with open(RULES, encoding='utf-8') as f:
        return CommunityApi(DocumentStore(engine, 'dacs'), RulesEngine(f.read()))


def write(api, auth, path, data):
    return api.handle('commit', {'writes': [{'op': 'set', 'path': path, 'data': data}]}, auth, NOW)


def test_rules_file_parses():
    with open(RULES, encoding='utf-8') as f:
        RulesEngine(f.read())


def test_profiles_owner_only_and_guests_blocked(api):
    write(api, member('alice'), 'profiles/alice', profile())
    with pytest.raises(ApiError) as exc:
        write(api, member('bob'), 'profiles/alice', profile())
    assert exc.value.code == 'permission-denied'
    guest = api.handle('read', {'targets': [{'kind': 'doc', 'path': 'profiles/alice'}]}, None, NOW)
    assert guest['results'][0]['error']['code'] == 'permission-denied'
    seen = api.handle('read', {'targets': [{'kind': 'doc', 'path': 'profiles/alice'}]}, member('bob'), NOW)
    assert seen['results'][0]['data']['name'] == 'Test member'


def test_queries_follow_firestore_semantics(api):
    write(api, member('alice'), 'profiles/alice', profile())
    write(api, member('carol'), 'profiles/carol', profile(visibility='private'))
    q = {'kind': 'query', 'collection': 'profiles', 'where': [['visibility', '==', 'community']]}
    ok = api.handle('read', {'targets': [q]}, member('bob'), NOW)['results'][0]
    assert [d['id'] for d in ok['docs']] == ['alice']
    everything = api.handle('read', {'targets': [{'kind': 'query', 'collection': 'profiles'}]},
                            member('bob'), NOW)['results'][0]
    assert everything['error']['code'] == 'permission-denied'


def test_platform_admin_has_secretariat_rights(api):
    write(api, member('alice'), 'profiles/alice', profile())
    api.handle('commit', {'writes': [{'op': 'delete', 'path': 'profiles/alice'}]},
               member('secretariat', admin=True), NOW)
    with pytest.raises(ApiError):
        api.handle('commit', {'writes': [{'op': 'delete', 'path': 'profiles/alice'}]},
                   member('bob'), NOW)
