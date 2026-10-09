# encoding: utf-8
"""Formularios de solicitud y revisión de membresías de iniciativas."""

from flask import abort, current_app, make_response, render_template
from ckan.common import current_user, request
import ckan.lib.helpers as h
import ckan.plugins.toolkit as toolkit

from . import initiative_membership as memberships

_ = toolkit._


def _context():
    return {'user': current_user.name, 'auth_user_obj': current_user}


def _group(name):
    try:
        return memberships.get_initiative(name)
    except toolkit.ObjectNotFound:
        abort(404, _('Initiative not found'))


def _render(template, **kwargs):
    response = make_response(render_template(template, **kwargs))
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def _protect_post():
    # CKAN puede eximir a extensiones antiguas; estas vistas sí validan CSRF.
    current_app.extensions['csrf'].protect()


def request_membership(name):
    group = _group(name)
    if not current_user.is_authenticated:
        return toolkit.redirect_to('user.login', came_from=toolkit.url_for(
            'theme_ejemplo.request_initiative_membership', name=group.name))
    group_dict = memberships._group_dict(group)
    state = memberships.initiative_membership_state(group_dict)
    if state['member'] or state['pending']:
        h.flash_notice(_('You are already a member of this initiative.') if state['member']
                       else _('You already have a pending request for this initiative.'))
        return toolkit.redirect_to('group.read', id=group.name)
    errors = {}
    message = request.form.get('message', '')
    if request.method == 'POST':
        _protect_post()
        try:
            toolkit.get_action('initiative_membership_request_create')(
                _context(), {'group_id': group.id, 'message': message})
        except toolkit.ValidationError as error:
            errors = error.error_dict
        else:
            h.flash_success(_('Your request to join this initiative has been sent.'))
            return toolkit.redirect_to('group.read', id=group.name)
    return _render('group/request_membership.html', group_dict=group_dict,
                   group_type='group', message=message, errors=errors)


def membership_requests(name):
    group = _group(name)
    if not current_user.is_authenticated:
        return toolkit.redirect_to('user.login', came_from=toolkit.url_for(
            'theme_ejemplo.initiative_membership_requests', name=group.name))
    if not memberships.can_manage(current_user, group.id):
        abort(403, _('Only initiative administrators can manage membership requests.'))
    tab = 'history' if request.args.get('tab') == 'history' else 'pending'
    if request.method == 'POST':
        _protect_post()
        try:
            toolkit.get_action('initiative_membership_request_process')(
                _context(), {'group_id': group.id,
                             'id': request.form.get('request_id'),
                             'action': request.form.get('action'),
                             'role': request.form.get('role', 'member'),
                             'admin_note': request.form.get('admin_note', '')})
        except toolkit.NotAuthorized:
            abort(403)
        except toolkit.ObjectNotFound:
            abort(404)
        except toolkit.ValidationError as error:
            h.flash_error(str(error))
        else:
            h.flash_success(_('Membership request approved successfully.')
                            if request.form.get('action') == 'approve'
                            else _('Membership request rejected.'))
        return toolkit.redirect_to('theme_ejemplo.initiative_membership_requests',
                                   name=group.name, tab=tab)
    result = toolkit.get_action('initiative_membership_request_list')(
        _context(), {'group_id': group.id})
    pending = [row for row in result['results'] if row['status'] == 'pending']
    return _render('group/membership_requests.html', group_dict=result['group'],
                   group_type='group', pending_requests=pending,
                   pending_count=len(pending), active_tab=tab,
                   history_requests=[row for row in result['results']
                                     if row['status'] != 'pending'])


def membership_requests_overview():
    if not current_user.is_authenticated:
        return toolkit.redirect_to('user.login', came_from=toolkit.url_for(
            'theme_ejemplo.initiative_membership_requests_overview'))
    groups = memberships.pending_groups(current_user)
    if len(groups) == 1:
        return toolkit.redirect_to('theme_ejemplo.initiative_membership_requests',
                                   name=groups[0].name)
    return _render('group/membership_requests_overview.html', groups_with_requests=groups)


def register_routes(blueprint):
    blueprint.add_url_rule('/group/<name>/request-membership',
                           'request_initiative_membership', request_membership,
                           methods=['GET', 'POST'])
    blueprint.add_url_rule('/group/<name>/membership-requests',
                           'initiative_membership_requests', membership_requests,
                           methods=['GET', 'POST'])
    blueprint.add_url_rule('/initiative-membership-requests',
                           'initiative_membership_requests_overview',
                           membership_requests_overview, methods=['GET'])
