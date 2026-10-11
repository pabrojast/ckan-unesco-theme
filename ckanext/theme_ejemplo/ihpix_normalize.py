# -*- coding: utf-8 -*-
u"""Normalización de valores heredados del reporting IHP-IX.

Módulo puro (sin CKAN) que reconcilia los valores que llegaron del Excel de
Microsoft Forms (744 filas, 2022-2026) con las taxonomías canónicas de
`ihpix_constants`:

- alias de opciones ('Report' → 'Report or paper', 'Online Course' →
  'Online training course', 'FRIEND-Water' → 'FRIEND', '2022 - 2023' →
  '2022-2023', dobles espacios…);
- multiselects guardados como texto con comas en vez de JSON;
- grupos de stakeholders con su descripción parentética;
- nombres de país distintos a los de `IhpixCountrySummary`;
- puertas Sí/No (`kpi_*_active`, `has_flagship`…) que el seed dejó en
  False aunque haya conteos o tipos informados.

Lo usan `model._normalize_ihpix_legacy_values` (migración idempotente al
arrancar), el CLI `ckan ihpix normalize-legacy`, `ihpix_forms` (alias al
guardar) e `ihpix_stats` (lectura tolerante al agregar).
"""
from __future__ import unicode_literals

import datetime
import json
import re
from collections import OrderedDict

from ckanext.theme_ejemplo import ihpix_constants as C

WS_RE = re.compile(r'\s+')
# '2022 - 2023' / '2022 – 2023' → '2022-2023'
BIENNIUM_DASH_RE = re.compile(r'^(\d{4})\s*[-–—]\s*(\d{4})$')
DATE_RE = re.compile(r'^(\d{4})-(\d{2})-(\d{2})')

# Campo → {alias: valor canónico}. `None` descarta el valor. Las claves se
# comparan sin distinguir mayúsculas ni espacios sobrantes.
LEGACY_VALUE_ALIASES = {
    'knowledge_product_type': OrderedDict([
        ('Report', 'Report or paper'),
        ('Paper', 'Report or paper'),
        ('Report or Paper', 'Report or paper'),
        ('Statistic', 'Statistic or data source'),
        ('Statistics', 'Statistic or data source'),
        ('Statistic or data', 'Statistic or data source'),
        ('Data source', 'Statistic or data source'),
    ]),
    'scientific_product_type': OrderedDict([
        ('Peer-reviewed article', 'Peer-reviewed articles'),
        ('Peer reviewed articles', 'Peer-reviewed articles'),
        ('Patent', 'Patents'),
        ('Scientific journal edition', 'Scientific journal editions'),
        ('Scientific conference proceeding', 'Scientific conference proceedings'),
    ]),
    'knowledge_activity_type': OrderedDict([
        ('Seminar of online webinar', 'Seminar or online webinar'),
        ('Workshop or physical/online training', 'Workshop or physical/online training course'),
    ]),
    'training_type': OrderedDict([
        ('Online Course', 'Online training course'),
        ('Online course', 'Online training course'),
        ('Training Video', 'Training video'),
        ('Physical training course implemented', 'Physical training course'),
        ('Workshop or physical/online training course', 'Physical training course'),
        ('Hard copy', 'Physical training material (hard copy)'),
        ('Soft copy', 'Physical training material (soft copy)'),
    ]),
    'flagships': OrderedDict([
        ('FRIEND-Water', 'FRIEND'),
        ('FRIEND Water', 'FRIEND'),
        ('LaSII', 'LASII'),
        ('GWADI', 'G-WADI'),
        ('WAMUNET', 'WAMU-NET'),
        ('No', None),
        ('None', None),
        ('N/A', None),
    ]),
    'regions': OrderedDict([
        ('Asia-Pacific', 'Asia and the Pacific'),
        ('Latin America and Caribbean', 'Latin America and the Caribbean'),
        ('Europe and North-America', 'Europe and North America'),
    ]),
    'cross_cutting_wg': OrderedDict(),
    'biennium': OrderedDict(),
    'institution_type': OrderedDict([
        ('1', None),
        ('NGO', 'Non-Governmental Organization'),
        ('Non-Governmental Organisation', 'Non-Governmental Organization'),
        ('Governmental Organisation', 'Governmental Organization'),
        ('UNESCO Category 2 Center', 'UNESCO Category II Center'),
        ('UNESCO Category 2 Centre', 'UNESCO Category II Center'),
        ('UNESCO Category II Centre', 'UNESCO Category II Center'),
        ('UNESCO Category 1 Center', 'UNESCO Category I Center'),
        ('UNESCO Category I Centre', 'UNESCO Category I Center'),
        ('UNESCO Chair', 'UNESCO Chair or UNITWIN'),
        ('UNITWIN', 'UNESCO Chair or UNITWIN'),
    ]),
    'stakeholder_group_type': OrderedDict([
        ('NGOs', 'Non-Governmental Organizations (NGOs)'),
        ('Non-Governmental Organizations', 'Non-Governmental Organizations (NGOs)'),
        ('Industry', 'Private Sector'),
        ('Community-Based Organizations', 'Community Groups'),
        ('Regional Water Management Bodies', 'River Basin Organizations or Regional Water Management Bodies'),
        ('River Basin Organizations', 'River Basin Organizations or Regional Water Management Bodies'),
    ]),
}

