# -*- coding: utf-8 -*-
"""Búsqueda de organizaciones/grupos insensible al orden de las palabras.

El core (``_group_or_org_list``) filtra con ``ILIKE '%<frase completa>%'``:
"water quality" encuentra resultados y "quality water" no. Aquí se tokeniza la
búsqueda y se exige que TODOS los tokens aparezcan (en cualquier orden), sin
distinguir mayúsculas ni acentos, y se ordena por relevancia.

La lógica de scoring está portada de ``ckanext-colab/lib/org_search.py`` (se
copia en vez de importarla porque colab es un plugin opcional).

Las funciones de matching son puras (no importan CKAN) para poder testearlas
sin entorno; sólo ``get_entity_index`` toca la base de datos.
"""
import logging
import re
import threading
import time
import unicodedata

log = logging.getLogger(__name__)

# Segundos que vive el índice de entidades en memoria (por proceso).
INDEX_TTL = 300
# Mínimo de caracteres para ofrecer sugerencias mientras se escribe.
MIN_SUGGEST_CHARS = 2

# Caracteres con significado en la sintaxis de consultas de Solr/Lucene.
_SOLR_SPECIAL_RE = re.compile(r'[+\-!(){}\[\]^"~*?:\\/&|]')

_index_lock = threading.Lock()
_index_cache = {'expires': 0.0, 'items': []}


def normalize_text(value):
    """Pliega mayúsculas y acentos: 'Université' coincide con 'universite'."""
    if not value:
        return ''
    decomposed = unicodedata.normalize('NFKD', str(value))
    stripped = ''.join(
        ch for ch in decomposed if unicodedata.category(ch) != 'Mn'
    )
    stripped = stripped.lower()
    stripped = re.sub(r'[^\w]+', ' ', stripped, flags=re.UNICODE)
    stripped = stripped.replace('_', ' ')
    return re.sub(r'\s+', ' ', stripped).strip()


def match_score(query, title, name='', extra=''):
    """Puntaje de relevancia, o None si no coincide. Más alto es mejor.

    Todos los tokens de la búsqueda deben aparecer en título, slug o ``extra``
    (descripción), en cualquier orden. Título exacto gana, luego prefijo,
    inicio de palabra, subcadena, coincidencias en el slug y, al final, las que
    sólo aparecen en la descripción.
    """
    q = normalize_text(query)
    if not q:
        return None

    title = normalize_text(title)
    name = normalize_text(name)
    extra = normalize_text(extra)
    main = (title + ' ' + name).strip()
    haystack = (main + ' ' + extra).strip()
    if not haystack:
        return None

    tokens = q.split()
    if not all(token in haystack for token in tokens):
        return None

    title_words = title.split()
    name_words = name.split()

    if title == q:
        score = 1000
    elif title.startswith(q):
        score = 900
    elif any(word.startswith(q) for word in title_words):
        score = 800
    elif q in title:
        score = 700
    elif name == q or name.startswith(q):
        score = 600
    elif any(word.startswith(q) for word in name_words):
        score = 550
    elif q in name:
        score = 500
    elif all(token in main for token in tokens):
        # Todos los tokens en título/slug pero en otro orden o separados.
        word_starts = sum(
            1 for token in tokens
            if any(word.startswith(token) for word in title_words)
        )
        score = 200 + (word_starts * 50)
    else:
        # Algún token sólo aparece en la descripción.
        score = 100

    # A igual calidad de coincidencia, preferir el nombre oficial más corto.
    score -= min(len(title), 80)
    return score


def filter_ranked(items, query, limit=None, include_description=True):
    """Devuelve los items que coinciden, ordenados por puntaje y luego título.

    Cada item es un dict con ``name``, ``title`` y opcionalmente
    ``description``. Con ``include_description=False`` sólo cuentan título y
    slug: en el desplegable de sugerencias un resultado cuyo título no contiene
    lo escrito desconcierta.
    """
    scored = []
    for item in items or []:
        score = match_score(
            query,
            item.get('title') or item.get('display_name') or '',
            item.get('name') or '',
            (item.get('description') or '') if include_description else '',
        )
        if score is None:
            continue
        scored.append((score, item))

    scored.sort(key=lambda pair: (
        -pair[0],
        (pair[1].get('title') or pair[1].get('name') or '').lower(),
    ))
    results = [item for _, item in scored]
    if limit is not None:
        return results[:limit]
    return results


