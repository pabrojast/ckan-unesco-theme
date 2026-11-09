# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_forms` (sin CKAN)."""
import datetime
import json

import pytest

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_forms as F


def _full_payload(**overrides):
    """Payload mínimo válido para un envío a revisión (todas las preguntas
    Sí/No respondidas, como exige el formulario oficial)."""
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
    for gate in F.GATE_FIELDS_REQUIRED:
        data[gate] = 'no'
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
    assert exc.value.details['description'][0] == 'description_required'
    assert exc.value.details['output'][0] == 'output_required'
    # Las 12 preguntas Sí/No deben venir respondidas
    for gate in F.GATE_FIELDS_REQUIRED:
        assert exc.value.details[gate][0] == 'gate_required'


def test_unanswered_gate_blocks_submission_but_not_draft():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(kpi_4_active=''), is_draft=False)
    assert set(exc.value.errors) == {'kpi_4_active'}
    values = F.validate_report_payload({'title': 'x', 'kpi_4_active': ''}, is_draft=True)
    assert values['kpi_4_active'] is None
    # Cualquier forma de 'yes'/'no' cuenta como respuesta
    values = F.validate_report_payload(_full_payload(kpi_4_active='yes', num_curricula='2'),
                                       is_draft=False)
    assert values['kpi_4_active'] is True and values['num_curricula'] == 2


def test_key_activity_code_validated_against_output():
    values = F.validate_report_payload(_full_payload(output='2.1', key_activity_code='2.1.1'),
                                       is_draft=False)
    assert values['key_activity_code'] == '2.1.1'
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(output='2.1', key_activity_code='1.3.2'),
                                  is_draft=False)
    assert exc.value.details['key_activity_code'][0] == 'key_activity_invalid'
    # Sin código elegido se deriva del texto heredado "x.y.z. …" si cuadra
    values = F.validate_report_payload(
        _full_payload(output='2.1', key_activity='2.1.2. Capacity building of educators'),
        is_draft=False)
    assert values['key_activity_code'] == '2.1.2'
    values = F.validate_report_payload(
        _full_payload(output='2.1', key_activity='1.3.2. Not this output'), is_draft=False)
    assert values['key_activity_code'] == ''


def test_legacy_aliases_are_accepted_and_stored_canonically():
    values = F.validate_report_payload(
        _full_payload(kpi_1a_active='yes', knowledge_product_type=['Report', 'Website'],
                      num_knowledge_products='2', kpi_3_active='yes',
                      training_type='Online Course, Lecture', num_training_materials='1',
                      biennium='2024 - 2025', institution_type='NGO',
                      has_flagship='yes', flagships=['FRIEND-Water', 'UWMP']),
        is_draft=False)
    assert json.loads(values['knowledge_product_type']) == ['Report or paper', 'Website']
    assert json.loads(values['training_type']) == ['Online training course', 'Lecture']
    assert values['biennium'] == '2024-2025'
    assert values['institution_type'] == 'Non-Governmental Organization'
    assert json.loads(values['flagships']) == ['FRIEND', 'UWMP']


def test_training_type_other_reset_when_gate_off():
    values = F.validate_report_payload(
        _full_payload(kpi_3_active='no', training_type=['Other'], training_type_other='Podcast'),
        is_draft=False)
    assert values['training_type'] == '' and values['training_type_other'] == ''
    values = F.validate_report_payload(
        _full_payload(kpi_3_active='yes', training_type=['Other'], training_type_other='Podcast',
                      num_training_materials='1'),
        is_draft=False)
    assert values['training_type_other'] == 'Podcast'


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


def test_multi_selects_reject_unknown_values_without_silent_loss():
    payload = _full_payload(
        has_flagship='yes',
        flagships=['FRIEND', 'NOT-A-FLAGSHIP', 'G-WADI'],
        regions_benefit='yes',
        regions='Africa,Mars',
        member_states=['fr', 'es'],
    )
    with pytest.raises(F.ReportValidationError) as error:
        F.validate_report_payload(payload, is_draft=False)
    assert {'flagships', 'regions'} <= set(error.value.errors)
    payload.update(flagships=['FRIEND', 'G-WADI'], regions=['Africa'])
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


@pytest.mark.parametrize('value', ['-3', 'abc', '1.8', '1e3', '2147483648', True, 3.1])
@pytest.mark.parametrize('draft', [True, False])
def test_invalid_integers_are_reported_without_silent_coercion(value, draft):
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(kpi_4_active='yes', num_curricula=value), is_draft=draft)
    assert 'num_curricula' in exc.value.errors


def test_unanswered_roundtrip_still_blocks_submission():
    original = _full_payload(kpi_4_active='', num_curricula='3')
    draft = F.validate_report_payload(original, is_draft=True)
    restored = F.activity_to_form_dict(draft)
    assert restored['kpi_4_active'] == ''
    assert restored['num_curricula'] == 3
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(restored, is_draft=False)
    assert 'kpi_4_active' in exc.value.errors


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
    # Pregunta sin responder (None) → '' para que el form no preseleccione
    assert F.activity_to_form_dict({'kpi_2_active': None})['kpi_2_active'] == ''
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


# ── Fase B: límites, URL, fechas, ratios y mensajes traducibles ─────────────

def test_long_text_limits_enforced():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            _full_payload(partners='p' * 501, additional_notes='n' * 3001,
                          key_activity='k' * 1001, synergies='s' * 1501),
            is_draft=False)
    assert set(exc.value.errors) >= {'partners', 'additional_notes', 'key_activity', 'synergies'}
    key, params = exc.value.details['partners']
    assert key == 'max_length' and params['max'] == 500


def test_link_must_be_http_url():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(link='www.example.org'), is_draft=True)
    assert exc.value.details['link'][0] == 'url_invalid'
    values = F.validate_report_payload(_full_payload(link='https://example.org/x'), is_draft=True)
    assert values['link'] == 'https://example.org/x'


def test_end_date_cannot_precede_start_date():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            _full_payload(start_date='2025-06-01', end_date='2025-01-01'), is_draft=False)
    assert exc.value.details['end_date'][0] == 'end_before_start'


def test_youth_and_female_cannot_exceed_total_when_gate_active():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(
            _full_payload(kpi_2_active='yes', stakeholders_knowledge='5',
                          stakeholders_knowledge_youth='6',
                          stakeholders_knowledge_female='2'),
            is_draft=False)
    assert 'stakeholders_knowledge_youth' in exc.value.errors
    assert 'stakeholders_knowledge_female' not in exc.value.errors
    # Con el gate en "no" no se comprueba (los hijos se resetean)
    values = F.validate_report_payload(
        _full_payload(kpi_2_active='no', stakeholders_knowledge='5',
                      stakeholders_knowledge_youth='6'), is_draft=False)
    assert values['stakeholders_knowledge_youth'] == 0


def test_email_regex_on_submission():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload(_full_payload(contact_email='ada@nodomain'), is_draft=False)
    assert exc.value.details['contact_email'][0] == 'email_invalid'


def test_errors_and_details_are_consistent():
    with pytest.raises(F.ReportValidationError) as exc:
        F.validate_report_payload({'title': ''}, is_draft=False)
    err = exc.value
    assert set(err.errors) == set(err.details)
    for field, (key, params) in err.details.items():
        assert key in F.MESSAGES
        assert err.errors[field] == F.MESSAGES[key].format(**params)
