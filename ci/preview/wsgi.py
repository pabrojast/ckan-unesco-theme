"""Identificación de despliegue sin exponer configuración ni credenciales."""
import json
from pathlib import Path
from wsgi import application as ckan_application

revision = Path('/app/preview-theme-sha').read_text().strip()


def application(environ, start_response):
    if environ.get('PATH_INFO') == '/__preview/version':
        data = json.dumps({'environment': 'preview', 'theme_sha': revision}).encode()
        start_response('200 OK', [('Content-Type', 'application/json'), ('Cache-Control', 'no-store'), ('Content-Length', str(len(data)))])
        return [] if environ.get('REQUEST_METHOD') == 'HEAD' else [data]

    def headers(status, response_headers, exc_info=None):
        response_headers.append(('X-Preview-Revision', revision))
        return start_response(status, response_headers, exc_info)
    return ckan_application(environ, headers)