# Nombre heredado (Excel / ISO fallback del formulario) → nombre tal como
# figura en `IhpixCountrySummary.country` (lista ONU usada por el seed).
# `None` descarta el valor.
COUNTRY_NAME_ALIASES = OrderedDict([
    ('Turkey', 'Türkiye'),
    ('Turkiye', 'Türkiye'),
    ('Venezuela (Bolivarian Republic of)', 'Venezuela'),
    ('Bolivarian Republic of Venezuela', 'Venezuela'),
    ('State of Palestine', 'Palestine'),
    ('Palestinian Territory', 'Palestine'),
    ('Micronesia (Federated States of)', 'Micronesia'),
    ('Federated States of Micronesia', 'Micronesia'),
    ('Central African', 'Central African Republic'),
    ('Republic Chad', 'Chad'),
    ('Republic of Chad', 'Chad'),
    ('Papua', 'Papua New Guinea'),
    ('New Guinea', 'Papua New Guinea'),
    ('Macau', 'Macao'),
    ('Macao SAR', 'Macao'),
    ('No', None),
    ('None', None),
    ('N/A', None),
    ('Global', None),
    # Nombres cortos del fallback ISO del formulario (`MEMBER_STATES`)
    ('Bolivia', 'Bolivia (Plurinational State of)'),
    ('Iran', 'Iran (Islamic Republic of)'),
    ('Russia', 'Russian Federation'),
    ('Korea (South)', 'Republic of Korea'),
    ('South Korea', 'Republic of Korea'),
    ('Korea (North)', 'Democratic People’s Republic of Korea'),
    ('North Korea', 'Democratic People’s Republic of Korea'),
    ("Democratic People's Republic of Korea", 'Democratic People’s Republic of Korea'),
    ('Laos', 'Lao People’s Democratic Republic'),
    ("Lao People's Democratic Republic", 'Lao People’s Democratic Republic'),
    ('Moldova', 'Republic of Moldova'),
    ('Syria', 'Syrian Arab Republic'),
    ('Tanzania', 'United Republic of Tanzania'),
    ('United Kingdom', 'United Kingdom of Great Britain and Northern Ireland'),
    ('UK', 'United Kingdom of Great Britain and Northern Ireland'),
    ('United States', 'United States of America'),
    ('USA', 'United States of America'),
    ('Vietnam', 'Viet Nam'),
    ('Czech Republic', 'Czechia'),
    ('Swaziland', 'Eswatini'),
    ('Brunei', 'Brunei Darussalam'),
    ('Cape Verde', 'Cabo Verde'),
    ('Ivory Coast', 'Côte d’Ivoire'),
    ("Cote d'Ivoire", 'Côte d’Ivoire'),
    ("Côte d'Ivoire", 'Côte d’Ivoire'),
    ('Congo (Democratic Republic)', 'Democratic Republic of the Congo'),
    ('DR Congo', 'Democratic Republic of the Congo'),
    ('Macedonia', 'North Macedonia'),
    ('East Timor', 'Timor-Leste'),
])

# Puertas Sí/No → (columnas de conteo, columnas de tipo) que las activan
GATE_SOURCES = OrderedDict([
    ('kpi_1a_active', (('num_knowledge_products',), ('knowledge_product_type',))),
    ('kpi_1b_active', (('num_scientific_products',), ('scientific_product_type',))),
    ('kpi_2_active', (('stakeholders_knowledge', 'stakeholders_knowledge_youth',
                       'stakeholders_knowledge_female'), ('knowledge_activity_type',))),
    ('kpi_3_active', (('num_training_materials',), ('training_type',))),
    ('kpi_4_active', (('num_curricula',), ())),
    ('kpi_5_active', (('stakeholders_awareness', 'stakeholders_awareness_youth',
                       'stakeholders_awareness_female'), ())),
    ('kpi_6_active', (('num_transboundary_ms',), ())),
    ('kpi_8_active', (('num_stakeholder_groups',), ('stakeholder_group_type',
                                                    'stakeholder_group_name'))),
    ('has_flagship', ((), ('flagships',))),
    ('regions_benefit', ((), ('regions', 'member_states'))),
    ('has_member_state_support', ((), ('supporting_member_state',))),
    ('has_synergies', ((), ('synergies',))),
])

