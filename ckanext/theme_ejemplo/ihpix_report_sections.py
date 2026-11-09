# -*- coding: utf-8 -*-
u"""Registro de secciones del informe IHP-IX.

Módulo puro (sin CKAN). A partir del JSON de `ihpix_stats.compute_progress_stats`
construye una lista ordenada de *secciones* (`build_sections`) que alimenta
tanto el documento narrativo (`templates/ihpix/narrative.html`) como las
diapositivas 16:9 (`ihpix_presentation.slides`). Cada sección declara sus
fichas (`tiles`, HTML), sus filas destacadas (`highlights`, ≤ 4, para
diapositivas), sus figuras (`figures`, specs de `ihpix_charts`) y, si la
tiene, una tabla propia. Añadir una sección = añadir un constructor en
`BUILDERS` y su id en `SECTION_IDS`; las dos salidas la recogen solas.

Todo el texto sale ya traducido: `translate` se inyecta desde la vista
(`tk._`) y las claves son literales ingleses registrados en
`ihpix_i18n_strings.REPORT_LABELS` para que Babel las extraiga.
"""
from __future__ import unicode_literals, division

from collections import OrderedDict

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_charts as X
from ckanext.theme_ejemplo.ihpix_stats import UNSPECIFIED, natural_key

identity = X.identity

SECTION_IDS = ('overview', 'dimension', 'geography', 'timeline', 'kpi_1', 'kpi_2',
               'kpi_34', 'kpi_5', 'kpi_6', 'kpi_8', 'produced_reached', 'institutions',
               'sources')
APPENDIX_IDS = ('sources',)

# Anchura del viewBox y recortes por salida. Las diapositivas usan un viewBox
# más estrecho que el navegador escala (~1,35×): así el texto crece sin
# parámetros de fuente distintos.
LAYOUTS = {
    'document': {'width': 680, 'max_rows': 15, 'column_height': 220, 'label_share': 0.42, 'compact': False},
    'slide': {'width': 520, 'max_rows': 8, 'column_height': 300, 'label_share': 0.38, 'compact': True},
}

SECTION_TITLES = OrderedDict([
    ('overview', 'Implementation overview'),
    ('dimension', 'Activities by scope'),
    ('geography', 'Where the activities take place'),
    ('timeline', 'Activities per biennium'),
    ('kpi_1', 'Knowledge and scientific products'),
    ('kpi_2', 'Knowledge exchange'),
    ('kpi_34', 'Training and education'),
    ('kpi_5', 'Awareness raising'),
    ('kpi_6', 'Transboundary water systems'),
    ('kpi_8', 'Stakeholder groups with strengthened capacity'),
    ('produced_reached', 'What was produced and who was reached'),
    ('institutions', 'Institutions with most activities'),
    ('sources', 'Appendix: source activities'),
])

KICKERS = {'kpi_1': 'KPI 1', 'kpi_2': 'KPI 2', 'kpi_34': 'KPI 3 and 4', 'kpi_5': 'KPI 5',
           'kpi_6': 'KPI 6', 'kpi_8': 'KPI 8'}

PA_SHORT = OrderedDict([('PA1', 'Scientific research'), ('PA2', 'Water education'),
                        ('PA3', 'Data-knowledge gap'), ('PA4', 'Water management'),
                        ('PA5', 'Water governance')])

DIMENSION_HEADERS = {'priority_area': 'Priority Area', 'output': 'Output',
                     'key_activity': 'Key Activity'}
DIMENSION_TITLES = {'priority_area': 'Activities by priority area',
                    'output': 'Activities by Output',
                    'key_activity': 'Activities by key activity'}

COUNTRY_COLUMNS = ('Country', 'Region', 'Activities', 'Reporting', 'Supporter', 'Beneficiary')
UNRESOLVED_MARK = ' *'


def section_choices(translate=identity):
    u"""[(id, título)] para los checkboxes del formulario (sin el anexo)."""
    return [(sid, translate(SECTION_TITLES[sid])) for sid in SECTION_IDS if sid not in APPENDIX_IDS]


