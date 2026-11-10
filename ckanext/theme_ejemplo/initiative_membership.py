"""Solicitudes de administración limitadas a una iniciativa concreta."""
import datetime as dt
import logging
import os
import uuid

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan import authz

log = logging.getLogger(__name__)
CONFIG = 'ckanext.theme_ejemplo.initiative_membership_requests_enabled'
ENV = 'CKANEXT__THEME_EJEMPLO__INITIATIVE_MEMBERSHIP_REQUESTS_ENABLED'
metadata = sa.MetaData()
requests = sa.Table(
    'initiative_membership_request', metadata,
    sa.Column('id', sa.UnicodeText, primary_key=True),
    sa.Column('group_id', sa.UnicodeText, nullable=False),
    sa.Column('user_id', sa.UnicodeText, nullable=False),
    sa.Column('message', sa.UnicodeText, nullable=False, default=''),
    sa.Column('status', sa.UnicodeText, nullable=False, default='pending'),
    sa.Column('created_at', sa.DateTime, nullable=False),
    sa.Column('handled_by', sa.UnicodeText),
    sa.Column('handled_at', sa.DateTime),
    sa.Column('admin_note', sa.UnicodeText),
    sa.Column('prior_capacity', sa.UnicodeText),
    sa.Column('member_id', sa.UnicodeText),
)
sa.Index('initiative_membership_pending_unique', requests.c.group_id,
         requests.c.user_id, unique=True,
         postgresql_where=requests.c.status == 'pending')
scopes = sa.Table(
    'initiative_admin_scope', metadata,
    sa.Column('member_id', sa.UnicodeText, primary_key=True),
    sa.Column('group_id', sa.UnicodeText, nullable=False),
    sa.Column('user_id', sa.UnicodeText, nullable=False),
    sa.Column('request_id', sa.UnicodeText, nullable=False),
    sa.Column('created_at', sa.DateTime, nullable=False),
)


def init_db():
    # Serializar DDL entre réplicas; las tablas son aditivas e idempotentes.
    with model.meta.engine.begin() as conn:
        conn.execute(sa.text('SELECT pg_advisory_xact_lock(19591110)'))
        metadata.create_all(conn)


def enabled():
    return (tk.asbool(os.environ.get(ENV, tk.config.get(CONFIG, False)))
            and getattr(authz, 'INITIATIVE_ADMIN_SCOPE_GUARD', False))


def _require_enabled():
    if not enabled():
        raise tk.NotAuthorized(tk._('Initiative access requests are not enabled.'))


def _actor(context):
    user = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if not user or getattr(user, 'state', None) != 'active':
        raise tk.NotAuthorized(tk._('An active account is required.'))
    return user


def _group(value):
    # Consultar pertenencia a Estados miembros directamente; fallar cerrado.
    group = model.Group.get(value)
    if not group or group.state != 'active' or group.is_organization or group.type != 'group':
        raise tk.ObjectNotFound(tk._('Initiative not found.'))
    member_states = model.Group.get('member-states')
    if group.name == 'member-states' or (member_states and model.Session.query(model.Member.id).filter(
            model.Member.group_id == member_states.id,
            model.Member.table_id == group.id,
            model.Member.table_name == 'group',
            model.Member.state == 'active').first()):
        raise tk.ObjectNotFound(tk._('Initiative not found.'))
    return group


def _membership(user_id, group_id):
    return model.Session.query(model.Member).filter_by(
        group_id=group_id, table_id=user_id, table_name='user', state='active').first()


def can_review(user, group):
    if not user or getattr(user, 'state', None) != 'active':
        return False
    member = _membership(user.id, group.id)
    return bool(user.sysadmin or (member and member.capacity == 'admin'))


def _reviewer(context, group):
    user = _actor(context)
    if not can_review(user, group):
        raise tk.NotAuthorized(tk._('Only administrators of this initiative can review requests.'))
    return user


