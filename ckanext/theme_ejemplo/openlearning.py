# encoding: utf-8
"""Sincronización de cursos de UNESCO Open Learning.

Este módulo consulta la API pública de Open edX de openlearning.unesco.org
y mantiene una caché persistente curada en la tabla ``open_learning_course``
(ver model.py). Las decisiones de curación (status, override de tipo, orden)
nunca se modifican desde aquí: el sync solo actualiza los datos de display,
crea cursos nuevos como 'pending' y marca como no disponibles los que
desaparecen de la API.
"""

import datetime
import json
import logging
import threading
import time

import requests

import ckan.plugins.toolkit as toolkit
import ckan.model.meta as meta

from ckanext.theme_ejemplo.model import (
    OpenLearningCourse,
    init_open_learning_courses_db,
)

log = logging.getLogger(__name__)

API_URL = 'https://openlearning.unesco.org/api/courses/v1/courses/'

# Sesión propia (no la de plugin.py, para evitar import circular)
_http_session = requests.Session()

# Estado en memoria del gatillo lazy: cooldown entre intentos para no
# martillar la API si está caída, y lock para evitar syncs concurrentes
# dentro del mismo worker.
_SYNC_ATTEMPT_COOLDOWN = 300  # segundos
_last_sync_attempt = {'time': 0}
_sync_lock = threading.Lock()


def _get_config_int(key, default):
    try:
        return max(0, toolkit.asint(toolkit.config.get(key, default)))
    except Exception:
        return default


def _get_search_terms():
    """Términos de búsqueda configurables (CSV)."""
    raw = toolkit.config.get(
        'ckanext.theme_ejemplo.openlearning_search_terms',
        'water,ihp,hydrology,climate change,groundwater,flood,drought,'
        'water management,water governance,wash,sdg6,transboundary,'
        'ecohydrology,water education,water quality,aquifer')
    terms = [t.strip() for t in str(raw).split(',') if t.strip()]
    return terms or ['water']


def _parse_iso_datetime(value):
    """Parsea fechas ISO de la API ('2023-05-01T00:00:00Z') o None."""
    if not value:
        return None
    try:
        return datetime.datetime.strptime(value[:19], '%Y-%m-%dT%H:%M:%S')
    except (ValueError, TypeError):
        return None


def _detect_course_type(api_course):
    """Auto-detección permanente vs fecha fija a partir de los datos API.

    Regla principal: 'pacing' de Open edX ('self' = a tu ritmo,
    'instructor' = calendario fijo). Fallback si no viene pacing:
    fecha fija solo si hay timestamp de inicio real y fecha de término.
    """
    pacing = (api_course.get('pacing') or u'').strip().lower()
    if pacing == 'self':
        return OpenLearningCourse.TYPE_PERMANENT
    if pacing == 'instructor':
        return OpenLearningCourse.TYPE_SCHEDULED
    if api_course.get('start_type') == 'timestamp' and api_course.get('end'):
        return OpenLearningCourse.TYPE_SCHEDULED
    return OpenLearningCourse.TYPE_PERMANENT


def _fetch_all_courses(search_terms):
    """Trae todos los cursos de la API para los términos dados.

    Devuelve (courses_by_id, full_success). ``full_success`` es False si
    CUALQUIER página de CUALQUIER término falló: en ese caso el caller no
    debe marcar cursos como no disponibles (falso negativo).
    """
    page_size = _get_config_int(
        'ckanext.theme_ejemplo.openlearning_page_size', 50) or 50
    max_pages = _get_config_int(
        'ckanext.theme_ejemplo.openlearning_max_pages', 10) or 10

    courses_by_id = {}
    full_success = True

    for term in search_terms:
        url = API_URL
        params = {'search_term': term, 'page_size': page_size}
        pages_fetched = 0

        while url and pages_fetched < max_pages:
            try:
                response = _http_session.get(
                    url, params=params, timeout=(5, 10))
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                log.warning(
                    u"Open Learning: error HTTP para '%s' (página %d): %s",
                    term, pages_fetched + 1, e)
                full_success = False
                break
            except ValueError as e:
                log.warning(
                    u"Open Learning: respuesta no-JSON para '%s': %s", term, e)
                full_success = False
                break

            for course in data.get('results', []):
                course_id = course.get('course_id')
                if not course_id or course.get('hidden'):
                    continue
                courses_by_id.setdefault(course_id, course)

            pages_fetched += 1
            # Las páginas siguientes vienen como URL absoluta en pagination.next
            url = (data.get('pagination') or {}).get('next')
            params = None

    return courses_by_id, full_success


