# =============================================================================
# AI for Water Management: diseño propio para las páginas de un grupo
# Added by Jorgen Van Der Biest (UNESCO-IHP, IHP-WINS), October 2026.
#
# Todo el código de este diseño está en este módulo, en templates/ai_water_portal/,
# templates/group/read.html, public/css/ai-water.css, public/js/ai-water.js y
# public/ai_water/. En los ficheros existentes solo se añaden unas pocas líneas,
# marcadas con "AI for Water Management (added by Jorgen Van Der Biest)":
#   plugin.py                     import de este módulo y registro de helpers
#   templates/group/read_base.html  bloques styles y content (solo para los
#                                   grupos de GROUP_LANDINGS; los demás grupos
#                                   no cambian)
# =============================================================================
import logging

import ckan.plugins.toolkit as toolkit
from ckan.common import request

from ckanext.theme_ejemplo.controller import (
    _get_data_stories_by_group,
    _get_pages_by_initiative,
)

log = logging.getLogger(__name__)


# Grupos con un diseño propio en todas sus páginas /group/<name>/... (ver
# templates/group/read.html y group/read_base.html). Para cada grupo:
#   overview  plantilla de la portada, que sustituye a la lista de datasets
#             en /group/<name> cuando la URL no lleva parámetros (con ?q=,
#             filtros o paginación se mantiene la lista estándar de CKAN)
#   header    cabecera común (migas, menú y título de sección)
#   intros    contenido que se añade encima de una pestaña, por endpoint
#   replace   contenido que sustituye al de una pestaña, por endpoint
# Las URLs son las de siempre: no se crea ninguna ruta nueva.
GROUP_LANDINGS = {
    'artificial-intelligence-for-water-management': {
        'overview': 'ai_water_portal/landing.html',
        'header': 'ai_water_portal/snippets/header.html',
        'intros': {
            'theme_ejemplo.group_members': 'ai_water_portal/partners_body.html',
            'group.read': 'ai_water_portal/hub_datasets_intro.html',
            'theme_ejemplo.group_data_stories': 'ai_water_portal/hub_stories_intro.html',
            'theme_ejemplo.group_publications': 'ai_water_portal/hub_documents_intro.html',
        },
        'replace': {
            'theme_ejemplo.group_news': 'ai_water_portal/news_events.html',
        },
    },
}


def group_landing(group_dict):
    """Configuración de diseño propio del grupo (dict) o None.

    Añade a la configuración:
      has_filters  True si la URL lleva parámetros (búsqueda, filtros, página)
    """
    try:
        conf = GROUP_LANDINGS.get((group_dict or {}).get('name'))
        if not conf:
            return None
        conf = dict(conf)
        conf['has_filters'] = bool(request.args)
        return conf
    except Exception as e:
        log.warning(f"group_landing error: {e}")
        return None


def group_pages(group_name, page_type):
    """Páginas (water-news, water-events...) asociadas a un grupo."""
    try:
        return _get_pages_by_initiative(group_name, page_type=page_type)
    except Exception as e:
        log.warning(f"group_pages error ({group_name}, {page_type}): {e}")
        return []


def group_landing_data(group_dict):
    """Contenido del grupo para su portada: datasets, documentos,
    noticias, eventos y data stories (los más recientes de cada uno)."""
    name = group_dict['name']

    def _search(fq, rows):
        try:
            return toolkit.get_action('package_search')(
                {'ignore_auth': True},
                {'fq': fq, 'rows': rows, 'sort': 'metadata_modified desc'}
            )
        except Exception as e:
            log.warning(f"Error buscando paquetes ({fq}) para {name}: {e}")
            return {'count': 0, 'results': []}

    datasets = _search(f'groups:{name} -type:documents -type:learning', 5)
    documents = _search(f'groups:{name} +type:documents', 5)

    news, events = [], []
    try:
        news = _get_pages_by_initiative(name, page_type='water-news')
        events = _get_pages_by_initiative(name, page_type='water-events')
    except Exception as e:
        log.warning(f"Error obteniendo páginas para el grupo {name}: {e}")

    return {
        'datasets': datasets.get('results', []),
        'datasets_count': datasets.get('count', 0),
        'documents': documents.get('results', []),
        'documents_count': documents.get('count', 0),
        'news': news[:3],
        'news_count': len(news),
        'events': events[:3],
        'events_count': len(events),
        'stories': _get_data_stories_by_group(group_dict['id'], limit=3),
    }


def get_helpers():
    """Helpers de plantilla de este módulo (se registran en plugin.py)."""
    return {
        'theme_ejemplo_group_landing': group_landing,
        'theme_ejemplo_group_pages': group_pages,
        'theme_ejemplo_group_landing_data': group_landing_data,
    }