def _row(request_id, lock=False):
    query = sa.select(requests).where(requests.c.id == request_id)
    if lock:
        query = query.with_for_update()
    row = model.Session.execute(query).mappings().first()
    if row is None:
        raise tk.ObjectNotFound(tk._('Request not found.'))
    return dict(row)


def _serialize(row):
    result = dict(row)
    for key in ('created_at', 'handled_at'):
        if result.get(key):
            result[key] = result[key].isoformat()
    user = model.User.get(result['user_id'])
    result['user_name'] = user.name if user else ''
    result['user_fullname'] = (user.fullname or user.name) if user else ''
    result['role'] = 'admin'
    return result


def _text(data, key, limit):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > limit:
        raise tk.ValidationError({key: [tk._('Invalid or overly long text.')]})
    return value.strip()


def _reviewer_ids(group):
    ids = [r[0] for r in model.Session.query(model.Member.table_id).join(
        model.User, model.User.id == model.Member.table_id).filter(
            model.Member.group_id == group.id, model.Member.table_name == 'user',
            model.Member.capacity == 'admin', model.Member.state == 'active',
            model.User.state == 'active').all()]
    return ids or [u.id for u in model.Session.query(model.User).filter_by(
        sysadmin=True, state='active').all()]


def _after_commit(group, request_row, created=False):
    from . import approvals
    from ckan.lib import mailer
    reviewer_ids = _reviewer_ids(group)
    global_ids = [u.id for u in model.Session.query(model.User).filter_by(sysadmin=True, state='active').all()]
    for user_id in set(reviewer_ids + global_ids + [request_row['user_id']]):
        approvals.invalidate(user_id)
    # El contador de sysadmins usa una clave global independiente.
    approvals.invalidate()
    recipients = reviewer_ids if created else [request_row['user_id']]
    url = tk.config.get('ckan.site_url', '').rstrip('/') + '/group/' + group.name
    subject = tk._('Initiative administrator access: {title}').format(title=group.title or group.name)
    body = (tk._('A request to administer this initiative is awaiting review.') if created else
            tk._('Your initiative administrator access request was {status}.').format(status=request_row['status']))
    body += '\n\n' + url + ('/membership-requests' if created else '')
    for user_id in set(recipients):
        user = model.User.get(user_id)
        if user and user.email:
            try:
                mailer.mail_user(user, subject, body)
            except Exception:
                log.warning('No se pudo enviar el aviso de acceso a iniciativa', exc_info=True)


def initiative_membership_request_create(context, data_dict):
    _require_enabled()
    user = _actor(context)
    group = _group(tk.get_or_bust(data_dict, 'group_id'))
    if can_review(user, group):
        raise tk.ValidationError({'group_id': [tk._('You already administer this initiative.')]})
    row = dict(id=str(uuid.uuid4()), group_id=group.id, user_id=user.id,
               message=_text(data_dict, 'message', 4000), status='pending',
               created_at=dt.datetime.utcnow())
    try:
        model.Session.execute(requests.insert().values(**row))
        model.Session.commit()
    except IntegrityError:
        model.Session.rollback()
        raise tk.ValidationError({'group_id': [tk._('You already have a pending request for this initiative.')]})
    _after_commit(group, row, created=True)
    return _serialize(row)


@tk.side_effect_free
def initiative_membership_request_list(context, data_dict):
    _require_enabled()
    group = _group(tk.get_or_bust(data_dict, 'group_id'))
    _reviewer(context, group)
    query = sa.select(requests).where(requests.c.group_id == group.id)
    status = data_dict.get('status')
    if status:
        if status not in ('pending', 'approved', 'rejected'):
            raise tk.ValidationError({'status': [tk._('Invalid request status.')]})
        query = query.where(requests.c.status == status)
    rows = model.Session.execute(query.order_by(requests.c.created_at.desc())).mappings().all()
    return {'results': [_serialize(r) for r in rows], 'count': len(rows)}


