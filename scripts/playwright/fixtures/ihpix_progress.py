import json
from pathlib import Path
from ckan.cli import load_config
from ckan.config.middleware import make_app
config=load_config('/qa/app.ini')
from urllib.parse import urlparse
connection=urlparse(config['sqlalchemy.url'])
assert connection.hostname == 'ihpix-ux-db' and connection.path == '/ihpix_ux', 'Only an isolated QA database is allowed'
app=make_app(config)
import ckan.model as m
from ckanext.theme_ejemplo.model import IhpixActivity as A, IhpixCountrySummary as CS, init_ihpix_activities_db, init_ihpix_country_summary_db
from ckanext.theme_ejemplo import ihpix_store as store
init_ihpix_activities_db();init_ihpix_country_summary_db();store.init_db()
assert m.Session.query(A).count() == 0, 'Use an empty QA activity database'
u=m.User.get('ihpix-ux-author')
assert u, 'Create the isolated QA author first'
org=m.Group(name='qa-water-institute',title='QA Water Institute',type='organization',is_organization=True)
m.Session.add(org);m.Session.flush();m.Session.add(m.Member(group=org,table_id=u.id,table_name='user',capacity='admin',state='active'))
for name,lat,lon in [('Chile',-33.45,-70.66),('Kenya',-1.29,36.82),('Egypt',26.8,30.8),('France',46.6,2.2)]:
 cs=CS(country=name);cs.latitude=lat;cs.longitude=lon;m.Session.add(cs)
rows=[]
for i,(country,beneficiaries,support,biennium) in enumerate([('Chile',['Kenya'],'Egypt','2024-2025'),('France',['Chile'],'','2022-2023'),('Kenya',[],'','2024-2025')]):
 row=A(title='QA activity '+str(i+1)+' — International cooperation for resilient water management across countries and institutions',priority_area='PA1',output='1.1',country=country,institution=org.title,reported_by=u.id,biennium=biennium,description=('Detailed report on international cooperation and water research. '*15),flagships='["FRIEND"]',cross_cutting_wg='["Ecohydrology and Water Quality"]',member_states=json.dumps(beneficiaries),supporting_member_state=support,kpi_2_active=True,stakeholders_knowledge=(i+1)*100,kpi_6_active=True,num_transboundary_ms=2)
 row.institution_org_id=org.id
 if i==0:row.contributions_json=json.dumps([{'priority_area':'PA1','output':'1.1','key_activity_code':'1.1.1'},{'priority_area':'PA1','output':'1.2','key_activity_code':'1.2.1'},{'priority_area':'PA2','output':'2.1','key_activity_code':'2.1.1'}])
 m.Session.add(row);rows.append(row)
for status in ('draft','pending','rejected'):
 row=A(title='QA '+status,priority_area='PA1',output='1.1',status=status,reported_by=u.id);m.Session.add(row)
m.Session.commit()
Path('/qa/fixture.json').write_text(json.dumps({'activities':[r.id for r in rows],'organization':org.id,'author':u.name}))
