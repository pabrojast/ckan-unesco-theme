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

log = logging.getLogger(__name__)

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

    if q:
        q_like = f'%{q}%'
        query = query.filter(
            model.User.name.ilike(q_like) |
            model.User.fullname.ilike(q_like)
        )

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
        q_like = f'%{q}%'
        query = query.filter(
            model.User.name.ilike(q_like) |
            model.User.fullname.ilike(q_like) |
            model.User.email.ilike(q_like)
        )

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

    priority_area = data_dict.get('priority_area', '')
    output = data_dict.get('output', '')
    q_text = data_dict.get('q', '')
    status = data_dict.get('status', '')
    limit = min(int(data_dict.get('limit', 20)), 100)
    offset = max(int(data_dict.get('offset', 0)), 0)

    user_obj = context.get('auth_user_obj')
    is_sysadmin = user_obj and user_obj.sysadmin

    if is_sysadmin and status:
        results, total = IhpixActivity.get_all(
            status=status, priority_area=priority_area,
            limit=limit, offset=offset
        )
    elif is_sysadmin and not status:
        results, total = IhpixActivity.get_all(
            priority_area=priority_area, limit=limit, offset=offset
        )
    else:
        results, total = IhpixActivity.get_published(
            priority_area=priority_area, output=output,
            q_text=q_text, limit=limit, offset=offset
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

    return activity.as_dict()


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
)

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
    if status not in ('draft', 'published'):
        raise toolkit.ValidationError(
            {'status': 'Must be draft or published'}
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
        if status not in ('draft', 'published'):
            raise toolkit.ValidationError(
                {'status': 'Must be draft or published'}
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

    import datetime as _dt
    activity.updated_at = _dt.datetime.utcnow()
    model.Session.commit()
    return activity.as_dict()


def ihpix_activity_delete(context, data_dict):
    """Delete an IHP-IX activity. Sysadmin only."""
    toolkit.check_access('ihpix_activity_delete', context, data_dict)
    init_ihpix_activities_db()

    activity_id = toolkit.get_or_bust(data_dict, 'id')
    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    model.Session.delete(activity)
    model.Session.commit()
    return {'success': True}


# ── IHP-IX Reporting & Dashboard ────────────────────────────────────────────

def ihpix_report_submit(context, data_dict):
    """Submit an IHP-IX activity report. Any logged-in user.
    Creates an activity with status=pending for admin review."""
    toolkit.check_access('ihpix_report_submit', context, data_dict)
    init_ihpix_activities_db()

    title = data_dict.get('title', u'').strip()
    priority_area = data_dict.get('priority_area', u'').strip()
    if not title:
        raise toolkit.ValidationError({'title': 'Title is required'})
    if priority_area not in VALID_PRIORITY_AREAS:
        raise toolkit.ValidationError(
            {'priority_area': 'Must be one of: {}'.format(
                ', '.join(VALID_PRIORITY_AREAS))}
        )

    import datetime as _dt
    activity = IhpixActivity(
        title=title,
        priority_area=priority_area,
        description=data_dict.get('description', u'').strip(),
        output=data_dict.get('output', u'').strip(),
        country=data_dict.get('country', u'').strip(),
        institution=data_dict.get('institution', u'').strip(),
        link=data_dict.get('link', u'').strip(),
        image_url=data_dict.get('image_url', u''),
        status=IhpixActivity.STATUS_PENDING,
        reported_by=context.get('user', u''),
        contact_name=data_dict.get('contact_name', u'').strip(),
        contact_email=data_dict.get('contact_email', u'').strip(),
    )

    # Parse dates
    for field in ('reported_date', 'start_date', 'end_date'):
        val = data_dict.get(field, u'').strip()
        if val:
            try:
                setattr(activity, field, _dt.datetime.strptime(val, '%Y-%m-%d').date())
            except (ValueError, TypeError):
                raise toolkit.ValidationError(
                    {field: 'Invalid date format. Use YYYY-MM-DD'}
                )

    model.Session.add(activity)
    model.Session.commit()
    return activity.as_dict()


def ihpix_report_review(context, data_dict):
    """Approve or reject a pending report. Sysadmin only.
    action: 'approve' → published, 'reject' → rejected."""
    toolkit.check_access('ihpix_report_review', context, data_dict)
    init_ihpix_activities_db()

    activity_id = toolkit.get_or_bust(data_dict, 'id')
    action = data_dict.get('action', u'').strip().lower()
    if action not in ('approve', 'reject'):
        raise toolkit.ValidationError(
            {'action': "Must be 'approve' or 'reject'"}
        )

    activity = IhpixActivity.get(activity_id)
    if not activity:
        raise toolkit.ObjectNotFound('IHP-IX activity not found')

    import datetime as _dt
    if action == 'approve':
        activity.status = IhpixActivity.STATUS_PUBLISHED
    else:
        activity.status = IhpixActivity.STATUS_REJECTED

    activity.review_notes = data_dict.get('review_notes', u'').strip()
    activity.reviewed_by = context.get('user', u'')
    activity.reviewed_at = _dt.datetime.utcnow()
    activity.updated_at = _dt.datetime.utcnow()

    model.Session.commit()
    return activity.as_dict()


@toolkit.side_effect_free
def ihpix_dashboard_stats(context, data_dict):
    """Aggregated statistics for IHP-IX dashboard. Public access.

    Filters: priority_area, biennium, region, country, output.
    """
    toolkit.check_access('ihpix_dashboard_stats', context, data_dict)
    init_ihpix_activities_db()

    filters = {}
    for key in ('priority_area', 'biennium', 'region', 'country', 'output'):
        val = data_dict.get(key, u'').strip()
        if val:
            filters[key] = val

    stats = IhpixActivity.get_stats(filters=filters)
    stats['timeline'] = IhpixActivity.get_timeline(filters=filters)
    stats['by_country'] = IhpixActivity.get_country_stats(
        filters=filters, limit=20
    )
    return stats


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

    region = data_dict.get('region', u'').strip() or None
    return IhpixCountrySummary.get_as_geojson(region=region)


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

    # Obtener actividades filtradas
    activities = IhpixActivity.get_published(
        priority_area=data_dict.get('priority_area', u'').strip() or None,
        output=data_dict.get('output', u'').strip() or None,
        biennium=data_dict.get('biennium', u'').strip() or None,
        country=data_dict.get('country', u'').strip() or None,
        flagship=data_dict.get('flagship', u'').strip() or None,
        region=data_dict.get('region', u'').strip() or None,
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