def initiative_membership_request_process(context, data_dict):
    _require_enabled()
    decision = data_dict.get('action')
    if decision not in ('approve', 'reject'):
        raise tk.ValidationError({'action': [tk._('Choose approve or reject.')]})
    request_id = tk.get_or_bust(data_dict, 'id')
    row = _row(request_id)
    group = _group(row['group_id'])
    actor = _reviewer(context, group)
    # El grupo del formulario nunca puede sustituir al destino guardado.
    if data_dict.get('group_id') and _group(data_dict['group_id']).id != group.id:
        raise tk.NotAuthorized(tk._('Request does not belong to this initiative.'))
    desired = 'approved' if decision == 'approve' else 'rejected'
    note = _text(data_dict, 'admin_note', 4000)
    try:
        row = _row(request_id, lock=True)
        if row['status'] != 'pending':
            if row['status'] != desired:
                raise tk.ValidationError({'action': [tk._('This request has already been processed.')]})
            model.Session.rollback()
            return _serialize(row)
        applicant = model.User.get(row['user_id'])
        if not applicant or applicant.state != 'active':
            raise tk.ValidationError({'user_id': [tk._('Applicant is no longer active.')]})
        changes = dict(status=desired, handled_by=actor.id,
                       handled_at=dt.datetime.utcnow(), admin_note=note)
        if decision == 'approve':
            # Serializar membresías y solicitudes del mismo grupo/usuario.
            model.Session.execute(sa.text('SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))'),
                                  {'key': 'initiative-admin:' + group.id + ':' + applicant.id})
            member = _membership(applicant.id, group.id)
            previous = member.capacity if member else None
            changes['prior_capacity'] = previous
            if previous != 'admin':
                # group_member_create de CKAN 2.10 descarta defer_commit al
                # delegar: usar member_create para confirmar membresía y límite
                # en una sola transacción, sin un Admin heredable intermedio.
                tk.get_action('member_create')(
                    dict(context, model=model, user=actor.name, auth_user_obj=actor, defer_commit=True),
                    {'id': group.id, 'object': applicant.id,
                     'object_type': 'user', 'capacity': 'admin'})
                model.Session.flush()
                member = _membership(applicant.id, group.id)
                if not member or member.capacity != 'admin':
                    raise tk.ValidationError({'group_id': [tk._('Administrator access could not be confirmed.')]})
                existing = model.Session.execute(sa.select(scopes.c.member_id).where(
                    scopes.c.member_id == member.id)).first()
                if not existing:
                    model.Session.execute(scopes.insert().values(
                        member_id=member.id, group_id=group.id, user_id=applicant.id,
                        request_id=row['id'], created_at=dt.datetime.utcnow()))
            changes['member_id'] = member.id
        model.Session.execute(requests.update().where(requests.c.id == row['id']).values(**changes))
        model.Session.commit()
    except Exception:
        model.Session.rollback()
        raise
    row.update(changes)
    _after_commit(group, row)
    return _serialize(row)


def review_groups(user):
    # Contar primero: no consultar todas las iniciativas/Estados en cada campana.
    query = model.Session.query(model.Group, sa.func.count(requests.c.id)).join(
        requests, requests.c.group_id == model.Group.id).filter(
        model.Group.type == 'group', model.Group.state == 'active',
        model.Group.is_organization == False, requests.c.status == 'pending')
    if not user.sysadmin:
        query = query.filter(sa.exists().where(
            model.Member.group_id == model.Group.id,
            model.Member.table_name == 'user', model.Member.table_id == user.id,
            model.Member.capacity == 'admin', model.Member.state == 'active'))
    result = []
    for group, count in query.group_by(model.Group.id).all():
        try:
            _group(group.id)
        except tk.ObjectNotFound:
            continue
        if count:
            result.append({'name': group.name, 'title': group.title or group.name, 'count': count})
    return result


@tk.side_effect_free
def initiative_membership_request_count(context, data_dict):
    _require_enabled()
    user = _actor(context)
    return {'count': sum(g['count'] for g in review_groups(user))}


