# encoding: utf-8
"""Custom action overrides for People & Organizations feature."""

import json
import logging
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user
from sqlalchemy.orm.attributes import flag_modified
from ckanext.theme_ejemplo.utils import (
    get_invalid_user_image_upload_reason,
    is_valid_user_image_reference,
    normalize_user_image_url,
)
from ckanext.theme_ejemplo.helpers import get_member_state_title
from ckanext.theme_ejemplo import search as theme_search

log = logging.getLogger(__name__)


def _invalidate_approvals_cache(user_id=None):
    """Refresh the header approvals bell right after processing a queue item."""
    try:
        from ckanext.theme_ejemplo import approvals
        approvals.invalidate(user_id)
    except Exception:
        pass


PROFILE_FIELDS = [
    'job_title', 'institution', 'country', 'phone',
    'website', 'orcid', 'expertise_areas', 'social_links',
    'member_states',
]


@toolkit.side_effect_free
def user_show(context, data_dict):
    """Override user_show to expose profile fields from plugin_extras."""
    result = logic.action.get.user_show(context, data_dict)

    # Read plugin_extras directly from model — core may not include it
    # in the result dict depending on CKAN version and auth context
    user_obj = model.User.get(result['id'])
    plugin_extras = (user_obj.plugin_extras or {}) if user_obj else {}
    profile = plugin_extras.get('theme_ejemplo', {})

    for field in PROFILE_FIELDS:
        val = profile.get(field, '')
        if field in ('expertise_areas', 'social_links', 'member_states') and isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                if field == 'social_links':
                    val = {}
                else:
                    val = []
        result[field] = val

    # Backward compat: si no hay member_states pero sí country, derivar
    if not result.get('member_states') and result.get('country'):
        result['member_states'] = [result['country']]

    # Always expose plugin_extras.theme_ejemplo as 'profile' for convenience
    result['profile'] = profile

    # Resolve member state slug to display title
    country_slug = result.get('country', '')
    result['country_display'] = get_member_state_title(country_slug) if country_slug else ''

    # Resolve all member state slugs to display titles
    result['member_states_display'] = [
        {'name': ms, 'title': get_member_state_title(ms)}
        for ms in (result.get('member_states') or [])
        if ms
    ]

    # Expose user's CKAN organizations (with capacity/role)
    try:
        user_obj2 = user_obj or model.User.get(result['id'])
        if user_obj2:
            # Build capacity map
            capacity_map = {}
            for g in user_obj2.get_groups('organization'):
                try:
                    members = toolkit.get_action('member_list')(
                        {'ignore_auth': True},
                        {'id': g.id, 'object_type': 'user'},
                    )
                    for uid, _otype, cap in members:
                        if uid == user_obj2.id:
                            capacity_map[g.id] = cap
                            break
                except Exception:
                    pass

            orgs = []
            for g in user_obj2.get_groups('organization'):
                orgs.append({
                    'id': g.id,
                    'name': g.name,
                    'title': g.title or g.name,
                    'image_url': g.image_url or '',
                    'capacity': capacity_map.get(g.id, 'member'),
                })
            result['organizations'] = orgs
        else:
            result['organizations'] = []
    except Exception:
        result['organizations'] = []

    return result


def user_update(context, data_dict):
    """Override user_update to save extra profile fields into plugin_extras."""
    # Extract profile fields before passing to core
    profile_data = {}
    for field in PROFILE_FIELDS:
        if field in data_dict:
            val = data_dict.pop(field)
            if field == 'expertise_areas' and isinstance(val, str):
                areas = [a.strip() for a in val.split(',') if a.strip()]
                val = json.dumps(areas)
            if field == 'member_states' and isinstance(val, str):
                states = [s.strip() for s in val.split(',') if s.strip()]
                val = json.dumps(states)
            profile_data[field] = val

    # Extract org role changes (sysadmin only, keys like org_role_<org_id>)
    org_role_changes = {}
    keys_to_pop = [k for k in data_dict if k.startswith('org_role_')]
    for key in keys_to_pop:
        org_id = key[len('org_role_'):]
        new_capacity = data_dict.pop(key)
        if new_capacity in ('member', 'editor', 'admin'):
            org_role_changes[org_id] = new_capacity

    # Assemble social_links from individual form fields (social_links_linkedin, etc.)
    social_keys = ['linkedin', 'twitter', 'researchgate', 'github', 'website']
    social_from_form = {}
    for sk in social_keys:
        form_key = f'social_links_{sk}'
        if form_key in data_dict:
            val = data_dict.pop(form_key)
            if val and val.strip():
                social_from_form[sk] = val.strip()
    if social_from_form:
        profile_data['social_links'] = json.dumps(social_from_form)

    invalid_image_upload_reason = get_invalid_user_image_upload_reason(
        data_dict.get('image_upload')
    )
    if invalid_image_upload_reason:
        log.warning(
            'Rejected invalid profile image upload for user %s: %s',
            context.get('user'),
            invalid_image_upload_reason,
        )
        raise toolkit.ValidationError({
            'image_upload': [toolkit._(
                'Profile picture must be a valid image file. Allowed formats: '
                'PNG, JPG, JPEG, GIF, WEBP, BMP, TIFF and AVIF.'
            )]
        })

    if data_dict.get('image_url') and not is_valid_user_image_reference(
        data_dict['image_url']
    ):
        data_dict['image_url'] = ''

    # Call core user_update
    result = logic.action.update.user_update(context, data_dict)

    # Save profile fields into plugin_extras
    if profile_data:
        user_obj = model.User.get(result['id'])
        if user_obj:
            extras = user_obj.plugin_extras or {}
            if 'theme_ejemplo' not in extras:
                extras['theme_ejemplo'] = {}

            old_country = extras['theme_ejemplo'].get('country', '')
            new_country = profile_data.get('country', old_country)

            # Leer member_states anterior (backward compat con country)
            old_ms_raw = extras['theme_ejemplo'].get('member_states', '[]')
            if isinstance(old_ms_raw, str):
                try:
                    old_member_states = json.loads(old_ms_raw)
                except (json.JSONDecodeError, TypeError):
                    old_member_states = []
            elif isinstance(old_ms_raw, list):
                old_member_states = old_ms_raw
            else:
                old_member_states = []
            if not old_member_states and old_country:
                old_member_states = [old_country]

            extras['theme_ejemplo'].update(profile_data)

            # Derivar country del primer member_state para backward compat
            if 'member_states' in profile_data:
                new_ms_raw = profile_data['member_states']
                if isinstance(new_ms_raw, str):
                    try:
                        new_member_states = json.loads(new_ms_raw)
                    except (json.JSONDecodeError, TypeError):
                        new_member_states = []
                elif isinstance(new_ms_raw, list):
                    new_member_states = new_ms_raw
                else:
                    new_member_states = []
                extras['theme_ejemplo']['country'] = new_member_states[0] if new_member_states else ''
            else:
                new_member_states = old_member_states

            user_obj.plugin_extras = extras
            flag_modified(user_obj, 'plugin_extras')
            model.Session.commit()

            # Sincronizar membresías en grupos de member states
            if 'member_states' in profile_data:
                _sync_member_state_memberships(
                    user_obj.id, old_member_states, new_member_states
                )
            elif 'country' in profile_data and old_country != new_country:
                _sync_member_state_membership(
                    user_obj.id, old_country, new_country
                )

            # Update result with saved profile
            for field in PROFILE_FIELDS:
                val = extras['theme_ejemplo'].get(field, '')
                if field in ('expertise_areas', 'social_links', 'member_states') and isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        if field == 'social_links':
                            val = {}
                        else:
                            val = []
                result[field] = val
            result['profile'] = extras.get('theme_ejemplo', {})

    # Apply org role changes (sysadmin only)
    if org_role_changes:
        calling_user = context.get('user')
        caller = model.User.get(calling_user) if calling_user else None
        if caller and caller.sysadmin:
            _apply_org_role_changes(result['id'], org_role_changes)

    return result


def _sync_member_state_membership(user_id, old_group_name, new_group_name):
    """Add/remove user from member state CKAN groups when profile country changes.

    This keeps the ``/group/<name>/members`` tab in sync with the profile
    country field so users who select a member state actually appear listed.
    """
    site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    admin_context = {'user': site_user['name'], 'ignore_auth': True}

    # Remove from old member state group
    if old_group_name:
        try:
            old_group = model.Group.get(old_group_name)
            if old_group and old_group.type == 'group':
                toolkit.get_action('member_delete')(
                    dict(admin_context),
                    {
                        'id': old_group.id,
                        'object': user_id,
                        'object_type': 'user',
                    },
                )
                log.info(
                    'Removed user %s from member state group %s',
                    user_id, old_group_name,
                )
        except toolkit.ObjectNotFound:
            pass
        except Exception as e:
            log.warning(
                'Could not remove user %s from group %s: %s',
                user_id, old_group_name, e,
            )

    # Add to new member state group
    if new_group_name:
        try:
            new_group = model.Group.get(new_group_name)
            if new_group and new_group.type == 'group':
                toolkit.get_action('member_create')(
                    dict(admin_context),
                    {
                        'id': new_group.id,
                        'object': user_id,
                        'object_type': 'user',
                        'capacity': 'member',
                    },
                )
                log.info(
                    'Added user %s to member state group %s',
                    user_id, new_group_name,
                )
        except Exception as e:
            log.warning(
                'Could not add user %s to group %s: %s',
                user_id, new_group_name, e,
            )


def _sync_member_state_memberships(user_id, old_states, new_states):
    """Sincroniza membresías de grupos de member states cuando cambia la lista.

    Compara la lista anterior con la nueva y agrega/elimina según corresponda.
    """
    old_set = set(s for s in old_states if s)
    new_set = set(s for s in new_states if s)

    to_remove = old_set - new_set
    to_add = new_set - old_set

    if not to_remove and not to_add:
        return

    site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    admin_context = {'user': site_user['name'], 'ignore_auth': True}

    for group_name in to_remove:
        try:
            group = model.Group.get(group_name)
            if group and group.type == 'group':
                toolkit.get_action('member_delete')(
                    dict(admin_context),
                    {
                        'id': group.id,
                        'object': user_id,
                        'object_type': 'user',
                    },
                )
                log.info(
                    'Removed user %s from member state group %s',
                    user_id, group_name,
                )
        except toolkit.ObjectNotFound:
            pass
        except Exception as e:
            log.warning(
                'Could not remove user %s from group %s: %s',
                user_id, group_name, e,
            )

    for group_name in to_add:
        try:
            group = model.Group.get(group_name)
            if group and group.type == 'group':
                toolkit.get_action('member_create')(
                    dict(admin_context),
                    {
                        'id': group.id,
                        'object': user_id,
                        'object_type': 'user',
                        'capacity': 'member',
                    },
                )
                log.info(
                    'Added user %s to member state group %s',
                    user_id, group_name,
                )
        except Exception as e:
            log.warning(
                'Could not add user %s to group %s: %s',
                user_id, group_name, e,
            )


def _apply_org_role_changes(user_id, org_role_changes):
    """Update the user's capacity in each organisation.

    ``org_role_changes`` is a dict mapping organisation **id** to the
    desired capacity (member / editor / admin).  Uses ``member_create``
    which upserts the membership record.
    """
    site_user = toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
    admin_context = {'user': site_user['name'], 'ignore_auth': True}

    for org_id, new_capacity in org_role_changes.items():
        try:
            toolkit.get_action('member_create')(
                dict(admin_context),
                {
                    'id': org_id,
                    'object': user_id,
                    'object_type': 'user',
                    'capacity': new_capacity,
                },
            )
            log.info(
                'Updated user %s role in org %s to %s',
                user_id, org_id, new_capacity,
            )
        except Exception as e:
            log.warning(
                'Could not update user %s role in org %s: %s',
                user_id, org_id, e,
            )


@toolkit.side_effect_free
def people_list(context, data_dict):
    """List active users with their profile information for the people directory."""
    toolkit.check_access('user_list', context, data_dict)

    q = data_dict.get('q', '')
    organization = data_dict.get('organization', '')
    country = data_dict.get('country', '')
    expertise = data_dict.get('expertise', '')
    limit = int(data_dict.get('limit', 21))
    offset = int(data_dict.get('offset', 0))

    query = model.Session.query(model.User).filter(
        model.User.state == 'active',
        model.User.name != 'default',
        model.User.name != 'harvest',
    )

    # Filtro por workspace IHP-IX (miembros activos del working group)
    ihpix_workspace = (data_dict.get('ihpix_workspace') or '').strip()
    ihpix_workspace_user_ids = None
    if ihpix_workspace:
        init_ihpix_working_groups_db()
        wg = IhpixWorkingGroup.get_by_id_or_output(ihpix_workspace)
        ihpix_workspace_user_ids = set(
            m.user_id for m in IhpixWorkingGroupMember.get_for_group(
                wg.id, status=W.MEMBER_ACTIVE)) if wg else set()

    if q:
        # Por tokens, en cualquier orden: "perez juan" encuentra "Juan Perez".
        query = theme_search.filter_by_tokens(
            query, q, [model.User.name, model.User.fullname])

    users = query.order_by(model.User.fullname.asc()).all()

    results = []
    for user_obj in users:
        extras = user_obj.plugin_extras or {}
        profile = extras.get('theme_ejemplo', {})

        # Filtrar por country / member_states
        if country:
            user_ms = profile.get('member_states', '[]')
            if isinstance(user_ms, str):
                try:
                    user_ms = json.loads(user_ms)
                except (json.JSONDecodeError, TypeError):
                    user_ms = []
            if not isinstance(user_ms, list):
                user_ms = []
            # Backward compat: usar country si no hay member_states
            if not user_ms:
                user_country = profile.get('country', '')
                user_ms = [user_country] if user_country else []
            if country.lower() not in [ms.lower() for ms in user_ms]:
                continue

        # Filter by expertise
        if expertise:
            user_expertise = profile.get('expertise_areas', '[]')
            if isinstance(user_expertise, str):
                try:
                    user_expertise = json.loads(user_expertise)
                except (json.JSONDecodeError, TypeError):
                    user_expertise = []
            if not any(expertise.lower() in e.lower() for e in user_expertise):
                continue

        # Filter by organization membership
        if organization:
            org_ids = [g.id for g in user_obj.get_groups('organization')]
            org_names = []
            for g in user_obj.get_groups('organization'):
                org_names.append(g.name)
            if organization not in org_names and organization not in org_ids:
                continue

        if ihpix_workspace_user_ids is not None and user_obj.id not in ihpix_workspace_user_ids:
            continue

        # Parse JSON fields
        expertise_areas = profile.get('expertise_areas', '[]')
        if isinstance(expertise_areas, str):
            try:
                expertise_areas = json.loads(expertise_areas)
            except (json.JSONDecodeError, TypeError):
                expertise_areas = []

        social_links = profile.get('social_links', '{}')
        if isinstance(social_links, str):
            try:
                social_links = json.loads(social_links)
            except (json.JSONDecodeError, TypeError):
                social_links = {}

        orgs = []
        for g in user_obj.get_groups('organization'):
            orgs.append({'name': g.name, 'title': g.title or g.name, 'image_url': g.image_url or ''})

        country_val = profile.get('country', '')
        member_states_raw = profile.get('member_states', '[]')
        if isinstance(member_states_raw, str):
            try:
                member_states_list = json.loads(member_states_raw)
            except (json.JSONDecodeError, TypeError):
                member_states_list = []
        elif isinstance(member_states_raw, list):
            member_states_list = member_states_raw
        else:
            member_states_list = []
        if not member_states_list and country_val:
            member_states_list = [country_val]

        results.append({
            'id': user_obj.id,
            'name': user_obj.name,
            'fullname': user_obj.fullname or user_obj.name,
            'image_url': normalize_user_image_url(user_obj.image_url),
            'job_title': profile.get('job_title', ''),
            'institution': profile.get('institution', ''),
            'country': country_val,
            'country_display': get_member_state_title(country_val) if country_val else '',
            'member_states': member_states_list,
            'member_states_display': [
                {'name': ms, 'title': get_member_state_title(ms)}
                for ms in member_states_list if ms
            ],
            'orcid': profile.get('orcid', ''),
            'expertise_areas': expertise_areas,
            'social_links': social_links,
            'organizations': orgs,
        })

    total = len(results)
    results = results[offset:offset + limit]

    return {
        'results': results,
        'count': total,
    }


@toolkit.side_effect_free
def organization_people(context, data_dict):
    """Get members of an organization with their profile information."""
    org_id = toolkit.get_or_bust(data_dict, 'id')
    toolkit.check_access('organization_show', context, {'id': org_id})

    org = toolkit.get_action('organization_show')(
        {'ignore_auth': True},
        {'id': org_id}
    )

    # Use member_list instead of include_users which is restricted in CKAN 2.10
    member_tuples = toolkit.get_action('member_list')(
        {'ignore_auth': True},
        {'id': org_id, 'object_type': 'user'}
    )

    members = []
    for user_id, _obj_type, capacity in member_tuples:
        try:
            user_obj = model.User.get(user_id)
            if not user_obj or user_obj.state != 'active':
                continue

            extras = user_obj.plugin_extras or {}
            profile = extras.get('theme_ejemplo', {})

            expertise_areas = profile.get('expertise_areas', '[]')
            if isinstance(expertise_areas, str):
                try:
                    expertise_areas = json.loads(expertise_areas)
                except (json.JSONDecodeError, TypeError):
                    expertise_areas = []

            country_val = profile.get('country', '')
            member_states_raw = profile.get('member_states', '[]')
            if isinstance(member_states_raw, str):
                try:
                    ms_list = json.loads(member_states_raw)
                except (json.JSONDecodeError, TypeError):
                    ms_list = []
            elif isinstance(member_states_raw, list):
                ms_list = member_states_raw
            else:
                ms_list = []
            if not ms_list and country_val:
                ms_list = [country_val]

            members.append({
                'id': user_obj.id,
                'name': user_obj.name,
                'fullname': user_obj.fullname or user_obj.name,
                'image_url': normalize_user_image_url(user_obj.image_url),
                'job_title': profile.get('job_title', ''),
                'institution': profile.get('institution', ''),
                'country': country_val,
                'country_display': get_member_state_title(country_val) if country_val else '',
                'member_states': ms_list,
                'member_states_display': [
                    {'name': ms, 'title': get_member_state_title(ms)}
                    for ms in ms_list if ms
                ],
                'expertise_areas': expertise_areas,
                'capacity': capacity or 'member',
            })
        except Exception as e:
            log.warning(f"Error getting user profile for {user_id}: {e}")

    return {
        'organization': org,
        'members': members,
    }


# ── Membership Request Actions ──────────────────────────────────────────────

from ckanext.theme_ejemplo.model import MembershipRequest


