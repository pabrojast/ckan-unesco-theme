# encoding: utf-8
"""Contribution ranking for Member States and Initiatives.

The score per group combines contribution volume (datasets, documents),
recent activity (recently modified packages + recent news/events) and
average metadata completeness (from Solr, fed by completeness.py).

Heavy aggregation runs offline (``ckan ranking recompute``, see cli.py)
and persists into the ``contribution_score`` table; the web tier only
reads that table through a small TTL cache.
"""

import datetime
import json
import logging
import math
import time

import ckan.model as model
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

WATER_PAGE_TYPES = ('water-news', 'water-events', 'water-publications')

# name -> default weight; overridable via
# ckanext.theme_ejemplo.ranking_weight_<name>
DEFAULT_WEIGHTS = {
    'datasets': 3.0,
    'documents': 2.0,
    'news': 1.0,
    'recent': 2.0,
    'completeness': 2.0,
}

_scores_cache = {}  # entity_type -> {'expires': ts, 'data': {...}}


def _weight(name):
    key = 'ckanext.theme_ejemplo.ranking_weight_' + name
    try:
        return float(toolkit.config.get(key, DEFAULT_WEIGHTS[name]))
    except (TypeError, ValueError):
        return DEFAULT_WEIGHTS[name]


def _cache_ttl():
    try:
        return int(toolkit.config.get(
            'ckanext.theme_ejemplo.ranking_cache_ttl', 300))
    except (TypeError, ValueError):
        return 300


# ── group classification ─────────────────────────────────────────────────────

def _member_state_names():
    """Names of the child groups of 'member-states' (direct DB query)."""
    ms_group = model.Session.query(model.Group).filter(
        model.Group.name == 'member-states',
        model.Group.state == 'active',
    ).first()
    if not ms_group:
        return set()
    rows = (
        model.Session.query(model.Group.name)
        .join(model.Member, model.Member.table_id == model.Group.id)
        .filter(
            model.Member.group_id == ms_group.id,
            model.Member.state == 'active',
            model.Member.table_name == 'group',
            model.Group.state == 'active',
            model.Group.name != 'member-states',
        )
        .all()
    )
    return {r.name for r in rows if r.name}


def _all_groups():
    """[(id, name, title)] for every active CKAN group of type 'group'."""
    rows = (
        model.Session.query(model.Group.id, model.Group.name,
                            model.Group.title)
        .filter(
            model.Group.state == 'active',
            model.Group.is_organization == False,  # noqa: E712
            model.Group.type == 'group',
        )
        .all()
    )
    return [(r.id, r.name, r.title or r.name) for r in rows]


# ── data sources ─────────────────────────────────────────────────────────────

def _facet_counts(fq):
    """{group_name: count} via one package_search facet query."""
    result = toolkit.get_action('package_search')(
        {'ignore_auth': True},
        {
            'q': '*:*',
            'fq': fq,
            'rows': 0,
            'facet': 'true',
            'facet.field': ['groups'],
            'facet.limit': -1,
        },
    )
    items = result.get('search_facets', {}).get('groups', {}).get('items', [])
    return {i['name']: i['count'] for i in items}


def _avg_completeness_by_group():
    """{group_name: avg score 0-100} via a Solr JSON facet.

    Returns {} when the field is not indexed yet (pre Fase 2 reindex) so
    callers treat it as "no data", never as 0.
    """
    try:
        from ckan.lib.search.common import make_connection
        conn = make_connection()
        site_id = toolkit.config.get('ckan.site_id', 'default')
        resp = conn.search(
            '*:*',
            fq=['+site_id:"%s"' % site_id, '+state:active',
                '+dataset_type:(dataset OR documents)'],
            rows=0,
            **{'json.facet': json.dumps({
                'by_group': {
                    'type': 'terms',
                    'field': 'groups',
                    'limit': -1,
                    'facet': {'avg_c': 'avg(metadata_completeness)'},
                }
            })}
        )
        buckets = (resp.raw_response.get('facets', {})
                   .get('by_group', {}).get('buckets', []))
        return {b['val']: b.get('avg_c')
                for b in buckets if b.get('avg_c') is not None}
    except Exception as e:
        log.warning('avg completeness facet unavailable: %s', e)
        return {}


def _page_counts_by_group():
    """News/events/publications (approved) attributed via initiative_groups.

    Returns {group_name: {'total': n, 'recent_90d': n, 'recent_365d': n}}.
    Legacy pages without submission_status count as approved.
    """
    counts = {}
    try:
        from ckanext.pages.db import Page
    except ImportError:
        return counts

    now = datetime.datetime.utcnow()
    try:
        pages = model.Session.query(Page).filter(
            Page.page_type.in_(WATER_PAGE_TYPES)).all()
    except Exception as e:
        log.warning('pages query failed for ranking: %s', e)
        return counts

    for pg in pages:
        status = getattr(pg, 'submission_status', None)
        if status not in (None, '', 'approved'):
            continue
        extras = {}
        if pg.extras:
            try:
                extras = json.loads(pg.extras)
            except (ValueError, TypeError):
                pass
        groups = extras.get('initiative_groups', [])
        if isinstance(groups, str):
            try:
                groups = json.loads(groups)
            except (ValueError, TypeError):
                groups = []
        names = {g.get('name') if isinstance(g, dict) else str(g)
                 for g in groups}
        names.discard(None)
        if not names:
            continue
        age_days = None
        if pg.created:
            age_days = (now - pg.created).days
        for name in names:
            entry = counts.setdefault(
                name, {'total': 0, 'recent_90d': 0, 'recent_365d': 0})
            entry['total'] += 1
            if age_days is not None:
                if age_days <= 90:
                    entry['recent_90d'] += 1
                if age_days <= 365:
                    entry['recent_365d'] += 1
    return counts


