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
import logging
from functools import lru_cache

# Configurar logging
log = logging.getLogger(__name__)

# Session reutilizable para requests HTTP
http_session = requests.Session()
# Timeout optimizado: (connect_timeout, read_timeout)
# connect_timeout: tiempo para establecer conexión
# read_timeout: tiempo para recibir respuesta
http_session.timeout = (5, 10)  # 5s conexión + 10s respuesta = máximo 15s total

class ThemeEjemploPlugin(plugins.SingletonPlugin, DefaultTranslation):
        '''An example theme plugin.

        '''
        # Declare that this class implements IConfigurer.
        plugins.implements(plugins.IConfigurer)
        plugins.implements(plugins.IBlueprint)
        plugins.implements(plugins.ITemplateHelpers)  # Implementar ITemplateHelpers
        plugins.implements(plugins.IPackageController, inherit=True)
        plugins.implements(plugins.ITranslation)  # Implementar ITemplateHelpers

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
                
                # Optimización: Solo obtener followers si es necesario
                featured_ = 'no'  # Valor por defecto
                try:
                    sysadmin_context = {
                        'user': 'ckan.system',
                        'ignore_auth': True
                    }
                    package = toolkit.get_action('dataset_follower_list')(sysadmin_context, {'id': package_id})
                    
                    #to define featured dataset
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
            """Procesamiento optimizado de facetas"""
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
                                    dataset_dict[facet] = json.loads(data)
                            except json.JSONDecodeError:
                                dataset_dict[facet] = data
                    else:
                        dataset_dict.pop(facet, None)  # Más eficiente que 'del'
            except Exception as e:
                log.error(f"Error processing facets: {e}")

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

            return blueprint
        
        def get_helpers(self):
            # Registrar el helper 'get_latest_courses'
            return {
                 'get_latest_courses': self.get_latest_courses,
                 'get_featured_datasets': self.get_featured_datasets,  # Nuevo helper añadido
                 'get_organization_image_by_name': self.get_organization_image_by_name,  # Cambio de nombre del helper
                 'get_featured_datasets_filtered': self.get_featured_datasets_filtered,
                 'theme_ejemplo_get_paged_resources': helpers.get_paged_resources
                 }
        
        @lru_cache(maxsize=32)  # Cache para evitar llamadas repetidas
        def get_latest_courses(self):
            """
            Mejorado con:
            - Session reutilizable
            - Manejo robusto de errores
            - Cache LRU
            - Timeout apropiado
            """
            try:
                url = 'https://openlearning.unesco.org/api/courses/v1/courses/'
                params = {'search_term': 'water'}
                
                response = http_session.get(url, params=params, timeout=5)
                response.raise_for_status()  # Lanza excepción para status HTTP de error
                
                courses = response.json().get('results', [])
                return courses[:8]  # Limitar a un máximo de 8 cursos
                
            except requests.exceptions.Timeout:
                log.warning("Timeout al obtener cursos de UNESCO")
                return []
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
                
        def get_featured_datasets_filtered(self, tag='FeaturedDataset', user=None):
            """Mejorado con mejor manejo de errores"""
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