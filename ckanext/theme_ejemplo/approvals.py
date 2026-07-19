# encoding: utf-8
"""Aggregated review queues for the header approvals bell.

Collapses the previous ~8 per-queue header badges (each one hitting the
DB on EVERY authenticated request) into a single cached aggregate:

- counts are cached in Redis (in-process fallback) for a short TTL,
- global sysadmin queues share one cache entry across all sysadmins,
- user-scoped counts (membership requests, own bug tickets) get a
  per-user entry,
- labels/urls are resolved at render time so the request locale applies
  (only counts are cached).

Every underlying helper keeps doing its own permission check (e.g. the
pages helpers return 0 for non-sysadmins); this module never widens
visibility, it only avoids repeated queries.
"""

import json
import logging
import time

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

REDIS_PREFIX = 'theme_ejemplo:approvals:'

# Queue definitions. 'helper' is looked up in toolkit.h (so queues from
# plugins that are not loaded silently disappear). 'scope' controls the
# cache entry: 'sysadmin' entries are shared, 'user' entries are per-user.
# 'route' is resolved with url_for at render time; 'url' is a literal.
QUEUE_DEFS = [
    {'id': 'water', 'icon': 'fa-tint', 'scope': 'sysadmin',
     'helper': 'get_pending_water_count',
     'route': 'pages.water_admin_dashboard'},
    {'id': 'oss', 'icon': 'fa-code', 'scope': 'sysadmin',
     'helper': 'get_pending_oss_count',
     'route': 'pages.open_source_admin_dashboard'},
    {'id': 'stories', 'icon': 'fa-book', 'scope': 'sysadmin',
     'helper': 'get_pending_stories_count',
     'route': 'data_stories.pending_review'},
    {'id': 'initiatives', 'icon': 'fa-flag', 'scope': 'sysadmin',
     'helper': 'get_pending_initiative_requests_count',
     'route': 'theme_ejemplo.initiative_requests_admin'},
    {'id': 'users', 'icon': 'fa-user-plus', 'scope': 'sysadmin',
     'helper': 'colab_pending_count',
     'route': 'colab.show_admin'},
    {'id': 'devices', 'icon': 'fa-microchip', 'scope': 'sysadmin',
     'helper': 'tb_pending_count',
     'route': 'thingsboard.admin_dashboard'},
    {'id': 'citizen_science', 'icon': 'fa-flask', 'scope': 'sysadmin',
     'helper': 'csunesco_pending_count',
     'url': '/cs-admin'},
    {'id': 'membership', 'icon': 'fa-users', 'scope': 'user',
     'helper': 'get_pending_membership_requests_count',
     'route': 'theme_ejemplo.membership_requests_overview'},
    {'id': 'data_access', 'icon': 'fa-key', 'scope': 'user',
     'helper': 'datashare_pending_access_count',
     'url': '/datashare/requests'},
    {'id': 'bugs', 'icon': 'fa-bug', 'scope': 'user',
     'helper': 'get_open_bug_tickets_count',
     'route': 'theme_ejemplo.bug_tickets_list'},
]


def _labels():
    """id -> translated label, evaluated per request so the locale applies."""
    _ = toolkit._
    return {
        'water': _('Water Family submissions'),
        'oss': _('Open-source tools'),
        'stories': _('Data stories'),
        'initiatives': _('Initiative requests'),
        'users': _('User registrations'),
        'devices': _('Device approvals'),
        'citizen_science': _('Citizen science'),
        'membership': _('Membership requests'),
        'data_access': _('Data access requests'),
        'bugs': _('Bug tickets'),
    }


_redis_client = None
_redis_init_attempted = False
_local_cache = {}  # key -> (expires_ts, counts_dict)


def _get_redis():
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    try:
        from ckan.lib.redis import connect_to_redis
        client = connect_to_redis()
        client.ping()
        _redis_client = client
    except Exception as e:
        _redis_client = None
        log.warning('approvals cache: Redis unavailable, using '
                    'in-process fallback: %s', e)
    return _redis_client


def _cache_ttl():
    try:
        return int(toolkit.config.get(
            'ckanext.theme_ejemplo.approvals_cache_ttl', 120))
    except (TypeError, ValueError):
        return 120


def _cached_counts(cache_key, compute):
    """Return {queue_id: count} from cache, computing on miss."""
    ttl = _cache_ttl()
    if ttl <= 0:
        return compute()
    full_key = REDIS_PREFIX + cache_key
    redis = _get_redis()
    if redis is not None:
        try:
            raw = redis.get(full_key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            log.debug('approvals cache read failed: %s', e)
        counts = compute()
        try:
            redis.setex(full_key, ttl, json.dumps(counts))
        except Exception as e:
            log.debug('approvals cache write failed: %s', e)
        return counts
    # in-process fallback
    now = time.time()
    cached = _local_cache.get(full_key)
    if cached and now < cached[0]:
        return cached[1]
    counts = compute()
    _local_cache[full_key] = (now + ttl, counts)
    return counts


def _compute_counts(scope):
    """Run the underlying helpers for one scope. {queue_id: count}."""
    h = toolkit.h
    counts = {}
    for queue in QUEUE_DEFS:
        if queue['scope'] != scope:
            continue
        helper = queue['helper']
        if helper not in h:
            continue
        try:
            counts[queue['id']] = int(h[helper]() or 0)
        except Exception as e:
            log.debug('approvals count %s failed: %s', queue['id'], e)
            counts[queue['id']] = 0
    return counts


def invalidate(user_id=None):
    """Best-effort cache invalidation after processing a queue item."""
    redis = _get_redis()
    keys = [REDIS_PREFIX + 'sysadmin']
    if user_id:
        keys.append(REDIS_PREFIX + 'user:%s' % user_id)
    for key in keys:
        _local_cache.pop(key, None)
        if redis is not None:
            try:
                redis.delete(key)
            except Exception:
                pass


def get_review_queues():
    """Visible review queues for the current user.

    Returns [{'id', 'label', 'count', 'url', 'icon'}, ...]. Sysadmins see
    every global queue (count 0 included — the dropdown doubles as
    navigation); other users only see their user-scoped queues when the
    count is positive.
    """
    try:
        userobj = getattr(toolkit.g, 'userobj', None)
    except (TypeError, RuntimeError, AttributeError):
        return []
    if not userobj:
        return []
    is_sysadmin = bool(getattr(userobj, 'sysadmin', False))

    counts = {}
    if is_sysadmin:
        counts.update(_cached_counts('sysadmin',
                                     lambda: _compute_counts('sysadmin')))
    counts.update(_cached_counts('user:%s' % userobj.id,
                                 lambda: _compute_counts('user')))

    h = toolkit.h
    labels = _labels()
    queues = []
    for queue in QUEUE_DEFS:
        qid = queue['id']
        if qid not in counts:
            continue
        count = counts[qid]
        if queue['scope'] == 'sysadmin' and not is_sysadmin:
            continue
        if queue['scope'] == 'user' and not is_sysadmin and count <= 0:
            continue
        if 'route' in queue:
            try:
                url = h.url_for(queue['route'])
            except Exception:
                continue
        else:
            url = queue['url']
        queues.append({
            'id': qid,
            'label': labels.get(qid, qid),
            'count': count,
            'url': url,
            'icon': queue['icon'],
        })
    return queues


def get_review_queues_total():
    return sum(q['count'] for q in get_review_queues())
