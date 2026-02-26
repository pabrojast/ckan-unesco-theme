from random import random
from flask import render_template, abort, jsonify
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
                priority_areas = {}
                for pa_num in range(1, 6):
                    pa_key = 'PA{}'.format(pa_num)
                    try:
                        result = toolkit.get_action('package_search')(
                            {'ignore_auth': True},
                            {
                                'fq': 'ihpix_priority_area:{}'.format(pa_key),
                                'sort': 'metadata_created desc',
                                'rows': 3,
                            }
                        )
                        priority_areas[pa_key] = result.get('results', [])
                    except Exception:
                        priority_areas[pa_key] = []

                return render_template("ihpix/index.html",
                                       priority_areas=priority_areas)

        def ihpix_outputs():
            if request.method == 'GET':
                pa_filter = request.args.get('pa', '')
                q = request.args.get('q', '')
                page = int(request.args.get('page', 1))
                items_per_page = 20

                fq_parts = []
                if pa_filter:
                    fq_parts.append('ihpix_priority_area:{}'.format(pa_filter))
                else:
                    fq_parts.append('ihpix_priority_area:[* TO *]')

                try:
                    result = toolkit.get_action('package_search')(
                        {'ignore_auth': True},
                        {
                            'q': q,
                            'fq': ' AND '.join(fq_parts),
                            'sort': 'metadata_created desc',
                            'rows': items_per_page,
                            'start': items_per_page * (page - 1),
                            'facet.field': ['ihpix_priority_area', 'ihpix_output'],
                            'facet': 'true',
                        }
                    )
                    activities = result.get('results', [])
                    facets = result.get('search_facets', {})
                    total = result.get('count', 0)
                except Exception as e:
                    log.error('Error fetching IHP-IX outputs: %s', e)
                    activities = []
                    facets = {}
                    total = 0

                return render_template("ihpix/outputs.html",
                                       activities=activities,
                                       facets=facets,
                                       total=total,
                                       pa_filter=pa_filter,
                                       q=q,
                                       page=page,
                                       items_per_page=items_per_page)

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
                    context, {'id': name}
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
                return

            if not current_user.is_authenticated:
                return toolkit.redirect_to('user.login')

            # Check if already a member
            try:
                members = toolkit.get_action('member_list')(
                    {'ignore_auth': True},
                    {'id': org['id'], 'object_type': 'user'}
                )
                if any(m[0] == current_user.id for m in members):
                    h.flash_notice(
                        _('You are already a member of "{org}".').format(
                            org=org.get('title', org['name'])
                        )
                    )
                    return toolkit.redirect_to('organization.read', id=name)
            except Exception:
                members = []

            if request.method == 'POST':
                message = request.form.get('message', '')
                user_name = current_user.name
                user_fullname = current_user.fullname or current_user.name

                # Find org admins via member_list (include_users is empty in CKAN 2.10)
                admins_notified = 0
                for member_id, _obj_type, capacity in members:
                    if capacity == 'admin':
                        try:
                            admin_obj = model.User.get(member_id)
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
                                    admins_notified += 1
                                except Exception as mail_err:
                                    log.warning(f"Failed to send membership request email: {mail_err}")
                        except Exception as e:
                            log.warning(f"Error notifying admin {member_id}: {e}")

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

        # --- User profile tab views ---

        def _get_user_context(id):
            """Shared helper to load user data for profile tabs."""
            context = {'ignore_auth': True}
            user_dict = toolkit.get_action('user_show')(context, {'id': id, 'include_plugin_extras': True})
            is_myself = hasattr(current_user, 'name') and current_user.name == user_dict['name']
            is_sysadmin = hasattr(current_user, 'sysadmin') and current_user.sysadmin
            return user_dict, is_myself, is_sysadmin

        def user_documents(id):
            """User documents tab."""
            try:
                user_dict, is_myself, is_sysadmin = MyLogica._get_user_context(id)
                page = h.get_page_number(request.args) or 1
                items_per_page = 21

                fq = 'creator_user_id:{} AND type:documents'.format(user_dict['id'])
                result = toolkit.get_action('package_search')(
                    {'ignore_auth': True},
                    {
                        'fq': fq,
                        'rows': items_per_page,
                        'start': items_per_page * (page - 1),
                        'sort': 'metadata_modified desc',
                    }
                )
                documents = result.get('results', [])
                total = result.get('count', 0)

                pager = h.Page(
                    collection=range(total),
                    page=page,
                    url=h.pager_url,
                    items_per_page=items_per_page,
                )
                pager.items = documents

                return render_template(
                    "user/documents.html",
                    user_dict=user_dict,
                    documents=documents,
                    page=pager,
                    total=total,
                    is_myself=is_myself,
                    is_sysadmin=is_sysadmin,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('User not found'))
            except Exception as e:
                log.error(f"Error in user_documents: {e}")
                abort(500)

        def user_organizations(id):
            """User organizations tab."""
            try:
                user_dict, is_myself, is_sysadmin = MyLogica._get_user_context(id)

                orgs = toolkit.get_action('organization_list_for_user')(
                    {'ignore_auth': True},
                    {'id': user_dict['id'], 'permission': 'read'}
                )

                return render_template(
                    "user/organizations.html",
                    user_dict=user_dict,
                    organizations=orgs,
                    is_myself=is_myself,
                    is_sysadmin=is_sysadmin,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('User not found'))
            except Exception as e:
                log.error(f"Error in user_organizations: {e}")
                abort(500)

        def user_data_stories(id):
            """User data stories tab."""
            try:
                user_dict, is_myself, is_sysadmin = MyLogica._get_user_context(id)

                stories = []
                try:
                    result = toolkit.get_action('data_story_list')(
                        {'ignore_auth': True},
                        {'author_id': user_dict['id'], 'limit': 50}
                    )
                    stories = result.get('stories', [])
                except Exception as e:
                    log.warning(f"Error fetching data stories for user {id}: {e}")

                return render_template(
                    "user/data_stories.html",
                    user_dict=user_dict,
                    stories=stories,
                    is_myself=is_myself,
                    is_sysadmin=is_sysadmin,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('User not found'))
            except Exception as e:
                log.error(f"Error in user_data_stories: {e}")
                abort(500)

        def user_news(id):
            """User news tab (water-news from pages plugin)."""
            try:
                user_dict, is_myself, is_sysadmin = MyLogica._get_user_context(id)

                news = []
                try:
                    from ckanext.pages.db import Page
                    pages = model.Session.query(Page).filter(
                        Page.user_id == user_dict['id'],
                        Page.page_type == 'water-news',
                    ).order_by(Page.created.desc()).all()
                    for pg in pages:
                        news.append({
                            'title': pg.title,
                            'name': pg.name,
                            'content': pg.content,
                            'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                            'created': pg.created.isoformat() if pg.created else None,
                            'page_type': pg.page_type,
                        })
                except Exception as e:
                    log.warning(f"Error fetching news for user {id}: {e}")

                return render_template(
                    "user/news.html",
                    user_dict=user_dict,
                    news=news,
                    is_myself=is_myself,
                    is_sysadmin=is_sysadmin,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('User not found'))
            except Exception as e:
                log.error(f"Error in user_news: {e}")
                abort(500)

        @staticmethod
        def dataset_resources_ajax(id):
            """AJAX endpoint for paginated/filtered resource list."""
            page = request.args.get('page', 1, type=int)
            items_per_page = request.args.get('limit', 20, type=int)
            q = request.args.get('q', '').strip()
            format_filter = request.args.get('format', '').strip()

            items_per_page = min(items_per_page, 100)

            try:
                pkg = toolkit.get_action('package_show')({}, {'id': id})
                can_edit = h.check_access('package_update', {'id': pkg['id']})
            except toolkit.ObjectNotFound:
                abort(404)
            except Exception:
                pkg = {'id': id, 'name': id, 'type': 'dataset'}
                can_edit = False

            # Filter and paginate from already-loaded resources
            resources = pkg.get('resources', [])
            all_formats = sorted(set(
                (r.get('format') or '').strip()
                for r in resources
                if (r.get('format') or '').strip()
            ), key=str.lower)

            if q:
                q_lower = q.lower()
                resources = [
                    r for r in resources
                    if q_lower in (r.get('name') or '').lower()
                    or q_lower in (r.get('description') or '').lower()
                    or q_lower in (r.get('url') or '').lower()
                ]
            if format_filter:
                fmt_lower = format_filter.lower()
                resources = [
                    r for r in resources
                    if (r.get('format') or '').lower() == fmt_lower
                ]

            total = len(resources)
            start = (page - 1) * items_per_page
            paged = resources[start:start + items_per_page]

            html = render_template(
                'package/snippets/resources_list_items.html',
                pkg=pkg,
                resources=paged,
                can_edit=can_edit,
            )

            return jsonify({
                'html': html,
                'total': total,
                'page': page,
                'items_per_page': items_per_page,
                'formats': all_formats,
            })
