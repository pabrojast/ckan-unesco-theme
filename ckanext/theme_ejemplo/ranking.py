# encoding: utf-8
"""Contribution ranking for Member States, Initiatives and Organizations.

The score per entity combines contribution volume (datasets, documents),
recent activity (recently modified packages + recent news/events), reach
(page views of its datasets) and average metadata completeness (from Solr,
fed by completeness.py).

Heavy aggregation runs offline (``ckan ranking recompute``, see cli.py)
and persists into the ``contribution_score`` table; the web tier only
reads that table through a small TTL cache.

Groups and organizations live in the same CKAN ``group`` table and share a
single name space, so ``group_name`` identifies a row unambiguously for all
three entity types. What differs is where each signal comes from: groups
facet on the Solr field ``groups`` and attribute news via the
``initiative_groups`` extra; organizations facet on ``organization`` and
attribute news via ``Page.ihp_organization``.
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
    'views': 1.5,
}

_scores_cache = {}  # entity_type -> {'expires': ts, 'data': {...}}
_rank_cache = {'expires': 0.0, 'data': {}}  # group_name -> rank dict


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


def _all_orgs():
    """[(id, name, title)] for every active CKAN organization."""
    rows = (
        model.Session.query(model.Group.id, model.Group.name,
                            model.Group.title)
        .filter(
            model.Group.state == 'active',
            model.Group.is_organization == True,  # noqa: E712
        )
        .all()
    )
    return [(r.id, r.name, r.title or r.name) for r in rows]


# ── data sources ─────────────────────────────────────────────────────────────

def _facet_counts(fq, field='groups'):
    """{name: count} via one package_search facet query.

    ``field`` is the Solr facet field: ``groups`` for groups/member states,
    ``organization`` for organizations.
    """
    result = toolkit.get_action('package_search')(
        {'ignore_auth': True},
        {
            'q': '*:*',
            'fq': fq,
            'rows': 0,
            'facet': 'true',
            'facet.field': [field],
            'facet.limit': -1,
        },
    )
    items = result.get('search_facets', {}).get(field, {}).get('items', [])
    return {i['name']: i['count'] for i in items}


def _avg_completeness_by_group(field='groups'):
    """{name: avg score 0-100} via a Solr JSON facet.

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
                    'field': field,
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


# Vistas acumuladas de los datasets de cada grupo/organización. Sale de las
# tablas que llena `ckan pageviews flush`; si aún no existen (portal recién
# desplegado) devolvemos {} y el score simplemente no suma por este eje.
_VIEWS_BY_GROUP_SQL = """
    SELECT g.name AS name,
           COALESCE(SUM(s.total_views), 0) AS total,
           COALESCE(SUM(s.recent_views), 0) AS recent
    FROM tracking_dataset_stats s
    JOIN package p ON p.name = s.dataset_name AND p.state = 'active'
    JOIN member m ON m.table_id = p.id
                 AND m.table_name = 'package'
                 AND m.state = 'active'
    JOIN "group" g ON g.id = m.group_id
                  AND g.state = 'active'
                  AND g.is_organization = false
    GROUP BY g.name
"""

_VIEWS_BY_ORG_SQL = """
    SELECT g.name AS name,
           COALESCE(SUM(s.total_views), 0) AS total,
           COALESCE(SUM(s.recent_views), 0) AS recent
    FROM tracking_dataset_stats s
    JOIN package p ON p.name = s.dataset_name AND p.state = 'active'
    JOIN "group" g ON g.id = p.owner_org
                  AND g.state = 'active'
                  AND g.is_organization = true
    GROUP BY g.name
"""


def _views_by(sql):
    """{name: {'total': n, 'recent': n}} from the pageview tracking tables."""
    from sqlalchemy import text
    counts = {}
    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT to_regclass('tracking_dataset_stats')")).fetchone()
            if not exists or exists[0] is None:
                return counts
            for row in conn.execute(text(sql)):
                counts[row[0]] = {'total': int(row[1] or 0),
                                  'recent': int(row[2] or 0)}
    except Exception as e:
        log.warning('view rollup unavailable for ranking: %s', e)
    return counts


def _blank_page_entry():
    return {'total': 0, 'recent_90d': 0, 'recent_365d': 0}


