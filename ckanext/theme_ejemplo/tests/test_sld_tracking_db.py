"""Verificación con PostgreSQL/Redis aislados; nunca usa la DB de CKAN."""
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import pytest

DSN = os.environ.get('SLD_TEST_DATABASE_URL')
REDIS_URL = os.environ.get('SLD_TEST_REDIS_URL')
pytestmark = pytest.mark.skipif(not DSN or not REDIS_URL, reason='Requiere PostgreSQL/Redis de pruebas')
S = '11111111-1111-1111-1111-111111111111'
D = '22222222-2222-2222-2222-222222222222'


@pytest.fixture
def system(monkeypatch):
    from sqlalchemy import create_engine, text
    from redis import Redis
    engine = create_engine(DSN)
    redis = Redis.from_url(REDIS_URL)
    # Sólo el namespace de esta suite en su instancia Redis de pruebas.
    for key in redis.scan_iter('theme_ejemplo:pv:*'):
        redis.delete(key)
    with engine.begin() as conn:
        for table in ('tracking_dataset_daily', 'tracking_dataset_stats', 'tracking_resource_stats', 'tracking_site_totals', 'tracking_raw', 'resource', 'package'):
            conn.execute(text('DROP TABLE IF EXISTS ' + table))
        conn.execute(text('CREATE TABLE resource (id text primary key, format text, mimetype text, url text, name text, state text, package_id text)'))
        conn.execute(text('CREATE TABLE package (id text primary key, name text, title text, state text)'))
        conn.execute(text("INSERT INTO package VALUES ('pkg', 'example', 'Example', 'active')"))
        conn.execute(text('CREATE TABLE tracking_resource_stats (resource_id text primary key, total_downloads bigint CHECK (total_downloads >= 0), updated timestamp default now())'))
        conn.execute(text('CREATE TABLE tracking_site_totals (id integer primary key, total_page_views bigint, total_downloads bigint, updated timestamp default now())'))
        conn.execute(text('CREATE TABLE tracking_dataset_stats (dataset_name text primary key, total_views bigint, recent_views bigint, updated timestamp default now())'))
        conn.execute(text('CREATE TABLE tracking_dataset_daily (dataset_name text, day date, views bigint, PRIMARY KEY (dataset_name, day))'))
        conn.execute(text('CREATE TABLE tracking_raw (url text, tracking_type text)'))
        conn.execute(text("INSERT INTO resource VALUES (:s,'SLD',NULL,'https://example.org/style','Style','active','pkg'), (:d,'CSV',NULL,'https://example.org/data.csv','Data','active','pkg')"), {'s': S, 'd': D})
        conn.execute(text('INSERT INTO tracking_resource_stats (resource_id,total_downloads) VALUES (:s,249),(:d,10)'), {'s': S, 'd': D})
        conn.execute(text('INSERT INTO tracking_site_totals (id,total_page_views,total_downloads) VALUES (1,80,259)'))
    toolkit = types.ModuleType('ckan.plugins.toolkit')
    toolkit.config = {'ckan.site_url': 'https://sld-test.invalid', 'ckanext.theme_ejemplo.pageviews_enabled': True}
    toolkit.asbool = bool; toolkit.asint = int
    model = types.ModuleType('ckan.model'); model.meta = types.SimpleNamespace(engine=engine)
    plugins = types.ModuleType('ckan.plugins'); plugins.toolkit = toolkit
    for name, value in {'ckan': types.ModuleType('ckan'), 'ckan.plugins': plugins,
                        'ckan.plugins.toolkit': toolkit, 'ckan.model': model,
                        'ckan.lib': types.ModuleType('ckan.lib'),
                        'ckan.lib.helpers': types.ModuleType('ckan.lib.helpers')}.items():
        monkeypatch.setitem(sys.modules, name, value)
    def load(name):
        fullname = 'ckanext.theme_ejemplo._test_' + name
        spec = importlib.util.spec_from_file_location(fullname, Path(__file__).parents[1] / (name + '.py'))
        module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module
    tracking=load('pageview_tracking'); helpers=load('helpers')
    tracking._redis_client=redis; tracking._redis_init_attempted=True
    yield tracking, helpers, engine, redis
    engine.dispose()


def scalar(engine, sql):
    from sqlalchemy import text
    with engine.connect() as conn:return conn.execute(text(sql)).scalar()