def membership_request_create(context, data_dict):
    """Create a membership request for an organization.

    :param organization_id: the id or name of the organization
    :param message: optional message to org admins
    """
    toolkit.check_access('membership_request_create', context, data_dict)

    org_id_or_name = toolkit.get_or_bust(data_dict, 'organization_id')
    message = data_dict.get('message', u'')

    org = toolkit.get_action('organization_show')(
        {'ignore_auth': True}, {'id': org_id_or_name}
    )
    org_id = org['id']
    user_obj = context.get('auth_user_obj') or model.User.get(context['user'])
    if not user_obj:
        raise toolkit.NotAuthorized(_('Must be logged in'))

    # Check not already a member
    members = toolkit.get_action('member_list')(
        {'ignore_auth': True},
        {'id': org_id, 'object_type': 'user'}
    )
    if any(m[0] == user_obj.id for m in members):
        raise toolkit.ValidationError(
            {'organization': [_('You are already a member of this organization.')]}
        )

    # Check no pending request already exists
    existing = MembershipRequest.get_pending_for_user_and_org(user_obj.id, org_id)
    if existing:
        raise toolkit.ValidationError(
            {'organization': [_('You already have a pending request for this organization.')]}
        )

    req = MembershipRequest(
        user_id=user_obj.id,
        organization_id=org_id,
        message=message,
    )
    model.Session.add(req)
    model.Session.commit()

    return {
        'id': req.id,
        'user_id': req.user_id,
        'organization_id': req.organization_id,
        'message': req.message,
        'status': req.status,
        'created_at': req.created_at.isoformat() if req.created_at else None,
    }


@toolkit.side_effect_free
def membership_request_list(context, data_dict):
    """List membership requests for an organization.

    :param organization_id: the id or name of the organization
    :param status: optional filter (pending/approved/rejected)
    """
    toolkit.check_access('membership_request_list', context, data_dict)

    org_id_or_name = toolkit.get_or_bust(data_dict, 'organization_id')
    status_filter = data_dict.get('status', None)

    org = toolkit.get_action('organization_show')(
        {'ignore_auth': True}, {'id': org_id_or_name}
    )

    requests_list = MembershipRequest.get_for_org(org['id'], status=status_filter)

    results = []
    for req in requests_list:
        user_obj = model.User.get(req.user_id)
        handler_obj = model.User.get(req.handled_by) if req.handled_by else None

        results.append({
            'id': req.id,
            'user_id': req.user_id,
            'user_name': user_obj.name if user_obj else u'',
            'user_fullname': (user_obj.fullname or user_obj.name) if user_obj else u'',
            'user_image_url': normalize_user_image_url(user_obj.image_url) if user_obj else u'',
            'organization_id': req.organization_id,
            'message': req.message or u'',
            'status': req.status,
            'handled_by': req.handled_by,
            'handler_name': (handler_obj.fullname or handler_obj.name) if handler_obj else u'',
            'handled_at': req.handled_at.isoformat() if req.handled_at else None,
            'admin_note': req.admin_note or u'',
            'role': req.role or u'member',
            'created_at': req.created_at.isoformat() if req.created_at else None,
        })

    return {
        'organization': org,
        'results': results,
        'count': len(results),
    }


def membership_request_process(context, data_dict):
    """Approve or reject a membership request.

    :param id: the membership request id
    :param action: 'approve' or 'reject'
    :param admin_note: optional note
    """
    import datetime
    toolkit.check_access('membership_request_process', context, data_dict)

    request_id = toolkit.get_or_bust(data_dict, 'id')
    action = toolkit.get_or_bust(data_dict, 'action')
    admin_note = data_dict.get('admin_note', u'')
    role = data_dict.get('role', 'member')
    if role not in ('member', 'editor', 'admin'):
        role = 'member'

    if action not in ('approve', 'reject'):
        raise toolkit.ValidationError({'action': [_('Must be "approve" or "reject"')]})

    req = MembershipRequest.get(request_id)
    if not req:
        raise toolkit.ObjectNotFound(_('Membership request not found'))

    if req.status != MembershipRequest.STATUS_PENDING:
        raise toolkit.ValidationError(
            {'status': [_('This request has already been processed.')]}
        )

    user_obj = context.get('auth_user_obj') or model.User.get(context['user'])

    req.status = MembershipRequest.STATUS_APPROVED if action == 'approve' else MembershipRequest.STATUS_REJECTED
    req.handled_by = user_obj.id if user_obj else None
    req.handled_at = datetime.datetime.utcnow()
    req.admin_note = admin_note

    if action == 'approve':
        req.role = role
        # Add user as member of the organization
        toolkit.get_action('member_create')(
            {'ignore_auth': True},
            {
                'id': req.organization_id,
                'object': req.user_id,
                'object_type': 'user',
                'capacity': role,
            }
        )

    model.Session.commit()
    _invalidate_approvals_cache(user_obj.id if user_obj else None)

    return {
        'id': req.id,
        'status': req.status,
        'handled_by': req.handled_by,
        'handled_at': req.handled_at.isoformat() if req.handled_at else None,
    }


@toolkit.side_effect_free
def membership_request_count(context, data_dict):
    """Count pending membership requests across organizations where user is admin.

    Called without params — uses current user context.
    """
    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if not user_obj:
        return {'count': 0}

    # Find orgs where user is admin
    org_ids = _get_admin_org_ids(user_obj.id)
    if not org_ids:
        return {'count': 0}

    count = MembershipRequest.count_pending_for_orgs(org_ids)
    return {'count': count}


def _get_admin_org_ids(user_id):
    """Return list of org IDs where user is admin."""
    orgs = model.Session.query(model.Member).filter(
        model.Member.table_name == 'user',
        model.Member.table_id == user_id,
        model.Member.capacity == 'admin',
        model.Member.state == 'active',
    ).all()
    return [m.group_id for m in orgs]


# ── Featured Dataset Actions ────────────────────────────────────────────────

FEATURED_TAG = 'FeaturedDataset'


@toolkit.side_effect_free
def featured_dataset_list(context, data_dict):
    """List all datasets tagged as featured. Sysadmin only."""
    toolkit.check_access('featured_dataset_list', context, data_dict)

    search_result = toolkit.get_action('package_search')(
        {'ignore_auth': True},
        {'fq': 'tags:{}'.format(FEATURED_TAG), 'rows': 100}
    )
    results = []
    for pkg in search_result.get('results', []):
        org = pkg.get('organization') or {}
        results.append({
            'id': pkg['id'],
            'name': pkg['name'],
            'title': pkg.get('title', pkg['name']),
            'notes': pkg.get('notes', ''),
            'organization_title': org.get('title', ''),
            'metadata_modified': pkg.get('metadata_modified', ''),
        })
    return {'results': results, 'count': search_result.get('count', 0)}


def featured_dataset_add(context, data_dict):
    """Add the FeaturedDataset tag to a dataset. Sysadmin only."""
    toolkit.check_access('featured_dataset_add', context, data_dict)
    dataset_id = toolkit.get_or_bust(data_dict, 'id')

    pkg = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': dataset_id}
    )

    tags = pkg.get('tags', [])
    if any(t['name'] == FEATURED_TAG for t in tags):
        return {'success': True, 'message': 'Already featured'}

    tags.append({'name': FEATURED_TAG})
    toolkit.get_action('package_patch')(
        {'ignore_auth': True},
        {'id': pkg['id'], 'tags': tags}
    )
    return {'success': True}


def featured_dataset_remove(context, data_dict):
    """Remove the FeaturedDataset tag from a dataset. Sysadmin only."""
    toolkit.check_access('featured_dataset_remove', context, data_dict)
    dataset_id = toolkit.get_or_bust(data_dict, 'id')

    pkg = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': dataset_id}
    )

    tags = [t for t in pkg.get('tags', []) if t['name'] != FEATURED_TAG]
    toolkit.get_action('package_patch')(
        {'ignore_auth': True},
        {'id': pkg['id'], 'tags': tags}
    )
    return {'success': True}


# ── Featured Publication Actions ─────────────────────────────────────────────

from ckanext.theme_ejemplo.model import FeaturedPublication, init_featured_publications_db


@toolkit.side_effect_free
def featured_publication_list(context, data_dict):
    """List all featured publications."""
    toolkit.check_access('featured_publication_list', context, data_dict)
    init_featured_publications_db()
    pubs = FeaturedPublication.get_all()
    return {'results': [p.as_dict() for p in pubs], 'count': len(pubs)}


def featured_publication_create(context, data_dict):
    """Create a new featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_create', context, data_dict)
    init_featured_publications_db()

    title = toolkit.get_or_bust(data_dict, 'title')
    link = toolkit.get_or_bust(data_dict, 'link')
    description = data_dict.get('description', u'')
    image_url = data_dict.get('image_url', u'')
    display_order = int(data_dict.get('display_order', 0))

    pub = FeaturedPublication(
        title=title,
        link=link,
        description=description,
        image_url=image_url,
        display_order=display_order,
    )
    model.Session.add(pub)
    model.Session.commit()
    return pub.as_dict()


def featured_publication_update(context, data_dict):
    """Update a featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_update', context, data_dict)
    init_featured_publications_db()

    pub_id = toolkit.get_or_bust(data_dict, 'id')
    pub = FeaturedPublication.get(pub_id)
    if not pub:
        raise toolkit.ObjectNotFound('Featured publication not found')

    for field in ('title', 'link', 'description', 'image_url'):
        if field in data_dict:
            setattr(pub, field, data_dict[field])
    if 'display_order' in data_dict:
        pub.display_order = int(data_dict['display_order'])

    model.Session.commit()
    return pub.as_dict()


