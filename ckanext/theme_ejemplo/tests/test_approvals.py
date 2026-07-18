from ckanext.theme_ejemplo import approvals


def test_get_review_queues_outside_request_returns_empty():
    # no Flask request context -> no user -> no queues, no crash
    assert approvals.get_review_queues() == []
    assert approvals.get_review_queues_total() == 0


def test_cached_counts_local_fallback(monkeypatch):
    monkeypatch.setattr(approvals, '_redis_init_attempted', True)
    monkeypatch.setattr(approvals, '_redis_client', None)
    approvals._local_cache.clear()

    calls = []

    def compute():
        calls.append(1)
        return {'water': 2, 'bugs': 1}

    first = approvals._cached_counts('sysadmin', compute)
    second = approvals._cached_counts('sysadmin', compute)
    assert first == second == {'water': 2, 'bugs': 1}
    assert len(calls) == 1  # second call served from cache


def test_invalidate_clears_local_cache(monkeypatch):
    monkeypatch.setattr(approvals, '_redis_init_attempted', True)
    monkeypatch.setattr(approvals, '_redis_client', None)
    approvals._local_cache.clear()

    calls = []

    def compute():
        calls.append(1)
        return {'membership': 3}

    approvals._cached_counts('user:abc', compute)
    approvals.invalidate('abc')
    approvals._cached_counts('user:abc', compute)
    assert len(calls) == 2  # recomputed after invalidation


def test_queue_defs_have_required_fields():
    labels = approvals._labels.__doc__  # sanity: labels helper exists
    assert labels is not None
    for queue in approvals.QUEUE_DEFS:
        assert queue['scope'] in ('sysadmin', 'user')
        assert 'helper' in queue
        assert 'route' in queue or 'url' in queue
