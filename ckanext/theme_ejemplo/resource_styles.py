"""Política común de archivos SLD y presentación de recursos, sin acceso a DB."""
import json
import re
from urllib.parse import unquote, urlsplit

SLD_MIME = 'application/vnd.ogc.sld+xml'
_RESOURCE_PATH = re.compile(r'/resource/([0-9a-fA-F-]{36})(?:/|$)')


def is_sld_url(url):
    try:
        return unquote(urlsplit(str(url or '').strip()).path).lower().endswith('.sld')
    except ValueError:
        return False


def is_sld_resource(resource):
    fmt = str(resource.get('format') or '').strip().lower()
    mime = str(resource.get('mimetype') or '').split(';', 1)[0].strip().lower()
    return fmt in ('sld', SLD_MIME) or mime == SLD_MIME or is_sld_url(resource.get('url'))


def sld_url_sql(column):
    """Expresión PostgreSQL; column siempre es un identificador interno fijo."""
    path = "lower(split_part(split_part(regexp_replace(trim(COALESCE(%s, '')), '^[a-zA-Z][a-zA-Z0-9+.-]*://[^/]*', ''), '?', 1), '#', 1))" % column
    for encoded, decoded in (('%2e', '.'), ('%73', 's'), ('%6c', 'l'), ('%64', 'd')):
        path = "replace(%s, '%s', '%s')" % (path, encoded, decoded)
    return "(%s LIKE '%%.sld')" % path


def sld_sql(alias='r'):
    """Misma clasificación para lecturas, rankings y consolidación histórica."""
    return "(lower(trim(COALESCE({a}.format, ''))) IN ('sld', '{mime}') OR lower(trim(split_part(COALESCE({a}.mimetype, ''), ';', 1))) = '{mime}' OR {url})".format(a=alias, mime=SLD_MIME, url=sld_url_sql(alias + '.url'))


def raw_download_sql(alias='t'):
    """Excluye también URLs históricas cuyo recurso ya no existe."""
    return "(NOT {url} AND NOT EXISTS (SELECT 1 FROM resource sr WHERE sr.id::text = lower(substring({a}.url from '/resource/([0-9a-fA-F-]{{36}})(?:/|$)')) AND {sld}))".format(url=sld_url_sql(alias + '.url'), a=alias, sld=sld_sql('sr'))


def present_resources(resources, views=(), page=1, items_per_page=20,
                      q='', format_filter='', mode='grouped'):
    """Agrupa antes de filtrar/paginar, sin mutar recursos ni vistas CKAN."""
    resources = list(resources)
    slds = {r['id']: r for r in resources if is_sld_resource(r)}
    by_url = {}
    for rid, res in slds.items():
        by_url.setdefault(res.get('url'), []).append(rid)
    related = {}
    ids = {r['id'] for r in resources if r['id'] not in slds}
    for view in views:
        rid = view.get('resource_id')
        if rid not in ids or view.get('view_type') != 'terria_view':
            continue
        config = view.get('config') or {}
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except (ValueError, TypeError):
                continue
        if not isinstance(config, dict):
            continue
        style = config.get('style')
        if not isinstance(style, str) or not style or style == 'NA':
            continue
        matches = by_url.get(style, [])
        sid = matches[0] if len(matches) == 1 else None
        if not sid:
            try:
                match = _RESOURCE_PATH.search(unquote(urlsplit(style).path))
            except ValueError:
                match = None
            if match and match.group(1).lower() in slds:
                sid = match.group(1).lower()
        if sid:
            item = related.setdefault(rid, {}).setdefault(sid, dict(slds[sid], _style_views=[]))
            title = view.get('title')
            if title and title not in item['_style_views']:
                item['_style_views'].append(title)

    attached = {sid for styles in related.values() for sid in styles}
    mode = 'all' if mode == 'all' else 'grouped'
    query, fmt = q.casefold(), format_filter.strip().casefold()

    def matches(res):
        text_match = not query or any(query in str(res.get(k) or '').casefold()
                                      for k in ('name', 'description', 'url'))
        format_match = not fmt or (fmt == 'sld' and is_sld_resource(res)) or str(res.get('format') or '').strip().casefold() == fmt
        return text_match and format_match

    result = []
    for res in resources:
        if mode == 'grouped' and res['id'] in attached:
            continue
        children = list(related.get(res['id'], {}).values()) if mode == 'grouped' else []
        own_match = matches(res)
        child_matches = [child for child in children if matches(child)]
        if not own_match and not child_matches:
            continue
        result.append(dict(res, _style_resources=children if own_match else child_matches,
                           _styles_expanded=bool(q or fmt), _is_sld=is_sld_resource(res)))
    total = len(result)
    items_per_page = max(1, min(int(items_per_page), 100))
    page = max(1, min(int(page), max(1, (total + items_per_page - 1) // items_per_page)))
    formats = {('SLD' if is_sld_resource(r) else str(r.get('format') or '').strip().upper()) for r in resources}
    return {'resources': result[(page - 1) * items_per_page:page * items_per_page],
            'total': total, 'page': page, 'items_per_page': items_per_page,
            'formats': sorted(formats - {''}), 'mode': mode,
            'resource_count': len(resources) - len(slds), 'style_count': len(slds)}
