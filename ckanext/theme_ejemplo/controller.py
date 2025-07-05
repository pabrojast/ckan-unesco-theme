from random import random
from flask import render_template, request, abort
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.search as search
import ckan.authz as authz
import ckan.plugins as plugins
from ckan.common import c, config, request, _
from functools import lru_cache
import time
import logging

log = logging.getLogger(__name__)
group_type = u'group'

# Cache con tiempo de expiración de 5 minutos
_cache_timestamp = {}

def timed_lru_cache(seconds: int, maxsize: int = 128):
    """LRU cache que expira después de un tiempo específico"""
    def decorator(func):
        cached_func = lru_cache(maxsize=maxsize)(func)
        
        def wrapper(*args, **kwargs):
            # Generar clave única para los argumentos
            cache_key = str(args) + str(kwargs)
            current_time = time.time()
            
            # Verificar si el cache ha expirado
            if cache_key in _cache_timestamp:
                if current_time - _cache_timestamp[cache_key] > seconds:
                    # Cache expirado, limpiar
                    cached_func.cache_clear()
                    _cache_timestamp.clear()
            
            # Actualizar timestamp y retornar resultado cacheado
            _cache_timestamp[cache_key] = current_time
            return cached_func(*args, **kwargs)
        
        wrapper.cache_clear = cached_func.cache_clear
        return wrapper
    return decorator

@timed_lru_cache(seconds=300, maxsize=10)  # Cache de 5 minutos
def get_member_states_groups():
    """Obtiene los grupos hijos de member-states con cache"""
    try:
        member_states = toolkit.get_action('group_show')(
            data_dict={'id': 'member-states', 'include_groups': True}
        )
        group_names = [item['name'] for item in member_states.get("groups", [])]
        group_names.append('member-states')  # Añadir el grupo principal
        return group_names
    except Exception as e:
        log.error(f"Error obteniendo member-states: {e}")
        return ['member-states']  # Retornar al menos el grupo principal

@timed_lru_cache(seconds=300, maxsize=20)  # Cache de 5 minutos
def get_all_groups_cached(sort_by=None):
    """Obtiene todos los grupos con cache"""
    try:
        return toolkit.get_action('group_list')(
            data_dict={'include_dataset_count': True, 'sort': sort_by}
        )
    except Exception as e:
        log.error(f"Error obteniendo lista de grupos: {e}")
        return []

class MyLogica():  
        
        def initiatives():
            if request.method == 'GET':
                try:
                    # Obtener parámetros
                    q = c.q = request.params.get('q', '')
                    sort_by = c.sort_by_selected = request.params.get('sort')
                    page = h.get_page_number(request.params) or 1
                    items_per_page = 21
                    
                    # Obtener grupos de member-states desde cache
                    member_states_groups = get_member_states_groups()
                    
                    # Obtener todos los grupos desde cache
                    all_groups = get_all_groups_cached(sort_by)
                    
                    # Calcular grupos de iniciativas (excluyendo member-states)
                    initiatives_groups = list(set(all_groups) - set(member_states_groups))
                    
                    # Si hay búsqueda, filtrar los grupos
                    if q:
                        # Hacer una sola consulta con todos los filtros
                        groups_result = toolkit.get_action('group_list')(
                            data_dict={
                                'q': q,
                                'include_dataset_count': True,
                                'all_fields': True,
                                'groups': initiatives_groups,
                                'include_groups': True,
                                'limit': items_per_page,
                                'offset': items_per_page * (page - 1),
                                'sort': sort_by
                            }
                        )
                        
                        # Para el conteo total con búsqueda
                        total_result = toolkit.get_action('group_list')(
                            data_dict={
                                'q': q,
                                'include_dataset_count': True,
                                'groups': initiatives_groups,
                                'limit': 500
                            }
                        )
                        groupcount = len(total_result)
                    else:
                        # Sin búsqueda, usar los datos cacheados y paginar manualmente
                        groupcount = len(initiatives_groups)
                        start = items_per_page * (page - 1)
                        end = start + items_per_page
                        
                        # Obtener detalles completos solo para la página actual
                        page_groups = initiatives_groups[start:end]
                        groups_result = toolkit.get_action('group_list')(
                            data_dict={
                                'include_dataset_count': True,
                                'all_fields': True,
                                'groups': page_groups,
                                'include_groups': True,
                                'limit': items_per_page,
                                'sort': sort_by
                            }
                        )
                    
                    # Configurar paginación
                    c.page = h.Page(
                        collection=initiatives_groups,
                        page=page,
                        url=h.pager_url,
                        items_per_page=items_per_page,
                    )
                    c.page.items = groups_result
                    
                    return render_template("initiatives/index.html", 
                                         q=q, 
                                         page=c.page, 
                                         groups=groups_result, 
                                         group_type=group_type, 
                                         groupcount=groupcount)
                    
                except Exception as e:
                    log.error(f"Error en initiatives: {e}")
                    # En caso de error, retornar página vacía
                    c.page = h.Page(
                        collection=[],
                        page=1,
                        url=h.pager_url,
                        items_per_page=items_per_page,
                    )
                    return render_template("initiatives/index.html", 
                                         q='', 
                                         page=c.page, 
                                         groups=[], 
                                         group_type=group_type, 
                                         groupcount=0)
        @staticmethod
        def redirect_to_group(name):
            """Redirige /paises/<nombre> a /group/<nombre>."""
            return toolkit.redirect_to('/group/{}'.format(name))
