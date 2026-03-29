"""Small shared utilities for the theme extension."""

from __future__ import annotations

from pathlib import PurePosixPath
from urllib.parse import urlsplit

ALLOWED_USER_IMAGE_EXTENSIONS = frozenset({
    'png',
    'jpg',
    'jpeg',
    'jpe',
    'jfif',
    'gif',
    'webp',
    'bmp',
    'tif',
    'tiff',
    'avif',
})

ALLOWED_USER_IMAGE_MIME_TYPES = frozenset({
    'image/png',
    'image/jpeg',
    'image/gif',
    'image/webp',
    'image/bmp',
    'image/tiff',
    'image/avif',
})

GENERIC_UPLOAD_MIME_TYPES = frozenset({
    'application/octet-stream',
    'binary/octet-stream',
})

_USER_IMAGE_MIME_ALIASES = {
    'image/jpg': 'image/jpeg',
    'image/pjpeg': 'image/jpeg',
    'image/x-png': 'image/png',
    'image/x-ms-bmp': 'image/bmp',
}

_USER_IMAGE_EXTENSIONS_BY_MIME = {
    'image/png': {'png'},
    'image/jpeg': {'jpg', 'jpeg', 'jpe', 'jfif'},
    'image/gif': {'gif'},
    'image/webp': {'webp'},
    'image/bmp': {'bmp'},
    'image/tiff': {'tif', 'tiff'},
    'image/avif': {'avif'},
}


def _get_image_extension(path_or_filename):
    suffix = PurePosixPath((path_or_filename or '').strip()).suffix
    return suffix.lower().lstrip('.')


def _normalize_mime_type(mime_type):
    if not mime_type:
        return ''

    normalized = str(mime_type).split(';', 1)[0].strip().lower()
    return _USER_IMAGE_MIME_ALIASES.get(normalized, normalized)


def _extract_upload_filename(upload):
    filename = getattr(upload, 'filename', '') or ''
    return PurePosixPath(str(filename).replace('\\', '/')).name


def _extract_upload_mime_type(upload):
    mime_type = (
        getattr(upload, 'mimetype', None)
        or getattr(upload, 'content_type', None)
        or getattr(upload, 'type', None)
        or ''
    )
    return _normalize_mime_type(mime_type)


def _get_upload_stream(upload):
    for attr in ('stream', 'file', 'fp'):
        stream = getattr(upload, attr, None)
        if stream is not None and hasattr(stream, 'read'):
            return stream
    return None


def _read_upload_header(upload, size=64):
    stream = _get_upload_stream(upload)
    if stream is None or not hasattr(stream, 'seek') or not hasattr(stream, 'tell'):
        return None

    try:
        original_position = stream.tell()
        stream.seek(0)
        header = stream.read(size) or b''
        stream.seek(original_position)
    except Exception:
        return None

    if isinstance(header, str):
        return header.encode('utf-8', 'ignore')

    return header


def _detect_image_mime_from_header(header):
    if not header:
        return ''

    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'image/png'
    if header.startswith(b'\xff\xd8\xff'):
        return 'image/jpeg'
    if header.startswith((b'GIF87a', b'GIF89a')):
        return 'image/gif'
    if header.startswith(b'BM'):
        return 'image/bmp'
    if header.startswith((b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+')):
        return 'image/tiff'
    if len(header) >= 12 and header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'image/webp'
    if len(header) >= 16 and header[4:8] == b'ftyp' and b'avif' in header[8:32]:
        return 'image/avif'

    return ''


def _detect_image_mime_with_pillow(upload):
    stream = _get_upload_stream(upload)
    if stream is None or not hasattr(stream, 'seek') or not hasattr(stream, 'tell'):
        return ''

    try:
        from PIL import Image
    except ImportError:
        return ''

    pillow_format_to_mime = {
        'PNG': 'image/png',
        'JPEG': 'image/jpeg',
        'GIF': 'image/gif',
        'WEBP': 'image/webp',
        'BMP': 'image/bmp',
        'TIFF': 'image/tiff',
        'AVIF': 'image/avif',
    }

    try:
        original_position = stream.tell()
        stream.seek(0)
        with Image.open(stream) as image:
            image_format = pillow_format_to_mime.get((image.format or '').upper(), '')
            image.verify()
        stream.seek(original_position)
        return image_format
    except Exception:
        try:
            stream.seek(original_position)
        except Exception:
            pass
        return ''


def _detect_upload_image_mime(upload):
    header = _read_upload_header(upload)
    if header is not None:
        if not header:
            return None
        detected_from_header = _detect_image_mime_from_header(header)
        if detected_from_header:
            return detected_from_header
        detected_with_pillow = _detect_image_mime_with_pillow(upload)
        if detected_with_pillow:
            return detected_with_pillow
        return None

    detected_with_pillow = _detect_image_mime_with_pillow(upload)
    return detected_with_pillow or ''


def is_valid_user_image_reference(image_url):
    """Return whether a stored avatar reference looks safe to render."""
    if not image_url:
        return False

    image_url = str(image_url).strip()
    if not image_url:
        return False

    if image_url.startswith('data:'):
        mime_type = _normalize_mime_type(image_url[5:].split(',', 1)[0].split(';', 1)[0])
        return mime_type in ALLOWED_USER_IMAGE_MIME_TYPES

    parsed_url = urlsplit(image_url)
    path = parsed_url.path or image_url
    extension = _get_image_extension(path)

    if extension:
        return extension in ALLOWED_USER_IMAGE_EXTENSIONS

    return image_url.startswith(('http://', 'https://', '//'))


def get_invalid_user_image_upload_reason(upload):
    """Return an error code when an uploaded avatar should be rejected."""
    if not upload:
        return None

    filename = _extract_upload_filename(upload)
    if not filename:
        return None

    extension = _get_image_extension(filename)
    if extension not in ALLOWED_USER_IMAGE_EXTENSIONS:
        return 'invalid_extension'

    declared_mime_type = _extract_upload_mime_type(upload)
    if (
        declared_mime_type and
        declared_mime_type not in ALLOWED_USER_IMAGE_MIME_TYPES and
        declared_mime_type not in GENERIC_UPLOAD_MIME_TYPES
    ):
        return 'invalid_mimetype'

    detected_mime_type = _detect_upload_image_mime(upload)
    if detected_mime_type is None:
        return 'invalid_content'

    if detected_mime_type:
        expected_extensions = _USER_IMAGE_EXTENSIONS_BY_MIME.get(detected_mime_type, set())
        if expected_extensions and extension not in expected_extensions:
            return 'extension_mismatch'

        if (
            declared_mime_type and
            declared_mime_type not in GENERIC_UPLOAD_MIME_TYPES and
            declared_mime_type != detected_mime_type
        ):
            return 'mimetype_mismatch'

    return None


def normalize_user_image_url(image_url, url_resolver=None):
    """Return a usable avatar URL for CKAN user images.

    CKAN often stores uploaded profile pictures as bare filenames under
    ``uploads/user/``. Some custom views in this extension render that raw
    value directly, which breaks outside the user profile page.
    """
    if not is_valid_user_image_reference(image_url):
        return ''

    image_url = str(image_url).strip()
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
