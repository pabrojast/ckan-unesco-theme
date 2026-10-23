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
    # 'Other' aparece en varias listas; se cubre desde LEAD_INSTITUTION_TYPES
    assert set(C.TRAINING_TYPES) - {'Other'} == set(S.TRAINING_TYPES)
    assert set(C.KNOWLEDGE_PRODUCT_TYPES) - {'Other'} == set(S.KNOWLEDGE_PRODUCT_TYPES)
    assert set(C.KNOWLEDGE_ACTIVITY_TYPES) - {'Other'} == set(S.KNOWLEDGE_ACTIVITY_TYPES)
    assert set(C.STAKEHOLDER_GROUP_TYPE_VALUES) - {'Other'} == set(S.STAKEHOLDER_GROUP_TYPES)
    assert set(C.TRAINING_TYPE_GROUPS) - {'Other'} == set(S.TRAINING_TYPE_GROUPS)
    assert set(C.FLAGSHIP_LABELS.values()) == set(S.FLAGSHIP_LABELS)
    assert {k['title'] for k in C.KPIS.values()} == set(S.KPI_TITLES)
    assert {k['question'] for k in C.KPIS.values()} == set(S.KPI_QUESTIONS)
    assert {k['gate_question'] for k in C.KPIS.values()} == set(S.KPI_GATE_QUESTIONS)
    assert {k['target'] for k in C.KPIS.values()} == set(S.KPI_TARGETS)


def test_flagships_include_review_additions_and_preserve_existing_codes():
    assert len(C.FLAGSHIPS) == 21
    assert {'CRIDA', 'Youth4Water', 'IAHR Label'} <= set(C.FLAGSHIPS)
    # Orden alfabético de la página oficial (GRAPHIC antes que G-WADI)
    assert list(C.FLAGSHIPS) == sorted(C.FLAGSHIPS, key=lambda s: s.replace('-', '').lower())
    for extra in ('IWRM', 'JIIHP', 'UWMP'):
        assert extra in C.FLAGSHIPS
    assert C.flagship_label('FRIEND') == 'FRIEND-Water'
    assert C.flagship_label('LASII') == 'LaSII'
    assert C.flagship_label('G-WADI') == 'G-WADI'


def test_slugs_round_trip_for_flagships_and_ctwgs():
    for code in C.FLAGSHIPS:
        slug = C.slugify(code)
        assert slug == slug.lower() and ' ' not in slug
        assert C.flagship_for_slug(slug) == code
    assert C.flagship_for_slug('G-WADI') == 'G-WADI'   # tolera el código
    assert C.flagship_for_slug('nope') is None
    for name in C.CROSS_CUTTING_WGS:
        assert C.ctwg_for_slug(C.slugify(name)) == name
    assert C.ctwg_for_slug('ecohydrology-and-water-quality') == 'Ecohydrology and Water Quality'
    assert C.ctwg_for_slug('x') is None


def test_kpi_type_choices_include_microsoft_form_options():
    assert 'Report or paper' in C.KNOWLEDGE_PRODUCT_TYPES
    assert 'Website' in C.KNOWLEDGE_PRODUCT_TYPES and 'Brochure' in C.KNOWLEDGE_PRODUCT_TYPES
    assert C.KNOWLEDGE_PRODUCT_TYPES[-1] == 'Other'
    for t in ('Presentation', 'Lecture', 'Training video', 'Online training course', 'Other'):
        assert t in C.TRAINING_TYPES
    grouped = [t for values in C.TRAINING_TYPE_GROUPS.values() for t in values]
    assert sorted(grouped) == sorted(C.TRAINING_TYPES)
    assert C.KPIS['3']['other_column'] == 'training_type_other'
    assert C.KPIS['1a']['type_choices'] is C.KNOWLEDGE_PRODUCT_TYPES


def test_output_titles_json_ships_all_34_outputs():
    titles = C.load_output_titles(force=True)
    assert set(titles) == set(C.all_output_codes())
    assert all(titles[code] for code in titles)
    assert C.output_label('1.3').startswith('1.3 – Research on uncertainty')


