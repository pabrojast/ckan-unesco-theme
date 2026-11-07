"""Carga revisable de las fuentes autorizadas en DEV; nunca publica ni aprueba.

Ejecutar dentro del contenedor CKAN con --ini y --sources (directorio con copias
planas de los siete archivos originales). Sin --apply sólo valida el manifiesto.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

FILES = [
    ('OETWG1 - Planned Activities.xlsx', 'oetwg-1', 'plans', 'planning'),
    ('OETWG IV - Planned Activities.xlsx', 'oetwg-4', 'plans', 'planning'),
    ('Contacts Priority Area 4.xlsx', 'oetwg-4', 'contacts', 'other'),
    ('Priority_Area_4_Report.xlsx', 'oetwg-4', 'execution', 'report'),
    ('RCTWS Activities implemented and ongoing.xlsx', 'oetwg-4', 'execution', 'report'),
    ('OETWG 4 IWRM_23Feb.pptx', 'oetwg-4', None, 'presentation'),
    ('IHP-IX Strategy Document.pdf', 'oetwg-4', None, 'strategy'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ini', required=True)
    parser.add_argument('--sources', required=True)
    parser.add_argument('--user', default='ckan_admin')
    parser.add_argument('--summary', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    from ckan.cli import load_config
    from ckan.config.middleware import make_app
    config = load_config(args.ini)
    host = urlparse(config['ckan.site_url']).hostname
    db = urlparse(config['sqlalchemy.url'])
    if host != 'data.dev-wins.com' and not (host == '127.0.0.1' and db.hostname == 'ihpix-form-db' and db.path == '/ihpix_form'):
        raise SystemExit('Only the authorized DEV or isolated QA environment is supported')
    source = Path(args.sources)
    manifest = []
    for filename, group, kind, category in FILES:
        raw = (source / filename).read_bytes()
        if len(raw) > 20*1024*1024:
            raise SystemExit('Source exceeds the private upload limit: '+filename)
        manifest.append(dict(file=filename,group=group,kind=kind,category=category,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)))
    if not args.apply:
        Path(args.summary).write_text(json.dumps(manifest,indent=2))
        print('Validated source files:',len(manifest))
        return
    make_app(config)
    import ckan.model as model
    import ckan.plugins.toolkit as tk
    from ckanext.theme_ejemplo import ihpix_groups as G, ihpix_group_store as D
    from werkzeug.datastructures import FileStorage
    import io
    user=model.User.get(args.user)
    assert user and user.sysadmin and user.state=='active'
    context={'user':user.name,'auth_user_obj':user,'model':model}
    result=[]
    for item in manifest:
        raw=(source/item['file']).read_bytes()
        # El archivo completo y su hash se conservan como documento privado versionado.
        document=G.document_save(context,dict(group_id=item['group'],category=item['category'],title=item['file'],
                                  upload=FileStorage(io.BytesIO(raw),filename=item['file'])))
        item['document_id']=document['id']
        if item['kind']:
            batch=G.import_preview(context,dict(group_id=item['group'],kind=item['kind'],filename=item['file'],workbook=base64.b64encode(raw).decode()))
            item['batch_id']=batch['id'];item['source_rows']=len(batch['payload'])
            item['rows_needing_correction']=sum(bool(r['errors']) for r in batch['payload'])
            if item['kind']=='execution':
                item['state']='awaiting_reconciliation'
                item['matching_rows']=sum(bool(r.get('match')) for r in batch['payload'])
            else:
                choices=[];corrections=[]
                for index,row in enumerate(batch['payload']):
                    updates={}
                    if row['errors']:
                        # No adivinar un correo. El valor completo sigue en origin.cells y el XLSX.
                        if item['kind']=='plans' and set(row['errors'])=={'email'}:
                            updates['email']='';corrections.append(dict(row=index,field='email',reason='Invalid source email retained in original source'))
                        else:
                            raise RuntimeError('Unexpected source validation errors; no batch applied: '+json.dumps(row['errors']))
                    choices.append(dict(index=index,decision='new',payload=updates))
                applied=G.import_apply(context,dict(id=batch['id'],rows=choices))
                item['record_ids']=applied['ids'];item['unique_records']=len(set(applied['ids']));item['corrections']=corrections;item['state']='imported_as_drafts' if item['kind']=='plans' else 'imported_without_accounts'
        result.append(item)
        Path(args.summary).write_text(json.dumps(result,indent=2,ensure_ascii=False))
    print(json.dumps([dict(file=i['file'],rows=i.get('source_rows',0),state=i.get('state','private_document')) for i in result]))


if __name__=='__main__':
    main()
