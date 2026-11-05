# -*- coding: utf-8 -*-
"""
Servidor local para probar la API de la comunidad sin CKAN.

Usa el mismo código que IHP-WINS (``community_store`` y ``community_rules``)
con SQLite en memoria. La identidad llega en la cabecera ``X-Test-Auth``
(sólo aquí; CKAN usa la sesión). Para reproducir las pruebas de Firebase, la
cuenta verificada alexandregermouty@gmail.com recibe ``platform_admin``, como
la cuenta propietaria de la versión Firebase.

    python tests/support/harness.py --port 8765 --rules ../../ckanext/theme_ejemplo/community_data/dacs.rules
"""
import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, REPO)

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from ckanext.theme_ejemplo.community_rules import RulesEngine  # noqa: E402
from ckanext.theme_ejemplo.community_store import (ApiError, CommunityApi,  # noqa: E402
                                                    DocumentStore)

OWNER_EMAIL = 'alexandregermouty@gmail.com'
LOCK = threading.Lock()


def make_api(rules_path):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    store = DocumentStore(engine, 'dacs')
    with open(rules_path) as f:
        rules = RulesEngine(f.read())
    return CommunityApi(store, rules)


def auth_from(header):
    if not header:
        return None
    info = json.loads(header)
    token = dict(info.get('token') or {})
    token['platform_admin'] = bool(token.get('email') == OWNER_EMAIL and token.get('email_verified'))
    return {'uid': info['uid'], 'token': token}


PUBLIC = os.path.join(REPO, 'ckanext', 'theme_ejemplo', 'public')
ROUTE = '/group/dacs/community-of-practice'
TYPES = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png',
         '.webp': 'image/webp', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml', '.woff2': 'font/woff2',
         '.mp4': 'video/mp4', '.webm': 'video/webm', '.pdf': 'application/pdf', '.json': 'application/json'}


def browser_auth(spec):
    """--browser-user uid:email:admin -> sesión simulada de CKAN para el navegador."""
    if not spec:
        return None
    uid, email, admin = (spec.split(':') + ['', ''])[:3]
    return {'uid': uid, 'token': {'email': email, 'email_verified': True, 'name': uid,
                                  'ckan_user': uid, 'platform_admin': admin == 'admin'}}


def serve(port, rules_path, browser_user=None):
    api = make_api(rules_path)
    session = browser_auth(browser_user)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            path = self.path.split('?', 1)[0]
            if path.startswith(ROUTE) and '/api/' not in path:
                with open(os.path.join(PUBLIC, 'dacs-community', 'index.html'), encoding='utf-8') as f:
                    html = f.read()
                cfg = {'routeBase': ROUTE + '/', 'apiBase': ROUTE + '/api/', 'loginUrl': '/user/login',
                       'registerUrl': '/user/register', 'logoutUrl': '/user/_logout', 'resetUrl': '/user/reset',
                       'groupUrl': '/group/dacs', 'groupTitle': 'DACS', 'csrfToken': 'test-token'}
                html = html.replace('<head>', '<head><script>window.__DACS__=%s;</script>' % json.dumps(cfg), 1)
                return self.reply(200, html.encode('utf-8'), 'text/html')
            if path.startswith('/dacs-community/'):
                full = os.path.normpath(os.path.join(PUBLIC, path.lstrip('/')))
                if full.startswith(PUBLIC) and os.path.isfile(full):
                    with open(full, 'rb') as f:
                        return self.reply(200, f.read(), TYPES.get(os.path.splitext(full)[1], 'application/octet-stream'))
            if path.endswith('/api/csrf'):
                return self.reply(200, b'{"token":"test-token"}', 'application/json')
            return self.reply(404, b'not found', 'text/plain')

        def reply(self, status, raw, ctype):
            self.send_response(status)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            length = int(self.headers.get('Content-Length') or 0)
            payload = json.loads(self.rfile.read(length) or b'{}')
            action = self.path.rstrip('/').rsplit('/', 1)[-1]
            status, body = 200, None
            with LOCK:
                try:
                    if action == 'clear':
                        api.store.clear()
                        body = {'ok': True}
                    else:
                        auth = auth_from(self.headers.get('X-Test-Auth')) or (
                            session if self.headers.get('X-Test-Bypass') != '1' else None)
                        if action == 'me':
                            body = {'user': None if not auth else {
                                'uid': auth['uid'], 'email': auth['token'].get('email'),
                                'name': auth['token'].get('name', auth['uid']), 'ckanName': auth['uid'],
                                'platformAdmin': auth['token'].get('platform_admin', False),
                                'sysadmin': False, 'accountUrl': '/user/' + auth['uid']}}
                        else:
                            body = api.handle(action, payload, auth,
                                              bypass=self.headers.get('X-Test-Bypass') == '1')
                            if os.environ.get('DACS_HARNESS_TRACE') and action == 'read':
                                for t, r in zip(payload.get('targets', []), body.get('results', [])):
                                    if 'error' in r:
                                        print('DENIED read', json.dumps(t), r['error']['code'], flush=True)
                except ApiError as exc:
                    status, body = exc.status, {'error': exc.as_dict()}
                    if os.environ.get('DACS_HARNESS_TRACE'):
                        print('DENIED', action, json.dumps(payload)[:400], exc.code, flush=True)
                except Exception as exc:  # error del servidor: visible en la prueba
                    import traceback
                    traceback.print_exc()
                    status, body = 500, {'error': {'code': 'internal', 'message': repr(exc)}}
            raw = json.dumps(body).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print('harness listening on %d' % port, flush=True)
    server.serve_forever()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--port', type=int, default=8765)
    p.add_argument('--rules', required=True)
    p.add_argument('--browser-user', help='uid:email[:admin], sesión simulada para probar en un navegador')
    a = p.parse_args()
    serve(a.port, a.rules, a.browser_user)
