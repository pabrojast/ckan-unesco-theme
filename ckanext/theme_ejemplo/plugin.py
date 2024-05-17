# encoding: utf-8

'''plugin.py

'''
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import requests


from flask import Blueprint
from ckanext.theme_ejemplo.controller import MyLogica

class ThemeEjemploPlugin(plugins.SingletonPlugin):
        '''An example theme plugin.

        '''
        # Declare that this class implements IConfigurer.
        plugins.implements(plugins.IConfigurer)
        plugins.implements(plugins.IBlueprint)
        plugins.implements(plugins.ITemplateHelpers)  # Implementar ITemplateHelpers

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
                response = requests.get('https://openlearning.unesco.org/api/courses/v1/courses/?search_term=water')
                courses = response.json().get('results', []) if response.status_code == 200 else []
                return courses
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
        
        def get_featured_datasets_filtered(self, tag='FeaturedDataset', user=None):
            try:
                query = 'tags:{tag}'.format(tag=tag)
                if user:
                    # Modificamos la query para incluir el id del usuario como creador y
                    # también verificamos si el usuario sigue el conjunto de datos
                    query += ' AND (creator_user_id:"{user}" OR followers_user_id:"{user}")'.format(user=user)
                data_dict = {
                    'fq': query,
                    'rows': 6  # Número de resultados que deseas obtener, ajusta según necesidad
                }
                search_result = toolkit.get_action('package_search')(None, data_dict)
                return search_result['results']
            except Exception as e:
                toolkit.abort(500, str(e))
        

        def get_organization_image_by_name(self, dataset_name):
            try:
                # Obtener el dataset por nombre
                dataset = toolkit.get_action('package_show')(None, {'id': dataset_name})
                if dataset and 'organization' in dataset:
                    org_id = dataset['organization']['id']
                    # Obtener la organización por ID
                    organization = toolkit.get_action('organization_show')(None, {'id': org_id})
                    if organization and 'image_url' in organization:
                        return organization['image_url']
                return None
            except Exception as e:
                toolkit.abort(500, str(e))