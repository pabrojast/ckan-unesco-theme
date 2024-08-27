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

class ThemeEjemploPlugin(plugins.SingletonPlugin, DefaultTranslation):
        '''An example theme plugin.

        '''
        # Declare that this class implements IConfigurer.
        plugins.implements(plugins.IConfigurer)
        plugins.implements(plugins.IBlueprint)
        plugins.implements(plugins.ITemplateHelpers)  # Implementar ITemplateHelpers
        plugins.implements(plugins.IPackageController, inherit=True)
        plugins.implements(plugins.ITranslation)  # Implementar ITemplateHelpers

        #this fix solr-bbox search
        #for ckan v2.9
        def before_index(self, dataset_dict):
            return self.before_dataset_index(dataset_dict)
        #for ckan v2.10
        def before_dataset_index(self, dataset_dict):

            # When using the default `solr-bbox` backend (based on bounding boxes), you need to
            # include the following fields in the returned dataset_dict:
            # Check if spatial exists and do nothing
            package_id = dataset_dict.get('id')
            sysadmin_context = {
                'user': 'ckan.system',
                'ignore_auth': True
            }
            package = toolkit.get_action('dataset_follower_list')(sysadmin_context, {'id': package_id })

            #to define featured dataset
            if(any(user['sysadmin'] for user in package)):
                featured_ = 'yes'
            else:
                featured_ = 'no'
            dataset_dict['followers'] = featured_
            

            #better compatibility    
            if 'dcat_type' not in dataset_dict or not dataset_dict['dcat_type']:
                dataset_dict['dcat_type'] = 'http://inspire.ec.europa.eu/metadata-codelist/ResourceType/dataset'

            
            if 'spatial' in dataset_dict and dataset_dict['spatial']:
                pass
            else:
                # Extraer todas las 'id'      
                xmin = dataset_dict.get('xmin')
                xmax = dataset_dict.get('xmax')
                ymin = dataset_dict.get('ymin')
                ymax = dataset_dict.get('ymax')
                
                def is_within_valid_range(x, y):
                    return -180 <= x <= 180 and -90 <= y <= 90
                
                if all(value is not None and value != '' for value in [xmin, xmax, ymin, ymax]):
                    try:
                        # Copiar los valores a los campos esperados por Solr
                        xmin = float(xmin)
                        xmax = float(xmax)
                        ymin = float(ymin)
                        ymax = float(ymax)
                    
                        # Verificar si las coordenadas están dentro del rango válido
                        if is_within_valid_range(xmin, ymin) and is_within_valid_range(xmax, ymax):
                            # Crear un polígono rectangular usando las coordenadas
                            bbox = shapely.geometry.box(xmin, ymin, xmax, ymax)
                            wkt = bbox.wkt
                        
                            # Solo establecer el campo `spatial_geom` si no existe o está vacío
                            if 'spatial_geom' not in dataset_dict or not dataset_dict['spatial_geom']:
                                dataset_dict['spatial_geom'] = wkt

                        else:
                            print("Coordenadas fuera de los límites válidos, omitiendo dataset.")
                        
                    except ValueError as e:
                        # Log the error and handle it (e.g., skip this dataset or set default values)
                        print(f"Error converting bounding box values to float: {e}")
                        #con el expect no hacemos nada
                        return dataset_dict
            """ from schemingdcat
            Processes the data dictionary before indexing.
            Iterates through each facet defined in the system's facets dictionary. For each facet present in the data dictionary, it attempts to parse its value as JSON. If the value is a valid JSON string, it replaces the original string value with the parsed JSON object. If the value cannot be parsed as JSON (e.g., because it's not a valid JSON string), it leaves the value unchanged. Facets present in the data dictionary but not containing any data are removed.
            Args:
                data_dict (dict): The data dictionary to be processed. It's expected to contain keys corresponding to facet names with their associated data as values.
            Returns:
                dict: The processed data dictionary with JSON strings parsed into objects where applicable and empty facets removed.
            """
            for facet, label in utils.get_facets_dict().items():
                    data = dataset_dict.get(facet)
                    #log.debug("[before_index] Data ({1}) in facet: {0}".format(data, facet))
                    if data:
                        if isinstance(data, str):
                            try:
                                if(facet == "spatial"):
                                    dataset_dict[facet] = json.dumps(data)
                                else:
                                    dataset_dict[facet] = json.loads(data)
                            except json.decoder.JSONDecodeError:
                                dataset_dict[facet] = data
                    else:
                        if facet in dataset_dict:
                            del dataset_dict[facet]

            # deprectado
            # if all(value is not None and value != '' for value in [xmin, xmax, ymin, ymax]):
            #     try:
            #         # Copiar los valores a los campos esperados por Solr
            #         dataset_dict["minx"] = float(xmin)
            #         dataset_dict["maxx"] = float(xmax)
            #         dataset_dict["miny"] = float(ymin)
            #         dataset_dict["maxy"] = float(ymax)
            #     except ValueError as e:
            #         # Log the error and handle it (e.g., skip this dataset or set default values)
            #         print(f"Error converting bounding box values to float: {e}")
            #         # Optionally, you can set default values or take other actions here
            #         dataset_dict["minx"] = None
            #         dataset_dict["maxx"] = None
            #         dataset_dict["miny"] = None
            #         dataset_dict["maxy"] = None
            # When using the `solr-spatial-field` backend, you need to include the `spatial_geom`
            # field in the returned dataset_dict. This should be a valid geometry in WKT format.
            # Shapely can help you get the WKT representation of your gemetry if you have it in GeoJSON:
            #si existe el campo, no se deberia hacer nada -- POR HACER --
            # No olvides devolver el dict
            return dataset_dict


        def update_config(self, config):
            # Add this plugin's templates dir to CKAN's extra_template_paths, so
            # that CKAN will use this plugin's custom templates.
            # 'templates' is the path to the templates dir, relative to this
            # plugin.py file.
            toolkit.add_template_directory(config, 'templates')
            #para el css y archivos necesarios
            toolkit.add_public_directory(config,'public')

        def get_blueprint(self):
            
            blueprint = Blueprint(self.name, self.__module__)        
        
            blueprint.add_url_rule(
                u'/memberstates',
                u'memberstates',
                MyLogica.memberstates,
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
                 'get_featured_datasets_filtered': self.get_featured_datasets_filtered
                 }
        
        def get_latest_courses(self):
            try:
                response = requests.get('https://openlearning.unesco.org/api/courses/v1/courses/?search_term=water', timeout=3)
                if response.status_code == 200:
                    courses = response.json().get('results', [])
                    return courses[:8]  # Limitar a un máximo de 8 cursos
                else:
                    return []
            except requests.RequestException:
                return []
            
        def get_featured_datasets(self):
            # Usar la función de búsqueda de CKAN para encontrar datasets por tag
            try:
                data_dict = {
                    'fq': 'tags:FeaturedDataset',  # Filtro por el tag 'FeaturedDataset'
                    'rows': 6  # Número de resultados que deseas obtener, ajusta según necesidad
                }
                search_result = toolkit.get_action('package_search')(None, data_dict)
                return search_result['results']
            except Exception as e:
                toolkit.abort(500, str(e))
        
        # def get_featured_datasets_filtered(self, tag='FeaturedDataset', user=None):
        #     try:
        #         query = 'tags:{tag}'.format(tag=tag)
        #         if user:
        #             # Modificamos la query para incluir el id del usuario como creador y
        #             # también verificamos si el usuario sigue el conjunto de datos
        #             query += ' AND (creator_user_id:"{user}" OR followers_user_id:"{user}")'.format(user=user)
        #         data_dict = {
        #             'fq': query,
        #             'rows': 6  # Número de resultados que deseas obtener, ajusta según necesidad
        #         }
        #         search_result = toolkit.get_action('package_search')(None, data_dict)
        #         return search_result['results']
        #     except Exception as e:
        #         toolkit.abort(500, str(e))
                
        def get_featured_datasets_filtered(self, tag='FeaturedDataset', user=None):
            try:
                # Obtener la lista de datasets seguidos por el usuario

                if user:
                    # Construir la consulta para buscar datasets destacados
                    
                    query = '( followers:yes AND tags:{tag} ) OR ( tags:{tag} AND creator_user_id:{user} )'.format(tag=tag, user=user)
                    print(query)
                    data_dict = {
                        'q': query,
                        'rows': 6  # Ajustar según sea necesario para obtener todos los datasets destacados
                    }
                    search_result = toolkit.get_action('package_search')(None, data_dict)
                    print(search_result)
                    # Limitar la cantidad de resultados a devolver
                    return search_result.get('results', [])
                
            except Exception as e:
                print('Error in Featured Dataset')
                search_result = []
                return search_result

        def get_organization_image_by_name(self, dataset_name):
            try:
                # Obtener el dataset por nombre
                dataset = toolkit.get_action('package_show')(None, {'id': dataset_name})
                if dataset and 'organization' in dataset:
                    org_id = dataset['organization']['id']
                    # Obtener la organización por ID
                    organization = toolkit.get_action('organization_show')(None, {'id': org_id})
                    if organization and 'image_display_url' in organization:
                        return organization['image_display_url']
                return None
            except Exception as e:
                toolkit.abort(500, str(e))