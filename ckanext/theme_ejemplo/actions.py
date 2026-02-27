# encoding: utf-8
"""Custom action overrides for People & Organizations feature."""

import json
import logging
import ckan.plugins.toolkit as toolkit
import ckan.logic as logic
import ckan.model as model
from ckan.common import current_user
from sqlalchemy.orm.attributes import flag_modified

log = logging.getLogger(__name__)

PROFILE_FIELDS = [
    'job_title', 'institution', 'country', 'phone',
    'website', 'orcid', 'expertise_areas', 'social_links',
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
        if field in ('expertise_areas', 'social_links') and isinstance(val, str):
            try:
                val = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                val = [] if field == 'expertise_areas' else {}
        result[field] = val

    # Always expose plugin_extras.theme_ejemplo as 'profile' for convenience
    result['profile'] = profile
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
            profile_data[field] = val

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

    # Call core user_update
    result = logic.action.update.user_update(context, data_dict)

    # Save profile fields into plugin_extras
    if profile_data:
        user_obj = model.User.get(result['id'])
        if user_obj:
            extras = user_obj.plugin_extras or {}
            if 'theme_ejemplo' not in extras:
                extras['theme_ejemplo'] = {}
            extras['theme_ejemplo'].update(profile_data)
            user_obj.plugin_extras = extras
            flag_modified(user_obj, 'plugin_extras')
            model.Session.commit()

            # Update result with saved profile
            for field in PROFILE_FIELDS:
                val = extras['theme_ejemplo'].get(field, '')
                if field in ('expertise_areas', 'social_links') and isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        val = [] if field == 'expertise_areas' else {}
                result[field] = val
            result['profile'] = extras.get('theme_ejemplo', {})

    return result


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

        # Filter by country
        if country and profile.get('country', '').lower() != country.lower():
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
            orgs.append({'name': g.name, 'title': g.title or g.name})

        results.append({
            'id': user_obj.id,
            'name': user_obj.name,
            'fullname': user_obj.fullname or user_obj.name,
            'image_url': user_obj.image_url,
            'job_title': profile.get('job_title', ''),
            'institution': profile.get('institution', ''),
            'country': profile.get('country', ''),
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

            members.append({
                'id': user_obj.id,
                'name': user_obj.name,
                'fullname': user_obj.fullname or user_obj.name,
                'image_url': user_obj.image_url,
                'job_title': profile.get('job_title', ''),
                'institution': profile.get('institution', ''),
                'country': profile.get('country', ''),
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
            'user_image_url': user_obj.image_url if user_obj else u'',
            'organization_id': req.organization_id,
            'message': req.message or u'',
            'status': req.status,
            'handled_by': req.handled_by,
            'handler_name': (handler_obj.fullname or handler_obj.name) if handler_obj else u'',
            'handled_at': req.handled_at.isoformat() if req.handled_at else None,
            'admin_note': req.admin_note or u'',
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
        # Add user as member of the organization
        toolkit.get_action('member_create')(
            {'ignore_auth': True},
            {
                'id': req.organization_id,
                'object': req.user_id,
                'object_type': 'user',
                'capacity': 'member',
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
