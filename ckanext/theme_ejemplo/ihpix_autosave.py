"""Identidad y comparación de borradores para reintentos sin duplicados."""
import datetime
import json
import uuid

from . import ihpix_links


def draft_identity(user_id, client_id):
    client_id = str(uuid.UUID(str(client_id)))
    identity = uuid.uuid5(uuid.NAMESPACE_URL, 'ihpix-draft:{}:{}'.format(user_id, client_id))
    return str(identity), identity.int & ((1 << 63) - 1)


def equivalent(stored, values):
    def normalize(value):
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, str) and value[:1] in ('[', '{'):
            try:
                return json.loads(value)
            except ValueError:
                pass
        return value
    return all(normalize(stored.get(key)) == normalize(value) for key, value in values.items())


def equivalent_links(stored, requested):
    def normalize(items):
        result, seen = [], set()
        for item in ihpix_links.parse_links_json(items):
            clean = ihpix_links.validate_link(item)
            key = ihpix_links.dedupe_key(clean)
            if key in seen:
                continue
            seen.add(key)
            clean.pop('id', None)
            clean.pop('display_order', None)
            result.append(clean)
        return result
    try:
        return normalize(stored) == normalize(requested)
    except (ihpix_links.LinkValidationError, ValueError, TypeError):
        return False
