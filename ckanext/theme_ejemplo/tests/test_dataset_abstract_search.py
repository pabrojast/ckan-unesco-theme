"""Integración CKAN/Solr: requiere schema.xml de ckan-unesco-docker actualizado."""
import json

import pytest

pytest.importorskip('ckan')

from ckan.plugins import toolkit
from ckan.tests import factories
from ckanext.theme_ejemplo import search


pytestmark = [pytest.mark.usefixtures('clean_db', 'clean_index'),
              pytest.mark.ckan_config('ckan.plugins', 'theme_ejemplo'),
              pytest.mark.ckan_config('ckanext.theme_ejemplo.search_partial_match', True)]


def _dataset(translations=None, **kwargs):
    if translations is not None:
        kwargs['extras'] = [{'key': 'notes_translated',
                             'value': json.dumps(translations)}]
    return factories.Dataset(**kwargs)


def _results(query, user='', **params):
    result = toolkit.get_action('package_search')({'user': user},
                                                dict(params, q=query))
    return [package['name'] for package in result['results']]


def _suggestions(app, query, token=None):
    headers = {toolkit.config['apikey_header_name']: token} if token else {}
    response = app.get('/api/theme/suggest', params={'q': query, 'scope': 'dataset'},
                       headers=headers)
    assert response.status_code == 200
    return [item['url'].rsplit('/', 1)[-1]
            for group in response.json['groups'] for item in group['items']]


@pytest.mark.parametrize('query', ['groundwater', 'groundw', 'gr', 'groundwate',
                                   'subterráneas', 'subterr', 'souterrain', 'الجوف'])
def test_search_and_suggestions_find_abstract_only_matches(app, query):
    package = _dataset({'en': 'Groundwater observations',
                        'es': 'Aguas subterráneas',
                        'fr': 'Eaux souterraines',
                        'ar': 'المياه الجوفية'},
                       title='Monitoring archive', notes='')
    assert _results(query) == [package['name']]
    assert _suggestions(app, query) == [package['name']]


def test_legacy_notes_and_long_complete_words_remain_searchable(app):
    package = _dataset(title='Monitoring archive',
                       notes='Hydrogeological measurements')
    for query in ('hydrogeological', 'hydrogeo'):
        assert _results(query) == [package['name']]
        assert _suggestions(app, query) == [package['name']]


def test_words_can_be_split_between_title_and_abstract(app):
    package = _dataset({'en': 'Groundwater observations'},
                       title='Regional archive', notes='')
    for query in ('regional groundw', 'groundw regional'):
        assert _results(query) == [package['name']]
        assert _suggestions(app, query) == [package['name']]


def test_title_match_ranks_above_abstract_match(app):
    abstract_match = _dataset(title='Monitoring archive', notes='Groundwater')
    title_match = _dataset(title='Groundwater', notes='Monitoring archive')
    for query in ('groundwater', 'groundw'):
        expected = [title_match['name'], abstract_match['name']]
        assert _results(query) == expected
        assert _suggestions(app, query) == expected


def test_private_abstract_matches_respect_authorization(app):
    owner = factories.User()
    organization = factories.Organization(
        users=[{'name': owner['name'], 'capacity': 'admin'}])
    public = _dataset(title='Public archive', notes='Groundwater')
    private = _dataset(title='Internal archive', notes='Groundwater',
                       owner_org=organization['id'], private=True)
    assert _results('groundw') == [public['name']]
    assert _suggestions(app, 'groundw') == [public['name']]
    outsider = factories.User()
    token = factories.APIToken(user=outsider['id'])['token']
    assert _results('groundw', user=outsider['name'], include_private=True) == [
        public['name']]
    assert _suggestions(app, 'groundw', token=token) == [public['name']]
    assert set(_results('groundw', user=owner['name'], include_private=True)) == {
        public['name'], private['name']}


def test_filters_explicit_query_fields_and_sort_are_preserved(app):
    first = _dataset(title='A archive', notes='Groundwater',
                     tags=[{'name': 'monitoring'}])
    second = _dataset(title='Z archive', notes='Groundwater')
    assert _results('groundw', fq='tags:monitoring') == [first['name']]
    assert _results('groundw', sort='title_string desc') == [
        second['name'], first['name']]
    assert _results('groundw', qf='title') == []
    assert _results('title:groundw') == []


def test_edited_abstract_replaces_old_partial_matches(app):
    package = _dataset({'en': 'Groundwater'}, title='Monitoring archive', notes='')
    assert _results('groundw') == [package['name']]
    toolkit.get_action('package_patch')({'ignore_auth': True}, {
        'id': package['id'],
        'extras': [{'key': 'notes_translated', 'value': '{"en": "Rainfall"}'}],
    })
    assert _results('groundw') == []
    assert _suggestions(app, 'groundw') == []
    assert _results('rainf') == [package['name']]
    toolkit.get_action('package_patch')({'ignore_auth': True}, {
        'id': package['id'], 'notes': '', 'extras': [],
    })
    assert _results('rainf') == []
    assert _suggestions(app, 'rainf') == []


def test_rebuild_backfills_existing_datasets_without_changing_metadata(app, monkeypatch):
    from ckan.lib.search import rebuild

    # Simular un documento indexado antes de incorporar el nuevo campo.
    with monkeypatch.context() as patch:
        patch.setattr(search, 'dataset_abstract_text', lambda package: '')
        package = _dataset({'en': 'Groundwater'}, title='Monitoring archive', notes='')
    assert _results('groundw') == []
    before = toolkit.get_action('package_show')({}, {'id': package['id']})
    rebuild(package_id=package['id'], force=True)
    assert _results('groundw') == [package['name']]
    assert _suggestions(app, 'groundw') == [package['name']]
    assert toolkit.get_action('package_show')({}, {'id': package['id']}) == before


def test_partial_abstract_index_does_not_contain_language_keys(app):
    package = _dataset({'zz': 'Groundwater'}, title='Monitoring archive', notes='')
    assert _results('groundw', qf='abstract_ngram') == [package['name']]
    assert _results('zz', qf='abstract_ngram') == []


def test_empty_abstract_and_other_content_types_do_not_gain_matches(app):
    _dataset(title='Monitoring archive', notes='')
    _dataset(title='Learning archive', notes='Groundwater', type='learning')
    assert _results('groundw') == []
    assert _suggestions(app, 'groundw') == []
