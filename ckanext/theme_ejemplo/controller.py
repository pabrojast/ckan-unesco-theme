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

group_type = u'group'

class MyLogica():
        def memberstates():
            
            if request.method == 'GET':

                #get the params
                q = c.q = request.params.get('q', '')
                sort_by = c.sort_by_selected = request.params.get('sort')

                # grupos = toolkit.get_action('group_list')(
                # data_dict={'q': q, 'include_dataset_count': True, 'all_fields': True, 'include_groups': True, 'limit' : 1000  })
                # # Función para verificar si un grupo pertenece al grupo-papa
                grupos = toolkit.get_action('group_show')(
                data_dict={'id': 'member-states', 'include_groups': True })

                # print(grupos)
                # def pertenece_a_grupo_papa(grupo):
                #     return any(g['name'] == 'member-states' for g in grupo['groups'])

                # # Filtrar los grupos que pertenecen al grupo-papa y luego obtener solo sus nombres
                # nombres_grupos_hijo_de_grupo_papa = map(lambda grupo: grupo['name'], filter(pertenece_a_grupo_papa, grupos))

                # # Convertir el resultado en una lista y imprimir
                # nombres_grupos_hijo_de_grupo_papa = list(nombres_grupos_hijo_de_grupo_papa)
                # print(nombres_grupos_hijo_de_grupo_papa)
                #print(grupos)
                nombres_grupos_hijo_de_grupo_papa = grupos["result"]
                page = h.get_page_number(request.params) or 1
                items_per_page = 21
                groups = toolkit.get_action('group_list')(
                data_dict={'include_dataset_count': True, 'all_fields': True, 'groups': nombres_grupos_hijo_de_grupo_papa, 'include_groups': True, 'limit' : 1000, 'offset' : items_per_page * (page - 1), 'sort': sort_by})
                print(groups)
                groupcount = len(groups)+(page - 1)*items_per_page
                c.page = h.Page(
                collection=groups,
                page=page,
                url=h.pager_url,
                items_per_page=items_per_page,
                )
                #you will get something like
                #[{'approval_status': 'approved', 'created': '2023-11-15T17:04:44.712875', 'description': '', 'display_name': 'ukgov', 'id': 'ff5b411d-dedd-4560-ac93-b59621644e61', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'ukgov', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.713652', 'description': '', 'display_name': 'test1', 'id': 'c1738e32-ced0-41dd-bb7d-251df5aa46b1', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test1', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714297', 'description': '', 'display_name': 'test2', 'id': 'cc89cb78-cfb1-47ff-9f17-e9551fa0f1ac', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'test2', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:04:44.714706', 'description': '', 'display_name': 'penguin', 'id': '9670daa2-0b07-4a8a-87e4-6313400c40df', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'penguin', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': '', 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.152620', 'description': 'These are books that David likes.', 'display_name': "Dave's books", 'id': '4f25f1e7-48c9-4bc0-81f7-044a91b8d527', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'david', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Dave's books", 'type': 'group'}, {'approval_status': 'approved', 'created': '2023-11-15T17:03:48.153429', 'description': 'Roger likes these books.', 'display_name': "Roger's books", 'id': 'ff2f73ff-dff5-4de6-8f46-efc5dc44cd43', 'image_display_url': '', 'image_url': '', 'is_organization': False, 'name': 'roger', 'num_followers': 0, 'package_count': 0, 'state': 'active', 'title': "Roger's books", 'type': 'group'}]
                return render_template("memberstates/index.html", q=q, page=c.page,  groups = groups, group_type = group_type, groupcount = groupcount)
