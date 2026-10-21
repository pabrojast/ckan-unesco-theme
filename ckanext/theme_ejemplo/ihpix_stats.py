# -*- coding: utf-8 -*-
u"""Agregación del progreso IHP-IX (réplica de los dashboards Power BI).

Módulo puro (sin CKAN): recibe filas de `IhpixActivity.as_dict()` (o dicts
equivalentes) y devuelve el JSON que consume `/ihpix/progress` y la acción
`ihpix_progress_stats`. Cinco ámbitos (`SCOPES`) con una dimensión de
desglose cada uno (`DIMENSION_BY_SCOPE`):

- overall / flagship / ctwg → por Priority Area
- pa                       → por Output
- output                   → por Key Activity

Reglas:
- Una actividad cuenta en un KPI si su puerta está activa *o* tiene
  conteo/tipo informado (`ihpix_normalize.derive_gates`): así las 744
  filas heredadas, cuyo seed dejó las puertas en False, se agregan.
- "Por tipo" expone `activities` (nº de actividades) y `products` (Σ del
  conteo de cada fila con ese tipo). Una actividad con varios tipos suma
  su conteo bajo cada uno, como hace Power BI (inferencia; el tooltip del
  dashboard lo explica).
- Member States impactados = nombres canónicos de `member_states` ∪
  `country` ∪ `supporting_member_state`, resueltos con `country_index`.
"""
from __future__ import unicode_literals

import datetime
from collections import OrderedDict

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_normalize as N
from ckanext.theme_ejemplo import ihpix_relations as R

SCOPES = ('overall', 'pa', 'output', 'flagship', 'ctwg')

DIMENSION_BY_SCOPE = {
    'overall': 'priority_area',
    'pa': 'output',
    'output': 'key_activity',
    'flagship': 'priority_area',
    'ctwg': 'priority_area',
}

UNSPECIFIED = 'Unspecified'

LIST_FIELDS = ('flagships', 'cross_cutting_wg', 'regions',
               'knowledge_product_type', 'scientific_product_type',
               'knowledge_activity_type', 'training_type',
               'stakeholder_group_type')

INT_FIELDS = (
    'num_knowledge_products', 'num_scientific_products',
    'num_training_materials', 'num_curricula', 'num_transboundary_ms',
    'num_stakeholder_groups',
    'stakeholders_knowledge', 'stakeholders_knowledge_youth',
    'stakeholders_knowledge_female',
    'stakeholders_awareness', 'stakeholders_awareness_youth',
    'stakeholders_awareness_female',
)


def natural_key(code):
    u"""Orden natural de códigos '1.10' > '1.9'; 'PA2' → (2,); desconocidos al final."""
    text = str(code or '')
    if text.startswith('PA') and text[2:].isdigit():
        return (int(text[2:]),)
    try:
        return tuple(int(p) for p in text.split('.'))
    except ValueError:
        return (9999, text)


def _key(value):
    return N.clean_text(value).lower()


def _pct(part, total):
    if not total:
        return None
    return round(100.0 * part / total, 1)


# ─── Índice de países ────────────────────────────────────────────────────

def build_country_index(summaries, group_pairs=None):
    u"""{clave normalizada: {'name', 'region', 'lat', 'lon'}}.

    `summaries`: dicts de `IhpixCountrySummary.as_dict()` (country, region,
    latitude, longitude). `group_pairs`: [(slug, título)] de los grupos CKAN
    hijos de `member-states` (el formulario guarda el slug). Se añaden los
    alias de `COUNTRY_NAME_ALIASES` que apunten a un país del índice.
    """
    index = {}
    for item in summaries or ():
        name = N.clean_text(item.get('country'))
        if not name:
            continue
        lat = item.get('latitude')
        lon = item.get('longitude')
        entry = {
            'name': name,
            'region': N.clean_text(item.get('region')),
            'lat': float(lat) if lat not in (None, '', 0, 0.0) else None,
            'lon': float(lon) if lon not in (None, '', 0, 0.0) else None,
        }
        index[_key(name)] = entry
        index.setdefault(C.slugify(name), entry)
    for slug, title in group_pairs or ():
        title = N.clean_text(title)
        slug = N.clean_text(slug)
        entry = index.get(_key(title))
        if entry is None:
            entry = {'name': title or slug, 'region': '', 'lat': None, 'lon': None}
            if title:
                index[_key(title)] = entry
        if slug:
            index.setdefault(_key(slug), entry)
    for alias, target in N.COUNTRY_NAME_ALIASES.items():
        if target and _key(target) in index:
            index.setdefault(_key(alias), index[_key(target)])
    for country in R.countries():
        name = country.get('country_title_en')
        if not name:
            continue
        entry = index.get(_key(name), {'name': name, 'lat': None, 'lon': None, 'region': ''})
        entry['regions'] = country.get('regional_group') or []
        entry['electoral_group'] = country.get('electoral_group') or ''
        entry['iso2'] = country.get('iso2')
        for field in ('iso2', 'iso3', 'country_title_en', 'country_title_fr', 'country_title_es', 'country_title_ar'):
            if country.get(field):
                index[_key(country[field])] = entry
                if C.slugify(country[field]):
                    index[C.slugify(country[field])] = entry
    return index


