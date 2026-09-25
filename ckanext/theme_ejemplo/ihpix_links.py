# -*- coding: utf-8 -*-
u"""Adjuntos de un reporte IHP-IX: publicaciones, webinars, eventos y datos.

Módulo puro (sin CKAN) con la validación de los enlaces que el formulario
envía en el campo oculto `links_json` y las reglas de coherencia entre el
tipo de adjunto (`link_type`) y a qué apunta (`target_kind`):

- `package`: un dataset CKAN (publicación = dataset `type:documents`,
  dataset/datos del output = `type:dataset`). `target_id` = id del package.
- `page`: una página de ckanext-pages `water-events` (evento o webinar).
  `target_id` = `name` de la página.
- `course`: un curso de UNESCO Open Learning de la caché curada
  (`OpenLearningCourse`, sólo `approved`). `target_id` = `course_id` de
  Open edX (p. ej. `course-v1:UNESCO+IHP01+2025`).
- `url`: cualquier enlace externo registrado a mano (título + URL).

Este módulo no crea objetos CKAN: sólo referencia los existentes o guarda
un enlace plano. La creación inline de publicaciones vive en
`ihpix_publications.py` + `actions.ihpix_publication_create`.
"""
from __future__ import unicode_literals

import datetime
import json
import re
from collections import OrderedDict

LINK_TYPES = ('publication', 'webinar', 'event', 'dataset', 'output_data',
              'course', 'other')
TARGET_KINDS = ('package', 'page', 'course', 'url')

# Tipo de adjunto → target_kind admitidos
ALLOWED_KINDS = OrderedDict([
    ('publication', ('package', 'url')),
    ('dataset', ('package', 'url')),
    ('output_data', ('package', 'url')),
    ('event', ('page', 'url')),
    ('webinar', ('page', 'url')),
    ('course', ('course', 'url')),
    ('other', ('url',)),
])

# Qué busca cada tipo en IHP-WINS (None = sólo entrada manual)
SEARCH_KIND_FOR_TYPE = OrderedDict([
    ('publication', 'publication'),
    ('dataset', 'dataset'),
    ('output_data', 'dataset'),
    ('event', 'event'),
    ('webinar', 'event'),
    ('course', 'course'),
    ('other', None),
])

# Etiquetas por defecto (los templates las pasan por `_()`)
TYPE_LABELS = OrderedDict([
    ('publication', 'Publication'),
    ('webinar', 'Webinar'),
    ('event', 'Event'),
    ('dataset', 'Dataset'),
    ('output_data', 'Output data'),
    ('course', 'Course'),
    ('other', 'Other link'),
])

# Iconos Font Awesome por tipo (templates y widget)
TYPE_ICONS = OrderedDict([
    ('publication', 'fa-book'),
    ('webinar', 'fa-video-camera'),
    ('event', 'fa-calendar'),
    ('dataset', 'fa-database'),
    ('output_data', 'fa-table'),
    ('course', 'fa-graduation-cap'),
    ('other', 'fa-link'),
])

# Misma plantilla que `model.OPENLEARNING_COURSE_URL`
COURSE_URL_TEMPLATE = 'https://openlearning.unesco.org/courses/{course_id}/about'
_COURSE_ID_RE = re.compile(r'/courses/(course-v1:[^/?#\s]+)', re.I)


def course_url(course_id):
    return COURSE_URL_TEMPLATE.format(course_id=course_id)


def parse_course_id(value):
    u"""`course_id` de Open edX a partir de una URL de Open Learning o del
    propio id ('course-v1:ORG+CODE+RUN'). '' si no se reconoce."""
    s = (value or '').strip()
    if not s:
        return ''
    if s.lower().startswith('course-v1:'):
        return s.split('?')[0].split('#')[0].rstrip('/')
    m = _COURSE_ID_RE.search(s)
    return m.group(1) if m else ''

TITLE_MAX = 300
DESCRIPTION_MAX = 500
URL_MAX = 2000

# Mensajes (inglés); se traducen en actions con `toolkit._()` vía `.details`
MESSAGES = OrderedDict([
    ('links_invalid_json', 'Invalid JSON'),
    ('links_not_list', 'Expected a list of links'),
    ('choice_invalid', 'Must be one of: {choices}'),
    ('kind_not_allowed', '{link_type} cannot point to a {target_kind}'),
    ('title_required', 'Title is required'),
    ('max_length', '{field} must be {max} characters or fewer'),
    ('url_required', 'URL is required'),
    ('url_invalid', 'URL must start with http:// or https://'),
    ('url_relative_invalid', 'URL must be absolute (http/https) or site-relative'),
    ('url_too_long', 'URL is too long'),
    ('target_required', 'target_id is required for a {target_kind}'),
    ('date_invalid', 'Invalid date format. Use YYYY-MM-DD'),
])


