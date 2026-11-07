"""Creación inline de datasets y eventos usando las acciones nativas del portal."""
import datetime
import html
import os
import uuid

from . import ihpix_publications as P

DATA_EXTENSIONS = ('csv', 'tsv', 'xls', 'xlsx', 'ods', 'json', 'geojson', 'jsonl',
                   'xml', 'txt', 'zip', 'gz', 'nc', 'netcdf', 'hdf', 'h5', 'tif',
                   'tiff', 'geotiff', 'gpkg', 'shp', 'kml', 'kmz', 'parquet', 'pdf')
AGENDA_EXTENSIONS = ('pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp')


class InputError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


def validate(data, allowed_orgs, filename='', size=0, max_mb=50):
    """Valida antes de crear contenido o subir ficheros."""
    clean = {key: str(data.get(key) or '').strip() for key in (
        'kind', 'title', 'organization', 'description', 'contact_email', 'license_id',
        'visibility', 'source_kind', 'source_url', 'start_date', 'end_date',
        'location', 'event_format', 'registration_url', 'output_code', 'request_id',
        'dcat_type', 'topic')}
    errors = {}
    if clean['kind'] not in ('dataset', 'event'):
        errors['kind'] = 'Choose dataset or event'
    for key in ('title', 'organization', 'description'):
        if not clean[key]:
            errors[key] = 'This field is required'
    for key, limit in (('title', 300), ('description', 5000), ('location', 300)):
        if len(clean[key]) > limit:
            errors[key] = 'This answer is too long'
    if clean['organization'] and clean['organization'] not in allowed_orgs:
        errors['organization'] = 'You cannot create content in this organization'
    try:
        clean['request_id'] = str(uuid.UUID(clean['request_id']))
    except (ValueError, TypeError):
        errors['request_id'] = 'Invalid request identifier'
    kind = clean['kind']
    source = clean['source_kind']
    if source == 'none' and kind == 'event':
        pass
    elif source == 'file':
        extensions = DATA_EXTENSIONS if kind == 'dataset' else AGENDA_EXTENSIONS
        if not filename:
            errors['source'] = 'Choose a file to upload'
        elif P.file_extension(filename) not in extensions:
            errors['source'] = 'This file type is not allowed'
        limit = min(max_mb, 20) if kind == 'event' else max_mb
        if size > limit * 1024 * 1024:
            errors['source'] = 'The file exceeds the upload limit'
    elif source == 'url':
        if not P.URL_RE.match(clean['source_url']):
            errors['source'] = 'The URL must start with http:// or https://'
    else:
        errors['source'] = 'Choose a file or a URL'
    if kind == 'dataset':
        if not P.EMAIL_RE.match(clean['contact_email']):
            errors['contact_email'] = 'Invalid email address'
        if clean['visibility'] not in ('private', 'public'):
            errors['visibility'] = 'Choose the dataset visibility'
        if not clean['license_id']:
            errors['license_id'] = 'Choose a license'
        for field in ('dcat_type', 'topic'):
            if not clean[field]:
                errors[field] = 'This field is required'
    if kind == 'event':
        for field in ('start_date', 'end_date'):
            value = clean[field]
            if field == 'start_date' and not value:
                errors[field] = 'This field is required'
            elif value:
                try:
                    clean[field] = datetime.datetime.strptime(value, '%Y-%m-%d').date().isoformat()
                except ValueError:
                    errors[field] = 'Enter a valid date'
        if not any(key in errors for key in ('start_date', 'end_date')) and clean['end_date'] and clean['end_date'] < clean['start_date']:
            errors['end_date'] = 'End date must not be before start date'
        if clean['event_format'] not in ('in-person', 'online', 'hybrid'):
            errors['event_format'] = 'Choose the event format'
        if clean['registration_url'] and not P.URL_RE.match(clean['registration_url']):
            errors['registration_url'] = 'The URL must start with http:// or https://'
    if errors:
        raise InputError(errors)
    clean['upload_filename'] = os.path.basename(filename)
    return clean


def content_identity(user_id, kind, request_id):
    identity = uuid.uuid5(uuid.NAMESPACE_URL, 'ihpix-resource:{}:{}:{}'.format(user_id, kind, request_id))
    return str(identity), identity.int & ((1 << 63) - 1)


def event_payload(clean, org_title, name):
    # Texto sin HTML ejecutable; la agenda y el registro conservan sus campos nativos.
    content = '<p>' + html.escape(clean['description']).replace('\n', '<br>') + '</p>'
    return dict(name=name, title=clean['title'], content=content, page_type='water-events',
                private=True, submission_action='submit', ihp_organization=clean['organization'],
                organization=org_title, publish_date=clean['start_date'],
                event_end_date=clean['end_date'] or clean['start_date'],
                event_format=clean['event_format'], location=clean['location'],
                registration_url=clean['registration_url'])


