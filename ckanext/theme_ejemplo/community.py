# -*- coding: utf-8 -*-
"""
Comunidad de práctica de un grupo de IHP-WINS (added by Jorgen Van Der Biest).

Sirve en ``/group/<name>/community-of-practice`` la plataforma de miembros de
la Década de Acción para las Ciencias Criosféricas (DACS Community, escrita por
Alexandre Germouty para Firebase), ahora sobre IHP-WINS:

- inicio de sesión: la cuenta y la sesión de CKAN (sin Firebase Authentication);
- datos: tabla ``dacs_community_document`` en la base de CKAN
  (``community_store.py``), creada en el primer uso, sin migración;
- permisos: el mismo archivo de reglas de la versión Firebase
  (``community_data/dacs.rules``), ejecutado por ``community_rules.py``;
- interfaz: la aplicación React compilada en ``public/dacs-community``
  (código fuente en ``frontend/dacs-community``).

Administradores de la comunidad (acceso completo de la Secretaría de UNESCO en
la aplicación): los sysadmins de IHP-WINS y los administradores del grupo CKAN.

Ver ``docs/obsidian-vault/Comunidad de Practica DACS.md``.
"""
import json
import logging
import os
from urllib.parse import quote, urlparse

from flask import Response, abort, redirect, request

import ckan.model as model
import ckan.plugins.toolkit as toolkit

from .community_rules import RulesEngine
from .community_store import ApiError, CommunityApi, DocumentStore

log = logging.getLogger(__name__)

# Grupos con comunidad de práctica: nombre del grupo CKAN -> configuración.
COMMUNITIES = {
    'dacs': {
        'title': u'UN Decade of Action for Cryospheric Sciences',
        'rules': 'dacs.rules',
    },
}

ROUTE = u'/group/<name>/community-of-practice'
STATIC_BASE = u'/dacs-community/'
MAX_BODY_BYTES = 24 * 1024 * 1024

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUILD_DIR = os.path.join(_HERE, 'public', 'dacs-community')
_RULES_DIR = os.path.join(_HERE, 'community_data')

_rules_cache = {}
_page_cache = {}


def register(blueprint):
    """Añade las rutas de la comunidad al blueprint del tema (llamado en plugin.py)."""
    blueprint.add_url_rule(ROUTE, u'community_of_practice', page,
                           methods=['GET'], strict_slashes=False)
    blueprint.add_url_rule(ROUTE + u'/api/<action>', u'community_of_practice_api', api,
                           methods=['GET', 'POST'])
    blueprint.add_url_rule(ROUTE + u'/<path:subpath>', u'community_of_practice_path', page,
                           methods=['GET'])


# ---------------------------------------------------------------------------
# Usuario, grupo y reglas
# ---------------------------------------------------------------------------

def _current_user():
    user = None
    try:
        from ckan.common import current_user
        if getattr(current_user, 'is_authenticated', False) and not getattr(current_user, 'is_anonymous', False):
            user = current_user
    except ImportError:
        pass
    if not user:
        # CKAN 2.10 pone g.userobj = '' (cadena vacía) para visitantes anónimos.
        user = getattr(toolkit.c, 'userobj', None) or None
    if not user or not getattr(user, 'id', None) or getattr(user, 'state', 'active') != 'active':
        return None
    # current_user es un proxy: se usa el objeto del modelo.
    return model.User.get(user.id) or user


def _group(name):
    try:
        return model.Group.get(name)
    except Exception:  # noqa
        log.exception(u'Comunidad %s: no se pudo leer el grupo', name)
        return None


def _is_group_admin(user, group):
    if user is None or group is None:
        return False
    q = model.Session.query(model.Member).filter(
        model.Member.group_id == group.id,
        model.Member.table_name == u'user',
        model.Member.table_id == user.id,
        model.Member.state == u'active',
        model.Member.capacity == u'admin')
    return q.first() is not None


def _auth(user, group):
    """Identidad que ven las reglas (equivale a request.auth de Firebase)."""
    if user is None:
        return None
    platform_admin = bool(getattr(user, 'sysadmin', False)) or _is_group_admin(user, group)
    return {
        'uid': user.id,
        'token': {
            'email': user.email or u'',
            # CKAN no envía correos de verificación; las reglas adaptadas ya no
            # dependen de este dato (ver secretariatOwner en dacs.rules).
            'email_verified': True,
            'name': user.fullname or user.name,
            'ckan_user': user.name,
            'platform_admin': platform_admin,
        },
    }


