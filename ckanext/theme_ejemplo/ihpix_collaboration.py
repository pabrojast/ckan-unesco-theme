# -*- coding: utf-8 -*-
"""Acciones de colaboración; permisos comprobados también en llamadas directas."""
import datetime
import json

from sqlalchemy import select, and_
import ckan.model as model
import ckan.plugins.toolkit as tk

from ckanext.theme_ejemplo import ihpix_store as S, ihpix_service as V
from ckanext.theme_ejemplo.ihpix_resource_access import visible, filtered
from ckanext.theme_ejemplo.model import (IhpixActivity, IhpixActivityLink,
                                       IhpixWorkingGroup, IhpixWorkingGroupMember)


def user(context):
    obj = context.get('auth_user_obj') or model.User.get(context.get('user', ''))
    if not obj or obj.state != 'active':
        raise tk.NotAuthorized('Sign in to continue')
    return obj


def workspace_access(context, code, write=False):
    actor = user(context)
    wg = IhpixWorkingGroup.get_by_id_or_output(code)
    if not wg:
        raise tk.ObjectNotFound('Workspace not found')
    member = IhpixWorkingGroupMember.get_membership(wg.id, actor.id)
    lead = actor.sysadmin or (wg.lead_user_id == actor.id and not member) or bool(
        member and member.status == 'active' and member.role == 'lead')
    if not lead and not (member and member.status == 'active'):
        raise tk.NotAuthorized('Only active members can read workspace collaboration')
    if write and (wg.status != 'active' or not (lead or member.role == 'contributor')):
        raise tk.NotAuthorized('This workspace is read-only for you')
    return actor, wg, member, lead


def report_access(context, report_id, author=False):
    actor = user(context)
    activity = IhpixActivity.get(report_id)
    if not activity:
        raise tk.ObjectNotFound('Report not found')
    if not (actor.sysadmin or activity.is_owned_by(actor) or
            (not author and V.can_collaborate(activity, actor))):
        raise tk.NotAuthorized('No access to report collaboration')
    return actor, activity


def _serialize(row):
    result = S.row_dict(row)
    for key, value in list(result.items()):
        if isinstance(value, (datetime.date, datetime.datetime)):
            result[key] = value.isoformat()
    return result


@tk.side_effect_free
def ihpix_workspace_item_list(context, data):
    actor, wg, member, lead = workspace_access(context, tk.get_or_bust(data, 'working_group_id'))
    rows = model.Session.execute(select(S.items).where(
        S.items.c.working_group_id == wg.id, S.items.c.deleted.is_(False))
        .order_by(S.items.c.created_at.desc()).limit(500)).fetchall()
    result = []
    for row in rows:
        item = _serialize(row)
        if item['activity_id']:
            activity = IhpixActivity.get(item['activity_id'])
            if not activity or not V.can_read(activity, actor):
                continue
            item['activity_title'] = activity.title
            item['activity_url'] = tk.url_for(
                'theme_ejemplo.ihpix_activity_detail' if activity.status == 'published'
                else 'theme_ejemplo.ihpix_report_edit', id=activity.id)
        if item['link_id']:
            link = IhpixActivityLink.get(item['link_id'])
            if not link or not visible(link.as_dict(), actor):
                continue
        item['can_edit'] = wg.status == 'active' and (lead or (
            member and member.role == 'contributor' and item['author_id'] == actor.id))
        item['can_update_status'] = (wg.status == 'active' and item['kind'] == 'task'
            and item['assignee_id'] == actor.id and bool(lead or (
                member and member.status == 'active' and member.role == 'contributor')))
        result.append(item)
    return {'results': result, 'can_write': wg.status == 'active' and
            bool(lead or (member and member.role == 'contributor'))}


