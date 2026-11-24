"""Qué listados se indexan: la regla del meta robots y las de robots.txt.

Suite pura: no importa CKAN. La plantilla se lee como texto y el bloque
``meta`` se renderiza con Jinja a secas.
"""
import re
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl

import pytest
from jinja2 import DictLoader, Environment

from ckanext.theme_ejemplo.crawl_policy import is_listing_path, listing_noindex

try:  # request.args es un MultiDict; sin werkzeug vale la lista de pares
    from werkzeug.datastructures import MultiDict
except ImportError:
    MultiDict = list

ROOT = Path(__file__).resolve().parents[1]
META = '<meta name="robots" content="noindex, follow" />'
# URL real que recorrían los crawlers.
CRAWLED = 'groups=montenegro&res_format=SHP&page=17&_groups_sort=name'


def args(query):
    return parse_qsl(query, keep_blank_values=True)


# ─── Parámetros ───────────────────────────────────────────────────────────


@pytest.mark.parametrize('query', [
    'groups=montenegro&res_format=SHP',
    'groups=montenegro&groups=serbia',
    'groups=a&tags=b&res_format=CSV&page=2',
    'q=water&groups=a&tags=b',
    CRAWLED,
    '_groups_sort=name',
    '_res_format_sort=count',
    '_groups_sort=',
    'groups=a&_groups_sort=name',
    'page=51',
    'groups=a&page=1000',
    'q=water&page=51',
])
def test_noindex(query):
    assert listing_noindex(args(query)) is True


@pytest.mark.parametrize('query', [
    '',
    'groups=montenegro',
    'res_format=SHP',
    'q=water',
    'q=water&sort=score+desc&page=3',
    'q=water&groups=montenegro',
    'groups=montenegro&page=2',
    'groups=montenegro&page=50',
    'groups=montenegro&sort=title_string+asc',
    'groups=montenegro&ext_bbox=1,2,3,4&ext_prev_extent=5,6,7,8',
    'groups=montenegro&_groups_limit=0',
    'groups=montenegro&_tags_limit=0&_res_format_limit=0',
    'groups=montenegro&tags=',
    'groups=&tags=',
    'page=50',
    'page=1',
    'page=',
    'page=abc',
    'page=-3',
    'sort=metadata_modified+desc',
    '_sort=name',
    'ext_bbox=1,2,3,4&ext_prev_extent=5,6,7,8',
])
def test_stays_indexable(query):
    assert listing_noindex(args(query)) is False


def test_accepts_werkzeug_multidict():
    multidict = pytest.importorskip('werkzeug.datastructures').MultiDict
    assert listing_noindex(multidict(args('groups=a&groups=b'))) is True
    assert listing_noindex(multidict(args('groups=a&page=2'))) is False
    assert listing_noindex(multidict(args(CRAWLED))) is True


def test_accepts_plain_mappings_and_empty_input():
    assert listing_noindex({'groups': ['a', 'b']}) is True
    assert listing_noindex({'groups': 'a', 'tags': 'b'}) is True
    assert listing_noindex({'groups': 'a', 'page': 2}) is False
    assert listing_noindex({'page': 51}) is True
    assert listing_noindex({'groups': None, 'tags': 'b'}) is False
    assert listing_noindex(None) is False
    assert listing_noindex({}) is False


# ─── Rutas ────────────────────────────────────────────────────────────────


LISTINGS = [
    '/dataset', '/dataset/', '/documents', '/documents/', '/learning',
    '/learning/', '/group/montenegro', '/group/montenegro/',
    '/organization/unesco', '/organization/unesco/', '/es/dataset/',
    '/fr/documents', '/pt_BR/group/montenegro', '/zh_Hans_CN/learning/',
]
NOT_LISTINGS = [
    '/', '/es', '/es/', '/about', '/dataset/boreholes-kenya-rural-focus',
    '/es/dataset/boreholes-kenya-rural-focus',
    '/dataset/boreholes-kenya-rural-focus/resource/1234',
    '/documents/some-report', '/learning/some-course', '/group',
    '/organization', '/es/group/', '/group/montenegro/members',
    '/organization/unesco/people', '/user/someone', '/api/3/action/package_search',
    '/datasets', '/dataset-old', '', None,
]


