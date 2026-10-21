# -*- coding: utf-8 -*-
"""Guardado único para formulario, edición compartida e importación."""
import json

import ckan.model as model
import ckan.plugins.toolkit as tk
from sqlalchemy import select

from ckanext.theme_ejemplo import ihpix_forms as F, ihpix_relations as R
from ckanext.theme_ejemplo import ihpix_store as S
from ckanext.theme_ejemplo.model import (IhpixActivity, IhpixWorkingGroup,
                                       IhpixWorkingGroupMember)


class RevisionConflict(tk.ValidationError):
    def __init__(self, activity, actor=None):
        from ckanext.theme_ejemplo import actions as A
        from ckanext.theme_ejemplo.ihpix_resource_access import filtered
        self.current = F.activity_to_form_dict(activity.as_dict())
        self.current['links_json'] = json.dumps(filtered(A._ihpix_links_for(activity.id), actor))
        self.current['expected_revision'] = activity.revision
        super().__init__({'expected_revision': 'revision_conflict',
                          'revision': activity.revision})


def active_workspaces(activity):
    outputs = R.dimension_values(activity.as_dict(), 'output')
    return model.Session.query(IhpixWorkingGroup).filter(
        IhpixWorkingGroup.output_code.in_(outputs),
        IhpixWorkingGroup.status == 'active').all()


def check_workspaces(*rows):
    outputs = {value for row in rows if row for value in R.dimension_values(row, 'output')}
    if model.Session.query(IhpixWorkingGroup).filter(
            IhpixWorkingGroup.output_code.in_(outputs), IhpixWorkingGroup.status == 'archived').first():
        raise tk.NotAuthorized('Archived workspaces are read-only')


def eligible(activity, user):
    if not user or user.state != 'active':
        return False
    for wg in active_workspaces(activity):
        member = IhpixWorkingGroupMember.get_membership(wg.id, user.id)
        if (wg.lead_user_id == user.id and not member) or (member and member.status == 'active'
                                          and member.role in ('lead', 'contributor')):
            return True
    return False


def can_collaborate(activity, user):
    if not eligible(activity, user):
        return False
    return bool(model.Session.execute(select(S.collaborators.c.id).where(
        S.collaborators.c.activity_id == activity.id,
        S.collaborators.c.user_id == user.id,
        S.collaborators.c.active.is_(True))).first())


def can_read(activity, user):
    return activity.status == 'published' or bool(user and (
        user.sysadmin or activity.is_owned_by(user) or can_collaborate(activity, user)))


def lock(activity_id, expected, actor=None):
    activity = model.Session.query(IhpixActivity).filter_by(id=activity_id).with_for_update().populate_existing().one_or_none()
    if not activity:
        raise tk.ObjectNotFound('Report not found')
    try:
        valid = str(expected).isdigit() and int(expected) == (activity.revision or 0)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise RevisionConflict(activity, actor)
    return activity


def validate_organizations(values):
    ids = list(R.read_list(values.get('partner_org_ids')))
    if values.get('institution_org_id'):
        ids.append(values['institution_org_id'])
    for org_id in ids:
        org = model.Group.get(org_id)
        if not org or not org.is_organization or org.state != 'active' or org.id != org_id:
            raise tk.ValidationError({'institution_org_id': 'Select an active IHP-WINS organization'})


def save(context, data, activity=None):
    """Valida y guarda sin commit: el llamador controla la transacción."""
    from ckanext.theme_ejemplo import actions as A
    user = A._ihpix_user_obj(context)
    is_draft = A.C.normalize_bool(data.get('save_as_draft'))
    if activity:
        activity = lock(activity.id, data.get('expected_revision'), user)
        owner = activity.is_owned_by(user)
        if not (user.sysadmin or owner or can_collaborate(activity, user)):
            raise tk.NotAuthorized('Report access was revoked')
        if not user.sysadmin and activity.status not in F.OWNER_EDITABLE_STATUSES:
            raise tk.ValidationError({'status': 'Only draft or rejected reports can be edited'})
        if not is_draft and not (owner or user.sysadmin):
            raise tk.NotAuthorized('Only the author can submit this report')
        outputs = R.dimension_values(activity.as_dict(), 'output')
        if outputs and not active_workspaces(activity):
            raise tk.NotAuthorized('Archived workspaces are read-only')
    values = A._ihpix_validate(data, is_draft)
    validate_organizations(values)
    check_workspaces(values, activity.as_dict() if activity else None)
    if activity is None:
        activity = IhpixActivity(title=values['title'], priority_area=values['priority_area'])
        activity.reported_by = user.id
        activity.status = 'draft'
        model.Session.add(activity)
    else:
        S.ensure_baseline(activity, A._ihpix_links_for(activity.id))
    A._apply_report_values(activity, values)
    if is_draft:
        activity.status = 'draft'
    elif activity.status != 'published':
        A._ihpix_mark_submitted(activity)
    if 'links_json' in data:
        A._sync_activity_links(activity, data['links_json'], user)
    model.Session.flush()
    links = A._ihpix_links_for(activity.id)
    S.snapshot(activity, user.id, links)
    if activity.status == 'pending':
        A._ihpix_ledger_on_submit(activity)
    model.Session.flush()
    return activity


def save_admin(context, data, activity=None):
    """Compatibilidad del editor administrativo, con el mismo validador e historial."""
    from ckanext.theme_ejemplo import actions as A
    actor = A._ihpix_user_obj(context)
    if not actor or not actor.sysadmin:
        raise tk.NotAuthorized('Administrator access required')
    payload = {}
    if activity:
        activity = lock(activity.id, data.get('expected_revision'), actor)
        payload = F.activity_to_form_dict(activity.as_dict())
    payload.update(data)
    if activity and 'contributions_json' not in data and any(
            key in data for key in ('priority_area', 'output', 'key_activity_code')):
        relations = R.associations(activity.as_dict())
        if relations:
            relations[0].update({key: data[key] for key in
                ('priority_area', 'output', 'key_activity_code') if key in data})
            payload['contributions_json'] = relations
    values = A._ihpix_validate(payload, True)
    validate_organizations(values)
    check_workspaces(values, activity.as_dict() if activity else None)
    status = data.get('status', activity.status if activity else 'published')
    if status not in IhpixActivity.VALID_STATUSES:
        raise tk.ValidationError({'status': 'Invalid report status'})
    if activity is None:
        activity = IhpixActivity(title=values['title'], priority_area=values['priority_area'])
        activity.reported_by = actor.id
        model.Session.add(activity)
    else:
        S.ensure_baseline(activity, A._ihpix_links_for(activity.id))
    A._apply_report_values(activity, values)
    for key in ('notes', 'unesco_participation', 'reported_by'):
        if key in data:
            setattr(activity, key, data[key])
    activity.status = status
    if 'links_json' in data:
        A._sync_activity_links(activity, data['links_json'], actor)
    model.Session.flush()
    S.snapshot(activity, actor.id, A._ihpix_links_for(activity.id))
    model.Session.flush()
    return activity
