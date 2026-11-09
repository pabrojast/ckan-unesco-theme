# -*- coding: utf-8 -*-
u"""Gráficos SVG puros para informes y diapositivas IHP-IX (sin CKAN ni JS).

Cada función recibe una *spec* (dict) ya traducida y devuelve un documento
SVG determinista (sin ids aleatorios, sin dependencias de navegador) que se
inserta con `|safe` en `templates/ihpix/narrative.html` y
`templates/ihpix/presentation.html`. La misma spec alimenta `table_for`, la
tabla accesible equivalente: una única fuente de verdad para cifras y texto.

Reglas de dibujo (guía dataviz del proyecto, DOC-033):
- barras ≤ 24 px, extremo de datos redondeado 4 px y base cuadrada;
- sin gridlines: cada barra lleva su valor directo en tinta (`INK`);
- segmentos apilados separados por un hueco de 2 px en color de superficie;
- el texto nunca usa el color de la serie; leyenda siempre con ≥ 2 series;
- `<title>`/`<desc>` enumeran los valores para lectores de pantalla y PDF.

`translate` sólo cubre los literales propios de este módulo ('{n} more in
the table', 'No data'); las etiquetas de la spec llegan ya traducidas desde
`ihpix_report_sections`. Las anchuras de texto se aproximan (Arial ≈ 0,55 em
por carácter): no hay medición real en servidor, por eso las etiquetas
largas se recortan con '…' y conservan el texto completo en `<title>`.
"""
from __future__ import unicode_literals, division

import math
import re
from collections import OrderedDict
from xml.sax.saxutils import escape as _xml_escape

from ckanext.theme_ejemplo import ihpix_constants as C

INK = '#0B2A4A'
INK_2 = '#5B6B7F'
ACTION = '#0069B4'
DEEP = '#004E8C'
PAPER = '#F4F8FC'
RULE = '#D5E0EC'
RULE_SOFT = '#E6EEF6'
SURFACE = '#FFFFFF'
NEUTRAL = '#94A3B8'

# Mismo orden fijo que `templates/ihpix/progress.html` (nunca cíclico: a
# partir del 9º valor se usa NEUTRAL o se pliega en "Other").
CATEGORICAL = ['#0069B4', '#D97706', '#7C3AED', '#059669', '#DC2626',
               '#0891B2', '#DB2777', '#4D7C0F']

# Series de medida (eje = dimensión). Comparten tonos con PA1-4, pero nunca
# conviven con la paleta PA en la misma figura y siempre llevan leyenda.
MEASURE_COLORS = OrderedDict([
    ('knowledge', '#0069B4'), ('scientific', '#D97706'),
    ('training', '#7C3AED'), ('curricula', '#059669'),
    ('knowledge_improved', '#0069B4'), ('awareness_raised', '#D97706'),
])

NEUTRAL_KEYS = ('Unspecified', 'Other', '')

FONT = 'Arial, Helvetica, sans-serif'
FONT_SIZE = 13
VALUE_SIZE = 12
SMALL_SIZE = 11.5
BAR_THICKNESS = 22
ROW_HEIGHT = 30
GAP = 2
CORNER = 4
TOP = 8
BOTTOM = 8
CHAR_WIDTH = 0.55  # fracción del tamaño de fuente por carácter (Arial)

DASH = '–'
_ID_RE = re.compile(r'[^A-Za-z0-9_-]+')


def identity(text):
    return text


def escape(text):
    u"""Escapa texto para atributos y contenido XML (incluye comillas)."""
    if text is None:
        return ''
    return _xml_escape('{}'.format(text), {'"': '&quot;', "'": '&#39;'})


def _num(value):
    if value is None or value == '':
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def format_number(value, formatter=None):
    u"""Texto de un número: formateador inyectado (p. ej. localised_number) o
    separador de miles por defecto; None/'' → '–'."""
    if value is None or value == '':
        return DASH
    if formatter is not None:
        try:
            return '{}'.format(formatter(value))
        except Exception:  # un formateador roto nunca tumba el informe
            pass
    if isinstance(value, float) and value != int(value):
        return '{:,.1f}'.format(value)
    try:
        return '{:,}'.format(int(value))
    except (TypeError, ValueError):
        return '{}'.format(value)


