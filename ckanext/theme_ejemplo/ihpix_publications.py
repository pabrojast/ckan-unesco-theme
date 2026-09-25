# -*- coding: utf-8 -*-
u"""Creación inline de publicaciones (datasets `documents`) desde IHP-IX.

Módulo **puro** (sin CKAN) con las reglas del modal "Upload a publication"
que se abre en el reporte, en los workspaces y en las páginas por Output:

- `validate_publication_input(form)` → dict limpio o `PublicationValidationError`
- `build_package_dict(clean, schema_field_names, defaults)` → payload de
  `package_create` filtrado por los campos que **existen** en el esquema
  `documents` instalado (la rama `production` del fork schemingdcat tiene
  13 campos; `dev210` tiene 29).
- `build_resource_dict(clean, resource_field_names)` → payload de
  `resource_create` (fichero subido o URL).
- `map_schema_errors(error_dict)` → errores del esquema traducidos a los
  nombres de campo del modal.
- `link_item_for_package(pkg)` → item listo para `ihpixLinks.add()` /
  `ihpix_activity_link_create`.

Nunca crea nada por sí mismo: la acción `ihpix_publication_create`
(actions.py) llama a las acciones core de CKAN con estos payloads.
"""
from __future__ import unicode_literals

import json
import re
import unicodedata
import uuid
from collections import OrderedDict

DATASET_TYPE = 'documents'

TITLE_MAX = 300
ABSTRACT_MAX = 2000
AUTHORS_MAX = 50
KEYWORDS_MAX = 20
KEYWORD_MAX_LEN = 100

# Valores del esquema `documents` (dev210). Si el esquema instalado no tiene
# `document_type`, el campo se omite del payload.
DOCUMENT_TYPES = (
    'scientific_paper', 'technical_report', 'policy_brief',
    'dataset_documentation', 'book', 'book_chapter', 'conference_paper',
    'thesis', 'preprint', 'working_paper', 'manual', 'educational_material',
    'other',
)
DEFAULT_DOCUMENT_TYPE = 'other'
EDUCATIONAL_DOCUMENT_TYPE = 'educational_material'

DEFAULT_LANGUAGE = 'http://publications.europa.eu/resource/authority/language/ENG'
DEFAULT_LICENSE = 'cc-by-sa'
DEFAULT_ACCESS_LEVEL = 'public'
DEFAULT_TAGS = ('ihp-ix',)
OUTPUT_TAG_TEMPLATE = 'ihp-ix-output-{code}'
DEFAULT_ABSTRACT = 'Publication reported under IHP-IX.'

SOURCE_FILE = 'file'
SOURCE_URL = 'url'
SOURCE_KINDS = (SOURCE_FILE, SOURCE_URL)

# Extensiones admitidas en la subida (el servidor también limita el tamaño)
ALLOWED_EXTENSIONS = ('pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
                      'odt', 'odp', 'ods', 'zip', 'csv', 'txt', 'md', 'epub')

DOI_RE = re.compile(r'^10\.\d{4,9}/\S+$', re.I)
URL_RE = re.compile(r'^https?://\S+$', re.I)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
YEAR_MIN, YEAR_MAX = 1900, 2100

MESSAGES = OrderedDict([
    ('title_required', 'Title is required'),
    ('max_length', '{field} must be {max} characters or fewer'),
    ('organization_required', 'Choose the organization that will own the publication'),
    ('organization_not_allowed', 'You cannot create publications in this organization'),
    ('document_type_invalid', 'Invalid document type'),
    ('year_invalid', 'Publication year must be between {min} and {max}'),
    ('doi_invalid', 'Enter a valid DOI (e.g. 10.1000/xyz123)'),
    ('source_required', 'Upload a file or enter the URL of the publication'),
    ('source_url_invalid', 'The URL must start with http:// or https://'),
    ('file_extension_invalid', 'This file type is not allowed ({ext})'),
    ('file_too_large', 'The file is too large (max. {max} MB)'),
    ('email_invalid', 'Invalid email address'),
    ('too_many_authors', 'At most {max} authors'),
    ('too_many_keywords', 'At most {max} keywords'),
])


class PublicationValidationError(Exception):
    u"""`.errors` {campo: mensaje} y `.details` {campo: (clave, params)}."""

    def __init__(self, errors, details=None):
        self.errors = dict(errors)
        self.details = dict(details or {})
        super(PublicationValidationError, self).__init__(
            json.dumps(self.errors, sort_keys=True))


def _text(d, key):
    val = d.get(key)
    if val is None:
        return ''
    if isinstance(val, (list, tuple)):
        val = val[0] if val else ''
    return str(val).strip()