def _resolve_country(value, index):
    u"""(nombre canónico o None, resuelto en el índice o no)."""
    name = N.normalize_country_name(value, index)
    if not name:
        return None, True
    if index is None:
        return name, True
    return name, _key(name) in index


# ─── Preparación y filtrado de filas ─────────────────────────────────────

def prepare_row(row, country_index=None):
    u"""Fila normalizada para agregar: listas en `list`, alias aplicados,
    puertas derivadas, países canónicos e `impacted_member_states`."""
    out = dict(row)
    for field in LIST_FIELDS:
        valid, unknown = N.normalize_multi(field, row.get(field))
        if unknown and 'Other' in (N.MULTI_VOCABULARIES.get(field, ((), None))[0] or ()):
            if 'Other' not in valid:
                valid.append('Other')
        out[field] = valid
    for field in INT_FIELDS:
        out[field] = N._int(row.get(field))
    out['biennium'] = N.normalize_choice('biennium', row.get('biennium')) or ''
    inst = N.normalize_choice('institution_type', row.get('institution_type'))
    out['institution_type'] = inst if inst in C.LEAD_INSTITUTION_TYPES else (
        'Other' if inst else '')
    out['priority_area'] = N.clean_text(row.get('priority_area'))
    out['output'] = N.clean_text(row.get('output'))
    out['institution'] = N.clean_text(row.get('institution'))
    code = N.clean_text(row.get('key_activity_code')) or C.key_activity_code(row.get('key_activity'))
    out['key_activity_code'] = code
    out.update(N.derive_gates(row))

    impacted = []
    unresolved = []
    roles = {}

    def _add(value, role):
        name, resolved = _resolve_country(value, country_index)
        if not name:
            return
        if name not in impacted:
            impacted.append(name)
        if not resolved and name not in unresolved:
            unresolved.append(name)
        roles.setdefault(name, set()).add(role)

    _add(row.get('country'), 'reporting')
    _add(row.get('supporting_member_state'), 'supporter')
    for supporter in R.read_list(row.get('supporters_json')):
        _add(supporter['country'], 'supporter')
    for item in N.split_legacy_multi(row.get('member_states')):
        _add(item, 'beneficiary')
    out['country'] = _resolve_country(row.get('country'), country_index)[0] or ''
    out['supporting_member_state'] = _resolve_country(
        row.get('supporting_member_state'), country_index)[0] or ''
    out['member_states'] = [n for n in impacted if 'beneficiary' in roles.get(n, ())]
    out['impacted_member_states'] = impacted
    out['impacted_roles'] = roles
    out['unresolved_member_states'] = unresolved
    return out


def _country_region(name, index):
    if not index:
        return []
    entry = index.get(_key(name))
    return (entry.get('regions') or [entry.get('region', '')]) if entry else []