def selected_ids(requested):
    u"""Normaliza la selección: None → todas; lista → sólo ids conocidos en
    el orden canónico; una selección sin ids válidos equivale a todas."""
    if requested is None:
        return list(SECTION_IDS)
    wanted = set(requested)
    return [sid for sid in SECTION_IDS if sid in wanted] or list(SECTION_IDS)


# ─── Utilidades ──────────────────────────────────────────────────────────

def _t(translate, text):
    return translate(text) if text else text


def clip(text, limit=90):
    u"""Recorta etiquetas largas (los títulos de Output llegan a 300
    caracteres) conservando el código inicial; también lo usan las
    diapositivas para que las filas quepan en 16:9."""
    text = '{}'.format(text or '')
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '\u2026'


_clip = clip


def _fill(text, **values):
    u"""Sustituye marcadores '{clave}' sin exigir que estén todos presentes."""
    for key, value in values.items():
        text = text.replace('{' + key + '}', '{}'.format(value))
    return text


def dimension_label(key, dimension, translate=identity):
    u"""Etiqueta traducida de una clave de dimensión ('PA1 – …', '1.3 – …')."""
    if key == UNSPECIFIED or not key:
        return translate('Unspecified')
    if dimension == 'priority_area':
        title = C.PRIORITY_AREAS.get(key, '')
        return '{} {} {}'.format(key, X.DASH, translate(title)) if title else key
    if dimension == 'output':
        title = C.output_title(key)
        return '{} {} {}'.format(key, X.DASH, title) if title else key
    title = C.key_activity_title(key)
    return '{} {} {}'.format(key, X.DASH, title) if title else key


def _dimension_color(key, dimension, index):
    if key == UNSPECIFIED or not key:
        return X.NEUTRAL
    if dimension == 'priority_area':
        return X.color_for(key, index)
    if dimension == 'output':
        return X.color_for(key, index, pa=C.priority_area_for_output(key))
    return X.ACTION


def short_label(key, dimension, translate=identity):
    u"""Etiqueta corta para leyendas estrechas (diapositivas): sólo las PA
    tienen forma corta; el resto repite la etiqueta completa."""
    if dimension == 'priority_area' and key in PA_SHORT:
        return '{} {} {}'.format(key, X.DASH, translate(PA_SHORT[key]))
    return dimension_label(key, dimension, translate)


def _dimension_rows(items, dimension, measure, translate):
    rows = []
    for index, item in enumerate(items or []):
        key = item.get('key') or UNSPECIFIED
        rows.append({'key': key, 'label': dimension_label(key, dimension, translate),
                     'short_label': short_label(key, dimension, translate),
                     'value': item.get(measure) or 0,
                     'color': _dimension_color(key, dimension, index)})
    return rows


def _dimension_spec(fid, title, items, dimension, measure, translate, value_label):
    return {'kind': 'bar', 'id': fid, 'title': title,
            'label_header': translate(DIMENSION_HEADERS[dimension]),
            'value_label': value_label,
            'rows': _dimension_rows(items, dimension, measure, translate)}


def _stacked_spec(fid, title, items, dimension, series, translate):
    u"""`items`: lista de dicts {key, <medida>…}; `series`: [(medida, etiqueta)]."""
    rows = []
    for item in items or []:
        key = item.get('key') or UNSPECIFIED
        rows.append({'key': key, 'label': dimension_label(key, dimension, translate),
                     'short_label': short_label(key, dimension, translate),
                     'values': dict((measure, item.get(measure) or 0) for measure, _ in series)})
    return {'kind': 'stacked_bar', 'id': fid, 'title': title,
            'label_header': translate(DIMENSION_HEADERS[dimension]),
            'series': [{'key': measure, 'label': translate(label),
                        'color': X.MEASURE_COLORS.get(measure, X.CATEGORICAL[index])}
                       for index, (measure, label) in enumerate(series)],
            'rows': rows}