def ihpix_workspace_item_save(context, data):
    actor, wg, member, lead = workspace_access(context, tk.get_or_bust(data, 'working_group_id'), write=True)
    existing = None
    if data.get('id'):
        row = model.Session.execute(select(S.items).where(S.items.c.id == data['id'])
                                    .with_for_update()).first()
        if not row or row.working_group_id != wg.id:
            raise tk.ObjectNotFound('Comment or task not found')
        existing = S.row_dict(row)
        if not (lead or row.author_id == actor.id):
            # El asignado puede cambiar únicamente el estado de su tarea.
            if row.kind != 'task' or row.assignee_id != actor.id or set(data) - {
                    'id', 'working_group_id', 'expected_revision', 'status', '_csrf_token'}:
                raise tk.NotAuthorized('Only the author or lead can edit this item')
        if str(data.get('expected_revision')) != str(row.revision):
            raise tk.ValidationError({'expected_revision': 'revision_conflict'})
    values = dict(existing or {})
    for key in ('kind', 'title', 'body', 'assignee_id', 'activity_id', 'link_id', 'status'):
        if key in data:
            values[key] = str(data[key] or '').strip()
    kind = values.get('kind', 'comment')
    if kind not in ('comment', 'task'):
        raise tk.ValidationError({'kind': 'Choose comment or task'})
    if not values.get('body') or len(values['body']) > 10000:
        raise tk.ValidationError({'body': 'Enter a description of up to 10000 characters'})
    if kind == 'task' and (not values.get('title') or len(values['title']) > 300):
        raise tk.ValidationError({'title': 'Enter a task title of up to 300 characters'})
    if values.get('status', 'pending') not in ('pending', 'in_progress', 'completed'):
        raise tk.ValidationError({'status': 'Invalid task status'})
    if 'due_date' in data:
        try:
            values['due_date'] = datetime.date.fromisoformat(data['due_date']) if data['due_date'] else None
        except (ValueError, TypeError):
            raise tk.ValidationError({'due_date': 'Use YYYY-MM-DD'})
    if values.get('assignee_id'):
        assigned = IhpixWorkingGroupMember.get_membership(wg.id, values['assignee_id'])
        if not (assigned and assigned.status == 'active' and assigned.role in ('lead', 'contributor')):
            raise tk.ValidationError({'assignee_id': 'Choose an active contributor or lead'})
    if values.get('activity_id'):
        activity = IhpixActivity.get(values['activity_id'])
        from ckanext.theme_ejemplo import ihpix_relations as R
        if (not activity or not V.can_read(activity, actor) or
                wg.output_code not in R.dimension_values(activity.as_dict(), 'output')):
            raise tk.ValidationError({'activity_id': 'Choose an accessible activity in this workspace'})
        if values.get('assignee_id') and not V.can_read(activity, model.User.get(values['assignee_id'])):
            raise tk.ValidationError({'assignee_id': 'Invite the assignee to this report before assigning its task'})
    if values.get('link_id'):
        link = IhpixActivityLink.get(values['link_id'])
        if not link or link.activity_id != values.get('activity_id') or not visible(link.as_dict(), actor):
            raise tk.ValidationError({'link_id': 'Choose a resource attached to the selected activity'})
        if values.get('assignee_id') and not visible(link.as_dict(), model.User.get(values['assignee_id'])):
            raise tk.ValidationError({'assignee_id': 'The assignee must have access to this resource'})
    values.update(kind=kind, updated_at=S.now(), revision=(existing or {}).get('revision', 0) + 1)
    if existing:
        if data.get('delete'):
            values['deleted'] = True
        model.Session.execute(S.items.update().where(S.items.c.id == existing['id']).values(**values))
    else:
        values.update(id=S.uid(), working_group_id=wg.id, author_id=actor.id,
                      created_at=S.now(), deleted=False)
        model.Session.execute(S.items.insert().values(**values))
    assignee = values.get('assignee_id')
    if assignee and assignee != (existing or {}).get('assignee_id'):
        S.notify(assignee, 'A workspace task was assigned to you', '/ihpix/workspaces/' + wg.output_code + '/collaboration')
    model.Session.commit()
    return {'id': values['id'], 'revision': values['revision']}


