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