def filter_rows(rows, scope='overall', value=None, filters=None, country_index=None):
    u"""Filas preparadas que caen en el ámbito y pasan los filtros."""
    filters = filters or {}
    biennium = N.normalize_choice('biennium', filters.get('biennium')) if filters.get('biennium') else ''
    region = N.clean_text(filters.get('region'))
    country = None
    if filters.get('country'):
        country = _resolve_country(filters.get('country'), country_index)[0]
    inst_type = N.clean_text(filters.get('institution_type'))
    out = []
    for row in rows:
        if scope == 'pa' and value not in (R.dimension_values(row, 'priority_area') or [row['priority_area']]):
            continue
        if scope == 'output' and value not in R.dimension_values(row, 'output'):
            continue
        if scope == 'flagship' and value not in row['flagships']:
            continue
        if scope == 'ctwg' and value not in row['cross_cutting_wg']:
            continue
        if biennium and row['biennium'] != biennium:
            continue
        if region:
            declared = region in row['regions']
            impacted = any(region in _country_region(n, country_index)
                           for n in row['impacted_member_states'])
            if not (declared or impacted):
                continue
        if country and country not in row['impacted_member_states']:
            continue
        if inst_type and row['institution_type'] != inst_type:
            continue
        row = dict(row, _scope=scope, _scope_value=value)
        out.append(row)
    return out


# ─── Agregación ──────────────────────────────────────────────────────────

def _dimension_key(row, dimension):
    if dimension == 'priority_area':
        return row['priority_area'] or UNSPECIFIED
    if dimension == 'output':
        return row['output'] or UNSPECIFIED
    return row['key_activity_code'] or UNSPECIFIED


def _dimension_label(key, dimension, labels):
    if key == UNSPECIFIED:
        return UNSPECIFIED
    labels = labels or {}
    if dimension == 'priority_area':
        title = C.PRIORITY_AREAS.get(key, '')
        return u'%s – %s' % (key, title) if title else key
    if dimension == 'output':
        title = (labels.get('outputs') or {}).get(key) or C.output_title(key)
        return u'%s – %s' % (key, title) if title else key
    title = (labels.get('key_activities') or {}).get(key) or C.key_activity_title(key)
    return u'%s – %s' % (key, title) if title else key


def _sorted_keys(keys):
    keys = list(keys)
    return sorted(keys, key=lambda k: ((1,) if k == UNSPECIFIED else (0,)) + natural_key(k))


def _by_dimension(rows, dimension, labels, measures):
    u"""[{key, label, <medida>…}] sumando `measures` = {nombre: fn(row)}."""
    buckets = OrderedDict()
    for row in rows:
        keys = R.dimension_values(row, dimension, row.get('_scope'), row.get('_scope_value'))
        fallback = UNSPECIFIED if row.get('_scope') in ('pa', 'output') else _dimension_key(row, dimension)
        for key in keys or [fallback]:
            bucket = buckets.setdefault(key, dict((m, 0) for m in measures))
            for name, fn in measures.items():
                bucket[name] += fn(row)
    result = []
    for key in _sorted_keys(buckets):
        item = {'key': key, 'label': _dimension_label(key, dimension, labels)}
        item.update(buckets[key])
        result.append(item)
    return result


def _by_type(rows, field, count_column, choices, value_key):
    u"""[{key, activities, <value_key>}] por valor del multiselect `field`,
    en el orden del vocabulario; sólo tipos con actividades."""
    counts = OrderedDict((c, {'activities': 0, value_key: 0}) for c in choices)
    for row in rows:
        for value in row[field]:
            bucket = counts.get(value)
            if bucket is None:
                continue
            bucket['activities'] += 1
            bucket[value_key] += row[count_column]
    return [dict(key=k, **v) for k, v in counts.items() if v['activities']]


def _count_by(rows, fn):
    out = OrderedDict()
    for row in rows:
        for key in fn(row):
            if key:
                out[key] = out.get(key, 0) + 1
    return out


def _scope_label(scope, value, labels):
    if scope == 'pa':
        return _dimension_label(value, 'priority_area', labels)
    if scope == 'output':
        return u'Output %s' % _dimension_label(value, 'output', labels)
    if scope == 'flagship':
        return C.flagship_label(value)
    if scope == 'ctwg':
        return value
    return 'Overall'


def _output_title(code, labels):
    u"""Título del Output (sin el código) o el propio código si no hay."""
    title = ((labels or {}).get('outputs') or {}).get(code) or C.output_title(code)
    return title or code