def _page_counts():
    """News/events/publications (approved), attributed to groups and orgs.

    Returns ``(by_group_name, by_org_id)``, each
    ``{key: {'total': n, 'recent_90d': n, 'recent_365d': n}}``.

    A page reaches a group through the ``initiative_groups`` extra and an
    organization through the ``ihp_organization`` column, which stores the
    organization *id* (see ckanext-pages actions.py:460). The two are
    independent: the same page can count for both.

    Legacy pages without submission_status count as approved.
    """
    by_group, by_org = {}, {}
    try:
        from ckanext.pages.db import Page
    except ImportError:
        return by_group, by_org

    now = datetime.datetime.utcnow()
    try:
        pages = model.Session.query(Page).filter(
            Page.page_type.in_(WATER_PAGE_TYPES)).all()
    except Exception as e:
        log.warning('pages query failed for ranking: %s', e)
        return by_group, by_org

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
        org_id = getattr(pg, 'ihp_organization', None)
        if not names and not org_id:
            continue
        age_days = None
        if pg.created:
            age_days = (now - pg.created).days

        targets = [(by_group, name) for name in names]
        if org_id:
            targets.append((by_org, org_id))
        for bucket, key in targets:
            entry = bucket.setdefault(key, _blank_page_entry())
            entry['total'] += 1
            if age_days is not None:
                if age_days <= 90:
                    entry['recent_90d'] += 1
                if age_days <= 365:
                    entry['recent_365d'] += 1
    return by_group, by_org


# ── scoring ──────────────────────────────────────────────────────────────────

def _score(datasets, documents, news, recent_90d, recent_365d,
           avg_completeness, views=0):
    """Contribution score. ``views`` is last with a default so that the
    signal can be added without breaking existing positional callers."""
    score = (
        _weight('datasets') * math.log1p(datasets)
        + _weight('documents') * math.log1p(documents)
        + _weight('news') * math.log1p(news)
        + _weight('recent') * math.log1p(recent_90d + 0.5 * recent_365d)
        + _weight('views') * math.log1p(views or 0)
    )
    if avg_completeness is not None:
        score += _weight('completeness') * (avg_completeness / 100.0)
    return round(score, 4)


def _facet_maps(field):
    """The four package_search facet maps for one facet field."""
    return (
        _facet_counts('+dataset_type:dataset', field),
        _facet_counts('+dataset_type:documents', field),
        _facet_counts('+dataset_type:(dataset OR documents)'
                      ' +metadata_modified:[NOW-90DAYS TO NOW]', field),
        _facet_counts('+dataset_type:(dataset OR documents)'
                      ' +metadata_modified:[NOW-365DAYS TO NOW]', field),
    )


def _build_rows(entities, entity_for, facets, avg_map, page_map, views_map,
                page_key=None):
    """Build ContributionScore rows for one family of entities.

    entities  -- [(id, name, title)]
    entity_for(name) -- returns the entity_type, or None to skip the entity
    page_key(entity_id, name) -- key under which the entity's pages are
                                 filed in page_map (defaults to the name)
    """
    from ckanext.theme_ejemplo.model import ContributionScore

    ds_map, doc_map, r90_map, r365_map = facets
    rows = []
    for entity_id, name, title in entities:
        entity = entity_for(name)
        if entity is None:
            continue
        key = page_key(entity_id, name) if page_key else name
        pages = page_map.get(key) or {}
        views = views_map.get(name) or {}
        datasets = ds_map.get(name, 0)
        documents = doc_map.get(name, 0)
        news = pages.get('total', 0)
        recent_90d = r90_map.get(name, 0) + pages.get('recent_90d', 0)
        recent_365d = r365_map.get(name, 0) + pages.get('recent_365d', 0)
        avg_c = avg_map.get(name)
        views_total = views.get('total', 0)
        views_recent = views.get('recent', 0)
        rows.append(ContributionScore(
            group_id=entity_id,
            group_name=name,
            group_title=title,
            entity_type=entity,
            datasets_count=datasets,
            documents_count=documents,
            news_events_count=news,
            recent_90d=recent_90d,
            recent_365d=recent_365d,
            avg_completeness=avg_c,
            views_total=views_total,
            views_recent=views_recent,
            score=_score(datasets, documents, news, recent_90d,
                         recent_365d, avg_c, views_total),
        ))
    return rows


