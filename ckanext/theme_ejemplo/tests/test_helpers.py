import importlib
import sys
import types


class DummyUser(object):
    is_authenticated = True
    sysadmin = True
    id = 'test-user-id'
    name = 'test-user'


class DummySession(object):
    def __init__(self):
        self.rollback_calls = 0

    def rollback(self):
        self.rollback_calls += 1


class FailingBugTicket(object):
    STATUS_OPEN = 'open'

    @classmethod
    def get_all(cls, **kwargs):
        raise RuntimeError('boom')


def test_get_open_bug_tickets_count_rolls_back_session_on_error(monkeypatch):
    session = DummySession()
    fake_toolkit = types.SimpleNamespace(asbool=bool, config={})
    fake_plugins = types.ModuleType('ckan.plugins')
    fake_plugins.toolkit = fake_toolkit
    fake_core_helpers = types.ModuleType('ckan.lib.helpers')
    fake_lib = types.ModuleType('ckan.lib')
    fake_lib.helpers = fake_core_helpers
    fake_model = types.ModuleType('ckan.model')
    fake_model.Session = session
    fake_common = types.ModuleType('ckan.common')
    fake_common.current_user = DummyUser()
    fake_ckan = types.ModuleType('ckan')
    fake_theme_model = types.ModuleType('ckanext.theme_ejemplo.model')
    fake_theme_model.BugTicket = FailingBugTicket
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

    assert helpers.get_open_bug_tickets_count() == 0
    assert session.rollback_calls == 1