@tk.side_effect_free
def ihpix_report_collaboration_show(context, data):
    actor, activity = report_access(context, tk.get_or_bust(data, 'id'))
    candidates = {}
    for wg in V.active_workspaces(activity):
        lead = model.User.get(wg.lead_user_id) if wg.lead_user_id else None
        if lead and V.eligible(activity, lead):
            candidates[lead.id] = {'id': lead.id, 'name': lead.display_name}
        for member in IhpixWorkingGroupMember.get_for_group(wg.id, 'active'):
            person = model.User.get(member.user_id)
            if person and V.eligible(activity, person):
                candidates[person.id] = {'id': person.id, 'name': person.display_name}
    members = [_serialize(r) for r in model.Session.execute(select(S.collaborators).where(
        S.collaborators.c.activity_id == activity.id)).fetchall()]
    history = [_serialize(r) for r in model.Session.execute(select(S.revisions.c.revision,
        S.revisions.c.user_id, S.revisions.c.created_at, S.revisions.c.snapshot).where(
        S.revisions.c.activity_id == activity.id).order_by(S.revisions.c.revision.desc()).limit(100))]
    for revision in history:
        snapshot = json.loads(revision['snapshot'])
        snapshot['links'] = filtered(snapshot.get('links', []), actor)
        revision['snapshot'] = snapshot
    return {'candidates': list(candidates.values()), 'collaborators': members,
            'history': history, 'can_invite': activity.is_owned_by(actor) or actor.sysadmin}


def ihpix_report_collaborator_update(context, data):
    actor, activity = report_access(context, tk.get_or_bust(data, 'id'), author=True)
    # Serializa invitaciones y revocaciones contra el mismo reporte.
    activity = model.Session.query(IhpixActivity).filter_by(id=activity.id).with_for_update().populate_existing().one()
    revoke = tk.asbool(data.get('revoke', False))
    if not revoke and (activity.status not in ('draft', 'rejected') or not V.active_workspaces(activity)):
        raise tk.ValidationError({'id': 'Only active draft or rejected reports can be shared'})
    target = model.User.get(tk.get_or_bust(data, 'user_id'))
    if not target or (not revoke and not V.eligible(activity, target)):
        raise tk.ValidationError({'user_id': 'Choose an active contributor of an associated workspace'})
    match = and_(S.collaborators.c.activity_id == activity.id, S.collaborators.c.user_id == target.id)
    existing = model.Session.execute(select(S.collaborators).where(match)).first()
    if existing:
        model.Session.execute(S.collaborators.update().where(match).values(active=not revoke))
    elif not revoke:
        model.Session.execute(S.collaborators.insert().values(id=S.uid(), activity_id=activity.id,
            user_id=target.id, invited_by=actor.id, active=True, created_at=S.now()))
    if not revoke and (not existing or not existing.active):
        S.notify(target.id, 'You were invited to collaborate on an IHP-IX report', '/ihpix/report/' + activity.id + '/edit')
    model.Session.commit()
    return {'success': True}


@tk.side_effect_free
def ihpix_notification_list(context, data):
    actor = user(context)
    return {'results': [_serialize(r) for r in model.Session.execute(select(S.notifications).where(
        S.notifications.c.user_id == actor.id).order_by(S.notifications.c.created_at.desc()).limit(100))]}


def ihpix_notification_read(context, data):
    actor = user(context)
    model.Session.execute(S.notifications.update().where(
        S.notifications.c.user_id == actor.id, S.notifications.c.id == tk.get_or_bust(data, 'id'))
        .values(is_read=True))
    model.Session.commit()
    return {'success': True}


ACTIONS = {name: value for name, value in list(globals().items()) if name.startswith('ihpix_') and callable(value)}
