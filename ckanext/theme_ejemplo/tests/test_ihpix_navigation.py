"""Regresiones de enlaces de regreso, filtros y rutas localizadas."""
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode, parse_qs, urlsplit

from jinja2 import Environment, FileSystemLoader
import pytest

from ckanext.theme_ejemplo.ihpix_navigation import breadcrumbs

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'


def url_for(endpoint, **params):
    return '/es/' + endpoint + ('?' + urlencode(params) if params else '')


def trail(name, values=None, args=None):
    return breadcrumbs('theme_ejemplo.' + name, values or {}, args or {}, url_for, lambda s: s)


def test_progress_direct_entry_returns_to_ihpix():
    assert trail('ihpix_progress')[-2][1] == '/es/theme_ejemplo.ihpix'
    assert trail('ihpix')[-2][1] == '/es/home.index'


@pytest.mark.parametrize('scope,value', [('pa', 'PA1'), ('output', '1.1'),
                                       ('flagship', 'friend'), ('ctwg', 'ecohydrology-and-water-quality')])
def test_scoped_progress_keeps_filters_on_parent(scope, value):
    filters = dict(country='Chile', biennium='2024-2025', organization='cazalac', region='Latin America')
    links = trail('ihpix_progress_' + scope, dict(scope=scope, value=value), filters)
    parent = urlsplit(links[-2][1])
    assert parent.path == '/es/theme_ejemplo.ihpix_progress'
    assert parse_qs(parent.query) == {k: [v] for k, v in filters.items()}


@pytest.mark.parametrize('name', ['ihpix_narrative', 'ihpix_presentation'])
def test_reports_return_to_selected_dashboard(name):
    links = trail(name, args=dict(scope='ctwg', value='Ecohydrology and Water Quality', country='Chile'))
    parent = urlsplit(links[-2][1])
    assert parent.path.endswith('ihpix_progress_ctwg')
    assert parse_qs(parent.query) == dict(value=['ecohydrology-and-water-quality'], country=['Chile'])


@pytest.mark.parametrize('name', ['ihpix_workspace_members', 'ihpix_workspace_collaboration'])
def test_nested_workspace_returns_to_detail_then_group_then_list(name):
    links = trail(name, dict(code='1.1'))
    assert links[-2][1] == '/es/theme_ejemplo.ihpix_workspace_detail?code=1.1'
    assert links[-3][1] == '/es/theme_ejemplo.ihpix_group?slug=oetwg-1'
    assert links[-4][1] == '/es/theme_ejemplo.ihpix_workspaces'


def test_plan_direct_entry_returns_to_plan_and_group():
    links = trail('ihpix_group_plan',dict(slug='oetwg-4',id='plan'))
    assert links[-2][1] == '/es/theme_ejemplo.ihpix_group?slug=oetwg-4&tab=plan'
    assert links[-3][1] == '/es/theme_ejemplo.ihpix_group?slug=oetwg-4'


def test_edit_and_collaboration_return_to_reports():
    links = trail('ihpix_report_collaboration', dict(id='report-id'))
    assert links[-2][1].endswith('ihpix_report_edit?id=report-id')
    assert links[-3][1].endswith('ihpix_my_reports')


def test_organization_report_returns_to_filtered_progress():
    links = trail('ihpix_narrative', args=dict(scope='organization', value='cazalac', country='Chile'))
    parent = urlsplit(links[-2][1])
    assert parent.path.endswith('ihpix_progress')
    assert parse_qs(parent.query) == dict(organization=['cazalac'], country=['Chile'])


def test_entity_and_admin_pages_return_to_ihpix():
    for name, values in [('group_ihpix', {'name': 'chile'}), ('organization_ihpix', {'name': 'cazalac'}),
                         ('user_ihpix', {'id': 'reporter'}), ('ihpix_workspaces_admin', {})]:
        links = trail(name, values)
        assert links[-2][1] == '/es/theme_ejemplo.ihpix'
        assert links[-1][1].startswith('/es/theme_ejemplo.' + name)


def test_navigation_is_absent_outside_ihpix():
    for endpoint in ('home.index', 'dataset.read', 'theme_ejemplo.member_states', None):
        assert breadcrumbs(endpoint, {}, {}, url_for, str) == []


def render_navigation(endpoint):
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    env.globals.update(
        _=lambda text: text,
        h=SimpleNamespace(url_for_static=lambda path: path),
        request=SimpleNamespace(endpoint=endpoint),
    )
    template = env.get_template('ihpix/snippets/navigation.html')
    return template.render(trail=[('Home', '/'), ('IHP IX', '/ihpix')])


def test_landing_navigation_uses_the_site_container():
    html = render_navigation('theme_ejemplo.ihpix')
    assert '<div class="container">' in html
    assert 'ix-navigation--site' in html


def test_child_navigation_keeps_its_own_width():
    html = render_navigation('theme_ejemplo.ihpix_progress')
    assert 'class="container"' not in html
    assert 'ix-navigation--site' not in html
