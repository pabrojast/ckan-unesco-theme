# encoding: utf-8
"""Membresía moderada de iniciativas: acciones, permisos y helpers."""

import datetime
import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.common import current_user, g

from .model import InitiativeMembershipRequest as MembershipRequest
from .utils import normalize_user_image_url

log = logging.getLogger(__name__)
_ = toolkit._


def _actor(context):
    user = context.get('auth_user_obj') or model.User.get(context.get('user'))
    return user if user and user.state == 'active' else None


def initiative_query():
    """Misma clasificación que /initiatives, sin caché para autorizar cambios."""
    query = model.Session.query(model.Group).filter(
        model.Group.type == 'group', model.Group.state == 'active',
        model.Group.is_organization == False,  # noqa: E712
        model.Group.name != 'member-states',
    )
    parent = model.Group.get('member-states')
    if parent:
        countries = model.Session.query(model.Member.table_id).filter(
            model.Member.group_id == parent.id,
            model.Member.table_name == 'group', model.Member.state == 'active')
        query = query.filter(~model.Group.id.in_(countries))
    return query


def get_initiative(identifier, lock=False):
    group = model.Group.get(identifier)
    query = initiative_query().filter(model.Group.id == group.id) if group else None
    if query is not None and lock:
        query = query.populate_existing().with_for_update()
    group = query.first() if query is not None else None
    if not group:
        raise toolkit.ObjectNotFound(_('Initiative not found'))
    return group


def _member(user_id, group_id):
    return model.Session.query(model.Member).filter(
        model.Member.table_name == 'user', model.Member.table_id == user_id,
        model.Member.group_id == group_id, model.Member.state == 'active').populate_existing().first()


def can_manage(user, group_id):
    if not user or user.state != 'active':
        return False
    if user.sysadmin:
        return True
    member = _member(user.id, group_id)
    return bool(member and member.capacity == 'admin')


def _pending(user_id, group_id):
    return model.Session.query(MembershipRequest).filter_by(
        user_id=user_id, group_id=group_id, status='pending').first()


def _authenticated(context, data_dict):
    return {'success': bool(_actor(context)), 'msg': _('Must be logged in')}


def _manage_auth(context, data_dict):
    try:
        group = get_initiative(data_dict.get('group_id'))
        allowed = can_manage(_actor(context), group.id)
        if data_dict.get('id'):
            req = model.Session.query(MembershipRequest).get(data_dict['id'])
            allowed = allowed and bool(req and req.group_id == group.id)
        return {'success': allowed}
    except toolkit.ObjectNotFound:
        return {'success': False}


def _group_dict(group):
    return toolkit.get_action('group_show')(
        {'ignore_auth': True}, {'id': group.id, 'include_datasets': False,
                                'include_users': False})


def _reviewers(group_id):
    admin_ids = model.Session.query(model.Member.table_id).filter(
        model.Member.group_id == group_id, model.Member.table_name == 'user',
        model.Member.capacity == 'admin', model.Member.state == 'active')
    return model.Session.query(model.User).filter(
        model.User.state == 'active',
        (model.User.id.in_(admin_ids)) | (model.User.sysadmin == True)).all()  # noqa: E712


def _after_change(req, group, created=False):
    """Avisos posteriores al commit: un fallo SMTP nunca revierte la decisión."""
    from ckan.lib import mailer
    from . import approvals
    try:
        reviewers = _reviewers(group.id)
        for reviewer in reviewers:
            approvals.invalidate(reviewer.id)
        title = group.title or group.name
        requester = model.User.get(req.user_id)
        if created:
            # Si no hay admins locales activos, los sysadmins reciben el aviso.
            local_admins = [user for user in reviewers
                            if _member(user.id, group.id) and
                            _member(user.id, group.id).capacity == 'admin']
            recipients = local_admins or reviewers
            subject = _('Request to join initiative: {title}').format(title=title)
            body = _('{name} has requested to join the initiative "{title}".\n\n'
                     'Message:\n{message}\n\nReview the request: {url}').format(
                name=requester.fullname or requester.name, title=title,
                message=req.message or _('No message provided'),
                url=toolkit.url_for('theme_ejemplo.initiative_membership_requests',
                                    name=group.name, qualified=True))
        else:
            recipients = [requester] if requester else []
            subject = _('Your membership request for {title}').format(title=title)
            decision = _('Approved') if req.status == 'approved' else _('Rejected')
            body = _('Your request to join the initiative "{title}" was reviewed.\n\n'
                     'Decision: {decision}\n{note}\n\nInitiative: {url}').format(
                title=title, decision=decision, note=req.admin_note or '',
                url=toolkit.url_for('group.read', id=group.name, qualified=True))
        for recipient in recipients:
            if recipient and recipient.email:
                try:
                    mailer.mail_user(recipient, subject, body)
                except Exception:
                    log.warning('No se pudo enviar el aviso de membresía de iniciativa',
                                exc_info=True)
    except Exception:
        log.warning('No se pudieron completar los avisos de membresía de iniciativa',
                    exc_info=True)