def _by_output(rows, labels):
    u"""Los 34 outputs en orden natural, siempre (aunque no tengan
    actividades): [{key, label, pa, count}] con los filtros ya aplicados."""
    counts = {}
    for row in rows:
        for output in R.dimension_values(row, 'output', row.get('_scope'), row.get('_scope_value')):
            counts[output] = counts.get(output, 0) + 1
    result = []
    for pa, pairs in C.OUTPUTS.items():
        for code, _ in pairs:
            result.append({'key': code, 'label': _output_title(code, labels),
                           'pa': pa, 'count': counts.get(code, 0)})
    return result


def _options(all_rows, labels, country_index, scope='overall', value=None):
    labels = labels or {}
    outputs_by_pa = OrderedDict()
    for pa, pairs in C.OUTPUTS.items():
        outputs_by_pa[pa] = [{'code': code, 'label': _output_title(code, labels)}
                             for code, _ in pairs]
    key_activities = []
    if scope == 'output' and value:
        key_activities = [{'code': item['code'], 'title': item['title']}
                          for item in C.key_activities_for(value)]
    regions = []
    if country_index:
        for entry in country_index.values():
            for region in entry.get('regions') or [entry.get('region')]:
                if region and region not in regions:
                    regions.append(region)
        regions.sort()
    if not regions:
        regions = [r for r in C.REGIONS if r != 'Global']
    biennia = [b for b in C.BIENNIA if any(r['biennium'] == b for r in all_rows)] or list(C.BIENNIA)
    return {
        'priority_areas': [{'code': pa, 'label': title} for pa, title in C.PRIORITY_AREAS.items()],
        'outputs_by_pa': outputs_by_pa,
        'flagships': [{'code': f, 'label': C.flagship_label(f), 'slug': C.slugify(f)} for f in C.FLAGSHIPS],
        'ctwgs': [{'name': w, 'slug': C.slugify(w)} for w in C.CROSS_CUTTING_WGS],
        'biennia': biennia,
        'regions': regions,
        'key_activities': key_activities,
    }


def _map_points(rows, country_index):
    u"""Un punto por país impactado con coordenadas, con sus roles."""
    points = OrderedDict()
    for row in rows:
        for name in row['impacted_member_states']:
            entry = country_index.get(_key(name)) if country_index else None
            if not entry or entry.get('lat') is None or entry.get('lon') is None:
                continue
            point = points.setdefault(name, {
                'country': entry['name'], 'region': entry.get('region', ''),
                'lat': entry['lat'], 'lon': entry['lon'], 'activities': 0,
                'as_reporting': 0, 'as_beneficiary': 0, 'as_supporter': 0,
            })
            point['activities'] += 1
            roles = row['impacted_roles'].get(name, ())
            if 'reporting' in roles:
                point['as_reporting'] += 1
            if 'beneficiary' in roles:
                point['as_beneficiary'] += 1
            if 'supporter' in roles:
                point['as_supporter'] += 1
    return sorted(points.values(), key=lambda p: (-p['activities'], p['country']))


def _by_region(rows, country_index):
    u"""[{key, member_states, activities}] según la región del país impactado
    (índice `IhpixCountrySummary.region`, las 5 regiones UNESCO)."""
    regions = OrderedDict()
    for row in rows:
        touched = set()
        for name in row['impacted_member_states']:
            for region in _country_region(name, country_index):
                if not region:
                    continue
                bucket = regions.setdefault(region, {'countries': set(), 'activities': 0})
                bucket['countries'].add(name)
                touched.add(region)
        for region in touched:
            regions[region]['activities'] += 1
    result = [{'key': r, 'member_states': len(v['countries']), 'activities': v['activities']}
              for r, v in regions.items()]
    return sorted(result, key=lambda x: (-x['activities'], x['key']))


def _output_biennium_matrix(rows):
    cells = OrderedDict()
    bienniums = set()
    for row in rows:
        if not row['biennium']:
            continue
        for output in R.dimension_values(row, 'output', row.get('_scope'), row.get('_scope_value')):
            cell = cells.setdefault(output, {'priority_area': C.priority_area_for_output(output),
                                               'total': 0, 'by_biennium': OrderedDict()})
            cell['by_biennium'][row['biennium']] = cell['by_biennium'].get(row['biennium'], 0) + 1
            cell['total'] += 1
            bienniums.add(row['biennium'])
    outputs = sorted(cells, key=natural_key)
    return {
        'bienniums': sorted(bienniums),
        'outputs': outputs,
        'rows': [dict(output=o, **cells[o]) for o in outputs],
    }


