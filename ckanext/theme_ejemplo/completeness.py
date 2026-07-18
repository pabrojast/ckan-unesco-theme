# encoding: utf-8
"""Metadata completeness scoring for datasets and documents.

Pure functions over a package dict (as returned by ``package_show``).
Nothing is persisted on the package itself: the score is injected into
API/template dicts at read time and sent to Solr at index time, so
harvested datasets are never modified and scheming validation is not
involved.
"""

import json
import logging

import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

SUPPORTED_TYPES = ('dataset', 'documents')

# Languages that earn the fluent bonus. 'en' is the schema's required
# base language, so it never counts towards the bonus by itself.
FLUENT_LANGS = ('en', 'es', 'fr', 'ar')
FLUENT_BONUS_FIELDS = ('title_translated', 'notes_translated')
FLUENT_BONUS_POINTS = 5
NOTES_MIN_LENGTH = 100

# Check types:
#   value    - non-empty scalar
#   list     - non-empty list (or non-empty comma-separated string)
#   any_of   - at least one of the listed fields is non-empty
#   notes    - notes_translated has an 'en' text; full weight only when
#              it is at least NOTES_MIN_LENGTH chars long
#   spatial  - 'spatial' geometry or a full xmin/ymin/xmax/ymax bbox
#   resource - at least one resource with the listed subfields filled
DATASET_FIELD_WEIGHTS = [
    {'field': 'notes_translated', 'weight': 10, 'check': 'notes'},
    {'field': 'tags', 'weight': 8, 'check': 'list'},
    {'field': 'theme', 'weight': 6, 'check': 'value'},
    {'field': 'graphic_overview', 'weight': 4, 'check': 'value'},
    {'field': 'spatial', 'weight': 8, 'check': 'spatial'},
    {'field': 'reference_system', 'weight': 3, 'check': 'value'},
    {'field': 'representation_type', 'weight': 2, 'check': 'value'},
    {'field': 'temporal_start', 'weight': 5, 'check': 'value'},
    {'field': 'temporal_end', 'weight': 3, 'check': 'value'},
    {'field': 'frequency', 'weight': 4, 'check': 'value'},
    {'field': 'provenance', 'weight': 6, 'check': 'value'},
    {'field': 'purpose', 'weight': 5, 'check': 'value'},
    {'field': 'lineage_source', 'weight': 4, 'check': 'list'},
    {'field': 'conforms_to', 'weight': 2, 'check': 'list'},
    {'field': 'license_id', 'weight': 6, 'check': 'value'},
    {'field': 'access_rights', 'weight': 4, 'check': 'value'},
    {'field': 'contact_name', 'weight': 4, 'check': 'value'},
    {'field': 'contact_url', 'weight': 2, 'check': 'value'},
    {'field': 'publisher_name', 'weight': 4, 'check': 'value'},
    {'field': 'publisher_type', 'weight': 2, 'check': 'value'},
    {'field': 'author', 'weight': 3, 'check': 'any_of',
     'fields': ('author', 'authors')},
    {'field': 'resources', 'weight': 8, 'check': 'resource',
     'subfields': ('description', 'format')},
    {'field': 'version', 'weight': 2, 'check': 'value'},
    {'field': 'version_notes', 'weight': 2, 'check': 'value'},
]

DOCUMENTS_FIELD_WEIGHTS = [
    {'field': 'notes_translated', 'weight': 10, 'check': 'notes'},
    {'field': 'document_type', 'weight': 8, 'check': 'value'},
    {'field': 'publication_year', 'weight': 6, 'check': 'value'},
    {'field': 'authors_json', 'weight': 8, 'check': 'any_of',
     'fields': ('authors_json', 'author')},
    {'field': 'ihp_water_theme', 'weight': 6, 'check': 'list'},
    {'field': 'citation', 'weight': 6, 'check': 'any_of',
     'fields': ('citation', 'custom_citation')},
    {'field': 'document_doi', 'weight': 8, 'check': 'any_of',
     'fields': ('document_doi', 'custom_doi')},
    {'field': 'tags', 'weight': 6, 'check': 'list'},
    {'field': 'graphic_overview', 'weight': 4, 'check': 'value'},
    {'field': 'license_id', 'weight': 6, 'check': 'value'},
    {'field': 'contact_name', 'weight': 4, 'check': 'value'},
    {'field': 'resources', 'weight': 6, 'check': 'resource',
     'subfields': ('format',)},
]

_WEIGHTS_BY_TYPE = {
    'dataset': DATASET_FIELD_WEIGHTS,
    'documents': DOCUMENTS_FIELD_WEIGHTS,
}


def _thresholds():
    config = toolkit.config
    try:
        full = int(config.get(
            'ckanext.theme_ejemplo.completeness_full_threshold', 75))
    except (TypeError, ValueError):
        full = 75
    try:
        medium = int(config.get(
            'ckanext.theme_ejemplo.completeness_medium_threshold', 40))
    except (TypeError, ValueError):
        medium = 40
    return full, medium


def get_category(score):
    full, medium = _thresholds()
    if score >= full:
        return 'full'
    if score >= medium:
        return 'medium'
    return 'limited'


