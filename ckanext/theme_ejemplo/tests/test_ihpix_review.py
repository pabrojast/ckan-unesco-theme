"""Regresiones del documento de revisión: relaciones, XLSX y presentación."""
import io
import json
import zipfile

import pytest
from openpyxl import load_workbook
from ckanext.theme_ejemplo import ihpix_bulk as B, ihpix_forms as F
from ckanext.theme_ejemplo import ihpix_relations as R, ihpix_stats as S
from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo.ihpix_presentation import slides


def workbook(rows, relations=None):
    book = load_workbook(io.BytesIO(B.template_v1()))
    for data in rows:
        book['Activities'].append([data.get(key, '') for key in B.FIELDS])
    for name, records in (relations or {}).items():
        for data in records:
            book[name].append([data.get(key, '') for key in B.SHEETS[name]])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_official_taxonomy_completeness_and_consistency():
    taxonomy = C.load_key_activities()
    assert len(taxonomy) == 34
    assert sum(map(len, taxonomy.values())) == 151
    assert C.is_valid_key_activity('1.2', '1.2.3')
    assert C.is_valid_key_activity('4.7', '4.7.5')
    assert all(x['code'].rsplit('.', 1)[0] == output for output, items in taxonomy.items() for x in items)


def test_multiple_associations_count_once_globally_and_once_per_scope():
    relations = [
        {'priority_area':'PA1', 'output':'1.10', 'key_activity_code':'1.10.1'},
        {'priority_area':'PA2', 'output':'2.1', 'key_activity_code':'2.1.1'},
        {'priority_area':'PA2', 'output':'2.1', 'key_activity_code':'2.1.2'},
    ]
    row = F.validate_report_payload({'title':'Cross-area', 'contributions_json':relations,
        'kpi_2_active':'yes', 'stakeholders_knowledge':100}, True)
    overall = S.compute_progress_stats([row])
    assert overall['overview']['activities'] == 1
    assert overall['kpi_2']['individuals'] == 100
    assert {r['key']:r['count'] for r in overall['overview']['by_dimension']} == {'PA1':1, 'PA2':1}
    assert S.compute_progress_stats([row], 'output', '2.1')['kpi_2']['individuals'] == 100
    assert S.compute_progress_stats([row], 'output', '1.3')['overview']['activities'] == 0
    by_key = S.compute_progress_stats([row], 'output', '2.1')['overview']['by_dimension']
    assert {x['key'] for x in by_key} == {'2.1.1', '2.1.2'}


@pytest.mark.parametrize('item', [
    {'priority_area':'PA1', 'output':'2.1'},
    {'priority_area':'PA1', 'output':'1.10', 'key_activity_code':'1.1.1'},
    {'priority_area':'PA9', 'output':'9.1'}, 'text',
])
def test_invalid_associations_reject_entire_save(item):
    with pytest.raises(F.ReportValidationError):
        F.validate_report_payload({'title':'x', 'contributions_json':[item]}, True)


def test_country_roles_and_regions_remain_distinct():
    egypt = R.country_metadata('EG')
    assert egypt['electoral_group'] == 'Group Vb'
    assert set(egypt['regional_group']) == {'Africa', 'Arab States'}
    row = F.validate_report_payload({'title':'x', 'country':'Chile',
        'has_member_state_support':'yes', 'supporters_json':[{'country':'EG','types':['hosting','financial']}],
        'regions_benefit':'yes', 'member_states':['Kenya']}, True)
    prepared = S.prepare_row(row, S.build_country_index([]))
    assert prepared['impacted_roles']['Chile'] == {'reporting'}
    assert prepared['impacted_roles']['Egypt'] == {'supporter'}
    assert prepared['impacted_roles']['Kenya'] == {'beneficiary'}


def test_xlsx_template_accepts_incomplete_drafts_and_profile_defaults():
    result = B.parse(workbook([{'row_ref':'A1','title':'Draft'}]), {'focal_point_name':'Test author'})
    assert not result['errors']
    assert result['warnings']
    assert result['rows'][0]['data']['focal_point_name'] == 'Test author'
    assert result['rows'][0]['data']['save_as_draft'] == '1'


def test_xlsx_duplicate_refs_orphan_relations_invalid_numbers_and_formulas():
    result = B.parse(workbook([
        {'row_ref':'A1','title':'One','num_curricula':'-7'},
        {'row_ref':'A1','title':'Duplicate'},
        {'row_ref':'A2','title':'=HYPERLINK("https://invalid.example","bad")'},
    ], {'Contributions':[{'row_ref':'missing','priority_area':'PA1','output':'1.1'}]}))
    messages = ' '.join(x['message'] for x in result['errors'])
    assert 'unique' in messages and 'matching' in messages
    assert 'Formulas' in messages and 'whole number' in messages
    assert any(x['cell'].endswith('2') and x['field'] == 'num_curricula' for x in result['errors'])