def initiative_membership_request_create(context, data_dict):
    """Solicita incorporarse; group_id acepta UUID o nombre, message es opcional."""
    toolkit.check_access('initiative_membership_request_create', context, data_dict)
    user = _actor(context)
    if not user:
        raise toolkit.NotAuthorized(_('Must be logged in'))
    group = get_initiative(toolkit.get_or_bust(data_dict, 'group_id'), lock=True)
    if _member(user.id, group.id):
        raise toolkit.ValidationError({'group_id': [_('You are already a member of this initiative.')]})
    if _pending(user.id, group.id):
        raise toolkit.ValidationError({'group_id': [_('You already have a pending request for this initiative.')]})
    message = data_dict.get('message') or ''
    if not isinstance(message, str):
        raise toolkit.ValidationError({'message': [_('Message must be text.')]})
    req = MembershipRequest(user.id, group.id, message.strip())
    model.Session.add(req)
    try:
        model.Session.commit()
    except IntegrityError as error:
        model.Session.rollback()
        if getattr(getattr(error.orig, 'diag', None), 'constraint_name', '') == 'initiative_membership_pending_unique':
            raise toolkit.ValidationError({'group_id': [_('You already have a pending request for this initiative.')]})
        raise
    _after_change(req, group, created=True)
    return req.as_dict()


@toolkit.side_effect_free
def initiative_membership_request_list(context, data_dict):
    """Pendientes o historial, visibles sólo para administradores autorizados."""
    toolkit.check_access('initiative_membership_request_list', context, data_dict)
    group = get_initiative(toolkit.get_or_bust(data_dict, 'group_id'))
    status = data_dict.get('status')
    if status not in (None, 'pending', 'approved', 'rejected'):
        raise toolkit.ValidationError({'status': [_('Invalid request status.')]})
    query = model.Session.query(MembershipRequest).filter_by(group_id=group.id)
    if status:
        query = query.filter_by(status=status)
    results = []
    for req in query.order_by(MembershipRequest.created_at.desc()).all():
        row = req.as_dict()
        user = model.User.get(req.user_id)
        handler = model.User.get(req.handled_by) if req.handled_by else None
        row.update(user_name=user.name if user else '',
                   user_fullname=(user.fullname or user.name) if user else _('Deleted user'),
                   user_image_url=normalize_user_image_url(user.image_url) if user else '',
                   handler_name=(handler.fullname or handler.name) if handler else '')
        results.append(row)
    return {'group': _group_dict(group), 'results': results, 'count': len(results)}


