# -*- coding: utf-8 -*-
u"""Adjuntos de un reporte IHP-IX: publicaciones, webinars, eventos y datos.

Módulo puro (sin CKAN) con la validación de los enlaces que el formulario
envía en el campo oculto `links_json` y las reglas de coherencia entre el
tipo de adjunto (`link_type`) y a qué apunta (`target_kind`):

- `package`: un dataset CKAN (publicación = dataset `type:documents`,
  dataset/datos del output = `type:dataset`). `target_id` = id del package.
- `page`: una página de ckanext-pages `water-events` (evento o webinar).
  `target_id` = `name` de la página.
- `url`: cualquier enlace externo registrado a mano (título + URL).

No se crean objetos CKAN desde aquí: sólo se referencian los existentes o
se guarda un enlace plano.
"""
from __future__ import unicode_literals

import datetime
import json
from collections import OrderedDict

LINK_TYPES = ('publication', 'webinar', 'event', 'dataset', 'output_data',
              'other')
TARGET_KINDS = ('package', 'page', 'url')

# Tipo de adjunto → target_kind admitidos
ALLOWED_KINDS = OrderedDict([
    ('publication', ('package', 'url')),
    ('dataset', ('package', 'url')),
    ('output_data', ('package', 'url')),
    ('event', ('page', 'url')),
    ('webinar', ('page', 'url')),
    ('other', ('url',)),
])

# Qué busca cada tipo en IHP-WINS (None = sólo entrada manual)
SEARCH_KIND_FOR_TYPE = OrderedDict([
    ('publication', 'publication'),
    ('dataset', 'dataset'),
    ('output_data', 'dataset'),
    ('event', 'event'),
    ('webinar', 'event'),
    ('other', None),
])

# Etiquetas por defecto (los templates las pasan por `_()`)
TYPE_LABELS = OrderedDict([
    ('publication', 'Publication'),
    ('webinar', 'Webinar'),
    ('event', 'Event'),
    ('dataset', 'Dataset'),
    ('output_data', 'Output data'),
    ('other', 'Other link'),
])

TITLE_MAX = 300
DESCRIPTION_MAX = 500
URL_MAX = 2000


class LinkValidationError(Exception):
    u"""Errores de validación de un adjunto: `.errors` es {campo: mensaje}."""

    def __init__(self, errors):
        self.errors = dict(errors)
        super(LinkValidationError, self).__init__(
            json.dumps(self.errors, sort_keys=True))


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
            raise LinkValidationError({'links_json': 'Invalid JSON'})
    if not isinstance(items, list):
        raise LinkValidationError({'links_json': 'Expected a list of links'})
    return [item for item in items if isinstance(item, dict)]


def validate_link(d):
    u"""Valida y normaliza un adjunto. Devuelve dict con las columnas de
    `IhpixActivityLink` (más `id`, vacío si es nuevo)."""
    errors = OrderedDict()
    link_type = _text(d, 'link_type').lower()
    target_kind = (_text(d, 'target_kind') or 'url').lower()
    target_id = _text(d, 'target_id')
    title = _text(d, 'title')
    url = _text(d, 'url')
    description = _text(d, 'description')

    if link_type not in LINK_TYPES:
        errors['link_type'] = 'Must be one of: {}'.format(', '.join(LINK_TYPES))
    if target_kind not in TARGET_KINDS:
        errors['target_kind'] = 'Must be one of: {}'.format(
            ', '.join(TARGET_KINDS))
    elif link_type in ALLOWED_KINDS and target_kind not in ALLOWED_KINDS[link_type]:
        errors['target_kind'] = '{} cannot point to a {}'.format(
            link_type, target_kind)

    if not title:
        errors['title'] = 'Title is required'
    elif len(title) > TITLE_MAX:
        errors['title'] = 'Title must be {} characters or fewer'.format(TITLE_MAX)

    if target_kind == 'url':
        if not url:
            errors['url'] = 'URL is required'
        elif not is_http_url(url):
            errors['url'] = 'URL must start with http:// or https://'
    else:
        if not target_id:
            errors['target_id'] = 'target_id is required for a {}'.format(
                target_kind)
        if url and not is_http_url(url) and not url.startswith('/'):
            errors['url'] = 'URL must be absolute (http/https) or site-relative'
    if len(url) > URL_MAX:
        errors['url'] = 'URL is too long'
    if len(description) > DESCRIPTION_MAX:
        errors['description'] = 'Description must be {} characters or fewer'.format(
            DESCRIPTION_MAX)

    event_date = None
    raw_date = _text(d, 'event_date')
    if raw_date:
        try:
            event_date = datetime.datetime.strptime(raw_date, '%Y-%m-%d').date()
        except ValueError:
            errors['event_date'] = 'Invalid date format. Use YYYY-MM-DD'

    try:
        display_order = max(0, int(d.get('display_order') or 0))
    except (TypeError, ValueError):
        display_order = 0

    if errors:
        raise LinkValidationError(errors)

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
    return url


def dedupe_key(link):
    u"""Clave para no adjuntar dos veces lo mismo (mismo objeto o misma URL)."""
    kind = link.get('target_kind') or 'url'
    if kind == 'url':
        return 'url:' + (link.get('url') or '').strip().lower()
    return kind + ':' + (link.get('target_id') or '')
