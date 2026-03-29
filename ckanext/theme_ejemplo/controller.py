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
from ckanext.theme_ejemplo.utils import normalize_user_image_url

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
    """Obtiene los grupos hijos de member-states con cache.
    Uses a direct DB query to avoid N+1 overhead from group_show(include_groups=True).
    """
    try:
        ms_group = model.Group.get('member-states')
        if not ms_group:
            return ['member-states']
        members = (
            model.Session.query(model.Group.name)
            .join(model.Member, model.Member.table_id == model.Group.id)
            .filter(
                model.Member.group_id == ms_group.id,
                model.Member.state == 'active',
                model.Member.table_name == 'group',
                model.Group.state == 'active',
            )
            .all()
        )
        group_names = [g.name for g in members if g.name]
        group_names.append('member-states')
        return group_names
    except Exception as e:
        log.error(f"Error obteniendo member-states: {e}")
        return ['member-states']

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

def _get_pages_by_initiative(initiative_name, page_type=None):
    """Query pages associated with an initiative via the initiative_groups extras field."""
    try:
        from ckanext.pages.db import Page
        search_pattern = '"%s"' % initiative_name
        query = model.Session.query(Page).filter(
            Page.extras.like('%' + search_pattern + '%')
        )
        if page_type:
            query = query.filter(Page.page_type == page_type)
        else:
            query = query.filter(
                Page.page_type.in_(['water-news', 'water-events', 'water-publications'])
            )
        query = query.order_by(Page.created.desc())
        results = []
        for pg in query.all():
            extras = {}
            if pg.extras:
                try:
                    extras = json.loads(pg.extras)
                except (ValueError, TypeError):
                    pass
            initiative_groups = extras.get('initiative_groups', '[]')
            if isinstance(initiative_groups, str):
                try:
                    initiative_groups = json.loads(initiative_groups)
                except (ValueError, TypeError):
                    initiative_groups = []
            names = [g.get('name', '') if isinstance(g, dict) else str(g)
                     for g in initiative_groups]
            if initiative_name not in names:
                continue
            page_dict = {
                'title': pg.title,
                'name': pg.name,
                'content': pg.content,
                'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                'created': pg.created.isoformat() if pg.created else None,
                'page_type': pg.page_type,
            }
            page_dict.update(extras)
            results.append(page_dict)
        return results
    except Exception as e:
        log.warning(f"_get_pages_by_initiative error: {e}")
        return []


def _get_pages_by_organization(org_id, page_type=None):
    """Query pages associated with an organization via the organization_id extras field."""
    try:
        from ckanext.pages.db import Page
        query = model.Session.query(Page).filter(
            Page.extras.like('%"organization_id"%'),
            Page.extras.like(f'%{org_id}%')
        )
        if page_type:
            query = query.filter(Page.page_type == page_type)
        else:
            query = query.filter(
                Page.page_type.in_(['water-news', 'water-events', 'water-publications'])
            )
        query = query.order_by(Page.created.desc())
        results = []
        for pg in query.all():
            extras = {}
            if pg.extras:
                try:
                    extras = json.loads(pg.extras)
                except (ValueError, TypeError):
                    pass
            if extras.get('organization_id') != org_id:
                continue
            page_dict = {
                'title': pg.title,
                'name': pg.name,
                'content': pg.content,
                'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                'created': pg.created.isoformat() if pg.created else None,
                'page_type': pg.page_type,
            }
            page_dict.update(extras)
            results.append(page_dict)
        return results
    except Exception as e:
        log.warning(f"_get_pages_by_organization error: {e}")
        return []