# ── scoring ──────────────────────────────────────────────────────────────────

def _score(datasets, documents, news, recent_90d, recent_365d,
           avg_completeness):
    score = (
        _weight('datasets') * math.log1p(datasets)
        + _weight('documents') * math.log1p(documents)
        + _weight('news') * math.log1p(news)
        + _weight('recent') * math.log1p(recent_90d + 0.5 * recent_365d)
    )
    if avg_completeness is not None:
        score += _weight('completeness') * (avg_completeness / 100.0)
    return round(score, 4)


def compute_all_scores():
    """Recompute and persist all contribution scores.

    Returns a summary dict for the CLI.
    """
    from ckanext.theme_ejemplo.model import (
        ContributionScore, init_contribution_scores_db)

    init_contribution_scores_db()

    member_states = _member_state_names()
    groups = _all_groups()

    ds_map = _facet_counts('+dataset_type:dataset')
    doc_map = _facet_counts('+dataset_type:documents')
    r90_map = _facet_counts(
        '+dataset_type:(dataset OR documents)'
        ' +metadata_modified:[NOW-90DAYS TO NOW]')
    r365_map = _facet_counts(
        '+dataset_type:(dataset OR documents)'
        ' +metadata_modified:[NOW-365DAYS TO NOW]')
    avg_map = _avg_completeness_by_group()
    page_map = _page_counts_by_group()

    rows = []
    for group_id, name, title in groups:
        if name == 'member-states':
            continue
        entity = (ContributionScore.ENTITY_MEMBER_STATE
                  if name in member_states
                  else ContributionScore.ENTITY_INITIATIVE)
        pages = page_map.get(name, {})
        datasets = ds_map.get(name, 0)
        documents = doc_map.get(name, 0)
        news = pages.get('total', 0)
        recent_90d = r90_map.get(name, 0) + pages.get('recent_90d', 0)
        recent_365d = r365_map.get(name, 0) + pages.get('recent_365d', 0)
        avg_c = avg_map.get(name)
        rows.append(ContributionScore(
            group_id=group_id,
            group_name=name,
            group_title=title,
            entity_type=entity,
            datasets_count=datasets,
            documents_count=documents,
            news_events_count=news,
            recent_90d=recent_90d,
            recent_365d=recent_365d,
            avg_completeness=avg_c,
            score=_score(datasets, documents, news, recent_90d,
                         recent_365d, avg_c),
        ))

    ContributionScore.replace_all(rows)
    _scores_cache.clear()
    return {
        'computed': len(rows),
        'member_states': sum(
            1 for r in rows
            if r.entity_type == ContributionScore.ENTITY_MEMBER_STATE),
        'initiatives': sum(
            1 for r in rows
            if r.entity_type == ContributionScore.ENTITY_INITIATIVE),
        'with_completeness': sum(
            1 for r in rows if r.avg_completeness is not None),
    }


# ── read side (web tier) ─────────────────────────────────────────────────────

def get_scores_map(entity_type):
    """{group_name: score} from the persisted table, cached a few minutes."""
    ttl = _cache_ttl()
    now = time.time()
    cached = _scores_cache.get(entity_type)
    if ttl > 0 and cached and now < cached['expires']:
        return cached['data']
    data = {}
    try:
        from ckanext.theme_ejemplo.model import ContributionScore
        for row in ContributionScore.get_ranked(entity_type):
            data[row.group_name] = row.score
    except Exception as e:
        log.debug('contribution scores unavailable: %s', e)
    _scores_cache[entity_type] = {'expires': now + ttl, 'data': data}
    return data


def order_by_score(names, entity_type):
    """Sort a list of group names by score desc.

    Groups without a score keep their incoming relative order and go last,
    so the listing degrades to the current behaviour when the job has not
    run yet.
    """
    scores = get_scores_map(entity_type)
    if not scores:
        return list(names)
    return sorted(names, key=lambda n: (n not in scores,
                                        -scores.get(n, 0.0)))


def get_rank_for_group(group_name):
    """{'rank': i, 'total': n, 'score': s} within its entity type, or None."""
    try:
        from ckanext.theme_ejemplo.model import ContributionScore
        row = ContributionScore.get_by_group(group_name)
        if row is None:
            return None
        ranked = ContributionScore.get_ranked(row.entity_type)
        for i, r in enumerate(ranked, start=1):
            if r.group_name == group_name:
                return {'rank': i, 'total': len(ranked), 'score': r.score}
    except Exception as e:
        log.debug('rank lookup failed for %s: %s', group_name, e)
    return None
