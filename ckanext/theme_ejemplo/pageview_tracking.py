# encoding: utf-8
"""Conteo liviano de visitas y descargas (reemplazo de ``ckan.tracking_enabled``).

El tracking por defecto de CKAN dispara un request extra a ``/_tracking`` por
cada vista y hace un ``INSERT`` síncrono en ``tracking_raw`` (más un cron que
agrega toda la tabla y empuja conteos a Solr). Bajo alto tráfico eso satura los
workers WSGI y Postgres.

Este módulo registra las vistas/descargas **en Redis** dentro del request que ya
ocurre (un ``before_request`` de Flask, espejo de :mod:`ckanext.theme_ejemplo.cache`):

- ``HINCRBY`` O(1), sin INSERT por vista, sin request extra. Funciona incluso si
  la página se sirve desde la caché anónima.
- Filtra bots por ``User-Agent`` y deduplica la misma vista (IP+URL) en una
  ventana corta con una clave Redis TTL.

Un comando CLI (``ckan pageviews flush``, ejecutado por un CronJob cada ~5 min)
vuelca los contadores de Redis a tablas planas de Postgres
(``tracking_dataset_stats`` / ``tracking_resource_stats`` /
``tracking_site_totals`` / ``tracking_dataset_daily``), que son las que la UI del
tema ya lee. Sin Solr y sin ``tracking_raw``.

Política de configuración: todo bajo ``ckanext.theme_ejemplo.pageviews_*``
(ver `Variables de Entorno` en la vault).
"""
import datetime
import hashlib
import logging
import re

from flask import request
import ckan.plugins.toolkit as toolkit
import ckan.model as model
from sqlalchemy import text

log = logging.getLogger(__name__)

# Namespace propio del tema en Redis.
REDIS_PREFIX = 'theme_ejemplo:pv:'
VIEWS_KEY = REDIS_PREFIX + 'views'            # hash dataset_name -> delta
DOWNLOADS_KEY = REDIS_PREFIX + 'downloads'    # hash resource_id  -> delta
DAILY_KEY_FMT = REDIS_PREFIX + 'daily:%s'     # hash dataset_name -> delta (por día)
DAILY_INDEX = REDIS_PREFIX + 'daily_dates'    # set de fechas con bucket diario
SEEN_KEY_FMT = REDIS_PREFIX + 'seen:%s'       # clave de dedup con TTL
LOCK_KEY = REDIS_PREFIX + 'flush:lock'        # lock del flush

# Rutas reservadas que NO son nombres de dataset.
_RESERVED_NAMES = frozenset({'new'})

# Detecta y permite quitar el prefijo de idioma (``/es``, ``/fr``, ``/en_GB``).
_LOCALE_RE = re.compile(r'^/[a-z]{2}(?:_[A-Z]{2})?(?=/|$)')

# User-Agents de bots/crawlers a ignorar (subcadena, case-insensitive).
_BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|bing|google|yandex|baidu|duckduck|facebook|'
    r'embedly|quora|outbrain|pinterest|slack|whatsapp|telegram|semrush|'
    r'ahrefs|mj12|dotbot|petalbot|bytespider|gptbot|ccbot|claudebot|'
    r'python-requests|aiohttp|curl|wget|scrapy|headless|monitor|uptime|'
    r'pingdom|statuscake|datadog',
    re.IGNORECASE,
)

# Cache de patrones compilados, reconstruido sólo si cambia ``pageviews_view_paths``.
_pattern_cache = {'paths': None, 'view': None, 'download': None}

_redis_client = None
_redis_init_attempted = False
_hooks_registered = False


# ─── Redis (patrón lazy idéntico a cache.py) ──────────────────────────────