def _get_data_stories_by_group(group_id, limit=50):
    """Query data stories associated with a CKAN group or organization."""
    try:
        result = toolkit.get_action('data_story_list')(
            {'ignore_auth': True},
            {
                'organization_id': group_id,
                'limit': limit,
                'sort': 'recent',
            }
        )
        return result.get('stories', [])
    except Exception as e:
        log.warning(f"Error fetching data stories for group {group_id}: {e}")
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
                                'include_groups': False,
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
                                'include_groups': False,
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
                                'include_groups': False,
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
                                    'include_groups': False,
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
                from ckanext.theme_ejemplo.model import (
                    IhpixContent, init_ihpix_content_db,
                    IhpixActivity, init_ihpix_activities_db,
                )
                init_ihpix_content_db()
                init_ihpix_activities_db()

                # Load page content from DB
                cta_cards = [item.as_dict() for item in
                             IhpixContent.get_by_type('cta_card')
                             if item.is_active]
                pa_sections = [item.as_dict() for item in
                               IhpixContent.get_by_type('priority_area')
                               if item.is_active]

                # Load recent activities per priority area
                priority_areas = {}
                for pa_num in range(1, 6):
                    pa_key = 'PA{}'.format(pa_num)
                    try:
                        activities = IhpixActivity.get_by_priority_area(
                            pa_key, status='published', limit=3
                        )
                        priority_areas[pa_key] = [a.as_dict() for a in activities]
                    except Exception:
                        priority_areas[pa_key] = []

                is_sysadmin = False
                try:
                    if c.userobj and c.userobj.sysadmin:
                        is_sysadmin = True
                except Exception:
                    pass

                return render_template("ihpix/index.html",
                                       cta_cards=cta_cards,
                                       pa_sections=pa_sections,
                                       priority_areas=priority_areas,
                                       is_sysadmin=is_sysadmin)

        def ihpix_outputs():
            if request.method == 'GET':
                from ckanext.theme_ejemplo.model import (
                    IhpixActivity, init_ihpix_activities_db,
                )
                init_ihpix_activities_db()

                pa_filter = request.args.get('pa', '')
                output_filter = request.args.get('output', '')
                q = request.args.get('q', '')
                page = int(request.args.get('page', 1))
                items_per_page = 20
                offset = items_per_page * (page - 1)

                try:
                    results, total = IhpixActivity.get_published(
                        priority_area=pa_filter or None,
                        output=output_filter or None,
                        q_text=q or None,
                        limit=items_per_page,
                        offset=offset,
                    )
                    activities = [a.as_dict() for a in results]
                    facets = IhpixActivity.get_facets()
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
                                       output_filter=output_filter,
                                       q=q,
                                       page=page,
                                       items_per_page=items_per_page)

        def iot_portal():
            if request.method == 'GET':
                from ckanext.theme_ejemplo.model import PortalCard, init_portal_cards_db
                init_portal_cards_db()
                cards = PortalCard.get_active_by_portal('iot')
                is_sysadmin = c.userobj and c.userobj.sysadmin
                return render_template("iot_portal/index.html",
                                       cards=[cd.as_dict() for cd in cards],
                                       is_sysadmin=is_sysadmin)

        def flood_drought_portal():
            if request.method == 'GET':
                from ckanext.theme_ejemplo.model import PortalCard, init_portal_cards_db
                init_portal_cards_db()
                cards = PortalCard.get_active_by_portal('flood_drought')
                is_sysadmin = c.userobj and c.userobj.sysadmin
                return render_template("flood_drought_portal/index.html",
                                       cards=[cd.as_dict() for cd in cards],
                                       is_sysadmin=is_sysadmin)

        def citizen_science_portal():
            if request.method == 'GET':
                from ckanext.theme_ejemplo.model import PortalCard, init_portal_cards_db
                init_portal_cards_db()
                cards = PortalCard.get_active_by_portal('citizen_science')
                is_sysadmin = c.userobj and c.userobj.sysadmin
                return render_template("citizen_science_portal/index.html",
                                       cards=[cd.as_dict() for cd in cards],
                                       is_sysadmin=is_sysadmin)

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
                try:
                    org_query = (
                        model.Session.query(model.Group.id, model.Group.name, model.Group.title)
                        .filter(model.Group.type == 'organization', model.Group.state == 'active')
                        .order_by(model.Group.title)
                        .all()
                    )
                    orgs = [{'id': o.id, 'name': o.name, 'title': o.title or o.name, 'display_name': o.title or o.name} for o in org_query]
                except Exception:
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
            """Organization publications tab — shows documents."""
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
                        'fq': f'owner_org:{org["id"]} AND (type:documents OR dcat_type:*marcgt*)',
                        'rows': items_per_page,
                        'start': items_per_page * (page - 1),
                        'sort': 'metadata_modified desc',
                    }
                )

                documents = pub_search.get('results', [])
                total = pub_search.get('count', 0)

                pager = h.Page(
                    collection=range(total),
                    page=page,
                    url=h.pager_url,
                    items_per_page=items_per_page,
                )
                pager.items = documents

                return render_template(
                    "organization/publications.html",
                    group_dict=org,
                    group_type='organization',
                    documents=documents,
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

                news = []
                try:
                    from ckanext.pages.db import Page
                    org_id = org.get('id', '')
                    pages = model.Session.query(Page).filter(
                        Page.page_type == 'water-news',
                        Page.ihp_organization == org_id,
                    ).order_by(Page.created.desc()).all()
                    for pg in pages:
                        news.append({
                            'title': pg.title,
                            'name': pg.name,
                            'content': pg.content,
                            'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                            'created': pg.created.isoformat() if pg.created else None,
                            'page_type': pg.page_type,
                            'image_url': pg.image_url if hasattr(pg, 'image_url') else None,
                        })
                except Exception as e:
                    log.warning(f"Error fetching news for org {name}: {e}")

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
                    from ckanext.pages.db import Page
                    org_id = org.get('id', '')
                    pages = model.Session.query(Page).filter(
                        Page.page_type == 'water-events',
                        Page.ihp_organization == org_id,
                    ).order_by(Page.created.desc()).all()
                    for pg in pages:
                        events.append({
                            'title': pg.title,
                            'name': pg.name,
                            'content': pg.content,
                            'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                            'created': pg.created.isoformat() if pg.created else None,
                            'page_type': pg.page_type,
                        })
                except Exception as e:
                    log.warning(f"Error fetching events for org {name}: {e}")

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

        def organization_data_stories(name):
            """Organization data stories tab."""
            try:
                context = {'ignore_auth': True}
                org = toolkit.get_action('organization_show')(
                    context, {'id': name}
                )

                stories = _get_data_stories_by_group(org['id'])

                return render_template(
                    "organization/data_stories.html",
                    group_dict=org,
                    group_type='organization',
                    stories=stories,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
            except Exception as e:
                log.error(f"Error in organization_data_stories: {e}")
                abort(500)

        def group_data_stories(name):
            """Group/member state/initiative data stories tab."""
            try:
                context = {'ignore_auth': True}
                group = toolkit.get_action('group_show')(
                    context, {'id': name}
                )

                stories = _get_data_stories_by_group(group['id'])

                return render_template(
                    "group/data_stories.html",
                    group_dict=group,
                    group_type='group',
                    stories=stories,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Group not found'))
            except Exception as e:
                log.error(f"Error in group_data_stories: {e}")
                abort(500)

        def group_members(name):
            """Group/Initiative members tab."""
            try:
                context = {'ignore_auth': True}
                group = toolkit.get_action('group_show')(
                    context, {'id': name}
                )

                member_tuples = toolkit.get_action('member_list')(
                    context, {'id': group['id'], 'object_type': 'user'}
                )

                members = []
                for user_id, _obj_type, capacity in member_tuples:
                    try:
                        user_obj = model.User.get(user_id)
                        if not user_obj or user_obj.state != 'active':
                            continue

                        extras = user_obj.plugin_extras or {}
                        profile = extras.get('theme_ejemplo', {})

                        expertise_areas = profile.get('expertise_areas', '[]')
                        if isinstance(expertise_areas, str):
                            try:
                                expertise_areas = json.loads(expertise_areas)
                            except (json.JSONDecodeError, TypeError):
                                expertise_areas = []

                        members.append({
                            'id': user_obj.id,
                            'name': user_obj.name,
                            'fullname': user_obj.fullname or user_obj.name,
                            'image_url': normalize_user_image_url(user_obj.image_url),
                            'job_title': profile.get('job_title', ''),
                            'institution': profile.get('institution', ''),
                            'country': profile.get('country', ''),
                            'expertise_areas': expertise_areas,
                            'capacity': capacity or 'member',
                        })
                    except Exception as e:
                        log.warning(f"Error getting user profile for {user_id}: {e}")

                return render_template(
                    "group/members.html",
                    group_dict=group,
                    group_type='group',
                    members=members,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Group not found'))
            except Exception as e:
                log.error(f"Error in group_members: {e}")
                abort(500)

        def group_news(name):
            """Group/Initiative news tab — shows water-news pages associated via initiative_groups."""
            try:
                context = {'ignore_auth': True}
                group = toolkit.get_action('group_show')(
                    context, {'id': name}
                )

                news = []
                try:
                    news = _get_pages_by_initiative(name, page_type='water-news')
                except Exception as e:
                    log.warning(f"Error fetching news for group {name}: {e}")

                return render_template(
                    "group/news.html",
                    group_dict=group,
                    group_type='group',
                    news=news,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Group not found'))
            except Exception as e:
                log.error(f"Error in group_news: {e}")
                abort(500)

        def group_events(name):
            """Group/Initiative events tab — shows water-events pages associated via initiative_groups."""
            try:
                context = {'ignore_auth': True}
                group = toolkit.get_action('group_show')(
                    context, {'id': name}
                )

                events = []
                try:
                    events = _get_pages_by_initiative(name, page_type='water-events')
                except Exception as e:
                    log.warning(f"Error fetching events for group {name}: {e}")

                return render_template(
                    "group/events.html",
                    group_dict=group,
                    group_type='group',
                    events=events,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Group not found'))
            except Exception as e:
                log.error(f"Error in group_events: {e}")
                abort(500)

        def group_publications(name):
            """Group/Initiative publications tab — shows documents associated with the group."""
            try:
                context = {'ignore_auth': True}
                group = toolkit.get_action('group_show')(
                    context, {'id': name}
                )

                datasets = []
                try:
                    result = toolkit.get_action('package_search')(
                        {'ignore_auth': True},
                        {
                            'fq': f'groups:{name} AND (type:documents OR dcat_type:*marcgt*)',
                            'rows': 50,
                            'sort': 'metadata_modified desc',
                        }
                    )
                    datasets = result.get('results', [])
                except Exception as e:
                    log.warning(f"Error fetching datasets for group {name}: {e}")

                return render_template(
                    "group/publications.html",
                    group_dict=group,
                    group_type='group',
                    datasets=datasets,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Group not found'))
            except Exception as e:
                log.error(f"Error in group_publications: {e}")
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

            # Check for existing pending request
            from ckanext.theme_ejemplo.model import MembershipRequest
            existing = MembershipRequest.get_pending_for_user_and_org(
                current_user.id, org['id']
            )
            if existing:
                h.flash_notice(
                    _('You already have a pending request for "{org}". Please wait for an administrator to review it.').format(
                        org=org.get('title', org['name'])
                    )
                )
                return toolkit.redirect_to('organization.read', id=name)

            if request.method == 'POST':
                message = request.form.get('message', '')
                user_name = current_user.name
                user_fullname = current_user.fullname or current_user.name

                # Persist the request
                try:
                    toolkit.get_action('membership_request_create')(
                        {'auth_user_obj': current_user, 'user': current_user.name},
                        {
                            'organization_id': org['id'],
                            'message': message,
                        }
                    )
                except toolkit.ValidationError as e:
                    h.flash_error(str(e))
                    return toolkit.redirect_to('organization.read', id=name)

                # Notify org admins via email
                for member_id, _obj_type, capacity in members:
                    if capacity == 'admin':
                        try:
                            admin_obj = model.User.get(member_id)
                            if admin_obj and admin_obj.email:
                                subject = _('Membership Request for {org}').format(org=org.get('title', org['name']))
                                body = _(
                                    'User {user} ({fullname}) has requested to join the organization "{org}".\n\n'
                                    'Message:\n{message}\n\n'
                                    'To review this request, visit: {url}'
                                ).format(
                                    user=user_name,
                                    fullname=user_fullname,
                                    org=org.get('title', org['name']),
                                    message=message or _('No message provided'),
                                    url=toolkit.url_for('theme_ejemplo.membership_requests', name=org['name'], qualified=True),
                                )
                                try:
                                    mailer.mail_user(admin_obj, subject, body)
                                except Exception as mail_err:
                                    log.warning(f"Failed to send membership request email: {mail_err}")
                        except Exception as e:
                            log.warning(f"Error notifying admin {member_id}: {e}")

                h.flash_success(
                    _('Your membership request for "{org}" has been sent. An administrator will review it shortly.').format(
                        org=org.get('title', org['name'])
                    )
                )
                return toolkit.redirect_to('organization.read', id=name)

            return render_template(
                "organization/request_membership.html",
                group_dict=org,
                group_type='organization',
            )

        @staticmethod
        def membership_requests(name):
            """Dashboard to manage membership requests for an organization."""
            if not current_user.is_authenticated:
                return toolkit.redirect_to('user.login')

            try:
                org = toolkit.get_action('organization_show')(
                    {'ignore_auth': True}, {'id': name}
                )
            except toolkit.ObjectNotFound:
                abort(404, _('Organization not found'))
                return

            # Check user is org admin or sysadmin
            is_admin = False
            if current_user.sysadmin:
                is_admin = True
            else:
                try:
                    members = toolkit.get_action('member_list')(
                        {'ignore_auth': True},
                        {'id': org['id'], 'object_type': 'user'}
                    )
                    is_admin = any(
                        m[0] == current_user.id and m[2] == 'admin'
                        for m in members
                    )
                except Exception:
                    pass

            if not is_admin:
                abort(403, _('Only organization administrators can manage membership requests.'))
                return

            tab = request.args.get('tab', 'pending')

            # Handle approve/reject POST
            if request.method == 'POST':
                action = request.form.get('action', '')
                request_id = request.form.get('request_id', '')
                admin_note = request.form.get('admin_note', '')
                role = request.form.get('role', 'member')

                if action in ('approve', 'reject') and request_id:
                    try:
                        toolkit.get_action('membership_request_process')(
                            {'auth_user_obj': current_user, 'user': current_user.name},
                            {
                                'id': request_id,
                                'action': action,
                                'admin_note': admin_note,
                                'role': role,
                            }
                        )
                        if action == 'approve':
                            h.flash_success(_('Membership request approved successfully.'))
                        else:
                            h.flash_success(_('Membership request rejected.'))
                    except Exception as e:
                        h.flash_error(str(e))

                return toolkit.redirect_to(
                    'theme_ejemplo.membership_requests', name=name, tab=tab
                )

            # Fetch requests — bypass auth since we verified admin above
            ctx = {'ignore_auth': True}
            try:
                pending = toolkit.get_action('membership_request_list')(
                    ctx, {'organization_id': org['id'], 'status': 'pending'}
                )
            except Exception as e:
                log.error(f"Error fetching pending membership requests: {e}")
                pending = {'results': [], 'count': 0}

            try:
                history = toolkit.get_action('membership_request_list')(
                    ctx, {'organization_id': org['id']}
                )
            except Exception as e:
                log.error(f"Error fetching membership request history: {e}")
                history = {'results': [], 'count': 0}
            # Filter history to only processed requests
            history_results = [
                r for r in history.get('results', [])
                if r['status'] != 'pending'
            ]

            return render_template(
                "organization/membership_requests.html",
                group_dict=org,
                group_type='organization',
                pending_requests=pending.get('results', []),
                pending_count=pending.get('count', 0),
                history_requests=history_results,
                active_tab=tab,
            )

        @staticmethod
        def membership_requests_overview():
            """Overview of pending membership requests across all orgs the user administers."""
            if not current_user.is_authenticated:
                return toolkit.redirect_to('user.login')

            from ckanext.theme_ejemplo.model import MembershipRequest

            # Get orgs where user is admin
            if current_user.sysadmin:
                # Sysadmins see all orgs with pending requests
                try:
                    org_rows = (
                        model.Session.query(
                            model.Group.id, model.Group.name, model.Group.title, model.Group.image_url
                        )
                        .filter(model.Group.type == 'organization', model.Group.state == 'active')
                        .all()
                    )
                    all_orgs = [
                        {'id': o.id, 'name': o.name, 'title': o.title or o.name,
                         'image_display_url': o.image_url or ''}
                        for o in org_rows
                    ]
                except Exception:
                    all_orgs = toolkit.get_action('organization_list')(
                        {'ignore_auth': True}, {'all_fields': True, 'limit': 1000}
                    )
            else:
                all_orgs = toolkit.get_action('organization_list_for_user')(
                    {'user': current_user.name},
                    {'permission': 'admin'}
                )

            orgs_with_requests = []
            for org in all_orgs:
                count = MembershipRequest.count_pending_for_orgs([org['id']])
                if count > 0:
                    orgs_with_requests.append({
                        'name': org['name'],
                        'title': org.get('title') or org['name'],
                        'image_display_url': org.get('image_display_url', ''),
                        'pending_count': count,
                    })

            # If only one org has requests, redirect directly
            if len(orgs_with_requests) == 1:
                return toolkit.redirect_to(
                    'theme_ejemplo.membership_requests',
                    name=orgs_with_requests[0]['name']
                )

            return render_template(
                "organization/membership_requests_overview.html",
                orgs_with_requests=orgs_with_requests,
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

                fq = 'creator_user_id:{} AND (type:documents OR dcat_type:*marcgt*)'.format(user_dict['id'])
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
                            'image_url': pg.image_url if hasattr(pg, 'image_url') else None,
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

        def user_events(id):
            """User events tab (water-events from pages plugin)."""
            try:
                user_dict, is_myself, is_sysadmin = MyLogica._get_user_context(id)

                events = []
                try:
                    from ckanext.pages.db import Page
                    pages = model.Session.query(Page).filter(
                        Page.user_id == user_dict['id'],
                        Page.page_type == 'water-events',
                    ).order_by(Page.created.desc()).all()
                    for pg in pages:
                        events.append({
                            'title': pg.title,
                            'name': pg.name,
                            'content': pg.content,
                            'publish_date': pg.publish_date.isoformat() if pg.publish_date else None,
                            'created': pg.created.isoformat() if pg.created else None,
                            'page_type': pg.page_type,
                        })
                except Exception as e:
                    log.warning(f"Error fetching events for user {id}: {e}")

                return render_template(
                    "user/events.html",
                    user_dict=user_dict,
                    events=events,
                    is_myself=is_myself,
                    is_sysadmin=is_sysadmin,
                )
            except toolkit.ObjectNotFound:
                abort(404, _('User not found'))
            except Exception as e:
                log.error(f"Error in user_events: {e}")
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

        @staticmethod
        def dataset_read(package_type, id):
            """Optimized dataset read view.

            Replaces the CKAN core read() which calls resource_view_list
            per resource (N+1 query problem). Uses a single batch SQL query
            instead.
            """
            from flask import g
            from ckan.logic import get_action, NotFound, NotAuthorized
            from ckan.lib.plugins import lookup_package_plugin
            import ckan.lib.datapreview as datapreview

            context = {
                u'model': model,
                u'session': model.Session,
                u'user': current_user.name,
                u'for_view': True,
                u'auth_user_obj': current_user,
            }
            data_dict = {u'id': id, u'include_tracking': True}

            try:
                pkg_dict = get_action(u'package_show')(context, data_dict)
                pkg = context[u'package']
            except NotFound:
                return base.abort(404, _(u'Dataset not found or you have no permission to view it'))
            except NotAuthorized:
                if config.get(u'ckan.auth.reveal_private_datasets'):
                    if current_user.is_authenticated:
                        return base.abort(403, _(u'Unauthorized to read package %s') % id)
                    else:
                        return h.redirect_to('user.login', came_from=h.url_for('{}.read'.format(package_type), id=id))
                return base.abort(404, _(u'Dataset not found or you have no permission to view it'))

            g.pkg_dict = pkg_dict
            g.pkg = pkg

            if plugins.plugin_loaded('activity'):
                activity_id = request.args.get('activity_id')
                if activity_id:
                    return h.redirect_to('activity.package_history', id=id, activity_id=activity_id)

            if data_dict['id'] == pkg_dict['id'] and data_dict['id'] != pkg_dict['name']:
                return h.redirect_to(u'{}.read'.format(package_type), id=pkg_dict['name'])

            # Batch query: get resource IDs that have views in ONE SQL query
            resource_ids = [r['id'] for r in pkg_dict.get('resources', [])]
            ids_with_views = set()
            if resource_ids:
                try:
                    rv_query = model.Session.query(
                        model.ResourceView.resource_id,
                        model.ResourceView.view_type,
                    ).filter(
                        model.ResourceView.resource_id.in_(resource_ids)
                    )
                    for rv_resource_id, rv_view_type in rv_query:
                        if datapreview.get_view_plugin(rv_view_type):
                            ids_with_views.add(rv_resource_id)
                except Exception as e:
                    log.warning(f'Batch resource_view query failed, falling back: {e}')
                    for r in pkg_dict['resources'][:20]:
                        try:
                            views = get_action('resource_view_list')(dict(context), {'id': r['id']})
                            if views:
                                ids_with_views.add(r['id'])
                        except Exception:
                            pass

            for r in pkg_dict['resources']:
                r['has_views'] = r['id'] in ids_with_views

            actual_type = pkg_dict[u'type'] or package_type
            pkg_plugin = lookup_package_plugin(actual_type)
            pkg_plugin.setup_template_variables(context, {u'id': id})
            try:
                template = pkg_plugin.read_template()
            except AttributeError:
                template = 'package/read.html'

            try:
                return base.render(
                    template, {
                        u'dataset_type': actual_type,
                        u'pkg_dict': pkg_dict,
                        u'pkg': pkg,
                    }
                )
            except Exception as e:
                log.error(f'Error rendering dataset read template: {e}')
                return base.abort(500, str(e))

        # ── Featured Datasets Admin Panel ─────────────────────────────────

        @staticmethod
        def featured_datasets_admin():
            """Render the featured datasets admin panel. Sysadmin only."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_dataset_list', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            featured = toolkit.get_action('featured_dataset_list')(context, {})
            extra_vars = {
                'featured_datasets': featured.get('results', []),
                'featured_count': featured.get('count', 0),
            }
            return base.render('admin/featured_datasets.html', extra_vars=extra_vars)

        @staticmethod
        def featured_datasets_search():
            """AJAX: Search datasets to add as featured."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_dataset_list', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            q = request.args.get('q', '')
            if not q or len(q) < 2:
                return jsonify({'results': []})

            try:
                search_result = toolkit.get_action('package_search')(
                    {'ignore_auth': True},
                    {'q': q, 'rows': 10}
                )
                results = []
                for pkg in search_result.get('results', []):
                    is_featured = any(
                        t['name'] == 'FeaturedDataset'
                        for t in pkg.get('tags', [])
                    )
                    org = pkg.get('organization') or {}
                    results.append({
                        'id': pkg['id'],
                        'name': pkg['name'],
                        'title': pkg.get('title', pkg['name']),
                        'organization_title': org.get('title', ''),
                        'is_featured': is_featured,
                    })
                return jsonify({'results': results})
            except Exception as e:
                log.error(f'Error searching datasets: {e}')
                return jsonify({'results': [], 'error': str(e)})

        @staticmethod
        def featured_datasets_add():
            """AJAX: Add a dataset as featured."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_dataset_add', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            dataset_id = request.form.get('id', '')
            if not dataset_id:
                return jsonify({'success': False, 'error': 'Missing dataset id'}), 400

            try:
                result = toolkit.get_action('featured_dataset_add')(
                    context, {'id': dataset_id}
                )
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Dataset not found'}), 404
            except Exception as e:
                log.error(f'Error adding featured dataset: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_datasets_remove():
            """AJAX: Remove a dataset from featured."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_dataset_remove', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            dataset_id = request.form.get('id', '')
            if not dataset_id:
                return jsonify({'success': False, 'error': 'Missing dataset id'}), 400

            try:
                result = toolkit.get_action('featured_dataset_remove')(
                    context, {'id': dataset_id}
                )
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Dataset not found'}), 404
            except Exception as e:
                log.error(f'Error removing featured dataset: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        # ── Featured Publications Admin Panel ─────────────────────────────

        @staticmethod
        def featured_publications_admin():
            """Render the featured publications admin panel. Sysadmin only."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_list', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            pubs = toolkit.get_action('featured_publication_list')(context, {})

            # Check for legacy UNESDOC datasets so we can show an import button
            legacy_count = 0
            try:
                legacy_user = '8ad64841-340c-49dc-8716-c6b61ea4b111'
                query = (
                    '( followers:yes AND tags:UNESDOC ) OR '
                    '( tags:UNESDOC AND creator_user_id:{user} )'
                ).format(user=legacy_user)
                search_result = toolkit.get_action('package_search')(
                    {'ignore_auth': True},
                    {'q': query, 'rows': 0}
                )
                legacy_count = search_result.get('count', 0)
            except Exception:
                legacy_count = 0

            extra_vars = {
                'publications': pubs.get('results', []),
                'publications_count': pubs.get('count', 0),
                'legacy_count': legacy_count,
            }
            return base.render('admin/featured_publications.html', extra_vars=extra_vars)

        @staticmethod
        def featured_publications_create():
            """AJAX: Create a featured publication."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            data = {
                'title': request.form.get('title', ''),
                'link': request.form.get('link', ''),
                'description': request.form.get('description', ''),
                'image_url': request.form.get('image_url', ''),
            }

            if not data['title'] or not data['link']:
                return jsonify({'success': False, 'error': 'Title and link are required'}), 400

            try:
                result = toolkit.get_action('featured_publication_create')(context, data)
                return jsonify(result)
            except Exception as e:
                log.error(f'Error creating featured publication: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_publications_update():
            """AJAX: Update a featured publication."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_update', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            pub_id = request.form.get('id', '')
            if not pub_id:
                return jsonify({'success': False, 'error': 'Missing id'}), 400

            data = {'id': pub_id}
            for field in ('title', 'link', 'description', 'image_url'):
                if field in request.form:
                    data[field] = request.form[field]

            try:
                result = toolkit.get_action('featured_publication_update')(context, data)
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            except Exception as e:
                log.error(f'Error updating featured publication: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_publications_delete():
            """AJAX: Delete a featured publication."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_delete', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            pub_id = request.form.get('id', '')
            if not pub_id:
                return jsonify({'success': False, 'error': 'Missing id'}), 400

            try:
                result = toolkit.get_action('featured_publication_delete')(context, {'id': pub_id})
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            except Exception as e:
                log.error(f'Error deleting featured publication: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_publications_reorder():
            """AJAX: Reorder featured publications."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_reorder', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                order = request.get_json(force=True).get('order', [])
            except Exception:
                order = request.form.getlist('order[]')

            try:
                result = toolkit.get_action('featured_publication_reorder')(
                    context, {'order': order}
                )
                return jsonify(result)
            except Exception as e:
                log.error(f'Error reordering featured publications: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_publications_upload_image():
            """AJAX: Upload an image for a featured publication.
            Uses CKAN's storage to save the file and returns the URL.
            """
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400

            upload_file = request.files['file']
            if not upload_file.filename:
                return jsonify({'success': False, 'error': 'Empty filename'}), 400

            try:
                import ckan.lib.uploader as uploader
                upload = uploader.get_uploader('featured_publications')
                upload.update_data_dict(
                    {'upload': upload_file, 'url': '', 'clear_upload': ''},
                    'url', 'upload', 'clear_upload'
                )
                upload.upload()
                image_url = h.url_for_static(
                    'uploads/featured_publications/{}'.format(upload.filename),
                    qualified=False
                )
                return jsonify({'success': True, 'image_url': image_url})
            except Exception as e:
                log.error(f'Error uploading image: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def featured_publications_import_legacy():
            """AJAX: Import legacy UNESDOC datasets as featured publications."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('featured_publication_import_legacy', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                result = toolkit.get_action('featured_publication_import_legacy')(context, {})
                return jsonify({
                    'success': True,
                    'imported': result.get('imported', 0),
                    'skipped': result.get('skipped', 0),
                    'results': result.get('results', []),
                })
            except Exception as e:
                log.error(f'Error importing legacy publications: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        # ── Portal Card Admin Views ──────────────────────────────────────────

        PORTAL_META = {
            'flood_drought': {
                'name': 'Flood and Drought Monitoring Portal',
                'icon': 'fa-tint',
                'url': '/flood-drought-portal',
                'banner_image': '/Landing_page/Content/flood_and_drought_monitoring_button_image.jpg',
            },
            'iot': {
                'name': 'Internet of Things Portal',
                'icon': 'fa-microchip',
                'url': '/iot-portal',
                'banner_image': '/Landing_page/Content/03IHP-INTERNET.jpg',
            },
            'citizen_science': {
                'name': 'Citizen Science Portal',
                'icon': 'fa-users',
                'url': '/citizen-science-portal',
                'banner_image': '/Landing_page/Content/02IHP-CITIZEN.jpg',
            },
        }

        @staticmethod
        def portal_cards_admin(portal_id):
            """Render the portal cards admin panel. Sysadmin only."""
            if portal_id not in MyLogica.PORTAL_META:
                return base.abort(404, _('Portal not found'))

            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_list', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            cards = toolkit.get_action('portal_card_list')(
                context, {'portal_id': portal_id}
            )
            portal_info = MyLogica.PORTAL_META[portal_id]
            extra_vars = {
                'cards': cards.get('results', []),
                'cards_count': cards.get('count', 0),
                'portal_id': portal_id,
                'portal_name': portal_info['name'],
                'portal_icon': portal_info['icon'],
                'portal_url': portal_info['url'],
                'portal_banner_image': portal_info.get('banner_image', ''),
            }
            return base.render('admin/portal_cards.html', extra_vars=extra_vars)

        @staticmethod
        def portal_cards_create():
            """AJAX: Create a portal card."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            data = {
                'portal_id': request.form.get('portal_id', ''),
                'title': request.form.get('title', ''),
                'link': request.form.get('link', ''),
                'description': request.form.get('description', ''),
                'image_url': request.form.get('image_url', ''),
                'is_coming_soon': request.form.get('is_coming_soon', ''),
            }

            if not data['title'] or not data['link'] or not data['portal_id']:
                return jsonify({'success': False, 'error': 'Title, link, and portal_id are required'}), 400

            try:
                result = toolkit.get_action('portal_card_create')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
                log.error(f'Error creating portal card: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def portal_cards_update():
            """AJAX: Update a portal card."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_update', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            card_id = request.form.get('id', '')
            if not card_id:
                return jsonify({'success': False, 'error': 'Missing id'}), 400

            data = {'id': card_id}
            for field in ('title', 'link', 'description', 'image_url', 'is_coming_soon', 'is_archived'):
                if field in request.form:
                    data[field] = request.form[field]

            try:
                result = toolkit.get_action('portal_card_update')(context, data)
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            except Exception as e:
                log.error(f'Error updating portal card: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def portal_cards_delete():
            """AJAX: Delete a portal card."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_delete', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            card_id = request.form.get('id', '')
            if not card_id:
                return jsonify({'success': False, 'error': 'Missing id'}), 400

            try:
                result = toolkit.get_action('portal_card_delete')(context, {'id': card_id})
                return jsonify(result)
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Not found'}), 404
            except Exception as e:
                log.error(f'Error deleting portal card: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def portal_cards_reorder():
            """AJAX: Reorder portal cards."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_reorder', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                order = request.get_json(force=True).get('order', [])
            except Exception:
                order = request.form.getlist('order[]')

            try:
                result = toolkit.get_action('portal_card_reorder')(
                    context, {'order': order}
                )
                return jsonify(result)
            except Exception as e:
                log.error(f'Error reordering portal cards: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def portal_cards_upload_image():
            """AJAX: Upload an image for a portal card."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('portal_card_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400

            upload_file = request.files['file']
            if not upload_file.filename:
                return jsonify({'success': False, 'error': 'Empty filename'}), 400

            try:
                import ckan.lib.uploader as uploader
                upload = uploader.get_uploader('portal_cards')
                upload.update_data_dict(
                    {'upload': upload_file, 'url': '', 'clear_upload': ''},
                    'url', 'upload', 'clear_upload'
                )
                upload.upload()
                image_url = h.url_for_static(
                    'uploads/portal_cards/{}'.format(upload.filename),
                    qualified=False
                )
                return jsonify({'success': True, 'image_url': image_url})
            except Exception as e:
                log.error(f'Error uploading portal card image: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def bug_tickets_list():
            """List all bug tickets (own for users, all for sysadmin)."""
            context = {
                'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj,
            }
            if not c.userobj:
                return toolkit.redirect_to('user.login')

            status_filter = request.args.get('status', '')
            try:
                result = toolkit.get_action('bug_ticket_list')(
                    context, {'status': status_filter or None}
                )
            except toolkit.NotAuthorized:
                return toolkit.abort(403, _('Not authorized'))

            extra_vars = {
                'tickets': result['results'],
                'count': result['count'],
                'status_filter': status_filter,
                'is_sysadmin': c.userobj.sysadmin if c.userobj else False,
            }
            return toolkit.render('bug_tickets/list.html', extra_vars=extra_vars)

        @staticmethod
        def bug_tickets_new():
            """Show the new ticket form or create a ticket on POST."""
            context = {
                'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj,
            }
            if not c.userobj:
                return toolkit.redirect_to('user.login')

            errors = {}
            data = {}

            if request.method == 'POST':
                data = {
                    'title': request.form.get('title', '').strip(),
                    'description': request.form.get('description', '').strip(),
                    'url': request.form.get('url', '').strip(),
                    'browser_info': request.form.get('browser_info', ''),
                    'log_snapshot': request.form.get('log_snapshot', ''),
                }

                # Handle image upload
                image_filename = u''
                upload_file = request.files.get('image')
                if upload_file and upload_file.filename:
                    try:
                        import ckan.lib.uploader as uploader
                        upload = uploader.get_uploader('bug_tickets')
                        upload.update_data_dict(
                            {'upload': upload_file, 'url': '', 'clear_upload': ''},
                            'url', 'upload', 'clear_upload'
                        )
                        upload.upload()
                        image_filename = upload.filename
                    except Exception as e:
                        log.error('Error uploading bug ticket image: %s', e)

                data['image_filename'] = image_filename

                if not data['title']:
                    errors['title'] = [_('Title is required')]
                if not data['description']:
                    errors['description'] = [_('Description is required')]

                if not errors:
                    try:
                        ticket = toolkit.get_action('bug_ticket_create')(context, data)
                        h.flash_success(_('Bug ticket created successfully'))
                        return toolkit.redirect_to('theme_ejemplo.bug_tickets_show',
                                                   id=ticket['id'])
                    except toolkit.ValidationError as e:
                        errors = e.error_dict

            extra_vars = {
                'data': data,
                'errors': errors,
                'referrer_url': request.referrer or '',
            }
            return toolkit.render('bug_tickets/new.html', extra_vars=extra_vars)

        @staticmethod
        def bug_tickets_show(id):
            """Show a single bug ticket detail."""
            context = {
                'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj,
            }
            if not c.userobj:
                return toolkit.redirect_to('user.login')

            try:
                ticket = toolkit.get_action('bug_ticket_show')(context, {'id': id})
            except toolkit.ObjectNotFound:
                return toolkit.abort(404, _('Ticket not found'))
            except toolkit.NotAuthorized:
                return toolkit.abort(403, _('Not authorized'))

            extra_vars = {
                'ticket': ticket,
                'is_sysadmin': c.userobj.sysadmin if c.userobj else False,
                'is_owner': c.userobj.id == ticket['user_id'] if c.userobj else False,
            }
            return toolkit.render('bug_tickets/show.html', extra_vars=extra_vars)

        @staticmethod
        def bug_tickets_close(id):
            """Close a ticket (user resolves it)."""
            context = {
                'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj,
            }
            if not c.userobj:
                return toolkit.redirect_to('user.login')

            from ckanext.theme_ejemplo.model import BugTicket
            status = BugTicket.STATUS_RESOLVED_USER
            if c.userobj.sysadmin:
                status = request.form.get('status', BugTicket.STATUS_RESOLVED_ADMIN)

            admin_notes = request.form.get('admin_notes', '')

            try:
                data = {'id': id, 'status': status}
                if admin_notes:
                    data['admin_notes'] = admin_notes
                toolkit.get_action('bug_ticket_update')(context, data)
                h.flash_success(_('Ticket updated successfully'))
            except (toolkit.NotAuthorized, toolkit.ObjectNotFound) as e:
                h.flash_error(str(e))

            return toolkit.redirect_to('theme_ejemplo.bug_tickets_show', id=id)

        @staticmethod
        def bug_tickets_update_status(id):
            """Admin: change ticket status (in_progress, resolved_by_admin, etc.)."""
            context = {
                'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj,
            }
            if not c.userobj or not c.userobj.sysadmin:
                return toolkit.abort(403, _('Not authorized'))

            new_status = request.form.get('status', '')
            admin_notes = request.form.get('admin_notes', '')

            try:
                data = {'id': id, 'status': new_status}
                if admin_notes:
                    data['admin_notes'] = admin_notes
                toolkit.get_action('bug_ticket_update')(context, data)
                h.flash_success(_('Ticket status updated'))
            except (toolkit.ValidationError, toolkit.NotAuthorized,
                    toolkit.ObjectNotFound) as e:
                h.flash_error(str(e))

            return toolkit.redirect_to('theme_ejemplo.bug_tickets_show', id=id)

        # ── Sysadmin User Management Panel ────────────────────────────────

        @staticmethod
        def users_admin():
            """Render the sysadmin user management panel."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_list', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            # Leer parámetros de filtro desde query string
            q = request.args.get('q', '')
            state = request.args.get('state', '')
            sysadmin = request.args.get('sysadmin', '')
            order_by = request.args.get('order_by', 'created')
            page = max(int(request.args.get('page', 1)), 1)
            limit = 25
            offset = (page - 1) * limit

            data_dict = {
                'q': q,
                'state': state,
                'order_by': order_by,
                'limit': limit,
                'offset': offset,
            }
            if sysadmin:
                data_dict['sysadmin'] = sysadmin

            result = toolkit.get_action('admin_user_list')(context, data_dict)
            total = result.get('count', 0)
            total_pages = max(1, (total + limit - 1) // limit)

            extra_vars = {
                'users': result.get('results', []),
                'total': total,
                'q': q,
                'state': state,
                'sysadmin_filter': sysadmin,
                'order_by': order_by,
                'page': page,
                'limit': limit,
                'total_pages': total_pages,
            }
            return base.render('admin/users.html', extra_vars=extra_vars)

        @staticmethod
        def users_admin_search():
            """AJAX: Search users for autocomplete/quick search."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_list', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            q = request.args.get('q', '')
            if not q or len(q) < 2:
                return jsonify({'results': []})

            try:
                result = toolkit.get_action('admin_user_list')(
                    context,
                    {'q': q, 'limit': 10, 'offset': 0}
                )
                return jsonify({
                    'results': result.get('results', []),
                    'count': result.get('count', 0),
                })
            except Exception as e:
                log.error(f'Error searching users: {e}')
                return jsonify({'results': [], 'error': str(e)})

        @staticmethod
        def users_admin_create():
            """AJAX: Create a new user."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {
                    'name': request.form.get('name', ''),
                    'email': request.form.get('email', ''),
                    'fullname': request.form.get('fullname', ''),
                    'password': request.form.get('password', ''),
                    'sysadmin': request.form.get('sysadmin', 'false'),
                }
                result = toolkit.get_action('admin_user_create')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except Exception as e:
                log.error(f'Error creating user: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_reset_password():
            """AJAX: Reset a user's password."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_reset_password', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {
                    'id': request.form.get('id', ''),
                    'password': request.form.get('password', ''),
                    'sysadmin_password': request.form.get('sysadmin_password', ''),
                }
                result = toolkit.get_action('admin_user_reset_password')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error resetting password: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_request_password_reset():
            """AJAX: Send password reset email to a user."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_request_password_reset', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {'id': request.form.get('id', '')}
                result = toolkit.get_action('admin_user_request_password_reset')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error sending password reset email: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_delete():
            """AJAX: Soft-delete a user."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_delete', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {'id': request.form.get('id', '')}
                result = toolkit.get_action('admin_user_delete')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error deleting user: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_purge():
            """AJAX: Permanently purge a deleted user."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_purge', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {
                    'id': request.form.get('id', ''),
                    'sysadmin_password': request.form.get('sysadmin_password', ''),
                }
                result = toolkit.get_action('admin_user_purge')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error purging user: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_reactivate():
            """AJAX: Reactivate a deleted user."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_reactivate', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {'id': request.form.get('id', '')}
                result = toolkit.get_action('admin_user_reactivate')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error reactivating user: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def users_admin_toggle_sysadmin():
            """AJAX: Promote or demote a user as sysadmin."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('admin_user_toggle_sysadmin', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            try:
                data = {
                    'id': request.form.get('id', ''),
                    'sysadmin': request.form.get('sysadmin', 'false'),
                }
                result = toolkit.get_action('admin_user_toggle_sysadmin')(context, data)
                return jsonify(result)
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'User not found'}), 404
            except Exception as e:
                log.error(f'Error toggling sysadmin: {e}')
                return jsonify({'success': False, 'error': str(e)}), 500

        # ── IHP-IX Admin Controller Methods ──────────────────────────────────

        @staticmethod
        def ihpix_content_admin():
            """Render IHP-IX content admin panel. Sysadmin only."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('ihpix_content_list', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            result = toolkit.get_action('ihpix_content_list')(context, {})
            cta_cards = [i for i in result['results']
                         if i['section_type'] == 'cta_card']
            priority_areas = [i for i in result['results']
                              if i['section_type'] == 'priority_area']

            return render_template(
                'admin/ihpix_content.html',
                cta_cards=cta_cards,
                priority_areas=priority_areas,
            )

        @staticmethod
        def ihpix_content_update():
            """AJAX: Update an IHP-IX content section."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                data = {}
                for key in ('id', 'section_key', 'title', 'description',
                            'image_url', 'link', 'badge_text', 'is_active',
                            'extra_fields'):
                    val = request.form.get(key)
                    if val is not None:
                        data[key] = val

                result = toolkit.get_action('ihpix_content_update')(context, data)
                return jsonify({'success': True, 'data': result})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Content not found'}), 404
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except Exception as e:
                log.error('Error updating IHP-IX content: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def ihpix_content_upload_image():
            """AJAX: Upload an image for IHP-IX content."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('ihpix_content_update', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400

            upload_file = request.files['file']
            if not upload_file.filename:
                return jsonify({'success': False, 'error': 'Empty filename'}), 400

            try:
                import ckan.lib.uploader as uploader
                upload = uploader.get_uploader('ihpix')
                upload.update_data_dict(
                    {'upload': upload_file, 'url': '', 'clear_upload': ''},
                    'url', 'upload', 'clear_upload'
                )
                upload.upload()
                image_url = h.url_for_static(
                    'uploads/ihpix/{}'.format(upload.filename),
                    qualified=False
                )
                return jsonify({'success': True, 'image_url': image_url})
            except Exception as e:
                log.error('Error uploading IHP-IX image: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def ihpix_activities_admin():
            """Render IHP-IX activities admin panel. Sysadmin only."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('ihpix_activity_create', context, {})
            except toolkit.NotAuthorized:
                return base.abort(403, _('Not authorized'))

            pa_filter = request.args.get('pa', '')
            page = int(request.args.get('page', 1))
            limit = 20
            offset = (page - 1) * limit

            data = {'limit': limit, 'offset': offset}
            if pa_filter:
                data['priority_area'] = pa_filter

            result = toolkit.get_action('ihpix_activity_list')(context, data)

            return render_template(
                'admin/ihpix_activities.html',
                activities=result['results'],
                total=result['count'],
                facets=result.get('facets', {}),
                pa_filter=pa_filter,
                page=page,
                items_per_page=limit,
            )

        @staticmethod
        def ihpix_activities_create():
            """AJAX: Create an IHP-IX activity."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                data = {}
                for key in ('title', 'description', 'priority_area', 'output',
                            'country', 'institution', 'link', 'image_url',
                            'status', 'reported_date'):
                    val = request.form.get(key)
                    if val is not None and val != '':
                        data[key] = val

                result = toolkit.get_action('ihpix_activity_create')(context, data)
                return jsonify({'success': True, 'data': result})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except Exception as e:
                log.error('Error creating IHP-IX activity: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def ihpix_activities_update():
            """AJAX: Update an IHP-IX activity."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                data = {}
                for key in ('id', 'title', 'description', 'priority_area',
                            'output', 'country', 'institution', 'link',
                            'image_url', 'status', 'reported_date'):
                    val = request.form.get(key)
                    if val is not None:
                        data[key] = val

                result = toolkit.get_action('ihpix_activity_update')(context, data)
                return jsonify({'success': True, 'data': result})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Activity not found'}), 404
            except toolkit.ValidationError as e:
                return jsonify({'success': False, 'error': e.error_dict}), 400
            except Exception as e:
                log.error('Error updating IHP-IX activity: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def ihpix_activities_delete():
            """AJAX: Delete an IHP-IX activity."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                activity_id = request.form.get('id', '')
                result = toolkit.get_action('ihpix_activity_delete')(
                    context, {'id': activity_id}
                )
                return jsonify(result)
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403
            except toolkit.ObjectNotFound:
                return jsonify({'success': False, 'error': 'Activity not found'}), 404
            except Exception as e:
                log.error('Error deleting IHP-IX activity: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        @staticmethod
        def ihpix_activities_upload_image():
            """AJAX: Upload an image for an IHP-IX activity."""
            context = {
                'user': c.user,
                'auth_user_obj': c.userobj,
            }
            try:
                toolkit.check_access('ihpix_activity_create', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False, 'error': 'Not authorized'}), 403

            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400

            upload_file = request.files['file']
            if not upload_file.filename:
                return jsonify({'success': False, 'error': 'Empty filename'}), 400

            try:
                import ckan.lib.uploader as uploader
                upload = uploader.get_uploader('ihpix_activities')
                upload.update_data_dict(
                    {'upload': upload_file, 'url': '', 'clear_upload': ''},
                    'url', 'upload', 'clear_upload'
                )
                upload.upload()
                image_url = h.url_for_static(
                    'uploads/ihpix_activities/{}'.format(upload.filename),
                    qualified=False
                )
                return jsonify({'success': True, 'image_url': image_url})
            except Exception as e:
                log.error('Error uploading IHP-IX activity image: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500

        # ── IHP-IX Reporting Form ──────────────────────────────────────────

        @staticmethod
        def ihpix_report():
            """Public form: logged-in users can submit IHP-IX activity reports."""
            from ckanext.theme_ejemplo.model import (
                IhpixActivity, init_ihpix_activities_db, VALID_PRIORITY_AREAS,
            )
            init_ihpix_activities_db()

            if request.method == 'POST':
                if not c.user:
                    return jsonify({'success': False,
                                    'error': 'You must be logged in'}), 403
                try:
                    context = {'user': c.user, 'model': model}
                    data_dict = {
                        'title': request.form.get('title', ''),
                        'description': request.form.get('description', ''),
                        'priority_area': request.form.get('priority_area', ''),
                        'output': request.form.get('output', ''),
                        'country': request.form.get('country', ''),
                        'institution': request.form.get('institution', ''),
                        'link': request.form.get('link', ''),
                        'contact_name': request.form.get('contact_name', ''),
                        'contact_email': request.form.get('contact_email', ''),
                        'reported_date': request.form.get('reported_date', ''),
                        'start_date': request.form.get('start_date', ''),
                        'end_date': request.form.get('end_date', ''),
                    }
                    result = toolkit.get_action('ihpix_report_submit')(
                        context, data_dict
                    )
                    return jsonify({'success': True, 'data': result})
                except toolkit.ValidationError as e:
                    return jsonify({'success': False,
                                    'error': str(e.error_dict)}), 400
                except toolkit.NotAuthorized:
                    return jsonify({'success': False,
                                    'error': 'Not authorized'}), 403
                except Exception as e:
                    log.error('Error submitting IHP-IX report: %s', e)
                    return jsonify({'success': False, 'error': str(e)}), 500

            # GET: render the form
            is_logged_in = bool(c.user)
            return render_template(
                'ihpix/report.html',
                is_logged_in=is_logged_in,
                priority_areas=list(VALID_PRIORITY_AREAS),
            )

        # ── IHP-IX Dashboard ──────────────────────────────────────────────

        @staticmethod
        def ihpix_dashboard():
            """Public dashboard with interactive charts."""
            from ckanext.theme_ejemplo.model import (
                IhpixActivity, init_ihpix_activities_db,
            )
            init_ihpix_activities_db()

            pa_filter = request.args.get('pa', '')
            try:
                context = {'user': c.user, 'model': model}
                stats = toolkit.get_action('ihpix_dashboard_stats')(
                    context, {'priority_area': pa_filter}
                )
            except Exception as e:
                log.error('Error fetching IHP-IX dashboard stats: %s', e)
                stats = {
                    'total_activities': 0, 'total_countries': 0,
                    'total_institutions': 0, 'pending_reports': 0,
                    'by_priority_area': [], 'by_output': [],
                    'timeline': [], 'by_country': [],
                }

            is_sysadmin = False
            try:
                if c.userobj and c.userobj.sysadmin:
                    is_sysadmin = True
            except Exception:
                pass

            return render_template(
                'ihpix/dashboard.html',
                stats=stats,
                pa_filter=pa_filter,
                is_sysadmin=is_sysadmin,
            )

        # ── IHP-IX Admin: Review Reports ──────────────────────────────────

        @staticmethod
        def ihpix_reports_admin():
            """Admin panel to review pending/rejected reports."""
            try:
                context = {'user': c.user, 'model': model}
                toolkit.check_access('ihpix_report_review', context, {})
            except toolkit.NotAuthorized:
                return abort(403)

            from ckanext.theme_ejemplo.model import (
                IhpixActivity, init_ihpix_activities_db,
            )
            init_ihpix_activities_db()

            status_filter = request.args.get('status', 'pending')
            page = int(request.args.get('page', 1))
            items_per_page = 20
            offset = items_per_page * (page - 1)

            try:
                if status_filter == 'all':
                    results, total = IhpixActivity.get_all(
                        limit=items_per_page, offset=offset
                    )
                elif status_filter == 'rejected':
                    results, total = IhpixActivity.get_all(
                        status='rejected',
                        limit=items_per_page, offset=offset
                    )
                else:
                    results, total = IhpixActivity.get_all(
                        status='pending',
                        limit=items_per_page, offset=offset
                    )
                reports = [r.as_dict() for r in results]
            except Exception as e:
                log.error('Error fetching IHP-IX reports: %s', e)
                reports = []
                total = 0

            try:
                _, pending_count = IhpixActivity.get_all(status='pending',
                                                          limit=1, offset=0)
                _, rejected_count = IhpixActivity.get_all(status='rejected',
                                                           limit=1, offset=0)
            except Exception:
                pending_count = 0
                rejected_count = 0

            return render_template(
                'admin/ihpix_reports.html',
                reports=reports,
                total=total,
                status_filter=status_filter,
                page=page,
                items_per_page=items_per_page,
                pending_count=pending_count,
                rejected_count=rejected_count,
            )

        @staticmethod
        def ihpix_report_review_admin():
            """AJAX endpoint: approve or reject a report."""
            try:
                context = {'user': c.user, 'model': model}
                toolkit.check_access('ihpix_report_review', context, {})
            except toolkit.NotAuthorized:
                return jsonify({'success': False,
                                'error': 'Not authorized'}), 403

            try:
                data_dict = {
                    'id': request.form.get('id', ''),
                    'action': request.form.get('action', ''),
                    'review_notes': request.form.get('review_notes', ''),
                }
                context = {'user': c.user, 'model': model}
                result = toolkit.get_action('ihpix_report_review')(
                    context, data_dict
                )
                return jsonify({'success': True, 'data': result})
            except toolkit.ValidationError as e:
                return jsonify({'success': False,
                                'error': str(e.error_dict)}), 400
            except toolkit.ObjectNotFound:
                return jsonify({'success': False,
                                'error': 'Report not found'}), 404
            except Exception as e:
                log.error('Error reviewing IHP-IX report: %s', e)
                return jsonify({'success': False, 'error': str(e)}), 500
