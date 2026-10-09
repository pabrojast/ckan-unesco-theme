"""Valida el runtime construido antes de publicar la imagen."""
import configparser
from pathlib import Path
from beaker.util import coerce_session_params
import ckanext.theme_ejemplo.plugin

config = configparser.ConfigParser(interpolation=None, strict=False)
config.read('/app/production.ini')
app = config['app:main']
# start.py inyecta este valor desde el Secret; la imagen conserva un campo vacío.
app['beaker.session.secret'] = 'preview-ci-session-validation-only'
coerce_session_params({key.removeprefix('beaker.session.'): value
                       for key, value in app.items() if key.startswith('beaker.session.')})
assert app['ckan.site_url'] == 'https://preview.dev-wins.com'
assert app['beaker.session.key'] == 'ckan_preview'
assert 'beaker.session.cookie_domain' not in app
assert Path('/app/preview-theme-sha').read_text().strip()
print('Preview runtime and session configuration verified')