def text_width(text, size=FONT_SIZE):
    u"""Anchura aproximada en px de `text` a `size` px (Arial)."""
    return len('{}'.format(text or '')) * size * CHAR_WIDTH


def ellipsis(text, max_px, size=FONT_SIZE):
    u"""Recorta con '…' para que quepa en `max_px` (aproximado)."""
    text = '{}'.format(text or '')
    if text_width(text, size) <= max_px:
        return text
    keep = int(max_px / (size * CHAR_WIDTH)) - 1
    if keep < 1:
        return '…'
    return text[:keep].rstrip() + '…'


def color_for(key, index=0, pa=None):
    u"""Color de una categoría: PA propia → PA madre → neutro para
    Unspecified/Other → paleta categórica en orden fijo (≥ 8 → neutro)."""
    if key in C.PA_COLORS:
        return C.PA_COLORS[key]
    if pa in C.PA_COLORS:
        return C.PA_COLORS[pa]
    if key in NEUTRAL_KEYS:
        return NEUTRAL
    if 0 <= index < len(CATEGORICAL):
        return CATEGORICAL[index]
    return NEUTRAL


def _label(item, spec):
    u"""Etiqueta a dibujar: la corta si la spec es `compact` y existe."""
    if spec.get('compact') and item.get('short_label'):
        return '{}'.format(item['short_label'])
    return '{}'.format(item.get('label') or item.get('key') or '')


def _n(value):
    u"""Número compacto para atributos SVG ('12', '12.5')."""
    text = '{:.1f}'.format(float(value))
    return text.rstrip('0').rstrip('.') if '.' in text else text


def _text(x, y, content, size=FONT_SIZE, fill=INK, anchor='start', weight=None, title=None):
    attrs = 'x="{}" y="{}" dy="0.35em" font-size="{}" fill="{}" text-anchor="{}"'.format(
        _n(x), _n(y), _n(size), fill, anchor)
    if weight:
        attrs += ' font-weight="{}"'.format(weight)
    inner = escape(content)
    if title:
        inner = '<title>{}</title>'.format(escape(title)) + inner
    return '<text {}>{}</text>'.format(attrs, inner)


def _bar(x, y, w, h, color, rounded=True):
    u"""Barra horizontal: base cuadrada a la izquierda, extremo redondeado."""
    if w <= 0:
        return ''
    r = min(CORNER, w, h / 2.0) if rounded else 0
    if r <= 0:
        return '<rect x="{}" y="{}" width="{}" height="{}" fill="{}"/>'.format(
            _n(x), _n(y), _n(w), _n(h), color)
    return ('<path d="M{x},{y} h{w1} a{r},{r} 0 0 1 {r},{r} v{h2} a{r},{r} 0 0 1 -{r},{r} '
            'h-{w1} z" fill="{c}"/>').format(x=_n(x), y=_n(y), w1=_n(w - r), r=_n(r),
                                             h2=_n(h - 2 * r), c=color)


def _column(x, y_base, w, h, color):
    u"""Columna vertical: base cuadrada, tapa redondeada."""
    if h <= 0:
        return ''
    r = min(CORNER, h, w / 2.0)
    return ('<path d="M{x},{yb} v-{h1} a{r},{r} 0 0 1 {r},-{r} h{w2} a{r},{r} 0 0 1 {r},{r} '
            'v{h1} z" fill="{c}"/>').format(x=_n(x), yb=_n(y_base), h1=_n(h - r), r=_n(r),
                                            w2=_n(w - 2 * r), c=color)


def _legend(items, width, y):
    u"""Leyenda horizontal con salto de línea; devuelve (svg, alto)."""
    if not items:
        return '', 0
    parts = []
    x = 0
    line = 0
    for item in items:
        label = '{}'.format(item.get('label') or '')
        item_w = 14 + 6 + text_width(label, VALUE_SIZE) + 18
        if x > 0 and x + item_w > width:
            x = 0
            line += 1
        cy = y + line * 20 + 10
        parts.append('<rect x="{}" y="{}" width="12" height="12" rx="2" fill="{}"/>'.format(
            _n(x), _n(cy - 6), item.get('color') or NEUTRAL))
        parts.append(_text(x + 18, cy, label, size=VALUE_SIZE, fill=INK_2))
        x += item_w
    return ''.join(parts), (line + 1) * 20 + 6


