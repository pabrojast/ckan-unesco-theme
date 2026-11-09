"""Vistas de espacios por grupo, formularios y descarga privada."""
import io
import json
import uuid
from flask import render_template, request, redirect, jsonify, send_file, abort
from ckan.common import c
import ckan.model as model
import ckan.plugins.toolkit as tk
from . import ihpix_groups as G, ihpix_group_store as D, ihpix_planning as P, ihpix_constants as C, ihpix_legacy_reports as E
from .ihpix_views import signed_in, context


def common():
    return dict(biennia=P.BIENNIA,execution_states=P.EXECUTION,review_states=P.REVIEW,
                report_fields=E.FIELDS,report_labels={v:k for k,v in E.HEADERS.items()},report_multi=E.F.MULTI_FIELDS,categories=P.DOC_CATEGORIES,output_titles=C.load_output_titles(),
                key_activities=C.load_key_activities(),group_options=G.list_groups(context(),{})['results'])


@signed_in
def index():
    return render_template('ihpix/groups/index.html',groups=G.list_groups(context(),{})['results'])


@signed_in
def detail(slug):
    data=G.show_group(context(),dict(request.args,group_id=slug))
    tab=request.args.get('tab','overview')
    if tab not in ('overview','calendar','plan','tracking','documents','members','conversations','settings'):tab='overview'
    legacy=[]
    from .model import IhpixWorkingGroup,IhpixWorkingGroupMember
    for output in data['outputs']:
        wg=IhpixWorkingGroup.get_by_output(output)
        if not wg:continue
        for m in IhpixWorkingGroupMember.get_for_group(wg.id,'active'):
            u=model.User.get(m.user_id)
            if u and data['can_manage']:legacy.append(dict(output=output,username=u.name,name=u.display_name,role=m.role))
    from .ihpix_calendar import month_view
    selected={p['id'] for p in data['plans']}
    filtered=any(request.args.get(k) for k in ('output','biennium','q','review_status','execution_status','institution','focal_point'))
    tasks=[t for t in data['items'] if not filtered or t.get('plan_id') in selected]
    calendar=month_view(data['plans'],tasks,request.args.get('month',''))
    return render_template('ihpix/groups/detail.html',group=data,tab=tab,legacy=legacy,calendar=calendar,**common())


@signed_in
def plan(slug,id=None):
    group=G.group(slug)
    if id:
        data=G.show_plan(context(),{'id':id})
        if data['group_id']!=slug:abort(404)
    else:
        G.access(c.userobj,slug,write=True)
        data={'id':'','group_id':slug,'revision':0,'review_status':'draft','execution_status':'planned',
              'can_edit':True,'can_review':False,'approved':{},'history':[],'reports':[],
              'payload':{'title':'','description':'','output':request.args.get('output',''),'periods':{},
                         'focal_point':c.userobj.display_name,'email':c.userobj.email or '', 'links':[]}}
    documents=[]
    if id:
        for r in model.Session.execute(D.documents.select().with_only_columns(*[col for col in D.documents.c if col.name!='content']).where(D.documents.c.plan_id==id)):
            doc=G.S.row_dict(r)
            try:G.document_access(c.userobj,doc)
            except tk.NotAuthorized:continue
            documents.append(doc)
    from .controller import MyLogica
    return render_template('ihpix/groups/plan.html',group=group,plan=data,request_id=str(uuid.uuid4()),
                           user_id=c.userobj.id,documents=documents,publication_ctx=MyLogica._ihpix_publication_context(data['payload'].get('output','')),
                           **common())


