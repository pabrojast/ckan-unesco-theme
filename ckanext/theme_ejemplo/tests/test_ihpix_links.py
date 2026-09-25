# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_links` (adjuntos de reportes IHP-IX)."""
import datetime
import json

import pytest

from ckanext.theme_ejemplo import ihpix_links as L


def test_parse_links_json_tolerates_empty_values():
    assert L.parse_links_json(None) == []
    assert L.parse_links_json('') == []
    assert L.parse_links_json('[]') == []
    assert L.parse_links_json([]) == []


def test_parse_links_json_rejects_invalid_json_and_non_lists():
    with pytest.raises(L.LinkValidationError):
        L.parse_links_json('{not json')
    with pytest.raises(L.LinkValidationError):
        L.parse_links_json('{"a": 1}')


def test_parse_links_json_ignores_non_dict_items():
    items = L.parse_links_json(json.dumps([{'title': 'x'}, 'junk', 3]))
    assert items == [{'title': 'x'}]


def test_validate_manual_url_link():
    link = L.validate_link({
        'link_type': 'webinar', 'title': 'Webinar on MAR',
        'url': 'https://example.org/webinar', 'event_date': '2025-05-06',
    })
    assert link['target_kind'] == 'url'
    assert link['event_date'] == datetime.date(2025, 5, 6)
    assert link['id'] == ''


def test_validate_requires_title_and_http_url_for_manual_links():
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'other', 'url': 'ftp://x'})
    assert set(exc.value.errors) >= {'title', 'url'}


def test_validate_package_link_needs_target_id():
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'publication', 'target_kind': 'package',
                         'title': 'Doc'})
    assert 'target_id' in exc.value.errors


def test_type_kind_coherence():
    # Un evento no puede apuntar a un package, ni una publicación a una page
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'event', 'target_kind': 'package',
                         'target_id': 'abc', 'title': 'x'})
    assert 'target_kind' in exc.value.errors
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'publication', 'target_kind': 'page',
                         'target_id': 'abc', 'title': 'x'})
    assert 'target_kind' in exc.value.errors


def test_unknown_type_rejected():
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'podcast', 'title': 'x',
                         'url': 'https://x.org'})
    assert 'link_type' in exc.value.errors


def test_invalid_event_date():
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'event', 'title': 'x',
                         'url': 'https://x.org', 'event_date': '06/05/2025'})
    assert 'event_date' in exc.value.errors


def test_link_public_url_by_kind():
    assert L.link_public_url({'target_kind': 'package', 'target_id': 'p1',
                              'link_type': 'publication'}) == '/documents/p1'
    assert L.link_public_url({'target_kind': 'package', 'target_id': 'p2',
                              'link_type': 'dataset'}) == '/dataset/p2'
    assert L.link_public_url({'target_kind': 'page', 'target_id': 'my-event',
                              'link_type': 'event'}) == '/water-events/my-event'
    assert L.link_public_url({'target_kind': 'url', 'url': 'https://x.org',
                              'link_type': 'other'}) == 'https://x.org'


def test_dedupe_key_distinguishes_objects_and_urls():
    a = {'target_kind': 'package', 'target_id': 'p1'}
    b = {'target_kind': 'package', 'target_id': 'p1', 'link_type': 'dataset'}
    c = {'target_kind': 'url', 'url': 'https://X.org/'}
    d = {'target_kind': 'url', 'url': 'https://x.org/'}
    assert L.dedupe_key(a) == L.dedupe_key(b)
    assert L.dedupe_key(c) == L.dedupe_key(d)
    assert L.dedupe_key(a) != L.dedupe_key(c)


def test_search_kind_covers_all_types():
    assert set(L.SEARCH_KIND_FOR_TYPE) == set(L.LINK_TYPES)
    assert set(L.ALLOWED_KINDS) == set(L.LINK_TYPES)
    assert set(L.TYPE_LABELS) == set(L.LINK_TYPES)


def test_link_errors_carry_translatable_details():
    with pytest.raises(L.LinkValidationError) as exc:
        L.validate_link({'link_type': 'other', 'url': 'ftp://x', 'title': 't' * 301})
    err = exc.value
    assert set(err.errors) == set(err.details)
    for field, (key, params) in err.details.items():
        assert key in L.MESSAGES
        assert err.errors[field] == L.MESSAGES[key].format(**params)


def test_course_link_type_and_url():
    values = L.validate_link({'link_type': 'course', 'target_kind': 'course',
                              'target_id': 'course-v1:UNESCO+IHP01+2025',
                              'title': 'Groundwater basics'})
    assert values['target_kind'] == 'course'
    assert L.link_public_url(values) == \
        'https://openlearning.unesco.org/courses/course-v1:UNESCO+IHP01+2025/about'
    # una URL guardada explícitamente manda
    values['url'] = 'https://example.org/mirror'
    assert L.link_public_url(values) == 'https://example.org/mirror'
    # un curso no puede apuntar a un package
    with pytest.raises(L.LinkValidationError):
        L.validate_link({'link_type': 'course', 'target_kind': 'package',
                         'target_id': 'x', 'title': 't'})
    assert L.SEARCH_KIND_FOR_TYPE['course'] == 'course'
    assert set(L.TYPE_ICONS) == set(L.LINK_TYPES) == set(L.TYPE_LABELS)


def test_parse_course_id():
    assert L.parse_course_id('https://openlearning.unesco.org/courses/course-v1:UNESCO+IHP01+2025/about') == \
        'course-v1:UNESCO+IHP01+2025'
    assert L.parse_course_id('course-v1:UNESCO+IHP01+2025/') == 'course-v1:UNESCO+IHP01+2025'
    assert L.parse_course_id('https://openlearning.unesco.org/program/ihp') == ''
    assert L.parse_course_id('') == ''
