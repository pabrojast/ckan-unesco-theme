from ckanext.theme_ejemplo import ranking


def test_score_grows_with_contributions():
    low = ranking._score(1, 0, 0, 0, 0, None)
    high = ranking._score(50, 10, 5, 3, 8, None)
    assert high > low > 0


def test_score_zero_for_empty_group():
    assert ranking._score(0, 0, 0, 0, 0, None) == 0


def test_missing_completeness_is_not_zero():
    without = ranking._score(10, 2, 1, 1, 2, None)
    zero = ranking._score(10, 2, 1, 1, 2, 0.0)
    full = ranking._score(10, 2, 1, 1, 2, 100.0)
    # no data adds nothing (same as explicit 0), real data adds weight
    assert without == zero
    assert full > without


def test_recent_activity_weighs_more_than_old():
    recent = ranking._score(10, 0, 0, 5, 5, None)
    stale = ranking._score(10, 0, 0, 0, 5, None)
    assert recent > stale


def test_views_add_to_the_score():
    without = ranking._score(10, 2, 1, 1, 2, None)
    with_views = ranking._score(10, 2, 1, 1, 2, None, 500)
    assert with_views > without


def test_views_default_keeps_positional_callers_working():
    # `views` was added last with a default; omitting it must equal zero.
    assert ranking._score(3, 1, 0, 0, 0, None) == \
        ranking._score(3, 1, 0, 0, 0, None, 0)


def test_views_are_damped():
    # log1p damping: ten times the views must not multiply the term by ten.
    small = ranking._score(0, 0, 0, 0, 0, None, 10)
    large = ranking._score(0, 0, 0, 0, 0, None, 100)
    assert large > small
    assert large < small * 10


def test_order_by_score(monkeypatch):
    monkeypatch.setattr(
        ranking, 'get_scores_map',
        lambda entity: {'chile': 5.0, 'zimbabwe': 9.0, 'france': 1.0})
    ordered = ranking.order_by_score(
        ['chile', 'france', 'unknown-a', 'zimbabwe', 'unknown-b'],
        'member_state')
    assert ordered == ['zimbabwe', 'chile', 'france',
                       'unknown-a', 'unknown-b']


def test_order_by_score_without_data_keeps_order(monkeypatch):
    monkeypatch.setattr(ranking, 'get_scores_map', lambda entity: {})
    names = ['b', 'a', 'c']
    assert ranking.order_by_score(names, 'initiative') == names


def test_page_counts_file_pages_under_group_and_org(monkeypatch):
    """One page attributed to both an initiative and an organization must
    count once on each side, keyed by name for groups and by id for orgs."""
    import datetime
    import json as _json
    import sys
    import types

    class FakePage(object):
        # `Page.page_type.in_(...)` is called on the class, so it needs a
        # column-ish attribute; the fake query ignores the filter anyway.
        page_type = types.SimpleNamespace(in_=lambda *a: None)
        submission_status = 'approved'
        extras = _json.dumps({'initiative_groups': [{'name': 'friend-water'}]})
        ihp_organization = 'org-uuid-1'
        created = datetime.datetime.utcnow()

    # ckanext-pages is not installed in the test image; _page_counts imports
    # it lazily, so a stub module is enough.
    fake_db = types.ModuleType('ckanext.pages.db')
    fake_db.Page = FakePage
    monkeypatch.setitem(sys.modules, 'ckanext.pages', types.ModuleType('ckanext.pages'))
    monkeypatch.setitem(sys.modules, 'ckanext.pages.db', fake_db)

    class FakeQuery(object):
        def filter(self, *a, **kw):
            return self

        def all(self):
            return [FakePage()]

    monkeypatch.setattr(ranking.model, 'Session',
                        types.SimpleNamespace(
                            query=lambda *a, **kw: FakeQuery()))
    by_group, by_org = ranking._page_counts()
    assert by_group['friend-water']['total'] == 1
    assert by_group['friend-water']['recent_90d'] == 1
    assert by_org['org-uuid-1']['total'] == 1


def test_order_by_score_for_organizations(monkeypatch):
    monkeypatch.setattr(
        ranking, 'get_scores_map',
        lambda entity: {'cazalac': 4.0, 'unesco-ihp': 7.0})
    assert ranking.order_by_score(
        ['cazalac', 'unesco-ihp'], 'organization') == ['unesco-ihp', 'cazalac']
