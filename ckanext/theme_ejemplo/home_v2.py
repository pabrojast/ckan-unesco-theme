# -*- coding: utf-8 -*-
"""Home page v2 (redesign) for IHP-WINS.

Added by Jorgen Van Der Biest. Everything for the home page design lives in
its own files so it can be reviewed and maintained separately:

- this module (template helpers)
- templates/home/home_v2.html (rendered by templates/home/index.html)
- public/css/home-v2.css and public/js/home-v2.js
- public/home_v2/ (hero video, poster and logos)

The page reuses the data helpers the previous home page used (site
statistics, recently added, popular datasets, featured viewers, news, events,
publications, courses). The helpers below only add what the previous home
page did not show (rapid response events, data stories).
"""
import logging

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)


def _anonymous_context():
    # Same result for every visitor, so drafts never leak onto the home page
    return {'user': '', 'auth_user_obj': None, 'ignore_auth': True}


def home_v2_rapid_response(limit=4):
    """Latest published rapid response pages (ckanext-pages), or []."""
    try:
        pages = toolkit.get_action('ckanext_pages_list')(
            _anonymous_context(),
            {'order_publish_date': True, 'private': False,
             'page_type': 'rapid-response'}) or []
    except Exception as e:  # extension or page type not available
        log.debug('home_v2: rapid response not available: %s', e)
        return []
    return [p for p in pages if p.get('name')][:limit]


def home_v2_data_stories(limit=3):
    """Latest published data stories (ckanext-pages data stories), or []."""
    try:
        result = toolkit.get_action('data_story_list')(
            _anonymous_context(),
            {'status': 'published', 'sort': 'recent', 'limit': limit}) or {}
    except Exception as e:  # data stories not enabled
        log.debug('home_v2: data stories not available: %s', e)
        return []
    stories = result.get('stories') if isinstance(result, dict) else result
    return [s for s in (stories or []) if s.get('slug')][:limit]


def home_v2_short_number(value):
    """1234 -> '1.2k', 135448 -> '135.4k', 12 -> '12'."""
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return '0'
    for limit, suffix in ((1e6, 'M'), (1e3, 'k')):
        if n >= limit:
            return ('%.1f' % (n / limit)).rstrip('0').rstrip('.') + suffix
    return '%d' % n


def get_helpers():
    return {
        'home_v2_rapid_response': home_v2_rapid_response,
        'home_v2_data_stories': home_v2_data_stories,
        'home_v2_short_number': home_v2_short_number,
    }
