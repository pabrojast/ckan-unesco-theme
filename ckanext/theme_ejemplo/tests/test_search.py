import copy
import json
import time

import pytest

from ckanext.theme_ejemplo import search


@pytest.mark.parametrize('serialized', [False, True])
def test_abstract_includes_all_languages_without_json_keys(serialized):
    translated = {'en': 'Groundwater observations', 'es': 'Aguas subterráneas',
                  'fr': 'Eaux souterraines', 'ar': 'المياه الجوفية'}
    value = json.dumps(translated) if serialized else translated
    package = {'type': 'dataset', 'notes_translated': value,
               'notes': 'Groundwater observations'}
    original = copy.deepcopy(package)
    assert search.dataset_abstract_text(package) == '\n'.join(translated.values())
    assert package == original


@pytest.mark.parametrize('field', ['validated_data_dict', 'data_dict'])
@pytest.mark.parametrize('serialized', [False, True])
def test_abstract_uses_complete_package_before_flattened_fields(field, serialized):
    package = {'notes_translated': {'es': 'Aguas subterráneas'},
               'notes': 'Groundwater observations'}
    data = {field: json.dumps(package) if serialized else package,
            'notes_translated': {'fr': 'Stale translation'}}
    assert search.dataset_abstract_text(data) == (
        'Aguas subterráneas\nGroundwater observations')


def test_abstract_reads_legacy_extras_and_notes():
    package = {'extras': [{'key': 'notes_translated',
                          'value': '{"fr": "Eaux souterraines"}'}],
               'notes': '[Observations](https://example.org) of aquifers'}
    assert search.dataset_abstract_text(package) == (
        'Eaux souterraines\n[Observations](https://example.org) of aquifers')


def test_abstract_falls_back_when_complete_package_is_invalid():
    package = {'validated_data_dict': '{broken', 'data_dict': '[]',
               'notes_translated': '{"en": "Groundwater observations"}'}
    assert search.dataset_abstract_text(package) == 'Groundwater observations'


def test_abstract_does_not_restore_removed_translations():
    package = {'validated_data_dict': '{"notes": "", "notes_translated": {}}',
               'notes_translated': {'en': 'Stale groundwater observations'}}
    assert search.dataset_abstract_text(package) == ''


@pytest.mark.parametrize('value', [None, '', {}, [], 123, '{"en": broken',
                                   '{"en": null, "es": 42}', '["ignore"]'])
def test_abstract_handles_empty_or_invalid_translations(value):
    assert search.dataset_abstract_text({'notes_translated': value}) == ''
    assert search.dataset_abstract_text(
        {'notes_translated': value, 'notes': 'Legacy abstract'}) == 'Legacy abstract'


@pytest.mark.parametrize('kind', ['documents', 'learning'])
def test_abstract_does_not_expand_other_content_types(kind):
    assert search.dataset_abstract_text(
        {'type': kind, 'notes': 'Groundwater observations'}) == ''


ORGS = [
    {'name': 'water-quality-lab', 'title': 'Water Quality Laboratory',
     'description': ''},
    {'name': 'igrac', 'title': 'IGRAC',
     'description': 'International centre for groundwater; water quality data.'},
    {'name': 'univ-montpellier', 'title': 'Université de Montpellier',
     'description': ''},
    {'name': 'quality', 'title': 'Quality', 'description': ''},
    {'name': 'unrelated', 'title': 'Hydrology Institute', 'description': ''},
]


def _names(query, items=ORGS, **kw):
    return [i['name'] for i in search.filter_ranked(items, query, **kw)]


def test_word_order_does_not_matter():
    # El bug original: el ILIKE del core encontraba "water quality" pero no
    # "quality water".
    assert _names('water quality') == _names('quality water')
    assert 'water-quality-lab' in _names('quality water')


def test_all_tokens_are_required():
    assert _names('water montpellier') == []
    assert 'unrelated' not in _names('water quality')


def test_accents_and_case_are_folded():
    assert _names('universite MONTPELLIER') == ['univ-montpellier']
    assert _names('Université') == ['univ-montpellier']


def test_partial_word_matches():
    assert 'water-quality-lab' in _names('quali wat')


def test_title_match_ranks_above_description_match():
    names = _names('water quality')
    assert names.index('water-quality-lab') < names.index('igrac')


def test_description_can_be_left_out_for_suggestions():
    assert 'igrac' in _names('water quality')
    assert 'igrac' not in _names('water quality', include_description=False)


def test_exact_title_ranks_first():
    assert _names('quality')[0] == 'quality'


def test_slug_is_searchable():
    assert _names('igrac') == ['igrac']


def test_empty_or_punctuation_query_matches_nothing():
    assert _names('') == []
    assert _names('   ') == []
    assert _names('!!!') == []


def test_limit():
    assert len(_names('quality', limit=1)) == 1


def test_escape_solr_neutralizes_query_syntax():
    assert search.escape_solr('title:"water') == 'title water'
    assert search.escape_solr('a && (b || c)') == 'a b c'
    assert search.escape_solr('***') == ''
    assert search.escape_solr(None) == ''


def test_search_entities_filters_by_kind(monkeypatch):
    index = [
        {'name': 'org-water', 'title': 'Water Org', 'description': '',
         'type': 'organization', 'is_organization': True},
        {'name': 'chile', 'title': 'Chile Water', 'description': '',
         'type': 'group', 'is_organization': False},
        {'name': 'g-wet', 'title': 'Water Initiative', 'description': '',
         'type': 'group', 'is_organization': False},
    ]
    monkeypatch.setitem(search._index_cache, 'items', index)
    monkeypatch.setitem(search._index_cache, 'expires', time.time() + 60)

    assert search.search_entity_names('water', is_organization=True) == ['org-water']
    assert search.search_entity_names(
        'water', is_organization=False, allowed=['chile']) == ['chile']
    assert search.search_entity_names(
        'water', is_organization=False, excluded=['chile']) == ['g-wet']
    # Prefijo del título ('Water ...') gana a inicio de palabra ('Chile Water').
    assert search.search_entity_names('water', limit=2) == ['org-water', 'g-wet']
