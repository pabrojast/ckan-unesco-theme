# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_stats` (dashboard de progreso IHP-IX)."""
import json

import pytest

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_stats as S


SUMMARIES = [
    {'country': 'Kenya', 'region': 'Africa', 'latitude': -1.29, 'longitude': 36.82},
    {'country': 'Chile', 'region': 'Latin America and the Caribbean', 'latitude': -33.45, 'longitude': -70.66},
    {'country': 'Republic of Korea', 'region': 'Asia and the Pacific', 'latitude': 37.57, 'longitude': 126.98},
    {'country': 'Türkiye', 'region': 'Europe and North America', 'latitude': 39.93, 'longitude': 32.86},
    {'country': 'Palestine', 'region': 'Arab States', 'latitude': 31.9, 'longitude': 35.2},
    {'country': 'Nowhere', 'region': 'Africa', 'latitude': 0, 'longitude': 0},  # sin coordenadas
]
GROUPS = [('republic-of-korea', 'Republic of Korea'), ('kenya', 'Kenya')]


def _row(**overrides):
    row = {
        'id': 'x', 'status': 'published', 'title': 't',
        'priority_area': 'PA1', 'output': '1.3', 'key_activity': '', 'key_activity_code': '',
        'biennium': '2024-2025', 'institution': 'Inst A', 'institution_type': 'University',
        'reported_by': 'u1', 'country': 'Kenya', 'supporting_member_state': '',
        'member_states': '', 'regions': '', 'flagships': '', 'cross_cutting_wg': '',
        'knowledge_product_type': '', 'num_knowledge_products': 0,
        'scientific_product_type': '', 'num_scientific_products': 0,
        'knowledge_activity_type': '', 'training_type': '', 'num_training_materials': 0,
        'num_curricula': 0, 'num_transboundary_ms': 0,
        'stakeholder_group_type': '', 'num_stakeholder_groups': 0,
        'stakeholders_knowledge': 0, 'stakeholders_knowledge_youth': 0,
        'stakeholders_knowledge_female': 0,
        'stakeholders_awareness': 0, 'stakeholders_awareness_youth': 0,
        'stakeholders_awareness_female': 0,
        'synergies': '', 'unesco_participation': '',
    }
    for gate in ('unesco_secretariat_participation', 'has_flagship', 'has_member_state_support',
                 'has_synergies', 'regions_benefit', 'kpi_1a_active', 'kpi_1b_active',
                 'kpi_2_active', 'kpi_3_active', 'kpi_4_active', 'kpi_5_active',
                 'kpi_6_active', 'kpi_8_active'):
        row[gate] = False
    row.update(overrides)
    return row


@pytest.fixture
def index():
    return S.build_country_index(SUMMARIES, GROUPS)


@pytest.fixture
def rows():
    return [
        # 1: PA1/1.3, KA 1.3.2, 2 tipos de conocimiento con 10 productos (puerta False)
        _row(id='a', key_activity='1.3.2. Research', knowledge_product_type='["Report", "Tool"]',
             num_knowledge_products=10, member_states='["Chile", "republic-of-korea"]',
             regions='["Africa"]', flagships='["FRIEND-Water"]',
             cross_cutting_wg='["Ecohydrology and Water Quality"]',
             stakeholders_knowledge=100, stakeholders_knowledge_youth=40,
             stakeholders_knowledge_female=50, knowledge_activity_type='["Seminar or online webinar"]'),
        # 2: PA1/1.3, KA 1.3.5, científicos, bienio 2022-2023, país heredado 'Turkey'
        _row(id='b', key_activity='1.3.5 Pilot', scientific_product_type='["Patents"]',
             num_scientific_products=3, kpi_1b_active=True, biennium='2022 - 2023',
             country='Turkey', institution='Inst B', reported_by='u2',
             training_type='["Online Course"]', num_training_materials=2),
        # 3: PA1/1.6 sin key activity, curricula, transboundary, grupos
        _row(id='c', output='1.6', num_curricula=2, num_transboundary_ms=4,
             supporting_member_state='State of Palestine',
             stakeholder_group_type='["Government Agencies (national ministries)"]',
             num_stakeholder_groups=3, stakeholders_awareness=1000,
             stakeholders_awareness_female=250, flagships='["FRIEND", "No"]'),
        # 4: PA2/2.1 pendiente: no cuenta
        _row(id='d', priority_area='PA2', output='2.1', status='pending',
             num_knowledge_products=99, kpi_1a_active=True),
        # 5: PA2/2.1 publicada, país desconocido (no resuelto), sin institución
        _row(id='e', priority_area='PA2', output='2.1', country='Atlantis', institution='',
             reported_by='', biennium='2024-2025', num_curricula=1, kpi_4_active=True),
    ]


def test_build_country_index_resolves_names_slugs_and_aliases(index):
    assert index['kenya']['region'] == 'Africa'
    assert index['republic-of-korea']['name'] == 'Republic of Korea'
    assert index['turkey']['name'] == 'Türkiye'
    assert index['state of palestine']['name'] == 'Palestine'
    assert index['nowhere']['lat'] is None


