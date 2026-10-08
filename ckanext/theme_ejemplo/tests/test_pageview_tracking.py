import importlib
import sys
import types


CHROME_UA = ('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
RESOURCE_ID = '6f419955-1f26-4b5e-8b3a-9d3a2c1b0f4e'
DOWNLOAD_PATH = '/dataset/mi-dataset/resource/%s/download/archivo.tif' % RESOURCE_ID


def _asbool(value):
    if isinstance(value, str):
        return value.strip().lower() in ('true', '1', 'yes', 'on')
    return bool(value)


class FakeRequest(object):
    def __init__(self):
        self.method = 'GET'
        self.path = '/'
        self.headers = {}
        self.remote_addr = '203.0.113.5'


class FakePipeline(object):
    def __init__(self, parent):
        self.parent = parent
        self.ops = []

    def hincrby(self, key, field, amount=1):
        self.ops.append(('hincrby', key, field, amount))
        return self

    def sadd(self, key, member):
        self.ops.append(('sadd', key, member))
        return self

    def execute(self):
        self.parent.pipeline_ops.extend(self.ops)
        return []


class FakeRedis(object):
    def __init__(self):
        self.seen = set()
        self.hincr_calls = []
        self.pipeline_ops = []

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.seen:
            return None
        self.seen.add(key)
        return True

    def hincrby(self, key, field, amount=1):
        self.hincr_calls.append((key, field, amount))
        return 1

    def pipeline(self, transaction=True):
        return FakePipeline(self)


def _load_tracking(monkeypatch, config=None):
    fake_request = FakeRequest()
    fake_flask = types.ModuleType('flask')
    fake_flask.request = fake_request

    cfg = {'ckanext.theme_ejemplo.pageviews_enabled': True}
    cfg.update(config or {})
    fake_toolkit = types.ModuleType('ckan.plugins.toolkit')
    fake_toolkit.config = cfg
    fake_toolkit.asbool = _asbool
    fake_toolkit.asint = int

    fake_plugins = types.ModuleType('ckan.plugins')
    fake_plugins.toolkit = fake_toolkit
    fake_ckan = types.ModuleType('ckan')
    fake_model = types.ModuleType('ckan.model')
    fake_sqlalchemy = types.ModuleType('sqlalchemy')
    fake_sqlalchemy.text = lambda value: value

    monkeypatch.setitem(sys.modules, 'flask', fake_flask)
    monkeypatch.setitem(sys.modules, 'ckan', fake_ckan)
    monkeypatch.setitem(sys.modules, 'ckan.plugins', fake_plugins)
    monkeypatch.setitem(sys.modules, 'ckan.plugins.toolkit', fake_toolkit)
    monkeypatch.setitem(sys.modules, 'ckan.model', fake_model)
    monkeypatch.setitem(sys.modules, 'sqlalchemy', fake_sqlalchemy)
    sys.modules.pop('ckanext.theme_ejemplo.pageview_tracking', None)

    mod = importlib.import_module('ckanext.theme_ejemplo.pageview_tracking')
    return mod, fake_request


def _with_redis(mod):
    fake = FakeRedis()
    mod._redis_client = fake
    mod._redis_init_attempted = True
    return fake


# ─── _is_user_download: matriz Fetch Metadata ─────────────────────────────


def test_is_user_download_matrix(monkeypatch):
    mod, _ = _load_tracking(monkeypatch)
    cases = [
        # clic en enlace normal
        ({'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}, True),
        # clic en <a download>
        ({'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'empty'}, True),
        # Chrome 76-79: Mode sin Dest
        ({'Sec-Fetch-Mode': 'navigate'}, True),
        # fetch/XHR de un visor (Terria)
        ({'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'}, False),
        # <img> embebido
        ({'Sec-Fetch-Mode': 'no-cors', 'Sec-Fetch-Dest': 'image'}, False),
        # <iframe>: tambien es navigate, el Dest decide
        ({'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'iframe'}, False),
        # lector tileado COG / resume
        ({'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document',
          'Range': 'bytes=0-1023'}, False),
        # prefetch especulativo
        ({'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document',
          'Sec-Purpose': 'prefetch'}, False),
        # sin Fetch Metadata y sin Referer: cuenta (Safari viejo)
        ({'User-Agent': CHROME_UA}, True),
    ]
    for headers, expected in cases:
        assert mod._is_user_download(headers) is expected, headers


def test_is_user_download_fallback_referer(monkeypatch):
    mod, _ = _load_tracking(monkeypatch, config={
        'ckanext.theme_ejemplo.pageviews_excluded_referrer_hosts':
            'terria.water-data.org, ihp-wins.unesco.org/terria',
    })
    ua = {'User-Agent': CHROME_UA}
    assert mod._is_user_download(
        dict(ua, Referer='https://terria.water-data.org/mapa')) is False
    # host + prefijo de path: solo excluye bajo /terria
    assert mod._is_user_download(
        dict(ua, Referer='https://ihp-wins.unesco.org/terria/#start=x')) is False
    assert mod._is_user_download(
        dict(ua, Referer='https://ihp-wins.unesco.org/dataset/x')) is True
    # sin Sec-Fetch pero con UA de herramienta: no cuenta
    assert mod._is_user_download({'User-Agent': 'Python-urllib/3.10'}) is False


# ─── _is_bot ampliado ─────────────────────────────────────────────────────


def test_is_bot_extended(monkeypatch):
    mod, _ = _load_tracking(monkeypatch)
    for ua in ('CKAN-TerriaView/1.0', 'Python-urllib/3.10', 'node-fetch/2.6',
               'axios/1.6.0', 'okhttp/4.9.0', 'Java/11.0.2',
               'Go-http-client/2.0', 'libwww-perl/6.05'):
        assert mod._is_bot(ua), ua
    # regresion: UAs de navegador real no deben matchear (p.ej. 'java/')
    assert not mod._is_bot(CHROME_UA)
    assert not mod._is_bot('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/605.1.15 Version/17.4 Safari/605.1.15')


# ─── _match ───────────────────────────────────────────────────────────────


def test_match_paths(monkeypatch):
    mod, _ = _load_tracking(monkeypatch, config={
        'ckanext.theme_ejemplo.pageviews_view_paths': '/dataset, /documents',
    })
    assert mod._match('/dataset/mi-dataset') == ('view', 'mi-dataset')
    assert mod._match('/documents/informe') == ('view', 'informe')
    assert mod._match(DOWNLOAD_PATH) == ('download', RESOURCE_ID)
    assert mod._match('/dataset/new') is None
    assert mod._match('/dataset/x/resource/no-es-uuid/download/f.csv') is None


# ─── _record: integracion ─────────────────────────────────────────────────


def test_record_head_does_not_count(monkeypatch):
    mod, req = _load_tracking(monkeypatch)
    redis = _with_redis(mod)
    req.method = 'HEAD'
    req.path = DOWNLOAD_PATH
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
    mod._record()
    assert redis.hincr_calls == []


def test_record_viewer_fetch_does_not_count_nor_burn_dedup(monkeypatch):
    mod, req = _load_tracking(monkeypatch)
    redis = _with_redis(mod)
    req.path = DOWNLOAD_PATH
    # 1) fetch de Terria: no cuenta y no debe consumir la clave de dedup
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'}
    mod._record()
    assert redis.hincr_calls == []
    # 2) clic real del mismo IP+URL justo despues: si cuenta
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
    mod._record()
    assert redis.hincr_calls == [(mod.DOWNLOADS_KEY, RESOURCE_ID, 1)]


def test_record_navigation_download_counts(monkeypatch):
    mod, req = _load_tracking(monkeypatch)
    redis = _with_redis(mod)
    req.path = DOWNLOAD_PATH
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
    mod._record()
    assert redis.hincr_calls == [(mod.DOWNLOADS_KEY, RESOURCE_ID, 1)]
    # repetido dentro de la ventana de dedup: no vuelve a contar
    mod._record()
    assert len(redis.hincr_calls) == 1


def test_record_flag_off_restores_legacy_counting(monkeypatch):
    mod, req = _load_tracking(monkeypatch, config={
        'ckanext.theme_ejemplo.pageviews_downloads_navigation_only': 'false',
    })
    redis = _with_redis(mod)
    req.path = DOWNLOAD_PATH
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'cors', 'Sec-Fetch-Dest': 'empty'}
    mod._record()
    assert redis.hincr_calls == [(mod.DOWNLOADS_KEY, RESOURCE_ID, 1)]


def test_record_views_unaffected_by_gate(monkeypatch):
    mod, req = _load_tracking(monkeypatch)
    redis = _with_redis(mod)
    req.path = '/dataset/mi-dataset'
    req.headers = {'User-Agent': CHROME_UA,
                   'Sec-Fetch-Mode': 'navigate', 'Sec-Fetch-Dest': 'document'}
    mod._record()
    views_ops = [op for op in redis.pipeline_ops
                 if op[0] == 'hincrby' and op[1] == mod.VIEWS_KEY]
    assert views_ops == [('hincrby', mod.VIEWS_KEY, 'mi-dataset', 1)]


def test_record_server_side_ua_filtered(monkeypatch):
    mod, req = _load_tracking(monkeypatch)
    redis = _with_redis(mod)
    req.path = DOWNLOAD_PATH
    req.headers = {'User-Agent': 'CKAN-TerriaView/1.0'}
    mod._record()
    assert redis.hincr_calls == []
    assert redis.pipeline_ops == []
