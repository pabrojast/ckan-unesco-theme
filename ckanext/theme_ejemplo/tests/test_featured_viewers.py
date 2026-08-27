"""Tests for the featured viewers homepage helpers.

Los datos viven en ckanext-pages; aquí sólo se prueba el pegamento: el gate de
disponibilidad, el fallback a los más recientes y que un fallo no deje la
sesión ORM abortada.
"""
import importlib
import sys
import types


class DummySession(object):
    def __init__(self):
        self.rollback_calls = 0

    def rollback(self):
        self.rollback_calls += 1


def _load_helpers(monkeypatch, config=None, get_action=None):
    """Carga helpers.py con los módulos de CKAN sustituidos por stubs.

    Mismo enfoque que test_helpers.py: evita necesitar un CKAN instalado.
    """
    session = DummySession()

    def _asbool(value):
        if isinstance(value, str):
            return value.strip().lower() in ('true', 'yes', 'on', '1')
        return bool(value)

    fake_toolkit = types.SimpleNamespace(
        asbool=_asbool,
        config=config if config is not None else {},
    )
    if get_action is not None:
        fake_toolkit.get_action = get_action

    fake_plugins = types.ModuleType('ckan.plugins')
    fake_plugins.toolkit = fake_toolkit
    fake_core_helpers = types.ModuleType('ckan.lib.helpers')
    fake_lib = types.ModuleType('ckan.lib')
    fake_lib.helpers = fake_core_helpers
    fake_model = types.ModuleType('ckan.model')
    fake_model.Session = session
    fake_common = types.ModuleType('ckan.common')
    fake_common.current_user = None
    fake_ckan = types.ModuleType('ckan')
    fake_theme_model = types.ModuleType('ckanext.theme_ejemplo.model')
    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda value: value

    monkeypatch.setitem(sys.modules, 'ckan', fake_ckan)
    monkeypatch.setitem(sys.modules, 'ckan.plugins', fake_plugins)
    monkeypatch.setitem(sys.modules, 'ckan.lib', fake_lib)
    monkeypatch.setitem(sys.modules, 'ckan.lib.helpers', fake_core_helpers)
    monkeypatch.setitem(sys.modules, 'ckan.model', fake_model)
    monkeypatch.setitem(sys.modules, 'ckan.common', fake_common)
    monkeypatch.setitem(sys.modules, 'ckanext.theme_ejemplo.model', fake_theme_model)
    monkeypatch.setitem(sys.modules, 'sqlalchemy', fake_sqlalchemy)
    sys.modules.pop('ckanext.theme_ejemplo.helpers', None)

    helpers = importlib.import_module('ckanext.theme_ejemplo.helpers')
    # El TTL de la home cachea entre tests; lo desactivamos por defecto.
    helpers._featured_viewers_cache.update(
        {'data': None, 'expires': 0, 'limit': None})
    return helpers, session


def _recording_get_action(responses):
    """Devuelve (get_action, calls) donde `responses` se consume en orden."""
    calls = []
    queue = list(responses)

    def get_action(name):
        if name != 'featured_viewer_list':
            raise KeyError(name)

        def action(context, data_dict):
            calls.append((context, data_dict))
            result = queue.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        return action

    return get_action, calls


ENABLED = {'ckanext.featured_viewers.enabled': 'true',
           'ckanext.theme_ejemplo.home_cache_ttl': '0'}


# ── featured_viewers_available ────────────────────────────────────────

def test_available_false_when_flag_off(monkeypatch):
    helpers, _ = _load_helpers(
        monkeypatch,
        config={'ckanext.featured_viewers.enabled': 'false'},
        get_action=lambda name: (lambda ctx, dd: {}),
    )
    assert helpers.featured_viewers_available() is False


def test_available_false_when_action_missing(monkeypatch):
    def get_action(name):
        raise KeyError(name)

    helpers, _ = _load_helpers(
        monkeypatch,
        config={'ckanext.featured_viewers.enabled': 'true'},
        get_action=get_action,
    )
    assert helpers.featured_viewers_available() is False


def test_available_true_when_flag_on_and_action_registered(monkeypatch):
    helpers, _ = _load_helpers(
        monkeypatch,
        config={'ckanext.featured_viewers.enabled': 'true'},
        get_action=lambda name: (lambda ctx, dd: {}),
    )
    assert helpers.featured_viewers_available() is True


