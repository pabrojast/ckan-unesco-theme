"""
Tests for plugin.py.

Tests are written using the pytest library (https://docs.pytest.org), and you
should read the testing guidelines in the CKAN docs:
https://docs.ckan.org/en/2.9/contributing/testing.html

To write tests for your extension you should install the pytest-ckan package:

    pip install pytest-ckan

This will allow you to use CKAN specific fixtures on your tests.

For instance, if your test involves database access you can use `clean_db` to
reset the database:

    import pytest

    from ckan.tests import factories

    @pytest.mark.usefixtures("clean_db")
    def test_some_action():

        dataset = factories.Dataset()

        # ...

For functional tests that involve requests to the application, you can use the
`app` fixture:

    from ckan.plugins import toolkit

    def test_some_endpoint(app):

        url = toolkit.url_for('myblueprint.some_endpoint')

        response = app.get(url)

        assert response.status_code == 200


To temporary patch the CKAN configuration for the duration of a test you can use:

    import pytest

    @pytest.mark.ckan_config("ckanext.myext.some_key", "some_value")
    def test_some_action():
        pass
"""
import pytest

pytest.importorskip('ckan')

import ckanext.theme_ejemplo.plugin as plugin


def test_plugin():
    assert plugin is not None


def test_initiatives_request_resolves_to_form_not_dynamic(app):
    """Regresión: /initiatives/request debe resolver al endpoint del formulario,
    NO a la ruta dinámica /initiatives/<name> (que causaría el bucle de redirects)."""
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    endpoint, _args = adapter.match('/initiatives/request', method='GET')
    assert endpoint == 'theme_ejemplo.request_initiative'


def test_group_request_redirects_to_initiatives_request(app):
    """Regresión: /group/request debe dar 301 a /initiatives/request y cerrar
    la cadena (sin bucle)."""
    resp = app.get('/group/request', follow_redirects=False)
    assert resp.status_code == 301
    assert '/initiatives/request' in resp.headers['Location']


def test_initiatives_request_does_not_redirect_to_group_request(app):
    """Regresión del bucle: GET /initiatives/request NO debe redirigir a /group/request."""
    resp = app.get('/initiatives/request', follow_redirects=False)
    location = resp.headers.get('Location', '') or ''
    assert '/group/request' not in location


def test_featured_viewers_admin_routes_are_registered(app):
    """Las rutas del panel se registran SIEMPRE, con el flag encendido o no.

    Así `h.url_for('theme_ejemplo.featured_viewers_admin')` en header.html
    nunca puede lanzar BuildError; el gate de disponibilidad vive en la vista.
    """
    adapter = app.flask_app.url_map.bind('test.ckan.net')

    endpoint, _args = adapter.match('/ckan-admin/featured-viewers', method='GET')
    assert endpoint == 'theme_ejemplo.featured_viewers_admin'

    endpoint, _args = adapter.match('/ckan-admin/featured-viewers/search', method='GET')
    assert endpoint == 'theme_ejemplo.featured_viewers_search'

    for path, expected in (
            ('/ckan-admin/featured-viewers/add', 'featured_viewers_add'),
            ('/ckan-admin/featured-viewers/remove', 'featured_viewers_remove'),
            ('/ckan-admin/featured-viewers/reorder', 'featured_viewers_reorder'),
    ):
        endpoint, _args = adapter.match(path, method='POST')
        assert endpoint == 'theme_ejemplo.' + expected


def test_featured_viewers_admin_is_forbidden_for_anonymous(app):
    """Regresión: el panel es sólo para sysadmins."""
    resp = app.get('/ckan-admin/featured-viewers', follow_redirects=False)
    assert resp.status_code in (302, 403)


def test_search_suggest_route_is_registered(app):
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    endpoint, _args = adapter.match('/api/theme/suggest', method='GET')
    assert endpoint == 'theme_ejemplo.search_suggest'


def test_search_suggest_ignores_too_short_queries(app):
    resp = app.get('/api/theme/suggest?q=a&scope=all')
    assert resp.status_code == 200
    assert resp.json['groups'] == []


def test_search_suggest_falls_back_to_all_on_unknown_scope(app):
    resp = app.get('/api/theme/suggest?q=&scope=nope')
    assert resp.json['scope'] == 'all'


def test_partial_match_adds_ngram_fields_to_qf():
    params = {'q': 'hidro'}
    plugin.ThemeEjemploPlugin._enable_partial_match(params)
    assert 'title_ngram' in params['qf']
    # conserva los campos y boosts del core
    assert params['qf'].startswith('name^4 title^4 tags^2 groups^2 text')


def test_partial_match_leaves_explicit_qf_and_field_queries_alone():
    params = {'q': 'hidro', 'qf': 'title'}
    plugin.ThemeEjemploPlugin._enable_partial_match(params)
    assert params['qf'] == 'title'

    for q in ('', '*:*', 'title:hidro'):
        params = {'q': q}
        plugin.ThemeEjemploPlugin._enable_partial_match(params)
        assert 'qf' not in params


# ── IHP-IX reporting (fase i) ──────────────────────────────────────────────