# Multiselects con vocabulario cerrado: campo → (valores permitidos, columna 'Other')
MULTI_VOCABULARIES = OrderedDict([
    ('flagships', (C.FLAGSHIPS, None)),
    ('cross_cutting_wg', (C.CROSS_CUTTING_WGS, None)),
    ('regions', (C.REGIONS, None)),
    ('knowledge_product_type', (C.KNOWLEDGE_PRODUCT_TYPES, 'knowledge_product_type_other')),
    ('scientific_product_type', (C.SCIENTIFIC_PRODUCT_TYPES, None)),
    ('knowledge_activity_type', (C.KNOWLEDGE_ACTIVITY_TYPES, 'knowledge_activity_type_other')),
    ('training_type', (C.TRAINING_TYPES, 'training_type_other')),
    ('stakeholder_group_type', (C.STAKEHOLDER_GROUP_TYPE_VALUES, 'stakeholder_group_type_other')),
])

SINGLE_VOCABULARIES = OrderedDict([
    ('biennium', C.BIENNIA),
    ('institution_type', C.LEAD_INSTITUTION_TYPES),
])


def _key(value):
    return WS_RE.sub(' ', str(value or '')).strip().lower()


def clean_text(value):
    u"""Colapsa espacios (incluidos los dobles del Excel) y recorta."""
    if value is None:
        return ''
    return WS_RE.sub(' ', str(value)).strip()


def _alias_lookup(field):
    u"""{clave normalizada: canónico} con los alias del campo y los propios
    valores permitidos (para igualar sin distinguir mayúsculas)."""
    table = {}
    allowed = MULTI_VOCABULARIES.get(field, (None, None))[0] or SINGLE_VOCABULARIES.get(field)
    for value in allowed or ():
        table[_key(value)] = value
    for alias, target in LEGACY_VALUE_ALIASES.get(field, {}).items():
        table[_key(alias)] = target
    return table


def normalize_choice(field, value):
    u"""Valor canónico de un campo de opción única o de un item de multi.

    - aplica alias y comparación sin mayúsculas;
    - `biennium`: quita los espacios alrededor del guion;
    - devuelve None si el alias descarta el valor y el valor limpio (sin
      cambios) si no se reconoce (el caller decide qué hacer con él).
    """
    text = clean_text(value)
    if not text:
        return ''
    if field == 'biennium':
        m = BIENNIUM_DASH_RE.match(text)
        if m:
            text = '%s-%s' % (m.group(1), m.group(2))
    table = _alias_lookup(field)
    key = _key(text)
    if key in table:
        return table[key]
    return text


def _split_tokens(text, allowed):
    u"""Divide un texto con comas/puntos y coma respetando los valores
    permitidos que contienen comas (los más largos primero)."""
    candidates = sorted((a for a in allowed or () if a), key=len, reverse=True)
    tokens = []
    rest = text
    while True:
        rest = rest.lstrip(',; ').strip()
        if not rest:
            break
        matched = False
        lower = rest.lower()
        for cand in candidates:
            n = len(cand)
            if lower.startswith(cand.lower()) and (len(rest) == n or rest[n] in ',;'):
                tokens.append(rest[:n])
                rest = rest[n:]
                matched = True
                break
        if matched:
            continue
        cut = len(rest)
        for sep in (',', ';'):
            i = rest.find(sep)
            if 0 <= i < cut:
                cut = i
        token = rest[:cut].strip()
        if token:
            tokens.append(token)
        rest = rest[cut:]
    return tokens


