from ckan.plugins import toolkit

def get_paged_resources(package_id, page=1, items_per_page=10):
    """
    Get paginated resources for a package
    """
    try:
        # Obtener el paquete completo
        package = toolkit.get_action('package_show')({}, {'id': package_id})
        
        # Obtener todos los recursos
        resources = package.get('resources', [])
        total = len(resources)
        
        # Calcular el inicio y fin para la paginación
        start = (page - 1) * items_per_page
        end = start + items_per_page
        
        # Obtener solo los recursos de la página actual
        paged_resources = resources[start:end]
        
        return {
            'resources': paged_resources,
            'total': total
        }
    except toolkit.ObjectNotFound:
        return {
            'resources': [],
            'total': 0
        }
