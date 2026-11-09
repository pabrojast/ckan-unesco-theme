"""La lectura del tema respeta las asociaciones y publicación de Pages."""

import json

import pytest
from ckan import model


@pytest.mark.usefixtures('with_plugins')
@pytest.mark.ckan_config('ckan.plugins', 'pages')
@pytest.mark.ckan_config('ckanext.data_stories.enabled', False)
@pytest.mark.parametrize('page_type', ['water-news', 'water-events'])
def test_initiative_reader_public_legacy_content(
        reset_db, migrate_db_for, page_type):
    from ckanext.pages.db import Page
    from ckanext.theme_ejemplo.controller import _get_pages_by_initiative

    reset_db()
    migrate_db_for('pages')
    for name, status, private in [
        ('visible', 'approved', False), ('private', 'approved', True),
        ('draft', 'draft', False), ('pending', 'pending', False),
        ('rejected', 'rejected', False),
    ]:
        model.Session.add(Page(
            revisions={},
            name=name, title=name, page_type=page_type,
            private=private, submission_status=status,
            extras=json.dumps({'initiative_groups': json.dumps(json.dumps(
                [{'name': 'be-resilient'}]))})))
    model.Session.commit()

    pages = _get_pages_by_initiative('be-resilient', page_type)
    assert [page['name'] for page in pages] == ['visible']
    assert _get_pages_by_initiative('other-initiative', page_type) == []


@pytest.mark.usefixtures('with_plugins')
@pytest.mark.ckan_config('ckan.plugins', 'pages')
@pytest.mark.ckan_config('ckanext.data_stories.enabled', False)
@pytest.mark.parametrize('kind', ['news', 'events'])
def test_initiative_tabs_provide_pages_navigation_context(
        app, reset_db, migrate_db_for, monkeypatch, kind):
    from ckan.common import c
    from ckan.tests import factories
    from ckanext.theme_ejemplo import controller

    reset_db()
    migrate_db_for('pages')
    group = factories.Group(name='be-resilient')

    def render(template, **context):
        assert c.group_dict['id'] == group['id']
        assert context['group_dict'] == c.group_dict
        assert context['group_type'] == 'group'
        assert template == 'group/%s.html' % kind
        return 'rendered'

    monkeypatch.setattr(controller, 'render_template', render)
    with app.flask_app.test_request_context():
        view = getattr(controller.MyLogica, 'group_' + kind)
        assert view(group['name']) == 'rendered'
