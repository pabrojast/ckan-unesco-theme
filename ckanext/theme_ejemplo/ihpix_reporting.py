# -*- coding: utf-8 -*-
"""Informes verificables e importaciones transaccionales de borradores."""
import base64
import hashlib
import json

from sqlalchemy import select, text
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.theme_ejemplo import (ihpix_bulk as B, ihpix_store as S,
    ihpix_service as V, ihpix_relations as R, ihpix_constants as C)
from ckanext.theme_ejemplo.ihpix_collaboration import user
from ckanext.theme_ejemplo.model import IhpixActivity


def defaults_for(actor):
    values = {'focal_point_name': actor.fullname or actor.name,
              'contact_email': actor.email or ''}
    organizations = tk.get_action('organization_list_for_user')(
        {'user': actor.name}, {'id': actor.id, 'permission': 'read'})
    if len(organizations) == 1:
        values['institution_org_id'] = organizations[0]['id']
        values['institution'] = organizations[0].get('title') or organizations[0]['name']
    return values


def ihpix_import_preview(context, data):
    actor = user(context)
    try:
        encoded = tk.get_or_bust(data, 'workbook')
        if len(encoded) > 7 * 1024 * 1024:
            raise ValueError('Workbook exceeds 5 MB')
        raw = base64.b64decode(encoded, validate=True)
        preview = B.parse(raw, defaults_for(actor))
    except (ValueError, TypeError) as exc:
        raise tk.ValidationError({'workbook': str(exc)})
    digest = hashlib.sha256(raw).hexdigest()
    # El bloqueo transaccional evita previews duplicados incluso antes del INSERT.
    model.Session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),
                          {'key': actor.id + digest})
    existing = model.Session.execute(select(S.imports).where(
        S.imports.c.user_id == actor.id, S.imports.c.digest == digest)).first()
    if existing:
        result = {'id': existing.id, 'status': existing.status,
                'preview': json.loads(existing.payload), 'created': json.loads(existing.result)}
        model.Session.commit()
        return result
    for item in preview['rows']:
        org = model.Group.get(item['data'].get('institution_org_id')) if item['data'].get('institution_org_id') else None
        if org and org.is_organization and org.state == 'active' and not item['data'].get('institution'):
            item['data']['institution'] = org.display_name
            preview['warnings'] = [warning for warning in preview['warnings'] if not (
                warning['sheet'] == 'Activities' and warning['row'] == item['row']
                and warning['field'] == 'institution')]
        from ckanext.theme_ejemplo.ihpix_resource_access import visible
        for link, number in zip(item['data'].get('links_json', []), item['resource_rows']):
            if not visible(link, actor):
                preview['errors'].append({'sheet': 'Resources', 'row': number,
                    'cell': 'D' + str(number), 'field': 'target_id',
                    'message': 'Choose an existing resource you can access'})
        from openpyxl.utils import get_column_letter
        org_cells = [(item['data'].get('institution_org_id'), 'Activities', item['row'],
                      'institution_org_id', get_column_letter(B.FIELDS.index('institution_org_id') + 1))]
        org_cells += [(org_id, 'Partners', number, 'organization_id', 'B') for org_id, number in
                      zip(item['data'].get('partner_org_ids', []), item['partner_rows'])]
        for org_id, sheet, number, field, column in org_cells:
            if not org_id:
                continue
            org = model.Group.get(org_id)
            if not org or not org.is_organization or org.state != 'active' or org.id != org_id:
                preview['errors'].append({'sheet': sheet, 'row': number,
                    'cell': column + str(number), 'field': field,
                    'message': 'Select an active IHP-WINS organization'})
    batch_id = S.uid()
    model.Session.execute(S.imports.insert().values(id=batch_id, user_id=actor.id,
        digest=digest, payload=json.dumps(preview), result='[]', status='preview', created_at=S.now()))
    model.Session.commit()
    return {'id': batch_id, 'status': 'preview', 'preview': preview, 'created': []}


@tk.side_effect_free
def ihpix_import_show(context, data):
    actor = user(context)
    batch = model.Session.execute(select(S.imports).where(S.imports.c.id == data.get('id'),
                                  S.imports.c.user_id == actor.id)).first()
    if not batch:
        raise tk.ObjectNotFound('Import preview not found')
    return {'id': batch.id, 'status': batch.status,
            'preview': json.loads(batch.payload), 'created': json.loads(batch.result)}