def split_legacy_multi(value, allowed=None):
    u"""Lista de items de un multiselect venga como venga.

    - list/tuple → items limpios;
    - texto JSON '["A","B"]' → lista;
    - texto con comas/puntos y coma → tokens, sin partir los valores
      permitidos que llevan comas ni los paréntesis descriptivos.
    """
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        items = [clean_text(v) for v in value]
        return [v for v in items if v]
    text = clean_text(value)
    if not text:
        return []
    if text.startswith('['):
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            data = None
        if isinstance(data, list):
            items = [clean_text(v) for v in data]
            return [v for v in items if v]
    candidates = list(allowed or ())
    candidates.extend(k for k in LEGACY_VALUE_ALIASES.get('cross_cutting_wg', {}))
    if ';' in text:
        parts = [p.strip() for p in text.split(';')]
        return [p for p in parts if p]
    if '(' in text and ',' in text and ',' not in text.split('(')[0]:
        # 'Community Groups (local communities, resident organizations) …'
        return [text]
    return _split_tokens(text, candidates)


def normalize_stakeholder_group_types(value):
    u"""Grupos de stakeholders: el Excel guardaba la frase completa con su
    descripción parentética ("Government Agencies (national water …)").
    Devuelve (válidos canónicos, desconocidos)."""
    allowed = C.STAKEHOLDER_GROUP_TYPE_VALUES
    items = split_legacy_multi(value, allowed)
    table = _alias_lookup('stakeholder_group_type')
    canon_sorted = sorted(allowed, key=len, reverse=True)
    valid, unknown = [], []
    for item in items:
        target = None
        key = _key(item)
        if key in table:
            target = table[key]
        else:
            lower = item.lower()
            for canon in canon_sorted:
                if lower.startswith(canon.lower()):
                    target = canon
                    break
            if target is None:
                prefix = item.split(' (')[0].strip()
                prefix_key = _key(prefix)
                if prefix_key in table:
                    target = table[prefix_key]
                else:
                    for canon in canon_sorted:
                        if prefix and canon.lower().startswith(prefix.lower()):
                            target = canon
                            break
        if target is None:
            if item not in unknown:
                unknown.append(item)
        elif target not in valid:
            valid.append(target)
    return valid, unknown


def normalize_multi(field, value, allowed=None):
    u"""(válidos canónicos sin duplicados, desconocidos) de un multiselect.

    `allowed=None` toma el vocabulario del campo; para campos sin
    vocabulario (member_states) todo item limpio es válido.
    """
    if field == 'stakeholder_group_type':
        return normalize_stakeholder_group_types(value)
    if allowed is None:
        allowed = MULTI_VOCABULARIES.get(field, (None, None))[0]
    alias_keys = list(LEGACY_VALUE_ALIASES.get(field, {}).keys())
    items = split_legacy_multi(value, list(allowed or ()) + alias_keys)
    if allowed is None:
        out = []
        for item in items:
            if item not in out:
                out.append(item)
        return out, []
    allowed_set = set(allowed)
    valid, unknown = [], []
    for item in items:
        target = normalize_choice(field, item)
        if target is None or target == '':
            continue
        if target in allowed_set:
            if target not in valid:
                valid.append(target)
        elif target not in unknown:
            unknown.append(target)
    return valid, unknown


def normalize_country_name(value, country_index=None):
    u"""Nombre canónico de un país (el de `IhpixCountrySummary`).

    `country_index` es {clave normalizada: {'name': …}} (nombres, alias y
    slugs de los grupos CKAN). Sin índice sólo se aplican los alias.
    Devuelve None para valores descartados ('No') y el texto limpio si no
    se reconoce.
    """
    text = clean_text(value)
    if not text:
        return ''
    key = _key(text)
    for alias, target in COUNTRY_NAME_ALIASES.items():
        if _key(alias) == key:
            if target is None:
                return None
            text, key = target, _key(target)
            break
    if country_index:
        entry = country_index.get(key)
        if entry:
            return entry.get('name') or text
    return text


def normalize_date(value):
    u"""'2023-09-29T00:00:00' / date / datetime → 'YYYY-MM-DD'; vacío → ''."""
    if value is None:
        return ''
    if isinstance(value, datetime.datetime):
        return value.date().isoformat()
    if isinstance(value, datetime.date):
        return value.isoformat()
    text = clean_text(value)
    if not text:
        return ''
    m = DATE_RE.match(text)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)),
                                 int(m.group(3))).isoformat()
        except ValueError:
            return ''
    for fmt in ('%d/%m/%Y', '%Y/%m/%d', '%d.%m.%Y'):
        try:
            return datetime.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return ''


def _int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, (list, tuple)):
        return any(clean_text(v) for v in value)
    text = clean_text(value)
    return bool(text) and text not in ('[]', '0')


