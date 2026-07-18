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
