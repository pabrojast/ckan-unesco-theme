"""Contratos de aislamiento y concurrencia del despliegue."""
import importlib.util
from pathlib import Path
import json
import pytest

spec = importlib.util.spec_from_file_location('preview_deploy', Path(__file__).with_name('deploy.py'))
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


@pytest.mark.parametrize('image', [
    'pabrojast/ckan-base210@sha256:' + 'a' * 64,
    'ghcr.io/pabrojast/ckan-theme-preview:latest',
    'ghcr.io/other/ckan-theme-preview@sha256:' + 'a' * 64,
])
def test_rejects_other_repositories_and_mutable_tags(image):
    assert not deploy.IMAGE.fullmatch(image)


def test_patch_compares_live_revision_and_changes_only_ckan(monkeypatch):
    calls = []
    monkeypatch.setattr(deploy, 'kube', lambda *args: calls.append(args) or '')
    d = {'metadata': {'resourceVersion': '42', 'annotations': {'keep': 'yes'}}, 'spec': {'template': {'spec': {'containers': [{'name': 'other', 'image': 'unchanged'}, {'name': 'ckan', 'image': 'old'}]}}}}
    deploy.patch(d, 'new', {'preview.dev-wins.com/theme-sha': 'abc'})
    ops = json.loads(calls[0][-1])
    assert ops[0] == {'op': 'test', 'path': '/metadata/resourceVersion', 'value': '42'}
    assert ops[1]['value'] == 'old'
    assert ops[2]['path'] == '/spec/template/spec/containers/1/image'
    assert ops[3]['value']['keep'] == 'yes'


def test_smoke_retries_transient_route_failure(monkeypatch):
    calls = []
    def check(sha):
        calls.append(sha)
        if len(calls) == 1:
            raise OSError('transient ingress connection reset')
    monkeypatch.setattr(deploy, 'smoke_once', check)
    monkeypatch.setattr(deploy.time, 'sleep', lambda _: None)
    deploy.smoke('expected-sha')
    assert calls == ['expected-sha', 'expected-sha']


def test_smoke_persistent_failure_is_not_accepted(monkeypatch):
    ticks = iter([0, 151])
    monkeypatch.setattr(deploy.time, 'monotonic', lambda: next(ticks))
    def fail(_):
        raise RuntimeError('wrong SHA')
    monkeypatch.setattr(deploy, 'smoke_once', fail)
    with pytest.raises(RuntimeError, match='wrong SHA'):
        deploy.smoke('expected-sha')
