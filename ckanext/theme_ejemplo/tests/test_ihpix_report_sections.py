# -*- coding: utf-8 -*-
"""Tests del registro de secciones del informe IHP-IX (`ihpix_report_sections`)."""
import pytest

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_i18n_strings as I
from ckanext.theme_ejemplo import ihpix_report_sections as SEC
from ckanext.theme_ejemplo import ihpix_stats as S

SUMMARIES = [
    {'country': 'Kenya', 'region': 'Africa', 'latitude': -1.29, 'longitude': 36.82},
    {'country': 'Chile', 'region': 'Latin America and the Caribbean', 'latitude': -33.45, 'longitude': -70.66},
]


def _row(**overrides):
    row = {'id': 'x', 'status': 'published', 'title': 't', 'priority_area': 'PA1', 'output': '1.3',
           'key_activity_code': '1.3.2', 'biennium': '2024-2025', 'institution': 'Inst A',
           'institution_type': 'University', 'reported_by': 'u1', 'country': 'Kenya',
           'member_states': '', 'regions': '', 'flagships': '', 'cross_cutting_wg': '',
           'knowledge_product_type': '', 'num_knowledge_products': 0, 'scientific_product_type': '',
           'num_scientific_products': 0, 'knowledge_activity_type': '', 'training_type': '',
           'num_training_materials': 0, 'num_curricula': 0, 'num_transboundary_ms': 0,
           'stakeholder_group_type': '', 'num_stakeholder_groups': 0,
           'stakeholders_knowledge': 0, 'stakeholders_knowledge_youth': 0, 'stakeholders_knowledge_female': 0,
           'stakeholders_awareness': 0, 'stakeholders_awareness_youth': 0, 'stakeholders_awareness_female': 0}
    row.update(overrides)
    return row


ROWS = [
    _row(id='a', knowledge_product_type='["Report or paper"]', num_knowledge_products=10,
         member_states='["Chile"]', stakeholders_knowledge=100, stakeholders_knowledge_youth=40,
         stakeholders_knowledge_female=50, knowledge_activity_type='["Seminar or online webinar"]',
         flagships='["FRIEND"]'),
    _row(id='b', priority_area='PA2', output='2.1', key_activity_code='', num_training_materials=2,
         training_type='["Online Course"]', num_curricula=1, country='Atlantis', institution='Inst B',
         biennium='2022-2023', num_transboundary_ms=3, num_stakeholder_groups=2,
         stakeholder_group_type='["Other"]', stakeholders_awareness=30),
    _row(id='c', priority_area='PA4', output='4.2', key_activity_code='', num_scientific_products=1,
         scientific_product_type='["Patents"]'),
]

SOURCES = [
    {'id': 'a', 'title': 'Alpha', 'institution': 'Inst A', 'outputs': ['1.3', '2.1'], 'biennium': '2024-2025',
     'priority_area': 'PA1', 'description': 'desc', 'outcomes': 'out'},
    {'id': 'b', 'title': 'Beta', 'institution': 'Inst B', 'outputs': ['2.1'], 'biennium': '2022-2023',
     'priority_area': 'PA2'},
    {'id': 'c', 'title': 'Gamma', 'institution': '', 'outputs': [], 'biennium': '', 'priority_area': ''},
]


@pytest.fixture
def index():
    return S.build_country_index(SUMMARIES)


def _stats(scope='overall', value=None, rows=ROWS, index=None):
    return S.compute_progress_stats(rows, scope, value, country_index=index)


def test_default_order_and_selection():
    sections = SEC.build_sections(_stats())
    assert [s['id'] for s in sections] == [sid for sid in SEC.SECTION_IDS if sid != 'sources']
    only = SEC.build_sections(_stats(), options={'sections': ['kpi_1', 'nope']})
    assert [s['id'] for s in only] == ['kpi_1']
    assert SEC.selected_ids(None) == list(SEC.SECTION_IDS)
    assert SEC.selected_ids(['kpi_2', 'overview']) == ['overview', 'kpi_2']
    assert SEC.selected_ids(['nope']) == list(SEC.SECTION_IDS)
    assert [sid for sid, _ in SEC.section_choices()] == [sid for sid in SEC.SECTION_IDS if sid != 'sources']