class LinkValidationError(Exception):
    u"""Errores de validación de un adjunto: `.errors` es {campo: mensaje}
    y `.details` {campo: (clave de MESSAGES, params)}."""

    def __init__(self, errors, details=None):
        self.errors = dict(errors)
        self.details = dict(details or {})
        super(LinkValidationError, self).__init__(
            json.dumps(self.errors, sort_keys=True))


def _err(errors, details, fname, key, **params):
    errors[fname] = MESSAGES[key].format(**params)
    details[fname] = (key, params)


def _text(d, key):
    val = d.get(key)
    return '' if val is None else str(val).strip()


def is_http_url(value):
    return value.startswith('http://') or value.startswith('https://')


def parse_links_json(raw):
    u"""`links_json` (string JSON, lista o vacío) → lista de dicts.

    Tolerante con '' / '[]' / None (→ []). JSON inválido o que no sea una
    lista → `LinkValidationError`. Los elementos que no sean dict se ignoran.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        s = str(raw).strip()
        if not s:
            return []
        try:
            items = json.loads(s)
        except (ValueError, TypeError):
            raise LinkValidationError({'links_json': MESSAGES['links_invalid_json']},
                                      {'links_json': ('links_invalid_json', {})})
    if not isinstance(items, list):
        raise LinkValidationError({'links_json': MESSAGES['links_not_list']},
                                  {'links_json': ('links_not_list', {})})
    return [item for item in items if isinstance(item, dict)]


def validate_link(d):
    u"""Valida y normaliza un adjunto. Devuelve dict con las columnas de
    `IhpixActivityLink` (más `id`, vacío si es nuevo)."""
    errors = OrderedDict()
    details = OrderedDict()
    link_type = _text(d, 'link_type').lower()
    target_kind = (_text(d, 'target_kind') or 'url').lower()
    target_id = _text(d, 'target_id')
    title = _text(d, 'title')
    url = _text(d, 'url')
    description = _text(d, 'description')

    if link_type not in LINK_TYPES:
        _err(errors, details, 'link_type', 'choice_invalid', choices=', '.join(LINK_TYPES))
    if target_kind not in TARGET_KINDS:
        _err(errors, details, 'target_kind', 'choice_invalid', choices=', '.join(TARGET_KINDS))
    elif link_type in ALLOWED_KINDS and target_kind not in ALLOWED_KINDS[link_type]:
        _err(errors, details, 'target_kind', 'kind_not_allowed',
             link_type=link_type, target_kind=target_kind)

    if not title:
        _err(errors, details, 'title', 'title_required')
    elif len(title) > TITLE_MAX:
        _err(errors, details, 'title', 'max_length', field='Title', max=TITLE_MAX)

    if target_kind == 'url':
        if not url:
            _err(errors, details, 'url', 'url_required')
        elif not is_http_url(url):
            _err(errors, details, 'url', 'url_invalid')
    else:
        if not target_id:
            _err(errors, details, 'target_id', 'target_required', target_kind=target_kind)
        if url and not is_http_url(url) and not url.startswith('/'):
            _err(errors, details, 'url', 'url_relative_invalid')
    if len(url) > URL_MAX:
        _err(errors, details, 'url', 'url_too_long')
    if len(description) > DESCRIPTION_MAX:
        _err(errors, details, 'description', 'max_length', field='Description', max=DESCRIPTION_MAX)

    event_date = None
    raw_date = _text(d, 'event_date')
    if raw_date:
        try:
            event_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            _err(errors, details, 'event_date', 'date_invalid')

    try:
        display_order = max(0, int(d.get('display_order') or 0))
    except (TypeError, ValueError):
        display_order = 0

    if errors:
        raise LinkValidationError(errors, details)

    return {
        'id': _text(d, 'id'),
        'link_type': link_type,
        'target_kind': target_kind,
        'target_id': target_id,
        'title': title,
        'url': url,
        'description': description,
        'event_date': event_date,
        'display_order': display_order,
    }


def link_public_url(link):
    u"""URL navegable de un adjunto (dict o modelo con los mismos atributos)."""
    def _get(key):
        if isinstance(link, dict):
            return link.get(key) or ''
        return getattr(link, key, None) or ''

    kind = _get('target_kind')
    target_id = _get('target_id')
    url = _get('url')
    if kind == 'package' and target_id:
        if _get('link_type') == 'publication':
            return '/documents/' + target_id
        return '/dataset/' + target_id
    if kind == 'page' and target_id:
        return '/water-events/' + target_id
    if kind == 'course' and target_id:
        return url or course_url(target_id)
    return url


def dedupe_key(link):
    u"""Clave para no adjuntar dos veces lo mismo (mismo objeto o misma URL)."""
    kind = link.get('target_kind') or 'url'
    if kind == 'url':
        return 'url:' + (link.get('url') or '').strip().lower()
    return kind + ':' + (link.get('target_id') or '')
