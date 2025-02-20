from ckan.plugins import toolkit

def get_paged_resources(package_id, page=1, items_per_page=10):
    """
    Get paginated resources for a package
    """
    # Obtener el total de recursos
    total = toolkit.get_action('resource_search')({}, {
        'query': f'package_id:{package_id}',
    })['count']
    
    # Obtener los recursos paginados
    resources = toolkit.get_action('resource_search')({}, {
        'query': f'package_id:{package_id}',
        'offset': (page - 1) * items_per_page,
        'limit': items_per_page,
    })['results']
    
    return {
        'resources': resources,
        'total': total
    }
