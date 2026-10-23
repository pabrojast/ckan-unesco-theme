"""Renderizado público de recursos con un CKAN real, sin crear contenido."""
import json
import os
from pathlib import Path

from ckan.cli import load_config
from ckan.config.middleware import make_app

config = load_config('/srv/app/production.ini')
config['ckanext.theme_ejemplo.pageviews_enabled'] = False
config['ckanext.theme_ejemplo.anon_cache_enabled'] = False
from werkzeug.test import Client
from werkzeug.wrappers import Response
app = make_app(config)
client = Client(app, Response)
from ckanext.theme_ejemplo.resource_styles import is_sld_resource
from ckan.plugins import toolkit
import ckan.model as model

names = [
    'harmonized-hydrogeological-map-of-the-hoa-1-5-000-000',
    'geological-map-of-somalia-1-1-500-000',
    'latin-american-drought-atlas-argentina',
]
checks = []
for name in names:
    pkg = toolkit.get_action('package_show')({}, {'id': name})
    before_ids = [r['id'] for r in pkg['resources']]
    for locale in ('', '/es', '/fr', '/ar'):
        response = client.get(locale + '/dataset/' + name, base_url='https://data.dev-wins.com')
        body = response.get_data(as_text=True)
        assert response.status_code == 200, (name, locale, response.status_code, body[-1500:])
        assert 'resource-style' in body and 'resources-all-files' in body, (name,locale)
        checks.append({'dataset': name, 'locale': locale, 'status': 200})
        if os.environ.get('SLD_SMOKE_OUTPUT'):
            Path(os.environ['SLD_SMOKE_OUTPUT']).mkdir(parents=True, exist_ok=True)
            Path(os.environ['SLD_SMOKE_OUTPUT'],name+(locale.replace('/','-') or '-en')+'.html').write_text(body)
    for query in ('mode=grouped','mode=all','mode=grouped&format=SLD','mode=all&format=SLD','page=2&limit=1'):
        response = client.get('/dataset/'+name+'/resources_ajax?'+query,base_url='https://data.dev-wins.com')
        assert response.status_code == 200, (name, query, response.get_data(as_text=True)[-1500:])
        data = response.get_json()
        assert data['html'] and data['total'] > 0, (name,query,data)
        checks.append({'dataset':name,'query':query,'total':data['total']})
    after = toolkit.get_action('package_show')({}, {'id':name})
    assert before_ids == [r['id'] for r in after['resources']]
    assert all(r['tracking_summary']['total'] == 0 for r in after['resources'] if is_sld_resource(r))
private = model.Session.query(model.Package).filter(model.Package.private == True, model.Package.state == 'active').first()
if private:
    response = client.get('/dataset/'+private.id+'/resources_ajax', base_url='https://data.dev-wins.com')
    assert response.status_code in (403,404), response.status_code
    checks.append({'private_dataset': 'access_denied', 'status':response.status_code})
print('SLD_SMOKE_RESULT='+json.dumps(checks))