def test_sources_only_with_flag_and_grouped_by_pa_and_output():
    assert all(s['id'] != 'sources' for s in SEC.build_sections(_stats(), sources=SOURCES))
    sections = SEC.build_sections(_stats(), options={'include_sources': True, 'sources_detail': False},
                                  sources=SOURCES)
    appendix = sections[-1]
    assert appendix['id'] == 'sources' and appendix['appendix'] and appendix['count'] == 3
    groups = appendix['groups']
    assert [g['pa'] for g in groups] == ['PA1', 'PA2', S.UNSPECIFIED]
    assert groups[0]['outputs'][0]['code'] == '1.3' and groups[0]['outputs'][0]['activities'][0]['title'] == 'Alpha'
    assert groups[1]['outputs'][0]['activities'][0]['title'] == 'Beta'
    # En ámbito PA2 la actividad Alpha (1.3 y 2.1) se agrupa bajo 2.1
    pa2 = SEC.group_sources(SOURCES[:2], 'pa', 'PA2')
    assert [g['pa'] for g in pa2] == ['PA2'] and len(pa2[0]['outputs'][0]['activities']) == 2
    out = SEC.group_sources(SOURCES[:1], 'output', '2.1')
    assert out[0]['outputs'][0]['code'] == '2.1'


def test_dimension_figures_follow_scope(index):
    overall = {s['id']: s for s in SEC.build_sections(_stats(index=index))}
    kinds = [f['spec']['kind'] for f in overall['dimension']['figures']]
    assert kinds == ['donut', 'bar']  # 3 PA → donut; segunda figura: outputs
    assert overall['dimension']['figures'][1]['spec']['rows'][0]['color'] == C.PA_COLORS['PA1']
    pa = {s['id']: s for s in SEC.build_sections(_stats('pa', 'PA1', index=index))}
    assert [f['spec']['kind'] for f in pa['dimension']['figures']] == ['bar']
    assert pa['dimension']['figures'][0]['spec']['rows'][0]['label'].startswith('1.3')
    output = {s['id']: s for s in SEC.build_sections(_stats('output', '1.3', index=index))}
    rows = output['dimension']['figures'][0]['spec']['rows']
    assert rows[0]['key'] == '1.3.2' and rows[0]['color'] == SEC.X.ACTION
    assert output['kpi_1']['figures'][0]['spec']['label_header'] == 'Key Activity'


def test_geography_and_kpi6_tables_include_unresolved_countries(index):
    sections = {s['id']: s for s in SEC.build_sections(_stats(index=index))}
    geo = sections['geography']
    assert geo['table']['columns'] == list(SEC.COUNTRY_COLUMNS)
    names = [r[0] for r in geo['table']['rows']]
    assert 'Kenya' in names and 'Chile' in names and 'Atlantis *' in names
    assert any(note.startswith('*') for note in geo['notes'])
    assert geo['figures'][0]['spec']['rows'][0]['label'] == 'Africa'
    k6 = sections['kpi_6']
    assert [r[0] for r in k6['table']['rows']] == ['Atlantis *']


def test_timeline_pads_biennia_and_builds_matrix():
    timeline = {s['id']: s for s in SEC.build_sections(_stats())}['timeline']
    columns = timeline['figures'][0]['spec']['columns']
    assert [c['key'] for c in columns] == list(C.BIENNIA)
    assert [c['value'] for c in columns][:2] == [1, 2]
    assert timeline['table']['columns'][0] == 'Output' and timeline['table']['columns'][-1] == 'Total'
    assert len(timeline['table']['rows']) == 3


def test_kpi_sections_carry_tiles_highlights_and_type_figures():
    sections = {s['id']: s for s in SEC.build_sections(_stats())}
    k1 = sections['kpi_1']
    assert k1['kicker'] == 'KPI 1' and ['Knowledge products', 10] in k1['highlights']
    assert [f['in_slides'] for f in k1['figures']] == [True, False, False]
    assert k1['figures'][1]['spec']['rows'][0]['label'] == 'Report or paper'
    k2 = sections['kpi_2']
    assert ['Youth / female (%)', '40 / 50'] in k2['highlights']
    assert k2['figures'][1]['spec']['suffix'] == '%' and k2['figures'][1]['spec']['max_value'] == 100
    k5 = sections['kpi_5']
    assert ['Youth / female (%)', '0 / 0'] in k5['highlights']
    k34 = sections['kpi_34']
    assert k34['figures'][0]['spec']['series'][0]['key'] == 'materials'
    assert {r['key']: r['values'] for r in k34['figures'][0]['spec']['rows']}['PA2'] == {'materials': 2, 'curricula': 1}
    k8 = sections['kpi_8']
    assert k8['figures'][1]['spec']['rows'][0]['color'] == SEC.X.NEUTRAL  # 'Other' en neutro
    assert sections['produced_reached']['highlights'][0] == ['Knowledge products', 10]
    assert sections['institutions']['figures'][0]['spec']['rows'][0]['label'] == 'Inst A'