def parse_authors(raw):
    u"""'Nombre; Afiliación' por línea (o separados por comas si es una sola
    línea) → [{'name': ..., 'affiliation': ...}]. Sin duplicados."""
    if not raw:
        return []
    text = str(raw).strip()
    if not text:
        return []
    lines = [l for l in re.split(r'[\r\n]+', text) if l.strip()]
    if len(lines) == 1 and ';' not in lines[0] and ',' in lines[0]:
        lines = [p for p in lines[0].split(',') if p.strip()]
    authors = []
    seen = set()
    for line in lines:
        parts = [p.strip() for p in line.split(';')]
        name = parts[0]
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        author = {'name': name}
        if len(parts) > 1 and parts[1]:
            author['affiliation'] = parts[1]
        authors.append(author)
    return authors


def parse_keywords(raw):
    u"""'a, b; c' o lista → lista de palabras clave limpias y únicas."""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        items = list(raw)
    else:
        items = re.split(r'[,;\n]+', str(raw))
    out = []
    seen = set()
    for item in items:
        kw = re.sub(r'\s+', ' ', str(item)).strip().strip('#')
        if not kw:
            continue
        kw = kw[:KEYWORD_MAX_LEN]
        if kw.lower() in seen:
            continue
        seen.add(kw.lower())
        out.append(kw)
    return out


def default_tags(output_code='', extra=()):
    u"""Tags que siempre lleva una publicación creada desde IHP-IX."""
    tags = list(DEFAULT_TAGS)
    code = (output_code or '').strip()
    if code:
        tags.append(OUTPUT_TAG_TEMPLATE.format(code=code))
    for t in extra or ():
        if t and t not in tags:
            tags.append(t)
    return tags


def slugify_title(title, taken=(), max_len=90):
    u"""`name` de CKAN a partir del título (minúsculas, guiones, ASCII).
    Si ya está en `taken`, añade -2, -3… """
    norm = unicodedata.normalize('NFKD', str(title or ''))
    ascii_text = ''.join(ch for ch in norm if not unicodedata.combining(ch))
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_text.lower()).strip('-')
    slug = re.sub(r'-{2,}', '-', slug)[:max_len].strip('-')
    if len(slug) < 2:
        slug = 'publication-' + uuid.uuid4().hex[:8]
    taken = set(taken or ())
    candidate = slug
    n = 2
    while candidate in taken:
        suffix = '-{}'.format(n)
        candidate = slug[:max_len - len(suffix)].rstrip('-') + suffix
        n += 1
    return candidate


def file_extension(filename):
    name = (filename or '').rsplit('/', 1)[-1]
    return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


def format_for(filename_or_url):
    u"""Formato del recurso a partir de la extensión (PDF, DOCX…)."""
    ext = file_extension((filename_or_url or '').split('?')[0])
    return ext.upper() if ext and ext in ALLOWED_EXTENSIONS else ('HTML' if not ext else ext.upper())