def svg_document(width, height, title, desc, body, figure_id):
    u"""Envoltorio SVG accesible: viewBox fijo, `role="img"`, title + desc."""
    fid = _ID_RE.sub('-', '{}'.format(figure_id or 'chart')).strip('-') or 'chart'
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" '
            'role="img" aria-labelledby="ixc-{id}-t ixc-{id}-d" class="ixc" '
            'style="direction:ltr;font-family:{font};max-width:100%;height:auto;display:block">'
            '<title id="ixc-{id}-t">{title}</title><desc id="ixc-{id}-d">{desc}</desc>'
            '{body}</svg>').format(w=_n(width), h=_n(height), id=fid, font=escape(FONT),
                                   title=escape(title), desc=escape(desc), body=body)


def empty_chart(width, height, message, title, figure_id):
    body = ('<rect x="0" y="0" width="{w}" height="{h}" rx="6" fill="{bg}"/>'.format(
        w=_n(width), h=_n(height), bg=PAPER)
        + _text(width / 2.0, height / 2.0, message, fill=INK_2, anchor='middle'))
    return svg_document(width, height, title, message, body, figure_id)


def _desc(title, pairs):
    return '{}. {}'.format(title, '; '.join('{}: {}'.format(label, value) for label, value in pairs))


def _overflow_note(hidden, width, y, translate):
    if not hidden:
        return '', 0
    note = translate('{n} more in the table').replace('{n}', '{}'.format(hidden))
    return _text(0, y + 8, note, size=SMALL_SIZE, fill=INK_2), 20


# ─── Barras horizontales ─────────────────────────────────────────────────

def bar_chart(spec, width, height=None, translate=identity, formatter=None):
    title = spec.get('title') or ''
    fid = spec.get('id') or 'bar'
    rows = list(spec.get('rows') or [])
    hidden = 0
    max_rows = spec.get('max_rows')
    if max_rows and len(rows) > max_rows:
        hidden = len(rows) - max_rows
        rows = rows[:max_rows]
    values = [_num(r.get('value')) for r in rows]
    max_value = _num(spec.get('max_value')) or (max(values) if values else 0)
    if not rows or max_value <= 0:
        return empty_chart(width, height or 120, translate('No data'), title, fid)
    suffix = spec.get('suffix') or ''
    label_w = int(width * (spec.get('label_share') or 0.42))
    x0 = label_w + 10
    value_texts = [format_number(r.get('value'), formatter) + suffix for r in rows]
    notes = ['{}'.format(r.get('note') or '') for r in rows]
    tip_w = max(text_width(v, VALUE_SIZE) + (text_width(n, SMALL_SIZE) + 6 if n else 0)
                for v, n in zip(value_texts, notes)) + 12
    plot_w = max(40, width - x0 - tip_w)
    body_h = TOP + len(rows) * ROW_HEIGHT + BOTTOM
    legend_svg, legend_h = _legend(spec.get('legend') or [], width, body_h)
    note_svg, note_h = _overflow_note(hidden, width, body_h + legend_h, translate)
    total_h = body_h + legend_h + note_h
    parts = ['<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{c}" stroke-width="1"/>'.format(
        x=_n(x0), y1=_n(TOP), y2=_n(TOP + len(rows) * ROW_HEIGHT), c=RULE)]
    pairs = []
    for i, row in enumerate(rows):
        full = '{}'.format(row.get('label') or row.get('key') or '')
        y = TOP + i * ROW_HEIGHT + (ROW_HEIGHT - BAR_THICKNESS) / 2.0
        cy = y + BAR_THICKNESS / 2.0
        w = plot_w * values[i] / max_value
        color = row.get('color') or ACTION
        label = ellipsis(_label(row, spec), label_w - 6, FONT_SIZE)
        pairs.append((full, value_texts[i] + (' ({})'.format(notes[i]) if notes[i] else '')))
        g = ['<g><title>{}</title>'.format(escape('{}: {}'.format(full, pairs[-1][1])))]
        g.append(_text(label_w, cy, label, anchor='end'))
        g.append(_bar(x0, y, w, BAR_THICKNESS, color))
        tip_x = x0 + w + 6
        g.append(_text(tip_x, cy, value_texts[i], size=VALUE_SIZE))
        if notes[i]:
            g.append(_text(tip_x + text_width(value_texts[i], VALUE_SIZE) + 6, cy, notes[i],
                           size=SMALL_SIZE, fill=INK_2))
        g.append('</g>')
        parts.append(''.join(g))
    parts.append(legend_svg)
    parts.append(note_svg)
    return svg_document(width, total_h, title, _desc(title, pairs), ''.join(parts), fid)