def create(context, data_dict):
    import ckan.model as model
    import ckan.plugins.toolkit as tk
    from sqlalchemy import text
    from . import actions as A

    tk.check_access('ihpix_resource_create', context, data_dict)
    user = A._ihpix_user_obj(context)
    if not user or user.state != 'active':
        raise tk.NotAuthorized(tk._('You must be logged in'))
    kind = data_dict.get('kind')
    permission = 'create_dataset' if kind == 'dataset' else 'read'
    orgs = tk.get_action('organization_list_for_user')(
        {'user': user.name, 'auth_user_obj': user}, {'permission': permission})
    allowed = {org['id']: org for org in orgs}
    upload = data_dict.get('upload')
    filename = getattr(upload, 'filename', '') if upload is not None else ''
    size = 0
    if filename:
        stream = upload.stream
        position = stream.tell(); stream.seek(0, 2); size = stream.tell(); stream.seek(position)
    try:
        clean = validate(data_dict, allowed, filename, size, A._ihpix_config_int('ihpix_upload_max_mb', 50))
    except InputError as exc:
        raise tk.ValidationError({key: tk._(message) for key, message in exc.errors.items()})
    ctx = {'user': user.name, 'auth_user_obj': user, 'model': model, 'session': model.Session}
    identity, lock_id = content_identity(user.id, kind, clean['request_id'])
    name = 'ihpix-' + identity
    # Las acciones nativas hacen commit: el lock usa otra conexión y cubre también la subida.
    with model.meta.engine.connect() as connection:
        connection.execute(text('SELECT pg_advisory_lock(:key)'), {'key': lock_id})
        try:
            if kind == 'dataset':
                return _dataset(ctx, clean, upload, identity, name)
            return _event(ctx, clean, upload, allowed[clean['organization']], name)
        finally:
            connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': lock_id})


def _dataset(context, clean, upload, identity, name):
    import ckan.model as model
    import ckan.plugins.toolkit as tk
    package = model.Package.get(name)
    if package and package.creator_user_id != context['auth_user_obj'].id:
        raise tk.NotAuthorized(tk._('Not authorized'))
    if package:
        tk.check_access('package_update', context, {'id': package.id})
        if package.state == 'active' and package.resources:
            return _dataset_result(tk.get_action('package_show')(dict(context), {'id': package.id}))
    schema = tk.get_action('scheming_dataset_schema_show')(dict(context), {'type': 'dataset'})
    for field in schema['dataset_fields']:
        key = field['field_name']
        if key in ('dcat_type', 'topic') and clean[key] not in {choice['value'] for choice in field['choices']}:
            raise tk.ValidationError({key: tk._('Please select a valid option')})
    fields = [field['field_name'] for field in schema['dataset_fields']]
    values = dict(clean, abstract=clean['description'])
    payload = P.build_package_dict(values, fields, defaults={
        'contact_name': context['auth_user_obj'].display_name,
        'access_level': 'confidential' if clean['visibility'] == 'private' else 'public',
    }, name=name, identifier=identity)
    payload.update(type='dataset', private=clean['visibility'] != 'public',
                   dcat_type=clean['dcat_type'], topic=clean['topic'])
    try:
        if package:
            payload['id'] = package.id
            payload['state'] = 'active'
            pkg = tk.get_action('package_update')(dict(context), payload)
        else:
            pkg = tk.get_action('package_create')(dict(context), payload)
    except tk.ValidationError as exc:
        errors = P.map_schema_errors(exc.error_dict)
        if 'abstract' in errors:
            errors['description'] = errors.pop('abstract')
        raise tk.ValidationError(errors)
    resource = P.build_resource_dict(values, ['description'], pkg['id'])
    if clean['source_kind'] == 'file':
        resource['upload'] = upload
    try:
        tk.get_action('resource_create')(dict(context), resource)
    except Exception:
        model.Session.rollback()
        # No dejar un dataset público vacío si falla la subida; el siguiente intento reutiliza su ID.
        tk.get_action('package_delete')(dict(context), {'id': pkg['id']})
        raise tk.ValidationError({'source': tk._('The file could not be uploaded. Please try again.')})
    return _dataset_result(tk.get_action('package_show')(dict(context), {'id': pkg['id']}))


def _dataset_result(pkg):
    import ckan.plugins.toolkit as tk
    return {'link': {'link_type': 'dataset', 'target_kind': 'package', 'target_id': pkg['id'],
                     'title': pkg['title'], 'url': tk.url_for('dataset.read', id=pkg['name'], qualified=True)}}


def _event(context, clean, upload, org, name):
    import ckan.model as model
    import ckan.plugins.toolkit as tk
    from ckanext.pages.db import Page
    page = model.Session.query(Page).filter_by(name=name).first()
    if page and (page.user_id != context['auth_user_obj'].id or page.page_type != 'water-events'):
        raise tk.NotAuthorized(tk._('Not authorized'))
    if not page:
        payload = event_payload(clean, org.get('title') or org['name'], name)
        tk.check_access('ckanext_pages_update', context, {'page_type': 'water-events'})
        if clean['source_kind'] == 'file':
            result = tk.get_action('ckanext_water_family_upload')(dict(context), {
                'upload': upload, 'water_content_type': 'water-events', 'file_type': 'document',
                'asset_role': 'agenda_document'})
            if not result.get('uploaded') or not result.get('url'):
                raise tk.ValidationError({'source': tk._('The file could not be uploaded. Please try again.')})
            payload['agenda_document'] = result['url']
        elif clean['source_kind'] == 'url':
            payload['agenda_document'] = clean['source_url']
        tk.get_action('ckanext_pages_update')(dict(context), payload)
        page = model.Session.query(Page).filter_by(name=name).one()
    return {'link': {'link_type': 'event', 'target_kind': 'page', 'target_id': page.name,
                     'title': page.title, 'event_date': str(page.publish_date.date()) if page.publish_date else '',
                     'url': tk.url_for('pages.water_events_show', page=page.name, qualified=True)}}