#        Deshabilita el registro de usuarios
#       @staticmethod
#       def redirect_to_colab():
#           """Redirige user/register a /colab."""
#           return toolkit.redirect_to('/colab')
            
        def memberstates():
            if request.method == 'GET':
                try:
                    # Obtener parámetros
                    q = c.q = request.params.get('q', '')
                    sort_by = c.sort_by_selected = request.params.get('sort')
                    page = h.get_page_number(request.params) or 1
                    items_per_page = 21
                    
                    # Obtener grupos de member-states desde cache (sin incluir el principal)
                    member_states_groups = get_member_states_groups()
                    # Remover 'member-states' del listado ya que solo queremos los hijos
                    member_states_only = [g for g in member_states_groups if g != 'member-states']
                    
                    # Si hay búsqueda, hacer consulta filtrada
                    if q:
                        # Consulta paginada con búsqueda
                        groups_result = toolkit.get_action('group_list')(
                            data_dict={
                                'q': q,
                                'include_dataset_count': True,
                                'all_fields': True,
                                'groups': member_states_only,
                                'include_groups': True,
                                'limit': items_per_page,
                                'offset': items_per_page * (page - 1),
                                'sort': sort_by
                            }
                        )
                        
                        # Para el conteo total con búsqueda
                        total_result = toolkit.get_action('group_list')(
                            data_dict={
                                'q': q,
                                'include_dataset_count': True,
                                'groups': member_states_only,
                                'limit': 500
                            }
                        )
                        groupcount = len(total_result)
                    else:
                        # Sin búsqueda, usar cache y paginar manualmente
                        groupcount = len(member_states_only)
                        start = items_per_page * (page - 1)
                        end = start + items_per_page
                        
                        # Obtener detalles completos solo para la página actual
                        page_groups = member_states_only[start:end]
                        if page_groups:
                            groups_result = toolkit.get_action('group_list')(
                                data_dict={
                                    'include_dataset_count': True,
                                    'all_fields': True,
                                    'groups': page_groups,
                                    'include_groups': True,
                                    'limit': items_per_page,
                                    'sort': sort_by
                                }
                            )
                        else:
                            groups_result = []
                    
                    # Configurar paginación
                    c.page = h.Page(
                        collection=member_states_only,
                        page=page,
                        url=h.pager_url,
                        items_per_page=items_per_page,
                    )
                    c.page.items = groups_result
                    
                    return render_template("memberstates/index.html", 
                                         q=q, 
                                         page=c.page, 
                                         groups=groups_result, 
                                         group_type=group_type, 
                                         groupcount=groupcount)
                    
                except Exception as e:
                    log.error(f"Error en memberstates: {e}")
                    # En caso de error, retornar página vacía
                    c.page = h.Page(
                        collection=[],
                        page=1,
                        url=h.pager_url,
                        items_per_page=items_per_page,
                    )
                    return render_template("memberstates/index.html", 
                                         q='', 
                                         page=c.page, 
                                         groups=[], 
                                         group_type=group_type, 
                                         groupcount=0)
        
        def thematicbuilder():
            
            if request.method == 'GET':
                #you will get something like
                #[{'approval_status': 'approved', 'created': '2023-11-15T17:04:44.712875', 'description': '', 'display_name': 'ukgov', 'id': 'ff5b411d-dedd-4560-ac93-b59621644e61', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'ukgov', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.713652', 'description': '', 'display_name': 'test1', 'id': 'c1738e32-ced0-41dd-bb7d-251df5aa46b1', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test1', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714297', 'description': '', 'display_name': 'test2', 'id': 'cc89cb78-cfb1-47ff-9f17-e9551fa0f1ac', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test2', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714706', 'description': '', 'display_name': 'penguin', 'id': '9670daa2-0b07-4a8a-87e4-6313400c40df', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'penguin', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.152620', 'description': 'These are books that David likes.', 'display_name': "Dave's books", 'id': '4f25f1e7-48c9-4bc0-81f7-044a91b8d527', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'david', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Dave's books", 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.153429', 'description': 'Roger likes these books.', 'display_name': "Roger's books", 'id': 'ff2f73ff-dff5-4de6-8f46-efc5dc44cd43', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'roger', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Roger's books", 'type': 'group'}]
                return render_template("thematicbuilder/index.html")

        def ihpix():
            
            if request.method == 'GET':
                return render_template("ihpix/index.html")

        def iot_portal():
            
            if request.method == 'GET':
                return render_template("iot_portal/index.html")

        def flood_drought_portal():
            
            if request.method == 'GET':
                return render_template("flood_drought_portal/index.html")

        def citizen_science_portal():
            
            if request.method == 'GET':
                return render_template("citizen_science_portal/index.html")