def _get(pkg_dict, field):
    """Field lookup with fallback to the extras list (legacy datasets)."""
    value = pkg_dict.get(field)
    if value not in (None, '', [], {}):
        return value
    for extra in pkg_dict.get('extras') or []:
        if isinstance(extra, dict) and extra.get('key') == field:
            return extra.get('value')
    return None


def _maybe_json(value):
    """Fluent fields may arrive as dicts or as their JSON string form."""
    if isinstance(value, str) and value.strip().startswith('{'):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return any(_has_value(v) for v in
                   (value.values() if isinstance(value, dict) else value))
    return True


def _fluent_langs(pkg_dict, field):
    value = _maybe_json(_get(pkg_dict, field))
    if not isinstance(value, dict):
        return []
    return [lang for lang in FLUENT_LANGS if _has_value(value.get(lang))]


def _check_points(pkg_dict, spec):
    """Return points earned for one spec entry (0..weight)."""
    check = spec['check']
    weight = spec['weight']

    if check == 'value':
        return weight if _has_value(_get(pkg_dict, spec['field'])) else 0

    if check == 'list':
        value = _get(pkg_dict, spec['field'])
        if isinstance(value, str):
            value = [v for v in value.split(',') if v.strip()]
        return weight if _has_value(value) else 0

    if check == 'any_of':
        for field in spec['fields']:
            value = _get(pkg_dict, field)
            if field.endswith('_json'):
                value = _maybe_json(value)
            if _has_value(value):
                return weight
        return 0

    if check == 'notes':
        value = _maybe_json(_get(pkg_dict, 'notes_translated'))
        text = ''
        if isinstance(value, dict):
            text = value.get('en') or ''
        elif isinstance(value, str):
            text = value
        if not text.strip():
            text = pkg_dict.get('notes') or ''
        if not text.strip():
            return 0
        # Present but short: half credit, still flagged for improvement.
        return weight if len(text.strip()) >= NOTES_MIN_LENGTH else weight // 2

    if check == 'spatial':
        if _has_value(_get(pkg_dict, 'spatial')):
            return weight
        bbox = [_get(pkg_dict, k) for k in ('xmin', 'ymin', 'xmax', 'ymax')]
        return weight if all(_has_value(v) for v in bbox) else 0

    if check == 'resource':
        for res in pkg_dict.get('resources') or []:
            if not isinstance(res, dict):
                continue
            if all(_has_value(res.get(sub)) for sub in spec['subfields']):
                return weight
        return 0

    return 0


def calculate_completeness(pkg_dict):
    """Score a package dict.

    Returns ``{'score', 'category', 'points', 'max_points', 'missing',
    'languages'}`` or ``None`` for unsupported package types.
    """
    pkg_type = pkg_dict.get('type') or 'dataset'
    weights = _WEIGHTS_BY_TYPE.get(pkg_type)
    if weights is None:
        return None

    points = 0
    max_points = 0
    missing = []
    for spec in weights:
        earned = _check_points(pkg_dict, spec)
        points += earned
        max_points += spec['weight']
        if earned < spec['weight']:
            missing.append(spec['field'])

    score = (100.0 * points / max_points) if max_points else 0.0

    # Fluent bonus: each of title/notes translated into a second language
    # (besides the required 'en') adds a few points, capped at 100.
    covered = None
    for field in FLUENT_BONUS_FIELDS:
        langs = _fluent_langs(pkg_dict, field)
        covered = set(langs) if covered is None else covered & set(langs)
        if len([l for l in langs if l != 'en']) >= 1 and len(langs) >= 2:
            score += FLUENT_BONUS_POINTS
    score = round(min(score, 100.0), 1)

    return {
        'score': score,
        'category': get_category(score),
        'points': points,
        'max_points': max_points,
        'missing': missing,
        'languages': sorted(covered or [],
                            key=lambda l: FLUENT_LANGS.index(l)),
    }


def inject(pkg_dict):
    """Attach ``metadata_completeness`` to a package dict in place."""
    if 'metadata_completeness' in pkg_dict:
        return pkg_dict
    if (pkg_dict.get('type') or 'dataset') not in SUPPORTED_TYPES:
        return pkg_dict
    result = calculate_completeness(pkg_dict)
    if result is not None:
        pkg_dict['metadata_completeness'] = result
    return pkg_dict


def for_index(dataset_dict):
    """Compute (score, category) for ``before_dataset_index``.

    The index dict flattens resources and may serialize fluent fields,
    so when the full validated package is available it is preferred.
    """
    pkg_dict = dataset_dict
    validated = dataset_dict.get('validated_data_dict')
    if validated:
        try:
            pkg_dict = json.loads(validated)
        except ValueError:
            pkg_dict = dataset_dict
    result = calculate_completeness(pkg_dict)
    if result is None:
        return None, None
    return result['score'], result['category']


def sort_value(score):
    """Clave de orden para Solr: el campo dinamico se indexa como string,
    asi que se rellena con ceros ('009.5' < '085.3' < '100.0') para que el
    orden lexicografico coincida con el numerico."""
    if score is None:
        return None
    return '%05.1f' % float(score)


def get_completeness(pkg_dict):
    """Template helper: injected value or on-the-fly calculation."""
    if not isinstance(pkg_dict, dict):
        return None
    existing = pkg_dict.get('metadata_completeness')
    if isinstance(existing, dict):
        return existing
    return calculate_completeness(pkg_dict)
