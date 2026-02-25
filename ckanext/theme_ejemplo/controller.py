from random import random
from flask import render_template, abort
import ckan.plugins.toolkit as toolkit
import ckan.model as model
import ckan.logic as logic
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.lib.navl.dictization_functions as dict_fns
import ckan.lib.search as search
import ckan.authz as authz
import ckan.plugins as plugins
import ckan.lib.mailer as mailer
from ckan.common import c, config, request, _, current_user
from functools import lru_cache
import time
import json
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
                    q = c.q = request.args.get('q', '')
                    sort_by = c.sort_by_selected = request.args.get('sort')
                    page = h.get_page_number(request.args) or 1
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
                    q = c.q = request.args.get('q', '')
                    sort_by = c.sort_by_selected = request.args.get('sort')
                    page = h.get_page_number(request.args) or 1
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

        # --- People & Organizations views ---

        def people_index():
            """People directory page."""
            q = request.args.get('q', '')
            country = request.args.get('country', '')
            organization = request.args.get('organization', '')
            expertise = request.args.get('expertise', '')
            page = h.get_page_number(request.args) or 1
            items_per_page = 21

            try:
                result = toolkit.get_action('people_list')(
                    {'ignore_auth': True},
                    {
                        'q': q,
                        'country': country,
                        'organization': organization,
                        'expertise': expertise,
                        'limit': items_per_page,
                        'offset': items_per_page * (page - 1),
                    }
                )

                people = result.get('results', [])
                total = result.get('count', 0)

                # Get filter options
                orgs = toolkit.get_action('organization_list')(
                    {'ignore_auth': True},
                    {'all_fields': True, 'sort': 'title asc'}
                )

                from ckanext.theme_ejemplo.helpers import get_country_list
                countries = get_country_list()

                # Build pagination
                dummy_collection = range(total)
                pager = h.Page(
                    collection=dummy_collection,
                    page=page,
                    url=h.pager_url,
                    items_per_page=items_per_page,
                )
                pager.items = people

                return render_template(
                    "people/index.html",
                    people=people,
                    page=pager,
                    q=q,
                    country=country,
                    organization=organization,
                    expertise=expertise,
                    organizations=orgs,
                    countries=countries,
                    total=total,
                )
            except Exception as e:
                log.error(f"Error in people_index: {e}")
                return render_template(
                    "people/index.html",
                    people=[],
                    page=h.Page(collection=[], page=1, url=h.pager_url, items_per_page=items_per_page),
                    q=q, country='', organization='', expertise='',
                    organizations=[], countries=[], total=0,
                )

        def organization_people(name):
            """Organization people tab."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name, 'include_users': True}
                )
                result = toolkit.get_action('organization_people')(
                    context, {'id': name}
                )
                members = result.get('members', [])

                return render_template(
                    "organization/people.html",
                    group_dict=org,
                    group_type='organization',
                    members=members,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
            except Exception as e:
                log.error(f"Error in organization_people: {e}")
                abort(500)

        def organization_publications(name):
            """Organization publications tab."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name}
                )

                page = h.get_page_number(request.args) or 1
                items_per_page = 20

                pub_search = toolkit.get_action('package_search')(
                    {},
                    {
                        'fq': f'owner_org:{org["id"]} AND (dcat_type:*document* OR dcat_type:*publication*)',
                        'rows': items_per_page,
                        'start': items_per_page * (page - 1),
                        'sort': 'metadata_modified desc',
                    }
                )

                publications = pub_search.get('results', [])
                total = pub_search.get('count', 0)

                pager = h.Page(
                    collection=range(total),
                    page=page,
                    url=h.pager_url,
                    items_per_page=items_per_page,
                )
                pager.items = publications

                return render_template(
                    "organization/publications.html",
                    group_dict=org,
                    group_type='organization',
                    publications=publications,
                    page=pager,
                    total=total,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
            except Exception as e:
                log.error(f"Error in organization_publications: {e}")
                abort(500)

        def organization_news(name):
            """Organization news tab."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name}
                )

                # Try to get pages tagged with org name
                news = []
                try:
                    pages = toolkit.get_action('ckanext_pages_list')(
                        context, {'page_type': 'page'}
                    )
                    org_name = org.get('name', '')
                    for p in pages:
                        extras = p.get('extras', {})
                        page_org = extras.get('organization', '') if isinstance(extras, dict) else ''
                        if page_org == org_name or org_name in p.get('name', ''):
                            news.append(p)
                except Exception:
                    pass

                return render_template(
                    "organization/news.html",
                    group_dict=org,
                    group_type='organization',
                    news=news,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
            except Exception as e:
                log.error(f"Error in organization_news: {e}")
                abort(500)

        def organization_events(name):
            """Organization events tab."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name}
                )

                events = []
                try:
                    pages = toolkit.get_action('ckanext_pages_list')(
                        context, {'page_type': 'page'}
                    )
                    org_name = org.get('name', '')
                    for p in pages:
                        extras = p.get('extras', {})
                        page_org = extras.get('organization', '') if isinstance(extras, dict) else ''
                        page_type = extras.get('type', '') if isinstance(extras, dict) else ''
                        if (page_org == org_name or org_name in p.get('name', '')) and page_type == 'event':
                            events.append(p)
                except Exception:
                    pass

                return render_template(
                    "organization/events.html",
                    group_dict=org,
                    group_type='organization',
                    events=events,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
            except Exception as e:
                log.error(f"Error in organization_events: {e}")
                abort(500)

        def request_membership(name):
            """Handle membership request for an organization."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name, 'include_users': True}
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
                return

            if not current_user.is_authenticated:
                return toolkit.redirect_to('user.login')

            if request.method == 'POST':
                message = request.form.get('message', '')
                user_name = current_user.name
                user_fullname = current_user.fullname or current_user.name

                # Find org admins to notify
                admins = [u for u in org.get('users', []) if u.get('capacity') == 'admin']

                for admin in admins:
                    try:
                        admin_obj = model.User.get(admin['id'])
                        if admin_obj and admin_obj.email:
                            subject = _('Membership Request for {org}').format(org=org.get('title', org['name']))
                            body = _(
                                'User {user} ({fullname}) has requested to join the organization "{org}".\n\n'
                                'Message:\n{message}\n\n'
                                'To manage members, visit: {url}'
                            ).format(
                                user=user_name,
                                fullname=user_fullname,
                                org=org.get('title', org['name']),
                                message=message or _('No message provided'),
                                url=toolkit.url_for('organization.member_new', id=org['name'], qualified=True),
                            )
                            try:
                                mailer.mail_user(admin_obj, subject, body)
                            except Exception as mail_err:
                                log.warning(f"Failed to send membership request email: {mail_err}")
                    except Exception as e:
                        log.warning(f"Error notifying admin {admin.get('id')}: {e}")

                h.flash_success(
                    _('Your membership request for "{org}" has been sent to the organization administrators.').format(
                        org=org.get('title', org['name'])
                    )
                )
                return toolkit.redirect_to('organization.read', id=name)

            return render_template(
                "organization/request_membership.html",
                group_dict=org,
                group_type='organization',
            )
