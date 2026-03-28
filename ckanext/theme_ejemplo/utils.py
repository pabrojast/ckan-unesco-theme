"""Small shared utilities for the theme extension."""


def normalize_user_image_url(image_url, url_resolver=None):
    """Return a usable avatar URL for CKAN user images.

    CKAN often stores uploaded profile pictures as bare filenames under
    ``uploads/user/``. Some custom views in this extension render that raw
    value directly, which breaks outside the user profile page.
    """
    if not image_url:
        return ''

    image_url = str(image_url)
    if image_url.startswith(('http://', 'https://', 'data:', '//')):
        return image_url

    normalized_path = image_url.lstrip('/')
    if normalized_path.startswith('uploads/'):
        target = '/' + normalized_path
    else:
        target = '/uploads/user/' + normalized_path

    if url_resolver is None:
        from ckan.lib import helpers as core_helpers
        url_resolver = core_helpers.url_for_static_or_external

    return url_resolver(target)
