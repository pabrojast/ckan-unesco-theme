from io import BytesIO

from ckanext.theme_ejemplo.utils import (
    get_invalid_user_image_upload_reason,
    normalize_user_image_url,
)


class DummyUpload(object):
    def __init__(self, filename, content, content_type='application/octet-stream'):
        self.filename = filename
        self.content_type = content_type
        self.stream = BytesIO(content)


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


def test_normalize_user_image_url_rejects_html_uploads():
    resolved = normalize_user_image_url(
        '2024-03-10-073653.403821index.html',
        url_resolver=lambda path: 'resolved:' + path,
    )

    assert resolved == ''


def test_normalize_user_image_url_rejects_non_image_data_urls():
    assert normalize_user_image_url('data:text/html;base64,PGgxPkJhZDwvaDE+') == ''


def test_get_invalid_user_image_upload_reason_accepts_valid_png():
    upload = DummyUpload(
        'avatar.png',
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01',
        content_type='image/png',
    )

    assert get_invalid_user_image_upload_reason(upload) is None


def test_get_invalid_user_image_upload_reason_rejects_html_extension():
    upload = DummyUpload(
        'avatar.html',
        b'<html><body>not an image</body></html>',
        content_type='text/html',
    )

    assert get_invalid_user_image_upload_reason(upload) == 'invalid_extension'


def test_get_invalid_user_image_upload_reason_rejects_html_disguised_as_png():
    upload = DummyUpload(
        'avatar.png',
        b'<html><body>not an image</body></html>',
        content_type='image/png',
    )

    assert get_invalid_user_image_upload_reason(upload) == 'invalid_content'


def test_get_invalid_user_image_upload_reason_rejects_empty_files():
    upload = DummyUpload(
        'avatar.png',
        b'',
        content_type='image/png',
    )

    assert get_invalid_user_image_upload_reason(upload) == 'invalid_content'