def _get_redis():
    """Obtiene un cliente Redis usando la configuración de CKAN (lazy)."""
    global _redis_client, _redis_init_attempted
    if _redis_init_attempted:
        return _redis_client
    _redis_init_attempted = True
    try:
        from ckan.lib.redis import connect_to_redis
        client = connect_to_redis()
        client.ping()
        _redis_client = client
        log.info('theme_ejemplo pageviews: usando Redis para conteo de vistas')
    except Exception as e:
        _redis_client = None
        log.warning('theme_ejemplo pageviews: Redis no disponible, '
                    'el conteo queda deshabilitado. Detalle: %s', e)
    return _redis_client


def _to_str(value):
    """Normaliza valores Redis (bytes o str) a str."""
    if isinstance(value, bytes):
        return value.decode('utf-8', 'replace')
    return value


# ─── Lectura de configuración ─────────────────────────────────────────────


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


def _is_enabled():
    return _cfg_bool('ckanext.theme_ejemplo.pageviews_enabled', False)


def _recent_days():
    return _cfg_int('ckanext.theme_ejemplo.pageviews_recent_days', 14) or 14


def _dedup_window():
    return _cfg_int('ckanext.theme_ejemplo.pageviews_dedup_window', 1800)


def _bot_filter_enabled():
    return _cfg_bool('ckanext.theme_ejemplo.pageviews_bot_filter', True)


def _view_paths():
    raw = toolkit.config.get('ckanext.theme_ejemplo.pageviews_view_paths')
    if not raw:
        return ('/dataset',)
    return tuple(p.strip().rstrip('/') for p in str(raw).split(',') if p.strip())


# ─── Heurísticas de matching ──────────────────────────────────────────────


def _strip_locale(path):
    stripped = _LOCALE_RE.sub('', path)
    return stripped or '/'


def _get_patterns():
    """Devuelve (view_re, download_re) compilados para los paths configurados."""
    paths = _view_paths()
    if _pattern_cache['paths'] != paths:
        alt = '|'.join(re.escape(p) for p in paths) or re.escape('/dataset')
        _pattern_cache['view'] = re.compile(r'^(?:%s)/([^/]+)$' % alt)
        _pattern_cache['download'] = re.compile(
            r'^(?:%s)/[^/]+/resource/([0-9a-fA-F-]{36})/download' % alt)
        _pattern_cache['paths'] = paths
    return _pattern_cache['view'], _pattern_cache['download']


def _match(norm_path):
    """Clasifica la ruta: ('view', name) | ('download', resource_id) | None."""
    view_re, download_re = _get_patterns()
    m = download_re.match(norm_path)
    if m:
        return ('download', m.group(1).lower())
    m = view_re.match(norm_path)
    if m:
        name = m.group(1)
        if name in _RESERVED_NAMES:
            return None
        return ('view', name)
    return None


def _is_bot(user_agent):
    return bool(user_agent) and bool(_BOT_RE.search(user_agent))


def _client_ip():
    fwd = request.headers.get('X-Forwarded-For')
    if fwd:
        return fwd.split(',')[0].strip()
    return request.remote_addr or ''


def _utc_today():
    return datetime.datetime.utcnow().date()


# ─── Registro (before_request) ────────────────────────────────────────────


def _record():
    """Registra una vista/descarga en Redis. Nunca corta el request."""
    try:
        if not _is_enabled() or request.method not in ('GET', 'HEAD'):
            return None

        norm_path = _strip_locale(request.path)
        matched = _match(norm_path)
        if not matched:
            return None
        kind, ident = matched

        if _bot_filter_enabled() and _is_bot(request.headers.get('User-Agent', '')):
            return None

        redis = _get_redis()
        if redis is None:
            return None

        # Dedup corto por IP+URL: evita inflar con refrescos del mismo visitante.
        window = _dedup_window()
        if window > 0:
            digest = hashlib.sha1(
                (_client_ip() + '|' + norm_path).encode('utf-8')).hexdigest()
            try:
                was_set = redis.set(SEEN_KEY_FMT % digest, 1, nx=True, ex=window)
            except Exception:
                was_set = True  # si el dedup falla, contamos igual
            if not was_set:
                return None

        if kind == 'view':
            today = _utc_today().isoformat()
            pipe = redis.pipeline(transaction=False)
            pipe.hincrby(VIEWS_KEY, ident, 1)
            pipe.hincrby(DAILY_KEY_FMT % today, ident, 1)
            pipe.sadd(DAILY_INDEX, today)
            pipe.execute()
        else:  # download
            redis.hincrby(DOWNLOADS_KEY, ident, 1)
    except Exception as e:
        # Nunca romper el serving por un fallo de conteo.
        log.debug('pageviews record error: %s', e)
    return None


