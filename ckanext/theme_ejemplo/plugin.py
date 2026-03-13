# encoding: utf-8

'''plugin.py

'''
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.plugins import DefaultTranslation
import shapely.geometry
import requests
import json
import ckanext.schemingdcat.utils as utils
from flask import Blueprint
from ckanext.theme_ejemplo.controller import MyLogica
from . import helpers
from . import actions as custom_actions
from . import auth as custom_auth
from . import model as membership_model
import logging
from functools import lru_cache
import time

# Configurar logging
log = logging.getLogger(__name__)

# Session reutilizable para requests HTTP
http_session = requests.Session()
# Timeout optimizado: (connect_timeout, read_timeout)
# connect_timeout: tiempo para establecer conexión
# read_timeout: tiempo para recibir respuesta
http_session.timeout = (5, 10)  # 5s conexión + 10s respuesta = máximo 15s total

# TTL caches para evitar llamadas repetidas en helpers costosos
_courses_cache = {'data': None, 'expires': 0}
_member_states_cache = {'data': None, 'expires': 0}
_initiatives_cache = {'data': None, 'expires': 0}
_recently_added_datasets_cache = {'data': None, 'expires': 0}
_recently_added_documents_cache = {'data': None, 'expires': 0}

def _get_cache_ttl(config_key, default):
    try:
        return max(0, toolkit.asint(toolkit.config.get(config_key, default)))
    except Exception:
        return default

