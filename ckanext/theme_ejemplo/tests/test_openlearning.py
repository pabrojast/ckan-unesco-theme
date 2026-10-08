import importlib
import sys
import types

import requests


API_URL = 'https://openlearning.unesco.org/api/courses/v1/courses/'


def _api_course(course_id, name='Curso', **extra):
    course = {'course_id': course_id, 'name': name, 'pacing': 'self'}
    course.update(extra)
    return course


class FakeResponse(object):
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError('HTTP %d' % self.status_code)

    def json(self):
        return self.payload


class FakeHttp(object):
    """Simula la API: listado por search_term y detalle por course_id."""

    def __init__(self, search_results, details=None, failing_details=()):
        self.search_results = search_results
        self.details = details or {}
        self.failing_details = set(failing_details)
        self.detail_calls = []

    def get(self, url, params=None, timeout=None):
        if url == API_URL:
            return FakeResponse(
                {'results': list(self.search_results), 'pagination': {}})
        course_id = url[len(API_URL):].rstrip('/')
        self.detail_calls.append(course_id)
        if course_id in self.failing_details:
            raise requests.exceptions.ConnectionError('API caída')
        if course_id in self.details:
            return FakeResponse(self.details[course_id])
        return FakeResponse({'developer_message': 'Course not found.'}, 404)


class FakeSession(object):
    def __init__(self, store):
        self.store = store
        self.commits = 0

    def add(self, course):
        self.store[course.course_id] = course

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass


def _load_openlearning(monkeypatch, http):
    store = {}

    class FakeCourse(object):
        TYPE_PERMANENT = u'permanent'
        TYPE_SCHEDULED = u'scheduled'

        def __init__(self, course_id, course_type=u'permanent', **fields):
            self.course_id = course_id
            self.course_type = course_type
            self.course_type_override = False
            self.status = u'pending'
            self.is_available = True
            self.last_seen_at = None
            self.updated_at = None
            for attr, value in fields.items():
                setattr(self, attr, value)

        @classmethod
        def get_by_course_id(cls, course_id):
            return store.get(course_id)

        @classmethod
        def get_not_in(cls, course_ids):
            seen = set(course_ids)
            return [c for cid, c in store.items() if cid not in seen]

    fake_toolkit = types.ModuleType('ckan.plugins.toolkit')
    fake_toolkit.config = {
        'ckanext.theme_ejemplo.openlearning_search_terms': 'water'}
    fake_toolkit.asint = int
    fake_toolkit.ObjectNotFound = type('ObjectNotFound', (Exception,), {})
    fake_toolkit.ValidationError = type('ValidationError', (Exception,), {})

    fake_plugins = types.ModuleType('ckan.plugins')
    fake_plugins.toolkit = fake_toolkit
    fake_meta = types.ModuleType('ckan.model.meta')
    fake_meta.Session = FakeSession(store)
    fake_ckan_model = types.ModuleType('ckan.model')
    fake_ckan_model.meta = fake_meta

    fake_theme_model = types.ModuleType('ckanext.theme_ejemplo.model')
    fake_theme_model.OpenLearningCourse = FakeCourse
    fake_theme_model.init_open_learning_courses_db = lambda: None

    monkeypatch.setitem(sys.modules, 'ckan', types.ModuleType('ckan'))
    monkeypatch.setitem(sys.modules, 'ckan.plugins', fake_plugins)
    monkeypatch.setitem(sys.modules, 'ckan.plugins.toolkit', fake_toolkit)
    monkeypatch.setitem(sys.modules, 'ckan.model', fake_ckan_model)
    monkeypatch.setitem(sys.modules, 'ckan.model.meta', fake_meta)
    monkeypatch.setitem(
        sys.modules, 'ckanext.theme_ejemplo.model', fake_theme_model)
    sys.modules.pop('ckanext.theme_ejemplo.openlearning', None)

    mod = importlib.import_module('ckanext.theme_ejemplo.openlearning')
    monkeypatch.setattr(mod, '_http_session', http)
    return mod, store, fake_toolkit


def test_consecutive_syncs_keep_courses_available(monkeypatch):
    # Regresión: el segundo sync marcaba todos los cursos como no disponibles
    http = FakeHttp([_api_course('c1'), _api_course('c2')])
    mod, store, _ = _load_openlearning(monkeypatch, http)

    first = mod.sync_courses()
    store['c1'].status = u'approved'
    second = mod.sync_courses()

    assert first['created'] == 2
    assert second['updated'] == 2
    assert second['marked_unavailable'] == 0
    assert store['c1'].is_available is True
    assert store['c2'].is_available is True
    assert store['c1'].status == u'approved'
    assert http.detail_calls == []


def test_course_gone_from_api_is_marked_unavailable(monkeypatch):
    http = FakeHttp([_api_course('c1'), _api_course('c2')])
    mod, store, _ = _load_openlearning(monkeypatch, http)
    mod.sync_courses()
    store['c2'].status = u'approved'

    http.search_results = [_api_course('c1')]
    summary = mod.sync_courses()

    assert summary['marked_unavailable'] == 1
    assert store['c2'].is_available is False
    assert store['c2'].status == u'approved'
    assert store['c1'].is_available is True


def test_course_outside_search_terms_stays_available(monkeypatch):
    # Curso agregado a mano: no sale en la búsqueda pero existe por ID
    http = FakeHttp(
        [_api_course('c1')],
        details={'manual': _api_course('manual', name='Nuevo nombre')})
    mod, store, _ = _load_openlearning(monkeypatch, http)
    mod.fetch_and_upsert_course('manual')
    store['manual'].is_available = False

    summary = mod.sync_courses()

    assert summary['marked_unavailable'] == 0
    assert store['manual'].is_available is True
    assert store['manual'].name == 'Nuevo nombre'


def test_hidden_course_is_marked_unavailable(monkeypatch):
    http = FakeHttp([_api_course('c1'), _api_course('c2')])
    mod, store, _ = _load_openlearning(monkeypatch, http)
    mod.sync_courses()

    http.search_results = [_api_course('c1')]
    http.details = {'c2': _api_course('c2', hidden=True)}
    mod.sync_courses()

    assert store['c2'].is_available is False


def test_detail_api_failure_leaves_row_untouched(monkeypatch):
    http = FakeHttp([_api_course('c1'), _api_course('c2')])
    mod, store, _ = _load_openlearning(monkeypatch, http)
    mod.sync_courses()

    http.search_results = [_api_course('c1')]
    http.failing_details = {'c2'}
    summary = mod.sync_courses()

    assert summary['marked_unavailable'] == 0
    assert store['c2'].is_available is True


def test_partial_fetch_never_marks_unavailable(monkeypatch):
    http = FakeHttp([_api_course('c1'), _api_course('c2')])
    mod, store, _ = _load_openlearning(monkeypatch, http)
    mod.sync_courses()

    monkeypatch.setattr(
        mod, '_fetch_all_courses',
        lambda terms: ({'c1': _api_course('c1')}, False))
    summary = mod.sync_courses()

    assert summary['marked_unavailable'] == 0
    assert store['c2'].is_available is True
    assert http.detail_calls == []


def test_fetch_and_upsert_unknown_course_raises_not_found(monkeypatch):
    http = FakeHttp([])
    mod, store, toolkit = _load_openlearning(monkeypatch, http)

    try:
        mod.fetch_and_upsert_course('no-existe')
        raised = False
    except toolkit.ObjectNotFound:
        raised = True

    assert raised
    assert store == {}