def sync_courses(force=False):
    """Sincroniza la tabla open_learning_course con la API.

    Upsert que preserva las decisiones de curación:
    - curso nuevo -> fila 'pending' con tipo auto-detectado
    - curso existente -> actualiza datos de display, last_seen_at y
      reactiva is_available; recalcula tipo solo sin override admin
    - cursos ausentes -> is_available=False, SOLO si el fetch fue completo
    Nunca toca status ni display_order de filas existentes.
    """
    init_open_learning_courses_db()

    sync_started_at = datetime.datetime.utcnow()
    courses_by_id, full_success = _fetch_all_courses(_get_search_terms())

    summary = {
        'created': 0,
        'updated': 0,
        'marked_unavailable': 0,
        'total_api': len(courses_by_id),
        'full_success': full_success,
    }

    if not courses_by_id:
        # API caída o sin resultados: no tocamos nada en BD
        log.warning(u'Open Learning: sync sin resultados de la API, BD intacta')
        return summary

    try:
        for course_id, api_course in courses_by_id.items():
            name = (api_course.get('name') or u'').strip()
            if not name:
                continue
            media = api_course.get('media') or {}
            image_url = ((media.get('image') or {}).get('raw')) or u''
            fields = {
                'name': name,
                'org': api_course.get('org') or u'',
                'short_description': api_course.get('short_description') or u'',
                'image_url': image_url,
                'start': _parse_iso_datetime(api_course.get('start')),
                'end': _parse_iso_datetime(api_course.get('end')),
                'start_display': api_course.get('start_display') or u'',
                'pacing': api_course.get('pacing') or u'',
                'raw_json': json.dumps(api_course, ensure_ascii=False),
            }

            existing = OpenLearningCourse.get_by_course_id(course_id)
            if existing is None:
                course = OpenLearningCourse(
                    course_id=course_id,
                    course_type=_detect_course_type(api_course),
                    **fields
                )
                meta.Session.add(course)
                summary['created'] += 1
            else:
                for attr, value in fields.items():
                    setattr(existing, attr, value)
                existing.last_seen_at = sync_started_at
                existing.updated_at = sync_started_at
                existing.is_available = True
                if not existing.course_type_override:
                    existing.course_type = _detect_course_type(api_course)
                summary['updated'] += 1

        if full_success:
            # Cursos que ya no aparecen en la API: marcarlos no disponibles
            # (sin borrarlos, para conservar la curación si reaparecen)
            missing = meta.Session.query(OpenLearningCourse).filter(
                OpenLearningCourse.last_seen_at < sync_started_at,
                OpenLearningCourse.is_available == True,  # noqa: E712
            ).all()
            for course in missing:
                course.is_available = False
                course.updated_at = sync_started_at
                summary['marked_unavailable'] += 1

        meta.Session.commit()
    except Exception as e:
        meta.Session.rollback()
        log.error(u'Open Learning: error en upsert del sync: %s', e)
        raise

    log.info(
        u'Open Learning sync: %(created)d nuevos, %(updated)d actualizados, '
        u'%(marked_unavailable)d no disponibles (api=%(total_api)d, '
        u'completo=%(full_success)s)', summary)
    return summary


def maybe_sync_courses():
    """Gatillo lazy: sincroniza solo si pasó el TTL desde el último sync.

    Pensado para llamarse desde helpers/vistas en cada request: jamás lanza
    excepción ni bloquea el render más allá del fetch con timeout corto.
    """
    try:
        sync_ttl = _get_config_int(
            'ckanext.theme_ejemplo.openlearning_sync_ttl', 21600)
        if sync_ttl <= 0:
            return

        now = time.time()
        if now - _last_sync_attempt['time'] < _SYNC_ATTEMPT_COOLDOWN:
            return

        init_open_learning_courses_db()
        last_sync = OpenLearningCourse.last_sync_at()
        if last_sync is not None:
            age = (datetime.datetime.utcnow() - last_sync).total_seconds()
            if age < sync_ttl:
                return

        # Evitar dos syncs simultáneos en el mismo worker
        if not _sync_lock.acquire(False):
            return
        try:
            _last_sync_attempt['time'] = now
            sync_courses()
        finally:
            _sync_lock.release()
    except Exception as e:
        log.warning(u'Open Learning: sync lazy falló (se sirve la BD): %s', e)