def test_ihpix_report_routes_are_registered(app):
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    for path, method, expected in (
            ('/ihpix/report', 'GET', 'ihpix_report'),
            ('/ihpix/report', 'POST', 'ihpix_report'),
            ('/ihpix/report/abc-123/edit', 'GET', 'ihpix_report_edit'),
            ('/ihpix/report/abc-123/edit', 'POST', 'ihpix_report_edit'),
            ('/ihpix/report/abc-123/delete', 'POST', 'ihpix_report_delete_view'),
            ('/ihpix/my-reports', 'GET', 'ihpix_my_reports'),
            ('/user/someone/ihpix', 'GET', 'user_ihpix'),
    ):
        endpoint, _args = adapter.match(path, method=method)
        assert endpoint == 'theme_ejemplo.' + expected, path


def test_ihpix_my_reports_requires_login(app):
    resp = app.get('/ihpix/my-reports', follow_redirects=False)
    assert resp.status_code in (302, 403)
    location = resp.headers.get('Location', '') or ''
    if resp.status_code == 302:
        assert '/user/login' in location


def test_ihpix_report_edit_requires_login(app):
    resp = app.get('/ihpix/report/abc-123/edit', follow_redirects=False)
    assert resp.status_code in (302, 403)


def test_ihpix_report_form_is_public(app):
    resp = app.get('/ihpix/report')
    assert resp.status_code == 200


# ── IHP-IX descubribilidad (fase iii) ──────────────────────────────────────

def test_ihpix_browse_routes_are_registered(app):
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    for path, expected in (
            ('/ihpix/outputs/1.1', 'ihpix_output_detail'),
            ('/ihpix/priority-area/PA3', 'ihpix_priority_area'),
            ('/ihpix/contributors', 'ihpix_contributors'),
    ):
        endpoint, _args = adapter.match(path, method='GET')
        assert endpoint == 'theme_ejemplo.' + expected, path
    endpoint, _args = adapter.match('/ckan-admin/ihpix/recompute-summary', method='POST')
    assert endpoint == 'theme_ejemplo.ihpix_recompute_summary_view'


def test_ihpix_browse_pages_require_login(app):
    for path in ('/ihpix/outputs', '/ihpix/dashboard', '/ihpix/outputs/1.1',
                 '/ihpix/priority-area/PA1', '/ihpix/contributors'):
        resp = app.get(path, follow_redirects=False)
        assert resp.status_code in (302, 403), path
        if resp.status_code == 302:
            assert '/user/login' in (resp.headers.get('Location') or ''), path


def test_ihpix_landing_is_public(app):
    resp = app.get('/ihpix')
    assert resp.status_code == 200
    assert b'ihpix-stats-initial' in resp.data


# ── IHP-IX working groups (fase iv) ────────────────────────────────────────

def test_ihpix_workspace_routes_are_registered(app):
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    for path, method, expected in (
            ('/ihpix/workspaces', 'GET', 'ihpix_workspaces'),
            ('/ihpix/workspaces/1.1', 'GET', 'ihpix_workspace_detail'),
            ('/ihpix/workspaces/1.1/join', 'POST', 'ihpix_workspace_join'),
            ('/ihpix/workspaces/1.1/leave', 'POST', 'ihpix_workspace_leave'),
            ('/ihpix/workspaces/1.1/members', 'GET', 'ihpix_workspace_members'),
            ('/ihpix/workspaces/1.1/members/process', 'POST', 'ihpix_workspace_member_process_view'),
            ('/ckan-admin/ihpix/workspaces', 'GET', 'ihpix_workspaces_admin'),
            ('/ckan-admin/ihpix/workspaces/update', 'POST', 'ihpix_workspaces_admin_update'),
    ):
        endpoint, _args = adapter.match(path, method=method)
        assert endpoint == 'theme_ejemplo.' + expected, path


def test_ihpix_workspaces_require_login(app):
    for path in ('/ihpix/workspaces', '/ihpix/workspaces/1.1', '/ihpix/workspaces/1.1/members'):
        resp = app.get(path, follow_redirects=False)
        assert resp.status_code in (302, 403), path
    resp = app.get('/ckan-admin/ihpix/workspaces', follow_redirects=False)
    assert resp.status_code in (302, 403)


# ── IHP-IX kit de formularios (fase A) ─────────────────────────────────────

def test_ihpix_markdown_preview_route_is_registered(app):
    adapter = app.flask_app.url_map.bind('test.ckan.net')
    endpoint, _args = adapter.match('/ihpix/markdown-preview', method='POST')
    assert endpoint == 'theme_ejemplo.ihpix_markdown_preview'


def test_ihpix_markdown_preview_requires_login(app):
    resp = app.post('/ihpix/markdown-preview', data={'text': '**bold**'})
    assert resp.status_code in (302, 403)


def test_ihpix_report_form_loads_forms_kit(app):
    resp = app.get('/ihpix/report')
    assert resp.status_code == 200
    assert b'ihpix-forms-i18n' in resp.data
    assert b'/css/ihpix-forms.css' in resp.data
