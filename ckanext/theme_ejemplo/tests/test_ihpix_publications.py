# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_publications` (modal "Upload a publication")."""
import json

import pytest

from ckanext.theme_ejemplo import ihpix_publications as P

DEV210_FIELDS = [
    'document_doi', 'title_translated', 'notes_translated', 'custom_doi', 'citation',
    'custom_citation', 'document_type', 'ihp_water_theme', 'topic', 'tag_string', 'tag_uri',
    'publication_year', 'publisher_name', 'authors_json', 'dataset_scope', 'owner_org',
    'access_level', 'groups__0__id', 'groups__1__id', 'graphic_overview', 'language',
    'license_id', 'access_rights', 'identifier', 'name', 'contact_uri', 'contact_name',
    'contact_email', 'contact_url',
]
# Esquema `documents` de la rama production del fork (13 campos)
PRODUCTION_FIELDS = [
    'title_translated', 'notes_translated', 'tag_string', 'owner_org', 'groups__0__id',
    'groups__1__id', 'language', 'license_id', 'identifier', 'name', 'contact_name',
    'contact_email', 'publication_year',
]


def _form(**over):
    d = {
        'title': 'Groundwater atlas of the Sahel',
        'organization': 'org-1',
        'document_type': 'technical_report',
        'publication_year': '2025',
        'authors': 'Ada Lovelace; UNESCO\nAlan Turing; Univ. Manchester',
        'abstract': 'An **atlas**.',
        'keywords': 'groundwater, sahel',
        'source_kind': 'url',
        'source_url': 'https://example.org/atlas.pdf',
        'member_state': 'niger',
        'output_code': '1.3',
    }
    d.update(over)
    return d


def test_validate_url_source_ok():
    clean = P.validate_publication_input(_form(), allowed_org_ids=['org-1'])
    assert clean['title'] == 'Groundwater atlas of the Sahel'
    assert clean['publication_year'] == 2025
    assert clean['authors'] == [
        {'name': 'Ada Lovelace', 'affiliation': 'UNESCO'},
        {'name': 'Alan Turing', 'affiliation': 'Univ. Manchester'},
    ]
    assert clean['keywords'] == ['groundwater', 'sahel']
    assert clean['source_kind'] == 'url'
    assert clean['upload_filename'] == ''


def test_validate_requires_title_org_and_source():
    with pytest.raises(P.PublicationValidationError) as exc:
        P.validate_publication_input({'title': '', 'organization': ''})
    err = exc.value
    assert set(err.errors) == {'title', 'organization', 'source'}
    for field, (key, params) in err.details.items():
        assert err.errors[field] == P.MESSAGES[key].format(**params)


def test_validate_rejects_org_not_allowed_and_bad_values():
    with pytest.raises(P.PublicationValidationError) as exc:
        P.validate_publication_input(
            _form(organization='other', document_type='novel', publication_year='1800',
                  doi='not-a-doi', contact_email='x@y', source_url='ftp://x'),
            allowed_org_ids=['org-1'])
    e = exc.value.errors
    assert set(e) == {'organization', 'document_type', 'publication_year', 'doi',
                      'contact_email', 'source'}


def test_validate_file_source_checks_extension_and_size():
    clean = P.validate_publication_input(
        _form(source_kind='file', source_url=''), allowed_org_ids=['org-1'],
        upload_filename='report.PDF', upload_size=1024, max_upload_mb=50)
    assert clean['source_kind'] == 'file' and clean['upload_filename'] == 'report.PDF'
    with pytest.raises(P.PublicationValidationError) as exc:
        P.validate_publication_input(
            _form(source_kind='file', source_url=''), upload_filename='virus.exe',
            upload_size=60 * 1024 * 1024, max_upload_mb=50)
    assert 'source' in exc.value.errors
    assert exc.value.details['source'][0] == 'file_extension_invalid'


def test_doi_accepts_doi_org_url():
    clean = P.validate_publication_input(_form(doi='https://doi.org/10.1000/xyz123'))
    assert clean['doi'] == '10.1000/xyz123'