def access_auth(context, data_dict):
    try:
        _require_enabled()
        _actor(context)
        return {'success': True}
    except tk.NotAuthorized:
        return {'success': False}


def review_auth(context, data_dict):
    try:
        _require_enabled()
        group_id = data_dict.get('group_id')
        if data_dict.get('id'):
            group_id = _row(data_dict['id'])['group_id']
        _reviewer(context, _group(group_id))
        return {'success': True}
    except (tk.NotAuthorized, tk.ObjectNotFound):
        return {'success': False}


def _limited_actor_scope(context, group_id):
    user = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if (not user or getattr(user, 'state', None) != 'active'
            or user.sysadmin or context.get('ignore_auth')):
        return None
    group = model.Group.get(group_id)
    if not group or group.is_organization:
        return None
    member = _membership(user.id, group.id)
    if not member or member.capacity != 'admin':
        return None
    return model.Session.execute(sa.select(scopes).where(scopes.c.member_id == member.id)).mappings().first()


def _protect_delegation(original, context, data_dict, partial_update=False):
    # Un Admin limitado tampoco puede delegar un Admin heredable por las
    # pantallas/API nativas de CKAN. Se conserva el alcance al añadir miembros.
    scope = _limited_actor_scope(context, data_dict.get('id'))
    if not scope:
        return original(context, data_dict)
    group_id = scope['group_id']
    # Cambiar padres permitiría heredar a través de otra iniciativa donde el
    # solicitante ya es Admin. Esa relación modifica el alcance de terceros.
    hierarchy_error = tk._('Changing initiative hierarchy requires an unrestricted administrator.')
    if data_dict.get('object_type') == 'group':
        raise tk.NotAuthorized(hierarchy_error)
    def parents():
        return {(m.table_id, m.capacity) for m in model.Session.query(model.Member).filter_by(
            group_id=group_id, table_name='group', state='active').all()}
    previous_parents = parents()
    def admins():
        return model.Session.query(model.Member).filter_by(group_id=group_id,
            table_name='user', state='active', capacity='admin').all()
    previous = {m.id for m in admins()}
    try:
        delegated_context = dict(context, defer_commit=True)
        if partial_update:
            # El formulario normal omite los padres; conservarlos al editar contenido.
            delegated_context['allow_partial_update'] = True
        result = original(delegated_context, data_dict)
        model.Session.flush()
        if parents() != previous_parents:
            raise tk.NotAuthorized(hierarchy_error)
        for member in admins():
            if member.id in previous:
                continue
            found = model.Session.execute(sa.select(scopes.c.member_id).where(scopes.c.member_id == member.id)).first()
            if not found:
                model.Session.execute(scopes.insert().values(member_id=member.id,
                    group_id=group_id, user_id=member.table_id,
                    request_id=scope['request_id'], created_at=dt.datetime.utcnow()))
        if not context.get('defer_commit'):
            model.Session.commit()
        return result
    except Exception:
        model.Session.rollback()
        raise


@tk.chained_action
def scoped_member_create(original, context, data_dict):
    return _protect_delegation(original, context, data_dict)


@tk.chained_action
def scoped_group_update(original, context, data_dict):
    return _protect_delegation(original, context, data_dict, partial_update=True)


@tk.chained_action
def scoped_organization_update(original, context, data_dict):
    # CKAN acepta group IDs en organization_update directo. No permitir que
    # ese alias evite las protecciones de miembros y jerarquía de iniciativas.
    if _limited_actor_scope(context, data_dict.get('id')):
        raise tk.NotAuthorized(tk._('Use initiative actions to update this initiative.'))
    return original(context, data_dict)


ACTIONS = {f.__name__: f for f in (
    initiative_membership_request_create, initiative_membership_request_list,
    initiative_membership_request_process, initiative_membership_request_count)}
AUTH = {name: (review_auth if name.endswith(('_list', '_process')) else access_auth)
        for name in ACTIONS}
ACTIONS.update(member_create=scoped_member_create, group_update=scoped_group_update,
               organization_update=scoped_organization_update)
