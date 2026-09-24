# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_forms` (sin CKAN)."""
import datetime
import json

import pytest

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_forms as F


def _full_payload(**overrides):
    """Payload mínimo válido para un envío a revisión."""
    data = {
        'title': 'Water education workshop',
        'priority_area': 'PA2',
        'output': '2.1',
        'focal_point_name': 'Ada Lovelace',
        'contact_email': 'ada@example.org',
        'institution_type': 'University',
        'institution': 'Example University',
        'biennium': '2024-2025',
        'description': 'Short description',
        'outcomes': 'Some outcomes',
    }
    data.update(overrides)
    return data


def test_draft_only_requires_title():
    values = F.validate_report_payload({'title': 'Only a title'}, is_draft=True)
    assert values['title'] == 'Only a title'
    # Sin PA el borrador cae en PA1 para respetar el NOT NULL
    assert values['priority_area'] == 'PA1'
    assert values['institution'] == ''


def test_draft_without_title_fails():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload({'title': '   '}, is_draft=True)
    assert 'title' in exc.value.errors


def test_submission_requires_all_mandatory_fields_at_once():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload({'title': 'x'}, is_draft=False)
    errors = exc.value.errors
    for field in F.REQUIRED_FOR_SUBMISSION:
        assert field in errors
    assert 'priority_area' in errors


def test_submission_valid_payload_returns_column_values():
    values = F.validate_report_payload(_full_payload(), is_draft=False)
    assert values['priority_area'] == 'PA2'
    assert values['output'] == '2.1'
    # contact_name hereda del focal point cuando no viene
    assert values['contact_name'] == 'Ada Lovelace'
    # Todos los gates son booleanos
    for gate in F.BOOL_FIELDS:
        assert values[gate] is False


def test_invalid_priority_area_rejected_even_in_draft():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload({'title': 'x', 'priority_area': 'PA9'},
                                  is_draft=True)
    assert 'priority_area' in exc.value.errors


def test_output_must_belong_to_priority_area():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(output='1.3'), is_draft=False)
    assert 'output' in exc.value.errors


def test_invalid_biennium_and_institution_type():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            _full_payload(biennium='2030-2031', institution_type='Circus'),
            is_draft=False)
    assert set(exc.value.errors) >= {'biennium', 'institution_type'}


def test_invalid_email_on_submission():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(contact_email='nope'),
                                  is_draft=False)
    assert 'contact_email' in exc.value.errors


def test_short_text_cap_is_enforced():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            {'title': 'x', 'description': 'a' * 251}, is_draft=True)
    assert 'description' in exc.value.errors


def test_multi_selects_are_filtered_and_stored_as_json():
    payload = _full_payload(
        has_flagship='yes',
        flagships=['FRIEND', 'NOT-A-FLAGSHIP', 'G-WADI'],
        regions_benefit='yes',
        regions='Africa,Mars',
        member_states=['fr', 'es'],
    )
    values = F.validate_report_payload(payload, is_draft=False)
    assert json.loads(values['flagships']) == ['FRIEND', 'G-WADI']
    assert json.loads(values['regions']) == ['Africa']
    # member_states no tiene vocabulario cerrado: se respeta lo enviado
    assert json.loads(values['member_states']) == ['fr', 'es']


def test_gate_off_resets_children():
    payload = _full_payload(
        kpi_1a_active='no',
        num_knowledge_products='12',
        knowledge_product_type=['Book'],
        kpi_2_active='yes',
        stakeholders_knowledge='40',
        stakeholders_knowledge_youth='10',
        has_synergies='no',
        synergies='Should vanish',
    )
    values = F.validate_report_payload(payload, is_draft=False)
    assert values['num_knowledge_products'] == 0
    assert values['knowledge_product_type'] == ''
    assert values['stakeholders_knowledge'] == 40
    assert values['stakeholders_knowledge_youth'] == 10
    assert values['synergies'] == ''


def test_ints_are_clamped_and_tolerant():
    values = F.validate_report_payload(
        _full_payload(kpi_4_active='yes', num_curricula='-3',
                      kpi_6_active='yes', num_transboundary_ms='abc'),
        is_draft=False)
    assert values['num_curricula'] == 0
    assert values['num_transboundary_ms'] == 0


def test_dates_parsed_only_when_present():
    values = F.validate_report_payload(
        _full_payload(start_date='2025-03-01', end_date=''), is_draft=False)
    assert values['start_date'] == datetime.date(2025, 3, 1)
    assert values['end_date'] is None
    # reported_date no venía en el payload: no se toca
    assert 'reported_date' not in values


def test_invalid_date_reported():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            _full_payload(end_date='01/03/2025'), is_draft=False)
    assert 'end_date' in exc.value.errors


def test_activity_to_form_dict_round_trip():
    activity = {
        'id': 'abc',
        'title': 'T',
        'has_flagship': True,
        'kpi_1a_active': False,
        'flagships': json.dumps(['FRIEND']),
        'regions': '',
        'end_date': None,
        'num_curricula': 3,
    }
    form = F.activity_to_form_dict(activity)
    assert form['has_flagship'] == 'yes'
    assert form['kpi_1a_active'] == 'no'
    assert form['flagships'] == ['FRIEND']
    assert form['regions'] == []
    assert form['end_date'] == ''
    assert form['num_curricula'] == 3
    assert form['id'] == 'abc'


def test_form_field_lists_cover_model_columns():
    # Los nombres que envía el formulario deben ser columnas conocidas
    assert 'reported_date' not in F.SINGLE_FORM_FIELDS
    assert 'start_date' in F.SINGLE_FORM_FIELDS
    assert set(F.MULTI_FORM_FIELDS) == set(F.MULTI_FIELDS)
    for gate in F.GATE_RESETS:
        assert gate in F.BOOL_FIELDS


def test_all_output_codes_are_34():
    assert len(C.all_output_codes()) == 34
