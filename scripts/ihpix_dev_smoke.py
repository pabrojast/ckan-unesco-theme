# -*- coding: utf-8 -*-
"""Humo de las páginas IHP-IX contra un CKAN real, desde dentro del pod.

Renderiza cada página como el primer sysadmin activo con el cliente de
pruebas de Flask (token de API temporal, revocado al final) y comprueba que
ninguna devuelve 5xx. No toca datos.

Uso (dev, contexto kubectl `default`):

    POD=$(kubectl -n ckan get pods -o name | grep pod/ckan- | grep -v datapusher | head -1)
    kubectl -n ckan exec -i $POD -c ckan -- python3 - < scripts/ihpix_dev_smoke.py 2>/dev/null

Imprime una línea por página y termina con código 1 si alguna falló.
"""
import json
import re
import sys
import warnings

warnings.filterwarnings('ignore')

from ckan.cli import load_config  # noqa: E402
from ckan.config.middleware import make_app  # noqa: E402

INI = '/srv/app/production.ini'
BASE_URL = 'https://data.dev-wins.com'
PAGES = [
    '/ihpix', '/ihpix/report', '/ihpix/report?output=1.3', '/ihpix/outputs', '/ihpix/outputs/1.3',
    '/ihpix/priority-area/PA1', '/ihpix/contributors', '/ihpix/workspaces', '/ihpix/workspaces/1.3',
    '/ihpix/workspaces/1.3/members', '/ihpix/dashboard', '/ihpix/my-reports',
    '/ckan-admin/ihpix', '/ckan-admin/ihpix/activities', '/ckan-admin/ihpix/reports?status=pending',
    '/ckan-admin/ihpix/workspaces', '/ckan-admin/ihpix/overview',
]
REPORT_MARKERS = ('ihpix-forms-i18n', 'data-ihpix-multipicker', 'data-ihpix-markdown',
                  'id="ihpix-publication-modal"', '<option value="course">')


def main():
    app = make_app(load_config(INI))
    flask_app = app
    while not hasattr(flask_app, 'test_client'):
        flask_app = (getattr(flask_app, 'app', None) or getattr(flask_app, '_wsgi_app', None)
                     or getattr(flask_app, 'wsgi_app'))
    import ckan.model as model
    import ckan.plugins.toolkit as tk
    admin = (model.Session.query(model.User)
             .filter(model.User.sysadmin == True, model.User.state == 'active')  # noqa: E712
             .order_by(model.User.created).first())
    ctx = {'user': admin.name, 'auth_user_obj': admin, 'model': model, 'ignore_auth': True}
    token = tk.get_action('api_token_create')(ctx, {'user': admin.name, 'name': 'ihpix-smoke-tmp'})['token']
    client = flask_app.test_client()
    headers = {'Authorization': token}
    failed = []
    try:
        for page in PAGES + ['/user/%s/ihpix' % admin.name]:
            r = client.get(page, headers=headers, base_url=BASE_URL)
            body = r.get_data(as_text=True)
            err = re.search(r'jinja2\.exceptions\.\w+: [^\n<]*', body)
            status = r.status_code
            print('%-44s %s %s' % (page, status, (err.group(0)[:120] if err else '')))
            if status >= 500:
                failed.append(page)
        r = client.get('/ihpix/report?output=1.3', headers=headers, base_url=BASE_URL)
        body = r.get_data(as_text=True)
        missing = [m for m in REPORT_MARKERS if m not in body]
        print('marcadores del reporte ausentes:', missing or 'ninguno')
        if missing:
            failed.append('markers')
        r = client.post('/ihpix/markdown-preview', headers=headers, data={'text': '**b**'}, base_url=BASE_URL)
        print('markdown-preview:', r.status_code, r.get_data(as_text=True)[:80])
    finally:
        tk.get_action('api_token_revoke')(ctx, {'token': token})
    print(json.dumps({'failed': failed}))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