def initiative_membership_request_process(context, data_dict):
    """Resuelve una solicitud de la iniciativa indicada, de forma transaccional."""
    toolkit.check_access('initiative_membership_request_process', context, data_dict)
    reviewer = _actor(context)
    if not reviewer:
        raise toolkit.NotAuthorized(_('Must be logged in'))
    action = toolkit.get_or_bust(data_dict, 'action')
    role = data_dict.get('role', 'member')
    if action not in ('approve', 'reject'):
        raise toolkit.ValidationError({'action': [_('Must be "approve" or "reject"')]})
    if role not in ('member', 'editor', 'admin'):
        raise toolkit.ValidationError({'role': [_('Invalid membership role.')]})
    note = data_dict.get('admin_note') or ''
    if not isinstance(note, str):
        raise toolkit.ValidationError({'admin_note': [_('Message must be text.')]})
    group = get_initiative(toolkit.get_or_bust(data_dict, 'group_id'), lock=True)
    if not can_manage(reviewer, group.id):
        raise toolkit.NotAuthorized(_('Only initiative administrators can manage membership requests.'))
    req = model.Session.query(MembershipRequest).filter_by(
        id=toolkit.get_or_bust(data_dict, 'id'), group_id=group.id
    ).populate_existing().with_for_update().first()
    if not req:
        raise toolkit.ObjectNotFound(_('Membership request not found'))
    if req.status != 'pending':
        raise toolkit.ValidationError({'status': [_('This request has already been processed.')]})
    try:
        if action == 'approve':
            user = model.User.get(req.user_id)
            if not user or user.state != 'active':
                raise toolkit.ValidationError({'user_id': [_('The applicant is no longer an active user.')]})
            member = _member(req.user_id, group.id)
            if member:
                role = member.capacity
            else:
                toolkit.get_action('member_create')(
                    dict(context, model=model, ignore_auth=True, defer_commit=True),
                    {'id': group.id, 'object': req.user_id,
                     'object_type': 'user', 'capacity': role})
            req.role = role
        req.status = 'approved' if action == 'approve' else 'rejected'
        req.handled_by = reviewer.id
        req.handled_at = datetime.datetime.utcnow()
        req.admin_note = note.strip()
        model.Session.commit()
    except Exception:
        model.Session.rollback()
        raise
    _after_change(req, group)
    return req.as_dict()


def pending_groups(user):
    """Conteo por iniciativa para el resumen y la campana del usuario actual."""
    if not user:
        return []
    query = initiative_query()
    if not user.sysadmin:
        admin_groups = model.Session.query(model.Member.group_id).filter(
            model.Member.table_name == 'user', model.Member.table_id == user.id,
            model.Member.state == 'active', model.Member.capacity == 'admin')
        query = query.filter(model.Group.id.in_(admin_groups))
    return query.join(MembershipRequest, MembershipRequest.group_id == model.Group.id).filter(
        MembershipRequest.status == 'pending').with_entities(
            model.Group.id, model.Group.name, model.Group.title, model.Group.image_url,
            func.count(MembershipRequest.id).label('pending_count')
        ).group_by(model.Group.id).order_by(model.Group.title, model.Group.name).all()


@toolkit.side_effect_free
def initiative_membership_request_count(context, data_dict):
    toolkit.check_access('initiative_membership_request_count', context, data_dict)
    return {'count': sum(row.pending_count for row in pending_groups(_actor(context)))}


def initiative_membership_state(group_dict):
    """Estado público mínimo para los botones; nunca expone mensajes privados."""
    state = dict(eligible=False, member=False, pending=False, can_manage=False, count=0)
    if not current_user or not current_user.is_authenticated:
        return state
    key = (group_dict.get('id'), current_user.id)
    cache = getattr(g, '_initiative_membership_state', {})
    if key in cache:
        return cache[key]
    try:
        group = get_initiative(group_dict.get('id'))
    except toolkit.ObjectNotFound:
        return state
    state.update(eligible=True, member=bool(_member(current_user.id, group.id)),
                 pending=bool(_pending(current_user.id, group.id)),
                 can_manage=can_manage(current_user, group.id))
    if state['can_manage']:
        state['count'] = model.Session.query(MembershipRequest).filter_by(
            group_id=group.id, status='pending').count()
    cache[key] = state
    g._initiative_membership_state = cache
    return state


def get_pending_initiative_memberships_count():
    if not current_user or not current_user.is_authenticated:
        return 0
    return sum(row.pending_count for row in pending_groups(current_user))


def get_actions():
    return {name: globals()[name] for name in (
        'initiative_membership_request_create', 'initiative_membership_request_list',
        'initiative_membership_request_process', 'initiative_membership_request_count')}


def get_auth_functions():
    return {'initiative_membership_request_create': _authenticated,
            'initiative_membership_request_count': _authenticated,
            'initiative_membership_request_list': _manage_auth,
            'initiative_membership_request_process': _manage_auth}


def get_helpers():
    return {'initiative_membership_state': initiative_membership_state,
            'get_pending_initiative_memberships_count': get_pending_initiative_memberships_count}