def escape_solr(query):
    """Neutraliza la sintaxis de Solr en texto escrito a medias por el usuario
    (una comilla sin cerrar o un ':' harían fallar la consulta de sugerencias).
    """
    cleaned = _SOLR_SPECIAL_RE.sub(' ', query or '')
    return re.sub(r'\s+', ' ', cleaned).strip()


def filter_by_tokens(sa_query, q, columns):
    """Aplica a una consulta SQLAlchemy un AND de ``ILIKE '%token%'`` por cada
    palabra de ``q``, cada una contra cualquiera de ``columns``.

    Para tablas grandes (usuarios) donde no conviene cargar todo en memoria:
    "perez juan" encuentra a "Juan Pérez"... salvo por el acento, que SQL no
    pliega sin la extensión ``unaccent``.
    """
    from sqlalchemy import or_
    for token in (q or '').split():
        escaped = (token.replace('\\', '\\\\')
                   .replace('%', '\\%').replace('_', '\\_'))
        pattern = u'%{0}%'.format(escaped)
        sa_query = sa_query.filter(
            or_(*[col.ilike(pattern, escape='\\') for col in columns]))
    return sa_query


def get_entity_index():
    """Índice liviano de organizaciones y grupos activos, cacheado en memoria.

    Una sola consulta SQL; son unos cientos de filas, así que filtrar en Python
    es más barato que un ILIKE por token y permite plegar acentos sin depender
    de la extensión ``unaccent`` de PostgreSQL.
    """
    now = time.time()
    if _index_cache['expires'] > now:
        return _index_cache['items']

    with _index_lock:
        if _index_cache['expires'] > now:
            return _index_cache['items']
        import ckan.model as model
        try:
            rows = (
                model.Session.query(
                    model.Group.name,
                    model.Group.title,
                    model.Group.description,
                    model.Group.type,
                    model.Group.is_organization,
                )
                .filter(model.Group.state == 'active')
                .all()
            )
        except Exception as e:
            log.error('Error construyendo el índice de búsqueda de entidades: %s', e)
            return _index_cache['items']
        _index_cache['items'] = [
            {
                'name': r.name,
                'title': r.title or r.name,
                'description': r.description or '',
                'type': r.type,
                'is_organization': bool(r.is_organization),
            }
            for r in rows if r.name
        ]
        _index_cache['expires'] = now + INDEX_TTL
        return _index_cache['items']


def clear_entity_index():
    """Invalida el índice (tests, o tras crear/editar una entidad)."""
    with _index_lock:
        _index_cache['expires'] = 0.0


def search_entities(query, is_organization=None, ckan_type=None, allowed=None,
                    excluded=None, limit=None, include_description=True):
    """Entidades del índice que coinciden con ``query``, por relevancia.

    is_organization / ckan_type: filtros sobre el tipo de entidad.
    allowed / excluded: colecciones de nombres para acotar (p. ej. los member
    states) sin que este módulo tenga que conocer esa clasificación.
    """
    items = get_entity_index()
    if is_organization is not None:
        items = [i for i in items if i['is_organization'] == is_organization]
    if ckan_type:
        items = [i for i in items if i['type'] == ckan_type]
    if allowed is not None:
        allowed = set(allowed)
        items = [i for i in items if i['name'] in allowed]
    if excluded:
        excluded = set(excluded)
        items = [i for i in items if i['name'] not in excluded]
    return filter_ranked(items, query, limit=limit,
                         include_description=include_description)


def search_entity_names(query, **kwargs):
    """Igual que ``search_entities`` pero devuelve sólo los nombres (slugs)."""
    return [i['name'] for i in search_entities(query, **kwargs)]
