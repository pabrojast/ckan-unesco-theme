# -*- coding: utf-8 -*-
"""Relaciones del reporte: validación pura y lectura compatible de heredados."""
import json
from functools import lru_cache
from pathlib import Path

from ckanext.theme_ejemplo import ihpix_constants as C

JSON_FIELDS = ('contributions_json', 'synergies_json', 'supporters_json',
               'partner_org_ids')
SUPPORT_TYPES = ('financial', 'in_kind', 'hosting')


def read_list(value):
    if value in (None, ''):
        return []
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, list):
        raise ValueError('Must be a JSON list')
    if len(value) > 200:
        raise ValueError('At most 200 entries are allowed')
    return value


def associations(row, kind='contribution'):
    """No reinterpreta texto libre heredado; sólo usa códigos conocidos."""
    field = 'contributions_json' if kind == 'contribution' else 'synergies_json'
    items = read_list(row.get(field))
    if not items and kind == 'contribution' and row.get('output'):
        items = [{'priority_area': row.get('priority_area'),
                  'output': row['output'],
                  'key_activity_code': row.get('key_activity_code') or
                  C.key_activity_code(row.get('key_activity'))}]
    return items


def dimension_values(row, dimension, scope=None, code=None):
    items = associations(row)
    if scope == 'pa':
        items = [x for x in items if x['priority_area'] == code]
    elif scope == 'output':
        items = [x for x in items if x['output'] == code]
    field = 'key_activity_code' if dimension == 'key_activity' else dimension
    values = list(dict.fromkeys(x.get(field) for x in items if x.get(field)))
    if (not values and dimension == 'priority_area' and not row.get('output')
            and not read_list(row.get('contributions_json')) and row.get('priority_area')
            and scope != 'output' and (scope != 'pa' or row['priority_area'] == code)):
        values = [row['priority_area']]
    return values


@lru_cache(maxsize=1)
def countries():
    with (Path(__file__).parent / 'data' / 'ihpix_countries.json').open() as f:
        return json.load(f)['countries']


@lru_cache(maxsize=1)
def country_index():
    result = {}
    for row in countries():
        for field in ('iso2', 'iso3', 'country_title_en', 'country_title_fr',
                      'country_title_es', 'country_title_ar'):
            value = row.get(field)
            if value:
                result[value.casefold()] = row
                slug = C.slugify(value)
                if slug:
                    result[slug] = row
    return result


def country_metadata(value):
    key = str(value or '').strip().casefold()
    return country_index().get(key) if key else None


def validate(data):
    """Devuelve valores serializados y errores por campo/fila."""
    values, errors = {}, {}
    for field in JSON_FIELDS:
        try:
            items = read_list(data.get(field))
            cleaned = []
            for i, item in enumerate(items):
                path = '{}.{}'.format(field, i + 1)
                if field == 'partner_org_ids':
                    if not isinstance(item, str) or not item.strip() or len(item) > 100:
                        errors[path] = 'Invalid organization identifier'
                        continue
                    value = item.strip()
                elif not isinstance(item, dict):
                    errors[path] = 'Each entry must be an object'
                    continue
                elif field == 'supporters_json':
                    country = country_metadata(item.get('country'))
                    kinds = item.get('types', [])
                    if not country or not country.get('iso2'):
                        errors[path] = 'Select a UNESCO country'
                        continue
                    if (not isinstance(kinds, list) or not kinds or
                            any(k not in SUPPORT_TYPES for k in kinds)):
                        errors[path] = 'Select financial, in-kind or hosting support'
                        continue
                    value = {'country': country['iso2'], 'types': sorted(set(kinds))}
                else:
                    pa, output, key = (str(item.get(k) or '').strip() for k in
                                       ('priority_area', 'output', 'key_activity_code'))
                    if not C.is_valid_output_for_pa(pa, output):
                        errors[path] = 'Select an Output belonging to its Priority Area'
                        continue
                    if key and not C.is_valid_key_activity(output, key):
                        errors[path] = 'Key activity does not belong to this Output'
                        continue
                    value = {'priority_area': pa, 'output': output, 'key_activity_code': key}
                if value not in cleaned:
                    cleaned.append(value)
            values[field] = json.dumps(cleaned, ensure_ascii=False)
        except (ValueError, TypeError):
            errors[field] = 'Invalid list of entries (maximum 200)'
    return values, errors
