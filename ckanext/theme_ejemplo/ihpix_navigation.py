"""Rutas de regreso compartidas; no dependen del historial del navegador."""

from .ihpix_constants import slugify


FILTERS = ('biennium', 'region', 'country', 'institution_type', 'organization')


def breadcrumbs(endpoint, values, args, url_for, translate):
    _ = translate
    name = (endpoint or '').split('.')[-1]
    if not (endpoint or '').startswith('theme_ejemplo.') or 'ihpix' not in name:
        return []
    trail = [(_('Home'), url_for('home.index')),
             ('IHP IX', url_for('theme_ejemplo.ihpix'))]
    filters = {key: args[key] for key in FILTERS if args.get(key)}

    def add(label, route, **params):
        trail.append((label, url_for('theme_ejemplo.' + route, **params)))

    def progress(scope='overall', value=''):
        add(_('Implementation progress'), 'ihpix_progress', **filters)
        labels = {'pa': _('Priority area'), 'output': _('Output'),
                  'flagship': _('Flagship initiative'),
                  'ctwg': _('Cross-cutting working group')}
        if scope in labels and value:
            add(labels[scope] + ' · ' + value, 'ihpix_progress_' + scope,
                value=slugify(value) if scope in ('flagship', 'ctwg') else value,
                **filters)

    if name == 'ihpix':
        return trail
    if name.startswith('ihpix_progress'):
        progress(values.get('scope', 'overall'), values.get('value') or '')
    elif name in ('ihpix_presentation', 'ihpix_narrative'):
        if args.get('scope') == 'organization' and args.get('value'):
            filters['organization'] = args['value']
        progress(args.get('scope', 'overall'), args.get('value', ''))
        add(_('Presentation / PDF') if name == 'ihpix_presentation' else _('Generate report'), name)
    elif name in ('ihpix_outputs', 'ihpix_output_detail', 'ihpix_activity_detail'):
        add(_('Activities Explorer'), 'ihpix_outputs', **filters)
        if name == 'ihpix_output_detail':
            add(_('Output') + ' ' + values['code'], name, code=values['code'])
        elif name == 'ihpix_activity_detail':
            add(_('Activity'), name, id=values['id'])
    elif name == 'ihpix_priority_area':
        add(_('Priority area') + ' ' + values['pa'], name, pa=values['pa'])
    elif name.startswith('ihpix_group') and values.get('slug'):
        add(_('Working groups'), 'ihpix_workspaces')
        add(_('Group workspace'), 'ihpix_group', slug=values['slug'])
        if name in ('ihpix_group_plan','ihpix_group_plan_new'):
            add(_('Activity plan'), 'ihpix_group', slug=values['slug'], tab='plan')
            add(_('Planned activity'), name, **values)
        elif name in ('ihpix_group_import','ihpix_group_import_batch'):
            add(_('Import with preview'), name, **values)
    elif name in ('ihpix_workspaces', 'ihpix_workspace_detail', 'ihpix_workspace_members', 'ihpix_workspace_collaboration'):
        add(_('Working groups'), 'ihpix_workspaces')
        if values.get('code'):
            add(_('Group workspace'), 'ihpix_group', slug='oetwg-'+values['code'][0])
            add(_('Output') + ' ' + values['code'], 'ihpix_workspace_detail', code=values['code'])
            if name == 'ihpix_workspace_members':
                add(_('Members'), name, code=values['code'])
            elif name == 'ihpix_workspace_collaboration':
                add(_('Workspace collaboration'), name, code=values['code'])
    elif name in ('ihpix_report_edit', 'ihpix_report_collaboration'):
        add(_('My reports'), 'ihpix_my_reports')
        add(_('Edit report'), 'ihpix_report_edit', id=values['id'])
        if name == 'ihpix_report_collaboration':
            add(_('Collaboration'), name, id=values['id'])
    else:
        labels = {'ihpix_report': _('Report an activity'),
                  'ihpix_import': _('Import reports'),
                  'ihpix_notifications': _('Notifications'),
                  'ihpix_contributors': _('Contributors'),
                  'user_ihpix': _('IHP-IX Reports'),
                  'group_ihpix': _('IHP-IX Activities'),
                  'organization_ihpix': _('IHP-IX Activities'),
                  'ihpix_content_admin': _('Page Content'),
                  'ihpix_activities_admin': _('Activities'),
                  'ihpix_reports_admin': _('Reports'),
                  'ihpix_admin_overview': _('Overview'),
                  'ihpix_workspaces_admin': _('Working groups'),
                  'ihpix_institutions_admin': _('Institutions')}
        if name in labels:
            add(labels[name], name, **values)
    return trail


def navigation():
    from flask import request
    from ckan.plugins import toolkit
    return breadcrumbs(request.endpoint, request.view_args or {}, request.args,
                       toolkit.url_for, toolkit._)