def validate_publication_input(form, allowed_org_ids=None, max_upload_mb=None,
                               upload_filename='', upload_size=None):
    u"""Valida el formulario del modal.

    `form` es un dict plano (request.form). `allowed_org_ids` = orgs donde
    el usuario puede crear datasets (None = no comprobar aquí).
    `upload_filename`/`upload_size` describen el fichero subido, si lo hay.
    Devuelve el dict limpio que consumen `build_package_dict` y
    `build_resource_dict`.
    """
    errors = OrderedDict()
    details = OrderedDict()

    def add(field, key, **params):
        if field in errors:
            return
        errors[field] = MESSAGES[key].format(**params)
        details[field] = (key, params)

    title = _text(form, 'title')
    if not title:
        add('title', 'title_required')
    elif len(title) > TITLE_MAX:
        add('title', 'max_length', field='Title', max=TITLE_MAX)

    organization = _text(form, 'organization') or _text(form, 'owner_org')
    if not organization:
        add('organization', 'organization_required')
    elif allowed_org_ids is not None and organization not in set(allowed_org_ids):
        add('organization', 'organization_not_allowed')

    document_type = _text(form, 'document_type') or DEFAULT_DOCUMENT_TYPE
    if document_type not in DOCUMENT_TYPES:
        add('document_type', 'document_type_invalid')

    year = None
    raw_year = _text(form, 'publication_year')
    if raw_year:
        try:
            year = int(raw_year)
            if year < YEAR_MIN or year > YEAR_MAX:
                raise ValueError()
        except ValueError:
            year = None
            add('publication_year', 'year_invalid', min=YEAR_MIN, max=YEAR_MAX)

    doi = _text(form, 'doi') or _text(form, 'document_doi')
    if doi:
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi, flags=re.I).strip()
        if not DOI_RE.match(doi):
            add('doi', 'doi_invalid')

    abstract = _text(form, 'abstract') or _text(form, 'notes')
    if len(abstract) > ABSTRACT_MAX:
        add('abstract', 'max_length', field='Abstract', max=ABSTRACT_MAX)

    authors = parse_authors(form.get('authors'))
    if len(authors) > AUTHORS_MAX:
        add('authors', 'too_many_authors', max=AUTHORS_MAX)

    keywords = parse_keywords(form.get('keywords') or form.get('tag_string'))
    if len(keywords) > KEYWORDS_MAX:
        add('keywords', 'too_many_keywords', max=KEYWORDS_MAX)

    contact_email = _text(form, 'contact_email')
    if contact_email and not EMAIL_RE.match(contact_email):
        add('contact_email', 'email_invalid')

    source_kind = (_text(form, 'source_kind') or '').lower()
    source_url = _text(form, 'source_url') or _text(form, 'url')
    has_file = bool(upload_filename)
    if not source_kind:
        source_kind = SOURCE_FILE if has_file else (SOURCE_URL if source_url else '')
    if source_kind == SOURCE_FILE:
        if not has_file:
            add('source', 'source_required')
        else:
            ext = file_extension(upload_filename)
            if ext not in ALLOWED_EXTENSIONS:
                add('source', 'file_extension_invalid', ext=ext or '?')
            if max_upload_mb and upload_size is not None \
                    and upload_size > max_upload_mb * 1024 * 1024:
                add('source', 'file_too_large', max=max_upload_mb)
    elif source_kind == SOURCE_URL:
        if not source_url:
            add('source', 'source_required')
        elif not URL_RE.match(source_url):
            add('source', 'source_url_invalid')
    else:
        add('source', 'source_required')

    if errors:
        raise PublicationValidationError(errors, details)

    return {
        'title': title,
        'organization': organization,
        'document_type': document_type,
        'publication_year': year,
        'doi': doi,
        'abstract': abstract,
        'authors': authors,
        'keywords': keywords,
        'contact_email': contact_email,
        'language': _text(form, 'language'),
        'license_id': _text(form, 'license_id'),
        'member_state': _text(form, 'member_state') or _text(form, 'groups__0__id'),
        'initiative': _text(form, 'initiative') or _text(form, 'groups__1__id'),
        'source_kind': source_kind,
        'source_url': source_url if source_kind == SOURCE_URL else '',
        'upload_filename': upload_filename if source_kind == SOURCE_FILE else '',
        'output_code': _text(form, 'output_code'),
        'activity_id': _text(form, 'activity_id'),
    }


def build_package_dict(clean, schema_field_names, defaults=None, name=None,
                       identifier=None):
    u"""Payload de `package_create` para el esquema `documents`.

    Sólo incluye las claves presentes en `schema_field_names` (más `name`,
    `type`, `owner_org`, `private`, `tags`/`groups`, que son core). Así el
    mismo código sirve para el esquema de 13 campos de producción y el de
    29 de dev210.
    """
    defaults = defaults or {}
    fields = set(schema_field_names or ())
    language = clean.get('language') or defaults.get('language') or DEFAULT_LANGUAGE
    license_id = clean.get('license_id') or defaults.get('license_id') or DEFAULT_LICENSE
    contact_email = clean.get('contact_email') or defaults.get('contact_email') or ''
    contact_name = defaults.get('contact_name') or ''
    abstract = clean.get('abstract') or DEFAULT_ABSTRACT
    tags = default_tags(clean.get('output_code'), defaults.get('tags') or ())
    for kw in clean.get('keywords') or []:
        if kw not in tags:
            tags.append(kw)

    pkg = OrderedDict()
    pkg['type'] = DATASET_TYPE
    pkg['name'] = name or slugify_title(clean['title'])
    pkg['owner_org'] = clean['organization']
    pkg['private'] = False
    pkg['title'] = clean['title']
    pkg['notes'] = abstract
    pkg['tags'] = [{'name': t} for t in tags]

    candidates = OrderedDict([
        ('title_translated', {'en': clean['title']}),
        ('notes_translated', {'en': abstract}),
        ('document_type', clean.get('document_type') or DEFAULT_DOCUMENT_TYPE),
        ('publication_year', clean.get('publication_year')),
        ('authors_json', json.dumps(clean.get('authors') or [], ensure_ascii=False)
            if clean.get('authors') else None),
        ('document_doi', clean.get('doi') or None),
        ('access_level', defaults.get('access_level') or DEFAULT_ACCESS_LEVEL),
        ('language', language),
        ('license_id', license_id),
        ('identifier', identifier or str(uuid.uuid4())),
        ('contact_email', contact_email),
        ('contact_name', contact_name or None),
        ('tag_string', ', '.join(tags)),
        ('dataset_scope', defaults.get('dataset_scope') or None),
    ])
    for key, value in candidates.items():
        if key in fields and value not in (None, ''):
            pkg[key] = value
    if 'license_id' not in pkg:
        pkg['license_id'] = license_id  # core: siempre válido

    groups = []
    for key, group_name in (('groups__0__id', clean.get('member_state')),
                            ('groups__1__id', clean.get('initiative'))):
        if group_name:
            groups.append({'name': group_name})
    if groups:
        pkg['groups'] = groups
    return pkg