def test_key_activities_json_loads_and_validates():
    kas = C.load_key_activities(force=True)
    assert set(kas) <= set(C.all_output_codes())
    assert len(kas) == 34
    total = sum(len(v) for v in kas.values())
    assert total >= 100
    for output, items in kas.items():
        for item in items:
            assert item['code'].startswith(output + '.')
            assert item['title']
    assert C.key_activities_for('9.9') == []
    assert C.key_activity_code('1.3.2. Research and …') == '1.3.2'
    assert C.key_activity_code('1.3.2.1 sub') == ''
    assert C.key_activity_code('Free text') == ''
    assert C.is_valid_key_activity('1.3', '1.3.2') is True
    assert C.is_valid_key_activity('1.3', '1.4.1') is False
    assert C.is_valid_key_activity('1.3', 'abc') is False
    assert C.key_activity_label('1.3.2').startswith('1.3.2 – ')


def test_key_activities_loaded_from_custom_json(tmp_path):
    path = tmp_path / 'kas.json'
    path.write_text(json.dumps({'9.9': [{'code': '9.9.1', 'title': 'Alpha'}, {'title': 'sin código'}]}),
                    encoding='utf-8')
    kas = C.load_key_activities(path=str(path))
    assert kas == {'9.9': [{'code': '9.9.1', 'title': 'Alpha'}]}
    assert C.load_key_activities(path='/nonexistent.json') == {}


def test_i18n_strings_cover_validation_messages():
    from ckanext.theme_ejemplo import ihpix_forms as F
    from ckanext.theme_ejemplo import ihpix_links as L
    literals = set(S.VALIDATION_MESSAGES)
    assert set(F.MESSAGES.values()) <= literals
    assert set(L.MESSAGES.values()) <= literals


def test_ihpix_snippet_modules_have_no_live_top_level_code():
    """Los snippets de macros no deben ejecutar nada al importarse (un `{# #}`
    anidado en un comentario dejó código vivo y rompió /ihpix/report en dev)."""
    import os
    from jinja2 import Environment, FileSystemLoader, nodes
    from jinja2.ext import Extension

    class CkanTags(Extension):
        tags = {'ckan_extends', 'snippet', 'resource', 'asset', 'url_for', 'link_for', 'image_for'}

        def parse(self, parser):
            tok = next(parser.stream)
            while parser.stream.current.type != 'block_end':
                next(parser.stream)
            return nodes.Output([nodes.Const('')]).set_lineno(tok.lineno)

    base = os.path.join(os.path.dirname(__file__), '..', 'templates')
    env = Environment(loader=FileSystemLoader(base),
                      extensions=['jinja2.ext.i18n', 'jinja2.ext.do', CkanTags])
    env.install_null_translations()
    for name in ('ihpix/snippets/publication_modal.html', 'ihpix/snippets/forms_assets.html',
                 'ihpix/snippets/activity_links.html', 'ihpix/snippets/page_styles.html',
                 'ihpix/snippets/report_section.html'):
        module = env.get_template(name).module  # evalúa el nivel superior
        assert any(not n.startswith('_') for n in dir(module)), name


def test_templates_do_not_call_gettext_with_printf_placeholders_and_no_kwargs():
    """El gettext "newstyle" de CKAN hace `texto % kwargs`: `_('… %(code)s …')`
    sin argumentos lanza KeyError al renderizar (500 en dev, 2026-09-24)."""
    import glob
    import io
    import os
    import re
    pat = re.compile(r"""(?<![\w.])_\(\s*(['"])(?P<s>(?:(?!\1).)*%\((?:[a-z_]+)\)[sdr](?:(?!\1).)*)\1\s*\)""")
    base = os.path.join(os.path.dirname(__file__), '..', 'templates')
    offenders = []
    for path in glob.glob(os.path.join(base, '**', '*.html'), recursive=True):
        source = io.open(path, encoding='utf-8').read()
        for m in pat.finditer(source):
            offenders.append((os.path.relpath(path, base), m.group('s')[:60]))
    assert offenders == []


def test_templates_do_not_nest_jinja_comments():
    """Un `{# … #}` dentro de otro cierra el comentario antes de tiempo y deja
    código de ejemplo vivo (UndefinedError en dev, 2026-09-24)."""
    import glob
    import io
    import os
    base = os.path.join(os.path.dirname(__file__), '..', 'templates')
    offenders = []
    for path in glob.glob(os.path.join(base, '**', '*.html'), recursive=True):
        source = io.open(path, encoding='utf-8').read()
        i = 0
        while True:
            a = source.find('{#', i)
            if a < 0:
                break
            b = source.find('#}', a + 2)
            if b < 0:
                break
            if '{#' in source[a + 2:b]:
                offenders.append((os.path.relpath(path, base), source[:a].count('\n') + 1))
            i = b + 2
    assert offenders == []
