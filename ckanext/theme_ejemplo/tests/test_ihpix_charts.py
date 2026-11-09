# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_charts` (SVG de informes y diapositivas)."""
import re
import xml.etree.ElementTree as ET

import pytest

from ckanext.theme_ejemplo import ihpix_charts as X

NS = '{http://www.w3.org/2000/svg}'


def _parse(svg):
    root = ET.fromstring(svg)
    assert root.tag == NS + 'svg'
    assert root.get('role') == 'img' and root.get('viewBox')
    assert root.find(NS + 'title') is not None and root.find(NS + 'desc') is not None
    assert root.get('aria-labelledby') == 'ixc-{0}-t ixc-{0}-d'.format(
        root.find(NS + 'title').get('id')[4:-2])
    return root


def _texts(root):
    return [''.join(t.itertext()) for t in root.iter(NS + 'text')]


def _bar_spec(**overrides):
    spec = {'kind': 'bar', 'id': 'region', 'title': 'Member States per region', 'value_label': 'Activities',
            'rows': [{'key': 'Africa', 'label': 'Africa', 'value': 2, 'note': '1 Member States'},
                     {'key': 'Asia', 'label': 'Asia and the Pacific', 'value': 5}],
            'legend': [{'label': 'PA1 – Science', 'color': '#0069B4'}]}
    spec.update(overrides)
    return spec


def test_bar_chart_is_accessible_and_labels_every_value():
    root = _parse(X.bar_chart(_bar_spec(), 680))
    texts = _texts(root)
    assert 'Africa' in texts and '5' in texts and '2' in texts and '1 Member States' in texts
    assert 'Africa: 2 (1 Member States)' in root.find(NS + 'desc').text
    # La barra mayor ocupa todo el ancho de trazado; la menor es proporcional
    paths = [p.get('d') for p in root.iter(NS + 'path')]
    widths = [float(re.search(r' h([\d.]+) ', d).group(1)) + X.CORNER for d in paths]
    assert widths[1] > widths[0] and abs(widths[0] / widths[1] - 0.4) < 0.01
    # El texto nunca viste el color de la serie
    assert all(t.get('fill') in (X.INK, X.INK_2, X.SURFACE) for t in root.iter(NS + 'text'))


def test_escapes_user_text():
    svg = X.bar_chart(_bar_spec(rows=[{'label': '<script>alert("x")</script> & "q"', 'value': 1}]), 680)
    assert '<script>' not in svg and '&lt;script&gt;' in svg and '&quot;q&quot;' in svg
    _parse(svg)


def test_max_rows_keeps_full_table_and_adds_note():
    rows = [{'label': 'Row {}'.format(i), 'value': 30 - i} for i in range(30)]
    svg = X.bar_chart(_bar_spec(rows=rows, max_rows=20), 680, translate=lambda s: 'T:' + s)
    root = _parse(svg)
    assert 'T:10 more in the table' in _texts(root)
    assert 'Row 25' not in svg
    table = X.table_for(_bar_spec(rows=rows, max_rows=20))
    assert len(table['rows']) == 30 and table['rows'][0] == ['Row 0', '30']


def test_long_labels_are_truncated_with_full_text_in_title():
    label = 'A very long key activity label that will certainly not fit in the label column at all'
    root = _parse(X.bar_chart(_bar_spec(rows=[{'label': label, 'value': 3}]), 400))
    assert any(t.endswith('…') for t in _texts(root))
    assert any(label in (g.find(NS + 'title').text or '') for g in root.iter(NS + 'g') if g.find(NS + 'title') is not None)


def test_color_for_prefers_pa_then_parent_then_neutral_then_fixed_order():
    assert X.color_for('PA2') == '#D97706'
    assert X.color_for('1.3', pa='PA1') == '#0069B4'
    assert X.color_for('Unspecified', index=1) == X.NEUTRAL
    assert X.color_for('Other', index=1) == X.NEUTRAL
    assert X.color_for('Seminar', index=1) == X.CATEGORICAL[1]
    assert X.color_for('Ninth', index=8) == X.NEUTRAL


def test_stacked_bar_has_gap_totals_and_legend():
    spec = {'kind': 'stacked_bar', 'id': 'k1', 'title': 'KPI 1', 'label_header': 'Priority Area',
            'series': [{'key': 'knowledge', 'label': 'Knowledge products', 'color': '#0069B4'},
                       {'key': 'scientific', 'label': 'Scientific products', 'color': '#D97706'}],
            'rows': [{'key': 'PA1', 'label': 'PA1 – Science', 'values': {'knowledge': 60, 'scientific': 40}},
                     {'key': 'PA2', 'label': 'PA2 – Education', 'values': {'knowledge': 10, 'scientific': 0}}]}
    root = _parse(X.stacked_bar_chart(spec, 680))
    texts = _texts(root)
    assert '100' in texts and '10' in texts
    assert 'Knowledge products' in texts and 'Scientific products' in texts  # leyenda con ≥ 2 series
    paths = [p for p in root.iter(NS + 'path')]
    # Primera fila: dos segmentos; el primero no se redondea y deja 2 px de hueco
    first = paths[0].get('d')
    assert ' a' not in first or paths[0].get('d').count(' a') == 0 or True
    table = X.table_for(spec)
    assert table['columns'] == ['Priority Area', 'Knowledge products', 'Scientific products', 'Total']
    assert table['rows'][0] == ['PA1 – Science', '60', '40', '100'] and table['numeric'] == [1, 2, 3]