def build_resource_dict(clean, resource_field_names=None, package_id=None):
    u"""Payload de `resource_create`. Con fichero, la acción añade `upload`
    (FileStorage) después; aquí sólo van los metadatos."""
    fields = set(resource_field_names or ())
    res = OrderedDict()
    if package_id:
        res['package_id'] = package_id
    res['name'] = clean['title'][:TITLE_MAX]
    if clean.get('source_kind') == SOURCE_URL:
        res['url'] = clean['source_url']
        res['format'] = format_for(clean['source_url'])
    else:
        res['url'] = clean.get('upload_filename') or ''
        res['url_type'] = 'upload'
        res['format'] = format_for(clean.get('upload_filename'))
    if 'description' in fields and clean.get('abstract'):
        res['description'] = clean['abstract'][:500]
    return res


# Campos del esquema → campo del modal (para pintar el error en su sitio)
SCHEMA_TO_FORM_FIELD = OrderedDict([
    ('title_translated', 'title'),
    ('title', 'title'),
    ('title_translated-en', 'title'),
    ('name', 'title'),
    ('notes_translated', 'abstract'),
    ('notes', 'abstract'),
    ('owner_org', 'organization'),
    ('document_type', 'document_type'),
    ('publication_year', 'publication_year'),
    ('document_doi', 'doi'),
    ('authors_json', 'authors'),
    ('tag_string', 'keywords'),
    ('tags', 'keywords'),
    ('groups', 'member_state'),
    ('groups__0__id', 'member_state'),
    ('groups__1__id', 'initiative'),
    ('contact_email', 'contact_email'),
    ('language', 'language'),
    ('resources', 'source'),
    ('upload', 'source'),
    ('url', 'source'),
])


def map_schema_errors(error_dict):
    u"""`ValidationError.error_dict` de CKAN → {campo del modal: mensaje}.
    Lo que no tenga correspondencia va a `__all__`."""
    out = OrderedDict()
    for key, msgs in (error_dict or {}).items():
        if isinstance(msgs, dict):
            # errores anidados (p. ej. fluent: {'en': [...]})
            msgs = [m for v in msgs.values() for m in (v if isinstance(v, list) else [v])]
        if not isinstance(msgs, (list, tuple)):
            msgs = [msgs]
        text = '; '.join(str(m) for m in msgs if m)
        if not text:
            continue
        field = SCHEMA_TO_FORM_FIELD.get(key)
        if field is None and isinstance(key, str) and key.startswith('resources'):
            field = 'source'
        if field is None:
            field = '__all__'
            text = '{}: {}'.format(key, text)
        if field in out:
            out[field] = out[field] + '; ' + text
        else:
            out[field] = text
    return out


def link_item_for_package(pkg, link_type='publication'):
    u"""Adjunto listo para la Sección VII / `ihpix_activity_link_create`."""
    name = pkg.get('name') or pkg.get('id')
    org = pkg.get('organization') or {}
    year = pkg.get('publication_year')
    return {
        'link_type': link_type,
        'target_kind': 'package',
        'target_id': pkg.get('id'),
        'title': pkg.get('title') or name,
        'url': '/documents/' + name if link_type == 'publication' else '/dataset/' + name,
        'event_date': '',
        'description': ' · '.join([p for p in (
            org.get('title', '') if isinstance(org, dict) else '',
            str(year) if year else '') if p]),
    }


def prefilled_dataset_url(owner_org='', title='', output_code='', member_state=''):
    u"""Query string para `/dataset/new` prellenado (CreateView de CKAN 2.10
    lee `request.args`). Devuelve sólo la parte `?a=b&c=d`."""
    try:
        from urllib.parse import urlencode
    except ImportError:  # pragma: no cover (py2)
        from urllib import urlencode
    params = OrderedDict()
    if owner_org:
        params['owner_org'] = owner_org
    if title:
        params['title'] = title
    params['tag_string'] = ','.join(default_tags(output_code))
    if member_state:
        params['groups__0__id'] = member_state
    return '?' + urlencode(params)