@pytest.mark.parametrize('path', LISTINGS)
def test_listing_paths(path):
    assert is_listing_path(path) is True
    assert listing_noindex(args(CRAWLED), path) is True
    assert listing_noindex(args('groups=montenegro'), path) is False
    assert listing_noindex(args(''), path) is False


@pytest.mark.parametrize('path', NOT_LISTINGS)
def test_other_pages_never_get_noindex(path):
    assert is_listing_path(path) is False
    assert listing_noindex(args(CRAWLED), '' if path is None else path) is False


# ─── Etiqueta meta en base.html ───────────────────────────────────────────


def render_meta(query, path):
    """Renderiza el bloque ``meta`` real de base.html sobre un padre mínimo."""
    source = (ROOT / 'templates/base.html').read_text(encoding='utf-8')
    block = re.search(r'{% block meta %}.*?{% endblock %}', source, re.S).group(0)
    env = Environment(autoescape=True, loader=DictLoader({
        'core': '{% block meta %}<meta charset="utf-8" />{% endblock %}',
        'theme': '{% extends "core" %}' + block,
    }))
    return env.get_template('theme').render(
        h=SimpleNamespace(theme_ejemplo_listing_noindex=listing_noindex),
        request=SimpleNamespace(args=MultiDict(args(query)), path=path))


@pytest.mark.parametrize('query,path', [
    (CRAWLED, '/documents/'),
    ('groups=a&tags=b', '/dataset/'),
    ('_groups_sort=name', '/group/montenegro'),
    ('page=51', '/organization/unesco'),
    ('groups=a&tags=b', '/learning/'),
])
def test_meta_tag_on_filtered_listings(query, path):
    html = render_meta(query, path)
    assert html.count(META) == 1
    assert '<meta charset="utf-8" />' in html


@pytest.mark.parametrize('query,path', [
    ('', '/dataset/'),
    ('groups=montenegro', '/dataset/'),
    ('groups=montenegro&page=2', '/documents/'),
    ('q=water&sort=score+desc', '/learning/'),
    ('', '/group/montenegro'),
    ('res_format=SHP', '/organization/unesco'),
    ('', '/dataset/boreholes-kenya-rural-focus'),
    (CRAWLED, '/dataset/boreholes-kenya-rural-focus'),
    (CRAWLED, '/'),
])
def test_no_meta_tag_elsewhere(query, path):
    html = render_meta(query, path)
    assert 'robots' not in html
    assert '<meta charset="utf-8" />' in html


def test_helper_used_by_base_html_is_registered():
    """Un helper desconocido tumba todas las páginas: base.html lo llama."""
    name = 'theme_ejemplo_listing_noindex'
    assert 'h.%s(request.args, request.path)' % name in (
        ROOT / 'templates/base.html').read_text(encoding='utf-8')
    assert "'%s': helpers.listing_noindex" % name in (
        ROOT / 'plugin.py').read_text(encoding='utf-8')
    assert 'from .crawl_policy import listing_noindex' in (
        ROOT / 'helpers.py').read_text(encoding='utf-8')


# ─── robots.txt ───────────────────────────────────────────────────────────


ROBOTS = ROOT / 'templates/home/robots.txt'
# Reglas del core 2.10 (ckan/templates/home/robots.txt), que llegan por super().
CORE_RULES = ['/dataset/rate/', '/revision/', '/dataset/*/history', '/api/']


def theme_rules():
    return re.findall(r'^Disallow: (\S+)$', ROBOTS.read_text(encoding='utf-8'), re.M)


