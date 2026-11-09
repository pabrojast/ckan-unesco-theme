"""Captura de sólo lectura; ejecutar en el pod y guardar stdout en lugar privado."""
import configparser
import datetime
import hashlib
import json
import os

import psycopg2
from redis import Redis

cfg = configparser.RawConfigParser()
cfg.read('/srv/app/production.ini')
url = os.environ.get('CKAN_SQLALCHEMY_URL') or cfg.get('app:main', 'sqlalchemy.url')
conn = psycopg2.connect(url.replace('postgresql+psycopg2://', 'postgresql://'))
conn.set_session(readonly=True, isolation_level='REPEATABLE READ')
result = {'created_at': datetime.datetime.utcnow().isoformat()+'Z',
          'site_url': cfg.get('app:main', 'ckan.site_url'), 'tables': {}}
assert result['site_url'] == 'https://data.dev-wins.com', 'Este respaldo es exclusivo de DEV'
with conn.cursor() as cur:
    cur.execute("SET LOCAL statement_timeout = '30s'")
    for table in ('tracking_dataset_stats', 'tracking_dataset_daily', 'tracking_resource_stats', 'tracking_site_totals'):
        cur.execute('SELECT * FROM '+table+' ORDER BY 1, 2')
        names = [d[0] for d in cur.description]
        result['tables'][table] = [dict(zip(names,row)) for row in cur.fetchall()]
    for table in ('resource', 'resource_view'):
        cur.execute('SELECT id, row_to_json(t)::text FROM '+table+' t ORDER BY id')
        result[table+'_hashes'] = {rid:hashlib.sha256(raw.encode()).hexdigest() for rid,raw in cur.fetchall()}
conn.rollback();conn.close()
redis_url = os.environ.get('CKAN__REDIS__URL') or cfg.get('app:main','ckan.redis.url')
r = Redis.from_url(redis_url)
result['pending_downloads'] = {k.decode():int(v) for k,v in r.hgetall('theme_ejemplo:pv:downloads').items()}
print(json.dumps(result,default=str,indent=2))
