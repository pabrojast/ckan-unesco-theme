# -*- coding: utf-8 -*-
"""Tests de `ihpix_constants` (títulos de Output y helpers) y del módulo de
cadenas i18n."""
import json

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_i18n_strings as S


def test_output_titles_default_to_codes_only():
    titles = C.load_output_titles(path='/nonexistent/ihpix_output_titles.json')
    assert titles == {}


def test_output_titles_loaded_from_json(tmp_path):
    path = tmp_path / 'ihpix_output_titles.json'
    path.write_text(json.dumps({'1.1': 'Water science networks', '9.9': 'x'}),
                    encoding='utf-8')
    titles = C.load_output_titles(path=str(path))
    assert titles['1.1'] == 'Water science networks'
    # No valida contra OUTPUTS: un código desconocido también se carga
    assert titles['9.9'] == 'x'


def test_output_label_falls_back_to_code(monkeypatch):
    monkeypatch.setattr(C, '_output_titles_cache', {'1.1': 'Networks'})
    assert C.output_label('1.1') == '1.1 – Networks'
    assert C.output_label('1.2') == '1.2'
    assert C.output_title('1.2') == ''


def test_priority_area_for_output():
    assert C.priority_area_for_output('1.10') == 'PA1'
    assert C.priority_area_for_output('5.5') == 'PA5'
    assert C.priority_area_for_output('9.1') is None


def test_i18n_strings_cover_taxonomies():
    assert set(S.PRIORITY_AREA_TITLES) == set(C.PRIORITY_AREAS.values())
    assert set(S.REGIONS) == set(C.REGIONS)
    assert set(S.CROSS_CUTTING_WGS) == set(C.CROSS_CUTTING_WGS)
    assert set(S.LEAD_INSTITUTION_TYPES) == set(C.LEAD_INSTITUTION_TYPES)
    assert set(S.SCIENTIFIC_PRODUCT_TYPES) == set(C.SCIENTIFIC_PRODUCT_TYPES)
    assert set(S.TRAINING_TYPES) == set(C.TRAINING_TYPES)
    # 'Other' aparece en varias listas; se cubre desde LEAD_INSTITUTION_TYPES
    assert set(C.KNOWLEDGE_PRODUCT_TYPES) - {'Other'} == set(S.KNOWLEDGE_PRODUCT_TYPES)
    assert set(C.KNOWLEDGE_ACTIVITY_TYPES) - {'Other'} == set(S.KNOWLEDGE_ACTIVITY_TYPES)
    assert set(C.STAKEHOLDER_GROUP_TYPE_VALUES) - {'Other'} == set(S.STAKEHOLDER_GROUP_TYPES)
