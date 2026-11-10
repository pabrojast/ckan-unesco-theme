"""Interfaz de solicitudes de administración por iniciativa."""
import sqlalchemy as sa
from flask import request, current_app
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError as CSRFValidationError
from ckan.common import current_user
import ckan.model as model
import ckan.plugins.toolkit as tk
from . import initiative_membership as service


def _context():
    return {'user': current_user.name, 'auth_user_obj': current_user}


def _validate_post():
    # El blueprint heredado puede estar exento globalmente; estas rutas no.
    field = current_app.config.get('WTF_CSRF_FIELD_NAME', 'csrf_token')
    try:
        validate_csrf(request.form.get(field))
    except CSRFValidationError:
        tk.abort(400, tk._('Invalid security token. Reload the page and try again.'))


def access_state(group_dict):
    if not service.enabled() or not current_user.is_authenticated:
        return None
    try:
        group = service._group(group_dict['id'])
    except tk.ObjectNotFound:
        return None
    if service.can_review(current_user, group):
        return {'name': group.name, 'status': 'admin'}
    pending = model.Session.execute(sa.select(service.requests.c.id).where(
        service.requests.c.group_id == group.id,
        service.requests.c.user_id == current_user.id,
        service.requests.c.status == 'pending')).first()
    return {'name': group.name, 'status': 'pending' if pending else 'available'}


def pending_count():
    if not service.enabled() or not current_user.is_authenticated:
        return 0
    return service.initiative_membership_request_count(_context(), {})['count']


def _prepare(name=None):
    if not service.enabled():
        tk.abort(404)
    if not current_user.is_authenticated:
        return None
    if name is None:
        return True
    try:
        group = service._group(name)
        return tk.get_action('group_show')(_context(), {'id': group.id, 'include_datasets': False})
    except tk.ObjectNotFound:
        tk.abort(404, tk._('Initiative not found.'))


def request_access(name):
    group = _prepare(name)
    if group is None:
        return tk.redirect_to('user.login', came_from=request.path)
    state = access_state(group)
    if state['status'] != 'available':
        tk.h.flash_notice(tk._('You already administer this initiative.') if state['status'] == 'admin'
                          else tk._('Your request is awaiting review.'))
        return tk.redirect_to('group.read', id=name)
    message = ''
    if request.method == 'POST':
        _validate_post()
        message = request.form.get('message', '')
        try:
            tk.get_action('initiative_membership_request_create')(
                _context(), {'group_id': group['id'], 'message': message})
        except (tk.ValidationError, tk.NotAuthorized) as exc:
            tk.h.flash_error(str(exc))
        else:
            tk.h.flash_success(tk._('Your administrator access request has been sent for review.'))
            return tk.redirect_to('group.read', id=name)
    return tk.render('initiative/access_request.html', extra_vars={
        'group_dict': group, 'group_type': 'group', 'message': message})


def review_access(name):
    group = _prepare(name)
    if group is None:
        return tk.redirect_to('user.login', came_from=request.path)
    try:
        service._reviewer(_context(), service._group(group['id']))
    except tk.NotAuthorized:
        tk.abort(403, tk._('Only administrators of this initiative can review requests.'))
    if request.method == 'POST':
        _validate_post()
        try:
            tk.get_action('initiative_membership_request_process')(_context(), {
                'id': request.form.get('request_id', ''), 'group_id': group['id'],
                'action': request.form.get('action'), 'admin_note': request.form.get('admin_note', '')})
        except (tk.ValidationError, tk.NotAuthorized, tk.ObjectNotFound) as exc:
            tk.h.flash_error(str(exc))
        else:
            tk.h.flash_success(tk._('Request processed.'))
        return tk.redirect_to('theme_ejemplo.initiative_membership_requests', name=name)
    rows = tk.get_action('initiative_membership_request_list')(_context(), {'group_id': group['id']})
    return tk.render('initiative/access_reviews.html', extra_vars={
        'group_dict': group, 'group_type': 'group',
        'pending': [r for r in rows['results'] if r['status'] == 'pending'],
        'history': [r for r in rows['results'] if r['status'] != 'pending']})


def overview():
    if _prepare() is None:
        return tk.redirect_to('user.login', came_from=request.path)
    return tk.render('initiative/access_overview.html', extra_vars={
        'initiatives': service.review_groups(service._actor(_context()))})


def register(blueprint):
    blueprint.add_url_rule('/group/<name>/request-membership',
                           'request_initiative_membership', request_access, methods=['GET', 'POST'])
    blueprint.add_url_rule('/group/<name>/membership-requests',
                           'initiative_membership_requests', review_access, methods=['GET', 'POST'])
    blueprint.add_url_rule('/initiative-membership-requests',
                           'initiative_membership_requests_overview', overview)


HELPERS = {'initiative_access_state': access_state,
           'get_pending_initiative_membership_requests_count': pending_count}