def init_app(app):
    """Registra el hook ``before_request`` en la Flask app (idempotente).

    Debe registrarse ANTES que el de la caché anónima: Flask ejecuta los
    ``before_request`` en orden de registro y la caché puede cortar el request
    con un HIT; registrar el conteo primero garantiza contar incluso esos hits.
    """
    global _hooks_registered
    if _hooks_registered:
        return
    if not hasattr(app, 'before_request'):
        # No es la Flask app (puede ser el wrapper WSGI legacy de Pylons).
        return
    app.before_request(_record)
    _hooks_registered = True
    log.info('theme_ejemplo: conteo liviano de vistas registrado')


# ─── Volcado a Postgres (CLI / CronJob) ───────────────────────────────────


def _rotate_hash(redis, key):
    """RENAME atómico ``key`` -> ``key:flush`` y devuelve su contenido como dict.

    Los nuevos incrementos van a un hash fresco mientras procesamos el snapshot.
    Devuelve ``{}`` si la clave no existía.
    """
    tmp = key + ':flush'
    try:
        redis.rename(key, tmp)
    except Exception:
        return {}
    try:
        raw = redis.hgetall(tmp) or {}
    finally:
        redis.delete(tmp)
    out = {}
    for k, v in raw.items():
        try:
            out[_to_str(k)] = int(v)
        except (TypeError, ValueError):
            continue
    return out


def _apply_to_db(views, downloads, daily):
    """Aplica los deltas a las tablas de Postgres en una sola transacción."""
    engine = model.meta.engine
    recent_days = _recent_days()
    today = _utc_today()
    recent_cutoff = today - datetime.timedelta(days=recent_days - 1)
    prune_cutoff = today - datetime.timedelta(days=recent_days)

    views_added = sum(views.values())
    downloads_added = sum(downloads.values())

    with engine.begin() as conn:
        if views:
            conn.execute(text("""
                INSERT INTO tracking_dataset_stats
                    (dataset_name, total_views, recent_views, updated)
                VALUES (:name, :delta, 0, now())
                ON CONFLICT (dataset_name) DO UPDATE SET
                    total_views = tracking_dataset_stats.total_views + EXCLUDED.total_views,
                    updated = now()
            """), [{'name': n, 'delta': d} for n, d in views.items()])

        for day_str, counts in daily.items():
            try:
                day = datetime.date.fromisoformat(day_str)
            except ValueError:
                continue
            conn.execute(text("""
                INSERT INTO tracking_dataset_daily (dataset_name, day, views)
                VALUES (:name, :day, :delta)
                ON CONFLICT (dataset_name, day) DO UPDATE SET
                    views = tracking_dataset_daily.views + EXCLUDED.views
            """), [{'name': n, 'day': day, 'delta': d}
                   for n, d in counts.items()])

        if downloads:
            conn.execute(text("""
                INSERT INTO tracking_resource_stats
                    (resource_id, total_downloads, updated)
                VALUES (:rid, :delta, now())
                ON CONFLICT (resource_id) DO UPDATE SET
                    total_downloads = tracking_resource_stats.total_downloads + EXCLUDED.total_downloads,
                    updated = now()
            """), [{'rid': r, 'delta': d} for r, d in downloads.items()])

        if views_added or downloads_added:
            conn.execute(text("""
                INSERT INTO tracking_site_totals
                    (id, total_page_views, total_downloads, updated)
                VALUES (1, :v, :d, now())
                ON CONFLICT (id) DO UPDATE SET
                    total_page_views = tracking_site_totals.total_page_views + :v,
                    total_downloads = tracking_site_totals.total_downloads + :d,
                    updated = now()
            """), {'v': views_added, 'd': downloads_added})

        # Poda de buckets diarios fuera de la ventana ``recent``.
        conn.execute(text(
            "DELETE FROM tracking_dataset_daily WHERE day < :cutoff"),
            {'cutoff': prune_cutoff})

        # Recalcula recent_views globalmente desde la tabla diaria (acotada y
        # barata): mantiene exactos los datasets cuya ventana se desplazó.
        conn.execute(text("""
            UPDATE tracking_dataset_stats s
            SET recent_views = COALESCE(d.recent, 0), updated = now()
            FROM (
                SELECT dataset_name, SUM(views) AS recent
                FROM tracking_dataset_daily
                WHERE day >= :cutoff
                GROUP BY dataset_name
            ) d
            WHERE s.dataset_name = d.dataset_name
              AND s.recent_views <> COALESCE(d.recent, 0)
        """), {'cutoff': recent_cutoff})
        conn.execute(text("""
            UPDATE tracking_dataset_stats
            SET recent_views = 0, updated = now()
            WHERE recent_views <> 0
              AND dataset_name NOT IN (
                  SELECT DISTINCT dataset_name
                  FROM tracking_dataset_daily
                  WHERE day >= :cutoff
              )
        """), {'cutoff': recent_cutoff})

    return {
        'datasets_updated': len(views),
        'resources_updated': len(downloads),
        'views_added': views_added,
        'downloads_added': downloads_added,
    }