def test_xlsx_relation_rows_report_their_origin():
    result = B.parse(workbook([{'row_ref':'A1','title':'One'}], {
        'Contributions':[{'row_ref':'A1','priority_area':'PA1','output':'2.1'}]}))
    assert any(x['sheet'] == 'Contributions' and x['row'] == 2 for x in result['errors'])


def test_xlsx_supports_multiple_relations_and_resources_without_publishing():
    result = B.parse(workbook([{'row_ref':'A1','title':'One','has_member_state_support':'yes'}], {
        'Contributions':[{'row_ref':'A1','priority_area':'PA1','output':'1.10'},
                         {'row_ref':'A1','priority_area':'PA2','output':'2.1'}],
        'Supporters':[{'row_ref':'A1','country':'CL','types':'financial;hosting'}],
        'Resources':[{'row_ref':'A1','link_type':'publication','target_kind':'url','url':'https://example.org/paper','title':'Paper'}]}))
    assert not result['errors']
    item = result['rows'][0]['data']
    assert len(item['contributions_json']) == 2 and item['save_as_draft'] == '1'
    assert item['supporters_json'][0]['types'] == ['financial','hosting']


def test_presentation_uses_dashboard_values_and_bounded_pages():
    stats = S.compute_progress_stats([{'title':'One', 'priority_area':'PA1', 'output':'1.10',
        'num_knowledge_products':5}])
    pages = slides(stats)
    assert pages[0]['rows'][0][1] == stats['overview']['activities']
    assert any(['Knowledge products', 5] in page['rows'] for page in pages)
    assert all(len(page['rows']) <= 4 for page in pages)
    # Cada figura `in_slides` es una diapositiva con su SVG; el anexo nunca entra
    assert any(page['figure'] and page['figure']['svg'].startswith('<svg') for page in pages)
    assert all(page['section_id'] != 'sources' for page in pages)
    assert {page['section_id'] for page in slides(stats, sections=['overview', 'kpi_1'])} == {'overview', 'kpi_1'}
    assert [page['id'] for page in slides(stats, sections=['overview'])] == ['overview-1']
    # Las filas destacadas se recortan: los títulos de Output no caben en 16:9
    assert all(len(label) <= 80 for page in pages for label, _ in page['rows'])
    assert any(label.endswith('\u2026') for page in pages for label, _ in page['rows'])


def test_secondary_output_without_key_does_not_inherit_primary_key():
    row = F.validate_report_payload({'title':'x', 'contributions_json':[
        {'priority_area':'PA1','output':'1.1','key_activity_code':'1.1.1'},
        {'priority_area':'PA2','output':'2.1','key_activity_code':''}]}, True)
    result = S.compute_progress_stats([row], 'output', '2.1')
    assert [x['key'] for x in result['overview']['by_dimension']] == [S.UNSPECIFIED]


def test_legacy_priority_area_without_output_keeps_its_count():
    assert R.dimension_values({'priority_area':'PA3'}, 'priority_area') == ['PA3']


@pytest.mark.parametrize('payload', [{'kpi_2_active':'maybe'}, {'output':'1.1'},
    {'key_activity_code':'1.1.1'}, {'contact_email':'invalid'}])
def test_informed_invalid_draft_answers_are_rejected(payload):
    with pytest.raises(F.ReportValidationError):
        F.validate_report_payload(dict(title='x', **payload), True)


def test_import_external_institution_does_not_inherit_verified_profile_id():
    result = B.parse(workbook([{'row_ref':'A','title':'External work','institution':'External NGO'}]),
        {'institution':'Profile University','institution_org_id':'profile-id'})
    row = result['rows'][0]['data']
    assert row['institution'] == 'External NGO' and not row['institution_org_id']


def test_xlsx_malformed_xml_is_a_validation_error():
    raw = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(B.template_v1())) as source, zipfile.ZipFile(raw, 'w') as target:
        for item in source.infolist():
            target.writestr(item, b'<worksheet>broken' if item.filename == 'xl/worksheets/sheet2.xml'
                            else source.read(item.filename))
    with pytest.raises(ValueError, match='valid XLSX'):
        B.parse(raw.getvalue())


def test_empty_country_never_resolves_to_a_country_with_non_latin_name():
    # Algunos títulos árabes producen un slug vacío; no deben registrar ese alias.
    for value in (None, '', '   '):
        assert R.country_metadata(value) is None
    assert '' not in R.country_index()
    assert R.country_metadata('CL')['country_title_en'] == 'Chile'
    assert R.country_metadata('مصر')['country_title_en'] == 'Egypt'