def test_render_figures_fills_svg_and_table_for_both_layouts(index):
    for layout in ('document', 'slide'):
        sections = SEC.render_figures(SEC.build_sections(_stats(index=index)), layout)
        for section in sections:
            for fig in section['figures']:
                assert fig['svg'].startswith('<svg') and 'viewBox="0 0 {} '.format(SEC.LAYOUTS[layout]['width']) in fig['svg']
                assert fig['table']['columns'] and fig['table']['rows']
    slide_sections = {s['id']: s for s in SEC.render_figures(SEC.build_sections(_stats(index=index)), 'slide')}
    assert 'PA1 \u2013 Scientific research' in slide_sections['dimension']['figures'][0]['svg']
    doc_sections = {s['id']: s for s in SEC.render_figures(SEC.build_sections(_stats(index=index)), 'document')}
    assert 'PA1 \u2013 Scientific Research and Innovation' in doc_sections['dimension']['figures'][0]['svg']


def test_translator_reaches_titles_labels_and_svg():
    sections = SEC.build_sections(_stats(), translate=lambda s: 'T:' + s)
    SEC.render_figures(sections, 'document', translate=lambda s: 'T:' + s)
    assert sections[0]['title'] == 'T:Implementation overview'
    assert sections[0]['tiles'][0]['label'] == 'T:Published activities'
    dimension = sections[1]
    assert dimension['figures'][0]['spec']['slices'][0]['label'].startswith('PA1 – T:Scientific')
    assert 'T:Activities' in dimension['figures'][0]['table']['columns'][1]


def test_empty_stats_do_not_fail():
    sections = SEC.build_sections(_stats(rows=[]), options={'include_sources': True}, sources=[])
    SEC.render_figures(sections, 'document')
    assert all(s['empty'] for s in sections)
    assert all('No data' in f['svg'] for s in sections for f in s['figures'])


def test_formatter_is_used_in_tiles_and_summaries():
    rows = [_row(id='big', stakeholders_knowledge=120579)]
    sections = {s['id']: s for s in SEC.build_sections(
        _stats(rows=rows), options={'format_number': lambda n: '{:,}'.format(int(n)).replace(',', '.')})}
    assert sections['kpi_2']['tiles'][0]['value'] == '120.579'
    assert '120.579' in sections['kpi_2']['summary'][0]
    assert sections['kpi_2']['highlights'][0] == ['Stakeholders', 120579]  # crudo para las diapositivas


def test_every_translated_key_is_registered_for_babel(index):
    seen = set()

    def recorder(text):
        seen.add(text)
        return text

    for scope, value in (('overall', None), ('pa', 'PA1'), ('output', '1.3'), ('flagship', 'FRIEND'),
                         ('ctwg', C.CROSS_CUTTING_WGS[0])):
        sections = SEC.build_sections(_stats(scope, value, index=index), recorder,
                                      {'include_sources': True, 'sources_detail': True}, sources=SOURCES)
        SEC.render_figures(sections, 'document', recorder)
        SEC.render_figures(sections, 'slide', recorder)
    SEC.render_figures(SEC.build_sections(_stats(rows=[]), recorder), 'document', recorder)
    SEC.section_choices(recorder)
    known = set()
    for name in dir(I):
        value = getattr(I, name)
        if name.isupper() and isinstance(value, list):
            known.update(value)
    known.update(C.PRIORITY_AREAS.values())
    known.update(C.REGIONS)
    known.update(C.KNOWLEDGE_PRODUCT_TYPES + C.SCIENTIFIC_PRODUCT_TYPES + C.KNOWLEDGE_ACTIVITY_TYPES
                 + C.TRAINING_TYPES + C.STAKEHOLDER_GROUP_TYPE_VALUES + C.CROSS_CUTTING_WGS)
    assert seen - known - {''} == set()
