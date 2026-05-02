# encoding: utf-8
"""Caché de respuestas anónimas para mitigar la carga de bots y crawlers.

Los crawlers golpean de forma muy concentrada las mismas variantes de
``/dataset/?_X_sort=...``, ``?page=N`` y combinaciones de facetas. Servir
esas respuestas desde un caché en Redis (con fallback a memoria local) por
unos minutos permite absorber esos picos sin pegarle a Solr ni renderizar
Jinja.

Política:

- Sólo se cachea ``GET``/``HEAD`` con respuesta ``200`` y ``Content-Type``
  texto/JSON/XML.
- Se descarta cualquier petición con cookie de sesión (autenticada o
  semi-autenticada): el caché es exclusivamente para tráfico anónimo.
- Se descartan respuestas que setean ``Set-Cookie`` o que vienen marcadas
  como ``private`` / ``no-store`` por upstream.
- La clave incluye método, idioma activo, path, query string ordenada y
  ``Accept-Encoding`` para no mezclar bodies comprimidos.
- Configurable por completo vía ``ckanext.theme_ejemplo.anon_cache_*``
  (ver `Variables de Entorno` en la vault).
"""
import logging
import pickle
import re
import time
from collections import OrderedDict
from threading import Lock
from urllib.parse import urlencode

from flask import request, Response
import ckan.plugins.toolkit as toolkit

log = logging.getLogger(__name__)

# Prefijo de todas las claves en Redis (namespace propio del tema).
REDIS_PREFIX = 'theme_ejemplo:anon_cache:'

# Cookies que indican una sesión activa. Si aparece cualquiera de ellas
# bypaseamos el caché — el tráfico autenticado nunca debería ser servido
# desde una respuesta compartida.
_AUTH_COOKIE_NAMES = (
    'auth_tkt',
    'ckan',
    'ckan.flask.session',
    'session',
)

# Prefijos de path que NO se deben cachear nunca, incluso si encajan en la
# lista de inclusión. Se evalúan después de quitar el prefijo de idioma.
_DEFAULT_EXCLUDE_PREFIXES = (
    '/api',
    '/ckan-admin',
    '/user',
    '/dashboard',
    '/feeds',
    '/util',
    '/_tracking',
    '/membership-requests',
    '/bug-tickets',
)

# Si la lista de inclusión está vacía, se cachea todo lo que no esté excluido.
_DEFAULT_INCLUDE_PREFIXES = ()

# Detecta y permite quitar el prefijo de idioma (``/es``, ``/fr``, ``/en_GB``).
_LOCALE_RE = re.compile(r'^/[a-z]{2}(?:_[A-Z]{2})?(?=/|$)')


# ─── Backend local (LRU con TTL) ──────────────────────────────────────────


class _LocalCache:
    """LRU + TTL en memoria — fallback cuando Redis no está disponible."""

    def __init__(self, max_items=1000):
        self._store = OrderedDict()
        self._max = max_items
        self._lock = Lock()

    def get(self, key):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires = entry
            if expires < time.time():
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    def setex(self, key, ttl, value):
        with self._lock:
            self._store[key] = (value, time.time() + ttl)
            self._store.move_to_end(key)
            while len(self._store) > self._max:
                self._store.popitem(last=False)


_local_cache = _LocalCache()
_redis_client = None
_redis_init_attempted = False
_hooks_registered = False


def _get_redis():
    """Obtiene un cliente Redis usando la configuración de CKAN."""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    try:
        from ckan.lib.redis import connect_to_redis
        client = connect_to_redis()
        client.ping()
        _redis_client = client
        log.info('theme_ejemplo anon-cache: usando Redis para tráfico anónimo')
    except Exception as e:
        _redis_client = None
        log.warning(
            'theme_ejemplo anon-cache: Redis no disponible, '
            'cayendo a caché local en proceso. Detalle: %s', e
        )
    return _redis_client


# ─── Lectura de configuración ────────────────────────────────────────────


def _cfg_bool(key, default):
    try:
        return toolkit.asbool(toolkit.config.get(key, default))
    except Exception:
        return default


def _cfg_int(key, default):
    try:
        return max(0, toolkit.asint(toolkit.config.get(key, default)))
    except Exception:
        return default


def _cfg_list(key, default_tuple):
    raw = toolkit.config.get(key)
    if raw is None or raw == '':
        return tuple(default_tuple)
    return tuple(p.strip() for p in str(raw).split(',') if p.strip())


def _is_enabled():
    return _cfg_bool('ckanext.theme_ejemplo.anon_cache_enabled', False)


# ─── Heurísticas ─────────────────────────────────────────────────────────


def _strip_locale(path):
    """Quita el prefijo ``/xx`` o ``/xx_YY`` para matching de prefijos."""
    stripped = _LOCALE_RE.sub('', path)
    return stripped or '/'


def _matches_prefix(path, prefixes):
    for p in prefixes:
        if path == p or path.startswith(p + '/') or path.startswith(p + '?'):
            return True
    return False