def compute_all_scores():
    """Recompute and persist all contribution scores.

    Groups *and* organizations are rebuilt in a single pass: ``replace_all``
    wipes the table first, so a partial recompute would erase the entity
    types it does not emit.

    Returns a summary dict for the CLI.
    """
    from ckanext.theme_ejemplo.model import (
        ContributionScore, init_contribution_scores_db)

    init_contribution_scores_db()

    member_states = _member_state_names()
    page_by_group, page_by_org = _page_counts()

    # Groups: member states + initiatives.
    def group_entity(name):
        if name == 'member-states':
            return None
        return (ContributionScore.ENTITY_MEMBER_STATE
                if name in member_states
                else ContributionScore.ENTITY_INITIATIVE)

    rows = _build_rows(
        _all_groups(), group_entity, _facet_maps('groups'),
        _avg_completeness_by_group('groups'), page_by_group,
        _views_by(_VIEWS_BY_GROUP_SQL))

    # Organizations: pages are filed under the organization id.
    rows += _build_rows(
        _all_orgs(), lambda name: ContributionScore.ENTITY_ORGANIZATION,
        _facet_maps('organization'),
        _avg_completeness_by_group('organization'), page_by_org,
        _views_by(_VIEWS_BY_ORG_SQL),
        page_key=lambda entity_id, name: entity_id)

    ContributionScore.replace_all(rows)
    _scores_cache.clear()
    _rank_cache['expires'] = 0.0
    return {
        'computed': len(rows),
        'member_states': sum(
            1 for r in rows
            if r.entity_type == ContributionScore.ENTITY_MEMBER_STATE),
        'initiatives': sum(
            1 for r in rows
            if r.entity_type == ContributionScore.ENTITY_INITIATIVE),
        'organizations': sum(
            1 for r in rows
            if r.entity_type == ContributionScore.ENTITY_ORGANIZATION),
        'with_completeness': sum(
            1 for r in rows if r.avg_completeness is not None),
    }


# ── read side (web tier) ─────────────────────────────────────────────────────

def get_scores_map(entity_type):
    """{group_name: score} from the persisted table, cached a few minutes.

    ``entity_type=None`` returns every entity. All three types share one
    formula, so their scores are directly comparable — that is what /group
    uses, since it mixes member states and initiatives in a single listing.
    """
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


def _rank_index():
    """{group_name: {'rank', 'total', 'score', 'entity_type'}} for every entity.

    Built in one pass and cached: the previous per-call implementation
    re-read and re-scanned the whole ranking, which is once per card on a
    listing page.
    """
    ttl = _cache_ttl()
    now = time.time()
    if ttl > 0 and now < _rank_cache['expires'] and _rank_cache['data']:
        return _rank_cache['data']
    index = {}
    try:
        from ckanext.theme_ejemplo.model import ContributionScore
        for entity_type in (ContributionScore.ENTITY_MEMBER_STATE,
                            ContributionScore.ENTITY_INITIATIVE,
                            ContributionScore.ENTITY_ORGANIZATION):
            ranked = ContributionScore.get_ranked(entity_type)
            total = len(ranked)
            for i, row in enumerate(ranked, start=1):
                index[row.group_name] = {
                    'rank': i,
                    'total': total,
                    'score': row.score,
                    'entity_type': entity_type,
                    'datasets': row.datasets_count,
                    'documents': row.documents_count,
                    'news_events': row.news_events_count,
                    'views': getattr(row, 'views_total', 0),
                    'avg_completeness': row.avg_completeness,
                }
    except Exception as e:
        log.debug('rank index unavailable: %s', e)
        return _rank_cache['data'] or {}
    _rank_cache['expires'] = now + ttl
    _rank_cache['data'] = index
    return index


def get_rank_for_group(group_name):
    """{'rank': i, 'total': n, 'score': s, …} within its entity type, or None.

    Also carries the score breakdown so a group/organization page can show
    why it sits where it does.
    """
    if not group_name:
        return None
    return _rank_index().get(group_name)
