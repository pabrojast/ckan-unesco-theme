# -*- coding: utf-8 -*-
"""Qué páginas de listado no deben indexar los buscadores.

Los crawlers recorren cada combinación de filtros de los listados con facetas
(``/dataset``, ``/documents``, ``/learning``, ``/group/<id>``,
``/organization/<id>``). ``templates/home/robots.txt`` les pide no entrar en
esas URL; aquí se decide cuáles llevan además
``<meta name="robots" content="noindex, follow">`` (``templates/base.html``).

Sin dependencias de CKAN ni de Flask, para testearlo sin entorno.
"""
import re

# Página más profunda de un listado que todavía se deja indexar.
MAX_INDEXED_PAGE = 50

# Parámetros que la búsqueda del core no trata como filtro (ckan/views/
# dataset.py): la consulta, el orden y la página, más los que empiezan por
# ``_`` (estado de la interfaz) o por ``ext_`` (extras como ``ext_bbox``).
NON_FILTER_PARAMS = frozenset(('q', 'sort', 'page'))
NON_FILTER_PREFIXES = ('_', 'ext_')

# Orden de los valores de una faceta: ``_groups_sort``, ``_res_format_sort``.
_FACET_SORT = re.compile(r'^_.+_sort$')

# Listados con facetas: el catálogo de cada tipo de dataset y la página de un
# grupo u organización, con o sin barra final. ``/dataset/<id>`` no lo es.
_LISTING_PATH = re.compile(
    r'^/(?:dataset|documents|learning|(?:group|organization)/[^/]+)/?$')

# Prefijo de idioma (``/es``, ``/pt_BR``, ``/zh_Hans_CN``). CKAN lo quita antes
# de que Flask vea la ruta; se tolera por si llega la URL pública.
_LOCALE_PREFIX = re.compile(r'^/[a-z]{2}(?:_[A-Za-z]{2,4}){0,2}(?=/|$)')


def is_listing_path(path):
    """True si ``path`` es un listado con facetas, con o sin prefijo de idioma."""
    path = str(path or '')
    return bool(_LISTING_PATH.match(path)
                or _LISTING_PATH.match(_LOCALE_PREFIX.sub('', path, count=1)))


def _pairs(args):
    """Pares ``(nombre, valor)`` de la query, con los parámetros repetidos.

    Acepta el ``MultiDict`` de werkzeug (``request.args``), un ``dict`` cuyos
    valores pueden ser listas, o una lista de pares.
    """
    if not args:
        return []
    items = getattr(args, 'items', None)
    if items is None:
        return [(name, value) for name, value in args]
    try:
        return list(items(multi=True))
    except TypeError:
        pairs = []
        for name, value in items():
            values = value if isinstance(value, (list, tuple)) else [value]
            pairs.extend((name, single) for single in values)
        return pairs


def _page_number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def listing_noindex(args, path=None):
    """True si la página debe llevar ``noindex, follow``.

    Con ``path`` solo aplica a los listados con facetas; sin ``path`` decide
    solo por los parámetros. Es ``True`` cuando la query trae:

    - el orden de alguna faceta (``_<faceta>_sort``), con cualquier valor;
    - ``page`` mayor que ``MAX_INDEXED_PAGE``;
    - dos o más filtros. Cuenta cada par nombre=valor con valor no vacío,
      así que ``groups=a&groups=b`` son dos. No cuentan ``q``, ``sort``,
      ``page`` ni los que empiezan por ``_`` o ``ext_``.

    Un listado sin filtros o con uno solo se indexa.
    """
    if path is not None and not is_listing_path(path):
        return False
    filters = 0
    for name, value in _pairs(args):
        name = str(name)
        value = '' if value is None else str(value).strip()
        if _FACET_SORT.match(name):
            return True
        if name == 'page':
            if _page_number(value) > MAX_INDEXED_PAGE:
                return True
            continue
        if (not value or name in NON_FILTER_PARAMS
                or name.startswith(NON_FILTER_PREFIXES)):
            continue
        filters += 1
    return filters >= 2