def _type_spec(fid, title, items, value_key, translate, value_label):
    rows = []
    for item in items or []:
        key = item.get('key') or ''
        rows.append({'key': key, 'label': translate(key) if key else translate('Unspecified'),
                     'value': item.get(value_key) or 0, 'color': X.ACTION if key != 'Other' else X.NEUTRAL,
                     'note': _fill(translate('Activities: {n}'), n=item.get('activities') or 0)})
    return {'kind': 'bar', 'id': fid, 'title': title, 'label_header': translate('Type'),
            'value_label': value_label, 'note_label': translate('Activities'), 'rows': rows}


def _merge_by_key(lists):
    u"""Fusiona varias listas `by_dimension` por `key` conservando el orden."""
    merged = OrderedDict()
    for items in lists:
        for item in items or []:
            bucket = merged.setdefault(item.get('key') or UNSPECIFIED, {'key': item.get('key') or UNSPECIFIED})
            bucket.update((k, v) for k, v in item.items() if k not in ('key', 'label'))
    return list(merged.values())


def _figure(spec, in_slides=True, top_rows=None):
    return {'id': spec['id'], 'title': spec['title'], 'spec': spec, 'svg': None, 'table': None,
            'in_slides': in_slides, 'top_rows': top_rows or []}


def _top_rows(rows, formatter=None, limit=4):
    return [[r['label'], r['value']] for r in rows[:limit]]


def _pct_text(value, translate):
    return X._n(round(value, 1)) if value is not None else translate('No data')


def _countries_table(countries, translate):
    rows = []
    unresolved = False
    for item in countries or []:
        name = item.get('country') or ''
        if not item.get('resolved', True):
            name += UNRESOLVED_MARK
            unresolved = True
        rows.append([name, _t(translate, item.get('region') or ''), item.get('activities') or 0,
                     item.get('as_reporting') or 0, item.get('as_supporter') or 0,
                     item.get('as_beneficiary') or 0])
    return {'columns': [translate(c) for c in COUNTRY_COLUMNS], 'rows': rows,
            'numeric': [2, 3, 4, 5], 'unresolved': unresolved}


def _section(sid, ctx, title=None, **fields):
    section = {'id': sid, 'kicker': _t(ctx['translate'], KICKERS.get(sid, '')),
               'title': title or ctx['translate'](SECTION_TITLES[sid]),
               'summary': [], 'tiles': [], 'highlights': [], 'figures': [], 'table': None,
               'notes': [], 'empty': ctx['empty'], 'appendix': sid in APPENDIX_IDS}
    section.update(fields)
    return section


# ─── Constructores ───────────────────────────────────────────────────────

def _overview(ctx):
    s, _, fmt = ctx['stats'], ctx['translate'], ctx['fmt']
    ov = s['overview']
    outputs_active = len([o for o in ov.get('by_output') or [] if o.get('count')])
    tiles = [{'label': _('Published activities'), 'value': fmt(ov['activities'])},
             {'label': _('Member States impacted'), 'value': fmt(ov['member_states_impacted'])},
             {'label': _('Institutions'), 'value': fmt(ov['institutions'])},
             {'label': _('Outputs with reported activity'), 'value': fmt(outputs_active)}]
    summary = [_fill(_('Published activities in the selected scope: {n}. Participating institutions: '
                       '{institutions}. Member States recorded in reporting, support or beneficiary '
                       'roles: {countries}.'),
                     n=fmt(ov['activities']), institutions=fmt(ov['institutions']),
                     countries=fmt(ov['member_states_impacted']))]
    highlights = [[_('Published activities'), ov['activities']],
                  [_('Institutions'), ov['institutions']],
                  [_('Countries across reporting, supporter and beneficiary roles'),
                   ov['member_states_impacted']]]
    return _section('overview', ctx, tiles=tiles, summary=summary, highlights=highlights,
                    notes=[_('An activity counts once in the overall total and in each linked scope. '
                             'Subtotals may overlap.')])