# ─── Barras apiladas ─────────────────────────────────────────────────────

def stacked_bar_chart(spec, width, height=None, translate=identity, formatter=None):
    title = spec.get('title') or ''
    fid = spec.get('id') or 'stacked'
    series = list(spec.get('series') or [])
    rows = list(spec.get('rows') or [])
    hidden = 0
    max_rows = spec.get('max_rows')
    if max_rows and len(rows) > max_rows:
        hidden = len(rows) - max_rows
        rows = rows[:max_rows]
    totals = [sum(_num((r.get('values') or {}).get(s['key'])) for s in series) for r in rows]
    max_total = max(totals) if totals else 0
    if not rows or not series or max_total <= 0:
        return empty_chart(width, height or 120, translate('No data'), title, fid)
    label_w = int(width * (spec.get('label_share') or 0.42))
    x0 = label_w + 10
    total_texts = [format_number(t if t == int(t) else round(t, 1), formatter) for t in totals]
    tip_w = max(text_width(t, VALUE_SIZE) for t in total_texts) + 12
    plot_w = max(40, width - x0 - tip_w)
    body_h = TOP + len(rows) * ROW_HEIGHT + BOTTOM
    legend_svg, legend_h = _legend([{'label': s.get('label') or s['key'], 'color': s.get('color') or NEUTRAL}
                                    for s in series], width, body_h)
    note_svg, note_h = _overflow_note(hidden, width, body_h + legend_h, translate)
    total_h = body_h + legend_h + note_h
    parts = ['<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" stroke="{c}" stroke-width="1"/>'.format(
        x=_n(x0), y1=_n(TOP), y2=_n(TOP + len(rows) * ROW_HEIGHT), c=RULE)]
    pairs = []
    for i, row in enumerate(rows):
        full = '{}'.format(row.get('label') or row.get('key') or '')
        y = TOP + i * ROW_HEIGHT + (ROW_HEIGHT - BAR_THICKNESS) / 2.0
        cy = y + BAR_THICKNESS / 2.0
        values = row.get('values') or {}
        detail = ', '.join('{} {}'.format(s.get('label') or s['key'], format_number(values.get(s['key']) or 0, formatter))
                           for s in series)
        pairs.append((full, '{} ({})'.format(total_texts[i], detail)))
        g = ['<g><title>{}</title>'.format(escape('{}: {}'.format(full, pairs[-1][1])))]
        g.append(_text(label_w, cy, ellipsis(_label(row, spec), label_w - 6, FONT_SIZE), anchor='end'))
        segments = [(s, _num(values.get(s['key']))) for s in series]
        segments = [(s, v) for s, v in segments if v > 0]
        cursor = x0
        for index, (s, v) in enumerate(segments):
            seg_w = plot_w * v / max_total
            last = index == len(segments) - 1
            draw_w = seg_w - (0 if last else GAP)
            g.append(_bar(cursor, y, draw_w, BAR_THICKNESS, s.get('color') or NEUTRAL, rounded=last))
            text = format_number(v if v != int(v) else int(v), formatter)
            if text_width(text, SMALL_SIZE) + 12 <= draw_w:
                g.append(_text(cursor + draw_w / 2.0, cy, text, size=SMALL_SIZE, fill=SURFACE, anchor='middle'))
            cursor += seg_w
        g.append(_text(x0 + plot_w * totals[i] / max_total + 6, cy, total_texts[i], size=VALUE_SIZE))
        g.append('</g>')
        parts.append(''.join(g))
    parts.append(legend_svg)
    parts.append(note_svg)
    return svg_document(width, total_h, title, _desc(title, pairs), ''.join(parts), fid)


# ─── Donut ───────────────────────────────────────────────────────────────

