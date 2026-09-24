# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_workspaces` (reglas del piloto de working groups)."""
import pytest

from ckanext.theme_ejemplo import ihpix_workspaces as W


def _wg(**kw):
    d = {'id': 'wg1', 'output_code': '1.1', 'status': W.WG_ACTIVE, 'lead_user_id': ''}
    d.update(kw)
    return d


def _member(**kw):
    d = {'id': 'm1', 'working_group_id': 'wg1', 'user_id': 'u1',
         'role': W.ROLE_CONTRIBUTOR, 'status': W.MEMBER_ACTIVE}
    d.update(kw)
    return d


def test_resolve_join_status():
    assert W.resolve_join_status(True) == W.MEMBER_ACTIVE
    assert W.resolve_join_status(False) == W.MEMBER_PENDING


def test_can_manage_sysadmin_lead_user_and_lead_member():
    wg = _wg(lead_user_id='boss')
    assert W.can_manage(wg, 'anyone', None, is_sysadmin=True)
    assert W.can_manage(wg, 'boss', None)
    assert W.can_manage(_wg(), 'u1', _member(role=W.ROLE_LEAD))
    assert not W.can_manage(_wg(), 'u1', _member(role=W.ROLE_LEAD, status=W.MEMBER_PENDING))
    assert not W.can_manage(_wg(), 'u1', _member())
    assert not W.can_manage(_wg(), None, None)


def test_approve_from_pending_only():
    status, role = W.validate_member_action(
        _member(status=W.MEMBER_PENDING), 'approve', 'lead', True)
    assert status == W.MEMBER_ACTIVE
    assert role == W.ROLE_CONTRIBUTOR
    with pytest.raises(W.WorkspaceRuleError) as exc:
        W.validate_member_action(_member(status=W.MEMBER_ACTIVE), 'approve', 'lead', True)
    assert 'status' in exc.value.errors


def test_only_managers_can_act():
    with pytest.raises(W.WorkspaceRuleError) as exc:
        W.validate_member_action(_member(status=W.MEMBER_PENDING), 'approve', 'u2', False)
    assert 'action' in exc.value.errors


def test_unknown_action_rejected():
    with pytest.raises(W.WorkspaceRuleError):
        W.validate_member_action(_member(), 'promote', 'lead', True)


def test_lead_cannot_remove_or_demote_themselves():
    me = _member(user_id='lead', role=W.ROLE_LEAD)
    with pytest.raises(W.WorkspaceRuleError) as exc:
        W.validate_member_action(me, 'remove', 'lead', True)
    assert 'user_id' in exc.value.errors
    with pytest.raises(W.WorkspaceRuleError):
        W.validate_member_action(me, 'set_role', 'lead', True, role=W.ROLE_OBSERVER)
    # Mantener el rol lead sí está permitido
    status, role = W.validate_member_action(me, 'set_role', 'lead', True, role=W.ROLE_LEAD)
    assert (status, role) == (W.MEMBER_ACTIVE, W.ROLE_LEAD)


def test_set_role_requires_valid_role():
    with pytest.raises(W.WorkspaceRuleError) as exc:
        W.validate_member_action(_member(), 'set_role', 'lead', True, role='boss')
    assert 'role' in exc.value.errors
    status, role = W.validate_member_action(_member(), 'set_role', 'lead', True, role=W.ROLE_OBSERVER)
    assert role == W.ROLE_OBSERVER


def test_reinstate_and_remove_transitions():
    status, _ = W.validate_member_action(_member(status=W.MEMBER_REMOVED), 'reinstate', 'lead', True)
    assert status == W.MEMBER_ACTIVE
    status, _ = W.validate_member_action(_member(), 'remove', 'lead', True)
    assert status == W.MEMBER_REMOVED


def test_validate_join_rules():
    with pytest.raises(W.WorkspaceRuleError):
        W.validate_join(_wg(status=W.WG_ARCHIVED), None)
    with pytest.raises(W.WorkspaceRuleError):
        W.validate_join(_wg(), _member(status=W.MEMBER_PENDING))
    with pytest.raises(W.WorkspaceRuleError):
        W.validate_join(_wg(), _member(status=W.MEMBER_ACTIVE))
    assert W.validate_join(_wg(), None) is False
    assert W.validate_join(_wg(), _member(status=W.MEMBER_REMOVED)) is True


def test_labels_and_title():
    assert W.workspace_title('1.3') == 'Output 1.3'
    assert W.workspace_title('1.3', 'Networks') == 'Output 1.3 – Networks'
    assert W.contribution_label('report_published') == 'Report published'
    assert W.role_label('lead') == 'Lead'
    assert set(W.MEMBER_ACTIONS) == {'approve', 'reject', 'remove', 'set_role', 'reinstate'}
