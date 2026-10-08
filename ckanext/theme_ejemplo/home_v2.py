# -*- coding: utf-8 -*-
"""Home page v2 (redesign) for IHP-WINS.

Added by Jorgen Van Der Biest. Everything for the new home page lives in its
own files so it can be reviewed, switched on and removed separately:

- this module (template helpers)
- templates/home/home_v2.html
- public/css/home-v2.css and public/js/home-v2.js
- public/home_v2/ (hero video, poster and logos)

The page reuses the data helpers the current home page already uses
(site statistics, recently added, popular datasets, featured viewers, news,
events, publications, courses). The helpers below only add what the current
home page does not show yet (rapid response events, data stories) and the
switch between the current and the new design.

Settings (ckan.ini or environment variables):

    ckanext.theme_ejemplo.home_design = classic | v2     (default: classic)
    ckanext.theme_ejemplo.home_design_switch = true      (default: false)

With the switch on, ?home=v2 or ?home=classic previews either design for
that one request, so the new page can be checked on the dev site before it
becomes the default.
"""
import logging

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

_DESIGNS = ('classic', 'v2')


def _config_design():
    value = (toolkit.config.get('ckanext.theme_ejemplo.home_design') or 'classic')
    value = str(value).strip().lower()
    return value if value in _DESIGNS else 'classic'


def home_v2_enabled():
    """True when the new home page should be shown for this request."""
    design = _config_design()
    try:
        if toolkit.asbool(toolkit.config.get(
                'ckanext.theme_ejemplo.home_design_switch', False)):
            asked = (toolkit.request.args.get('home') or '').strip().lower()
            if asked in _DESIGNS:
                design = asked
    except Exception:
        # No request context (CLI, tests): keep the configured design
        pass
    return design == 'v2'


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
        'home_v2_enabled': home_v2_enabled,
        'home_v2_rapid_response': home_v2_rapid_response,
        'home_v2_data_stories': home_v2_data_stories,
        'home_v2_short_number': home_v2_short_number,
    }