def donut_chart(spec, width, height=None, translate=identity, formatter=None):
    title = spec.get('title') or ''
    fid = spec.get('id') or 'donut'
    slices = [s for s in (spec.get('slices') or []) if _num(s.get('value')) > 0]
    total = sum(_num(s.get('value')) for s in slices)
    if not slices or total <= 0:
        return empty_chart(width, height or 160, translate('No data'), title, fid)
    radius = 88
    stroke = 30
    legend_x = 2 * (radius + stroke / 2.0) + 36
    legend_w = max(120, width - legend_x)
    row_h = 24
    legend_h = len(slices) * row_h
    total_h = height or max(2 * (radius + stroke / 2.0) + 24, legend_h + 24)
    cx = radius + stroke / 2.0 + 8
    cy = total_h / 2.0
    parts = []
    pairs = []
    angle = -math.pi / 2.0
    boundaries = []
    for s in slices:
        value = _num(s.get('value'))
        share = value / total
        a0 = angle
        a1 = angle + 2 * math.pi * share
        color = s.get('color') or NEUTRAL
        if len(slices) == 1:
            parts.append('<circle cx="{}" cy="{}" r="{}" fill="none" stroke="{}" stroke-width="{}"/>'.format(
                _n(cx), _n(cy), _n(radius), color, _n(stroke)))
        else:
            x0, y0 = cx + radius * math.cos(a0), cy + radius * math.sin(a0)
            x1, y1 = cx + radius * math.cos(a1), cy + radius * math.sin(a1)
            large = 1 if (a1 - a0) > math.pi else 0
            parts.append('<path d="M{} {} A{} {} 0 {} 1 {} {}" fill="none" stroke="{}" stroke-width="{}"/>'.format(
                _n(x0), _n(y0), _n(radius), _n(radius), large, _n(x1), _n(y1), color, _n(stroke)))
            boundaries.append(a0)
        pairs.append(('{}'.format(s.get('label') or s.get('key') or ''),
                      '{} ({}%)'.format(format_number(s.get('value'), formatter), _n(round(100.0 * share, 1)))))
        angle = a1
    inner = radius - stroke / 2.0 - 1
    outer = radius + stroke / 2.0 + 1
    for a in boundaries:
        parts.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="{}"/>'.format(
            _n(cx + inner * math.cos(a)), _n(cy + inner * math.sin(a)),
            _n(cx + outer * math.cos(a)), _n(cy + outer * math.sin(a)), SURFACE, GAP))
    parts.append(_text(cx, cy - 6, format_number(total if total != int(total) else int(total), formatter),
                       size=28, anchor='middle', weight='700'))
    if spec.get('center_label'):
        parts.append(_text(cx, cy + 16, spec['center_label'], size=VALUE_SIZE, fill=INK_2, anchor='middle'))
    ly = (total_h - legend_h) / 2.0 + row_h / 2.0
    for s, (label, value_text) in zip(slices, pairs):
        value_w = text_width(value_text, VALUE_SIZE)
        parts.append('<g><title>{}</title>'.format(escape('{}: {}'.format(label, value_text))))
        parts.append('<rect x="{}" y="{}" width="12" height="12" rx="2" fill="{}"/>'.format(
            _n(legend_x), _n(ly - 6), s.get('color') or NEUTRAL))
        parts.append(_text(legend_x + 18, ly, ellipsis(_label(s, spec), legend_w - 18 - value_w - 12, FONT_SIZE)))
        parts.append(_text(width - 2, ly, value_text, size=VALUE_SIZE, anchor='end'))
        parts.append('</g>')
        ly += row_h
    return svg_document(width, total_h, title, _desc(title, pairs), ''.join(parts), fid)


# ─── Columnas (serie temporal corta) ─────────────────────────────────────