def test_overall_totals_union_of_country_fields(rows, index):
    stats = S.compute_progress_stats(rows, 'overall', country_index=index)
    ov = stats['overview']
    assert ov['activities'] == 4          # la pendiente no cuenta
    # Kenya (a, c, e via country), Chile, Republic of Korea (member_states),
    # Türkiye (country alias), Palestine (supporting), Atlantis (no resuelto)
    assert ov['member_states_impacted'] == 6
    assert ov['unresolved_member_states'] == ['Atlantis']
    assert ov['institutions'] == 2
    assert ov['contributors'] == 2
    assert [(d['key'], d['count']) for d in ov['by_dimension']] == [('PA1', 3), ('PA2', 1)]
    assert ov['by_dimension'][0]['label'].startswith('PA1 – Scientific')
    regions = {r['key']: r for r in ov['by_region']}
    # Kenya (filas a y c); la fila e reporta desde 'Atlantis' (sin región)
    assert regions['Africa'] == {'key': 'Africa', 'member_states': 1, 'activities': 2}
    assert regions['Asia and the Pacific']['member_states'] == 2  # UNESCO incluye Türkiye en ambas regiones
    # Mapa: sólo países con coordenadas; Kenya acumula roles
    points = {p['country']: p for p in ov['map']}
    assert points['Kenya']['activities'] == 2 and points['Kenya']['as_reporting'] == 2
    assert points['Republic of Korea']['as_beneficiary'] == 1
    assert 'Atlantis' not in points
    assert [b['key'] for b in ov['by_biennium']] == ['2022-2023', '2024-2025']
    assert 'output_biennium_matrix' in ov
    assert ov['output_biennium_matrix']['outputs'] == ['1.3', '1.6', '2.1']


def test_kpis_count_rows_with_data_even_when_gate_is_false(rows, index):
    stats = S.compute_progress_stats(rows, 'overall', country_index=index)
    k1 = stats['kpi_1']
    assert k1['knowledge_products'] == 10 and k1['scientific_products'] == 3
    assert k1['active_activities'] == 2
    # Alias 'Report' → 'Report or paper'; cada tipo suma el conteo completo (Power BI)
    assert k1['knowledge_by_type'] == [
        {'key': 'Report or paper', 'activities': 1, 'products': 10},
        {'key': 'Tool', 'activities': 1, 'products': 10},
    ]
    assert k1['scientific_by_type'] == [{'key': 'Patents', 'activities': 1, 'products': 3}]
    k2 = stats['kpi_2']
    assert (k2['individuals'], k2['youth'], k2['female']) == (100, 40, 50)
    assert k2['pct_youth'] == 40.0 and k2['pct_female'] == 50.0
    assert k2['by_activity_type'] == [{'key': 'Seminar or online webinar', 'activities': 1, 'individuals': 100}]
    k3 = stats['kpi_3']
    assert k3['materials'] == 2
    assert k3['by_type'] == [{'key': 'Online training course', 'activities': 1, 'materials': 2}]
    assert stats['kpi_4']['curricula'] == 3
    k5 = stats['kpi_5']
    assert k5['individuals'] == 1000 and k5['pct_female'] == 25.0 and k5['pct_youth'] == 0.0
    k6 = stats['kpi_6']
    assert k6['member_states_reported'] == 4 and k6['member_states_distinct'] == 2
    assert [p['country'] for p in k6['map']] == ['Kenya', 'Palestine']
    k8 = stats['kpi_8']
    assert k8['stakeholder_groups'] == 3
    assert k8['by_type'] == [{'key': 'Government Agencies', 'activities': 1, 'groups': 3}]


def test_percentages_are_none_when_total_is_zero(index):
    stats = S.compute_progress_stats([_row()], 'overall', country_index=index)
    assert stats['kpi_2']['pct_youth'] is None
    assert stats['kpi_5']['pct_female'] is None
    assert stats['kpi_1']['knowledge_by_type'] == []


def test_output_scope_breaks_down_by_key_activity(rows, index):
    stats = S.compute_progress_stats(rows, 'output', '1.3', country_index=index)
    assert stats['scope'] == {
        'kind': 'output', 'value': '1.3', 'dimension': 'key_activity',
        'label': 'Output 1.3 – ' + C.output_title('1.3'),
    }
    assert stats['overview']['activities'] == 2
    keys = [d['key'] for d in stats['overview']['by_dimension']]
    assert keys == ['1.3.2', '1.3.5']
    produced = {d['key']: d for d in stats['produced_by_dimension']}
    assert produced['1.3.2']['knowledge'] == 10 and produced['1.3.5']['scientific'] == 3
    assert produced['1.3.5']['training'] == 2
    reached = {d['key']: d for d in stats['reached_by_dimension']}
    assert reached['1.3.2']['knowledge_improved'] == 100
    assert 'output_biennium_matrix' not in stats['overview']
    kas = stats['options']['key_activities']
    assert kas and all(k['code'].startswith('1.3.') and k['title'] for k in kas)
    assert kas == [{'code': i['code'], 'title': i['title']} for i in C.key_activities_for('1.3')]