def _rules(name):
    path = os.path.join(_RULES_DIR, COMMUNITIES[name]['rules'])
    mtime = os.path.getmtime(path)
    cached = _rules_cache.get(path)
    if cached is None or cached[0] != mtime:
        with open(path, encoding='utf-8') as f:
            cached = (mtime, RulesEngine(f.read()))
        _rules_cache[path] = cached
    return cached[1]


def _api(name):
    return CommunityApi(DocumentStore(model.meta.engine, name), _rules(name))


def _csrf_token():
    try:
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    except Exception:  # CKAN 2.9 o CSRF desactivado
        return u''


# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------

def _built_page(filename):
    path = os.path.join(_BUILD_DIR, filename)
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return None
    cached = _page_cache.get(path)
    if cached is None or cached[0] != mtime:
        with open(path, encoding='utf-8') as f:
            cached = (mtime, f.read())
        _page_cache[path] = cached
    return cached[1]


def _no_store(resp):
    # Nunca en el caché anónimo (cache.py) ni en el del navegador.
    resp.headers['Cache-Control'] = 'no-store, private'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    return resp


def page(name, subpath=None):
    if name not in COMMUNITIES:
        abort(404)
    if subpath:
        if subpath.startswith('logo-desk'):
            return redirect(STATIC_BASE + subpath)
        if subpath.startswith('api'):
            abort(404)
    html = _built_page('index.html')
    if html is None:
        return _no_store(Response(
            u'<p>The community application has not been built yet '
            u'(frontend/dacs-community: <code>npm run build:ckan</code>).</p>', status=503))
    group = _group(name)
    route_base = u'/group/%s/community-of-practice/' % name
    here = request.full_path if request.query_string else request.path
    cfg = {
        'routeBase': route_base,
        'apiBase': route_base + u'api/',
        'staticBase': STATIC_BASE,
        'csrfToken': _csrf_token(),
        'loginUrl': u'/user/login?came_from=' + quote(here, safe=''),
        'registerUrl': u'/colab',  # registro de IHP-WINS (ckanext-colab), como el enlace Register del encabezado
        'logoutUrl': u'/user/_logout',
        'resetUrl': u'/user/reset',
        'groupUrl': u'/group/%s' % name,
        'groupTitle': (group.display_name if group is not None else COMMUNITIES[name]['title']),
        'siteTitle': u'IHP-WINS',
    }
    script = u'<script>window.__DACS__=%s;</script>' % json.dumps(cfg).replace(u'</', u'<\\/')
    html = html.replace(u'<head>', u'<head>' + script, 1)
    return _no_store(Response(html, mimetype='text/html'))


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

def _json(body, status=200):
    resp = Response(json.dumps(body, ensure_ascii=False, separators=(',', ':')),
                    status=status, mimetype='application/json')
    return _no_store(resp)


def _same_origin():
    """Rechaza peticiones enviadas desde otro sitio (además de la cabecera propia)."""
    for header in ('Origin', 'Referer'):
        value = request.headers.get(header)
        if value:
            return urlparse(value).netloc == request.host
    return True


def _me(user, group, name):
    auth = _auth(user, group)
    info = None
    if auth is not None:
        info = {
            'uid': auth['uid'],
            'email': auth['token']['email'],
            'name': auth['token']['name'],
            'ckanName': user.name,
            'platformAdmin': auth['token']['platform_admin'],
            'sysadmin': bool(getattr(user, 'sysadmin', False)),
            'accountUrl': u'/user/%s' % user.name,
        }
    return {'user': info}


def api(name, action):
    if name not in COMMUNITIES:
        abort(404)
    if request.method == 'GET':
        if action == 'csrf':
            return _json({'token': _csrf_token()})
        return _json({'error': {'code': 'not-found', 'message': 'Unknown action'}}, 404)
    if request.headers.get('X-DACS-Request') != '1' or not _same_origin():
        return _json({'error': {'code': 'permission-denied', 'message': 'Cross-site request refused.'}}, 403)
    if (request.content_length or 0) > MAX_BODY_BYTES:
        return _json({'error': {'code': 'resource-exhausted', 'message': 'Request too large.'}}, 413)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return _json({'error': {'code': 'invalid-argument', 'message': 'JSON body expected.'}}, 400)
    try:
        user = _current_user()
        group = _group(name)
        if action == 'me':
            return _json(_me(user, group, name))
        result = _api(name).handle(action, payload, _auth(user, group))
    except ApiError as exc:
        if exc.code not in ('permission-denied', 'not-found'):
            log.info(u'Comunidad %s: %s (%s)', name, exc.message, action)
        return _json({'error': exc.as_dict()}, exc.status)
    except Exception:  # noqa
        log.exception(u'Comunidad %s: error en la acción %s', name, action)
        return _json({'error': {'code': 'internal', 'message': 'Server error.'}}, 500)
    return _json(result)