def flush_to_db():
    """Vuelca los contadores de Redis a Postgres. Pensado para correr por cron.

    Usa un lock en Redis para no solaparse con otra corrida del CronJob.
    """
    redis = _get_redis()
    if redis is None:
        return {'status': 'no-redis'}

    try:
        got_lock = redis.set(LOCK_KEY, 1, nx=True, ex=600)
    except Exception as e:
        log.warning('pageviews flush: no se pudo tomar el lock: %s', e)
        got_lock = True
    if not got_lock:
        return {'status': 'locked'}

    try:
        views = _rotate_hash(redis, VIEWS_KEY)
        downloads = _rotate_hash(redis, DOWNLOADS_KEY)

        daily = {}
        try:
            dates = redis.smembers(DAILY_INDEX) or set()
        except Exception:
            dates = set()
        for raw_date in dates:
            day_str = _to_str(raw_date)
            counts = _rotate_hash(redis, DAILY_KEY_FMT % day_str)
            if counts:
                daily[day_str] = counts
            try:
                redis.srem(DAILY_INDEX, raw_date)
            except Exception:
                pass

        result = _apply_to_db(views, downloads, daily)
        result['status'] = 'ok'
        return result
    finally:
        try:
            redis.delete(LOCK_KEY)
        except Exception:
            pass


def get_status():
    """Resumen para ``ckan pageviews status``: pendientes en Redis + totales DB."""
    status = {'enabled': _is_enabled(), 'redis': False,
              'pending_views': 0, 'pending_downloads': 0, 'pending_days': 0,
              'total_page_views': None, 'total_downloads': None}

    redis = _get_redis()
    if redis is not None:
        status['redis'] = True
        try:
            status['pending_views'] = redis.hlen(VIEWS_KEY)
            status['pending_downloads'] = redis.hlen(DOWNLOADS_KEY)
            status['pending_days'] = redis.scard(DAILY_INDEX)
        except Exception as e:
            log.debug('pageviews status redis error: %s', e)

    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            exists = conn.execute(text(
                "SELECT to_regclass('tracking_site_totals')")).fetchone()[0]
            if exists is not None:
                row = conn.execute(text(
                    "SELECT total_page_views, total_downloads "
                    "FROM tracking_site_totals WHERE id = 1")).fetchone()
                if row:
                    status['total_page_views'] = row[0]
                    status['total_downloads'] = row[1]
    except Exception as e:
        log.debug('pageviews status db error: %s', e)

    return status
