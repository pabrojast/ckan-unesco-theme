# -*- coding: utf-8 -*-
u"""Enlaces entre las actividades IHP-IX y las entidades del portal.

Módulo puro (sin CKAN). Dos responsabilidades:

- `group_scope`: a qué ámbito corresponde la pestaña IHP-IX de un grupo
  CKAN. Los grupos hijos de `member-states` son países; los demás grupos
  ("iniciativas") se reconocen como flagship o Cross-cutting Working Group
  por el slug de su nombre o de su título. Antes la pestaña filtraba
  siempre por país, así que en las iniciativas salía vacía.
- `activity_links`: fichas enlazables de una actividad (país sede,
  Member States beneficiarios y de apoyo, flagships, CTWG, institución)
  con el nombre canónico y el slug del grupo o la organización destino,
  para que explorador y pestañas enlacen en ambos sentidos.
"""
from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_normalize as N
from ckanext.theme_ejemplo import ihpix_relations as R
from ckanext.theme_ejemplo import ihpix_stats as S

COUNTRY_TITLE_FIELDS = ('country_title_en', 'country_title_fr',
                        'country_title_es', 'country_title_ar')


def _is_country_title(text):
    u"""True si el texto es el título (no el ISO) de un país de la lista
    oficial; evita que iniciativas de tres letras se confundan con ISO3."""
    meta = R.country_metadata(text)
    if not meta:
        return False
    key = N._key(text)
    for field in COUNTRY_TITLE_FIELDS:
        value = meta.get(field)
        if value and (N._key(value) == key or C.slugify(value) == key):
            return True
    return False


def group_scope(name, title=None, member_state_names=()):
    u"""(scope, value) de la pestaña IHP-IX de un grupo CKAN.

    ('country', slug) para Member States, ('flagship', código) y
    ('ctwg', nombre) para iniciativas reconocidas, (None, None) si el grupo
    no se puede atribuir (iniciativa sin flagship ni CTWG equivalente).
    """
    name = N.clean_text(name)
    title = N.clean_text(title)
    if name and name in set(member_state_names or ()):
        return 'country', name
    code = C.flagship_for_group(name, title)
    if code:
        return 'flagship', code
    ctwg = C.ctwg_for_group(name, title)
    if ctwg:
        return 'ctwg', ctwg
    if name and (_is_country_title(title) or _is_country_title(name)):
        return 'country', name
    return None, None


def scope_slug(scope, value):
    u"""Valor del ámbito tal como viaja en las URL del explorador y del
    panel de progreso (slug de flagship/CTWG; el slug del grupo si es país)."""
    if scope in ('flagship', 'ctwg'):
        return C.slugify(value)
    return value or ''


def member_state_slugs(pairs, country_index=None):
    u"""{nombre canónico de país: slug del grupo Member State}."""
    out = {}
    for slug, title in pairs or ():
        name = S._resolve_country(title, country_index)[0] or N.clean_text(title)
        if name and slug and name not in out:
            out[name] = slug
    return out


def flagship_groups(pairs):
    u"""{código de flagship: slug del grupo de iniciativa que lo representa}."""
    out = {}
    for slug, title in pairs or ():
        code = C.flagship_for_group(slug, title)
        if code and code not in out:
            out[code] = slug
    return out


def ctwg_groups(pairs):
    u"""{nombre de CTWG: slug del grupo de iniciativa que lo representa}."""
    out = {}
    for slug, title in pairs or ():
        name = C.ctwg_for_group(slug, title)
        if name and name not in out:
            out[name] = slug
    return out


def partner_ids(activity):
    u"""Ids de organizaciones socias guardados en la actividad (lista vacía
    si el JSON no es válido)."""
    try:
        return [str(x) for x in R.read_list(activity.get('partner_org_ids')) if x]
    except (ValueError, TypeError):
        return []


def activity_links(activity, country_index=None, member_states=None,
                   flagships=None, ctwgs=None):
    u"""Fichas enlazables de una actividad.

    Devuelve {'country', 'supporters', 'beneficiaries', 'flagships',
    'cross_cutting_wg', 'regions', 'institution', 'partners'}; cada país trae
    `label` (canónico), `group` (slug del Member State o None) y `resolved`;
    cada flagship `code`, `label`, `slug` y `group`; la institución
    `label` y `org_id`. Los slugs de grupo salen de `member_state_slugs`,
    `flagship_groups` y `ctwg_groups`; las URL las construye la vista.
    """
    row = S.prepare_row(activity, country_index)
    member_states = member_states or {}
    flagships = flagships or {}
    ctwgs = ctwgs or {}
    roles = row['impacted_roles']

    def _country(name):
        return {'label': name, 'group': member_states.get(name),
                'resolved': name not in row['unresolved_member_states']}

    return {
        'country': _country(row['country']) if row['country'] else None,
        'supporters': [_country(n) for n in row['impacted_member_states']
                       if 'supporter' in roles.get(n, ())],
        'beneficiaries': [_country(n) for n in row['member_states']],
        'flagships': [{'code': code, 'label': C.flagship_label(code),
                       'slug': C.slugify(code), 'group': flagships.get(code)}
                      for code in row['flagships']],
        'cross_cutting_wg': [{'label': name, 'slug': C.slugify(name),
                              'group': ctwgs.get(name)}
                             for name in row['cross_cutting_wg']],
        'regions': list(row['regions']),
        'institution': {'label': row['institution'],
                        'org_id': N.clean_text(activity.get('institution_org_id'))},
        'partners': partner_ids(activity),
    }