# ── get_featured_viewers ──────────────────────────────────────────────

def test_returns_empty_when_module_unavailable(monkeypatch):
    helpers, session = _load_helpers(
        monkeypatch,
        config={'ckanext.featured_viewers.enabled': 'false'},
        get_action=lambda name: (lambda ctx, dd: {}),
    )
    assert helpers.get_featured_viewers() == []
    assert session.rollback_calls == 0


def test_uses_featured_viewers_when_present(monkeypatch):
    featured = {'viewers': [{'id': 'a', 'order_index': 0, 'created_at': '2026-01-01'}]}
    get_action, calls = _recording_get_action([featured])
    helpers, _ = _load_helpers(monkeypatch, config=dict(ENABLED),
                               get_action=get_action)

    result = helpers.get_featured_viewers()

    assert [v['id'] for v in result] == ['a']
    # Una sola llamada: no se toca el fallback si ya hay destacados.
    assert len(calls) == 1
    assert calls[0][1] == {'is_featured': True, 'status': 'published',
                           'sort': 'order', 'limit': 6}


def test_falls_back_to_most_recent_when_nothing_featured(monkeypatch):
    recent = {'viewers': [{'id': 'b', 'order_index': 0, 'created_at': '2026-02-01'}]}
    get_action, calls = _recording_get_action([{'viewers': []}, recent])
    helpers, _ = _load_helpers(monkeypatch, config=dict(ENABLED),
                               get_action=get_action)

    result = helpers.get_featured_viewers()

    assert [v['id'] for v in result] == ['b']
    assert len(calls) == 2
    assert calls[1][1] == {'status': 'published', 'sort': 'recent', 'limit': 6}


def test_queries_run_with_an_anonymous_context(monkeypatch):
    """El contexto sin usuario es lo que hace la caché compartida segura."""
    get_action, calls = _recording_get_action([{'viewers': [{'id': 'a'}]}])
    helpers, _ = _load_helpers(monkeypatch, config=dict(ENABLED),
                               get_action=get_action)

    helpers.get_featured_viewers()

    context = calls[0][0]
    assert context['user'] == ''
    assert context['auth_user_obj'] is None


def test_orders_by_order_index_then_created_at(monkeypatch):
    featured = {'viewers': [
        {'id': 'c', 'order_index': 2, 'created_at': '2026-01-01'},
        {'id': 'a', 'order_index': 0, 'created_at': '2026-03-01'},
        {'id': 'b', 'order_index': 0, 'created_at': '2026-01-01'},
    ]}
    get_action, _ = _recording_get_action([featured])
    helpers, _ = _load_helpers(monkeypatch, config=dict(ENABLED),
                               get_action=get_action)

    result = helpers.get_featured_viewers()

    assert [v['id'] for v in result] == ['b', 'a', 'c']


def test_respects_the_limit(monkeypatch):
    featured = {'viewers': [{'id': str(i), 'order_index': i} for i in range(10)]}
    get_action, calls = _recording_get_action([featured])
    helpers, _ = _load_helpers(monkeypatch, config=dict(ENABLED),
                               get_action=get_action)

    assert len(helpers.get_featured_viewers(3)) == 3
    assert calls[0][1]['limit'] == 3


def test_rolls_back_session_and_returns_empty_on_error(monkeypatch):
    """La acción consulta Postgres: sin rollback se rompe el resto de la home."""
    get_action, _ = _recording_get_action([RuntimeError('boom')])
    helpers, session = _load_helpers(monkeypatch, config=dict(ENABLED),
                                     get_action=get_action)

    assert helpers.get_featured_viewers() == []
    assert session.rollback_calls == 1


def test_caches_between_calls_when_ttl_is_positive(monkeypatch):
    featured = {'viewers': [{'id': 'a', 'order_index': 0}]}
    get_action, calls = _recording_get_action([featured])
    helpers, _ = _load_helpers(
        monkeypatch,
        config={'ckanext.featured_viewers.enabled': 'true',
                'ckanext.theme_ejemplo.home_cache_ttl': '300'},
        get_action=get_action,
    )

    first = helpers.get_featured_viewers()
    second = helpers.get_featured_viewers()

    assert first == second
    # La segunda llamada sale de caché; si no, `queue.pop(0)` habría reventado.
    assert len(calls) == 1