def column_chart(spec, width, height=None, translate=identity, formatter=None):
    title = spec.get('title') or ''
    fid = spec.get('id') or 'column'
    columns = list(spec.get('columns') or [])
    values = [_num(c.get('value')) for c in columns]
    max_value = max(values) if values else 0
    if not columns or max_value <= 0:
        return empty_chart(width, height or 160, translate('No data'), title, fid)
    total_h = height or 220
    top = 22
    axis_h = 26
    plot_h = total_h - top - axis_h
    y_base = top + plot_h
    slot = width / len(columns)
    col_w = min(48, slot * 0.6)
    parts = ['<line x1="0" y1="{y}" x2="{w}" y2="{y}" stroke="{c}" stroke-width="1"/>'.format(
        y=_n(y_base), w=_n(width), c=RULE)]
    pairs = []
    for i, col in enumerate(columns):
        label = '{}'.format(col.get('label') or col.get('key') or '')
        text = format_number(col.get('value'), formatter)
        pairs.append((label, text))
        x = slot * i + (slot - col_w) / 2.0
        h = plot_h * values[i] / max_value
        parts.append('<g><title>{}</title>'.format(escape('{}: {}'.format(label, text))))
        parts.append(_column(x, y_base, col_w, h, col.get('color') or ACTION))
        parts.append(_text(x + col_w / 2.0, y_base - h - 10, text, size=VALUE_SIZE, anchor='middle'))
        parts.append(_text(x + col_w / 2.0, y_base + 14, ellipsis(label, slot - 8, VALUE_SIZE),
                           size=VALUE_SIZE, fill=INK_2, anchor='middle'))
        parts.append('</g>')
    return svg_document(width, total_h, title, _desc(title, pairs), ''.join(parts), fid)


RENDERERS = {
    'bar': bar_chart,
    'stacked_bar': stacked_bar_chart,
    'donut': donut_chart,
    'column': column_chart,
}


def render(spec, width, height=None, translate=identity, formatter=None):
    u"""Despacha por `spec['kind']`; un tipo desconocido devuelve el gráfico vacío."""
    renderer = RENDERERS.get(spec.get('kind'))
    if renderer is None:
        return empty_chart(width, height or 120, translate('No data'), spec.get('title') or '',
                           spec.get('id') or 'chart')
    return renderer(spec, width, height, translate, formatter)


def table_for(spec, translate=identity, formatter=None):
    u"""Tabla accesible equivalente a la spec: {'columns', 'rows', 'numeric'}.
    Incluye *todas* las filas (el gráfico puede recortar con `max_rows`)."""
    kind = spec.get('kind')
    label_header = spec.get('label_header') or ''
    if kind == 'stacked_bar':
        series = list(spec.get('series') or [])
        columns = [label_header] + [s.get('label') or s['key'] for s in series] + [translate('Total')]
        rows = []
        for row in spec.get('rows') or []:
            values = row.get('values') or {}
            cells = [row.get('label') or row.get('key') or '']
            total = 0
            for s in series:
                v = _num(values.get(s['key']))
                total += v
                cells.append(format_number(values.get(s['key']) or 0, formatter))
            cells.append(format_number(int(total) if total == int(total) else total, formatter))
            rows.append(cells)
        return {'columns': columns, 'rows': rows, 'numeric': list(range(1, len(columns)))}
    if kind == 'donut':
        slices = list(spec.get('slices') or [])
        total = sum(_num(s.get('value')) for s in slices)
        rows = []
        for s in slices:
            share = (100.0 * _num(s.get('value')) / total) if total else 0
            rows.append([s.get('label') or s.get('key') or '', format_number(s.get('value'), formatter),
                         _n(round(share, 1)) + '%'])
        return {'columns': [label_header, spec.get('value_label') or translate('Total'), '%'],
                'rows': rows, 'numeric': [1, 2]}
    if kind == 'column':
        rows = [[c.get('label') or c.get('key') or '', format_number(c.get('value'), formatter)]
                for c in spec.get('columns') or []]
        return {'columns': [label_header, spec.get('value_label') or translate('Total')],
                'rows': rows, 'numeric': [1]}
    rows_spec = list(spec.get('rows') or [])
    suffix = spec.get('suffix') or ''
    has_notes = any(r.get('note') for r in rows_spec)
    columns = [label_header, spec.get('value_label') or translate('Total')]
    if has_notes:
        columns.append(spec.get('note_label') or '')
    rows = []
    for r in rows_spec:
        cells = [r.get('label') or r.get('key') or '', format_number(r.get('value'), formatter) + suffix]
        if has_notes:
            cells.append('{}'.format(r.get('note') or ''))
        rows.append(cells)
    return {'columns': columns, 'rows': rows, 'numeric': [1]}
