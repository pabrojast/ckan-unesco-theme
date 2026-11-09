"""Regresiones de asociaciones, descubrimiento y paginación de estilos."""
from copy import deepcopy
import pytest
from ckanext.theme_ejemplo.resource_styles import is_sld_resource, present_resources

S1 = '11111111-1111-1111-1111-111111111111'
S2 = '22222222-2222-2222-2222-222222222222'


def resource(rid, fmt='GeoJSON', name=None):
    return {'id': rid, 'name': name or rid, 'format': fmt,
            'url': 'https://data.dev-wins.com/dataset/example/resource/%s/download/file.%s' % (rid, fmt.lower())}


def view(rid, sid, title='Map'):
    return {'resource_id': rid, 'view_type': 'terria_view', 'title': title,
            'config': {'style': 'https://ihp-wins.unesco.org/dataset/old/resource/%s/download/old.sld' % sid}}


@pytest.mark.parametrize('res,expected', [
    ({'format': ' SLD '}, True), ({'format': 'application/vnd.ogc.sld+xml'}, True),
    ({'mimetype': 'application/vnd.ogc.sld+xml; charset=utf-8'}, True),
    ({'url': 'https://example.com/style.SLD?token=x#y'}, True),
    ({'url': 'https://example.com/style%2E%73%6c%64'}, True),
    ({'format': 'XML', 'url': 'https://example.com/style.xml'}, False),
    ({'url': 'https://example.com/data.csv?style=x.sld'}, False),
    ({'url': 'https://style.sld'}, False), ({'url': 'http://[invalid'}, False),
])
def test_classification(res, expected):
    assert is_sld_resource(res) is expected


def test_shared_style_uses_existing_view_links_and_preserves_input():
    resources = [resource('data-a'), resource(S1, 'SLD'), resource('data-b'), resource(S2, 'sld')]
    original = deepcopy(resources)
    views = [view('data-a', S1), view('data-b', S1), view('data-a', S1, 'Other map')]
    result = present_resources(resources, views)
    assert resources == original
    assert [r['id'] for r in result['resources']] == ['data-a', 'data-b', S2]
    assert result['resource_count'] == 2 and result['style_count'] == 2
    child = result['resources'][0]['_style_resources'][0]
    assert child['id'] == S1 and child['_style_views'] == ['Map', 'Other map']
    assert result['resources'][1]['_style_resources'][0]['id'] == S1
    assert result['resources'][2]['_is_sld']


def test_multiple_styles_and_search_retain_parent_context():
    resources = [resource('parent'), resource(S1, 'SLD', 'Hydrogeology'), resource(S2, 'SLD', 'Geology')]
    views = [view('parent', S1), view('parent', S2)]
    result = present_resources(resources, views, q='Hydrogeology')
    assert result['total'] == 1
    parent = result['resources'][0]
    assert parent['id'] == 'parent' and parent['_styles_expanded']
    assert [r['id'] for r in parent['_style_resources']] == [S1]
    assert len(present_resources(resources, views, format_filter='sld')['resources'][0]['_style_resources']) == 2
    assert present_resources(resources, views, format_filter='CSV')['total'] == 0


def test_all_files_mode_and_sld_filter():
    resources = [resource('parent'), resource(S1, 'SLD')]
    result = present_resources(resources, [view('parent', S1)], mode='all', format_filter='SLD')
    assert result['total'] == 1 and result['resources'][0]['id'] == S1
    assert not result['resources'][0]['_style_resources']


def test_grouping_precedes_pagination():
    resources = [resource('data-%s' % i) for i in range(25)]
    resources.insert(0, resource(S1, 'SLD'))
    views = [view('data-24', S1)]
    first = present_resources(resources, views)
    second = present_resources(resources, views, page=2)
    assert first['total'] == 25 and len(first['resources']) == 20
    assert len(second['resources']) == 5
    assert second['resources'][-1]['_style_resources'][0]['id'] == S1
    assert present_resources(resources, views, page=99)['page'] == 2
    assert present_resources(resources, views, page=-2, items_per_page=0)['page'] == 1


def test_unresolved_unrelated_and_malformed_views_do_not_hide_files():
    resources = [resource('parent'), resource(S1, 'SLD')]
    views = [view('other-dataset', S1), view('parent', S2),
             dict(view('parent', S1), config='not json'),
             dict(view('parent', S1), view_type='other'),
             dict(view('parent', S1), config=[])]
    assert present_resources(resources, views)['total'] == 2


def test_exact_external_url_and_serialized_config():
    resources = [resource('parent'), dict(resource(S1, 'SLD'), url='https://example.org/style')]
    views = [{'resource_id': 'parent', 'title': 'Map', 'view_type': 'terria_view',
              'config': '{"style": "https://example.org/style"}'}]
    assert present_resources(resources, views)['total'] == 1
