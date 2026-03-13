# encoding: utf-8
"""Auth functions for membership request actions."""

import ckan.plugins.toolkit as toolkit
import ckan.model as model
from ckanext.theme_ejemplo.actions import _get_admin_org_ids


def membership_request_create(context, data_dict):
    """Any authenticated user can create a membership request."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    return {'success': True}


def membership_request_list(context, data_dict):
    """Only org admins or sysadmins can list requests."""
    user_obj = context.get('auth_user_obj')
    if not user_obj:
        return {'success': False}
    if user_obj.sysadmin:
        return {'success': True}

    org_id_or_name = data_dict.get('organization_id', '')
    if org_id_or_name:
        try:
            org = toolkit.get_action('organization_show')(
                {'ignore_auth': True}, {'id': org_id_or_name}
            )
            admin_org_ids = _get_admin_org_ids(user_obj.id)
            if org['id'] in admin_org_ids:
                return {'success': True}
        except Exception:
            pass
    return {'success': False, 'msg': toolkit._('Only organization admins can manage requests')}


def membership_request_process(context, data_dict):
    """Only org admins or sysadmins can approve/reject requests."""
    user_obj = context.get('auth_user_obj')
    if not user_obj:
        return {'success': False}
    if user_obj.sysadmin:
        return {'success': True}

    request_id = data_dict.get('id', '')
    if request_id:
        from ckanext.theme_ejemplo.model import MembershipRequest
        req = MembershipRequest.get(request_id)
        if req:
            admin_org_ids = _get_admin_org_ids(user_obj.id)
            if req.organization_id in admin_org_ids:
                return {'success': True}
    return {'success': False, 'msg': toolkit._('Only organization admins can process requests')}


def membership_request_count(context, data_dict):
    """Any authenticated user can check their count."""
    if not context.get('auth_user_obj'):
        return {'success': False}
    return {'success': True}


# ── Featured Dataset Auth ────────────────────────────────────────────────────

def _sysadmin_only(context, data_dict):
    user_obj = context.get('auth_user_obj')
    if user_obj and user_obj.sysadmin:
        return {'success': True}
    return {'success': False, 'msg': toolkit._('Only sysadmins can manage featured datasets')}


def featured_dataset_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_dataset_add(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_dataset_remove(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── Featured Publication Auth ────────────────────────────────────────────────

def featured_publication_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_publication_create(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_publication_update(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_publication_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_publication_reorder(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── Portal Card Auth ─────────────────────────────────────────────────────────

def portal_card_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def portal_card_create(context, data_dict):
    return _sysadmin_only(context, data_dict)


def portal_card_update(context, data_dict):
    return _sysadmin_only(context, data_dict)


def portal_card_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)


def portal_card_reorder(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── Bug Ticket Auth ──────────────────────────────────────────────────────────

def bug_ticket_create(context, data_dict):
    """Any authenticated user can create a bug ticket."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    return {'success': True}


def bug_ticket_list(context, data_dict):
    """Any authenticated user can list tickets (filtered to own)."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    return {'success': True}


def bug_ticket_show(context, data_dict):
    """Any authenticated user can view tickets (checked in action)."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    return {'success': True}


def bug_ticket_update(context, data_dict):
    """Any authenticated user can update (action enforces ownership)."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    return {'success': True}


def bug_ticket_api_list(context, data_dict):
    """Only sysadmins can access the AI API endpoint."""
    return _sysadmin_only(context, data_dict)


# ── Sysadmin User Management Auth ───────────────────────────────────────────

def admin_user_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_reset_password(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_purge(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_reactivate(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_toggle_sysadmin(context, data_dict):
    return _sysadmin_only(context, data_dict)


def admin_user_create(context, data_dict):
    return _sysadmin_only(context, data_dict)