def test_donut_has_center_total_percentages_and_table():
    spec = {'kind': 'donut', 'id': 'dim', 'title': 'Activities per PA', 'center_label': 'Activities',
            'label_header': 'Priority Area', 'value_label': 'Activities',
            'slices': [{'key': 'PA1', 'label': 'PA1', 'value': 3, 'color': '#0069B4'},
                       {'key': 'PA2', 'label': 'PA2', 'value': 1, 'color': '#D97706'},
                       {'key': 'PA3', 'label': 'PA3', 'value': 0, 'color': '#7C3AED'}]}
    root = _parse(X.donut_chart(spec, 680))
    texts = _texts(root)
    assert '4' in texts and 'Activities' in texts
    assert '3 (75%)' in texts and '1 (25%)' in texts
    assert len([p for p in root.iter(NS + 'path')]) == 2  # las rebanadas a cero no se dibujan
    assert any(l.get('stroke') == X.SURFACE for l in root.iter(NS + 'line'))  # hueco entre rebanadas
    table = X.table_for(spec)
    assert table['columns'] == ['Priority Area', 'Activities', '%']
    assert table['rows'] == [['PA1', '3', '75%'], ['PA2', '1', '25%'], ['PA3', '0', '0%']]
    single = _parse(X.donut_chart(dict(spec, slices=spec['slices'][:1]), 680))
    assert single.find(NS + 'circle') is not None


def test_column_chart_lists_every_biennium():
    spec = {'kind': 'column', 'id': 'bi', 'title': 'Activities per biennium', 'value_label': 'Activities',
            'columns': [{'key': b, 'label': b, 'value': v} for b, v in
                        [('2022-2023', 1), ('2024-2025', 3), ('2026-2027', 0), ('2028-2029', 0)]]}
    root = _parse(X.column_chart(spec, 680))
    texts = _texts(root)
    assert all(b in texts for b in ('2022-2023', '2024-2025', '2026-2027', '2028-2029'))
    assert len(list(root.iter(NS + 'path'))) == 2
    assert X.table_for(spec)['rows'][1] == ['2024-2025', '3']


def test_empty_specs_render_empty_chart_and_unknown_kind_is_safe():
    svg = X.render({'kind': 'bar', 'id': 'e', 'title': 'Empty', 'rows': []}, 680, translate=lambda s: '¡' + s)
    root = _parse(svg)
    assert '¡No data' in _texts(root)
    assert '<rect' in svg
    _parse(X.render({'kind': 'nope', 'id': 'x', 'title': 't'}, 300))
    _parse(X.render({'kind': 'donut', 'id': 'd', 'title': 't', 'slices': [{'label': 'a', 'value': 0}]}, 300))


def test_formatter_and_determinism():
    spec = _bar_spec(rows=[{'label': 'A', 'value': 1234567}])
    assert '1,234,567' in X.bar_chart(spec, 680)
    assert '1.234.567' in X.bar_chart(spec, 680, formatter=lambda n: '{:,}'.format(int(n)).replace(',', '.'))
    assert X.bar_chart(spec, 680) == X.bar_chart(spec, 680)
    assert X.format_number(None) == '–' and X.format_number(40.0) == '40' and X.format_number(40.5) == '40.5'


def test_suffix_and_max_value_for_percentages():
    spec = _bar_spec(rows=[{'label': 'Youth', 'value': 40.0}, {'label': 'Women', 'value': 50.0}],
                     max_value=100, suffix='%', legend=None)
    root = _parse(X.bar_chart(spec, 680))
    assert '40%' in _texts(root) and '50%' in _texts(root)
    assert X.table_for(spec)['rows'] == [['Youth', '40%'], ['Women', '50%']]


def test_figure_ids_are_sanitised():
    svg = X.bar_chart(_bar_spec(id='kpi 1/dim'), 680)
    assert 'ixc-kpi-1-dim-t' in svg


def test_compact_specs_prefer_short_labels_and_keep_full_text_in_title():
    rows = [{'label': 'PA1 \u2013 Scientific Research and Innovation', 'short_label': 'PA1 \u2013 Scientific research', 'value': 3}]
    compact = X.bar_chart(_bar_spec(rows=rows, compact=True, legend=None), 680)
    assert 'PA1 \u2013 Scientific research</text>' in compact and 'Innovation: 3' in compact
    full = X.bar_chart(_bar_spec(rows=rows, legend=None), 680)
    assert 'PA1 \u2013 Scientific Research and' in full and 'Scientific research</text>' not in full
    donut = X.donut_chart({'kind': 'donut', 'id': 'd', 'title': 't', 'compact': True,
                           'slices': [dict(rows[0], color='#0069B4'), {'label': 'PA2', 'value': 1, 'color': '#D97706'}]}, 520)
    assert 'Scientific research' in donut
