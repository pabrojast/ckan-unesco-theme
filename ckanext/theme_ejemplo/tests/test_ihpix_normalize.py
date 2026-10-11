# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_normalize` (valores heredados del Excel)."""
import json

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_normalize as N


def _legacy_row(**overrides):
    """Fila heredada típica: puertas en False aunque haya datos (seed)."""
    row = {
        'title': 'Legacy activity',
        'priority_area': 'PA1',
        'output': '1.3',
        'key_activity': '1.3.2. Research and preparation of state-of-the-art publications',
        'key_activity_code': '',
        'biennium': '2022 - 2023',
        'institution_type': 'University',
        'institution_type_other': '',
        'country': 'Turkey',
        'supporting_member_state': '',
        'member_states': json.dumps(['Kenya', 'Asia and the  Pacific', 'State of Palestine']),
        'regions': 'Asia and the  Pacific, Africa',
        'flagships': 'No',
        'cross_cutting_wg': 'Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus, Ecohydrology and Water Quality',
        'knowledge_product_type': 'Report, Statistic',
        'knowledge_product_type_other': '',
        'num_knowledge_products': 3,
        'scientific_product_type': '',
        'num_scientific_products': 0,
        'knowledge_activity_type': '',
        'knowledge_activity_type_other': '',
        'training_type': json.dumps(['Online Course', 'Training Video', 'Lecture']),
        'training_type_other': '',
        'num_training_materials': 4,
        'num_curricula': 0,
        'num_transboundary_ms': 0,
        'stakeholder_group_type': json.dumps([
            'Government Agencies (national water departments or ministries, environmental protection agencies)',
            'Private Sector (private companies involved in water-related services) or Industry (industrial companies)',
            'Community Groups (local communities, resident organizations) or Community-Based Organizations (local groups)',
        ]),
        'stakeholder_group_type_other': '',
        'stakeholder_group_name': '',
        'num_stakeholder_groups': 2,
        'stakeholders_knowledge': 0,
        'stakeholders_knowledge_youth': 0,
        'stakeholders_knowledge_female': 0,
        'stakeholders_awareness': 0,
        'stakeholders_awareness_youth': 5,
        'stakeholders_awareness_female': 0,
        'synergies': '',
        'unesco_participation': 'Yes',
        'unesco_secretariat_participation': False,
        'has_flagship': False,
        'has_member_state_support': False,
        'has_synergies': False,
        'regions_benefit': False,
        'kpi_1a_active': False, 'kpi_1b_active': False, 'kpi_2_active': False,
        'kpi_3_active': False, 'kpi_4_active': False, 'kpi_5_active': False,
        'kpi_6_active': False, 'kpi_8_active': False,
        'end_date': '2023-09-29T00:00:00',
    }
    row.update(overrides)
    return row


def test_clean_text_collapses_whitespace():
    assert N.clean_text('  Asia and the  Pacific ') == 'Asia and the Pacific'
    assert N.clean_text(None) == ''


def test_normalize_choice_applies_aliases_case_insensitively():
    assert N.normalize_choice('knowledge_product_type', 'Report') == 'Report or paper'
    assert N.normalize_choice('knowledge_product_type', 'statistic') == 'Statistic or data source'
    assert N.normalize_choice('training_type', 'Online Course') == 'Online training course'
    assert N.normalize_choice('training_type', 'training video') == 'Training video'
    assert N.normalize_choice('training_type', 'Physical training course implemented') == 'Physical training course'
    assert N.normalize_choice('flagships', 'FRIEND-Water') == 'FRIEND'
    assert N.normalize_choice('flagships', 'LaSII') == 'LASII'
    assert N.normalize_choice('flagships', 'No') is None
    assert N.normalize_choice('biennium', '2022 - 2023') == '2022-2023'
    assert N.normalize_choice('biennium', '2024–2025') == '2024-2025'
    assert N.normalize_choice('institution_type', '1') is None
    assert N.normalize_choice('institution_type', 'NGO') == 'Non-Governmental Organization'
    # Desconocido: se devuelve limpio, sin inventar
    assert N.normalize_choice('institution_type', 'Groundwater  Management Institution') == 'Groundwater Management Institution'


def test_split_legacy_multi_accepts_json_lists_and_comma_text():
    assert N.split_legacy_multi(['A', ' B ', '']) == ['A', 'B']
    assert N.split_legacy_multi('["A","B"]') == ['A', 'B']
    assert N.split_legacy_multi('A, B,C') == ['A', 'B', 'C']
    assert N.split_legacy_multi('') == []
    assert N.split_legacy_multi(None) == []


def test_split_legacy_multi_keeps_allowed_values_with_commas():
    text = ('Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus, '
            'Ecohydrology and Water Quality')
    assert N.split_legacy_multi(text, C.CROSS_CUTTING_WGS) == [
        'Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus',
        'Ecohydrology and Water Quality',
    ]


def test_normalize_multi_returns_valid_and_unknown():
    valid, unknown = N.normalize_multi('knowledge_product_type', 'Report, Statistic, Poster')
    assert valid == ['Report or paper', 'Statistic or data source']
    assert unknown == ['Poster']
    valid, unknown = N.normalize_multi('flagships', '["FRIEND-Water", "No", "G-WADI", "G-WADI"]')
    assert valid == ['FRIEND', 'G-WADI'] and unknown == []
    # Sin vocabulario (member_states): todo item limpio es válido, sin duplicados
    valid, unknown = N.normalize_multi('member_states', ['Kenya', 'Kenya ', 'Chile'])
    assert valid == ['Kenya', 'Chile'] and unknown == []


