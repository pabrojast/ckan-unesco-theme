# -*- coding: utf-8 -*-
"""Rutas de colaboración, importación e informes sobre los mismos servicios API."""
import base64
from functools import wraps

from flask import render_template, request, redirect, Response, abort, session, jsonify
from ckan.common import c
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckanext.theme_ejemplo import ihpix_collaboration as C, ihpix_reporting as R
from ckanext.theme_ejemplo import ihpix_bulk as B, ihpix_constants as K
from ckanext.theme_ejemplo.model import IhpixActivity, IhpixActivityLink, IhpixWorkingGroupMember


def context():
    return {'user': c.user, 'auth_user_obj': c.userobj, 'model': model}


def signed_in(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not c.userobj:
            return redirect(tk.url_for('user.login', came_from=request.full_path))
        try:
            return view(*args, **kwargs)
        except tk.NotAuthorized as exc:
            model.Session.rollback()
            abort(403, str(exc))
        except tk.ObjectNotFound as exc:
            model.Session.rollback()
            abort(404, str(exc))
        except tk.ValidationError as exc:
            model.Session.rollback()
            return render_template('ihpix/tool_error.html', errors=exc.error_dict,
                                   back=request.path), 400
    return wrapped


@signed_in
def workspace(code):
    actor, wg, member, lead = C.workspace_access(context(), code)
    if request.method == 'POST':
        C.ihpix_workspace_item_save(context(), dict(request.form, working_group_id=wg.id))
        return redirect(request.path)
    result = C.ihpix_workspace_item_list(context(), {'working_group_id': wg.id})
    people = []
    for member in IhpixWorkingGroupMember.get_for_group(wg.id, 'active'):
        person = model.User.get(member.user_id)
        if person:
            people.append({'id': person.id, 'name': person.display_name, 'role': member.role})
    from ckanext.theme_ejemplo import ihpix_service as service
    from ckanext.theme_ejemplo.ihpix_resource_access import visible
    rows, _ = IhpixActivity.get_filtered(output=wg.output_code, limit=None)
    activities = [row.as_dict() for row in rows if service.can_read(row, actor)]
    ids = [row['id'] for row in activities]
    resources = [link.as_dict() for link in model.Session.query(IhpixActivityLink).filter(
        IhpixActivityLink.activity_id.in_(ids)).all() if visible(link.as_dict(), actor)]
    return render_template('ihpix/collaboration.html', workspace=wg.as_dict(),
                           result=result, people=people, activities=activities, resources=resources)


@signed_in
def report_collaboration(id):
    if request.method == 'POST':
        C.ihpix_report_collaborator_update(context(), dict(request.form, id=id))
        return redirect(request.path)
    actor, activity = C.report_access(context(), id)
    return render_template('ihpix/report_collaboration.html', activity=activity.as_dict(),
                           result=C.ihpix_report_collaboration_show(context(), {'id': id}))


@signed_in
def notifications():
    if request.method == 'POST':
        C.ihpix_notification_read(context(), dict(request.form))
        return redirect(request.path)
    return render_template('ihpix/notifications.html', result=C.ihpix_notification_list(context(), {}))


@signed_in
def import_template():
    organizations = tk.get_action('organization_list')(context(), {'all_fields': True, 'limit': 1000})
    return Response(B.template(organizations), mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    headers={'Content-Disposition': 'attachment; filename=ihpix-import-v1.xlsx'})


@signed_in
def bulk_import():
    batch = None
    if request.method == 'POST':
        if request.form.get('confirm'):
            R.ihpix_import_create(context(), dict(request.form))
            return redirect(tk.url_for('theme_ejemplo.ihpix_import', id=request.form['id']))
        upload = request.files.get('workbook')
        if not upload:
            raise tk.ValidationError({'workbook': 'Choose an XLSX workbook'})
        raw = upload.read(5 * 1024 * 1024 + 1)
        batch = R.ihpix_import_preview(context(), {'workbook': base64.b64encode(raw).decode('ascii')})
        return redirect(tk.url_for('theme_ejemplo.ihpix_import', id=batch['id']))
    if request.args.get('id'):
        batch = R.ihpix_import_show(context(), {'id': request.args['id']})
    return render_template('ihpix/import.html', batch=batch)


@signed_in
def narrative():
    data = R.ihpix_narrative_data(context(), dict(request.args)) if request.args.get('value') else None
    organizations = tk.get_action('organization_list')(context(), {'all_fields': True, 'limit': 1000})
    return render_template('ihpix/narrative.html', report=data, organizations=organizations,
                           priority_areas=K.PRIORITY_AREAS, outputs=K.load_output_titles(), biennia=K.BIENNIA)


def activity(id):
    row = IhpixActivity.get(id)
    if not row or row.status != 'published':
        abort(404)
    from ckanext.theme_ejemplo import ihpix_relations as relations, ihpix_stats as stats
    from ckanext.theme_ejemplo.actions import _ihpix_country_index, _ihpix_links_for
    from ckanext.theme_ejemplo.ihpix_resource_access import filtered
    data = row.as_dict()
    return render_template('ihpix/activity_detail.html', activity=data,
        contributions=relations.associations(data),
        prepared=stats.prepare_row(data, _ihpix_country_index()),
        stats=stats.compute_progress_stats([data], country_index=_ihpix_country_index()),
        resources=filtered(_ihpix_links_for(row.id), c.userobj))


@signed_in
def presentation():
    from ckanext.theme_ejemplo.ihpix_presentation import slides
    data = dict(request.args)
    stats = tk.get_action('ihpix_progress_stats')(context(), data)
    filters = {key: data[key] for key in ('biennium', 'region', 'country', 'institution_type') if data.get(key)}
    back = tk.url_for('theme_ejemplo.ihpix_progress')
    return render_template('ihpix/presentation.html', stats=stats, slides=slides(stats),
                           filters=filters, back=back, source_url=request.url)


def pending_resource():
    pending = session.get('ihpix_resource_return')
    return pending if pending and c.userobj and pending['user_id'] == c.userobj.id else None


@signed_in
def resource_start(id):
    actor, activity = C.report_access(context(), id)
    if activity.status not in ('draft', 'rejected'):
        raise tk.ValidationError({'id': 'Save the report as a draft before creating a resource'})
    kind = request.form.get('kind')
    if kind not in ('dataset', 'event'):
        raise tk.ValidationError({'kind': 'Choose dataset or event'})
    session['ihpix_resource_return'] = {'report_id': id, 'user_id': actor.id, 'kind': kind}
    if kind == 'dataset':
        url = tk.url_for('dataset.new')
    else:
        url = tk.h.ihpix_pages_url('pages.water_events_new', '/water-events_edit')
    return jsonify({'url': url})


@signed_in
def resource_attach():
    pending = pending_resource()
    if not pending:
        raise tk.ValidationError({'id': 'No report is waiting for an attachment'})
    actor, activity = C.report_access(context(), pending['report_id'])
    from ckanext.theme_ejemplo import actions as A, ihpix_service as V, ihpix_forms as F
    target = request.form.get('target_id', '')
    if pending['kind'] == 'dataset':
        pkg = tk.get_action('package_show')(context(), {'id': target})
        link = {'link_type': 'dataset', 'target_kind': 'package', 'target_id': pkg['id'],
                'title': pkg.get('title') or pkg['name'], 'url': tk.url_for('dataset.read', id=pkg['name'], qualified=True)}
    else:
        from ckanext.pages.db import Page
        page = model.Session.query(Page).filter_by(name=target, page_type='water-events').first()
        if not page:
            raise tk.ObjectNotFound('Event not found')
        link = {'link_type': 'event', 'target_kind': 'page', 'target_id': page.name,
                'title': page.title, 'url': tk.config.get('ckan.site_url', '') + '/water-events/' + page.name}
    values = F.activity_to_form_dict(activity.as_dict())
    from ckanext.theme_ejemplo.ihpix_resource_access import filtered
    values.update(expected_revision=activity.revision, save_as_draft='1',
                  links_json=filtered(A._ihpix_links_for(activity.id), actor) + [link])
    V.save(context(), values, activity)
    model.Session.commit()
    session.pop('ihpix_resource_return', None)
    return redirect(tk.url_for('theme_ejemplo.ihpix_report_edit', id=activity.id) + '#section-7')


def register(blueprint):
    for path, endpoint, view, methods in [
        ('/ihpix/report/<id>/resource-start', 'ihpix_resource_start', resource_start, ['POST']),
        ('/ihpix/resource-return/attach', 'ihpix_resource_attach', resource_attach, ['POST']),
        ('/ihpix/presentation', 'ihpix_presentation', presentation, ['GET']),
        ('/ihpix/workspaces/<code>/collaboration', 'ihpix_workspace_collaboration', workspace, ['GET', 'POST']),
        ('/ihpix/report/<id>/collaboration', 'ihpix_report_collaboration', report_collaboration, ['GET', 'POST']),
        ('/ihpix/notifications', 'ihpix_notifications', notifications, ['GET', 'POST']),
        ('/ihpix/import/template.xlsx', 'ihpix_import_template', import_template, ['GET']),
        ('/ihpix/import', 'ihpix_import', bulk_import, ['GET', 'POST']),
        ('/ihpix/reports/generate', 'ihpix_narrative', narrative, ['GET']),
        ('/ihpix/activities/<id>', 'ihpix_activity_detail', activity, ['GET']),
    ]:
        blueprint.add_url_rule(path, endpoint, view, methods=methods)
