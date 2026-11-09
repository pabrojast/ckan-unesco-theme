#!/usr/bin/env python3
"""Regresión sobre la instancia QA aislada; ver Testing.md."""
import sys,json,io,base64,uuid
from pathlib import Path
sys.path.insert(0,str(Path('scripts').resolve()));from ihpix_review_acceptance import api,check,TOKENS,BASE
from openpyxl import load_workbook
import requests
prefix='ROLLBACK-QA-'+uuid.uuid4().hex
book=load_workbook(io.BytesIO(requests.get(BASE+'/ihpix/import/template.xlsx',headers={'Authorization':TOKENS['author']}).content));heads=[x.value for x in book['Activities'][1]]
for ref,output in [('A','1.1'),('B','1.10')]:book['Activities'].append([{'row_ref':ref,'title':prefix+ref,'priority_area':'PA1','output':output}.get(x,'') for x in heads])
b=io.BytesIO();book.save(b);preview=api('ihpix_import_preview',{'workbook':base64.b64encode(b.getvalue()).decode()});check('batch validates before concurrent workspace change',not preview['preview']['errors'])
try:
 api('ihpix_working_group_update',{'id':'1.10','status':'archived'},role='admin')
 api('ihpix_import_create',{'id':preview['id'],'confirm':True},success=False)
 rows=api('ihpix_my_reports_list',{'limit':100})['results'];check('failure in second import row rolls back first row',not any(x['title'].startswith(prefix) for x in rows))
 check('failed batch remains an uncreated preview',api('ihpix_import_show',{'id':preview['id']})['status']=='preview')
finally:api('ihpix_working_group_update',{'id':'1.10','status':'active'},role='admin')
result=api('ihpix_import_create',{'id':preview['id'],'confirm':True});check('same preview can be retried after rollback',len(result['created'])==2)
for row in result['created']:api('ihpix_report_delete',{'id':row['id']},role='admin')
print('ROLLBACK COMPLETE',prefix)