def api(operation):
    if not c.userobj or getattr(c.userobj,'state',None)!='active':return jsonify(success=False,error=tk._('You must be logged in')),403
    # La ruta de formulario acepta sólo peticiones AJAX del mismo origen.
    # Los clientes externos con token usan las acciones CKAN /api/3/action.
    origin=request.headers.get('Origin')
    allowed={request.host_url.rstrip('/'),tk.config.get('ckan.site_url','').rstrip('/')}
    if request.headers.get('X-Requested-With')!='XMLHttpRequest' or (origin and origin.rstrip('/') not in allowed):
        return jsonify(success=False,error=tk._('Not authorized')),403
    name='ihpix_'+operation
    if name not in G.ACTIONS:abort(404)
    data=dict(request.form) if request.mimetype!='application/json' else (request.get_json(silent=True) or {})
    if not isinstance(data,dict):return jsonify(success=False,error='Invalid request'),400
    if request.files.get('file') is not None:data['upload']=request.files['file']
    if operation=='group_import_preview' and request.files.get('file') is not None:
        import base64
        upload=request.files['file'];data['filename']=upload.filename
        data['workbook']=base64.b64encode(upload.read(10*1024*1024+1)).decode()
    try:
        result=tk.get_action(name)(context(),data)
        # JSON de fechas/objetos: nunca serializar contenido binario.
        return jsonify(success=True,result=json.loads(json.dumps(result,default=str,ensure_ascii=False)))
    except tk.ValidationError as exc:
        model.Session.rollback()
        return jsonify(success=False,errors=exc.error_dict),409 if 'expected_revision' in exc.error_dict else 400
    except tk.NotAuthorized:
        model.Session.rollback();return jsonify(success=False,error=tk._('Not authorized')),403
    except tk.ObjectNotFound:
        model.Session.rollback();return jsonify(success=False,error=tk._('Not found')),404
    except Exception:
        model.Session.rollback()
        import logging
        logging.getLogger(__name__).exception('IHP-IX: error en grupos %s',operation)
        return jsonify(success=False,error=tk._('The operation failed. Your changes have not been confirmed.')),500


@signed_in
def download(slug,id):
    doc=G.document_show(context(),{'id':id})
    if doc['group_id']!=slug:abort(404)
    raw=model.Session.execute(D.documents.select().with_only_columns(D.documents.c.content).where(D.documents.c.id==id)).scalar()
    # Siempre attachment; impedir HTML/SVG ejecutable y evitar cachés compartidas.
    response=send_file(io.BytesIO(raw),as_attachment=True,download_name=doc['filename'],mimetype='application/octet-stream')
    response.headers['Cache-Control']='private, no-store';response.headers['X-Content-Type-Options']='nosniff'
    return response


@signed_in
def export(slug):
    G.access(c.userobj,slug)
    g=G.show_group(context(),dict(request.args,group_id=slug))
    response=send_file(io.BytesIO(P.export_plans(g['plans'],g['outputs'])),as_attachment=True,
                       download_name=slug+'-plan.xlsx',mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response.headers['Cache-Control']='private, no-store';return response


@signed_in
def imports(slug,id=None):
    g=G.access(c.userobj,slug,manage=True)
    batch=G.import_show(context(),{'id':id}) if id else None
    if batch and batch['group_id']!=slug:abort(404)
    candidates={}
    if batch:
        for row in batch['payload']:
            for target in (row.get('match') or {}).get('candidates',[]):
                if batch['kind']=='execution':
                    old=G.IhpixActivity.get(target)
                    if old and G.V.can_read(old,c.userobj):candidates[target]={'revision':old.revision,'payload':old.as_dict()}
                else:
                    old=D.row(D.plans if batch['kind']=='plans' else D.contacts,target)
                    if old:candidates[target]={'revision':old['revision'],'payload':P.unpack(old['payload'],{})}
    return render_template('ihpix/groups/import.html',group=g,batch=batch,candidates=candidates,**common())


def register(blueprint):
    for path,name,view,methods in [
        ('/ihpix/workspaces/groups/<slug>','ihpix_group',detail,['GET']),
        ('/ihpix/workspaces/groups/<slug>/plans/new','ihpix_group_plan_new',plan,['GET']),
        ('/ihpix/workspaces/groups/<slug>/plans/<id>','ihpix_group_plan',plan,['GET']),
        ('/ihpix/workspaces/groups/<slug>/documents/<id>','ihpix_group_document',download,['GET']),
        ('/ihpix/workspaces/groups/<slug>/export.xlsx','ihpix_group_export',export,['GET']),
        ('/ihpix/workspaces/groups/<slug>/import','ihpix_group_import',imports,['GET']),
        ('/ihpix/workspaces/groups/<slug>/import/<id>','ihpix_group_import_batch',imports,['GET']),
        ('/ihpix/group-api/<operation>','ihpix_group_api',api,['POST']),
    ]:blueprint.add_url_rule(path,name,view,methods=methods)