def _has_meaningful(field, value):
    u"""True si el campo trae algo que cuente tras aplicar alias: 'No' en
    `flagships` o en `supporting_member_state` no es un dato."""
    if not _has_value(value):
        return False
    if field in MULTI_VOCABULARIES:
        valid, unknown = normalize_multi(field, value)
        return bool(valid or unknown)
    if field == 'member_states':
        return any(normalize_country_name(v) for v in split_legacy_multi(value))
    if field == 'supporting_member_state':
        return bool(normalize_country_name(value))
    return True


def derive_gates(row):
    u"""{puerta: bool} combinando el valor guardado con los datos de la fila.

    Una puerta se considera activa si ya lo estaba, si algún conteo
    asociado es > 0 o si hay tipo/texto informado (tras alias: un
    flagship 'No' no activa nada). `unesco_secretariat_participation`
    hereda del texto heredado `unesco_participation`.
    """
    gates = OrderedDict()
    for gate, (counts, texts) in GATE_SOURCES.items():
        active = C.normalize_bool(row.get(gate))
        if not active:
            active = any(_int(row.get(col)) > 0 for col in counts)
        if not active:
            active = any(_has_meaningful(col, row.get(col)) for col in texts)
        gates[gate] = bool(active)
    active = C.normalize_bool(row.get('unesco_secretariat_participation'))
    if not active:
        active = C.normalize_bool(row.get('unesco_participation'))
    gates['unesco_secretariat_participation'] = bool(active)
    return gates


def _json_or_empty(items):
    return json.dumps(items) if items else ''


def _stored_items(value):
    u"""Lista almacenada tal cual (sin limpiar) si el valor ya es una lista
    o un JSON de lista; None si es texto plano (comas) y hay que reescribir."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    text = str(value).strip()
    if not text:
        return []
    if text.startswith('['):
        try:
            data = json.loads(text)
        except (ValueError, TypeError):
            return None
        if isinstance(data, list):
            return [str(v) for v in data]
    return None


def normalize_activity_row(row):
    u"""Cambios a aplicar sobre una fila (`IhpixActivity.as_dict()` o dict
    equivalente). Devuelve sólo las claves cuyo valor cambia; aplicar los
    cambios y volver a llamar devuelve {} (idempotente).
    """
    changes = OrderedDict()

    # Opción única
    for field in SINGLE_VOCABULARIES:
        raw = row.get(field)
        if not clean_text(raw):
            continue
        target = normalize_choice(field, raw)
        if target is None:
            target = ''
        elif field == 'institution_type' and target not in C.LEAD_INSTITUTION_TYPES:
            # Categoría libre → 'Other' conservando el texto original
            if not clean_text(row.get('institution_type_other')):
                changes['institution_type_other'] = target
            target = 'Other'
        if target != raw:
            changes[field] = target

    # Multiselects con vocabulario
    for field, (allowed, other_column) in MULTI_VOCABULARIES.items():
        raw = row.get(field)
        if not _has_value(raw):
            continue
        valid, unknown = normalize_multi(field, raw, allowed)
        if unknown and 'Other' in allowed:
            if 'Other' not in valid:
                valid.append('Other')
            if other_column and not clean_text(row.get(other_column)):
                changes[other_column] = ', '.join(unknown)[:150]
        if _stored_items(raw) != valid:
            changes[field] = _json_or_empty(valid)

    # Member States beneficiarios (sin vocabulario cerrado)
    raw = row.get('member_states')
    if _has_value(raw):
        names = []
        for item in split_legacy_multi(raw):
            name = normalize_country_name(item)
            if name and name not in names:
                names.append(name)
        if _stored_items(raw) != names:
            changes['member_states'] = _json_or_empty(names)

    for field in ('country', 'supporting_member_state'):
        raw = row.get(field)
        if clean_text(raw):
            name = normalize_country_name(raw)
            name = '' if name is None else name
            if name != raw:
                changes[field] = name

    # Key activity: código oficial derivado del texto heredado
    code = C.key_activity_code(row.get('key_activity'))
    if code and code != (row.get('key_activity_code') or ''):
        changes['key_activity_code'] = code

    # Fecha de finalización con formatos mixtos del Excel
    raw = row.get('end_date')
    if raw not in (None, ''):
        normalized = normalize_date(raw)
        if normalized and normalized != (raw if isinstance(raw, str) else normalize_date(raw)):
            changes['end_date'] = normalized

    # Puertas Sí/No derivadas de los datos
    for gate, active in derive_gates(row).items():
        if active != C.normalize_bool(row.get(gate)):
            changes[gate] = active

    return changes