class ThemeEjemploPlugin(plugins.SingletonPlugin, DefaultTranslation):
        '''An example theme plugin.

        '''
        # Declare that this class implements IConfigurer.
        plugins.implements(plugins.IConfigurer)
        plugins.implements(plugins.IBlueprint)
        plugins.implements(plugins.ITemplateHelpers)
        plugins.implements(plugins.IPackageController, inherit=True)
        plugins.implements(plugins.ITranslation)
        plugins.implements(plugins.IActions)
        plugins.implements(plugins.IAuthFunctions)

        def __init__(self, name=None):
            super().__init__(name=name)
            # Cache para mejorar rendimiento
            self._organization_cache = {}
        
        #this fix solr-bbox search
        #for ckan v2.9
        def before_index(self, dataset_dict):
            return self.before_dataset_index(dataset_dict)
        #for ckan v2.10
        def before_dataset_index(self, dataset_dict):
            """
            Optimizado para mejor rendimiento:
            - Reducción de llamadas a APIs
            - Mejor manejo de errores
            - Logging apropiado
            """
            try:
                package_id = dataset_dict.get('id')
                
                # Evitar llamadas costosas en indexación (habilitar solo si es imprescindible)
                featured_ = 'no'  # Valor por defecto
                if toolkit.asbool(toolkit.config.get('ckanext.theme_ejemplo.index_followers', False)):
                    try:
                        sysadmin_context = {
                            'user': 'ckan.system',
                            'ignore_auth': True
                        }
                        package = toolkit.get_action('dataset_follower_list')(sysadmin_context, {'id': package_id})

                        # to define featured dataset
                        if package and any(user.get('sysadmin', False) for user in package):
                            featured_ = 'yes'
                    except Exception as e:
                        log.warning(f"Error getting followers for dataset {package_id}: {e}")

                dataset_dict['followers'] = featured_

                #better compatibility    
                if 'dcat_type' not in dataset_dict or not dataset_dict['dcat_type']:
                    dataset_dict['dcat_type'] = 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset'

                # Optimización spatial: Procesamiento más eficiente
                self._process_spatial_data(dataset_dict)
                
                # Procesamiento de facetas optimizado
                self._process_facets(dataset_dict)
                
                # Sanitizar campos para evitar problemas con atomic updates de Solr
                self._sanitize_solr_fields(dataset_dict)
                
                return dataset_dict
            
            except Exception as e:
                log.error(f"Error in before_dataset_index for dataset {dataset_dict.get('id', 'unknown')}: {e}")
                return dataset_dict

        def _process_spatial_data(self, dataset_dict):
            """Procesamiento optimizado de datos espaciales"""
            if 'spatial' in dataset_dict and dataset_dict['spatial']:
                return
                
            try:
                coords = {
                    'xmin': dataset_dict.get('xmin'),
                    'xmax': dataset_dict.get('xmax'),
                    'ymin': dataset_dict.get('ymin'),
                    'ymax': dataset_dict.get('ymax')
                }
                
                # Verificar que todas las coordenadas existen
                if not all(value is not None and value != '' for value in coords.values()):
                    return
                
                # Convertir a float una sola vez
                try:
                    coords = {k: float(v) for k, v in coords.items()}
                except ValueError as e:
                    log.warning(f"Error converting coordinates to float: {e}")
                    return
                
                # Validar rangos
                if not self._is_within_valid_range(coords['xmin'], coords['ymin']) or \
                   not self._is_within_valid_range(coords['xmax'], coords['ymax']):
                    log.warning(f"Coordinates out of valid range for dataset {dataset_dict.get('id')}")
                    return
                
                # Crear geometría WKT
                bbox = shapely.geometry.box(coords['xmin'], coords['ymin'], 
                                          coords['xmax'], coords['ymax'])
                
                if 'spatial_geom' not in dataset_dict or not dataset_dict['spatial_geom']:
                    dataset_dict['spatial_geom'] = bbox.wkt
                    
            except Exception as e:
                log.error(f"Error processing spatial data: {e}")

        @staticmethod
        def _is_within_valid_range(x, y):
            """Función estática para validación de coordenadas"""
            return -180 <= x <= 180 and -90 <= y <= 90

        def _process_facets(self, dataset_dict):
            """Procesamiento optimizado de facetas con mejor manejo de campos multiidioma"""
            try:
                facets_dict = utils.get_facets_dict()
                for facet, label in facets_dict.items():
                    data = dataset_dict.get(facet)
                    if data:
                        if isinstance(data, str):
                            try:
                                if facet == "spatial":
                                    dataset_dict[facet] = json.dumps(data)
                                else:
                                    # Verificar si es JSON válido antes de procesar
                                    parsed_data = json.loads(data)
                                    
                                    # Manejo especial para campos multiidioma
                                    if isinstance(parsed_data, dict):
                                        # Si es un diccionario con códigos de idioma como claves
                                        if self._contains_language_codes(parsed_data):
                                            # Serializar como JSON string para evitar problemas de atomic update
                                            dataset_dict[facet] = json.dumps(parsed_data)
                                        else:
                                            dataset_dict[facet] = parsed_data
                                    elif isinstance(parsed_data, list):
                                        # Manejar listas que pueden contener objetos con códigos de idioma
                                        dataset_dict[facet] = self._sanitize_list_for_solr(parsed_data)
                                    else:
                                        dataset_dict[facet] = parsed_data
                                        
                            except json.JSONDecodeError:
                                # Si no es JSON válido, mantener como string
                                dataset_dict[facet] = data
                            except Exception as e:
                                log.warning(f"Error processing facet {facet}: {e}")
                                dataset_dict[facet] = data
                    else:
                        dataset_dict.pop(facet, None)  # Más eficiente que 'del'
            except Exception as e:
                log.error(f"Error processing facets: {e}")
        
        def _contains_language_codes(self, data_dict):
            """Verificar si el diccionario contiene códigos de idioma como claves"""
            language_codes = ['en', 'es', 'fr', 'de', 'it', 'pt', 'ar', 'zh', 'ja', 'ru']
            if isinstance(data_dict, dict):
                return any(key in language_codes for key in data_dict.keys())
            return False
        
        def _sanitize_list_for_solr(self, data_list):
            """Sanitizar listas para evitar problemas con Solr atomic updates"""
            try:
                sanitized = []
                for item in data_list:
                    if isinstance(item, dict) and self._contains_language_codes(item):
                        # Convertir dictionaries con códigos de idioma a JSON string
                        sanitized.append(json.dumps(item))
                    else:
                        sanitized.append(item)
                return sanitized
            except Exception as e:
                log.warning(f"Error sanitizing list for Solr: {e}")
                return data_list
        
        def _sanitize_solr_fields(self, dataset_dict):
            """
            Sanitizar todos los campos del dataset para evitar problemas con Solr atomic updates.
            Especialmente importante para campos que pueden contener códigos de idioma como 'fr'
            """
            try:
                # Campos que frecuentemente causan problemas con atomic updates
                problematic_fields = [
                    'title', 'description', 'notes', 'title_translated', 'notes_translated',
                    'theme', 'theme_eu', 'language', 'alternate_identifier', 'theme_inspire',
                    'keywords', 'tags', 'extras', 'resources'
                ]
                
                for field in problematic_fields:
                    if field in dataset_dict:
                        value = dataset_dict[field]
                        dataset_dict[field] = self._sanitize_field_value(value, field)
                
                # Buscar y sanitizar cualquier campo que contenga diccionarios con códigos de idioma
                for key, value in list(dataset_dict.items()):
                    if isinstance(value, dict) and self._contains_language_codes(value):
                        dataset_dict[key] = json.dumps(value)
                        log.debug(f"Sanitized field {key} containing language codes")
                        
            except Exception as e:
                log.error(f"Error sanitizing Solr fields: {e}")
        
        def _sanitize_field_value(self, value, field_name):
            """Sanitizar un valor específico de campo"""
            try:
                if isinstance(value, str):
                    # Intentar parsear como JSON
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict) and self._contains_language_codes(parsed):
                            return json.dumps(parsed)  # Re-serialize para asegurar formato correcto
                        return value
                    except json.JSONDecodeError:
                        return value
                        
                elif isinstance(value, dict):
                    if self._contains_language_codes(value):
                        return json.dumps(value)
                    return value
                    
                elif isinstance(value, list):
                    return self._sanitize_list_for_solr(value)
                    
                return value
                
            except Exception as e:
                log.warning(f"Error sanitizing field {field_name}: {e}")
                return value

        # ── Tracking injection hooks ──────────────────────────────────────

        def after_dataset_show(self, context, pkg_dict):
            """Inject tracking_summary from materialized views into pkg_dict."""
            try:
                name = pkg_dict.get('name')
                if name:
                    tracking = helpers.get_dataset_tracking(name)
                    pkg_dict['tracking_summary'] = {
                        'total': tracking.get('total', 0),
                        'recent': tracking.get('recent', 0),
                    }
                for res in pkg_dict.get('resources', []):
                    rid = res.get('id')
                    if rid:
                        dl = helpers.get_resource_downloads(rid)
                        res['tracking_summary'] = {
                            'total': dl.get('total', 0),
                            'recent': 0,
                        }
            except Exception as e:
                log.debug(f"Tracking injection skipped: {e}")

        def after_dataset_search(self, search_results, search_params):
            """Inject tracking_summary into search results for view-count badges."""
            try:
                for pkg_dict in search_results.get('results', []):
                    name = pkg_dict.get('name')
                    if name:
                        tracking = helpers.get_dataset_tracking(name)
                        pkg_dict['tracking_summary'] = {
                            'total': tracking.get('total', 0),
                            'recent': tracking.get('recent', 0),
                        }
            except Exception as e:
                log.debug(f"Tracking injection in search skipped: {e}")
            return search_results

        def update_config(self, config):
            # Add this plugin's templates dir to CKAN's extra_template_paths, so
            # that CKAN will use this plugin's custom templates.
            # 'templates' is the path to the templates dir, relative to this
            # plugin.py file.
            toolkit.add_template_directory(config, 'templates')
            #para el css y archivos necesarios
            toolkit.add_public_directory(config,'public')
            #Assets
            toolkit.add_resource('public', 'theme')

            # Create membership_request table if needed
            membership_model.init_db()
            # Create featured_publication table if needed
            membership_model.init_featured_publications_db()
            # Create bug_ticket table if needed
            membership_model.init_bug_tickets_db()
            # Create portal_card table if needed
            membership_model.init_portal_cards_db()
            
        def get_blueprint(self):
            
            blueprint = Blueprint(self.name, self.__module__)        
        
            blueprint.add_url_rule(
                u'/memberstates',
                u'memberstates',
                MyLogica.memberstates,
                methods=['GET']
            )
            
            blueprint.add_url_rule(
                u'/thematicbuilder',
                u'thematicbuilder',
                MyLogica.thematicbuilder,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/ihpix',
                u'ihpix',
                MyLogica.ihpix,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/ihpix/outputs',
                u'ihpix_outputs',
                MyLogica.ihpix_outputs,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/iot-portal',
                u'iot_portal',
                MyLogica.iot_portal,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/flood-drought-portal',
                u'flood_drought_portal',
                MyLogica.flood_drought_portal,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/citizen-science-portal',
                u'citizen_science_portal',
                MyLogica.citizen_science_portal,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/initiatives',
                u'initiatives',
                MyLogica.initiatives,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/memberstates/<name>',
                u'redirect_paises',
                MyLogica.redirect_to_group,
                methods=['GET']
    )
            blueprint.add_url_rule(
                u'/initiatives/<name>',
                u'redirect_paises',
                MyLogica.redirect_to_group,
                methods=['GET']
    )