def test_sql_classification_matches_python(system):
    from sqlalchemy import text
    from ckanext.theme_ejemplo.resource_styles import is_sld_resource, sld_sql
    _, _, engine, _ = system
    cases=[{'format':' SLD '}, {'mimetype':'application/vnd.ogc.sld+xml; charset=utf-8'},
           {'url':'https://example.org/style%2E%73%6c%64?x=1'},
           {'url':'https://example.org/style.SLD#x'}, {'url':'https://style.sld'},
           {'url':'https://example.org/data.csv?style=x.sld'}, {'format':'XML'}]
    with engine.connect() as conn:
        for resource in cases:
            data=dict(format=None,mimetype=None,url=None);data.update(resource)
            sql='SELECT '+sld_sql()+' FROM (SELECT CAST(:format AS text) AS format, CAST(:mimetype AS text) AS mimetype, CAST(:url AS text) AS url) r'
            assert bool(conn.execute(text(sql),data).scalar()) == is_sld_resource(resource)


def test_helpers_and_rankings_exclude_historical_sld(system):
    _, helpers, _, _ = system
    assert helpers.get_resource_downloads(S)=={'total':0}
    assert helpers.get_resource_downloads(D)=={'total':10}
    assert helpers.get_tracking_totals()=={'page_views':80,'downloads':10}
    assert [r['resource_id'] for r in helpers.get_popular_resources()] == [D]


def test_flush_filters_pending_styles_without_erasing_history(system):
    tracking, _, engine, redis = system
    redis.hset(tracking.DOWNLOADS_KEY, mapping={S:100,D:2})
    result=tracking.flush_to_db()
    assert result['downloads_added']==2 and result['resources_updated']==1
    assert scalar(engine,"SELECT total_downloads FROM tracking_resource_stats WHERE resource_id='%s'" % S)==249
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==12
    assert scalar(engine,'SELECT total_page_views FROM tracking_site_totals')==80
    tracking.flush_to_db()
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==12


def test_reconciliation_dry_apply_repeat_and_backup(system,tmp_path):
    tracking, _, engine, redis = system
    redis.hset(tracking.DOWNLOADS_KEY,D,3)
    preview=tracking.reconcile_downloads()
    assert preview['before']==259 and preview['after']==10
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==259
    backup=tmp_path/'before.json'
    result=tracking.reconcile_downloads(apply=True,backup=str(backup))
    assert result['after']==10
    snapshot=json.loads(backup.read_text())
    assert snapshot['pending_downloads'][D]==3
    assert len(snapshot['resources'])==2
    assert scalar(engine,"SELECT total_downloads FROM tracking_resource_stats WHERE resource_id='%s'" % S)==249
    assert tracking.reconcile_downloads(apply=True,backup=str(tmp_path/'again.json'))['after']==10
    tracking.flush_to_db()
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==13
    assert scalar(engine,'SELECT total_page_views FROM tracking_site_totals')==80


def test_reconciliation_refuses_missing_backup_or_busy_lock(system,tmp_path):
    tracking, _, engine, redis = system
    with pytest.raises(ValueError):tracking.reconcile_downloads(apply=True)
    redis.set(tracking.LOCK_KEY,'other',ex=60)
    with pytest.raises(RuntimeError):tracking.reconcile_downloads(apply=True,backup=str(tmp_path/'backup.json'))
    assert redis.get(tracking.LOCK_KEY)==b'other'
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==259


def test_backup_failure_preserves_totals_and_releases_lock(system,tmp_path):
    tracking, _, engine, redis = system
    backup=tmp_path/'exists.json';backup.write_text('existing')
    with pytest.raises(FileExistsError):tracking.reconcile_downloads(apply=True,backup=str(backup))
    assert backup.read_text()=='existing'
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==259
    assert not redis.exists(tracking.LOCK_KEY)


def test_flush_database_failure_restores_pending(system):
    tracking, _, engine, redis = system
    redis.hset(tracking.DOWNLOADS_KEY,D,-20)
    with pytest.raises(Exception):tracking.flush_to_db()
    assert scalar(engine,'SELECT total_downloads FROM tracking_site_totals')==259
    assert int(redis.hget(tracking.DOWNLOADS_KEY,D))==-20
    assert not redis.exists(tracking.LOCK_KEY)


def test_legacy_raw_fallback_excludes_style_ids_and_urls(system):
    from sqlalchemy import text
    _, helpers, engine, _ = system
    with engine.begin() as conn:
        conn.execute(text('DROP TABLE tracking_site_totals'))
        conn.execute(text('DROP TABLE tracking_dataset_stats'))
        conn.execute(text("INSERT INTO tracking_raw VALUES ('/dataset/example','page'), (:s,'resource'), (:d,'resource'), ('https://other.org/style.SLD?x=1','resource')"), {'s':'/dataset/example/resource/'+S+'/download','d':'/dataset/example/resource/'+D+'/download/data.csv'})
    assert helpers.get_tracking_totals()=={'page_views':1,'downloads':1}
    assert helpers.get_resource_downloads(S)=={'total':0}
