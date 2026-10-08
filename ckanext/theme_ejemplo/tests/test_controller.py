"""Tests del listado rankeado de entidades (/organization y /group)."""
from ckanext.theme_ejemplo.controller import _name_filter_key


def test_organization_list_uses_the_organizations_key():
    """La regresión que dejó /organization mostrando 1 de 230.

    organization_list hace ``data_dict['groups'] = data_dict.pop(
    'organizations', [])``, así que pasarle ``groups`` lo borra y devuelve la
    primera página por título en vez del subconjunto pedido. El controlador
    intersecta ese resultado con la página ordenada por score, y sólo
    sobrevivían las organizaciones que estaban en ambas listas.
    """
    assert _name_filter_key('organization_list') == 'organizations'


def test_group_list_keeps_the_groups_key():
    """group_list sí acepta `groups` de forma nativa: /group nunca se rompió."""
    assert _name_filter_key('group_list') == 'groups'


def test_unknown_actions_default_to_groups():
    assert _name_filter_key('something_else') == 'groups'
