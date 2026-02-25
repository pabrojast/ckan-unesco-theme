# encoding: utf-8
"""Validators for People & Organizations extended user profile fields."""

import json
import logging
from ckan.plugins import toolkit

log = logging.getLogger(__name__)

# Extra profile fields stored in plugin_extras
PROFILE_FIELDS = [
    'job_title', 'institution', 'country', 'phone',
    'website', 'orcid', 'expertise_areas', 'social_links',
]


def _not_empty_string(value):
    if isinstance(value, str):
        return value.strip()
    return value or ''


def user_profile_field(key, data, errors, context):
    """Validator that accepts any string value for a profile field."""
    value = data.get(key)
    if value is toolkit.missing or value is None:
        data[key] = ''
    else:
        data[key] = _not_empty_string(value)


def user_expertise_areas(key, data, errors, context):
    """Validate expertise_areas as a comma-separated string or JSON list."""
    value = data.get(key)
    if value is toolkit.missing or value is None:
        data[key] = '[]'
        return

    if isinstance(value, list):
        data[key] = json.dumps(value)
        return

    if isinstance(value, str):
        value = value.strip()
        if not value:
            data[key] = '[]'
            return
        # Try JSON list first
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                data[key] = json.dumps(parsed)
                return
        except (json.JSONDecodeError, TypeError):
            pass
        # Treat as comma-separated
        items = [item.strip() for item in value.split(',') if item.strip()]
        data[key] = json.dumps(items)


def user_social_links(key, data, errors, context):
    """Validate social_links as a JSON dict with known keys."""
    value = data.get(key)
    allowed_keys = {'linkedin', 'twitter', 'researchgate', 'github', 'website'}

    if value is toolkit.missing or value is None:
        data[key] = '{}'
        return

    if isinstance(value, dict):
        filtered = {k: v for k, v in value.items() if k in allowed_keys and v}
        data[key] = json.dumps(filtered)
        return

    if isinstance(value, str):
        value = value.strip()
        if not value:
            data[key] = '{}'
            return
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                filtered = {k: v for k, v in parsed.items() if k in allowed_keys and v}
                data[key] = json.dumps(filtered)
                return
        except (json.JSONDecodeError, TypeError):
            pass
        data[key] = '{}'
