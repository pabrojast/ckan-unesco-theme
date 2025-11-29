from ckan.plugins import toolkit
from jinja2.filters import do_truncate
from markupsafe import Markup
from ckan.lib import helpers as core_helpers

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

def markdown_excerpt(text, length=180, killwords=False, end='...'):
    """
    Render markdown and return a plain-text excerpt without relying on deprecated helpers.
    """
    if not text:
        return ''

    rendered = core_helpers.render_markdown(text)
    plain_text = Markup(rendered).striptags()
    return do_truncate(None, plain_text, length=length, killwords=killwords, end=end)