def featured_publication_delete(context, data_dict):
    """Delete a featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_delete', context, data_dict)
    init_featured_publications_db()

    pub_id = toolkit.get_or_bust(data_dict, 'id')
    pub = FeaturedPublication.get(pub_id)
    if not pub:
        raise toolkit.ObjectNotFound('Featured publication not found')

    model.Session.delete(pub)
    model.Session.commit()
    return {'success': True}


def featured_publication_reorder(context, data_dict):
    """Reorder featured publications. Sysadmin only.
    Expects 'order': list of publication IDs in desired order.
    """
    toolkit.check_access('featured_publication_reorder', context, data_dict)
    init_featured_publications_db()

    order = data_dict.get('order', [])
    if not order:
        return {'success': True}

    for idx, pub_id in enumerate(order):
        pub = FeaturedPublication.get(pub_id)
        if pub:
            pub.display_order = idx

    model.Session.commit()
    return {'success': True}


def featured_publication_import_legacy(context, data_dict):
    """Import legacy UNESDOC publications (tag-based datasets) into the
    featured_publication table.  Sysadmin only.

    Legacy datasets are found by searching for packages tagged 'UNESDOC'
    that are either followed or created by a specific user.  Each dataset
    is mapped to a FeaturedPublication row so it can be managed from the
    admin panel.

    Returns: dict with 'imported' count and 'skipped' count.
    """
    toolkit.check_access('featured_publication_import_legacy', context, data_dict)
    init_featured_publications_db()

    # The hardcoded user / org from the original template fallback
    legacy_user = data_dict.get('user_id', '8ad64841-340c-49dc-8716-c6b61ea4b111')
    tag = data_dict.get('tag', 'UNESDOC')

    # Fetch legacy datasets via package_search
    try:
        query = (
            '( followers:yes AND tags:{tag} ) OR '
            '( tags:{tag} AND creator_user_id:{user} )'
        ).format(tag=tag, user=legacy_user)

        search_result = toolkit.get_action('package_search')(
            {'ignore_auth': True},
            {'q': query, 'rows': 50}
        )
        datasets = search_result.get('results', [])
    except Exception as e:
        log.error(u'Error fetching legacy publications: %s', e)
        datasets = []

    if not datasets:
        return {'imported': 0, 'skipped': 0, 'results': []}

    # Collect existing links to avoid duplicates
    existing_links = set()
    for pub in FeaturedPublication.get_all():
        if pub.link:
            existing_links.add(pub.link.strip().rstrip('/'))

    existing_count = len(FeaturedPublication.get_all())
    imported = 0
    skipped = 0
    results = []

    for ds in datasets:
        # Extract fields using same priority as the legacy template
        extras = {e['key']: e['value'] for e in ds.get('extras', [])} if ds.get('extras') else {}

        image_url = (
            ds.get('image')
            or extras.get('unesdocimage')
            or '/Landing_page/Content/data_catalogue_button1.png'
        )
        link = (
            extras.get('unesdocurl')
            or ds.get('url')
            or 'https://unesdoc.unesco.org/'
        )
        title = ds.get('title', '')
        description = ds.get('notes', '')

        # Skip if link already exists
        normalised = link.strip().rstrip('/')
        if normalised in existing_links:
            skipped += 1
            continue

        pub = FeaturedPublication(
            title=title,
            link=link,
            description=description,
            image_url=image_url,
            display_order=existing_count + imported,
        )
        model.Session.add(pub)
        existing_links.add(normalised)
        imported += 1
        results.append(pub.as_dict())

    if imported:
        model.Session.commit()

    return {'imported': imported, 'skipped': skipped, 'results': results}


# ── Portal Card Actions ──────────────────────────────────────────────────────

from ckanext.theme_ejemplo.model import (
    PortalCard, init_portal_cards_db, VALID_PORTAL_IDS
)


@toolkit.side_effect_free
def portal_card_list(context, data_dict):
    """List all cards for a given portal. Sysadmin only."""
    toolkit.check_access('portal_card_list', context, data_dict)
    init_portal_cards_db()
    portal_id = data_dict.get('portal_id', '')
    if portal_id and portal_id not in VALID_PORTAL_IDS:
        raise toolkit.ValidationError({'portal_id': 'Invalid portal_id'})
    cards = PortalCard.get_by_portal(portal_id) if portal_id else []
    return {'results': [c.as_dict() for c in cards], 'count': len(cards)}


def portal_card_create(context, data_dict):
    """Create a new portal card. Sysadmin only."""
    toolkit.check_access('portal_card_create', context, data_dict)
    init_portal_cards_db()

    portal_id = toolkit.get_or_bust(data_dict, 'portal_id')
    if portal_id not in VALID_PORTAL_IDS:
        raise toolkit.ValidationError({'portal_id': 'Invalid portal_id'})

    title = toolkit.get_or_bust(data_dict, 'title')
    link = toolkit.get_or_bust(data_dict, 'link')
    description = data_dict.get('description', u'')
    image_url = data_dict.get('image_url', u'')
    display_order = int(data_dict.get('display_order', 0))
    is_coming_soon = data_dict.get('is_coming_soon', False)
    if isinstance(is_coming_soon, str):
        is_coming_soon = is_coming_soon.lower() in ('true', '1', 'yes', 'on')

    card = PortalCard(
        portal_id=portal_id,
        title=title,
        link=link,
        description=description,
        image_url=image_url,
        display_order=display_order,
        is_coming_soon=is_coming_soon,
    )
    model.Session.add(card)
    model.Session.commit()
    return card.as_dict()


def portal_card_update(context, data_dict):
    """Update a portal card. Sysadmin only."""
    toolkit.check_access('portal_card_update', context, data_dict)
    init_portal_cards_db()

    card_id = toolkit.get_or_bust(data_dict, 'id')
    card = PortalCard.get(card_id)
    if not card:
        raise toolkit.ObjectNotFound('Portal card not found')

    for field in ('title', 'link', 'description', 'image_url'):
        if field in data_dict:
            setattr(card, field, data_dict[field])
    if 'display_order' in data_dict:
        card.display_order = int(data_dict['display_order'])
    if 'is_coming_soon' in data_dict:
        val = data_dict['is_coming_soon']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes', 'on')
        card.is_coming_soon = val
    if 'is_archived' in data_dict:
        val = data_dict['is_archived']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes', 'on')
        card.is_archived = val

    model.Session.commit()
    return card.as_dict()


def portal_card_delete(context, data_dict):
    """Delete a portal card. Sysadmin only."""
    toolkit.check_access('portal_card_delete', context, data_dict)
    init_portal_cards_db()

    card_id = toolkit.get_or_bust(data_dict, 'id')
    card = PortalCard.get(card_id)
    if not card:
        raise toolkit.ObjectNotFound('Portal card not found')

    model.Session.delete(card)
    model.Session.commit()
    return {'success': True}


def portal_card_reorder(context, data_dict):
    """Reorder portal cards. Expects 'order': list of card IDs."""
    toolkit.check_access('portal_card_reorder', context, data_dict)
    init_portal_cards_db()

    order = data_dict.get('order', [])
    if not order:
        return {'success': True}

    for idx, card_id in enumerate(order):
        card = PortalCard.get(card_id)
        if card:
            card.display_order = idx

    model.Session.commit()
    return {'success': True}

from ckanext.theme_ejemplo.model import BugTicket, init_bug_tickets_db


def bug_ticket_create(context, data_dict):
    """Create a new bug ticket. Any authenticated user."""
    toolkit.check_access('bug_ticket_create', context, data_dict)
    init_bug_tickets_db()

    user_obj = context.get('auth_user_obj') or model.User.get(context['user'])
    if not user_obj:
        raise toolkit.NotAuthorized('Must be logged in')

    title = toolkit.get_or_bust(data_dict, 'title')
    description = toolkit.get_or_bust(data_dict, 'description')
    url = data_dict.get('url', u'')
    image_filename = data_dict.get('image_filename', u'')
    browser_info = data_dict.get('browser_info', u'')
    log_snapshot = data_dict.get('log_snapshot', u'')

    ticket = BugTicket(
        user_id=user_obj.id,
        title=title,
        description=description,
        url=url,
        image_filename=image_filename,
        browser_info=browser_info,
        log_snapshot=log_snapshot,
    )
    model.Session.add(ticket)
    model.Session.commit()

    result = ticket.as_dict()
    result['user_name'] = user_obj.fullname or user_obj.name
    return result


@toolkit.side_effect_free
def bug_ticket_list(context, data_dict):
    """List bug tickets. Users see their own; sysadmins see all."""
    toolkit.check_access('bug_ticket_list', context, data_dict)
    init_bug_tickets_db()

    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))
    status = data_dict.get('status', None)
    limit = int(data_dict.get('limit', 50))
    offset = int(data_dict.get('offset', 0))

    # Sysadmins see all; regular users see only their own
    user_filter = None
    if not (user_obj and user_obj.sysadmin):
        user_filter = user_obj.id if user_obj else '__none__'

    tickets, total = BugTicket.get_all(
        status=status, user_id=user_filter,
        limit=limit, offset=offset
    )

    results = []
    for t in tickets:
        d = t.as_dict()
        u = model.User.get(t.user_id)
        d['user_name'] = (u.fullname or u.name) if u else t.user_id
        results.append(d)

    return {'results': results, 'count': total}


@toolkit.side_effect_free
def bug_ticket_show(context, data_dict):
    """Show a single bug ticket."""
    toolkit.check_access('bug_ticket_show', context, data_dict)
    init_bug_tickets_db()

    ticket_id = toolkit.get_or_bust(data_dict, 'id')
    ticket = BugTicket.get(ticket_id)
    if not ticket:
        raise toolkit.ObjectNotFound('Bug ticket not found')

    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if not (user_obj and (user_obj.sysadmin or user_obj.id == ticket.user_id)):
        raise toolkit.NotAuthorized('Not authorized to view this ticket')

    result = ticket.as_dict()
    u = model.User.get(ticket.user_id)
    result['user_name'] = (u.fullname or u.name) if u else ticket.user_id
    if ticket.resolved_by:
        resolver = model.User.get(ticket.resolved_by)
        result['resolved_by_name'] = (resolver.fullname or resolver.name) if resolver else ticket.resolved_by
    return result


def bug_ticket_update(context, data_dict):
    """Update a bug ticket status/notes. Sysadmin can change status; user can close."""
    toolkit.check_access('bug_ticket_update', context, data_dict)
    init_bug_tickets_db()
    import datetime as dt

    ticket_id = toolkit.get_or_bust(data_dict, 'id')
    ticket = BugTicket.get(ticket_id)
    if not ticket:
        raise toolkit.ObjectNotFound('Bug ticket not found')

    user_obj = context.get('auth_user_obj') or model.User.get(context['user'])
    new_status = data_dict.get('status')

    if new_status:
        if new_status not in BugTicket.VALID_STATUSES:
            raise toolkit.ValidationError(
                {'status': ['Must be one of: {}'.format(', '.join(BugTicket.VALID_STATUSES))]}
            )
        # Regular users can only close their own tickets
        if not user_obj.sysadmin:
            if ticket.user_id != user_obj.id:
                raise toolkit.NotAuthorized('Cannot update others\' tickets')
            if new_status != BugTicket.STATUS_RESOLVED_USER:
                raise toolkit.NotAuthorized('Users can only close their own tickets')
            new_status = BugTicket.STATUS_RESOLVED_USER

        ticket.status = new_status
        if new_status in (BugTicket.STATUS_RESOLVED_USER, BugTicket.STATUS_RESOLVED_ADMIN):
            ticket.resolved_by = user_obj.id
            ticket.resolved_at = dt.datetime.utcnow()

    if 'admin_notes' in data_dict and user_obj.sysadmin:
        ticket.admin_notes = data_dict['admin_notes']

    ticket.updated_at = dt.datetime.utcnow()
    model.Session.commit()

    result = ticket.as_dict()
    u = model.User.get(ticket.user_id)
    result['user_name'] = (u.fullname or u.name) if u else ticket.user_id
    return result


@toolkit.side_effect_free
def bug_ticket_api_list(context, data_dict):
    """API endpoint for external AI systems to fetch open tickets.

    Returns open/in_progress tickets with full detail for automated analysis.
    Sysadmin-only access (use API key).
    """
    toolkit.check_access('bug_ticket_api_list', context, data_dict)
    init_bug_tickets_db()

    status = data_dict.get('status', BugTicket.STATUS_OPEN)
    limit = int(data_dict.get('limit', 100))
    offset = int(data_dict.get('offset', 0))

    tickets, total = BugTicket.get_all(
        status=status, limit=limit, offset=offset
    )

    results = []
    for t in tickets:
        d = t.as_dict()
        u = model.User.get(t.user_id)
        d['user_name'] = (u.fullname or u.name) if u else t.user_id
        if t.image_filename:
            d['image_url'] = '/uploads/bug_tickets/' + t.image_filename
        results.append(d)

    return {'results': results, 'count': total}


# ── Sysadmin User Management Actions ────────────────────────────────────────

def _get_sysadmin_context(context):
    """Verifica que el usuario actual es sysadmin y retorna el user_obj."""
    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user', ''))
    if not user_obj or not user_obj.sysadmin:
        raise toolkit.NotAuthorized('Only sysadmins can perform this action')
    return user_obj


@toolkit.side_effect_free
def admin_user_list(context, data_dict):
    """Lista paginada de usuarios con filtros para el panel de administración.

    Solo accesible por sysadmins. Incluye usuarios eliminados y campos
    extendidos del perfil.
    """
    toolkit.check_access('admin_user_list', context, data_dict)

    q = data_dict.get('q', '').strip()
    state_filter = data_dict.get('state', '')
    sysadmin_filter = data_dict.get('sysadmin', None)
    limit = min(int(data_dict.get('limit', 25)), 100)
    offset = max(int(data_dict.get('offset', 0)), 0)
    order_by = data_dict.get('order_by', 'created')

    query = model.Session.query(model.User).filter(
        model.User.name != 'default',
        model.User.name != 'harvest',
    )

    if state_filter:
        query = query.filter(model.User.state == state_filter)

    if sysadmin_filter is not None:
        if isinstance(sysadmin_filter, str):
            sysadmin_filter = sysadmin_filter.lower() in ('true', '1', 'yes')
        query = query.filter(model.User.sysadmin == sysadmin_filter)

    if q:
        query = theme_search.filter_by_tokens(
            query, q,
            [model.User.name, model.User.fullname, model.User.email])

    # Ordenamiento
    order_map = {
        'name': model.User.name.asc(),
        'name_desc': model.User.name.desc(),
        'created': model.User.created.desc(),
        'created_asc': model.User.created.asc(),
        'email': model.User.email.asc(),
    }
    query = query.order_by(order_map.get(order_by, model.User.created.desc()))

    total = query.count()
    users = query.offset(offset).limit(limit).all()

    results = []
    for user_obj in users:
        extras = user_obj.plugin_extras or {}
        profile = extras.get('theme_ejemplo', {})

        orgs = []
        try:
            for g in user_obj.get_groups('organization'):
                orgs.append({'name': g.name, 'title': g.title or g.name})
        except Exception:
            pass

        num_datasets = 0
        try:
            num_datasets = model.Session.query(model.Package).filter(
                model.Package.creator_user_id == user_obj.id,
                model.Package.state == 'active',
            ).count()
        except Exception:
            pass

        results.append({
            'id': user_obj.id,
            'name': user_obj.name,
            'fullname': user_obj.fullname or '',
            'email': user_obj.email or '',
            'image_url': normalize_user_image_url(user_obj.image_url),
            'state': user_obj.state,
            'sysadmin': user_obj.sysadmin,
            'created': user_obj.created.isoformat() if user_obj.created else '',
            'job_title': profile.get('job_title', ''),
            'institution': profile.get('institution', ''),
            'country': profile.get('country', ''),
            'organizations': orgs,
            'num_datasets': num_datasets,
        })

    return {
        'results': results,
        'count': total,
    }


def admin_user_reset_password(context, data_dict):
    """Permite a un sysadmin cambiar la contraseña de cualquier usuario.

    Requiere verificar la contraseña del sysadmin que ejecuta la acción
    como medida de seguridad adicional.
    """
    toolkit.check_access('admin_user_reset_password', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    new_password = toolkit.get_or_bust(data_dict, 'password')
    sysadmin_password = toolkit.get_or_bust(data_dict, 'sysadmin_password')

    if len(new_password) < 8:
        raise toolkit.ValidationError(
            {'password': ['Password must be at least 8 characters']}
        )

    # Verificar la contraseña del sysadmin que ejecuta la acción
    sysadmin_obj = _get_sysadmin_context(context)
    if not sysadmin_obj.validate_password(sysadmin_password):
        raise toolkit.ValidationError(
            {'sysadmin_password': ['Invalid sysadmin password']}
        )

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    target_user.password = new_password
    model.Session.commit()

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'Password updated for {target_user.name}',
    }


def admin_user_request_password_reset(context, data_dict):
    """Envía un correo de restablecimiento de contraseña al usuario.

    Utiliza el mecanismo nativo de CKAN (ckan.lib.mailer.send_reset_link)
    para generar un token y enviar el email con el enlace de reset.
    """
    from ckan.lib import mailer

    toolkit.check_access('admin_user_request_password_reset', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state != 'active':
        raise toolkit.ValidationError(
            {'id': ['Cannot send reset email to a non-active user']}
        )

    if not target_user.email:
        raise toolkit.ValidationError(
            {'id': ['User does not have an email address']}
        )

    try:
        mailer.send_reset_link(target_user)
    except mailer.MailerException as e:
        log.error(f'Error sending password reset email to {target_user.name}: {e}')
        raise toolkit.ValidationError(
            {'email': [str(e)]}
        )

    log.info(
        f'Sysadmin {context.get("user")} requested password reset for '
        f'{target_user.name} ({target_user.email})'
    )

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'Password reset email sent to {target_user.email}',
    }


def admin_user_delete(context, data_dict):
    """Soft-delete de un usuario (estado -> deleted). Eliminación inmediata."""
    toolkit.check_access('admin_user_delete', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state == 'deleted':
        raise toolkit.ValidationError(
            {'id': ['User is already deleted']}
        )

    # No permitir eliminar al propio sysadmin
    sysadmin_obj = _get_sysadmin_context(context)
    if target_user.id == sysadmin_obj.id:
        raise toolkit.ValidationError(
            {'id': ['Cannot delete your own account']}
        )

    # Usar la acción core de CKAN para soft-delete
    toolkit.get_action('user_delete')(
        {'user': sysadmin_obj.name, 'ignore_auth': True},
        {'id': target_user.id}
    )

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'User {target_user.name} has been deleted',
    }


def admin_user_purge(context, data_dict):
    """Eliminación permanente de un usuario de la base de datos.

    Solo se permite purgar usuarios que ya están en estado 'deleted'.
    Esta acción es IRREVERSIBLE.
    """
    toolkit.check_access('admin_user_purge', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    sysadmin_password = toolkit.get_or_bust(data_dict, 'sysadmin_password')

    sysadmin_obj = _get_sysadmin_context(context)
    if not sysadmin_obj.validate_password(sysadmin_password):
        raise toolkit.ValidationError(
            {'sysadmin_password': ['Invalid sysadmin password']}
        )

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state != 'deleted':
        raise toolkit.ValidationError(
            {'id': ['User must be in deleted state before purging. '
                    'Delete the user first.']}
        )

    user_name = target_user.name

    # Eliminar membresías de grupos/organizaciones residuales
    model.Session.query(model.Member).filter(
        model.Member.table_id == target_user.id,
        model.Member.table_name == 'user',
    ).delete(synchronize_session=False)

    # Eliminar el usuario permanentemente
    model.Session.delete(target_user)
    model.Session.commit()

    return {
        'success': True,
        'user_name': user_name,
        'message': f'User {user_name} has been permanently purged',
    }


def admin_user_reactivate(context, data_dict):
    """Reactivar un usuario eliminado (estado deleted -> active).

    Sin período de espera — reactivación inmediata.
    """
    toolkit.check_access('admin_user_reactivate', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state != 'deleted':
        raise toolkit.ValidationError(
            {'id': ['User is not in deleted state']}
        )

    target_user.state = model.State.ACTIVE
    model.Session.commit()

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'User {target_user.name} has been reactivated',
    }


def admin_user_toggle_sysadmin(context, data_dict):
    """Promover o degradar un usuario como sysadmin."""
    toolkit.check_access('admin_user_toggle_sysadmin', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    make_sysadmin = data_dict.get('sysadmin', False)
    if isinstance(make_sysadmin, str):
        make_sysadmin = make_sysadmin.lower() in ('true', '1', 'yes')

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    sysadmin_obj = _get_sysadmin_context(context)

    # Protección contra auto-degradación
    if target_user.id == sysadmin_obj.id and not make_sysadmin:
        raise toolkit.ValidationError(
            {'id': ['Cannot remove your own sysadmin privileges']}
        )

    # Verificar que no se quede sin sysadmins (con lock para evitar race conditions)
    if not make_sysadmin and target_user.sysadmin:
        from sqlalchemy import func
        sysadmin_count = model.Session.query(func.count(model.User.id)).filter(
            model.User.sysadmin == True,
            model.User.state == 'active',
        ).with_for_update().scalar()
        if sysadmin_count <= 1:
            raise toolkit.ValidationError(
                {'id': ['Cannot remove the last sysadmin']}
            )

    target_user.sysadmin = make_sysadmin
    model.Session.commit()

    action_label = 'promoted to' if make_sysadmin else 'removed from'
    return {
        'success': True,
        'user_name': target_user.name,
        'sysadmin': make_sysadmin,
        'message': f'User {target_user.name} {action_label} sysadmin',
    }


def admin_user_create(context, data_dict):
    """Crear un nuevo usuario desde el panel de administración.

    Útil cuando el registro público está deshabilitado.
    """
    toolkit.check_access('admin_user_create', context, data_dict)

    name = toolkit.get_or_bust(data_dict, 'name')
    email = toolkit.get_or_bust(data_dict, 'email')
    password = toolkit.get_or_bust(data_dict, 'password')

    if len(password) < 8:
        raise toolkit.ValidationError(
            {'password': ['Password must be at least 8 characters']}
        )

    sysadmin_obj = _get_sysadmin_context(context)

    user_data = {
        'name': name,
        'email': email,
        'password': password,
        'fullname': data_dict.get('fullname', ''),
    }

    new_user = toolkit.get_action('user_create')(
        {'user': sysadmin_obj.name, 'ignore_auth': True},
        user_data
    )

    # Si se indicó que sea sysadmin, actualizarlo
    make_sysadmin = data_dict.get('sysadmin', False)
    if isinstance(make_sysadmin, str):
        make_sysadmin = make_sysadmin.lower() in ('true', '1', 'yes')

    if make_sysadmin:
        created_user = model.User.get(new_user['id'])
        if created_user:
            created_user.sysadmin = True
            model.Session.commit()

    return {
        'success': True,
        'user': new_user,
        'message': f'User {name} created successfully',
    }


# ── IHP-IX Content Actions ──────────────────────────────────────────────────

from ckanext.theme_ejemplo.model import (
    IhpixContent, init_ihpix_content_db, VALID_IHPIX_SECTION_KEYS,
    IhpixActivity, init_ihpix_activities_db, VALID_PRIORITY_AREAS,
)
from ckanext.theme_ejemplo.model import (
    IhpixActivityLink, init_ihpix_activity_links_db,
    IhpixWorkingGroup, IhpixWorkingGroupMember, IhpixContribution,
    init_ihpix_working_groups_db,
)
from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_workspaces as W
from ckanext.theme_ejemplo import ihpix_forms
from ckanext.theme_ejemplo import ihpix_links
import datetime as _dt


@toolkit.side_effect_free
def ihpix_content_list(context, data_dict):
    """List all IHP-IX page content sections. Sysadmin only."""
    toolkit.check_access('ihpix_content_list', context, data_dict)
    init_ihpix_content_db()

    section_type = data_dict.get('section_type', '')
    if section_type:
        items = IhpixContent.get_by_type(section_type)
    else:
        items = IhpixContent.get_all()
    return {'results': [i.as_dict() for i in items], 'count': len(items)}


def ihpix_content_update(context, data_dict):
    """Update an IHP-IX content section. Sysadmin only."""
    toolkit.check_access('ihpix_content_update', context, data_dict)
    init_ihpix_content_db()

    item_id = data_dict.get('id', '')
    section_key = data_dict.get('section_key', '')

    item = None
    if item_id:
        item = IhpixContent.get(item_id)
    elif section_key:
        item = IhpixContent.get_by_key(section_key)

    if not item:
        raise toolkit.ObjectNotFound('IHP-IX content section not found')

    for field in ('title', 'description', 'image_url', 'link',
                  'badge_text', 'extra_fields'):
        if field in data_dict:
            setattr(item, field, data_dict[field])
    if 'display_order' in data_dict:
        item.display_order = int(data_dict['display_order'])
    if 'is_active' in data_dict:
        val = data_dict['is_active']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes', 'on')
        item.is_active = val

    import datetime as _dt
    item.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    return item.as_dict()


# ── IHP-IX Activity Actions ─────────────────────────────────────────────────

@toolkit.side_effect_free
def ihpix_activity_list(context, data_dict):
    """List IHP-IX activities. Public for published, sysadmin for all."""
    toolkit.check_access('ihpix_activity_list', context, data_dict)
    init_ihpix_activities_db()

    def _arg(key):
        return (data_dict.get(key) or u'').strip() or None

    status = _arg('status')
    limit = min(_parse_int_field(data_dict, 'limit', 20), 100)
    offset = max(_parse_int_field(data_dict, 'offset', 0), 0)

    user_obj = context.get('auth_user_obj')
    is_sysadmin = bool(user_obj and user_obj.sysadmin)
    if status and status not in IhpixActivity.VALID_STATUSES:
        raise toolkit.ValidationError(
            {'status': 'Must be one of: {}'.format(
                ', '.join(IhpixActivity.VALID_STATUSES))})
    # Sólo el sysadmin puede listar estados distintos de published
    if not is_sysadmin:
        status = IhpixActivity.STATUS_PUBLISHED

    results, total = IhpixActivity.get_filtered(
        status=status,
        priority_area=_arg('priority_area'),
        output=_arg('output'),
        q_text=_arg('q'),
        biennium=_arg('biennium'),
        country=_arg('country'),
        region=_arg('region'),
        flagship=_arg('flagship'),
        organization=_arg('organization'),
        ctwg=_arg('ctwg'),
        limit=limit, offset=offset,
    )

    facets = IhpixActivity.get_facets()

    return {
        'results': [r.as_dict() for r in results],
        'count': total,
        'facets': facets,
    }


@toolkit.side_effect_free
def ihpix_activity_show(context, data_dict):
    """Show a single IHP-IX activity. Public."""
    toolkit.check_access('ihpix_activity_show', context, data_dict)
    init_ihpix_activities_db()

    activity_id = toolkit.get_or_bust(data_dict, 'id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    user_obj = context.get('auth_user_obj')
    is_sysadmin = user_obj and user_obj.sysadmin
    if activity.status != 'published' and not is_sysadmin:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    result = activity.as_dict()
    result['links'] = _ihpix_links_for(activity.id)
    return result


def _parse_date_field(data_dict, field_name):
    """Parsea un campo de fecha desde data_dict. Retorna date o None."""
    val = data_dict.get(field_name, None)
    if val and isinstance(val, str):
        import datetime as _dt
        try:
            return _dt.datetime.strptime(val, '%Y-%m-%d').date()
        except ValueError:
            raise toolkit.ValidationError(
                {field_name: 'Invalid date format. Use YYYY-MM-DD'}
            )
    return val


def _parse_int_field(data_dict, field_name, default=0):
    """Parsea un campo entero desde data_dict."""
    val = data_dict.get(field_name, default)
    if val is None or val == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


# Campos de texto extendidos de IhpixActivity
_IHPIX_TEXT_FIELDS = (
    'description', 'output', 'country', 'institution', 'link', 'image_url',
    'contact_name', 'contact_email', 'key_activity', 'outcomes', 'biennium',
    'institution_type', 'partners', 'unesco_participation',
    'flagships', 'regions', 'member_states',
    'knowledge_product_type', 'knowledge_product_type_other',
    'scientific_product_type', 'training_type',
    'knowledge_activity_type', 'knowledge_activity_type_other',
    'stakeholder_group_type', 'notes',
    'cross_cutting_wg', 'synergies', 'supporting_member_state',
    # PDF 2026
    'focal_point_name', 'institution_type_other',
    'stakeholder_group_type_other', 'stakeholder_group_name',
    'additional_notes',
)

# Gates Y/N del PDF 2026 (booleanos explícitos)
_IHPIX_BOOL_FIELDS = ihpix_forms.BOOL_FIELDS

# Campos numéricos de IhpixActivity
_IHPIX_INT_FIELDS = (
    'num_knowledge_products', 'num_scientific_products',
    'num_training_materials', 'num_curricula', 'num_transboundary_ms',
    'stakeholders_knowledge', 'stakeholders_knowledge_female',
    'stakeholders_knowledge_youth', 'stakeholders_awareness',
    'stakeholders_awareness_female', 'stakeholders_awareness_youth',
    'num_stakeholder_groups',
)

# Campos de fecha de IhpixActivity
_IHPIX_DATE_FIELDS = ('start_date', 'end_date', 'reported_date')


def ihpix_activity_create(context, data_dict):
    """Create a new IHP-IX activity. Sysadmin only."""
    toolkit.check_access('ihpix_activity_create', context, data_dict)
    init_ihpix_activities_db()

    title = toolkit.get_or_bust(data_dict, 'title')
    priority_area = toolkit.get_or_bust(data_dict, 'priority_area')
    if priority_area not in VALID_PRIORITY_AREAS:
        raise toolkit.ValidationError(
            {'priority_area': 'Must be one of: {}'.format(
                ', '.join(VALID_PRIORITY_AREAS))}
        )

    status = data_dict.get('status', 'published')
    if status not in IhpixActivity.VALID_STATUSES:
        raise toolkit.ValidationError(
            {'status': 'Must be one of: {}'.format(
                ', '.join(IhpixActivity.VALID_STATUSES))}
        )

    user_obj = context.get('auth_user_obj')
    reported_by = data_dict.get('reported_by', '')
    if not reported_by and user_obj:
        reported_by = user_obj.id

    # Construir kwargs para todos los campos del modelo
    kwargs = {
        'title': title,
        'priority_area': priority_area,
        'status': status,
        'reported_by': reported_by,
    }

    for field in _IHPIX_TEXT_FIELDS:
        kwargs[field] = data_dict.get(field, u'')

    for field in _IHPIX_INT_FIELDS:
        kwargs[field] = _parse_int_field(data_dict, field, 0)

    for field in _IHPIX_BOOL_FIELDS:
        kwargs[field] = C.normalize_bool(data_dict.get(field))

    for field in _IHPIX_DATE_FIELDS:
        kwargs[field] = _parse_date_field(data_dict, field)

    activity = IhpixActivity(**kwargs)
    model.Session.add(activity)
    model.Session.commit()
    return activity.as_dict()


def ihpix_activity_update(context, data_dict):
    """Update an IHP-IX activity. Sysadmin only."""
    toolkit.check_access('ihpix_activity_update', context, data_dict)
    init_ihpix_activities_db()

    activity_id = toolkit.get_or_bust(data_dict, 'id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    # Campos de texto simples
    for field in _IHPIX_TEXT_FIELDS + ('title', 'reported_by'):
        if field in data_dict:
            setattr(activity, field, data_dict[field])

    if 'priority_area' in data_dict:
        pa = data_dict['priority_area']
        if pa not in VALID_PRIORITY_AREAS:
            raise toolkit.ValidationError(
                {'priority_area': 'Must be one of: {}'.format(
                    ', '.join(VALID_PRIORITY_AREAS))}
            )
        activity.priority_area = pa

    if 'status' in data_dict:
        status = data_dict['status']
        if status not in IhpixActivity.VALID_STATUSES:
            raise toolkit.ValidationError(
                {'status': 'Must be one of: {}'.format(
                    ', '.join(IhpixActivity.VALID_STATUSES))}
            )
        activity.status = status

    # Campos de fecha
    for field in _IHPIX_DATE_FIELDS:
        if field in data_dict:
            setattr(activity, field, _parse_date_field(data_dict, field))

    # Campos numéricos
    for field in _IHPIX_INT_FIELDS:
        if field in data_dict:
            setattr(activity, field, _parse_int_field(data_dict, field, 0))

    # Gates Y/N
    for field in _IHPIX_BOOL_FIELDS:
        if field in data_dict:
            setattr(activity, field, C.normalize_bool(data_dict[field]))

    if 'links_json' in data_dict:
        _sync_activity_links(activity, data_dict.get('links_json'),
                             context.get('auth_user_obj'))

    activity.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    result = activity.as_dict()
    result['links'] = _ihpix_links_for(activity.id)
    return result


def ihpix_activity_delete(context, data_dict):
    """Delete an IHP-IX activity. Sysadmin only."""
    toolkit.check_access('ihpix_activity_delete', context, data_dict)
    init_ihpix_activities_db()

    activity_id = toolkit.get_or_bust(data_dict, 'id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    init_ihpix_activity_links_db()
    IhpixActivityLink.delete_for_activity(activity.id)
    model.Session.delete(activity)
    model.Session.commit()
    return {'success': True}


# ── IHP-IX Reporting & Dashboard ────────────────────────────────────────────

# ── Helpers del workflow de reporte ─────────────────────────────────────────

def _ihpix_user_obj(context):
    """Objeto usuario del contexto (auth_user_obj, o lookup por nombre)."""
    user_obj = context.get('auth_user_obj')
    if user_obj is None and context.get('user'):
        user_obj = model.User.get(context['user'])
    return user_obj


def _ihpix_get_report_or_404(data_dict):
    activity_id = toolkit.get_or_bust(data_dict, 'id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX report not found')
    return activity


def _ihpix_translate_errors(exc):
    """{campo: mensaje traducido} a partir de `.details` (clave + params) de
    `ReportValidationError` / `LinkValidationError`; si no hay detalle se
    devuelve el mensaje en inglés del módulo puro."""
    _ = toolkit._
    out = {}
    details = getattr(exc, 'details', None) or {}
    # La tabla de mensajes del módulo que lanzó la excepción tiene prioridad
    # (las claves se repiten entre módulos, p. ej. contact_email_required)
    own = getattr(exc, 'messages', None) or {}
    for field, msg in exc.errors.items():
        key_params = details.get(field)
        template = None
        if key_params:
            key, params = key_params
            template = own.get(key) or ihpix_forms.MESSAGES.get(key) or ihpix_links.MESSAGES.get(key)
            try:
                out[field] = _(template).format(**params) if template else msg
                continue
            except (KeyError, IndexError, ValueError):
                pass
        out[field] = msg
    return out


def _ihpix_validate(data_dict, is_draft):
    """Traduce `ReportValidationError` (módulo puro) a `toolkit.ValidationError`."""
    try:
        return ihpix_forms.validate_report_payload(data_dict, is_draft)
    except ihpix_forms.ReportValidationError as e:
        raise toolkit.ValidationError(_ihpix_translate_errors(e))


def _apply_report_values(activity, values):
    """Vuelca el dict validado (columna → valor) sobre la actividad."""
    for key, value in values.items():
        setattr(activity, key, value)
    activity.updated_at = _dt.datetime.utcnow()


def _ihpix_mark_submitted(activity):
    """Pasa el reporte a la cola de revisión."""
    now = _dt.datetime.utcnow()
    activity.status = IhpixActivity.STATUS_PENDING
    activity.submitted_at = now
    if not activity.reported_date:
        activity.reported_date = now.date()
    # La revisión anterior (si la hubo) deja de aplicar; review_notes se
    # conserva como "última observación" visible para el reportante.
    activity.reviewed_by = u''
    activity.reviewed_at = None


def _ihpix_links_for(activity_id):
    """Adjuntos de una actividad como lista de dicts (orden de display)."""
    init_ihpix_activity_links_db()
    return [link.as_dict() for link in IhpixActivityLink.get_by_activity(activity_id)]


def _sync_activity_links(activity, links_payload, user_obj):
    """Sincroniza los adjuntos de una actividad con `links_json` (full replace).

    Valida cada item con `ihpix_links.validate_link`, actualiza los que traen
    `id`, crea los nuevos y borra los que ya no vienen. No hace commit: el
    caller lo hace junto con la actividad para que sea atómico.
    """
    init_ihpix_activity_links_db()
    try:
        items = ihpix_links.parse_links_json(links_payload)
    except ihpix_links.LinkValidationError as e:
        raise toolkit.ValidationError(_ihpix_translate_errors(e))

    validated = []
    errors = {}
    for idx, item in enumerate(items):
        try:
            validated.append(ihpix_links.validate_link(item))
        except ihpix_links.LinkValidationError as e:
            for key, msg in _ihpix_translate_errors(e).items():
                errors['links[{}].{}'.format(idx, key)] = msg
    if errors:
        raise toolkit.ValidationError(errors)

    existing = {link.id: link for link in IhpixActivityLink.get_by_activity(activity.id)}
    keep = set()
    seen_keys = set()
    created = []
    for order, values in enumerate(validated):
        key = ihpix_links.dedupe_key(values)
        if key in seen_keys:
            continue  # el mismo objeto/URL dos veces: se conserva el primero
        seen_keys.add(key)
        link = existing.get(values['id']) if values['id'] else None
        if link is None:
            link = IhpixActivityLink(
                activity_id=activity.id,
                link_type=values['link_type'],
                title=values['title'],
                added_by=(user_obj.id if user_obj else u''),
            )
            model.Session.add(link)
            created.append(link)
        for field in ('link_type', 'target_kind', 'target_id', 'title',
                      'url', 'description', 'event_date'):
            setattr(link, field, values[field])
        link.display_order = order
        keep.add(link.id)
    for link_id, link in existing.items():
        if link_id not in keep:
            model.Session.delete(link)
    if created and user_obj:
        try:
            wg = _ihpix_wg_for_activity(activity)
            for link in created:
                _ihpix_record_contribution(
                    user_obj.id, 'link_added',
                    working_group_id=wg.id if wg else u'',
                    activity_id=activity.id, link_id=link.id)
        except Exception as e:
            log.warning('IHP-IX ledger (links): %s', e)
    return created


# ── Ledger de participación (working groups) ───────────────────────────────

def _ihpix_wg_config_bool(key, default):
    return toolkit.asbool(toolkit.config.get('ckanext.theme_ejemplo.' + key, default))


def _ihpix_record_contribution(user_id, kind, working_group_id=u'',
                               activity_id=u'', link_id=u'', meta=None,
                               dedupe=True):
    """Añade una fila al ledger `ihpix_contribution` (sin commit).

    Con `dedupe` no repite la misma (user, kind, activity/link), p. ej. un
    reporte reenviado varias veces cuenta una sola vez como 'submitted'.
    """
    if not user_id or kind not in W.CONTRIBUTION_KINDS:
        return None
    init_ihpix_working_groups_db()
    if dedupe and (activity_id or link_id) and IhpixContribution.exists(
            user_id, kind, activity_id, link_id):
        return None
    row = IhpixContribution(
        user_id=user_id, kind=kind, working_group_id=working_group_id or u'',
        activity_id=activity_id or u'', link_id=link_id or u'',
        meta_json=json.dumps(meta or {}))
    model.Session.add(row)
    return row


def _ihpix_wg_for_activity(activity):
    """Workspace (working group) del Output de la actividad, o None."""
    if not activity or not (activity.output or u'').strip():
        return None
    init_ihpix_working_groups_db()
    return IhpixWorkingGroup.get_by_output(activity.output.strip())


def _ihpix_ensure_contributor(wg, user_id, invited_by=u'system'):
    """Crea o activa la membresía `contributor` (sin commit).

    Respeta la decisión del lead: una membresía `removed` no se reactiva
    automáticamente. Devuelve (membership, activada_ahora).
    """
    membership = IhpixWorkingGroupMember.get_membership(wg.id, user_id)
    now = _dt.datetime.utcnow()
    if membership is None:
        membership = IhpixWorkingGroupMember(
            wg.id, user_id, role=W.ROLE_CONTRIBUTOR, status=W.MEMBER_ACTIVE,
            invited_by=invited_by)
        model.Session.add(membership)
        return membership, True
    if membership.status == W.MEMBER_PENDING:
        membership.status = W.MEMBER_ACTIVE
        membership.joined_at = now
        membership.updated_at = now
        return membership, True
    return membership, False


def _ihpix_ledger_on_submit(activity):
    """Reporte enviado a revisión → 'report_submitted' en su workspace."""
    try:
        wg = _ihpix_wg_for_activity(activity)
        _ihpix_record_contribution(
            activity.reported_by, 'report_submitted',
            working_group_id=wg.id if wg else u'', activity_id=activity.id)
    except Exception as e:
        log.warning('IHP-IX ledger (submit): %s', e)


def _ihpix_ledger_on_publish(activity):
    """Reporte publicado → 'report_published' y, si la config lo permite,
    el reportante pasa a ser contributor activo del workspace del Output."""
    try:
        wg = _ihpix_wg_for_activity(activity)
        _ihpix_record_contribution(
            activity.reported_by, 'report_published',
            working_group_id=wg.id if wg else u'', activity_id=activity.id)
        if wg and activity.reported_by and _ihpix_wg_config_bool(
                'ihpix_wg_auto_contributor', True):
            if model.User.get(activity.reported_by) is None:
                return  # filas del seed sin usuario real
            membership, activated = _ihpix_ensure_contributor(
                wg, activity.reported_by, invited_by=u'system')
            if activated:
                _ihpix_record_contribution(
                    activity.reported_by, 'member_joined',
                    working_group_id=wg.id, meta={'auto': True}, dedupe=False)
                _ihpix_notify_wg_member(membership, wg, 'auto_joined')
    except Exception as e:
        log.warning('IHP-IX ledger (publish): %s', e)


def _ihpix_wg_leads(wg):
    """Usuarios que gestionan el workspace (lead_user_id + miembros lead activos)."""
    ids = set()
    if wg.lead_user_id:
        ids.add(wg.lead_user_id)
    for m in IhpixWorkingGroupMember.get_for_group(wg.id, status=W.MEMBER_ACTIVE):
        if m.role == W.ROLE_LEAD:
            ids.add(m.user_id)
    users = []
    for user_id in ids:
        user = model.User.get(user_id)
        if user and user.email:
            users.append(user)
    return users


def _ihpix_wg_url(wg, suffix=u''):
    try:
        return toolkit.url_for('theme_ejemplo.ihpix_workspace_detail',
                               code=wg.output_code, qualified=True) + suffix
    except Exception:
        return toolkit.config.get('ckan.site_url', '') + '/ihpix/workspaces/' + wg.output_code + suffix


def _ihpix_notify_wg_leads(wg, requester):
    """Email a los leads cuando alguien pide unirse (best effort)."""
    try:
        import ckan.lib.mailer as mailer
        _ = toolkit._
        for lead in _ihpix_wg_leads(wg):
            subject = _('New request to join the IHP-IX working group "{title}"').format(
                title=wg.title)
            body = _(
                'Dear {name},\n\n'
                '{requester} has requested to join the working group "{title}".\n\n'
                'Review the request here: {url}\n'
            ).format(name=lead.display_name or lead.name,
                     requester=requester.display_name or requester.name,
                     title=wg.title, url=_ihpix_wg_url(wg, u'/members'))
            mailer.mail_user(lead, subject, body)
    except Exception as e:
        log.warning('IHP-IX: no se pudo avisar a los leads del workspace: %s', e)


def _ihpix_notify_wg_member(membership, wg, action):
    """Email al usuario afectado por una decisión sobre su membresía."""
    try:
        user = model.User.get(membership.user_id)
        if not user or not user.email:
            return
        import ckan.lib.mailer as mailer
        _ = toolkit._
        url = _ihpix_wg_url(wg)
        name = user.display_name or user.name
        if action == 'approve':
            subject = _('You have joined the IHP-IX working group "{title}"').format(title=wg.title)
            body = _('Dear {name},\n\nYour request to join the working group "{title}" was approved.\n\nOpen the workspace: {url}\n').format(name=name, title=wg.title, url=url)
        elif action == 'auto_joined':
            subject = _('You are now a contributor of the IHP-IX working group "{title}"').format(title=wg.title)
            body = _('Dear {name},\n\nYour published IHP-IX report added you as a contributor of the working group "{title}".\n\nOpen the workspace: {url}\n').format(name=name, title=wg.title, url=url)
        elif action == 'reject':
            subject = _('Your request to join the IHP-IX working group "{title}" was not accepted').format(title=wg.title)
            body = _('Dear {name},\n\nYour request to join the working group "{title}" was not accepted by its lead.\n\nWorkspace: {url}\n').format(name=name, title=wg.title, url=url)
        elif action == 'remove':
            subject = _('You were removed from the IHP-IX working group "{title}"').format(title=wg.title)
            body = _('Dear {name},\n\nYou are no longer a member of the working group "{title}".\n\nWorkspace: {url}\n').format(name=name, title=wg.title, url=url)
        else:
            return
        mailer.mail_user(user, subject, body)
    except Exception as e:
        log.warning('IHP-IX: no se pudo avisar al miembro del workspace: %s', e)


def _ihpix_invalidate_wg_approvals(wg):
    """Refresca la campana de los leads del workspace y de los sysadmins."""
    try:
        from ckanext.theme_ejemplo import approvals
        approvals.invalidate()
        for lead in _ihpix_wg_leads(wg):
            approvals.invalidate(lead.id)
    except Exception:
        pass


def _ihpix_notify_reporter(activity, action):
    """Email al reportante con el resultado de la revisión (best effort).

    Nunca bloquea la acción: cualquier fallo (sin SMTP, usuario sin email,
    fila del seed sin usuario) sólo deja un warning en el log.
    """
    try:
        if not activity.reported_by:
            return
        user = model.User.get(activity.reported_by)
        if not user or not user.email:
            return
        import ckan.lib.mailer as mailer
        _ = toolkit._
        site_title = toolkit.config.get('ckan.site_title', 'IHP-WINS')
        try:
            reports_url = toolkit.url_for(
                'theme_ejemplo.user_ihpix', id=user.name, qualified=True)
        except Exception:
            reports_url = toolkit.config.get('ckan.site_url', '') + '/ihpix/my-reports'
        if action == 'approve':
            subject = _('Your IHP-IX report "{title}" has been published').format(
                title=activity.title)
            body = _(
                'Dear {name},\n\n'
                'Your IHP-IX activity report "{title}" has been reviewed and '
                'published on {site}.\n\n'
                'You can see all your reports here: {url}\n\n'
                'Thank you for contributing to IHP-IX.\n'
            ).format(name=user.display_name or user.name, title=activity.title,
                     site=site_title, url=reports_url)
        else:
            subject = _('Your IHP-IX report "{title}" needs changes').format(
                title=activity.title)
            body = _(
                'Dear {name},\n\n'
                'Your IHP-IX activity report "{title}" was reviewed on {site} '
                'and could not be published as submitted.\n\n'
                'Reviewer notes:\n{notes}\n\n'
                'You can edit and resubmit it here: {url}\n'
            ).format(name=user.display_name or user.name, title=activity.title,
                     site=site_title, notes=activity.review_notes or '-',
                     url=reports_url)
        mailer.mail_user(user, subject, body)
    except Exception as e:
        log.warning('IHP-IX: no se pudo enviar el email de revisión: %s', e)


def ihpix_report_submit(context, data_dict):
    """Crea un reporte IHP-IX (PDF 2026) desde el formulario.

    - `save_as_draft=1` → status=draft (sólo exige título).
    - Si no → status=pending (validación completa) y entra en la cola de
      revisión.

    La validación vive en `ihpix_forms.validate_report_payload`; aquí sólo
    se persiste. `reported_by` guarda el **id** del usuario.
    """
    toolkit.check_access('ihpix_report_submit', context, data_dict)
    init_ihpix_activities_db()

    is_draft = C.normalize_bool(data_dict.get('save_as_draft'))
    values = _ihpix_validate(data_dict, is_draft)
    user_obj = _ihpix_user_obj(context)

    activity = IhpixActivity(title=values['title'],
                             priority_area=values['priority_area'])
    _apply_report_values(activity, values)
    activity.status = IhpixActivity.STATUS_DRAFT
    activity.reported_by = user_obj.id if user_obj else context.get('user', u'')
    if not is_draft:
        _ihpix_mark_submitted(activity)

    model.Session.add(activity)
    if 'links_json' in data_dict:
        _sync_activity_links(activity, data_dict.get('links_json'), user_obj)
    if not is_draft:
        _ihpix_ledger_on_submit(activity)
    model.Session.commit()
    if not is_draft:
        _invalidate_approvals_cache()
    result = activity.as_dict()
    result['links'] = _ihpix_links_for(activity.id)
    return result


def ihpix_report_update(context, data_dict):
    """Edita un reporte y, opcionalmente, lo (re)envía a revisión.

    Recibe el payload *completo* del formulario (igual que submit) más `id`.
    - Propietario: sólo si el reporte está en `draft` o `rejected`.
    - Sysadmin: cualquier estado; un reporte `published` se corrige sin
      volver a la cola.
    - `save_as_draft=1` → draft; si no → pending.
    """
    toolkit.check_access('ihpix_report_update', context, data_dict)
    init_ihpix_activities_db()

    activity = _ihpix_get_report_or_404(data_dict)
    user_obj = _ihpix_user_obj(context)
    is_sysadmin = bool(user_obj and user_obj.sysadmin)
    if (not is_sysadmin
            and activity.status not in ihpix_forms.OWNER_EDITABLE_STATUSES):
        raise toolkit.ValidationError(
            {'status': 'Only draft or rejected reports can be edited'})

    is_draft = C.normalize_bool(data_dict.get('save_as_draft'))
    values = _ihpix_validate(data_dict, is_draft)
    _apply_report_values(activity, values)

    if is_draft:
        activity.status = IhpixActivity.STATUS_DRAFT
    elif is_sysadmin and activity.status == IhpixActivity.STATUS_PUBLISHED:
        pass  # corrección editorial: sigue publicado
    else:
        _ihpix_mark_submitted(activity)

    if 'links_json' in data_dict:
        _sync_activity_links(activity, data_dict.get('links_json'), user_obj)
    if activity.status == IhpixActivity.STATUS_PENDING:
        _ihpix_ledger_on_submit(activity)
    model.Session.commit()
    if activity.status == IhpixActivity.STATUS_PENDING:
        _invalidate_approvals_cache()
    result = activity.as_dict()
    result['links'] = _ihpix_links_for(activity.id)
    return result


@toolkit.side_effect_free
def ihpix_report_show(context, data_dict):
    """Reporte completo para su propietario o un sysadmin.

    Devuelve `as_dict()` más `form` (valores listos para rellenar el
    formulario) y `reporter` (usuario resuelto).
    """
    toolkit.check_access('ihpix_report_show', context, data_dict)
    init_ihpix_activities_db()

    activity = _ihpix_get_report_or_404(data_dict)
    result = activity.as_dict()
    result['form'] = ihpix_forms.activity_to_form_dict(result)
    result['links'] = _ihpix_links_for(activity.id)
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter
    result['reporter'] = get_ihpix_reporter(activity.reported_by)
    result['can_edit'] = bool(
        (context.get('auth_user_obj') and context['auth_user_obj'].sysadmin)
        or activity.status in ihpix_forms.OWNER_EDITABLE_STATUSES)
    return result


def ihpix_report_delete(context, data_dict):
    """Borra un reporte: el propietario sólo sus borradores; sysadmin cualquiera."""
    toolkit.check_access('ihpix_report_delete', context, data_dict)
    init_ihpix_activities_db()

    activity = _ihpix_get_report_or_404(data_dict)
    user_obj = _ihpix_user_obj(context)
    if (not (user_obj and user_obj.sysadmin)
            and activity.status != IhpixActivity.STATUS_DRAFT):
        raise toolkit.ValidationError(
            {'status': 'Only draft reports can be deleted'})

    activity_id = activity.id
    init_ihpix_activity_links_db()
    IhpixActivityLink.delete_for_activity(activity_id)
    model.Session.delete(activity)
    model.Session.commit()
    return {'success': True, 'id': activity_id}


@toolkit.side_effect_free
def ihpix_my_reports_list(context, data_dict):
    """Reportes del usuario autenticado, con contadores por estado."""
    toolkit.check_access('ihpix_my_reports_list', context, data_dict)
    init_ihpix_activities_db()

    user_obj = _ihpix_user_obj(context)
    status = (data_dict.get('status') or u'').strip() or None
    if status and status not in IhpixActivity.VALID_STATUSES:
        raise toolkit.ValidationError(
            {'status': 'Must be one of: {}'.format(
                ', '.join(IhpixActivity.VALID_STATUSES))})
    limit = min(_parse_int_field(data_dict, 'limit', 20), 100)
    offset = max(_parse_int_field(data_dict, 'offset', 0), 0)

    results, total = IhpixActivity.get_by_reporter(
        user_obj, status=status, limit=limit, offset=offset)
    return {
        'results': [a.as_dict() for a in results],
        'count': total,
        'counts_by_status': IhpixActivity.count_by_status_for_reporter(user_obj),
    }


# ── Adjuntos (publicaciones, webinars, eventos, datos) ─────────────────────

@toolkit.side_effect_free
def ihpix_activity_link_list(context, data_dict):
    """Adjuntos de una actividad (publicada, o propia / sysadmin)."""
    toolkit.check_access('ihpix_activity_link_list', context, data_dict)
    activity_id = toolkit.get_or_bust(data_dict, 'activity_id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')
    results = _ihpix_links_for(activity.id)
    return {'results': results, 'count': len(results)}


def ihpix_activity_link_create(context, data_dict):
    """Añade un adjunto a una actividad propia (o cualquiera, sysadmin)."""
    toolkit.check_access('ihpix_activity_link_create', context, data_dict)
    init_ihpix_activity_links_db()
    activity_id = toolkit.get_or_bust(data_dict, 'activity_id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')
    try:
        values = ihpix_links.validate_link(data_dict)
    except ihpix_links.LinkValidationError as e:
        raise toolkit.ValidationError(_ihpix_translate_errors(e))

    existing = [l.as_dict() for l in IhpixActivityLink.get_by_activity(activity.id)]
    key = ihpix_links.dedupe_key(values)
    for link in existing:
        if ihpix_links.dedupe_key(link) == key:
            raise toolkit.ValidationError(
                {'target_id': 'This item is already attached to the activity'})

    user_obj = _ihpix_user_obj(context)
    link = IhpixActivityLink(
        activity_id=activity.id,
        link_type=values['link_type'],
        title=values['title'],
        target_kind=values['target_kind'],
        target_id=values['target_id'],
        url=values['url'],
        description=values['description'],
        event_date=values['event_date'],
        added_by=(user_obj.id if user_obj else u''),
        display_order=len(existing),
    )
    model.Session.add(link)
    activity.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    return link.as_dict()


def ihpix_activity_link_delete(context, data_dict):
    """Quita un adjunto (propietario de la actividad o sysadmin)."""
    toolkit.check_access('ihpix_activity_link_delete', context, data_dict)
    init_ihpix_activity_links_db()
    link_id = toolkit.get_or_bust(data_dict, 'id')
    link = IhpixActivityLink.get(link_id)
    if not link:
        raise toolkit.ObjectNotFound('IHP-IX attachment not found')
    activity = IhpixActivity.get(link.activity_id)
    model.Session.delete(link)
    if activity:
        activity.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    return {'success': True, 'id': link_id}


def _search_water_events(q, limit):
    """Busca páginas `water-events` de ckanext-pages por título.

    Devuelve None si la extensión no está disponible (la UI ofrece entonces
    la entrada manual). Se omiten páginas privadas o no aprobadas.
    """
    try:
        from ckanext.pages.db import Page
    except ImportError:
        return None
    try:
        query = model.Session.query(Page).filter(Page.page_type == 'water-events')
        if q:
            query = query.filter(Page.title.ilike(u'%' + q + u'%'))
        # En el fork (RapidResponseAndRecovery) `private` y `submission_status`
        # son columnas reales; filtrar en SQL. Si no existen, se cae al
        # filtrado por `extras` de más abajo.
        has_status_col = hasattr(Page, 'submission_status')
        if hasattr(Page, 'private'):
            query = query.filter(Page.private == False)  # noqa: E712
        if has_status_col:
            from sqlalchemy import or_
            query = query.filter(or_(
                Page.submission_status == None,  # noqa: E711
                Page.submission_status.notin_(['pending', 'rejected'])))
        query = query.order_by(Page.created.desc()).limit(limit * 3)
        results = []
        for pg in query.all():
            if getattr(pg, 'private', False):
                continue
            extras = {}
            if pg.extras:
                try:
                    extras = json.loads(pg.extras)
                except (ValueError, TypeError):
                    extras = {}
            if not has_status_col and extras.get('submission_status') in ('pending', 'rejected'):
                continue
            publish_date = getattr(pg, 'publish_date', None)
            results.append({
                'target_kind': 'page',
                'target_id': pg.name,
                'title': pg.title,
                'event_date': publish_date.date().isoformat() if publish_date else '',
                'location': extras.get('location', ''),
                'url': '/water-events/' + pg.name,
            })
            if len(results) >= limit:
                break
        return results
    except Exception as e:
        model.Session.rollback()
        log.warning('IHP-IX: no se pudieron buscar eventos: %s', e)
        return None


@toolkit.side_effect_free
def ihpix_link_search(context, data_dict):
    """Busca objetos existentes de IHP-WINS para adjuntar a un reporte.

    kind: publication (datasets type:documents), dataset / output_data
    (type:dataset), event / webinar (páginas water-events).
    """
    toolkit.check_access('ihpix_link_search', context, data_dict)
    kind = (data_dict.get('kind') or u'').strip().lower()
    q = (data_dict.get('q') or u'').strip()
    limit = min(max(_parse_int_field(data_dict, 'limit', 10), 1), 25)

    if kind in ('publication', 'dataset', 'output_data'):
        fq = 'type:documents' if kind == 'publication' else 'type:dataset'
        res = toolkit.get_action('package_search')(context, {
            'q': q or '*:*',
            'fq': fq,
            'rows': limit,
            'include_private': True,
        })
        results = []
        for pkg in res.get('results', []):
            org = pkg.get('organization') or {}
            results.append({
                'target_kind': 'package',
                'target_id': pkg['id'],
                'name': pkg.get('name', ''),
                'title': pkg.get('title') or pkg.get('name', ''),
                'organization': org.get('title', '') if isinstance(org, dict) else '',
                'year': str(pkg.get('publication_year') or ''),
                'url': ('/documents/' if kind == 'publication' else '/dataset/')
                       + pkg.get('name', pkg['id']),
            })
        return {'results': results, 'count': len(results), 'kind': kind,
                'search_available': True}

    if kind in ('event', 'webinar'):
        results = _search_water_events(q, limit)
        if results is None:
            return {'results': [], 'count': 0, 'kind': kind,
                    'search_available': False}
        return {'results': results, 'count': len(results), 'kind': kind,
                'search_available': True}

    if kind == 'course':
        if _ihpix_learning_loaded():
            # Catálogo nativo (ckanext-learning): cursos aprobados = públicos
            results = _ihpix_learning_course_search(q, limit)
            return {'results': results, 'count': len(results), 'kind': kind,
                    'search_available': True,
                    'can_propose': _ihpix_config_bool('ihpix_course_proposals_enabled', True)}
        # Caché curada legacy de Open Learning
        from ckanext.theme_ejemplo.model import (
            OpenLearningCourse, init_open_learning_courses_db,
        )
        init_open_learning_courses_db()
        results = []
        try:
            for course in OpenLearningCourse.search_public(q, limit=limit):
                results.append({
                    'target_kind': 'course',
                    'target_id': course.course_id,
                    'name': course.course_id,
                    'title': course.name,
                    'organization': course.org or '',
                    'year': (course.start_display or ''),
                    'url': ihpix_links.course_url(course.course_id),
                })
        except Exception as e:
            model.Session.rollback()
            log.warning('IHP-IX: no se pudieron buscar cursos: %s', e)
        return {'results': results, 'count': len(results), 'kind': kind,
                'search_available': True,
                'can_propose': _ihpix_config_bool('ihpix_course_proposals_enabled', True)}

    raise toolkit.ValidationError(
        {'kind': 'Must be one of: publication, dataset, output_data, event, webinar, course'})


# ── Puentes al ecosistema: publicaciones inline y propuestas de cursos ─────

def _ihpix_config_bool(key, default):
    return toolkit.asbool(toolkit.config.get('ckanext.theme_ejemplo.' + key, default))


def _ihpix_learning_loaded():
    """¿Está cargado ckanext-learning (catálogo nativo de cursos)? En ese caso
    los cursos son packages `type:learning` y la tabla legacy
    `open_learning_course` ya no es la fuente de verdad."""
    try:
        import ckan.plugins as p
        return p.plugin_loaded('learning')
    except Exception:
        return False


def _ihpix_learning_page_url(name):
    try:
        return toolkit.url_for('learning.read', id=name)
    except Exception:
        return '/learning/' + name


def _ihpix_learning_course_search(q, limit):
    """Cursos aprobados (públicos) del catálogo nativo → items de adjunto."""
    try:
        res = toolkit.get_action('package_search')({'user': ''}, {
            'q': q or '*:*',
            'fq': 'type:learning vocab_learning_type:course',
            'rows': limit,
        })
    except Exception as e:
        log.warning('IHP-IX: búsqueda de cursos learning falló: %s', e)
        return []
    items = []
    for pkg in res.get('results', []):
        item = ihpix_links.course_link_from_learning_package(
            pkg, _ihpix_learning_page_url(pkg.get('name', '')))
        items.append({
            'target_kind': 'course', 'target_id': item['target_id'],
            'name': pkg.get('name', ''), 'title': item['title'],
            'organization': item['description'], 'year': pkg.get('learning_start') or '',
            'url': item['url'],
        })
    return items


def _ihpix_learning_find_course(course_id):
    """Package `learning` (incluidos privados/pendientes) con ese id externo."""
    try:
        res = toolkit.get_action('package_search')({'ignore_auth': True}, {
            'q': 'learning_external_id:"%s"' % course_id.replace('"', ''),
            'fq': 'type:learning', 'rows': 1, 'include_private': True,
        })
        for pkg in res.get('results', []):
            if (pkg.get('learning_external_id') or '') == course_id:
                return pkg
    except Exception as e:
        log.warning('IHP-IX: búsqueda del curso %s en learning falló: %s', course_id, e)
    return None


def _ihpix_learning_propose(course_id, user_obj, note, output_code):
    """Propuesta de curso con ckanext-learning: crea el package `learning`
    en estado pending (cola /ckan-admin/learning) vía su capa compat."""
    _ = toolkit._
    from ckanext.learning import compat
    existing = _ihpix_learning_find_course(course_id)
    if existing is not None:
        status = existing.get('learning_status') or 'pending'
        if status == 'hidden':
            raise toolkit.ValidationError({'course_url': _(
                'This course is not available in the IHP-WINS catalogue.')})
        link = ihpix_links.course_link_from_learning_package(
            existing, _ihpix_learning_page_url(existing.get('name', '')))
        return {'status': status, 'created': False,
                'course': {'course_id': course_id, 'name': existing.get('title'),
                           'status': status, 'package_id': existing.get('id')},
                'link': link if status == 'approved' else None}
    try:
        result = compat.add({'ignore_auth': True, 'user': None}, {'course_id': course_id})
    except toolkit.ObjectNotFound:
        raise toolkit.ValidationError({'course_url': _(
            'No course with that address was found on Open Learning.')})
    except toolkit.ValidationError:
        raise
    except Exception as e:
        log.warning('IHP-IX: propuesta de curso vía learning falló: %s', e)
        raise toolkit.ValidationError({'course_url': _(
            'Open Learning is not reachable right now. Please try again later.')})
    course = result.get('course') or {}
    status = course.get('status') or 'pending'
    try:
        wg = None
        if output_code:
            init_ihpix_working_groups_db()
            wg = IhpixWorkingGroup.get_by_output(output_code)
        _ihpix_record_contribution(
            user_obj.id, 'course_proposed', working_group_id=wg.id if wg else u'',
            meta={'course_id': course_id, 'name': course.get('name'), 'note': note,
                  'package_id': course.get('package_id'), 'catalogue': 'learning'},
            dedupe=False)
        model.Session.commit()
    except Exception as e:
        model.Session.rollback()
        log.warning('IHP-IX ledger (course/learning): %s', e)
    if result.get('action') == 'created':
        pseudo = type('C', (), {'name': course.get('name') or course_id, 'course_id': course_id})()
        _ihpix_notify_course_proposal(pseudo, user_obj, note)
        try:
            from ckanext.theme_ejemplo import approvals
            approvals.invalidate()
        except Exception:
            pass
    return {'status': status, 'created': result.get('action') == 'created', 'course': course, 'link': None}


def _ihpix_config_int(key, default):
    try:
        return int(toolkit.config.get('ckanext.theme_ejemplo.' + key, default))
    except (TypeError, ValueError):
        return default


def ihpix_publication_orgs(context):
    """Organizaciones donde el usuario del contexto puede crear datasets
    (editor/admin). Lista de dicts `organization_list_for_user`."""
    user_obj = _ihpix_user_obj(context)
    if not user_obj:
        return []
    try:
        return toolkit.get_action('organization_list_for_user')(
            {'ignore_auth': True, 'user': user_obj.name},
            {'id': user_obj.id, 'permission': 'create_dataset'}) or []
    except Exception as e:
        log.warning('IHP-IX: organization_list_for_user falló: %s', e)
        return []


def ihpix_documents_schema_fields(context):
    """(campos del dataset, campos del recurso) del esquema `documents`
    instalado, vía `scheming_dataset_schema_show`. Si scheming no está o el
    esquema no existe se devuelve el listado completo de dev210 para no
    bloquear la subida."""
    from ckanext.theme_ejemplo import ihpix_publications as P
    fallback = (
        ['title_translated', 'notes_translated', 'document_type', 'tag_string',
         'publication_year', 'authors_json', 'owner_org', 'access_level',
         'groups__0__id', 'groups__1__id', 'language', 'license_id',
         'identifier', 'name', 'contact_name', 'contact_email', 'document_doi'],
        ['url', 'name', 'description', 'format'])
    try:
        schema = toolkit.get_action('scheming_dataset_schema_show')(
            {'ignore_auth': True}, {'type': P.DATASET_TYPE})
    except Exception as e:
        log.warning('IHP-IX: no se pudo leer el esquema %s: %s', P.DATASET_TYPE, e)
        return fallback
    ds = [f.get('field_name') for f in schema.get('dataset_fields', []) if f.get('field_name')]
    rs = [f.get('field_name') for f in schema.get('resource_fields', []) if f.get('field_name')]
    return (ds or fallback[0], rs or fallback[1])


def ihpix_publication_create(context, data_dict):
    """Crea una publicación (dataset `documents` + recurso) desde IHP-IX y,
    si viene `activity_id`, la adjunta al reporte.

    data_dict: campos del modal (ver `ihpix_publications.validate_publication_input`)
    + `upload` (FileStorage) opcional. Devuelve
    {'package': {...}, 'link': {...}, 'attached': bool, 'warnings': [...]}.
    """
    from ckanext.theme_ejemplo import ihpix_publications as P
    toolkit.check_access('ihpix_publication_create', context, data_dict)
    user_obj = _ihpix_user_obj(context)
    _ = toolkit._

    orgs = ihpix_publication_orgs(context)
    allowed = set()
    for o in orgs:
        allowed.add(o.get('id'))
        allowed.add(o.get('name'))
    if not allowed:
        raise toolkit.NotAuthorized(
            _('You need to be an editor or admin of an organization to upload publications'))

    upload = data_dict.get('upload')
    upload_filename = getattr(upload, 'filename', '') if upload is not None else ''
    upload_size = None
    if upload is not None:
        try:
            stream = getattr(upload, 'stream', None) or upload
            pos = stream.tell()
            stream.seek(0, 2)
            upload_size = stream.tell()
            stream.seek(pos)
        except Exception:
            upload_size = None
    max_mb = _ihpix_config_int('ihpix_upload_max_mb', 50)
    # contact_email: el esquema `documents` lo exige; por defecto el del usuario
    if not (data_dict.get('contact_email') or u'').strip():
        data_dict = dict(data_dict)
        data_dict['contact_email'] = (user_obj.email or u'') if user_obj else u''
    try:
        clean = P.validate_publication_input(
            data_dict, allowed_org_ids=allowed, max_upload_mb=max_mb,
            upload_filename=upload_filename, upload_size=upload_size,
            require_contact_email=True)
    except P.PublicationValidationError as e:
        raise toolkit.ValidationError(_ihpix_translate_errors(e))

    # Resolver el `id` de la organización (el modal puede mandar el name)
    owner = next((o for o in orgs if o.get('id') == clean['organization']
                  or o.get('name') == clean['organization']), None)
    clean['organization'] = owner['id'] if owner else clean['organization']

    activity = None
    if clean.get('activity_id'):
        init_ihpix_activities_db()
        activity = IhpixActivity.get(clean['activity_id'])
        if activity is None:
            raise toolkit.ObjectNotFound('IHP-IX activity not found')
        toolkit.check_access('ihpix_activity_link_create', context,
                             {'activity_id': activity.id})
        if not clean.get('output_code'):
            clean['output_code'] = (activity.output or u'').strip()

    ds_fields, res_fields = ihpix_documents_schema_fields(context)
    defaults = {
        'language': toolkit.config.get(
            'ckanext.theme_ejemplo.ihpix_publication_default_language', P.DEFAULT_LANGUAGE),
        'license_id': toolkit.config.get(
            'ckanext.theme_ejemplo.ihpix_publication_default_license', P.DEFAULT_LICENSE),
        'contact_email': (user_obj.email if user_obj and user_obj.email else '') or
                         toolkit.config.get('email_to', ''),
        'contact_name': (user_obj.display_name or user_obj.name) if user_obj else '',
        'tags': [t.strip() for t in toolkit.config.get(
            'ckanext.theme_ejemplo.ihpix_publication_tags', 'ihp-ix').split(',') if t.strip()],
    }

    create_ctx = {'user': user_obj.name, 'auth_user_obj': user_obj,
                  'model': model, 'session': model.Session}
    warnings = []
    pkg = None
    last_error = None
    taken = set()
    for attempt in range(4):
        name = P.slugify_title(clean['title'], taken=taken)
        pkg_dict = P.build_package_dict(clean, ds_fields, defaults=defaults, name=name)
        try:
            pkg = toolkit.get_action('package_create')(dict(create_ctx), pkg_dict)
            break
        except toolkit.ValidationError as e:
            errors = e.error_dict or {}
            if 'name' in errors and attempt < 3:
                taken.add(name)  # colisión de slug: reintentar con sufijo
                continue
            if 'groups' in errors and pkg_dict.get('groups'):
                clean['member_state'] = ''
                clean['initiative'] = ''
                warnings.append(_('The publication could not be linked to the Member State group; you can add it later from the dataset page.'))
                continue
            last_error = e
            break
        except toolkit.NotAuthorized as e:
            if pkg_dict.get('groups'):
                # `package_create` exige permisos sobre los grupos → sin grupos
                clean['member_state'] = ''
                clean['initiative'] = ''
                warnings.append(_('The publication could not be linked to the Member State group; you can add it later from the dataset page.'))
                continue
            raise
    if pkg is None:
        if last_error is not None:
            raise toolkit.ValidationError(P.map_schema_errors(last_error.error_dict))
        raise toolkit.ValidationError({'__all__': _('The publication could not be created')})

    res_dict = P.build_resource_dict(clean, res_fields, package_id=pkg['id'])
    if clean['source_kind'] == P.SOURCE_FILE:
        res_dict['upload'] = upload
    try:
        toolkit.get_action('resource_create')(dict(create_ctx), res_dict)
    except Exception as e:
        # Rollback best effort: no dejar un documento sin fichero
        try:
            toolkit.get_action('package_delete')(dict(create_ctx), {'id': pkg['id']})
        except Exception as e2:
            log.warning('IHP-IX: no se pudo borrar el package %s tras fallar el recurso: %s', pkg['id'], e2)
        log.warning('IHP-IX: resource_create falló para %s: %s', pkg['id'], e)
        if isinstance(e, toolkit.ValidationError):
            raise toolkit.ValidationError({'source': P.map_schema_errors(e.error_dict).get(
                'source') or _('The file could not be uploaded')})
        raise toolkit.ValidationError({'source': _('The file could not be uploaded')})

    try:
        pkg = toolkit.get_action('package_show')(dict(create_ctx), {'id': pkg['id']})
    except Exception:
        pass
    link_item = P.link_item_for_package(pkg)
    link_item['description'] = link_item.get('description') or ''

    attached = None
    if activity is not None:
        try:
            attached = toolkit.get_action('ihpix_activity_link_create')(
                dict(context), dict(link_item, activity_id=activity.id))
        except toolkit.ValidationError as e:
            warnings.append(_format_validation_error_text(e))

    # Ledger del workspace del Output (con o sin reporte adjunto)
    try:
        wg = None
        if clean.get('output_code'):
            init_ihpix_working_groups_db()
            wg = IhpixWorkingGroup.get_by_output(clean['output_code'])
        _ihpix_record_contribution(
            user_obj.id, 'publication_created',
            working_group_id=wg.id if wg else u'',
            activity_id=activity.id if activity else u'',
            meta={'package_id': pkg['id'], 'name': pkg.get('name'), 'title': pkg.get('title'),
                  'document_type': clean.get('document_type')},
            dedupe=False)
        model.Session.commit()
    except Exception as e:
        model.Session.rollback()
        log.warning('IHP-IX ledger (publication): %s', e)

    return {
        'package': {'id': pkg['id'], 'name': pkg.get('name'), 'title': pkg.get('title'),
                    'url': link_item['url']},
        'link': attached or link_item,
        'attached': attached is not None,
        'warnings': warnings,
    }


def _format_validation_error_text(exc):
    parts = []
    for key, msgs in (getattr(exc, 'error_dict', None) or {}).items():
        if isinstance(msgs, (list, tuple)):
            msgs = ', '.join(str(m) for m in msgs)
        parts.append(u'{}: {}'.format(key, msgs))
    return u'; '.join(parts) or str(exc)


def ihpix_course_propose(context, data_dict):
    """Propone un curso de UNESCO Open Learning para el catálogo de IHP-WINS.

    data_dict: `course_url` o `course_id`, `note` opcional, `output_code`
    opcional (ledger). Un curso nuevo queda `pending` hasta que un sysadmin
    lo apruebe; si ya está aprobado devuelve el adjunto listo para usar.
    """
    toolkit.check_access('ihpix_course_propose', context, data_dict)
    _ = toolkit._
    if not _ihpix_config_bool('ihpix_course_proposals_enabled', True):
        raise toolkit.NotAuthorized(_('Course proposals are disabled'))
    from ckanext.theme_ejemplo.model import (
        OpenLearningCourse, init_open_learning_courses_db,
    )
    from ckanext.theme_ejemplo import openlearning
    init_open_learning_courses_db()
    user_obj = _ihpix_user_obj(context)

    raw = (data_dict.get('course_url') or data_dict.get('course_id') or u'').strip()
    course_id = ihpix_links.parse_course_id(raw)
    if not course_id:
        raise toolkit.ValidationError({'course_url': _(
            'Paste the address of a course on openlearning.unesco.org (…/courses/course-v1:…/about)')})
    note = (data_dict.get('note') or u'').strip()[:500]

    # Rate limit por usuario y día
    per_day = _ihpix_config_int('ihpix_course_proposals_per_day', 10)
    since = _dt.datetime.utcnow() - _dt.timedelta(days=1)
    try:
        proposed_today = OpenLearningCourse.count_proposed_since(user_obj.id, since) if per_day else 0
    except Exception as e:  # columnas nuevas aún sin migrar: no bloquear
        model.Session.rollback()
        log.warning('IHP-IX: no se pudo comprobar el límite de propuestas: %s', e)
        proposed_today = 0
    if per_day and proposed_today >= per_day:
        raise toolkit.ValidationError({'course_url': _(
            'You have reached the daily limit of course proposals. Please try again tomorrow.')})

    if _ihpix_learning_loaded():
        return _ihpix_learning_propose(course_id, user_obj, note,
                                       (data_dict.get('output_code') or u'').strip())

    existing = OpenLearningCourse.get_by_course_id(course_id)
    if existing is not None and existing.status == OpenLearningCourse.STATUS_HIDDEN:
        raise toolkit.ValidationError({'course_url': _(
            'This course is not available in the IHP-WINS catalogue.')})
    if existing is not None and existing.status == OpenLearningCourse.STATUS_APPROVED:
        return {'status': 'approved', 'created': False, 'course': existing.as_dict(),
                'link': _ihpix_course_link_item(existing)}

    try:
        course, action = openlearning.fetch_and_upsert_course(course_id)
    except toolkit.ObjectNotFound:
        raise toolkit.ValidationError({'course_url': _(
            'No course with that address was found on Open Learning.')})
    except RuntimeError:
        raise toolkit.ValidationError({'course_url': _(
            'Open Learning is not reachable right now. Please try again later.')})

    now = _dt.datetime.utcnow()
    if action == 'created' or not (getattr(course, 'proposed_by', None) or u''):
        course.proposed_by = user_obj.id
        course.proposed_at = now
        course.proposal_note = note
        course.updated_at = now
    try:
        wg = None
        output_code = (data_dict.get('output_code') or u'').strip()
        if output_code:
            init_ihpix_working_groups_db()
            wg = IhpixWorkingGroup.get_by_output(output_code)
        _ihpix_record_contribution(
            user_obj.id, 'course_proposed', working_group_id=wg.id if wg else u'',
            meta={'course_id': course_id, 'name': course.name}, dedupe=False)
    except Exception as e:
        log.warning('IHP-IX ledger (course): %s', e)
    model.Session.commit()

    if action == 'created':
        _ihpix_notify_course_proposal(course, user_obj, note)
        try:
            from ckanext.theme_ejemplo import approvals
            approvals.invalidate()
        except Exception:
            pass
    return {'status': course.status, 'created': action == 'created',
            'course': course.as_dict(),
            'link': _ihpix_course_link_item(course) if course.status == 'approved' else None}


def _ihpix_course_link_item(course):
    return {
        'link_type': 'course', 'target_kind': 'course', 'target_id': course.course_id,
        'title': course.name, 'url': ihpix_links.course_url(course.course_id),
        'event_date': '', 'description': course.org or u'',
    }


def _ihpix_notify_course_proposal(course, proposer, note):
    """Email a los sysadmins con la propuesta (best effort)."""
    try:
        import ckan.lib.mailer as mailer
        _ = toolkit._
        site_url = toolkit.config.get('ckan.site_url', '').rstrip('/')
        admin_url = site_url + toolkit.url_for('theme_ejemplo.open_learning_admin')
        subject = _('New IHP Open Learning course proposed: {name}').format(name=course.name)
        body = _(
            'Dear {name},\n\n'
            '{proposer} proposed the course "{course}" for the IHP-WINS catalogue.\n\n'
            'Course: {url}\n'
            'Note: {note}\n\n'
            'Review it here: {admin_url}\n'
        )
        for admin in model.Session.query(model.User).filter(
                model.User.sysadmin == True, model.User.state == 'active').all():  # noqa: E712
            if not admin.email:
                continue
            mailer.mail_user(admin, subject, body.format(
                name=admin.display_name or admin.name,
                proposer=proposer.display_name or proposer.name,
                course=course.name, url=ihpix_links.course_url(course.course_id),
                note=note or '-', admin_url=admin_url))
    except Exception as e:
        log.warning('IHP-IX: no se pudo avisar de la propuesta de curso: %s', e)


# ── Working groups (workspaces por Output) ─────────────────────────────────

def _ihpix_wg_or_404(data_dict, key='id'):
    init_ihpix_working_groups_db()
    value = ((data_dict.get(key) or data_dict.get('output_code') or u'')).strip()
    wg = IhpixWorkingGroup.get_by_id_or_output(value) if value else None
    if not wg:
        raise toolkit.ObjectNotFound('IHP-IX working group not found')
    return wg


def _ihpix_wg_actor(context, wg):
    """(user_obj, membership, can_manage) del usuario del contexto."""
    user_obj = _ihpix_user_obj(context)
    membership = None
    if user_obj:
        membership = IhpixWorkingGroupMember.get_membership(wg.id, user_obj.id)
    can_manage = W.can_manage(
        wg, user_obj.id if user_obj else None,
        membership.as_dict() if membership else None,
        bool(user_obj and user_obj.sysadmin))
    return user_obj, membership, can_manage


def _ihpix_wg_dict(wg, counts=None, last_activity=None):
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter
    d = wg.as_dict()
    d['output_title'] = C.output_title(wg.output_code)
    d['priority_area_title'] = C.PRIORITY_AREAS.get(wg.priority_area, u'')
    c = (counts or {}).get(wg.id, {})
    d['members_active'] = c.get('active', 0)
    d['members_pending'] = c.get('pending', 0)
    d['last_activity_at'] = last_activity.isoformat() if last_activity else None
    d['lead'] = get_ihpix_reporter(wg.lead_user_id) if wg.lead_user_id else None
    return d


@toolkit.side_effect_free
def ihpix_working_group_list(context, data_dict):
    """Workspaces (uno por Output) con conteos y la membresía del usuario."""
    toolkit.check_access('ihpix_working_group_list', context, data_dict)
    init_ihpix_working_groups_db()
    init_ihpix_activities_db()
    status = (data_dict.get('status') or u'').strip() or None
    pa = (data_dict.get('priority_area') or u'').strip() or None
    groups = IhpixWorkingGroup.get_all(status=status, priority_area=pa)
    ids = [g.id for g in groups]
    counts = IhpixWorkingGroup.member_counts(ids)
    last = IhpixContribution.last_activity_for_groups(ids)
    facet_items = IhpixActivity.get_facets().get('ihpix_output', {}).get('items', [])
    published = {item['name']: item['count'] for item in facet_items}
    user_obj = _ihpix_user_obj(context)
    mine = {}
    if user_obj:
        mine = {m.working_group_id: m for m in IhpixWorkingGroupMember.get_for_user(user_obj.id)}
    results = []
    for g in groups:
        d = _ihpix_wg_dict(g, counts, last.get(g.id))
        d['published_activities'] = published.get(g.output_code, 0)
        m = mine.get(g.id)
        d['my_membership'] = m.as_dict() if m else None
        results.append(d)
    return {'results': results, 'count': len(results)}


@toolkit.side_effect_free
def ihpix_working_group_show(context, data_dict):
    """Un workspace (por id o código de Output) con stats y permisos del usuario."""
    toolkit.check_access('ihpix_working_group_show', context, data_dict)
    wg = _ihpix_wg_or_404(data_dict)
    init_ihpix_activities_db()
    user_obj, membership, can_manage = _ihpix_wg_actor(context, wg)
    counts = IhpixWorkingGroup.member_counts([wg.id])
    last = IhpixContribution.last_activity_for_groups([wg.id])
    d = _ihpix_wg_dict(wg, counts, last.get(wg.id))
    d['my_membership'] = membership.as_dict() if membership else None
    d['can_manage'] = can_manage
    d['stats'] = IhpixActivity.get_stats({'output': wg.output_code})
    d['contribution_counts'] = IhpixContribution.counts_for_group(wg.id)
    return d


def ihpix_working_group_update(context, data_dict):
    """Edita un workspace: título/descripción/settings (lead o sysadmin);
    lead_user_id y status solo sysadmin."""
    toolkit.check_access('ihpix_working_group_update', context, data_dict)
    wg = _ihpix_wg_or_404(data_dict)
    user_obj = _ihpix_user_obj(context)
    is_sysadmin = bool(user_obj and user_obj.sysadmin)
    now = _dt.datetime.utcnow()

    if 'title' in data_dict:
        title = (data_dict.get('title') or u'').strip()
        if not title:
            raise toolkit.ValidationError({'title': 'Title is required'})
        wg.title = title
    if 'description' in data_dict:
        wg.description = (data_dict.get('description') or u'').strip()
    if 'settings' in data_dict:
        raw = data_dict.get('settings')
        if isinstance(raw, dict):
            wg.settings = json.dumps(raw)
        else:
            try:
                parsed = json.loads(raw or u'{}')
                if not isinstance(parsed, dict):
                    raise ValueError
                wg.settings = json.dumps(parsed)
            except (ValueError, TypeError):
                raise toolkit.ValidationError({'settings': 'Must be a JSON object'})
    if 'lead_user_id' in data_dict:
        if not is_sysadmin:
            raise toolkit.NotAuthorized('Only sysadmins can assign the lead')
        value = (data_dict.get('lead_user_id') or u'').strip()
        if value:
            lead = model.User.get(value)
            if not lead:
                raise toolkit.ValidationError({'lead_user_id': 'User not found'})
            wg.lead_user_id = lead.id
            membership, _activated = _ihpix_ensure_contributor(wg, lead.id, invited_by=user_obj.id)
            membership.role = W.ROLE_LEAD
            membership.updated_at = now
        else:
            wg.lead_user_id = u''
    if 'status' in data_dict:
        if not is_sysadmin:
            raise toolkit.NotAuthorized('Only sysadmins can archive a working group')
        status = (data_dict.get('status') or u'').strip()
        if status not in W.WG_STATUSES:
            raise toolkit.ValidationError({'status': 'Must be one of: {}'.format(', '.join(W.WG_STATUSES))})
        wg.status = status
    wg.updated_at = now
    model.Session.commit()
    return ihpix_working_group_show(context, {'id': wg.id})


def ihpix_working_group_join(context, data_dict):
    """Solicita unirse (o se une, si `ihpix_wg_open_join`) a un workspace."""
    toolkit.check_access('ihpix_working_group_join', context, data_dict)
    wg = _ihpix_wg_or_404(data_dict)
    user_obj = _ihpix_user_obj(context)
    membership = IhpixWorkingGroupMember.get_membership(wg.id, user_obj.id)
    try:
        reactivate = W.validate_join(wg.as_dict(), membership.as_dict() if membership else None)
    except W.WorkspaceRuleError as e:
        raise toolkit.ValidationError(e.errors)
    status = W.resolve_join_status(_ihpix_wg_config_bool('ihpix_wg_open_join', False))
    note = (data_dict.get('note') or u'').strip()[:500]
    now = _dt.datetime.utcnow()
    if reactivate:
        membership.status = status
        membership.role = W.ROLE_CONTRIBUTOR
        membership.note = note
        membership.joined_at = now if status == W.MEMBER_ACTIVE else None
        membership.updated_at = now
    else:
        membership = IhpixWorkingGroupMember(
            wg.id, user_obj.id, role=W.ROLE_CONTRIBUTOR, status=status, note=note)
        model.Session.add(membership)
    if status == W.MEMBER_ACTIVE:
        _ihpix_record_contribution(user_obj.id, 'member_joined', working_group_id=wg.id, dedupe=False)
    model.Session.commit()
    _ihpix_invalidate_wg_approvals(wg)
    if status == W.MEMBER_PENDING:
        _ihpix_notify_wg_leads(wg, user_obj)
    result = membership.as_dict()
    result['workspace'] = _ihpix_wg_dict(wg)
    return result


def ihpix_working_group_leave(context, data_dict):
    """Abandona un workspace (los leads deben pedirlo a un sysadmin)."""
    toolkit.check_access('ihpix_working_group_leave', context, data_dict)
    wg = _ihpix_wg_or_404(data_dict)
    user_obj = _ihpix_user_obj(context)
    membership = IhpixWorkingGroupMember.get_membership(wg.id, user_obj.id)
    if not membership or membership.status == W.MEMBER_REMOVED:
        raise toolkit.ValidationError({'id': 'You are not a member of this working group'})
    if membership.role == W.ROLE_LEAD and membership.status == W.MEMBER_ACTIVE:
        raise toolkit.ValidationError({'id': 'A lead cannot leave; ask a sysadmin to reassign the lead first'})
    membership.status = W.MEMBER_REMOVED
    membership.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    _ihpix_invalidate_wg_approvals(wg)
    return membership.as_dict()


def ihpix_working_group_member_process(context, data_dict):
    """approve / reject / remove / set_role / reinstate sobre una membresía
    (lead del workspace o sysadmin)."""
    toolkit.check_access('ihpix_working_group_member_process', context, data_dict)
    init_ihpix_working_groups_db()
    membership_id = toolkit.get_or_bust(data_dict, 'membership_id')
    membership = IhpixWorkingGroupMember.get(membership_id)
    if not membership:
        raise toolkit.ObjectNotFound('Membership not found')
    wg = IhpixWorkingGroup.get(membership.working_group_id)
    if not wg:
        raise toolkit.ObjectNotFound('IHP-IX working group not found')
    user_obj, _actor_membership, can_manage = _ihpix_wg_actor(context, wg)
    action = (data_dict.get('action') or u'').strip().lower()
    role = (data_dict.get('role') or u'').strip().lower() or None
    try:
        new_status, new_role = W.validate_member_action(
            membership.as_dict(), action, user_obj.id if user_obj else None,
            can_manage, role)
    except W.WorkspaceRuleError as e:
        raise toolkit.ValidationError(e.errors)

    now = _dt.datetime.utcnow()
    was_active = membership.status == W.MEMBER_ACTIVE
    membership.status = new_status
    membership.role = new_role
    membership.updated_at = now
    if new_status == W.MEMBER_ACTIVE and not was_active:
        membership.joined_at = now
        _ihpix_record_contribution(membership.user_id, 'member_joined',
                                   working_group_id=wg.id, dedupe=False)
    model.Session.commit()
    _ihpix_invalidate_wg_approvals(wg)
    if action in ('approve', 'reject', 'remove'):
        _ihpix_notify_wg_member(membership, wg, action)
    result = membership.as_dict()
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter
    result['user'] = get_ihpix_reporter(membership.user_id)
    return result


@toolkit.side_effect_free
def ihpix_working_group_member_list(context, data_dict):
    """Miembros de un workspace. Los pendientes solo para quien gestiona."""
    toolkit.check_access('ihpix_working_group_member_list', context, data_dict)
    wg = _ihpix_wg_or_404(data_dict)
    user_obj, _membership, can_manage = _ihpix_wg_actor(context, wg)
    status = (data_dict.get('status') or u'').strip() or None
    if status and status not in W.MEMBER_STATUSES:
        raise toolkit.ValidationError({'status': 'Must be one of: {}'.format(', '.join(W.MEMBER_STATUSES))})
    if status and status != W.MEMBER_ACTIVE and not can_manage:
        raise toolkit.NotAuthorized('Only the working group lead can see pending or removed members')
    rows = IhpixWorkingGroupMember.get_for_group(wg.id, status=status)
    if not can_manage:
        rows = [m for m in rows if m.status == W.MEMBER_ACTIVE]
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter
    results = []
    for m in rows:
        d = m.as_dict()
        d['user'] = get_ihpix_reporter(m.user_id)
        d['is_lead'] = (m.role == W.ROLE_LEAD and m.status == W.MEMBER_ACTIVE) or m.user_id == wg.lead_user_id
        results.append(d)
    return {'results': results, 'count': len(results), 'can_manage': can_manage}


@toolkit.side_effect_free
def ihpix_contribution_list(context, data_dict):
    """Feed del ledger por workspace (`working_group_id` / código) o por
    usuario (`user_id`, id o nombre; por defecto el usuario actual)."""
    toolkit.check_access('ihpix_contribution_list', context, data_dict)
    init_ihpix_working_groups_db()
    init_ihpix_activities_db()
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter
    kind = (data_dict.get('kind') or u'').strip() or None
    if kind and kind not in W.CONTRIBUTION_KINDS:
        raise toolkit.ValidationError({'kind': 'Must be one of: {}'.format(', '.join(W.CONTRIBUTION_KINDS))})
    limit = min(_parse_int_field(data_dict, 'limit', 30), 100)
    offset = max(_parse_int_field(data_dict, 'offset', 0), 0)

    wg_value = (data_dict.get('working_group_id') or u'').strip()
    if wg_value:
        wg = IhpixWorkingGroup.get_by_id_or_output(wg_value)
        if not wg:
            raise toolkit.ObjectNotFound('IHP-IX working group not found')
        rows, total = IhpixContribution.get_for_group(wg.id, kind=kind, limit=limit, offset=offset)
    else:
        user_value = (data_dict.get('user_id') or u'').strip()
        user = model.User.get(user_value) if user_value else _ihpix_user_obj(context)
        if not user:
            raise toolkit.ObjectNotFound('User not found')
        rows, total = IhpixContribution.get_for_user(user.id, kind=kind, limit=limit, offset=offset)

    activity_ids = {r.activity_id for r in rows if r.activity_id}
    wg_ids = {r.working_group_id for r in rows if r.working_group_id}
    activities = {}
    if activity_ids:
        for a in model.Session.query(IhpixActivity).filter(IhpixActivity.id.in_(list(activity_ids))).all():
            activities[a.id] = {'id': a.id, 'title': a.title, 'status': a.status, 'output': a.output}
    workspaces = {}
    if wg_ids:
        for g in model.Session.query(IhpixWorkingGroup).filter(IhpixWorkingGroup.id.in_(list(wg_ids))).all():
            workspaces[g.id] = {'id': g.id, 'output_code': g.output_code, 'title': g.title}
    results = []
    for r in rows:
        d = r.as_dict()
        # `meta` viaja como JSON en BD; los templates lo leen como dict
        try:
            d['meta'] = json.loads(d.get('meta') or u'{}') or {}
        except (TypeError, ValueError):
            d['meta'] = {}
        d['label'] = W.contribution_label(r.kind)
        d['user'] = get_ihpix_reporter(r.user_id)
        d['activity'] = activities.get(r.activity_id)
        d['workspace'] = workspaces.get(r.working_group_id)
        results.append(d)
    return {'results': results, 'count': total}


# Transiciones válidas de la revisión: acción → estados de origen permitidos.
# `rejected → published` cubre el botón "Re-approve" del panel admin.
_IHPIX_REVIEW_TRANSITIONS = {
    'approve': (IhpixActivity.STATUS_PENDING, IhpixActivity.STATUS_REJECTED),
    'reject': (IhpixActivity.STATUS_PENDING,),
}


def ihpix_report_review(context, data_dict):
    """Aprueba o rechaza un reporte. Sysadmin only.

    action: 'approve' → published, 'reject' → rejected (exige review_notes).
    Valida la transición de estado y avisa por email al reportante.
    """
    toolkit.check_access('ihpix_report_review', context, data_dict)
    init_ihpix_activities_db()

    activity = _ihpix_get_report_or_404(data_dict)
    action = (data_dict.get('action') or u'').strip().lower()
    if action not in _IHPIX_REVIEW_TRANSITIONS:
        raise toolkit.ValidationError(
            {'action': "Must be 'approve' or 'reject'"})
    if activity.status not in _IHPIX_REVIEW_TRANSITIONS[action]:
        raise toolkit.ValidationError(
            {'status': "Cannot {} a report in status '{}'".format(
                action, activity.status)})

    review_notes = (data_dict.get('review_notes') or u'').strip()
    if action == 'reject' and not review_notes:
        raise toolkit.ValidationError(
            {'review_notes': 'Review notes are required when rejecting'})

    now = _dt.datetime.utcnow()
    if action == 'approve':
        activity.status = IhpixActivity.STATUS_PUBLISHED
    else:
        activity.status = IhpixActivity.STATUS_REJECTED
    activity.review_notes = review_notes
    activity.reviewed_by = context.get('user', u'')
    activity.reviewed_at = now
    activity.updated_at = now

    if action == 'approve':
        _ihpix_ledger_on_publish(activity)
    model.Session.commit()
    _invalidate_approvals_cache()
    _ihpix_notify_reporter(activity, action)
    if action == 'approve':
        _ihpix_recompute_country_after_approve(activity)
    return activity.as_dict()


def _ihpix_recompute_country_after_approve(activity):
    """Mantiene el mapa al día tras publicar un reporte (best effort).

    Gobernado por `ckanext.theme_ejemplo.ihpix_recompute_on_approve`
    (default true). Sólo recalcula el país del reporte.
    """
    if not toolkit.asbool(toolkit.config.get(
            'ckanext.theme_ejemplo.ihpix_recompute_on_approve', True)):
        return
    if not (activity.country or u'').strip():
        return
    try:
        init_ihpix_country_summary_db()
        IhpixCountrySummary.recompute_from_activities(
            country=activity.country, resolve_name=ihpix_country_name)
    except Exception as e:
        model.Session.rollback()
        log.warning('IHP-IX: no se pudo recalcular el país %s: %s',
                    activity.country, e)


@toolkit.side_effect_free
def ihpix_dashboard_stats(context, data_dict):
    """Aggregated statistics for IHP-IX dashboard. Public access.

    Filters: priority_area, biennium, region, country, output.
    """
    toolkit.check_access('ihpix_dashboard_stats', context, data_dict)
    init_ihpix_activities_db()

    filters = {}
    for key in ('priority_area', 'biennium', 'region', 'country', 'output',
                'flagship'):
        val = (data_dict.get(key) or u'').strip()
        if val:
            filters[key] = val

    stats = IhpixActivity.get_stats(filters=filters)
    stats['timeline'] = IhpixActivity.get_timeline(filters=filters)
    stats['by_country'] = IhpixActivity.get_country_stats(
        filters=filters, limit=20
    )
    # Analítica adicional (fase iii): contribuidores, instituciones, matriz
    stats['contributors_total'] = IhpixActivity.count_distinct_reporters(filters)
    stats['top_institutions'] = IhpixActivity.get_top_institutions(filters, limit=10)
    stats['output_biennium_matrix'] = IhpixActivity.get_output_biennium_matrix(filters)
    return stats


@toolkit.side_effect_free
def ihpix_contributor_list(context, data_dict):
    """Usuarios que han reportado actividades publicadas, con sus conteos.

    Filtros: q (nombre de usuario), priority_area, output, biennium, region,
    country, flagship. Cada resultado incluye `reporter` resuelto.
    """
    toolkit.check_access('ihpix_contributor_list', context, data_dict)
    init_ihpix_activities_db()
    from ckanext.theme_ejemplo.helpers import get_ihpix_reporter

    filters = {}
    for key in ('priority_area', 'biennium', 'region', 'country', 'output',
                'flagship'):
        val = (data_dict.get(key) or u'').strip()
        if val:
            filters[key] = val
    q_text = (data_dict.get('q') or u'').strip() or None
    limit = min(_parse_int_field(data_dict, 'limit', 24), 100)
    offset = max(_parse_int_field(data_dict, 'offset', 0), 0)

    rows, total = IhpixActivity.get_contributor_stats(
        filters=filters, q_text=q_text, limit=limit, offset=offset)
    for row in rows:
        row['reporter'] = get_ihpix_reporter(row['reported_by'])
    return {'results': rows, 'count': total}


@toolkit.side_effect_free
def ihpix_admin_overview_stats(context, data_dict):
    """Extended admin-only stats for the IHP-IX overview dashboard.

    Adds: KPI activation counts + target totals, flagship counts, CTWG
    counts, institution-type counts, completeness histogram, status
    breakdown, recent pending activities, list of available filters.

    Filter args (all optional): priority_area, biennium, region, country,
    output, flagship, ctwg, status.
    """
    toolkit.check_access('ihpix_admin_overview_stats', context, data_dict)
    init_ihpix_activities_db()

    from ckanext.theme_ejemplo import ihpix_constants as C
    import json as _json

    filters = {}
    for key in ('priority_area', 'biennium', 'region', 'country', 'output',
                'flagship', 'ctwg', 'status'):
        val = data_dict.get(key, u'').strip() if data_dict.get(key) else u''
        if val:
            filters[key] = val

    q = model.Session.query(IhpixActivity)
    if 'priority_area' in filters:
        q = q.filter(IhpixActivity.priority_area == filters['priority_area'])
    if 'biennium' in filters:
        q = q.filter(IhpixActivity.biennium == filters['biennium'])
    if 'output' in filters:
        q = q.filter(IhpixActivity.output == filters['output'])
    if 'country' in filters:
        q = q.filter(IhpixActivity.country.ilike('%' + filters['country'] + '%'))
    if 'status' in filters:
        q = q.filter(IhpixActivity.status == filters['status'])
    if 'region' in filters:
        q = q.filter(IhpixActivity.regions.ilike('%' + filters['region'] + '%'))
    if 'flagship' in filters:
        q = q.filter(IhpixActivity.flagships.ilike('%' + filters['flagship'] + '%'))
    if 'ctwg' in filters:
        q = q.filter(IhpixActivity.cross_cutting_wg.ilike('%' + filters['ctwg'] + '%'))

    activities = q.all()
    total = len(activities)

    # ── Status breakdown ──
    status_counts = {}
    for s in (IhpixActivity.STATUS_DRAFT, IhpixActivity.STATUS_PENDING,
              IhpixActivity.STATUS_PUBLISHED, IhpixActivity.STATUS_REJECTED):
        status_counts[s] = sum(1 for a in activities if a.status == s)

    # ── KPI activation & target totals ──
    kpi_breakdown = {}
    for kpi_id, meta in C.KPIS.items():
        gate_attr = 'kpi_{}_active'.format(kpi_id)
        count_col = meta.get('count_column')
        actives = [a for a in activities if getattr(a, gate_attr, False)]
        total_target = 0
        youth_total = 0
        female_total = 0
        if count_col:
            for a in actives:
                total_target += int(getattr(a, count_col, 0) or 0)
        if meta.get('has_youth_female'):
            youth_attr = count_col + '_youth' if count_col else None
            female_attr = count_col + '_female' if count_col else None
            for a in actives:
                if youth_attr and hasattr(a, youth_attr):
                    youth_total += int(getattr(a, youth_attr, 0) or 0)
                if female_attr and hasattr(a, female_attr):
                    female_total += int(getattr(a, female_attr, 0) or 0)
        kpi_breakdown[kpi_id] = {
            'title': meta['title'],
            'active_count': len(actives),
            'target_total': total_target,
            'youth_total': youth_total,
            'female_total': female_total,
            'has_youth_female': meta.get('has_youth_female', False),
        }

    # ── Distribution helpers ──
    def _count_by_attr(attr):
        out = {}
        for a in activities:
            v = (getattr(a, attr, u'') or u'').strip()
            if v:
                out[v] = out.get(v, 0) + 1
        return [{'name': k, 'count': v} for k, v in
                sorted(out.items(), key=lambda x: -x[1])]

    def _count_by_json_attr(attr):
        out = {}
        for a in activities:
            raw = (getattr(a, attr, u'') or u'').strip()
            if not raw:
                continue
            try:
                items = _json.loads(raw) if raw.startswith('[') else [raw]
            except Exception:
                items = [raw]
            for it in items:
                if isinstance(it, str) and it.strip():
                    out[it] = out.get(it, 0) + 1
        return [{'name': k, 'count': v} for k, v in
                sorted(out.items(), key=lambda x: -x[1])]

    by_pa = _count_by_attr('priority_area')
    by_biennium = _count_by_attr('biennium')
    by_output = _count_by_attr('output')
    by_institution_type = _count_by_attr('institution_type')
    by_flagship = _count_by_json_attr('flagships')
    by_ctwg = _count_by_json_attr('cross_cutting_wg')
    by_region = _count_by_json_attr('regions')
    by_member_state = _count_by_json_attr('member_states')

    # ── Completeness (% per record) ──
    SECTION_FIELDS = {
        'I': ['focal_point_name', 'contact_email', 'institution_type',
              'institution', 'title', 'description', 'outcomes', 'biennium'],
        'II': ['priority_area', 'output', 'key_activity'],
        'III': ['cross_cutting_wg'],
        'IV': ['regions', 'member_states'],
        'V': ['kpi_1a_active', 'kpi_1b_active', 'kpi_2_active', 'kpi_3_active',
              'kpi_4_active', 'kpi_5_active', 'kpi_6_active', 'kpi_8_active'],
        'VI': ['additional_notes'],
    }
    completeness_buckets = {'0-25': 0, '25-50': 0, '50-75': 0, '75-100': 0}
    section_blank_counts = {sec: 0 for sec in SECTION_FIELDS}
    for a in activities:
        total_fields = 0
        filled_fields = 0
        for sec, fields in SECTION_FIELDS.items():
            sec_filled = 0
            for f in fields:
                total_fields += 1
                val = getattr(a, f, None)
                if val not in (None, '', 0, False):
                    filled_fields += 1
                    sec_filled += 1
            if sec_filled == 0:
                section_blank_counts[sec] += 1
        pct = (filled_fields * 100.0 / total_fields) if total_fields else 0
        if pct < 25:
            completeness_buckets['0-25'] += 1
        elif pct < 50:
            completeness_buckets['25-50'] += 1
        elif pct < 75:
            completeness_buckets['50-75'] += 1
        else:
            completeness_buckets['75-100'] += 1

    avg_completeness = 0
    if activities:
        total_fields = sum(len(f) for f in SECTION_FIELDS.values())
        s = 0
        for a in activities:
            filled = 0
            for fields in SECTION_FIELDS.values():
                for f in fields:
                    val = getattr(a, f, None)
                    if val not in (None, '', 0, False):
                        filled += 1
            s += (filled * 100.0 / total_fields) if total_fields else 0
        avg_completeness = round(s / len(activities), 1)

    # ── Member-state coverage ──
    member_states_covered = len({ms['name'] for ms in by_member_state})

    # ── Recent pending (5) ──
    recent_pending = (
        model.Session.query(IhpixActivity)
        .filter(IhpixActivity.status == IhpixActivity.STATUS_PENDING)
        .order_by(IhpixActivity.created_at.desc())
        .limit(5)
        .all()
    )
    recent_pending_list = [{
        'id': a.id,
        'title': a.title,
        'priority_area': a.priority_area,
        'institution': a.institution,
        'biennium': a.biennium,
        'reported_by': a.reported_by,
        'created_at': a.created_at.strftime('%Y-%m-%d') if a.created_at else '',
    } for a in recent_pending]

    return {
        'filters_applied': filters,
        'total': total,
        'status_counts': status_counts,
        'avg_completeness': avg_completeness,
        'member_states_covered': member_states_covered,
        'biennium_active': sum(1 for b in C.BIENNIA if any(a.biennium == b for a in activities)),
        'kpi_breakdown': kpi_breakdown,
        'by_priority_area': by_pa,
        'by_biennium': by_biennium,
        'by_output': by_output[:10],
        'by_institution_type': by_institution_type,
        'by_flagship': by_flagship,
        'by_ctwg': by_ctwg,
        'by_region': by_region,
        'by_member_state': by_member_state[:20],
        'completeness_buckets': completeness_buckets,
        'section_blank_counts': section_blank_counts,
        'recent_pending': recent_pending_list,
        # Adjuntos (publicaciones, eventos, datos) de las actividades filtradas
        'links_by_type': IhpixActivityLink.count_by_type(
            filters={k: v for k, v in filters.items()
                     if k in ('priority_area', 'biennium', 'output', 'country')},
            status=filters.get('status')),
    }


# ── IHP-IX GeoJSON & Country Summary Actions ───────────────────────────────

from ckanext.theme_ejemplo.model import (
    IhpixCountrySummary, init_ihpix_country_summary_db,
)


@toolkit.side_effect_free
def ihpix_geojson(context, data_dict):
    """GeoJSON FeatureCollection with country-level IHP-IX data.

    Filters:
        region (str): Filter by UNESCO region
        priority_area (str): Not used yet at country level, reserved

    Returns a GeoJSON FeatureCollection with Point features per country.
    """
    toolkit.check_access('ihpix_geojson', context, data_dict)
    init_ihpix_country_summary_db()

    region = (data_dict.get('region') or u'').strip() or None
    live_filters = {}
    for key in ('priority_area', 'biennium', 'output', 'flagship'):
        val = (data_dict.get(key) or u'').strip()
        if val:
            live_filters[key] = val
    if not live_filters:
        return IhpixCountrySummary.get_as_geojson(region=region)

    # Con filtros de actividad los conteos se calculan en vivo y se cruzan
    # con las coordenadas del snapshot por país.
    init_ihpix_activities_db()
    if region:
        live_filters['region'] = region
    counts = IhpixActivity.get_country_counts(live_filters)
    features = []
    for cs in IhpixCountrySummary.get_all(region=region):
        live = counts.get(cs.country)
        if not live or not (cs.latitude and cs.longitude):
            continue
        props = cs.as_dict()
        props['total_activities'] = live['total']
        for i in range(1, 6):
            props['pa%d_count' % i] = live['pa%d_count' % i]
        features.append({
            'type': 'Feature',
            'geometry': {'type': 'Point',
                         'coordinates': [float(cs.longitude), float(cs.latitude)]},
            'properties': props,
        })
    return {'type': 'FeatureCollection', 'features': features,
            'filters_applied': live_filters}


@toolkit.side_effect_free
def ihpix_activity_geojson(context, data_dict):
    """GeoJSON FeatureCollection of individual activities geolocated via
    their country's coordinates from ihpix_country_summary.

    Filters:
        priority_area (str)
        output (str)
        biennium (str)
        flagship (str)
        country (str)
        region (str)
    """
    toolkit.check_access('ihpix_activity_geojson', context, data_dict)
    init_ihpix_activities_db()
    init_ihpix_country_summary_db()

    # Obtener actividades filtradas (sin el tope por defecto de 20; el máximo
    # es configurable para no serializar decenas de miles de features)
    try:
        max_features = int(toolkit.config.get(
            'ckanext.theme_ejemplo.ihpix_geojson_max', 5000))
    except (TypeError, ValueError):
        max_features = 5000
    activities, _total = IhpixActivity.get_published(
        priority_area=(data_dict.get('priority_area') or u'').strip() or None,
        output=(data_dict.get('output') or u'').strip() or None,
        biennium=(data_dict.get('biennium') or u'').strip() or None,
        country=(data_dict.get('country') or u'').strip() or None,
        flagship=(data_dict.get('flagship') or u'').strip() or None,
        region=(data_dict.get('region') or u'').strip() or None,
        limit=max_features,
    )

    # Construir lookup de coordenadas por país
    country_coords = {}
    for cs in IhpixCountrySummary.get_all():
        if cs.latitude and cs.longitude:
            country_coords[cs.country] = (
                float(cs.longitude), float(cs.latitude)
            )

    features = []
    for act in activities:
        country = act.country or u''
        coords = country_coords.get(country)
        if not coords:
            continue
        features.append({
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': list(coords),
            },
            'properties': act.as_dict(),
        })

    return {
        'type': 'FeatureCollection',
        'features': features,
    }


def ihpix_country_name(value):
    """Slug de grupo Member State → título del grupo; cualquier otro valor
    (nombre completo del seed Excel) se devuelve tal cual.

    No usa `get_member_state_title` porque su fallback capitaliza el texto
    ("Republic of Korea" → "Republic Of Korea") y duplicaría filas.
    """
    value = (value or u'').strip()
    if not value:
        return value
    try:
        for name, title in toolkit.h.get_member_states_groups_list():
            if name == value:
                return title or value
    except Exception:
        pass
    return value


def ihpix_country_summary_recompute(context, data_dict):
    """Recalcula ihpix_country_summary desde las actividades publicadas.
    Sysadmin only. `country` opcional para limitar el recálculo."""
    toolkit.check_access('ihpix_country_summary_recompute', context, data_dict)
    init_ihpix_activities_db()
    init_ihpix_country_summary_db()
    country = (data_dict.get('country') or u'').strip() or None
    updated = IhpixCountrySummary.recompute_from_activities(
        country=country, resolve_name=ihpix_country_name)
    return {'success': True, 'updated': updated}


@toolkit.side_effect_free
def ihpix_country_summary_list(context, data_dict):
    """List country summary records for IHP-IX.

    Filters:
        region (str): UNESCO region filter
    """
    toolkit.check_access('ihpix_country_summary_list', context, data_dict)
    init_ihpix_country_summary_db()

    region = data_dict.get('region', u'').strip() or None
    items = IhpixCountrySummary.get_all(region=region)
    return {
        'results': [i.as_dict() for i in items],
        'count': len(items),
    }


# ── Initiative Request Actions ──────────────────────────────────────────────

from ckanext.theme_ejemplo.model import (
    InitiativeRequest,
    init_initiative_requests_db,
)


def _process_initiative_logo_upload(upload_file):
    """Valida y sube el logo de una solicitud de iniciativa.

    Devuelve la URL pública estática del archivo subido o lanza ValidationError.
    """
    if not upload_file or not getattr(upload_file, 'filename', ''):
        return u''

    reason = get_invalid_user_image_upload_reason(upload_file)
    if reason:
        raise toolkit.ValidationError({
            'logo_upload': [toolkit._(
                'El archivo subido no es una imagen válida (razón: {reason}).'
            ).format(reason=reason)]
        })

    import ckan.lib.uploader as uploader
    import ckan.lib.helpers as h_core
    upload = uploader.get_uploader('initiative_requests')
    upload.update_data_dict(
        {'upload': upload_file, 'url': u'', 'clear_upload': u''},
        'url', 'upload', 'clear_upload',
    )
    upload.upload()
    return h_core.url_for_static(
        'uploads/initiative_requests/{}'.format(upload.filename),
        qualified=False,
    )


def initiative_request_create(context, data_dict):
    """Crea una solicitud de iniciativa.

    :param title: título de la iniciativa (requerido)
    :param description: descripción
    :param logo_upload: FileStorage opcional con el logo
    :param logo_url: URL alternativa al logo (si no se sube archivo)
    """
    toolkit.check_access('initiative_request_create', context, data_dict)
    init_initiative_requests_db()

    title = (toolkit.get_or_bust(data_dict, 'title') or u'').strip()
    description = (data_dict.get('description', u'') or u'').strip()
    logo_url = (data_dict.get('logo_url', u'') or u'').strip()
    logo_upload = data_dict.get('logo_upload')

    if not title:
        raise toolkit.ValidationError({
            'title': [toolkit._('Title is required.')]
        })

    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if not user_obj:
        raise toolkit.NotAuthorized(toolkit._('You must be logged in.'))

    # No permitir más de una solicitud pendiente por usuario
    existing = InitiativeRequest.get_pending_for_user(user_obj.id)
    if existing:
        raise toolkit.ValidationError({
            'title': [toolkit._(
                'You already have a pending initiative request. '
                'Please wait for an administrator to review it.'
            )]
        })

    # Procesar logo (upload tiene prioridad sobre URL externa)
    if logo_upload and getattr(logo_upload, 'filename', ''):
        logo_url = _process_initiative_logo_upload(logo_upload)
    elif logo_url and not is_valid_user_image_reference(logo_url):
        raise toolkit.ValidationError({
            'logo_url': [toolkit._('The logo URL is not valid.')]
        })

    # Sugerir slug a partir del título
    from ckan.lib.munge import munge_name
    proposed_name = munge_name(title)

    req = InitiativeRequest(
        user_id=user_obj.id,
        title=title,
        description=description,
        name=proposed_name,
        logo_url=logo_url,
    )
    model.Session.add(req)
    model.Session.commit()

    return req.as_dict()


@toolkit.side_effect_free
def initiative_request_list(context, data_dict):
    """Lista solicitudes de iniciativa para el panel admin.

    :param status: filtro opcional (pending/approved/rejected)
    """
    toolkit.check_access('initiative_request_list', context, data_dict)
    init_initiative_requests_db()

    status_filter = data_dict.get('status', None)
    requests_list = InitiativeRequest.get_all(status=status_filter)

    results = []
    for req in requests_list:
        user_obj = model.User.get(req.user_id) if req.user_id else None
        handler_obj = model.User.get(req.handled_by) if req.handled_by else None
        entry = req.as_dict()
        entry.update({
            'user_name': user_obj.name if user_obj else u'',
            'user_fullname': (user_obj.fullname or user_obj.name) if user_obj else u'',
            'user_email': user_obj.email if user_obj else u'',
            'user_image_url': normalize_user_image_url(user_obj.image_url) if user_obj else u'',
            'handler_name': (handler_obj.fullname or handler_obj.name) if handler_obj else u'',
        })
        results.append(entry)

    return {'results': results, 'count': len(results)}


def initiative_request_process(context, data_dict):
    """Aprueba o rechaza una solicitud de iniciativa.

    Al aprobar: crea el grupo CKAN con el logo subido y añade al solicitante
    como admin del grupo. Al rechazar: guarda admin_note.

    :param id: id de la solicitud
    :param action: 'approve' o 'reject'
    :param admin_note: nota opcional (motivo de rechazo)
    :param name: slug opcional (editable por el admin antes de aprobar)
    """
    import datetime
    toolkit.check_access('initiative_request_process', context, data_dict)
    init_initiative_requests_db()

    request_id = toolkit.get_or_bust(data_dict, 'id')
    action = toolkit.get_or_bust(data_dict, 'action')
    admin_note = (data_dict.get('admin_note', u'') or u'').strip()
    override_name = (data_dict.get('name', u'') or u'').strip()

    if action not in ('approve', 'reject'):
        raise toolkit.ValidationError({
            'action': [toolkit._('Debe ser "approve" o "reject".')]
        })

    req = InitiativeRequest.get(request_id)
    if not req:
        raise toolkit.ObjectNotFound(toolkit._('Solicitud no encontrada.'))

    if req.status != InitiativeRequest.STATUS_PENDING:
        raise toolkit.ValidationError({
            'status': [toolkit._('Esta solicitud ya fue procesada.')]
        })

    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))

    if action == 'reject':
        req.status = InitiativeRequest.STATUS_REJECTED
        req.handled_by = user_obj.id if user_obj else None
        req.handled_at = datetime.datetime.utcnow()
        req.admin_note = admin_note
        model.Session.commit()
        _invalidate_approvals_cache()
        return req.as_dict()

    # action == 'approve' — crear grupo y añadir solicitante como admin
    from ckan.lib.munge import munge_name
    group_name = munge_name(override_name or req.name or req.title)

    group_dict = {
        'name': group_name,
        'title': req.title,
        'description': req.description or u'',
        'type': 'group',
    }
    if req.logo_url:
        group_dict['image_url'] = req.logo_url

    try:
        created = toolkit.get_action('group_create')(
            {'ignore_auth': True, 'user': user_obj.name if user_obj else None},
            group_dict,
        )
    except toolkit.ValidationError as e:
        # Probablemente colisión de slug; relanzar para que el admin lo vea
        raise toolkit.ValidationError({
            'name': [toolkit._(
                'No se pudo crear el grupo (posible conflicto de nombre): {err}'
            ).format(err=str(e))]
        })

    # Añadir al solicitante como admin del grupo recién creado
    try:
        toolkit.get_action('member_create')(
            {'ignore_auth': True},
            {
                'id': created['id'],
                'object': req.user_id,
                'object_type': 'user',
                'capacity': 'admin',
            },
        )
    except Exception as e:
        log.warning(
            f'Initiative approved (group {created["id"]}) but failed to add '
            f'requester as admin: {e}'
        )

    req.status = InitiativeRequest.STATUS_APPROVED
    req.handled_by = user_obj.id if user_obj else None
    req.handled_at = datetime.datetime.utcnow()
    req.admin_note = admin_note
    req.created_group_id = created['id']
    req.name = group_name
    model.Session.commit()
    _invalidate_approvals_cache()

    return req.as_dict()


@toolkit.side_effect_free
def initiative_request_count(context, data_dict):
    """Cantidad de solicitudes pendientes. Para el badge sysadmin."""
    user_obj = context.get('auth_user_obj') or model.User.get(context.get('user'))
    if not user_obj or not user_obj.sysadmin:
        return {'count': 0}
    init_initiative_requests_db()
    return {'count': InitiativeRequest.count_pending()}


# ── Open Learning Course Actions ─────────────────────────────────────────────

from ckanext.theme_ejemplo.model import (
    OpenLearningCourse, init_open_learning_courses_db,
    VALID_COURSE_STATUSES, VALID_COURSE_TYPES,
)


@toolkit.side_effect_free
def open_learning_course_list(context, data_dict):
    """Lista los cursos de la caché curada. Solo sysadmin.

    Filtros opcionales: status, course_type, is_available.
    """
    toolkit.check_access('open_learning_course_list', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.course_list(context, data_dict)
    init_open_learning_courses_db()

    courses = OpenLearningCourse.get_all()

    status = data_dict.get('status')
    if status:
        courses = [c for c in courses if c.status == status]
    course_type = data_dict.get('course_type')
    if course_type:
        courses = [c for c in courses if c.course_type == course_type]
    if 'is_available' in data_dict:
        val = data_dict['is_available']
        if isinstance(val, str):
            val = val.lower() in ('true', '1', 'yes', 'on')
        courses = [c for c in courses if bool(c.is_available) == val]

    last_sync = OpenLearningCourse.last_sync_at()
    return {
        'results': [c.as_dict() for c in courses],
        'count': len(courses),
        'counts_by_status': OpenLearningCourse.counts_by_status(),
        'last_sync_at': last_sync.isoformat() if last_sync else None,
    }


def open_learning_course_set_status(context, data_dict):
    """Cambia el status de curación de un curso. Solo sysadmin."""
    toolkit.check_access('open_learning_course_set_status', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.set_status(context, data_dict)
    init_open_learning_courses_db()

    course_id = toolkit.get_or_bust(data_dict, 'id')
    status = toolkit.get_or_bust(data_dict, 'status')
    if status not in VALID_COURSE_STATUSES:
        raise toolkit.ValidationError({'status': 'Invalid status'})

    course = OpenLearningCourse.get(course_id)
    if not course:
        raise toolkit.ObjectNotFound('Open Learning course not found')

    import datetime
    course.status = status
    course.updated_at = datetime.datetime.utcnow()
    model.Session.commit()
    return course.as_dict()


def open_learning_course_set_type(context, data_dict):
    """Corrige manualmente el tipo de un curso (permanent/scheduled).

    Marca course_type_override para que el sync no lo recalcule. Con
    reset_override=True vuelve a la auto-detección.
    """
    toolkit.check_access('open_learning_course_set_type', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.set_type(context, data_dict)
    init_open_learning_courses_db()

    course_id = toolkit.get_or_bust(data_dict, 'id')
    course = OpenLearningCourse.get(course_id)
    if not course:
        raise toolkit.ObjectNotFound('Open Learning course not found')

    reset_override = data_dict.get('reset_override', False)
    if isinstance(reset_override, str):
        reset_override = reset_override.lower() in ('true', '1', 'yes', 'on')

    if reset_override:
        from ckanext.theme_ejemplo import openlearning
        try:
            api_course = json.loads(course.raw_json or u'{}')
        except ValueError:
            api_course = {}
        course.course_type = openlearning._detect_course_type(api_course)
        course.course_type_override = False
    else:
        course_type = toolkit.get_or_bust(data_dict, 'course_type')
        if course_type not in VALID_COURSE_TYPES:
            raise toolkit.ValidationError({'course_type': 'Invalid course_type'})
        course.course_type = course_type
        course.course_type_override = True

    import datetime
    course.updated_at = datetime.datetime.utcnow()
    model.Session.commit()
    return course.as_dict()


def open_learning_sync(context, data_dict):
    """Fuerza una sincronización con la API de Open Learning. Solo sysadmin."""
    toolkit.check_access('open_learning_sync', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.sync(context, data_dict)
    from ckanext.theme_ejemplo import openlearning
    return openlearning.sync_courses(force=True)


@toolkit.side_effect_free
def open_learning_course_search(context, data_dict):
    """Busca cursos en la API de Open Learning por término. Solo sysadmin.

    No persiste nada: devuelve los resultados de la API marcando cuáles
    ya están en la BD para que el admin decida cuáles agregar.
    """
    toolkit.check_access('open_learning_course_search', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.search(context, data_dict)
    init_open_learning_courses_db()

    query = data_dict.get('query', u'').strip()
    if not query:
        return {'results': [], 'already_in_db': 0}

    from ckanext.theme_ejemplo import openlearning
    try:
        api_results = openlearning.search_courses_api(query)
    except RuntimeError:
        raise toolkit.ValidationError({'query': 'Open Learning API is unavailable'})

    results = []
    already_in_db = 0
    for c in api_results:
        existing = OpenLearningCourse.get_by_course_id(c['course_id'])
        if existing:
            already_in_db += 1
            c['in_db'] = True
            c['db_status'] = existing.status
        else:
            c['in_db'] = False
        results.append(c)

    return {'results': results, 'already_in_db': already_in_db}


def open_learning_course_add(context, data_dict):
    """Agrega un curso de Open Learning por course_id. Solo sysadmin.

    Fetcha el curso individual de la API y hace upsert en la BD.
    Respeta el contrato de curation: nuevos cursos como 'pending',
    existentes preservan status/course_type_override/display_order.
    """
    toolkit.check_access('open_learning_course_add', context, data_dict)
    from ckan import plugins as p
    if p.plugin_loaded('learning'):
        from ckanext.learning import compat
        return compat.add(context, data_dict)
    init_open_learning_courses_db()

    course_id = toolkit.get_or_bust(data_dict, 'course_id')

    from ckanext.theme_ejemplo import openlearning
    try:
        course, action = openlearning.fetch_and_upsert_course(course_id)
    except RuntimeError:
        raise toolkit.ValidationError(
            {'course_id': 'Open Learning API is unavailable'})
    return {'success': True, 'course': course.as_dict(), 'action': action}