def compute_progress_stats(rows, scope='overall', value=None, filters=None,
                           country_index=None, labels=None):
    u"""JSON completo del dashboard de progreso para un ámbito.

    `rows`: dicts de actividades (sólo se agregan las publicadas si traen
    `status`). `value`: PA ('PA1'), Output ('1.3'), código de flagship o
    nombre de CTWG según `scope`. `labels`: {'outputs': {code: title},
    'key_activities': {code: title}} opcional (por defecto, constantes).
    """
    if scope not in SCOPES:
        raise ValueError('scope desconocido: %s' % scope)
    if scope == 'overall':
        value = None
    dimension = DIMENSION_BY_SCOPE[scope]
    filters = dict(filters or {})

    prepared = [prepare_row(r, country_index) for r in rows
                if (r.get('status') or 'published') == 'published']
    scoped = filter_rows(prepared, scope, value, filters, country_index)

    impacted = []
    unresolved = set()
    for row in scoped:
        for name in row['impacted_member_states']:
            if name not in impacted:
                impacted.append(name)
        unresolved.update(row['unresolved_member_states'])

    institutions = set(_key(r['institution']) for r in scoped if r['institution'])
    contributors = set(N.clean_text(r.get('reported_by')) for r in scoped
                       if N.clean_text(r.get('reported_by')))

    top_inst = OrderedDict()
    for row in scoped:
        if row['institution']:
            top_inst[row['institution']] = top_inst.get(row['institution'], 0) + 1
    top_institutions = [{'name': k, 'count': v} for k, v in
                        sorted(top_inst.items(), key=lambda x: (-x[1], x[0]))[:10]]

    overview = {
        'activities': len(scoped),
        'member_states_impacted': len(impacted),
        'institutions': len(institutions),
        'contributors': len(contributors),
        'by_dimension': _by_dimension(scoped, dimension, labels, {'count': lambda r: 1}),
        'by_output': _by_output(scoped, labels),
        'by_region': _by_region(scoped, country_index),
        'regions_declared': [{'key': k, 'count': v} for k, v in
                             sorted(_count_by(scoped, lambda r: r['regions']).items(),
                                    key=lambda x: (-x[1], x[0]))],
        'map': _map_points(scoped, country_index),
        'unresolved_member_states': sorted(unresolved),
        'by_biennium': [{'key': k, 'count': v} for k, v in
                        sorted(_count_by(scoped, lambda r: [r['biennium']]).items())],
        'top_institutions': top_institutions,
    }
    if scope in ('overall', 'pa'):
        overview['output_biennium_matrix'] = _output_biennium_matrix(scoped)

    k1a = [r for r in scoped if r['kpi_1a_active']]
    k1b = [r for r in scoped if r['kpi_1b_active']]
    kpi_1 = {
        'active_activities': len([r for r in scoped if r['kpi_1a_active'] or r['kpi_1b_active']]),
        'active_knowledge_activities': len(k1a),
        'active_scientific_activities': len(k1b),
        'knowledge_products': sum(r['num_knowledge_products'] for r in k1a),
        'scientific_products': sum(r['num_scientific_products'] for r in k1b),
        'by_dimension': _by_dimension(scoped, dimension, labels, OrderedDict([
            ('knowledge', lambda r: r['num_knowledge_products'] if r['kpi_1a_active'] else 0),
            ('scientific', lambda r: r['num_scientific_products'] if r['kpi_1b_active'] else 0),
        ])),
        'knowledge_by_type': _by_type(k1a, 'knowledge_product_type', 'num_knowledge_products',
                                      C.KNOWLEDGE_PRODUCT_TYPES, 'products'),
        'scientific_by_type': _by_type(k1b, 'scientific_product_type', 'num_scientific_products',
                                       C.SCIENTIFIC_PRODUCT_TYPES, 'products'),
    }

    def _people(rows_, total_col, gate):
        active = [r for r in rows_ if r[gate]]
        individuals = sum(r[total_col] for r in active)
        youth = sum(r[total_col + '_youth'] for r in active)
        female = sum(r[total_col + '_female'] for r in active)
        return active, {
            'active_activities': len(active),
            'individuals': individuals,
            'youth': youth,
            'female': female,
            'pct_youth': _pct(youth, individuals),
            'pct_female': _pct(female, individuals),
            'by_dimension': _by_dimension(scoped, dimension, labels, {
                'individuals': lambda r: r[total_col] if r[gate] else 0}),
        }

    k2, kpi_2 = _people(scoped, 'stakeholders_knowledge', 'kpi_2_active')
    kpi_2['by_activity_type'] = _by_type(k2, 'knowledge_activity_type', 'stakeholders_knowledge',
                                         C.KNOWLEDGE_ACTIVITY_TYPES, 'individuals')

    k3 = [r for r in scoped if r['kpi_3_active']]
    kpi_3 = {
        'active_activities': len(k3),
        'materials': sum(r['num_training_materials'] for r in k3),
        'by_dimension': _by_dimension(scoped, dimension, labels, {
            'materials': lambda r: r['num_training_materials'] if r['kpi_3_active'] else 0}),
        'by_type': _by_type(k3, 'training_type', 'num_training_materials',
                            C.TRAINING_TYPES, 'materials'),
    }

    k4 = [r for r in scoped if r['kpi_4_active']]
    kpi_4 = {
        'active_activities': len(k4),
        'curricula': sum(r['num_curricula'] for r in k4),
        'by_dimension': _by_dimension(scoped, dimension, labels, {
            'curricula': lambda r: r['num_curricula'] if r['kpi_4_active'] else 0}),
    }

    _, kpi_5 = _people(scoped, 'stakeholders_awareness', 'kpi_5_active')

    k6 = [r for r in scoped if r['kpi_6_active']]
    k6_countries = []
    for row in k6:
        for name in row['impacted_member_states']:
            if name not in k6_countries:
                k6_countries.append(name)
    kpi_6 = {
        'active_activities': len(k6),
        'member_states_reported': sum(r['num_transboundary_ms'] for r in k6),
        'member_states_distinct': len(k6_countries),
        'by_dimension': _by_dimension(scoped, dimension, labels, {
            'member_states': lambda r: r['num_transboundary_ms'] if r['kpi_6_active'] else 0}),
        'map': _map_points(k6, country_index),
    }

    k8 = [r for r in scoped if r['kpi_8_active']]
    k8_countries = set()
    for row in k8:
        k8_countries.update(row['impacted_member_states'])
    kpi_8 = {
        'active_activities': len(k8),
        'stakeholder_groups': sum(r['num_stakeholder_groups'] for r in k8),
        'member_states_distinct': len(k8_countries),
        'by_dimension': _by_dimension(scoped, dimension, labels, {
            'groups': lambda r: r['num_stakeholder_groups'] if r['kpi_8_active'] else 0}),
        'by_type': _by_type(k8, 'stakeholder_group_type', 'num_stakeholder_groups',
                            C.STAKEHOLDER_GROUP_TYPE_VALUES, 'groups'),
    }

    produced = _by_dimension(scoped, dimension, labels, OrderedDict([
        ('knowledge', lambda r: r['num_knowledge_products'] if r['kpi_1a_active'] else 0),
        ('scientific', lambda r: r['num_scientific_products'] if r['kpi_1b_active'] else 0),
        ('training', lambda r: r['num_training_materials'] if r['kpi_3_active'] else 0),
        ('curricula', lambda r: r['num_curricula'] if r['kpi_4_active'] else 0),
    ]))
    reached = _by_dimension(scoped, dimension, labels, OrderedDict([
        ('knowledge_improved', lambda r: r['stakeholders_knowledge'] if r['kpi_2_active'] else 0),
        ('awareness_raised', lambda r: r['stakeholders_awareness'] if r['kpi_5_active'] else 0),
    ]))

    return {
        'scope': {
            'kind': scope,
            'value': value,
            'label': _scope_label(scope, value, labels),
            'dimension': dimension,
        },
        'filters': filters,
        'generated_at': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
        'overview': overview,
        'kpi_1': kpi_1,
        'kpi_2': kpi_2,
        'kpi_3': kpi_3,
        'kpi_4': kpi_4,
        'kpi_5': kpi_5,
        'kpi_6': kpi_6,
        'kpi_8': kpi_8,
        'produced_by_dimension': produced,
        'reached_by_dimension': reached,
        'options': _options(prepared, labels, country_index, scope, value),
    }
