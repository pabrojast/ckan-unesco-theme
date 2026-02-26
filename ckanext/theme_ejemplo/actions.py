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