def test_by_output_lists_all_34_outputs_in_every_scope(rows, index):
    for scope, value in (('overall', None), ('pa', 'PA1'), ('flagship', 'FRIEND'),
                         ('output', '1.3')):
        stats = S.compute_progress_stats(rows, scope, value, country_index=index)
        by_output = stats['overview']['by_output']
        assert [o['key'] for o in by_output] == C.all_output_codes()
        assert by_output[0] == {'key': '1.1', 'label': C.output_title('1.1'), 'pa': 'PA1', 'count': 0}
    overall = S.compute_progress_stats(rows, 'overall', country_index=index)
    counts = {o['key']: o['count'] for o in overall['overview']['by_output']}
    assert counts['1.3'] == 2 and counts['1.6'] == 1 and counts['2.1'] == 1
    # Con filtro de bienio los conteos cambian pero la lista sigue completa
    filtered = S.compute_progress_stats(rows, 'overall', filters={'biennium': '2022-2023'},
                                        country_index=index)
    counts = {o['key']: o['count'] for o in filtered['overview']['by_output']}
    assert counts['1.3'] == 1 and len(filtered['overview']['by_output']) == 34
    k1 = overall['kpi_1']
    assert (k1['active_knowledge_activities'], k1['active_scientific_activities']) == (1, 1)


def test_unspecified_bucket_sorts_last(rows, index):
    stats = S.compute_progress_stats(rows, 'pa', 'PA1', country_index=index)
    assert stats['scope']['dimension'] == 'output'
    assert [d['key'] for d in stats['overview']['by_dimension']] == ['1.3', '1.6']
    rows2 = rows + [_row(id='f', output='')]
    stats = S.compute_progress_stats(rows2, 'pa', 'PA1', country_index=index)
    assert [d['key'] for d in stats['overview']['by_dimension']] == ['1.3', '1.6', 'Unspecified']
    assert stats['overview']['by_dimension'][-1]['label'] == 'Unspecified'


def test_flagship_and_ctwg_scopes_use_aliases(rows, index):
    friend = S.compute_progress_stats(rows, 'flagship', 'FRIEND', country_index=index)
    assert friend['overview']['activities'] == 2   # 'FRIEND-Water' y 'FRIEND'
    assert friend['scope']['label'] == 'FRIEND-Water'
    assert friend['scope']['dimension'] == 'priority_area'
    eco = S.compute_progress_stats(rows, 'ctwg', 'Ecohydrology and Water Quality', country_index=index)
    assert eco['overview']['activities'] == 1


def test_filters_by_biennium_region_and_country(rows, index):
    by_biennium = S.compute_progress_stats(rows, 'overall', filters={'biennium': '2022-2023'},
                                           country_index=index)
    assert by_biennium['overview']['activities'] == 1   # '2022 - 2023' normalizado
    # Región: declarada en `regions` o inferida del país impactado
    asia = S.compute_progress_stats(rows, 'overall', filters={'region': 'Asia and the Pacific'},
                                    country_index=index)
    assert asia['overview']['activities'] == 2          # Republic of Korea y Türkiye (catálogo UNESCO)
    africa = S.compute_progress_stats(rows, 'overall', filters={'region': 'Africa'},
                                      country_index=index)
    assert africa['overview']['activities'] == 2       # a (declarada y Kenya) y c (Kenya)
    chile = S.compute_progress_stats(rows, 'overall', filters={'country': 'Chile'},
                                     country_index=index)
    assert chile['overview']['activities'] == 1
    assert chile['filters'] == {'country': 'Chile'}


def test_options_list_taxonomies(rows, index):
    stats = S.compute_progress_stats(rows, 'overall', country_index=index)
    opts = stats['options']
    assert opts['priority_areas'][0] == {'code': 'PA1', 'label': 'Scientific Research and Innovation'}
    assert [p['code'] for p in opts['priority_areas']] == list(C.PRIORITY_AREAS)
    assert len(opts['outputs_by_pa']['PA1']) == 10
    assert opts['outputs_by_pa']['PA1'][0] == {'code': '1.1', 'label': C.output_title('1.1')}
    assert opts['key_activities'] == []           # sólo en ámbito output
    assert {'code': 'FRIEND', 'label': 'FRIEND-Water', 'slug': 'friend'} in opts['flagships']
    assert opts['ctwgs'][1] == {'name': 'Ecohydrology and Water Quality',
                                'slug': 'ecohydrology-and-water-quality'}
    assert opts['biennia'] == ['2022-2023', '2024-2025']
    assert 'Africa' in opts['regions']


def test_invalid_scope_raises():
    with pytest.raises(ValueError):
        S.compute_progress_stats([], 'galaxy')


def test_output_is_json_serializable(rows, index):
    stats = S.compute_progress_stats(rows, 'overall', country_index=index)
    json.dumps(stats)