def _dimension(ctx):
    s, _, dimension = ctx['stats'], ctx['translate'], ctx['dimension']
    ov = s['overview']
    items = ov.get('by_dimension') or []
    title = _(DIMENSION_TITLES[dimension])
    rows = _dimension_rows(items, dimension, 'count', _)
    figures = []
    if dimension == 'priority_area' and 3 <= len([r for r in rows if r['value']]) <= 8:
        spec = {'kind': 'donut', 'id': 'dimension', 'title': title,
                'label_header': _(DIMENSION_HEADERS[dimension]), 'value_label': _('Activities'),
                'center_label': _('Activities'),
                'slices': [{'key': r['key'], 'label': r['label'], 'short_label': r['short_label'],
                            'value': r['value'], 'color': r['color']} for r in rows]}
    else:
        spec = _dimension_spec('dimension', title, items, dimension, 'count', _, _('Activities'))
    figures.append(_figure(spec, top_rows=_top_rows(rows)))
    if ctx['scope'] in ('overall', 'flagship', 'ctwg'):
        outputs = [o for o in ov.get('by_output') or [] if o.get('count')]
        out_rows = [{'key': o['key'], 'label': dimension_label(o['key'], 'output', _),
                     'value': o['count'], 'color': X.color_for(o['key'], index, pa=o.get('pa'))}
                    for index, o in enumerate(outputs)]
        figures.append(_figure({'kind': 'bar', 'id': 'outputs', 'title': _('Activities per Output'),
                                'label_header': _('Output'), 'value_label': _('Activities'),
                                'rows': out_rows,
                                'legend': [{'label': '{} {} {}'.format(pa, X.DASH, _(short)),
                                            'color': C.PA_COLORS[pa]} for pa, short in PA_SHORT.items()]},
                               top_rows=_top_rows(out_rows)))
    summary = []
    if rows:
        top = max(rows, key=lambda r: r['value'])
        summary.append(_fill(_('Largest share: {label} ({n}).'), label=top['label'], n=ctx['fmt'](top['value'])))
    return _section('dimension', ctx, title=title, figures=figures, summary=summary,
                    highlights=_top_rows(rows))


def _geography(ctx):
    s, _, fmt = ctx['stats'], ctx['translate'], ctx['fmt']
    ov = s['overview']
    rows = [{'key': r['key'], 'label': _(r['key']), 'value': r.get('activities') or 0, 'color': X.ACTION,
             'note': _fill(_('Member States: {n}'), n=r.get('member_states') or 0)}
            for r in ov.get('by_region') or []]
    spec = {'kind': 'bar', 'id': 'regions', 'title': _('Activities per region'),
            'label_header': _('Region'), 'value_label': _('Activities'),
            'note_label': _('Member States'), 'rows': rows}
    table = _countries_table(ov.get('countries') or [], _)
    notes = [_('A country counts in every role it holds: reporting institution, supporting Member State '
               'or beneficiary. Totals describe whole activities, not results allocated per country.')]
    if table.pop('unresolved', False):
        notes.append(_('* Not matched to a UNESCO Member State record.'))
    summary = [_fill(_('Member States impacted: {n}, across {regions} regions.'),
                     n=fmt(ov['member_states_impacted']), regions=fmt(len(rows)))]
    return _section('geography', ctx, figures=[_figure(spec, top_rows=_top_rows(rows))],
                    table=table, summary=summary, notes=notes, highlights=_top_rows(rows))


def _timeline(ctx):
    s, _, fmt = ctx['stats'], ctx['translate'], ctx['fmt']
    ov = s['overview']
    counts = dict((b['key'], b['count']) for b in ov.get('by_biennium') or [])
    columns = [{'key': b, 'label': b, 'value': counts.get(b, 0), 'color': X.ACTION} for b in C.BIENNIA]
    spec = {'kind': 'column', 'id': 'biennium', 'title': _('Activities per biennium'),
            'label_header': _('Biennium'), 'value_label': _('Activities'), 'columns': columns}
    table = None
    matrix = ov.get('output_biennium_matrix')
    if matrix and matrix.get('rows'):
        bienniums = matrix.get('bienniums') or []
        table = {'columns': [_('Output')] + list(bienniums) + [_('Total')],
                 'rows': [[_clip(dimension_label(r['output'], 'output', _))]
                          + [r['by_biennium'].get(b, 0) for b in bienniums] + [r['total']]
                          for r in matrix['rows'] if r.get('total')],
                 'numeric': list(range(1, len(bienniums) + 2))}
    without = ov['activities'] - sum(counts.values())
    summary = [_fill(_('Activities with a reported biennium: {n}.'), n=fmt(sum(counts.values())))]
    notes = []
    if without > 0:
        notes.append(_fill(_('Activities without a biennium: {n}.'), n=fmt(without)))
    return _section('timeline', ctx, figures=[_figure(spec, top_rows=[[c['label'], c['value']] for c in columns])],
                    table=table, summary=summary, notes=notes,
                    highlights=[[c['label'], c['value']] for c in columns])


