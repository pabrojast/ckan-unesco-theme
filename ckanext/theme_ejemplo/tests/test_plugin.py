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
