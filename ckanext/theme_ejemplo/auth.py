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


def _logged_in_only(context, data_dict):
    """Cualquier usuario autenticado (API o web)."""
    if context.get('auth_user_obj') or context.get('user'):
        return {'success': True}
    return {'success': False, 'msg': toolkit._('Must be logged in')}


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


def featured_publication_import_legacy(context, data_dict):
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


def admin_user_request_password_reset(context, data_dict):
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


# ── IHP-IX Content Auth ─────────────────────────────────────────────────────

def ihpix_content_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def ihpix_content_update(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── IHP-IX Activity Auth ────────────────────────────────────────────────────

def ihpix_activity_list(context, data_dict):
    """Actividades publicadas: cualquier usuario autenticado (2026-09)."""
    return _logged_in_only(context, data_dict)


def ihpix_activity_show(context, data_dict):
    """Una actividad: cualquier usuario autenticado."""
    return _logged_in_only(context, data_dict)


def ihpix_contributor_list(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_activity_create(context, data_dict):
    return _sysadmin_only(context, data_dict)


def ihpix_activity_update(context, data_dict):
    return _sysadmin_only(context, data_dict)


def ihpix_activity_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── IHP-IX Reporting & Dashboard Auth ──────────────────────────────────────

def ihpix_report_submit(context, data_dict):
    """Any logged-in user can submit a report."""
    user = context.get('user')
    if not user:
        return {'success': False,
                'msg': 'You must be logged in to submit a report'}
    return {'success': True}


def _ihpix_report_owner_or_sysadmin(context, data_dict):
    """Propietario del reporte (`reported_by`) o sysadmin.

    Si el reporte no existe se autoriza igualmente para que la acción
    devuelva ObjectNotFound (404) en vez de NotAuthorized (403).
    """
    user_obj = context.get('auth_user_obj')
    if not user_obj and context.get('user'):
        user_obj = model.User.get(context['user'])
    if not user_obj:
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    if user_obj.sysadmin:
        return {'success': True}
    activity_id = (data_dict or {}).get('id')
    if not activity_id:
        return {'success': False, 'msg': toolkit._('Report id is required')}
    from ckanext.theme_ejemplo.model import IhpixActivity
    activity = IhpixActivity.get(activity_id)
    if activity is None or activity.is_owned_by(user_obj):
        return {'success': True}
    return {'success': False,
            'msg': toolkit._('You can only manage your own IHP-IX reports')}


def ihpix_report_show(context, data_dict):
    return _ihpix_report_owner_or_sysadmin(context, data_dict)


def ihpix_report_update(context, data_dict):
    return _ihpix_report_owner_or_sysadmin(context, data_dict)


def ihpix_report_delete(context, data_dict):
    return _ihpix_report_owner_or_sysadmin(context, data_dict)


def ihpix_my_reports_list(context, data_dict):
    return _logged_in_only(context, data_dict)


# ── IHP-IX Adjuntos ─────────────────────────────────────────────────────────

def ihpix_activity_link_list(context, data_dict):
    """Adjuntos visibles si la actividad está publicada, o para su
    propietario / sysadmin. Si no existe, se autoriza para devolver 404."""
    from ckanext.theme_ejemplo.model import IhpixActivity
    activity_id = (data_dict or {}).get('activity_id')
    activity = IhpixActivity.get(activity_id) if activity_id else None
    if activity is None or activity.status == IhpixActivity.STATUS_PUBLISHED:
        return {'success': True}
    return _ihpix_report_owner_or_sysadmin(context, {'id': activity_id})


def ihpix_activity_link_create(context, data_dict):
    return _ihpix_report_owner_or_sysadmin(
        context, {'id': (data_dict or {}).get('activity_id')})


def ihpix_activity_link_delete(context, data_dict):
    from ckanext.theme_ejemplo.model import IhpixActivityLink
    link_id = (data_dict or {}).get('id')
    link = IhpixActivityLink.get(link_id) if link_id else None
    if link is None:
        return _logged_in_only(context, data_dict)
    return _ihpix_report_owner_or_sysadmin(context, {'id': link.activity_id})


def ihpix_link_search(context, data_dict):
    return _logged_in_only(context, data_dict)


# ── IHP-IX Working groups (workspaces) ──────────────────────────────────────

def _ihpix_wg_manager_or_sysadmin(context, data_dict, wg=None):
    """Lead del workspace (lead_user_id o miembro lead activo) o sysadmin.
    Si el workspace no existe se autoriza para que la acción devuelva 404."""
    user_obj = context.get('auth_user_obj')
    if not user_obj and context.get('user'):
        user_obj = model.User.get(context['user'])
    if not user_obj:
        return {'success': False, 'msg': toolkit._('Must be logged in')}
    if user_obj.sysadmin:
        return {'success': True}
    from ckanext.theme_ejemplo.model import IhpixWorkingGroup, IhpixWorkingGroupMember
    from ckanext.theme_ejemplo import ihpix_workspaces as W
    if wg is None:
        value = (data_dict or {}).get('id') or (data_dict or {}).get('output_code')
        wg = IhpixWorkingGroup.get_by_id_or_output(value) if value else None
    if wg is None:
        return {'success': True}
    membership = IhpixWorkingGroupMember.get_membership(wg.id, user_obj.id)
    if W.can_manage(wg, user_obj.id, membership, False):
        return {'success': True}
    return {'success': False,
            'msg': toolkit._('Only the working group lead can do this')}


def ihpix_working_group_list(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_working_group_show(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_working_group_update(context, data_dict):
    return _ihpix_wg_manager_or_sysadmin(context, data_dict)


def ihpix_working_group_join(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_working_group_leave(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_working_group_member_process(context, data_dict):
    from ckanext.theme_ejemplo.model import IhpixWorkingGroupMember, IhpixWorkingGroup
    membership_id = (data_dict or {}).get('membership_id')
    membership = IhpixWorkingGroupMember.get(membership_id) if membership_id else None
    if membership is None:
        return _logged_in_only(context, data_dict)
    wg = IhpixWorkingGroup.get(membership.working_group_id)
    return _ihpix_wg_manager_or_sysadmin(context, {'id': membership.working_group_id}, wg=wg)


def ihpix_working_group_member_list(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_contribution_list(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_report_review(context, data_dict):
    return _sysadmin_only(context, data_dict)


def ihpix_dashboard_stats(context, data_dict):
    """Estadísticas del dashboard: usuarios autenticados. La landing
    pública las obtiene en servidor con `ignore_auth`."""
    return _logged_in_only(context, data_dict)


def ihpix_admin_overview_stats(context, data_dict):
    """Sysadmin-only access to the extended admin overview statistics."""
    return _sysadmin_only(context, data_dict)


# ── IHP-IX GeoJSON & Country Summary Auth ──────────────────────────────────

def ihpix_geojson(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_activity_geojson(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_country_summary_list(context, data_dict):
    return _logged_in_only(context, data_dict)


def ihpix_country_summary_recompute(context, data_dict):
    return _sysadmin_only(context, data_dict)


# ── Initiative Request Auth ─────────────────────────────────────────────────

def initiative_request_create(context, data_dict):
    """Cualquier usuario autenticado puede solicitar una iniciativa."""
    if not context.get('auth_user_obj'):
        return {'success': False, 'msg': toolkit._('Debes iniciar sesión.')}
    return {'success': True}


def initiative_request_list(context, data_dict):
    """Solo sysadmins pueden listar solicitudes."""
    return _sysadmin_only(context, data_dict)


def initiative_request_process(context, data_dict):
    """Solo sysadmins pueden aprobar/rechazar solicitudes."""
    return _sysadmin_only(context, data_dict)


def initiative_request_count(context, data_dict):
    """Cualquier usuario autenticado puede consultar el conteo (devuelve 0 si no es sysadmin)."""
    if not context.get('auth_user_obj'):
        return {'success': False}
    return {'success': True}


# ── Open Learning Course Auth ────────────────────────────────────────────────

def open_learning_course_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def open_learning_course_set_status(context, data_dict):
    return _sysadmin_only(context, data_dict)


def open_learning_course_set_type(context, data_dict):
    return _sysadmin_only(context, data_dict)


def open_learning_sync(context, data_dict):
    return _sysadmin_only(context, data_dict)


def open_learning_course_search(context, data_dict):
    return _sysadmin_only(context, data_dict)


def open_learning_course_add(context, data_dict):
    return _sysadmin_only(context, data_dict)
