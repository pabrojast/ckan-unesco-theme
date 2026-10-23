# -*- coding: utf-8 -*-
u"""Diapositivas 16:9 construidas sobre el registro de secciones del informe.

Una diapositiva por figura marcada `in_slides` (gráfico SVG + ≤ 4 filas
destacadas); las secciones sin figura (overview) paginan sus filas de 4 en
4. El anexo de fuentes nunca entra en la presentación. Mismo cálculo que el
dashboard (`ihpix_progress_stats`): las cifras coinciden siempre.
"""
from __future__ import unicode_literals

from ckanext.theme_ejemplo import ihpix_report_sections as SEC

ROWS_PER_SLIDE = 4
LABEL_LIMIT = 80  # caracteres por fila destacada: los títulos de Output no caben enteros


def _rows(rows):
    return [[SEC.clip(label, LABEL_LIMIT), value] for label, value in list(rows)[:ROWS_PER_SLIDE]]


def slides(stats, translate=SEC.identity, sections=None, formatter=None):
    u"""[{id, section_id, kicker, title, subtitle, figure, rows, notes}]."""
    built = SEC.build_sections(stats, translate, {
        'sections': sections, 'layout': 'slide', 'include_sources': False,
        'format_number': formatter})
    SEC.render_figures(built, 'slide', translate, formatter)
    pages = []
    for section in built:
        base = {'section_id': section['id'], 'kicker': section['kicker'],
                'title': section['title'], 'notes': section['notes']}
        figures = [fig for fig in section['figures'] if fig['in_slides']]
        if not figures:
            rows = section['highlights'] or [[t['label'], t['value']] for t in section['tiles']]
            for offset in range(0, max(len(rows), 1), ROWS_PER_SLIDE):
                pages.append(dict(base, id='{}-{}'.format(section['id'], offset // ROWS_PER_SLIDE + 1),
                                  subtitle='', figure=None,
                                  rows=_rows(rows[offset:offset + ROWS_PER_SLIDE])))
            continue
        for index, fig in enumerate(figures):
            rows = section['highlights'] if index == 0 else fig['top_rows']
            pages.append(dict(base, id='{}-{}'.format(section['id'], fig['id']),
                              subtitle=fig['title'], figure=fig, rows=_rows(rows)))
    return pages


def scope_title(stats, translate=SEC.identity):
    u"""Título traducido del ámbito ('Overall', 'PA1 – …', 'Output 1.3 – …')."""
    scope = stats.get('scope') or {}
    kind = scope.get('kind') or 'overall'
    value = scope.get('value') or ''
    if kind == 'pa':
        return SEC.dimension_label(value, 'priority_area', translate)
    if kind == 'output':
        return '{} {}'.format(translate('Output'), SEC.dimension_label(value, 'output', translate))
    if kind == 'flagship':
        from ckanext.theme_ejemplo import ihpix_constants as C
        return C.flagship_label(value)
    if kind == 'ctwg':
        return translate(value) if value else value
    return translate('Overall')
