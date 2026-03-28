from ckanext.theme_ejemplo.utils import normalize_user_image_url


def test_normalize_user_image_url_keeps_external_urls():
    image_url = 'https://example.com/avatar.png'

    assert normalize_user_image_url(image_url, url_resolver=lambda path: 'bad:' + path) == image_url


def test_normalize_user_image_url_prefixes_uploaded_filenames():
    resolved = normalize_user_image_url(
        '2024-04-29-131808.431574IHP-Logo.png',
        url_resolver=lambda path: 'resolved:' + path,
    )

    assert resolved == 'resolved:/uploads/user/2024-04-29-131808.431574IHP-Logo.png'


def test_normalize_user_image_url_preserves_existing_uploads_path():
    resolved = normalize_user_image_url(
        '/uploads/user/2024-04-29-131808.431574IHP-Logo.png',
        url_resolver=lambda path: 'resolved:' + path,
    )

    assert resolved == 'resolved:/uploads/user/2024-04-29-131808.431574IHP-Logo.png'
