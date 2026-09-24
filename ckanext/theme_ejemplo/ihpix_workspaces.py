# -*- coding: utf-8 -*-
u"""Reglas del piloto de "Collaborative IHP-IX working groups".

Módulo puro (sin CKAN): constantes, transiciones de membresía y reglas de
permiso sobre dicts/objetos simples, para poder testearlas sin la pila
CKAN. La persistencia (ledger, membresías) vive en `actions.py`.

Un *workspace* es un working group por Output IHP-IX (34, sembrados desde
`ihpix_constants.OUTPUTS`). Roles de miembro: lead (gestiona), contributor,
observer. Estados de membresía: pending → active → removed.
"""
from __future__ import unicode_literals

from collections import OrderedDict

ROLE_LEAD = 'lead'
ROLE_CONTRIBUTOR = 'contributor'
ROLE_OBSERVER = 'observer'
ROLES = (ROLE_LEAD, ROLE_CONTRIBUTOR, ROLE_OBSERVER)

MEMBER_PENDING = 'pending'
MEMBER_ACTIVE = 'active'
MEMBER_REMOVED = 'removed'
MEMBER_STATUSES = (MEMBER_PENDING, MEMBER_ACTIVE, MEMBER_REMOVED)

WG_ACTIVE = 'active'
WG_ARCHIVED = 'archived'
WG_STATUSES = (WG_ACTIVE, WG_ARCHIVED)

# Tipos de contribución del ledger (`ihpix_contribution.kind`)
CONTRIBUTION_KINDS = OrderedDict([
    ('report_submitted', 'Report submitted for review'),
    ('report_published', 'Report published'),
    ('link_added', 'Publication, event or data attached'),
    ('member_joined', 'Joined the working group'),
    ('comment', 'Comment'),  # reservado: sin UI en el piloto
])

ROLE_LABELS = OrderedDict([
    (ROLE_LEAD, 'Lead'),
    (ROLE_CONTRIBUTOR, 'Contributor'),
    (ROLE_OBSERVER, 'Observer'),
])

MEMBER_STATUS_LABELS = OrderedDict([
    (MEMBER_PENDING, 'Pending approval'),
    (MEMBER_ACTIVE, 'Active'),
    (MEMBER_REMOVED, 'Removed'),
])

# Acciones de gestión de miembros → (estados de origen, estado destino)
MEMBER_ACTIONS = OrderedDict([
    ('approve', ((MEMBER_PENDING,), MEMBER_ACTIVE)),
    ('reject', ((MEMBER_PENDING,), MEMBER_REMOVED)),
    ('remove', ((MEMBER_ACTIVE,), MEMBER_REMOVED)),
    ('set_role', ((MEMBER_ACTIVE,), MEMBER_ACTIVE)),
    ('reinstate', ((MEMBER_REMOVED,), MEMBER_ACTIVE)),
])


class WorkspaceRuleError(Exception):
    u"""Regla de negocio violada: `.errors` es {campo: mensaje}."""

    def __init__(self, errors):
        self.errors = dict(errors)
        super(WorkspaceRuleError, self).__init__(str(self.errors))


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def resolve_join_status(open_join):
    u"""Estado inicial de una solicitud de ingreso según la config
    `ckanext.theme_ejemplo.ihpix_wg_open_join`."""
    return MEMBER_ACTIVE if open_join else MEMBER_PENDING


def is_lead(membership):
    return bool(membership) and (
        _get(membership, 'role') == ROLE_LEAD
        and _get(membership, 'status') == MEMBER_ACTIVE)


def can_manage(workspace, user_id, membership=None, is_sysadmin=False):
    u"""True si el usuario puede gestionar el workspace: sysadmin, el
    `lead_user_id` del workspace o un miembro activo con rol lead."""
    if is_sysadmin:
        return True
    if not user_id:
        return False
    if _get(workspace, 'lead_user_id') == user_id:
        return True
    return is_lead(membership)


def can_view_pending(workspace, user_id, membership=None, is_sysadmin=False):
    u"""Las solicitudes pendientes solo las ven quienes gestionan."""
    return can_manage(workspace, user_id, membership, is_sysadmin)


def validate_member_action(membership, action, actor_user_id, actor_can_manage,
                           role=None):
    u"""Valida una transición de membresía. Devuelve (new_status, new_role).

    Reglas:
    - Solo quien gestiona (lead/sysadmin) puede ejecutar acciones.
    - Un lead no puede quitarse a sí mismo (evita workspaces sin gestor).
    - `set_role` exige un rol válido.
    - La transición debe partir de un estado permitido (`MEMBER_ACTIONS`).
    """
    errors = {}
    if action not in MEMBER_ACTIONS:
        raise WorkspaceRuleError({'action': 'Must be one of: {}'.format(
            ', '.join(MEMBER_ACTIONS))})
    if not actor_can_manage:
        raise WorkspaceRuleError({'action': 'Only the working group lead or a '
                                            'sysadmin can manage members'})
    allowed_from, target_status = MEMBER_ACTIONS[action]
    current = _get(membership, 'status')
    if current not in allowed_from:
        errors['status'] = "Cannot {} a membership in status '{}'".format(
            action, current)
    new_role = _get(membership, 'role') or ROLE_CONTRIBUTOR
    if action == 'set_role':
        if role not in ROLES:
            errors['role'] = 'Must be one of: {}'.format(', '.join(ROLES))
        else:
            new_role = role
    if action in ('remove', 'set_role') and (
            _get(membership, 'user_id') == actor_user_id
            and _get(membership, 'role') == ROLE_LEAD
            and (action == 'remove' or new_role != ROLE_LEAD)):
        errors['user_id'] = 'A lead cannot remove or demote themselves'
    if errors:
        raise WorkspaceRuleError(errors)
    return target_status, new_role


def validate_join(workspace, membership):
    u"""Reglas para solicitar ingreso: workspace activo y sin membresía
    pendiente/activa previa. Devuelve True si hay que reactivar una
    membresía `removed` en lugar de crear una nueva."""
    if _get(workspace, 'status') != WG_ACTIVE:
        raise WorkspaceRuleError({'id': 'This working group is archived'})
    status = _get(membership, 'status') if membership else None
    if status in (MEMBER_PENDING, MEMBER_ACTIVE):
        raise WorkspaceRuleError({'user_id': 'You already belong to (or have '
                                             'requested to join) this working group'})
    return status == MEMBER_REMOVED


def contribution_label(kind):
    return CONTRIBUTION_KINDS.get(kind, kind or '')


def role_label(role):
    return ROLE_LABELS.get(role, role or '')


def member_status_label(status):
    return MEMBER_STATUS_LABELS.get(status, status or '')


def workspace_title(code, output_title=''):
    u"""Título por defecto de un workspace: 'Output 1.3 – Título' o 'Output 1.3'."""
    if output_title:
        return 'Output {} – {}'.format(code, output_title)
    return 'Output {}'.format(code)