# Deshabilita el registro de usuarios
#            blueprint.add_url_rule(
#                u'/user/register',
#                u'redirect_to_colab',
#                MyLogica.redirect_to_colab,
#                methods=['GET']
#    )

            # People directory
            blueprint.add_url_rule(
                u'/people',
                u'people_index',
                MyLogica.people_index,
                methods=['GET']
            )

            # Organization tabs
            blueprint.add_url_rule(
                u'/organization/<name>/people',
                u'organization_people',
                MyLogica.organization_people,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/organization/<name>/publications',
                u'organization_publications',
                MyLogica.organization_publications,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/organization/<name>/news',
                u'organization_news',
                MyLogica.organization_news,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/organization/<name>/events',
                u'organization_events',
                MyLogica.organization_events,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/organization/<name>/data-stories',
                u'organization_data_stories',
                MyLogica.organization_data_stories,
                methods=['GET']
            )

            # Membership request
            blueprint.add_url_rule(
                u'/organization/<name>/request-membership',
                u'request_membership',
                MyLogica.request_membership,
                methods=['GET', 'POST']
            )

            # Membership requests management dashboard
            blueprint.add_url_rule(
                u'/organization/<name>/membership-requests',
                u'membership_requests',
                MyLogica.membership_requests,
                methods=['GET', 'POST']
            )

            # Membership requests overview (multi-org landing page)
            blueprint.add_url_rule(
                u'/membership-requests',
                u'membership_requests_overview',
                MyLogica.membership_requests_overview,
                methods=['GET']
            )

            # User profile tabs
            blueprint.add_url_rule(
                u'/user/<id>/documents',
                u'user_documents',
                MyLogica.user_documents,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/user/<id>/organizations',
                u'user_organizations',
                MyLogica.user_organizations,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/user/<id>/data-stories',
                u'user_data_stories',
                MyLogica.user_data_stories,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/user/<id>/news',
                u'user_news',
                MyLogica.user_news,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/user/<id>/events',
                u'user_events',
                MyLogica.user_events,
                methods=['GET']
            )

            blueprint.add_url_rule(
                u'/dataset/<id>/resources_ajax',
                u'dataset_resources_ajax',
                MyLogica.dataset_resources_ajax,
                methods=['GET']
            )

            # Featured datasets admin panel (sysadmin only)
            blueprint.add_url_rule(
                u'/ckan-admin/featured-datasets',
                u'featured_datasets_admin',
                MyLogica.featured_datasets_admin,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-datasets/search',
                u'featured_datasets_search',
                MyLogica.featured_datasets_search,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-datasets/add',
                u'featured_datasets_add',
                MyLogica.featured_datasets_add,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-datasets/remove',
                u'featured_datasets_remove',
                MyLogica.featured_datasets_remove,
                methods=['POST']
            )

            # Featured publications admin panel (sysadmin only)
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications',
                u'featured_publications_admin',
                MyLogica.featured_publications_admin,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications/create',
                u'featured_publications_create',
                MyLogica.featured_publications_create,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications/update',
                u'featured_publications_update',
                MyLogica.featured_publications_update,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications/delete',
                u'featured_publications_delete',
                MyLogica.featured_publications_delete,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications/reorder',
                u'featured_publications_reorder',
                MyLogica.featured_publications_reorder,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/featured-publications/upload-image',
                u'featured_publications_upload_image',
                MyLogica.featured_publications_upload_image,
                methods=['POST']
            )

            # Portal cards admin panel (sysadmin only)
            # Static routes must be registered before the wildcard <portal_id>
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/create',
                u'portal_cards_create',
                MyLogica.portal_cards_create,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/update',
                u'portal_cards_update',
                MyLogica.portal_cards_update,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/delete',
                u'portal_cards_delete',
                MyLogica.portal_cards_delete,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/reorder',
                u'portal_cards_reorder',
                MyLogica.portal_cards_reorder,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/upload-image',
                u'portal_cards_upload_image',
                MyLogica.portal_cards_upload_image,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/portal-cards/<portal_id>',
                u'portal_cards_admin',
                MyLogica.portal_cards_admin,
                methods=['GET']
            )

            # Bug ticket system
            blueprint.add_url_rule(
                u'/bug-tickets',
                u'bug_tickets_list',
                MyLogica.bug_tickets_list,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/bug-tickets/new',
                u'bug_tickets_new',
                MyLogica.bug_tickets_new,
                methods=['GET', 'POST']
            )
            blueprint.add_url_rule(
                u'/bug-tickets/<id>',
                u'bug_tickets_show',
                MyLogica.bug_tickets_show,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/bug-tickets/<id>/close',
                u'bug_tickets_close',
                MyLogica.bug_tickets_close,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/bug-tickets/<id>/update-status',
                u'bug_tickets_update_status',
                MyLogica.bug_tickets_update_status,
                methods=['POST']
            )

            # Sysadmin user management panel
            blueprint.add_url_rule(
                u'/ckan-admin/users',
                u'users_admin',
                MyLogica.users_admin,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/search',
                u'users_admin_search',
                MyLogica.users_admin_search,
                methods=['GET']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/create',
                u'users_admin_create',
                MyLogica.users_admin_create,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/reset-password',
                u'users_admin_reset_password',
                MyLogica.users_admin_reset_password,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/delete',
                u'users_admin_delete',
                MyLogica.users_admin_delete,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/purge',
                u'users_admin_purge',
                MyLogica.users_admin_purge,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/reactivate',
                u'users_admin_reactivate',
                MyLogica.users_admin_reactivate,
                methods=['POST']
            )
            blueprint.add_url_rule(
                u'/ckan-admin/users/toggle-sysadmin',
                u'users_admin_toggle_sysadmin',
                MyLogica.users_admin_toggle_sysadmin,
                methods=['POST']
            )

            # Register /dataset/new explicitly BEFORE /dataset/<id> so that
            # Flask does not capture "new" as a dataset id.  We delegate to
            # the scheming CreateView which is what IDatasetForm would use.
            from ckanext.scheming.views import SchemingCreateView
            blueprint.add_url_rule(
                u'/dataset/new',
                u'dataset_new',
                SchemingCreateView.as_view(str(u'theme_dataset_new')),
                methods=['GET', 'POST'],
                defaults={u'package_type': u'dataset'},
            )

            # Override CKAN core dataset read view with optimized version
            # that uses batch SQL for resource views instead of N+1 queries
            blueprint.add_url_rule(
                u'/dataset/<id>',
                u'dataset_read',
                lambda id: MyLogica.dataset_read('dataset', id),
                methods=['GET']
            )

            return blueprint
        
        def get_helpers(self):
            return {
                 'get_latest_courses': self.get_latest_courses,
                 'get_featured_datasets': self.get_featured_datasets,
                 'get_organization_image_by_name': self.get_organization_image_by_name,
                 'get_featured_datasets_filtered': self.get_featured_datasets_filtered,
                 'theme_ejemplo_get_paged_resources': helpers.get_paged_resources,
                 'theme_ejemplo_markdown_excerpt': helpers.markdown_excerpt,
                 'theme_ejemplo_site_statistics': self.get_site_statistics_cached,
                 'get_member_states_groups_list': self.get_member_states_groups_list,
                 'get_initiatives_groups_list': self.get_initiatives_groups_list,
                 'get_people_directory': helpers.get_people_directory,
                 'get_user_profile': helpers.get_user_profile,
                 'get_org_members_with_profiles': helpers.get_org_members_with_profiles,
                 'get_org_statistics': helpers.get_org_statistics,
                 'get_org_publications': helpers.get_org_publications,
                 'get_country_list': helpers.get_country_list,
                 'is_org_member': helpers.is_org_member,
                 'is_org_admin': helpers.is_org_admin,
                 'get_pending_membership_requests_count': helpers.get_pending_membership_requests_count,
                 'get_user_admin_orgs': helpers.get_user_admin_orgs,
                 'has_pending_membership_request': helpers.has_pending_membership_request,
                 'get_recently_added': self.get_recently_added,
                 'get_featured_publications': helpers.get_featured_publications,
                 'get_open_bug_tickets_count': helpers.get_open_bug_tickets_count,
                 'get_dataset_tracking': helpers.get_dataset_tracking,
                 'get_resource_downloads': helpers.get_resource_downloads,
                 'get_tracking_totals': helpers.get_tracking_totals,
                 'get_popular_datasets': helpers.get_popular_datasets,
                 'get_popular_resources': helpers.get_popular_resources,
                 }

        # IActions
        def get_actions(self):
            return {
                'user_show': custom_actions.user_show,
                'user_update': custom_actions.user_update,
                'people_list': custom_actions.people_list,
                'organization_people': custom_actions.organization_people,
                'membership_request_create': custom_actions.membership_request_create,
                'membership_request_list': custom_actions.membership_request_list,
                'membership_request_process': custom_actions.membership_request_process,
                'membership_request_count': custom_actions.membership_request_count,
                'featured_dataset_list': custom_actions.featured_dataset_list,
                'featured_dataset_add': custom_actions.featured_dataset_add,
                'featured_dataset_remove': custom_actions.featured_dataset_remove,
                'featured_publication_list': custom_actions.featured_publication_list,
                'featured_publication_create': custom_actions.featured_publication_create,
                'featured_publication_update': custom_actions.featured_publication_update,
                'featured_publication_delete': custom_actions.featured_publication_delete,
                'featured_publication_reorder': custom_actions.featured_publication_reorder,
                'portal_card_list': custom_actions.portal_card_list,
                'portal_card_create': custom_actions.portal_card_create,
                'portal_card_update': custom_actions.portal_card_update,
                'portal_card_delete': custom_actions.portal_card_delete,
                'portal_card_reorder': custom_actions.portal_card_reorder,
                'bug_ticket_create': custom_actions.bug_ticket_create,
                'bug_ticket_list': custom_actions.bug_ticket_list,
                'bug_ticket_show': custom_actions.bug_ticket_show,
                'bug_ticket_update': custom_actions.bug_ticket_update,
                'bug_ticket_api_list': custom_actions.bug_ticket_api_list,
                'admin_user_list': custom_actions.admin_user_list,
                'admin_user_reset_password': custom_actions.admin_user_reset_password,
                'admin_user_delete': custom_actions.admin_user_delete,
                'admin_user_purge': custom_actions.admin_user_purge,
                'admin_user_reactivate': custom_actions.admin_user_reactivate,
                'admin_user_toggle_sysadmin': custom_actions.admin_user_toggle_sysadmin,
                'admin_user_create': custom_actions.admin_user_create,
            }

        # IAuthFunctions
        def get_auth_functions(self):
            return {
                'membership_request_create': custom_auth.membership_request_create,
                'membership_request_list': custom_auth.membership_request_list,
                'membership_request_process': custom_auth.membership_request_process,
                'membership_request_count': custom_auth.membership_request_count,
                'featured_dataset_list': custom_auth.featured_dataset_list,
                'featured_dataset_add': custom_auth.featured_dataset_add,
                'featured_dataset_remove': custom_auth.featured_dataset_remove,
                'featured_publication_list': custom_auth.featured_publication_list,
                'featured_publication_create': custom_auth.featured_publication_create,
                'featured_publication_update': custom_auth.featured_publication_update,
                'featured_publication_delete': custom_auth.featured_publication_delete,
                'featured_publication_reorder': custom_auth.featured_publication_reorder,
                'portal_card_list': custom_auth.portal_card_list,
                'portal_card_create': custom_auth.portal_card_create,
                'portal_card_update': custom_auth.portal_card_update,
                'portal_card_delete': custom_auth.portal_card_delete,
                'portal_card_reorder': custom_auth.portal_card_reorder,
                'bug_ticket_create': custom_auth.bug_ticket_create,
                'bug_ticket_list': custom_auth.bug_ticket_list,
                'bug_ticket_show': custom_auth.bug_ticket_show,
                'bug_ticket_update': custom_auth.bug_ticket_update,
                'bug_ticket_api_list': custom_auth.bug_ticket_api_list,
                'admin_user_list': custom_auth.admin_user_list,
                'admin_user_reset_password': custom_auth.admin_user_reset_password,
                'admin_user_delete': custom_auth.admin_user_delete,
                'admin_user_purge': custom_auth.admin_user_purge,
                'admin_user_reactivate': custom_auth.admin_user_reactivate,
                'admin_user_toggle_sysadmin': custom_auth.admin_user_toggle_sysadmin,
                'admin_user_create': custom_auth.admin_user_create,
            }
        
        def get_member_states_groups_list(self):
            """Obtiene los grupos de member-states como lista de tuplas (name, display_name).
            Uses a direct DB query to avoid N+1 overhead from group_show(include_groups=True).
            """
            cache_ttl = _get_cache_ttl('ckanext.theme_ejemplo.groups_cache_ttl', 300)
            now = time.time()
            if cache_ttl > 0 and _member_states_cache['data'] is not None and now < _member_states_cache['expires']:
                return _member_states_cache['data']

            try:
                from ckan import model as ckan_model
                ms_group = ckan_model.Group.get('member-states')
                if not ms_group:
                    raise toolkit.ObjectNotFound("Group 'member-states' not found")
                members = (
                    ckan_model.Session.query(ckan_model.Group.name, ckan_model.Group.title)
                    .join(ckan_model.Member, ckan_model.Member.table_id == ckan_model.Group.id)
                    .filter(
                        ckan_model.Member.group_id == ms_group.id,
                        ckan_model.Member.state == 'active',
                        ckan_model.Member.table_name == 'group',
                        ckan_model.Group.state == 'active',
                    )
                    .order_by(ckan_model.Group.title)
                    .all()
                )
                result = [(g.name, g.title or g.name) for g in members if g.name]
                log.debug(f"Member states groups found: {len(result)}")
                if cache_ttl > 0:
                    _member_states_cache['data'] = result
                    _member_states_cache['expires'] = now + cache_ttl
                return result
            except toolkit.ObjectNotFound:
                log.warning("Group 'member-states' not found")
                result = []
                if cache_ttl > 0:
                    _member_states_cache['data'] = result
                    _member_states_cache['expires'] = now + cache_ttl
                return result
            except Exception as e:
                log.error(f"Error obteniendo member-states groups: {e}")
                return _member_states_cache['data'] or []
        
        def get_initiatives_groups_list(self):
            """Obtiene los grupos de initiatives (excluyendo member-states).
            Uses a direct DB query to avoid N+1 overhead from group_list(all_fields=True).
            """
            cache_ttl = _get_cache_ttl('ckanext.theme_ejemplo.groups_cache_ttl', 300)
            now = time.time()
            if cache_ttl > 0 and _initiatives_cache['data'] is not None and now < _initiatives_cache['expires']:
                return _initiatives_cache['data']

            try:
                from ckan import model as ckan_model
                # Intentar obtener member-states group names
                member_states = self.get_member_states_groups_list()
                member_states_names = {name for name, _ in member_states}
                member_states_names.add('member-states')
                
                groups = (
                    ckan_model.Session.query(ckan_model.Group.name, ckan_model.Group.title)
                    .filter(
                        ckan_model.Group.type == 'group',
                        ckan_model.Group.state == 'active',
                        ~ckan_model.Group.name.in_(member_states_names) if member_states_names else True,
                    )
                    .order_by(ckan_model.Group.title)
                    .all()
                )
                
                initiatives = [(g.name, g.title or g.name) for g in groups]
                log.debug(f"Initiatives groups found: {len(initiatives)}")
                if cache_ttl > 0:
                    _initiatives_cache['data'] = initiatives
                    _initiatives_cache['expires'] = now + cache_ttl
                return initiatives
            except Exception as e:
                log.error(f"Error obteniendo initiatives groups: {e}")
                return _initiatives_cache['data'] or []
        
        def get_latest_courses(self):
            """
            Mejorado con:
            - Session reutilizable
            - Manejo robusto de errores
            - Cache TTL configurable
            - Timeout apropiado
            """
            cache_ttl = _get_cache_ttl('ckanext.theme_ejemplo.courses_cache_ttl', 600)
            now = time.time()
            if cache_ttl > 0 and _courses_cache['data'] is not None and now < _courses_cache['expires']:
                return _courses_cache['data']

            try:
                url = 'https://openlearning.unesco.org/api/courses/v1/courses/'
                params = {'search_term': 'water'}

                response = http_session.get(url, params=params, timeout=5)
                response.raise_for_status()  # Lanza excepción para status HTTP de error

                courses = response.json().get('results', [])
                result = courses[:8]  # Limitar a un máximo de 8 cursos
            except requests.exceptions.Timeout:
                log.warning("Timeout al obtener cursos de UNESCO")
                result = _courses_cache['data'] or []
            except requests.exceptions.RequestException as e:
                log.warning(f"Error HTTP al obtener cursos de UNESCO: {e}")
                result = _courses_cache['data'] or []
            except (ValueError, json.JSONDecodeError) as e:
                log.warning(f"Error al parsear cursos de UNESCO: {e}")
                result = _courses_cache['data'] or []
            except Exception as e:
                log.error(f"Error inesperado al obtener cursos: {e}")
                result = _courses_cache['data'] or []

            if cache_ttl > 0:
                _courses_cache['data'] = result
                _courses_cache['expires'] = now + cache_ttl
            return result

        def get_recently_added(self, item_type='dataset', limit=5):
            """Returns recently created datasets or documents, with TTL cache."""
            if item_type == 'documents':
                cache = _recently_added_documents_cache
            else:
                cache = _recently_added_datasets_cache

            cache_ttl = _get_cache_ttl('ckanext.theme_ejemplo.recently_added_cache_ttl', 300)
            now = time.time()
            if cache_ttl > 0 and cache['data'] is not None and now < cache['expires']:
                return cache['data']

            try:
                result = toolkit.get_action('package_search')(
                    {'ignore_auth': True},
                    {
                        'fq': 'type:{}'.format(item_type),
                        'sort': 'metadata_created desc',
                        'rows': limit,
                    }
                )
                items = result.get('results', [])
            except Exception as e:
                log.error('Error getting recently added %s: %s', item_type, e)
                items = cache['data'] or []

            if cache_ttl > 0:
                cache['data'] = items
                cache['expires'] = now + cache_ttl
            return items

        def _get_home_cache_ttl(self):
            try:
                return max(0, toolkit.asint(toolkit.config.get('ckanext.theme_ejemplo.home_cache_ttl', 300)))
            except Exception:
                return 300
            except requests.exceptions.RequestException as e:
                log.error(f"Error al obtener cursos de UNESCO: {e}")
                return []
            except json.JSONDecodeError as e:
                log.error(f"Error al parsear respuesta JSON de UNESCO: {e}")
                return []
            except Exception as e:
                log.error(f"Error inesperado al obtener cursos: {e}")
                return []
            
        def get_featured_datasets(self):
            """Mejorado con mejor manejo de errores y logging"""
            try:
                data_dict = {
                    'fq': 'tags:FeaturedDataset',  # Filtro por el tag 'FeaturedDataset'
                    'rows': 12  # Número de resultados que deseas obtener, ajusta según necesidad
                }
                search_result = toolkit.get_action('package_search')(None, data_dict)
                return search_result.get('results', [])
            except Exception as e:
                log.error(f"Error getting featured datasets: {e}")
                return []  # Retornar lista vacía en lugar de abortar
                
        def _get_featured_datasets_filtered_uncached(self, tag, user):
            try:
                if not user:
                    return []

                # Construir la consulta para buscar datasets destacados
                query = '( followers:yes AND tags:{tag} ) OR ( tags:{tag} AND creator_user_id:{user} )'.format(
                    tag=tag, user=user
                )

                data_dict = {
                    'q': query,
                    'rows': 12  # Ajustar según sea necesario para obtener todos los datasets destacados
                }
                search_result = toolkit.get_action('package_search')(None, data_dict)

                # Limitar la cantidad de resultados a devolver
                return search_result.get('results', [])
            except Exception as e:
                log.error(f'Error in get_featured_datasets_filtered: {e}')
                return []

        @lru_cache(maxsize=64)
        def _get_featured_datasets_filtered_cached(self, tag, user, cache_buster):
            return self._get_featured_datasets_filtered_uncached(tag, user)

        def get_featured_datasets_filtered(self, tag='FeaturedDataset', user=None):
            """Mejorado con cache TTL configurable"""
            cache_ttl = self._get_home_cache_ttl()
            if cache_ttl <= 0:
                return self._get_featured_datasets_filtered_uncached(tag, user)
            cache_buster = int(time.time() / cache_ttl)
            return self._get_featured_datasets_filtered_cached(tag, user, cache_buster)

        def _get_site_statistics_uncached(self):
            stats = {}
            stats['dataset_count'] = toolkit.get_action('package_search')({}, {'rows': 1}).get('count', 0)
            stats['group_count'] = len(toolkit.get_action('group_list')({}, {}))
            stats['organization_count'] = len(toolkit.get_action('organization_list')({}, {}))
            return stats

        @lru_cache(maxsize=16)
        def _get_site_statistics_cached(self, cache_buster):
            return self._get_site_statistics_uncached()

        def get_site_statistics_cached(self):
            cache_ttl = self._get_home_cache_ttl()
            if cache_ttl <= 0:
                return self._get_site_statistics_uncached()
            cache_buster = int(time.time() / cache_ttl)
            return self._get_site_statistics_cached(cache_buster)

        def get_organization_image_by_name(self, dataset_name):
            """
            Mejorado con:
            - Cache para evitar llamadas repetidas
            - Mejor manejo de errores
            - Validación de entrada
            """
            if not dataset_name:
                return None
                
            # Verificar cache
            if dataset_name in self._organization_cache:
                return self._organization_cache[dataset_name]
                
            try:
                # Obtener el dataset por nombre
                dataset = toolkit.get_action('package_show')(None, {'id': dataset_name})
                
                if not dataset or 'organization' not in dataset or not dataset['organization']:
                    self._organization_cache[dataset_name] = None
                    return None
                
                org_id = dataset['organization']['id']
                
                # Obtener la organización por ID
                organization = toolkit.get_action('organization_show')(None, {'id': org_id})
                
                image_url = organization.get('image_display_url') if organization else None
                
                # Guardar en cache
                self._organization_cache[dataset_name] = image_url
                return image_url
                
            except toolkit.ObjectNotFound:
                log.warning(f"Dataset or organization not found: {dataset_name}")
                self._organization_cache[dataset_name] = None
                return None
            except Exception as e:
                log.error(f"Error getting organization image for {dataset_name}: {e}")
                return None
