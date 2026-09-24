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


def test_ihpix_reports_queue_is_registered():
    ids = [q['id'] for q in approvals.QUEUE_DEFS]
    assert 'ihpix_reports' in ids
    assert 'ihpix_wg_members' in ids
    wg_queue = next(q for q in approvals.QUEUE_DEFS if q['id'] == 'ihpix_wg_members')
    assert wg_queue['scope'] == 'user'
    assert wg_queue['helper'] == 'get_pending_ihpix_wg_members_count'
    queue = next(q for q in approvals.QUEUE_DEFS if q['id'] == 'ihpix_reports')
    assert queue['scope'] == 'sysadmin'
    assert queue['helper'] == 'get_pending_ihpix_reports_count'
    assert queue['route'] == 'theme_ejemplo.ihpix_reports_admin'


def test_every_queue_has_a_label(monkeypatch):
    import ckan.plugins.toolkit as toolkit
    monkeypatch.setattr(toolkit, '_', lambda s: s, raising=False)
    labels = approvals._labels()
    for queue in approvals.QUEUE_DEFS:
        assert queue['id'] in labels