def crawlable(url):
    """Coincidencia de Google y Bing: prefijo, ``*`` comodín y ``$`` final.

    Aquí no hay reglas ``Allow``, así que basta una coincidencia para vetar.
    """
    for rule in CORE_RULES + theme_rules():
        pattern = '.*'.join(re.escape(part) for part in rule.rstrip('$').split('*'))
        if re.match(pattern + ('$' if rule.endswith('$') else ''), url):
            return False
    return True


DISALLOWED = [
    '/documents/?' + CRAWLED,
    '/dataset/?_groups_sort=name',
    '/dataset?_groups_sort=count',
    '/es/dataset/?_res_format_sort=name',
    '/dataset/?groups=montenegro&_groups_sort=name',
    '/organization/unesco?_tags_sort=count',
    '/dataset?groups=montenegro&res_format=SHP',
    '/dataset/?groups=montenegro&res_format=SHP',
    '/documents?groups=montenegro&res_format=PDF',
    '/documents/?groups=montenegro&res_format=PDF',
    '/learning?level=basic&language=es',
    '/learning/?level=basic&language=es',
    '/group/montenegro?res_format=SHP&tags=water',
    '/group/montenegro/?res_format=SHP&tags=water',
    '/organization/unesco?res_format=SHP&tags=water',
    '/es/dataset?groups=montenegro&res_format=SHP',
    '/es/dataset/?groups=montenegro&res_format=SHP',
    '/fr/documents?groups=montenegro&res_format=PDF',
    '/fr/documents/?groups=montenegro&res_format=PDF',
    '/es/learning?level=basic&language=es',
    '/es/learning/?level=basic&language=es',
    '/pt_BR/group/montenegro?res_format=SHP&tags=water',
    '/zh_Hans_CN/organization/unesco?res_format=SHP&tags=water',
    '/dataset/rate/5',
    '/dataset/boreholes-kenya-rural-focus/history',
    '/api/3/action/package_search?q=water',
]
CRAWLABLE = [
    '/', '/es/', '/about', '/dataset', '/dataset/', '/es/dataset/',
    '/dataset/?groups=montenegro',
    '/dataset?res_format=SHP',
    '/es/dataset/?groups=montenegro',
    '/dataset/?page=2',
    '/dataset/?q=water',
    '/dataset/?sort=title_string+asc',
    '/documents/', '/documents/?groups=montenegro',
    '/learning/', '/es/learning/?level=basic',
    '/group/montenegro', '/group/montenegro?res_format=SHP',
    '/es/group/montenegro?res_format=SHP',
    '/organization/unesco', '/organization/unesco?page=3',
    '/dataset/boreholes-kenya-rural-focus',
    '/es/dataset/boreholes-kenya-rural-focus',
    '/dataset/boreholes-kenya-rural-focus/resource/1234',
    '/dataset/boreholes-kenya-rural-focus?activity_id=1&x=2',
    '/documents/some-report',
    '/group', '/organization', '/memberstates',
]


@pytest.mark.parametrize('url', DISALLOWED)
def test_robots_disallows(url):
    assert crawlable(url) is False


@pytest.mark.parametrize('url', CRAWLABLE)
def test_robots_keeps_crawlable(url):
    assert crawlable(url) is True


def test_robots_template_keeps_core_rules_and_plain_syntax():
    text = ROBOTS.read_text(encoding='utf-8')
    assert text.startswith('{% ckan_extends %}')
    block = re.search(r'{% block all_user_agents -%}\n(.*?)\n{%- endblock %}', text, re.S).group(1)
    lines = block.split('\n')
    assert lines[0] == '{{ super() }}'
    # Sin líneas en blanco: hay parsers que cierran el grupo en la primera.
    assert all(line.startswith(('# ', 'Disallow: /')) for line in lines[1:])
    rules = theme_rules()
    assert len(rules) == len(set(rules)) == 18
    # Solo los comodines que entienden Google y Bing.
    assert all(re.fullmatch(r'/[A-Za-z_/*?&=]*', rule) for rule in rules)
