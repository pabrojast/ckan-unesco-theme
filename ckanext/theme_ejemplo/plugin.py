# encoding: utf-8

'''plugin.py

'''
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import Blueprint
from ckanext.theme_ejemplo.controller import MyLogica

class ThemeEjemploPlugin(plugins.SingletonPlugin):
        '''An example theme plugin.

        '''
        # Declare that this class implements IConfigurer.
        plugins.implements(plugins.IConfigurer)
        plugins.implements(plugins.IBlueprint)

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
                u'/iniciatives',
                u'iniciatives',
                MyLogica.iniciatives,
                methods=['GET']
            )

            return blueprint