def _should_skip_request():
    """True si la petición NO es candidata a servirse/guardarse en caché."""
    if request.method not in ('GET', 'HEAD'):
        return True

    cookies = request.cookies
    if any(name in cookies for name in _AUTH_COOKIE_NAMES):
        return True

    # Permite forzar bypass para debug.
    if request.args.get('_nocache') is not None:
        return True
    if 'no-cache' in request.headers.get('Cache-Control', '').lower():
        return True

    norm_path = _strip_locale(request.path)
    excludes = _cfg_list(
        'ckanext.theme_ejemplo.anon_cache_exclude_paths',
        _DEFAULT_EXCLUDE_PREFIXES,
    )
    if _matches_prefix(norm_path, excludes):
        return True

    includes = _cfg_list(
        'ckanext.theme_ejemplo.anon_cache_include_paths',
        _DEFAULT_INCLUDE_PREFIXES,
    )
    if includes and not _matches_prefix(norm_path, includes):
        return True

    return False


def _build_key():
    """Construye la clave: método + idioma + path + query ordenada + accept-encoding."""
    qs_pairs = sorted(request.args.lists()) if hasattr(request.args, 'lists') else sorted(request.args.items(multi=True))
    qs_norm = urlencode(qs_pairs, doseq=True)

    try:
        lang = toolkit.h.lang() or ''
    except Exception:
        lang = ''

    accept_enc = request.headers.get('Accept-Encoding', '')
    if 'br' in accept_enc:
        enc_key = 'br'
    elif 'gzip' in accept_enc:
        enc_key = 'gzip'
    else:
        enc_key = ''

    return '{prefix}{lang}|{enc}|{method}|{path}?{qs}'.format(
        prefix=REDIS_PREFIX,
        lang=lang,
        enc=enc_key,
        method=request.method,
        path=request.path,
        qs=qs_norm,
    )


# ─── Backend get/set unificado ───────────────────────────────────────────


def _cache_get(key):
    redis = _get_redis()
    if redis is not None:
        try:
            blob = redis.get(key)
            if blob is None:
                return None
            return pickle.loads(blob)
        except Exception as e:
            log.warning('anon-cache redis get falló: %s', e)
    return _local_cache.get(key)


def _cache_set(key, payload, ttl):
    redis = _get_redis()
    if redis is not None:
        try:
            redis.setex(key, ttl, pickle.dumps(payload, protocol=4))
            return
        except Exception as e:
            log.warning('anon-cache redis setex falló: %s', e)
    _local_cache.setex(key, ttl, payload)


# ─── Hooks Flask ─────────────────────────────────────────────────────────


def _before_request():
    if not _is_enabled():
        return None
    try:
        if _should_skip_request():
            return None
        key = _build_key()
        payload = _cache_get(key)
        if payload is None:
            request.environ['theme_ejemplo.anon_cache_key'] = key
            return None
        body, status, headers = payload
        resp = Response(body, status=status, headers=headers)
        resp.headers['X-Anon-Cache'] = 'HIT'
        return resp
    except Exception as e:
        log.debug('anon-cache before_request error: %s', e)
        return None


def _after_request(response):
    if not _is_enabled():
        return response
    try:
        key = request.environ.get('theme_ejemplo.anon_cache_key')
        if not key:
            return response
        if response.status_code != 200:
            return response
        # Respuestas con Set-Cookie son personalizadas — nunca cachear.
        if response.headers.get('Set-Cookie'):
            return response
        if response.is_streamed or getattr(response, 'direct_passthrough', False):
            return response
        cache_control = response.headers.get('Cache-Control', '').lower()
        if 'private' in cache_control or 'no-store' in cache_control:
            return response

        ctype = response.headers.get('Content-Type', '')
        if not (ctype.startswith('text/') or 'json' in ctype or 'xml' in ctype):
            return response

        body = response.get_data()
        max_bytes = _cfg_int('ckanext.theme_ejemplo.anon_cache_max_bytes', 1024 * 1024)
        if max_bytes and len(body) > max_bytes:
            return response

        ttl = _cfg_int('ckanext.theme_ejemplo.anon_cache_ttl', 300)
        if ttl <= 0:
            return response

        keep_headers = {}
        for name in ('Content-Type', 'Content-Encoding', 'Content-Language', 'Vary'):
            v = response.headers.get(name)
            if v is not None:
                keep_headers[name] = v

        _cache_set(key, (body, response.status_code, keep_headers), ttl)
        response.headers['X-Anon-Cache'] = 'MISS'
    except Exception as e:
        log.debug('anon-cache after_request error: %s', e)
    return response


def init_app(app):
    """Registra los hooks ``before_request``/``after_request`` en la Flask app.

    Idempotente — se asegura de no registrar dos veces si ``make_middleware``
    se invoca múltiples veces durante el arranque de CKAN.
    """
    global _hooks_registered
    if _hooks_registered:
        return
    if not (hasattr(app, 'before_request') and hasattr(app, 'after_request')):
        # No es la Flask app (puede ser el wrapper WSGI legacy de Pylons).
        return
    app.before_request(_before_request)
    app.after_request(_after_request)
    _hooks_registered = True
    log.info('theme_ejemplo: caché de respuestas anónimas registrado')