def ihpix_import_create(context, data):
    actor = user(context)
    if not tk.asbool(data.get('confirm', False)):
        raise tk.ValidationError({'confirm': 'Confirm the reviewed import preview'})
    batch = model.Session.execute(select(S.imports).where(S.imports.c.id == data.get('id'),
        S.imports.c.user_id == actor.id).with_for_update()).first()
    if not batch:
        raise tk.ObjectNotFound('Import preview not found')
    if batch.status == 'created':
        result = {'created': json.loads(batch.result), 'repeated': True}
        model.Session.commit()
        return result
    payload = json.loads(batch.payload)
    if payload['errors']:
        raise tk.ValidationError({'workbook': 'Correct all invalid values before importing'})
    result = []
    try:
        for item in payload['rows']:
            data = dict(item['data'], save_as_draft='1')
            activity = V.save(context, data)
            result.append({'ref': item['ref'], 'id': activity.id, 'title': activity.title})
        model.Session.execute(S.imports.update().where(S.imports.c.id == batch.id)
                              .values(status='created', result=json.dumps(result)))
        model.Session.commit()
    except Exception:
        model.Session.rollback()
        raise
    return {'created': result, 'repeated': False}


@tk.side_effect_free
def ihpix_narrative_data(context, data):
    user(context)
    scope = data.get('scope', 'pa')
    value = str(data.get('value') or '').strip()
    biennium = str(data.get('biennium') or '').strip()
    if biennium and biennium not in C.BIENNIA:
        raise tk.ValidationError({'biennium': 'Select a reporting biennium'})
    geography = {key: str(data.get(key) or '').strip() for key in ('country', 'region')}
    filters = dict(status='published', biennium=biennium, limit=None, **geography)
    from ckanext.theme_ejemplo.actions import _ihpix_resolve_scope_value
    if scope == 'overall':
        value = ''
        title = tk._('Overall implementation progress')
    elif scope in ('flagship', 'ctwg'):
        value = _ihpix_resolve_scope_value(scope, value)
        if value is None:
            raise tk.ValidationError({'value': tk._('Choose a valid reporting scope')})
        filters[scope] = value
        title = C.flagship_label(value) if scope == 'flagship' else value
    elif scope == 'pa' and value in C.PRIORITY_AREAS:
        filters['priority_area'] = value
        title = value + ' · ' + C.PRIORITY_AREAS[value]
    elif scope == 'output' and value in C.all_output_codes():
        filters['output'] = value
        title = C.output_label(value)
    elif scope == 'organization':
        org = model.Group.get(value)
        if not org or not org.is_organization or org.state != 'active':
            raise tk.ObjectNotFound('Organization not found')
        filters['organization'] = org.id
        title = org.display_name
    else:
        raise tk.ValidationError({'scope': 'Choose an organization, Priority Area or Output'})
    rows, total = IhpixActivity.get_filtered(**filters)
    from ckanext.theme_ejemplo.ihpix_stats import compute_progress_stats, prepare_row, filter_rows
    from ckanext.theme_ejemplo.actions import _ihpix_country_index
    index = _ihpix_country_index()
    stat_scope = scope if scope != 'organization' else 'overall'
    stat_filters = dict(geography, biennium=biennium)
    # Una sola selección para indicadores y fuentes; evita coincidencias parciales de SQL.
    selected = filter_rows([prepare_row(a.as_dict(), index) for a in rows],
                          stat_scope, value, stat_filters, index)
    selected_ids = {a['id'] for a in selected}
    rows = [a for a in rows if a.id in selected_ids]
    stats = compute_progress_stats([a.as_dict() for a in rows], scope=stat_scope,
        value=value, filters=stat_filters, country_index=index)
    return {'title': title, 'scope': scope, 'value': value, 'biennium': biennium,
            'filters': stat_filters,
            'generated_at': stats['generated_at'], 'stats': stats,
            'sources': [{'id': a.id, 'title': a.title, 'description': a.description,
                         'outcomes': a.outcomes, 'institution': a.institution,
                         'outputs': R.dimension_values(a.as_dict(), 'output')} for a in rows],
            'unlinked_legacy': (model.Session.query(IhpixActivity).filter(
                IhpixActivity.status == 'published',
                (IhpixActivity.institution_org_id == '') | IhpixActivity.institution_org_id.is_(None)).count()
                if scope == 'organization' else 0)}


ACTIONS = {name: value for name, value in list(globals().items()) if name.startswith('ihpix_') and callable(value)}