def test_build_package_dict_dev210_schema():
    clean = P.validate_publication_input(_form(), allowed_org_ids=['org-1'])
    pkg = P.build_package_dict(clean, DEV210_FIELDS, defaults={'contact_email': 'me@x.org'},
                               identifier='fixed-id')
    assert pkg['type'] == 'documents'
    assert pkg['name'] == 'groundwater-atlas-of-the-sahel'
    assert pkg['owner_org'] == 'org-1' and pkg['private'] is False
    assert pkg['title_translated'] == {'en': 'Groundwater atlas of the Sahel'}
    assert pkg['notes_translated'] == {'en': 'An **atlas**.'}
    assert pkg['document_type'] == 'technical_report'
    assert pkg['publication_year'] == 2025
    assert json.loads(pkg['authors_json'])[0]['name'] == 'Ada Lovelace'
    assert pkg['access_level'] == 'public'
    assert pkg['language'] == P.DEFAULT_LANGUAGE
    assert pkg['identifier'] == 'fixed-id'
    assert pkg['contact_email'] == 'me@x.org'
    assert pkg['tag_string'] == 'ihp-ix, ihp-ix-output-1.3, groundwater, sahel'
    assert [t['name'] for t in pkg['tags']][:2] == ['ihp-ix', 'ihp-ix-output-1.3']
    assert pkg['groups'] == [{'name': 'niger'}]
    assert 'document_doi' not in pkg  # sin DOI no se envía


def test_build_package_dict_filters_to_production_schema():
    clean = P.validate_publication_input(_form(doi='10.1000/abc'), allowed_org_ids=['org-1'])
    pkg = P.build_package_dict(clean, PRODUCTION_FIELDS, identifier='x')
    for absent in ('document_type', 'authors_json', 'document_doi', 'access_level'):
        assert absent not in pkg
    for present in ('title_translated', 'notes_translated', 'owner_org', 'language',
                    'license_id', 'identifier', 'tag_string', 'publication_year'):
        assert present in pkg


def test_build_package_dict_default_abstract_and_no_groups():
    clean = P.validate_publication_input(
        _form(abstract='', member_state='', keywords=''), allowed_org_ids=['org-1'])
    pkg = P.build_package_dict(clean, DEV210_FIELDS)
    assert pkg['notes_translated'] == {'en': P.DEFAULT_ABSTRACT}
    assert 'groups' not in pkg
    assert pkg['tag_string'] == 'ihp-ix, ihp-ix-output-1.3'


def test_build_resource_dict_url_and_upload():
    clean = P.validate_publication_input(_form())
    res = P.build_resource_dict(clean, ['url', 'name', 'description', 'format'], package_id='p1')
    assert res == {'package_id': 'p1', 'name': 'Groundwater atlas of the Sahel',
                   'url': 'https://example.org/atlas.pdf', 'format': 'PDF',
                   'description': 'An **atlas**.'}
    clean_f = P.validate_publication_input(
        _form(source_kind='file', source_url=''), upload_filename='slides.pptx')
    res_f = P.build_resource_dict(clean_f, [], package_id='p1')
    assert res_f['url'] == 'slides.pptx' and res_f['url_type'] == 'upload'
    assert res_f['format'] == 'PPTX'


def test_slugify_title_handles_accents_and_collisions():
    assert P.slugify_title('Água & Saneamento: relatório 2025') == 'agua-saneamento-relatorio-2025'
    assert P.slugify_title('Atlas', taken={'atlas', 'atlas-2'}) == 'atlas-3'
    assert P.slugify_title('!!').startswith('publication-')
    assert len(P.slugify_title('x' * 500)) <= 90


def test_parse_authors_single_line_commas_and_dedupe():
    assert P.parse_authors('A, B, A') == [{'name': 'A'}, {'name': 'B'}]
    assert P.parse_authors('') == [] and P.parse_authors(None) == []


def test_map_schema_errors():
    mapped = P.map_schema_errors({
        'title_translated': {'en': ['Missing value']},
        'owner_org': ['Organization does not exist'],
        'resources': [{'url': ['Missing']}],
        'identifier': ['Invalid'],
    })
    assert mapped['title'] == 'Missing value'
    assert mapped['organization'] == 'Organization does not exist'
    assert mapped['source'].startswith('{')  # el error anidado se serializa
    assert mapped['__all__'].startswith('identifier:')


def test_link_item_for_package():
    item = P.link_item_for_package({'id': 'abc', 'name': 'atlas', 'title': 'Atlas',
                                    'publication_year': 2025,
                                    'organization': {'title': 'UNESCO'}})
    assert item['target_kind'] == 'package' and item['target_id'] == 'abc'
    assert item['url'] == '/documents/atlas'
    assert item['description'] == 'UNESCO · 2025'


def test_prefilled_dataset_url():
    qs = P.prefilled_dataset_url(owner_org='o1', output_code='2.1', member_state='chile')
    assert qs.startswith('?owner_org=o1')
    assert 'tag_string=ihp-ix%2Cihp-ix-output-2.1' in qs
    assert 'groups__0__id=chile' in qs


def test_i18n_messages_covered():
    from ckanext.theme_ejemplo import ihpix_i18n_strings as S
    assert set(P.MESSAGES.values()) <= set(S.VALIDATION_MESSAGES)
