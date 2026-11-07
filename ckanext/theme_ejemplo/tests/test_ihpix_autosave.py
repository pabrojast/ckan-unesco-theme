"""Identidad del borrador y reconocimiento de reintentos tras perder el acuse."""
import datetime
import json
import uuid

import pytest

from ckanext.theme_ejemplo import ihpix_autosave as D


def test_retry_identity_is_stable_and_scoped_to_user():
    client = str(uuid.uuid4())
    first = D.draft_identity('author', client)
    assert first == D.draft_identity('author', client.upper())
    assert first != D.draft_identity('another-author', client)
    assert first != D.draft_identity('author', str(uuid.uuid4()))
    assert 0 <= first[1] < 2 ** 63


@pytest.mark.parametrize('client', [None, '', 'not-a-uuid'])
def test_missing_or_invalid_client_identity_is_rejected(client):
    with pytest.raises((ValueError, TypeError)):
        D.draft_identity('author', client)


def test_equivalence_normalizes_dates_and_json_but_keeps_answers_distinct():
    stored = {'date': datetime.date(2026, 11, 6), 'countries': '["Chile", "Kenya"]', 'title': 'Draft', 'revision': 4}
    assert D.equivalent(stored, {'date': '2026-11-06', 'countries': ['Chile', 'Kenya'], 'title': 'Draft'})
    assert not D.equivalent(stored, {'title': 'Changed'})
    assert not D.equivalent(stored, {'countries': ['Kenya']})
    assert not D.equivalent({'answer': False}, {'answer': None})
    assert D.equivalent({'title': '[unfinished'}, {'title': '[unfinished'})


def test_link_retry_ignores_generated_ids_but_checks_content():
    link = dict(link_type='other', target_kind='url', title='Source', url='https://example.org/report')
    stored = [dict(link, id='server-id')]
    assert D.equivalent_links(stored, json.dumps([link, link]))
    assert not D.equivalent_links(stored, [dict(link, title='Changed')])
    assert not D.equivalent_links(stored, [])


@pytest.mark.parametrize('links', ['invalid json', '{}', '[{"url":"javascript:alert(1)"}]'])
def test_invalid_links_are_never_acknowledged_as_saved(links):
    assert not D.equivalent_links([], links)