def _kpi_1(ctx):
    s, _, fmt, dimension = ctx['stats'], ctx['translate'], ctx['fmt'], ctx['dimension']
    k = s['kpi_1']
    tiles = [{'label': _('Knowledge products'), 'value': fmt(k['knowledge_products'])},
             {'label': _('Scientific products'), 'value': fmt(k['scientific_products'])},
             {'label': _('Activities reported'), 'value': fmt(k['active_activities'])}]
    figures = [_figure(_stacked_spec('kpi1-dimension', _('Products per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), k.get('by_dimension'), dimension,
        [('knowledge', 'Knowledge products'), ('scientific', 'Scientific products')], _),
        top_rows=[[dimension_label(i['key'], dimension, _), (i.get('knowledge') or 0) + (i.get('scientific') or 0)]
                  for i in (k.get('by_dimension') or [])[:4]])]
    figures.append(_figure(_type_spec('kpi1-knowledge-type', _('Knowledge products by type'),
                                      k.get('knowledge_by_type'), 'products', _, _('Products')), in_slides=False))
    figures.append(_figure(_type_spec('kpi1-scientific-type', _('Scientific products by type'),
                                      k.get('scientific_by_type'), 'products', _, _('Products')), in_slides=False))
    summary = [_fill(_('Knowledge products: {k}. Scientific products: {s}. Contributing activities: {a}.'),
                     k=fmt(k['knowledge_products']), s=fmt(k['scientific_products']), a=fmt(k['active_activities']))]
    highlights = [[_('Knowledge products'), k['knowledge_products']],
                  [_('Scientific products'), k['scientific_products']],
                  [_('Activities reported'), k['active_activities']]]
    return _section('kpi_1', ctx, tiles=tiles, figures=figures, summary=summary, highlights=highlights,
                    notes=[_('An activity with several product types adds its count under each type.')])


def _people(ctx, sid, key, fid, reached_label, type_items=None):
    s, _, fmt, dimension = ctx['stats'], ctx['translate'], ctx['fmt'], ctx['dimension']
    k = s[key]
    tiles = [{'label': _(reached_label), 'value': fmt(k['individuals'])},
             {'label': _('Youth (18–35)'), 'value': fmt(k['youth'])},
             {'label': _('Female participants'), 'value': fmt(k['female'])},
             {'label': _('Activities reported'), 'value': fmt(k['active_activities'])}]
    figures = [_figure(_dimension_spec(fid + '-dimension', _('Individuals per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), k.get('by_dimension'), dimension, 'individuals', _,
        _('Individuals')),
        top_rows=_top_rows(_dimension_rows(k.get('by_dimension'), dimension, 'individuals', _)))]
    if k.get('pct_youth') is not None or k.get('pct_female') is not None:
        rows = [{'key': 'youth', 'label': _('Youth (18–35)'), 'value': k.get('pct_youth') or 0, 'color': X.ACTION},
                {'key': 'female', 'label': _('Female participants'), 'value': k.get('pct_female') or 0, 'color': X.ACTION}]
        figures.append(_figure({'kind': 'bar', 'id': fid + '-shares', 'title': _('Youth and female participation (%)'),
                                'label_header': _('Group'), 'value_label': '%', 'max_value': 100, 'suffix': '%',
                                'rows': rows}, in_slides=False))
    if type_items is not None:
        figures.append(_figure(_type_spec(fid + '-type', _('Individuals by activity type'), type_items,
                                          'individuals', _, _('Individuals')), in_slides=False))
    summary = [_fill(_('{reached}: {n}. Youth: {youth}%. Female participants: {female}%. Contributing activities: {a}.'),
                     reached=_(reached_label), n=fmt(k['individuals']), youth=_pct_text(k.get('pct_youth'), _),
                     female=_pct_text(k.get('pct_female'), _), a=fmt(k['active_activities']))]
    highlights = [[_('Stakeholders'), k['individuals']], [_('Youth (18–35)'), k['youth']],
                  [_('Female participants'), k['female']],
                  [_('Youth / female (%)'), '{} / {}'.format(_pct_text(k.get('pct_youth'), _),
                                                              _pct_text(k.get('pct_female'), _))]]
    return _section(sid, ctx, tiles=tiles, figures=figures, summary=summary, highlights=highlights,
                    notes=[_('Youth and female participants may overlap.')])


def _kpi_2(ctx):
    return _people(ctx, 'kpi_2', 'kpi_2', 'kpi2', 'Stakeholders reached through knowledge exchange',
                   type_items=ctx['stats']['kpi_2'].get('by_activity_type') or [])


def _kpi_5(ctx):
    return _people(ctx, 'kpi_5', 'kpi_5', 'kpi5', 'Stakeholders reached through awareness activities')


def _kpi_34(ctx):
    s, _, fmt, dimension = ctx['stats'], ctx['translate'], ctx['fmt'], ctx['dimension']
    k3, k4 = s['kpi_3'], s['kpi_4']
    tiles = [{'label': _('Training materials and courses'), 'value': fmt(k3['materials'])},
             {'label': _('Curricula'), 'value': fmt(k4['curricula'])},
             {'label': _('Activities with training materials'), 'value': fmt(k3['active_activities'])},
             {'label': _('Activities with curricula'), 'value': fmt(k4['active_activities'])}]
    merged = _merge_by_key([k3.get('by_dimension'), k4.get('by_dimension')])
    figures = [_figure(_stacked_spec('kpi34-dimension', _('Materials and curricula per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), merged, dimension,
        [('materials', 'Training materials and courses'), ('curricula', 'Curricula')], _),
        top_rows=[[dimension_label(i['key'], dimension, _), (i.get('materials') or 0) + (i.get('curricula') or 0)]
                  for i in merged[:4]]),
               _figure(_type_spec('kpi3-type', _('Training materials by type'), k3.get('by_type'), 'materials', _,
                                  _('Materials')), in_slides=False)]
    summary = [_fill(_('Training materials and courses: {m}. Curricula: {c}.'),
                     m=fmt(k3['materials']), c=fmt(k4['curricula']))]
    highlights = [[_('Training materials and courses'), k3['materials']], [_('Curricula'), k4['curricula']],
                  [_('Activities with training materials'), k3['active_activities']],
                  [_('Activities with curricula'), k4['active_activities']]]
    return _section('kpi_34', ctx, tiles=tiles, figures=figures, summary=summary, highlights=highlights)


def _kpi_6(ctx):
    s, _, fmt, dimension = ctx['stats'], ctx['translate'], ctx['fmt'], ctx['dimension']
    k = s['kpi_6']
    tiles = [{'label': _('Member States supported, as reported'), 'value': fmt(k['member_states_reported'])},
             {'label': _('Distinct countries'), 'value': fmt(k['member_states_distinct'])},
             {'label': _('Activities reported'), 'value': fmt(k['active_activities'])}]
    rows = _dimension_rows(k.get('by_dimension'), dimension, 'member_states', _)
    figures = [_figure(_dimension_spec('kpi6-dimension', _('Member States supported per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), k.get('by_dimension'), dimension, 'member_states', _,
        _('Member States')), top_rows=_top_rows(rows))]
    table = _countries_table(k.get('countries') or [], _)
    notes = [_('Reported counts come from each activity; distinct countries are the union of the countries '
               'linked to those activities.')]
    if table.pop('unresolved', False):
        notes.append(_('* Not matched to a UNESCO Member State record.'))
    summary = [_fill(_('Member States supported in transboundary water management, as reported: {n}, '
                       'across {d} distinct countries and {a} activities.'),
                     n=fmt(k['member_states_reported']), d=fmt(k['member_states_distinct']),
                     a=fmt(k['active_activities']))]
    highlights = [[_('Activities reported'), k['active_activities']],
                  [_('Member States supported in transboundary water management, as reported'), k['member_states_reported']],
                  [_('Distinct countries'), k['member_states_distinct']]]
    return _section('kpi_6', ctx, tiles=tiles, figures=figures, table=table if table['rows'] else None,
                    summary=summary, highlights=highlights, notes=notes)


def _kpi_8(ctx):
    s, _, fmt, dimension = ctx['stats'], ctx['translate'], ctx['fmt'], ctx['dimension']
    k = s['kpi_8']
    tiles = [{'label': _('Stakeholder groups'), 'value': fmt(k['stakeholder_groups'])},
             {'label': _('Distinct countries'), 'value': fmt(k['member_states_distinct'])},
             {'label': _('Activities reported'), 'value': fmt(k['active_activities'])}]
    rows = _dimension_rows(k.get('by_dimension'), dimension, 'groups', _)
    figures = [_figure(_dimension_spec('kpi8-dimension', _('Stakeholder groups per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), k.get('by_dimension'), dimension, 'groups', _,
        _('Groups')), top_rows=_top_rows(rows)),
               _figure(_type_spec('kpi8-type', _('Stakeholder groups by type'), k.get('by_type'), 'groups', _,
                                  _('Groups')), in_slides=False)]
    summary = [_fill(_('Stakeholder groups with strengthened capacity: {n}, across {d} distinct countries.'),
                     n=fmt(k['stakeholder_groups']), d=fmt(k['member_states_distinct']))]
    highlights = [[_('Activities reported'), k['active_activities']],
                  [_('Stakeholder groups'), k['stakeholder_groups']],
                  [_('Distinct countries'), k['member_states_distinct']]]
    return _section('kpi_8', ctx, tiles=tiles, figures=figures, summary=summary, highlights=highlights)


def _produced_reached(ctx):
    s, _, dimension = ctx['stats'], ctx['translate'], ctx['dimension']
    produced = [('knowledge', 'Knowledge products'), ('scientific', 'Scientific products'),
                ('training', 'Training materials and courses'), ('curricula', 'Curricula')]
    reached = [('knowledge_improved', 'Stakeholders reached through knowledge exchange'),
               ('awareness_raised', 'Stakeholders reached through awareness activities')]
    totals = lambda items, measures: [[_(label), sum(i.get(m) or 0 for i in items or [])] for m, label in measures]
    figures = [_figure(_stacked_spec('produced', _('Products per {dimension}').replace(
        '{dimension}', _(DIMENSION_HEADERS[dimension])), s.get('produced_by_dimension'), dimension, produced, _),
        top_rows=totals(s.get('produced_by_dimension'), produced)),
               _figure(_stacked_spec('reached', _('Individuals reached per {dimension}').replace(
                   '{dimension}', _(DIMENSION_HEADERS[dimension])), s.get('reached_by_dimension'), dimension,
                   reached, _), top_rows=totals(s.get('reached_by_dimension'), reached))]
    return _section('produced_reached', ctx, figures=figures,
                    highlights=totals(s.get('produced_by_dimension'), produced),
                    notes=[_('Products and individuals are summed from the activity records linked to each scope.')])


def _institutions(ctx):
    s, _ = ctx['stats'], ctx['translate']
    rows = [{'key': i['name'], 'label': i['name'], 'value': i['count'], 'color': X.ACTION}
            for i in s['overview'].get('top_institutions') or []]
    spec = {'kind': 'bar', 'id': 'institutions', 'title': _('Institutions with most activities'),
            'label_header': _('Institution'), 'value_label': _('Activities'), 'rows': rows}
    return _section('institutions', ctx, figures=[_figure(spec, top_rows=_top_rows(rows))],
                    highlights=_top_rows(rows),
                    notes=[_('Institution names as reported; the same institution may appear under several spellings.')])


def group_sources(sources, scope, scope_value, translate=identity):
    u"""Agrupa las fuentes por PA → Output (el primero del ámbito) para el anexo.

    La clave de las actividades se llama `activities` (no `items`): en Jinja
    `out.items` resolvería al método del dict."""
    groups = OrderedDict()
    for item in sources or []:
        outputs = [o for o in (item.get('outputs') or []) if o]
        if scope == 'output' and scope_value:
            candidates = [scope_value]
        elif scope == 'pa' and scope_value:
            candidates = [o for o in outputs if C.priority_area_for_output(o) == scope_value] or outputs
        else:
            candidates = outputs
        first = candidates[0] if candidates else ''
        pa = C.priority_area_for_output(first) or item.get('priority_area') or UNSPECIFIED
        bucket = groups.setdefault(pa, OrderedDict())
        bucket.setdefault(first or UNSPECIFIED, []).append(item)
    result = []
    for pa in sorted(groups, key=lambda k: ((1,) if k == UNSPECIFIED else (0,)) + natural_key(k)):
        outputs = groups[pa]
        result.append({'pa': pa, 'title': dimension_label(pa, 'priority_area', translate),
                       'outputs': [{'code': code, 'label': dimension_label(code, 'output', translate),
                                    'activities': outputs[code]}
                                   for code in sorted(outputs, key=lambda k: ((1,) if k == UNSPECIFIED else (0,)) + natural_key(k))]})
    return result


def _sources(ctx, sources, detail):
    _ = ctx['translate']
    groups = group_sources(sources, ctx['scope'], ctx['scope_value'], _)
    return _section('sources', ctx, groups=groups, detail=bool(detail), count=len(sources or []),
                    summary=[_fill(_('Source activities listed: {n}.'), n=ctx['fmt'](len(sources or [])))],
                    notes=[_('Published records only. Open each activity to verify its figures.')])


BUILDERS = OrderedDict([
    ('overview', _overview), ('dimension', _dimension), ('geography', _geography),
    ('timeline', _timeline), ('kpi_1', _kpi_1), ('kpi_2', _kpi_2), ('kpi_34', _kpi_34),
    ('kpi_5', _kpi_5), ('kpi_6', _kpi_6), ('kpi_8', _kpi_8),
    ('produced_reached', _produced_reached), ('institutions', _institutions),
])


def build_sections(stats, translate=identity, options=None, sources=None):
    u"""Secciones ordenadas para una salida.

    `options`: {'sections': ids o None, 'layout': 'document'|'slide',
    'include_sources': bool, 'sources_detail': bool, 'format_number': callable}.
    El anexo sólo se construye con `include_sources` y `sources` no None.
    """
    options = dict(options or {})
    formatter = options.get('format_number')
    scope = stats.get('scope') or {}
    ctx = {
        'stats': stats,
        'translate': translate,
        'fmt': lambda value: X.format_number(value, formatter),
        'dimension': scope.get('dimension') or 'priority_area',
        'scope': scope.get('kind') or 'overall',
        'scope_value': scope.get('value') or '',
        'empty': not (stats.get('overview') or {}).get('activities'),
    }
    wanted = selected_ids(options.get('sections'))
    sections = []
    for sid in SECTION_IDS:
        if sid not in wanted:
            continue
        if sid in APPENDIX_IDS:
            if options.get('include_sources') and sources is not None:
                sections.append(_sources(ctx, sources, options.get('sources_detail')))
            continue
        section = BUILDERS[sid](ctx)
        if section is not None:
            sections.append(section)
    return sections


def render_figures(sections, layout='document', translate=identity, formatter=None):
    u"""Rellena `svg` y `table` de cada figura según la salida (in place)."""
    params = LAYOUTS.get(layout) or LAYOUTS['document']
    for section in sections:
        for fig in section.get('figures') or []:
            spec = dict(fig['spec'])
            spec.setdefault('max_rows', params['max_rows'])
            spec.setdefault('label_share', params['label_share'])
            spec.setdefault('compact', params['compact'])
            height = params['column_height'] if spec.get('kind') == 'column' else None
            fig['svg'] = X.render(spec, params['width'], height, translate, formatter)
            fig['table'] = X.table_for(spec, translate, formatter)
    return sections
