import json

from ckanext.theme_ejemplo import completeness


LONG_NOTES = 'A sufficiently long description of the dataset. ' * 4


def _rich_dataset():
    return {
        'type': 'dataset',
        'title_translated': {'en': 'Title', 'es': 'Titulo', 'fr': 'Titre'},
        'notes_translated': {'en': LONG_NOTES, 'es': LONG_NOTES,
                             'fr': LONG_NOTES},
        'tags': [{'name': 'water'}],
        'theme': 'http://inspire.ec.europa.eu/theme/hy',
        'graphic_overview': 'https://example.org/img.png',
        'spatial': '{"type": "Polygon", "coordinates": []}',
        'reference_system': 'EPSG:4326',
        'representation_type': 'vector',
        'temporal_start': '2020-01-01',
        'temporal_end': '2024-12-31',
        'frequency': 'annual',
        'provenance': {'en': 'Produced by UNESCO'},
        'purpose': {'en': 'Monitoring'},
        'lineage_source': ['survey'],
        'conforms_to': ['https://inspire.ec.europa.eu'],
        'license_id': 'cc-by',
        'access_rights': 'public',
        'contact_name': 'IHP-WINS',
        'contact_url': 'https://ihp-wins.unesco.org',
        'publisher_name': 'UNESCO',
        'publisher_type': 'international',
        'author': 'UNESCO IHP',
        'resources': [{'description': 'CSV data', 'format': 'CSV'}],
        'version': '1.0',
        'version_notes': {'en': 'Initial release'},
    }


def test_empty_dataset_is_limited():
    result = completeness.calculate_completeness({'type': 'dataset'})
    assert result['category'] == 'limited'
    assert result['score'] < 40
    assert 'notes_translated' in result['missing']
    assert 'tags' in result['missing']


def test_rich_dataset_is_full():
    result = completeness.calculate_completeness(_rich_dataset())
    assert result['category'] == 'full'
    assert result['score'] == 100.0
    assert result['missing'] == []
    assert result['languages'] == ['en', 'es', 'fr']


def test_fluent_bonus_rewards_translations():
    monolingual = _rich_dataset()
    monolingual['title_translated'] = {'en': 'Title'}
    monolingual['notes_translated'] = {'en': LONG_NOTES}
    multilingual = _rich_dataset()
    # drop fields so neither hits the 100 cap and the bonus is visible
    for pkg in (monolingual, multilingual):
        del pkg['provenance']
        del pkg['spatial']

    mono = completeness.calculate_completeness(monolingual)
    multi = completeness.calculate_completeness(multilingual)
    assert multi['score'] == round(mono['score'] + 10, 1)
    assert mono['languages'] == ['en']


def test_short_notes_get_half_credit():
    pkg = {'type': 'dataset', 'notes_translated': {'en': 'Too short'}}
    result = completeness.calculate_completeness(pkg)
    long_pkg = {'type': 'dataset', 'notes_translated': {'en': LONG_NOTES}}
    long_result = completeness.calculate_completeness(long_pkg)
    assert 0 < result['score'] < long_result['score']
    assert 'notes_translated' in result['missing']
    assert 'notes_translated' not in long_result['missing']


def test_documents_use_their_own_weights():
    doc = {
        'type': 'documents',
        'notes_translated': {'en': LONG_NOTES},
        'document_type': 'report',
        'publication_year': '2024',
        'authors_json': json.dumps([{'name': 'Jane'}]),
        'ihp_water_theme': ['groundwater'],
        'custom_citation': 'UNESCO (2024)',
        'custom_doi': 'https://doi.org/10.1000/x',
        'tags': [{'name': 'report'}],
        'graphic_overview': 'https://example.org/cover.png',
        'license_id': 'cc-by',
        'contact_name': 'IHP',
        'resources': [{'format': 'PDF'}],
    }
    result = completeness.calculate_completeness(doc)
    assert result['category'] == 'full'
    assert result['missing'] == []


def test_unsupported_type_is_skipped():
    assert completeness.calculate_completeness({'type': 'harvest'}) is None
    pkg = {'type': 'harvest'}
    completeness.inject(pkg)
    assert 'metadata_completeness' not in pkg


def test_inject_is_idempotent_and_respects_existing():
    pkg = {'type': 'dataset', 'metadata_completeness': {'score': 99}}
    completeness.inject(pkg)
    assert pkg['metadata_completeness'] == {'score': 99}


def test_extras_fallback_for_legacy_datasets():
    pkg = {
        'type': 'dataset',
        'extras': [
            {'key': 'provenance', 'value': 'Legacy provenance'},
            {'key': 'contact_name', 'value': 'Legacy contact'},
        ],
    }
    result = completeness.calculate_completeness(pkg)
    assert 'provenance' not in result['missing']
    assert 'contact_name' not in result['missing']


def test_fluent_fields_accept_json_strings():
    pkg = {
        'type': 'dataset',
        'title_translated': json.dumps({'en': 'T', 'es': 'T', 'fr': 'T'}),
        'notes_translated': json.dumps({'en': LONG_NOTES, 'es': LONG_NOTES}),
    }
    result = completeness.calculate_completeness(pkg)
    assert 'notes_translated' not in result['missing']
    assert result['languages'] == ['en', 'es']


def test_for_index_prefers_validated_data_dict():
    validated = json.dumps(_rich_dataset())
    score, category = completeness.for_index({
        'id': 'x',
        'validated_data_dict': validated,
        # index dict lacks the structured fields
    })
    assert category == 'full'
    assert score == 100.0


def test_for_index_unsupported_type():
    score, category = completeness.for_index(
        {'validated_data_dict': json.dumps({'type': 'harvest'})})
    assert score is None and category is None


def test_sort_value_orders_lexicographically():
    scores = [9.5, 100.0, 85.3, 0.0, 20.0]
    padded = [completeness.sort_value(s) for s in scores]
    assert padded == ['009.5', '100.0', '085.3', '000.0', '020.0']
    # el orden lexicografico de las claves coincide con el numerico
    assert sorted(padded) == [completeness.sort_value(s)
                              for s in sorted(scores)]


def test_sort_value_none_passthrough():
    assert completeness.sort_value(None) is None
