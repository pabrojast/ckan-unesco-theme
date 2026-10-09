"""Ajustes de preview para las bases publicadas antes de estas correcciones."""
import configparser
from pathlib import Path

for path in (Path('/app/production.ini'), Path('/srv/app/production.ini')):
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read(path)
    app = config['app:main']
    app.pop('beaker.session.cookie_domain', None)
    # DOI ejecuta escrituras externas en after_dataset_create incluso en test_mode.
    app['ckan.plugins'] = ' '.join(p for p in app['ckan.plugins'].split() if p != 'doi')
    with path.open('w') as stream:
        config.write(stream)