def test_stakeholder_group_types_strip_parenthetical_descriptions():
    valid, unknown = N.normalize_stakeholder_group_types(json.dumps([
        'Government Agencies (national water departments or ministries)',
        'Private Sector (private companies) or Industry (industrial companies)',
        'Non-Governmental Organizations (NGOs) (environmental groups working on water)',
        'Research and Academic Institutions',
        'University of Mpumalanga, University of the Free State',
    ]))
    assert valid == ['Government Agencies', 'Private Sector',
                     'Non-Governmental Organizations (NGOs)',
                     'Research and Academic Institutions']
    assert unknown == ['University of Mpumalanga, University of the Free State']


def test_country_name_aliases_and_index():
    assert N.normalize_country_name('Turkey') == 'Türkiye'
    assert N.normalize_country_name('State of Palestine') == 'Palestine'
    assert N.normalize_country_name('Central African') == 'Central African Republic'
    assert N.normalize_country_name('Papua') == 'Papua New Guinea'
    assert N.normalize_country_name('No') is None
    assert N.normalize_country_name('') == ''
    index = {'kenya': {'name': 'Kenya'}, 'republic-of-korea': {'name': 'Republic of Korea'}}
    assert N.normalize_country_name('kenya', index) == 'Kenya'
    assert N.normalize_country_name('republic-of-korea', index) == 'Republic of Korea'
    # Desconocido con índice: texto limpio
    assert N.normalize_country_name('Atlantis', index) == 'Atlantis'


def test_normalize_date_handles_mixed_formats():
    import datetime
    assert N.normalize_date('2023-09-29T00:00:00') == '2023-09-29'
    assert N.normalize_date('2023-04-21') == '2023-04-21'
    assert N.normalize_date(datetime.date(2024, 1, 2)) == '2024-01-02'
    assert N.normalize_date('') == ''
    assert N.normalize_date('not a date') == ''


def test_derive_gates_from_counts_and_types():
    gates = N.derive_gates(_legacy_row())
    assert gates['kpi_1a_active'] is True      # 3 productos
    assert gates['kpi_1b_active'] is False     # nada
    assert gates['kpi_3_active'] is True       # tipos + 4 materiales
    assert gates['kpi_5_active'] is True       # youth > 0 aunque total 0
    assert gates['kpi_8_active'] is True
    assert gates['kpi_4_active'] is False
    assert gates['has_flagship'] is False      # 'No' no cuenta como flagship
    assert gates['regions_benefit'] is True
    assert gates['has_member_state_support'] is False
    assert gates['unesco_secretariat_participation'] is True  # hereda 'Yes'
    # Una puerta ya activa se respeta aunque no haya datos
    assert N.derive_gates({'kpi_4_active': 'yes'})['kpi_4_active'] is True


def test_normalize_activity_row_returns_only_changes_and_is_idempotent():
    row = _legacy_row()
    changes = N.normalize_activity_row(row)
    assert changes['biennium'] == '2022-2023'
    assert changes['country'] == 'Türkiye'
    assert json.loads(changes['member_states']) == ['Kenya', 'Asia and the Pacific', 'Palestine']
    assert json.loads(changes['regions']) == ['Asia and the Pacific', 'Africa']
    assert changes['flagships'] == ''
    assert json.loads(changes['cross_cutting_wg']) == [
        'Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus',
        'Ecohydrology and Water Quality']
    assert json.loads(changes['knowledge_product_type']) == ['Report or paper', 'Statistic or data source']
    assert json.loads(changes['training_type']) == ['Online training course', 'Training video', 'Lecture']
    assert json.loads(changes['stakeholder_group_type']) == [
        'Government Agencies', 'Private Sector', 'Community Groups']
    assert changes['key_activity_code'] == '1.3.2'
    assert changes['end_date'] == '2023-09-29'
    assert changes['kpi_1a_active'] is True
    assert changes['unesco_secretariat_participation'] is True
    assert 'institution_type' not in changes
    assert 'kpi_1b_active' not in changes

    normalized = dict(row)
    normalized.update(changes)
    assert N.normalize_activity_row(normalized) == {}


def test_unknown_institution_type_becomes_other_with_detail():
    changes = N.normalize_activity_row(_legacy_row(
        institution_type='Groundwater Management Institution'))
    assert changes['institution_type'] == 'Other'
    assert changes['institution_type_other'] == 'Groundwater Management Institution'
    changes = N.normalize_activity_row(_legacy_row(institution_type='1'))
    assert changes['institution_type'] == ''


def test_unknown_multi_values_go_to_other_and_detail():
    changes = N.normalize_activity_row(_legacy_row(
        knowledge_product_type='Report, Poster', knowledge_product_type_other=''))
    assert json.loads(changes['knowledge_product_type']) == ['Report or paper', 'Other']
    assert changes['knowledge_product_type_other'] == 'Poster'
    # Sin 'Other' en el vocabulario (CTWG) el desconocido se descarta
    changes = N.normalize_activity_row(_legacy_row(cross_cutting_wg='["climate change"]'))
    assert changes['cross_cutting_wg'] == ''


def test_clean_row_produces_no_changes():
    clean = _legacy_row(
        biennium='2024-2025', country='Kenya', member_states='', regions='',
        flagships='', cross_cutting_wg='', knowledge_product_type='',
        num_knowledge_products=0, training_type='', num_training_materials=0,
        stakeholder_group_type='', num_stakeholder_groups=0,
        stakeholders_awareness_youth=0, unesco_participation='', end_date=None,
        key_activity='Free text without code')
    assert N.normalize_activity_row(clean) == {}
