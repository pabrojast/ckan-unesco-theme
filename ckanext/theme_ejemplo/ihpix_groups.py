"""Servicios de grupos: permisos, planes, revisión, recursos privados e importaciones."""
import base64
import datetime
import hashlib
import json
import os
import re
import uuid
from functools import wraps
from sqlalchemy import select, text
import ckan.model as model
import ckan.plugins.toolkit as tk
from . import ihpix_group_store as D, ihpix_planning as P, ihpix_store as S, ihpix_legacy_reports as E
from . import ihpix_constants as C, ihpix_service as V, ihpix_forms as F
from .model import IhpixWorkingGroup, IhpixWorkingGroupMember, IhpixActivity

ACTIONS = {}


def action(name, readonly=False):
    def decorate(fn):
        @wraps(fn)
        def wrapped(context, data):
            tk.check_access(name,context,data)
            try:
                if name!='ihpix_group_list':
                    required='group_id' if name in ('ihpix_group_show','ihpix_group_update','ihpix_group_member_save','ihpix_plan_save','ihpix_group_document_save','ihpix_group_contact_save','ihpix_group_item_save','ihpix_group_import_preview') else 'id'
                    tk.get_or_bust(data,required)
                result=fn(context,data)
                if not readonly: model.Session.commit()
                return result
            except P.Invalid as exc:
                model.Session.rollback()
                raise tk.ValidationError({k:tk._(v) for k,v in exc.errors.items()})
            except Exception:
                model.Session.rollback();raise
        if readonly: wrapped=tk.side_effect_free(wrapped)
        ACTIONS[name]=wrapped
        return wrapped
    return decorate


def actor(context):
    user=context.get('auth_user_obj') or model.User.get(context.get('user',''))
    if not user or getattr(user,'state',None)!='active': raise tk.NotAuthorized(tk._('You must be logged in'))
    return user


def fail(field,message):
    raise P.Invalid({field:message})


def group(id):
    row=D.row(D.groups,id)
    if not row: raise tk.ObjectNotFound('Working group not found')
    row['outputs']=P.unpack(row['outputs'],[])
    return row


def membership(user,gid):
    return next(iter(D.rows(D.members,D.members.c.group_id==gid,D.members.c.user_id==user.id)),None)


def manager(user,gid):
    m=membership(user,gid)
    return user.sysadmin or bool(m and m['status']=='active' and m['role']=='manager')


def access(user,gid,write=False,manage=False):
    g=group(gid);m=membership(user,gid);lead=manager(user,gid)
    if not lead and (not m or m['status']!='active' or manage or (write and m['role']=='observer')):
        raise tk.NotAuthorized('Group membership required')
    if write and g['status']!='active': raise tk.NotAuthorized('Archived workspaces are read-only')
    return g


def output_lead(user,output):
    wg=IhpixWorkingGroup.get_by_output(output) if output else None
    if not wg: return False
    member=IhpixWorkingGroupMember.get_membership(wg.id,user.id)
    return bool((member and member.status=='active' and member.role=='lead') or
                (not member and wg.lead_user_id==user.id))


def decode_plan(row):
    return dict(row,payload=P.unpack(row['payload'],{}),approved=P.unpack(row['approved'],{}),origin=P.unpack(row['origin'],{}))


def plan_access(user,id,write=False,review=False,lock=False):
    row=D.row(D.plans,id,lock)
    if not row: raise tk.ObjectNotFound('Planned activity not found')
    p=decode_plan(row);g=group(p['group_id'])
    responsible=manager(user,g['id']) or output_lead(user,p['payload'].get('output'))
    owner=p['author_id']==user.id
    m=membership(user,g['id'])
    active=bool(m and m['status']=='active')
    associated=bool(p['approved'] and any((membership(user,i) or {}).get('status')=='active' for i in p['approved'].get('associated_groups',[])))
    if review:
        allowed=responsible
    elif write:
        allowed=responsible or (owner and active and m['role']!='observer')
    else:
        allowed=responsible or (owner and active) or (active and (p['review_status']=='submitted' or bool(p['approved']))) or associated
    if not allowed: raise tk.NotAuthorized('No access to this planned activity')
    if (write or review) and g['status']!='active': raise tk.NotAuthorized('Archived workspaces are read-only')
    p['can_review']=responsible and g['status']=='active'
    p['can_edit']=g['status']=='active' and (responsible or (owner and active and m['role']!='observer'))
    # Una revisión en borrador nunca sustituye el plan acordado para otros lectores.
    if not (responsible or owner) and p['approved']:
        p['payload']=p['approved'];p['review_note']='';p['review_status']='approved'
    return p


def present_plan(p,user):
    from .ihpix_resource_access import filtered
    for field in ('payload','approved'):
        if p.get(field):p[field]=dict(p[field],links=filtered(p[field].get('links',[]),user))
    for version in p.get('history',[]):
        for field in ('payload','approved'):
            values=P.unpack(version['snapshot'].get(field),{})
            if values:version['snapshot'][field]=dict(values,links=filtered(values.get('links',[]),user))
    return p


def revision(row,data):
    if str(data.get('expected_revision'))!=str(row['revision']):
        raise tk.ValidationError({'expected_revision':tk._('Another editor saved changes. Reload before continuing.')})


def notify_reviewers(gid,output,message,url,exclude=''):
    ids={m['user_id'] for m in D.rows(D.members,D.members.c.group_id==gid,D.members.c.status=='active',D.members.c.role=='manager')}
    wg=IhpixWorkingGroup.get_by_output(output) if output else None
    if wg:
        ids.update(m.user_id for m in IhpixWorkingGroupMember.get_for_group(wg.id,'active') if m.role=='lead')
    for id in ids-{exclude}: S.notify(id,message,url)


def plan_url(plan):
    return tk.url_for('theme_ejemplo.ihpix_group_plan',slug=plan['group_id'],id=plan['id'])


def validate_plan(user, payload, g):
    payload=P.validate(payload,g['outputs'])
    for associated in payload['associated_groups']:
        access(user,associated)
        if not set([payload['output']]+payload['additional_outputs']) & set(group(associated)['outputs']):
            fail('associated_groups','Choose a group related to these outputs')
    from .ihpix_resource_access import visible
    if any(not visible(link,user) for link in payload['links']):fail('links','You cannot attach this resource')
    return payload


@action('ihpix_group_list',True)
def list_groups(context,data):
    user=actor(context);result=[]
    for row in D.rows(D.groups):
        g=group(row['id']);g['membership']=membership(user,g['id']);g['can_manage']=manager(user,g['id'])
        result.append(g)
    return {'results':sorted(result,key=lambda g:(g['kind']!='oetwg',g['id']))}


@action('ihpix_group_show',True)
def show_group(context,data):
    user=actor(context);g=group(data['group_id']);m=membership(user,g['id'])
    result=dict(g,membership=m,can_manage=manager(user,g['id']))
    result['can_read']=result['can_manage'] or bool(m and m['status']=='active')
    result['can_write']=g['status']=='active' and (result['can_manage'] or bool(m and m['status']=='active' and m['role']!='observer'))
    result['imports']=[];result['plans']=[];result['people']=[];result['contacts']=[];result['documents']=[];result['items']=[];result['reports']=[]
    for row in D.rows(D.plans):
        p=decode_plan(row)
        if p['group_id']!=g['id'] and g['id'] not in p['approved'].get('associated_groups',[]): continue
        try: item=plan_access(user,p['id'])
        except tk.NotAuthorized: continue
        payload=item['payload']
        if any(data.get(key) and data[key]!=payload.get(key) for key in ('output','institution','focal_point')): continue
        if data.get('biennium') and not payload['periods'].get(data['biennium']): continue
        if data.get('review_status') and data['review_status']!=item['review_status']: continue
        if data.get('execution_status') and data['execution_status']!=p['execution_status']: continue
        if data.get('q') and data['q'].casefold() not in json.dumps(payload,ensure_ascii=False).casefold(): continue
        result['plans'].append(present_plan(item,user))
    result['plans'].sort(key=lambda p:p['updated_at'],reverse=True)
    if not result['can_read']: return result
    if result['can_manage']:
        result['imports']=[dict(id=b['id'],kind=b['kind'],status=b['status'],rows=len(P.unpack(b['payload'],[])),filename=next((r.get('origin',{}).get('file','') for r in P.unpack(b['payload'],[])),'')) for b in D.rows(D.imports,D.imports.c.group_id==g['id'],D.imports.c.actor_id==user.id)]
    report_ids={rid for batch in D.rows(D.imports,D.imports.c.group_id==g['id'],D.imports.c.kind=='execution',D.imports.c.status=='applied') for rid in P.unpack(batch['result'],[])}
    for rid in report_ids:
        report=IhpixActivity.get(rid)
        if report and V.can_read(report,user):result['reports'].append({'id':rid,'title':report.title,'status':report.status})
    for member in D.rows(D.members,D.members.c.group_id==g['id']):
        if member['status']!='active' and not result['can_manage']: continue
        u=model.User.get(member['user_id'])
        if u: result['people'].append(dict(member,name=u.display_name,username=u.name))
    result['contacts']=[dict(c,payload=P.unpack(c['payload'],{})) for c in D.rows(D.contacts,D.contacts.c.group_id==g['id'])]
    # No cargar blobs para listar archivos.
    cols=[col for col in D.documents.c if col.name!='content']
    for raw in model.Session.execute(select(*cols).where(D.documents.c.group_id==g['id']).order_by(D.documents.c.created_at.desc())):
        doc=S.row_dict(raw)
        if doc['plan_id']:
            try: document_access(user,doc)
            except tk.NotAuthorized: continue
        result['documents'].append(doc)
    for item in D.rows(D.items,D.items.c.group_id==g['id']):
        if item['plan_id']:
            try: plan_access(user,item['plan_id'])
            except tk.NotAuthorized: continue
        u=model.User.get(item['author_id']);item['author']=u.display_name if u else ''
        item['can_edit']=g['status']=='active' and (result['can_manage'] or (result['can_write'] and item['author_id']==user.id))
        result['items'].append(item)
    result['items'].sort(key=lambda r:r['created_at'])
    return result


@action('ihpix_group_update')
def update_group(context,data):
    user=actor(context);D.row(D.groups,data['group_id'],True);g=group(data['group_id'])
    if not manager(user,g['id']): raise tk.NotAuthorized('Group manager required')
    if g['status']=='archived' and not user.sysadmin:raise tk.NotAuthorized('Archived workspaces are read-only')
    revision(g,data)
    updates={'revision':g['revision']+1}
    if 'title' in data:
        title=str(data['title']).strip()
        if not title or len(title)>300: fail('title','This field is required')
        updates['title']=title
    if 'outputs' in data:
        if not user.sysadmin: raise tk.NotAuthorized('Administrator access required')
        outputs=P.unpack(data['outputs'],[])
        if not outputs or any(o not in C.all_output_codes() for o in outputs): fail('outputs','Select a valid output')
        if g['kind']=='oetwg' and set(outputs)!=set(C.output_codes_for('PA'+g['id'][-1])): fail('outputs','OETWG outputs follow their priority area')
        if any(P.unpack(p['payload'],{}).get('output') not in outputs for p in D.rows(D.plans,D.plans.c.group_id==g['id']) if P.unpack(p['payload'],{}).get('output')):
            fail('outputs','Keep outputs that already have planned activities')
        updates['outputs']=json.dumps(sorted(set(outputs)))
        updates['source']='Administrator configuration'
    if 'status' in data:
        if not user.sysadmin: raise tk.NotAuthorized('Administrator access required')
        if data['status'] not in ('active','archived'): fail('status','Invalid status')
        updates['status']=data['status']
    D.put(D.groups,g['id'],**updates);return group(g['id'])


@action('ihpix_group_member_save')
def member_save(context,data):
    user=actor(context);g=group(data['group_id']);manages=manager(user,g['id'])
    target=model.User.get(data.get('user_id') or user.id)
    if not target or target.state!='active': fail('user_id','Choose an active user')
    model.Session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'member:'+g['id']+target.id})
    current=membership(target,g['id']);op=data.get('operation','request')
    if g['status']!='active': raise tk.NotAuthorized('Archived workspaces are read-only')
    if op=='request':
        if target.id!=user.id: raise tk.NotAuthorized('Not authorized')
        if current and current['status'] in ('active','pending'):return current
        values=dict(role='contributor',status='pending',institutional_role='')
    elif op=='leave':
        if target.id!=user.id or not current or current['role']=='manager':raise tk.NotAuthorized('A manager must arrange a replacement before leaving')
        values=dict(status='removed')
    else:
        if not manages: raise tk.NotAuthorized('Group manager required')
        role=data.get('role','contributor');status=data.get('status','active')
        if role not in ('manager','contributor','observer') or status not in ('active','removed'):fail('role','Invalid role or membership status')
        if target.id==user.id and current and current['role']=='manager' and (role!='manager' or status!='active'):
            fail('role','Another manager must change your role')
        values=dict(role=role,status=status,institutional_role=str(data.get('institutional_role',''))[:200])
    if current: D.put(D.members,current['id'],**values)
    else:D.insert(D.members,group_id=g['id'],user_id=target.id,**values)
    S.notify(target.id,'Working group membership updated',tk.url_for('theme_ejemplo.ihpix_group',slug=g['id']))
    if op=='request':notify_reviewers(g['id'],'','Membership request',tk.url_for('theme_ejemplo.ihpix_group',slug=g['id'],tab='members'),user.id)
    return membership(target,g['id'])


@action('ihpix_plan_save')
def save_plan(context,data):
    user=actor(context);gid=data['group_id'];g=access(user,gid,write=True)
    try:id=data.get('id') or P.identity(user.id,data.get('request_id'))
    except (ValueError,TypeError,AttributeError):fail('request_id','Invalid request identifier')
    model.Session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'plan:'+id})
    row=D.row(D.plans,id,True)
    if data.get('id') and not row:raise tk.ObjectNotFound('Planned activity not found')
    payload=validate_plan(user,P.unpack(data.get('payload'),{}) or {},g)
    if row:
        p=plan_access(user,id,write=True,lock=True)
        if p['group_id']!=gid: raise tk.NotAuthorized('Not authorized')
        if p['review_status']=='submitted':fail('review_status','Wait for review before editing')
        if payload==p['payload']:return present_plan(p,user)
        revision(p,data)
        D.put(D.plans,id,payload=json.dumps(payload,ensure_ascii=False),review_status='draft' if p['review_status']=='approved' else p['review_status'],revision=p['revision']+1,updated_at=S.now())
    else:
        D.insert(D.plans,id=id,group_id=gid,author_id=user.id,payload=json.dumps(payload,ensure_ascii=False),approved='{}',
                 review_status='draft',execution_status='planned',execution_note='',review_note='',revision=1,origin='{}',created_at=S.now(),updated_at=S.now())
    D.snapshot(D.row(D.plans,id),user,'save');return present_plan(plan_access(user,id),user)


@action('ihpix_plan_show',True)
def show_plan(context,data):
    user=actor(context);p=plan_access(user,data['id'])
    p['history']=[]
    if p['can_edit'] or p['can_review']:
        p['history']=[dict(v,snapshot=P.unpack(v['snapshot'],{})) for v in D.rows(D.versions,D.versions.c.plan_id==p['id'])]
    for version in p['history']:
        version['snapshot']['payload']=P.unpack(version['snapshot'].get('payload'),{})
    p['reports']=[]
    for link in D.rows(D.reports,D.reports.c.plan_id==p['id']):
        r=IhpixActivity.get(link['report_id'])
        if r and V.can_read(r,user):p['reports'].append({'id':r.id,'title':r.title,'status':r.status})
    return present_plan(p,user)


@action('ihpix_plan_transition')
def transition(context,data):
    user=actor(context);op=data.get('operation');p=plan_access(user,data['id'],write=True,review=op in ('approve','return'),lock=True)
    revision(p,data);changes={}
    if op=='submit':
        if p['review_status'] not in ('draft','returned'):fail('status','This proposal cannot be submitted')
        P.validate(p['payload'],group(p['group_id'])['outputs'],True)
        changes={'review_status':'submitted','review_note':''}
        notify_reviewers(p['group_id'],p['payload']['output'],'Planned activity awaiting review',plan_url(p),user.id)
    elif op in ('approve','return'):
        if p['review_status']!='submitted':fail('status','This proposal is not awaiting review')
        note=str(data.get('note','')).strip()
        if op=='return' and not note:fail('note','Add a reason for returning the proposal')
        changes={'review_status':'approved' if op=='approve' else 'returned','review_note':note[:10000]}
        if op=='approve':
            document_ids=[r[0] for r in model.Session.execute(select(D.documents.c.id).where(D.documents.c.plan_id==p['id']))]
            changes['approved']=json.dumps(dict(p['payload'],document_ids=document_ids),ensure_ascii=False)
        S.notify(p['author_id'],'Planned activity review completed',plan_url(p))
    elif op=='execution':
        if not p['approved']:fail('status','Approve the plan before updating execution')
        status=data.get('execution_status')
        if status not in P.EXECUTION:fail('execution_status','Invalid execution status')
        changes={'execution_status':status,'execution_note':str(data.get('note',''))[:10000]}
    else:fail('operation','Invalid operation')
    D.put(D.plans,p['id'],**dict(changes,revision=p['revision']+1,updated_at=S.now()))
    D.snapshot(D.row(D.plans,p['id']),user,op);return present_plan(plan_access(user,p['id']),user)


@action('ihpix_plan_report_create')
def create_report(context,data):
    user=actor(context);p=plan_access(user,data['id'],write=True,lock=True)
    if not p['approved']:fail('id','Approve the plan before reporting execution')
    try:request_id=str(uuid.UUID(data.get('request_id','')))
    except (ValueError,TypeError):fail('request_id','Invalid request identifier')
    values=p['approved']
    periods=[b for b in P.BIENNIA if values.get('periods',{}).get(b)]
    biennium=data.get('biennium') or (periods[0] if len(periods)==1 else '')
    if biennium not in periods:fail('biennium','Choose a biennium from the agreed plan')
    # Un formulario restaurado por el navegador puede conservar UUID al cambiar el bienio.
    request_id=str(uuid.uuid5(uuid.UUID(request_id),p['id']+':'+biennium))
    existing=D.rows(D.reports,D.reports.c.actor_id==user.id,D.reports.c.request_id==request_id)
    if existing:
        if existing[0]['plan_id']!=p['id']:raise tk.NotAuthorized('Not authorized')
        return {'id':existing[0]['report_id']}
    # Reanudar el borrador editable de este usuario/período bajo el bloqueo del plan.
    for link in D.rows(D.reports,D.reports.c.plan_id==p['id'],D.reports.c.actor_id==user.id):
        report=IhpixActivity.get(link['report_id'])
        if report and report.status in ('draft','rejected') and report.biennium==biennium and (report.is_owned_by(user) or user.sysadmin or V.can_collaborate(report,user)):
            return {'id':report.id}
    from .ihpix_resource_access import filtered
    # Precargar contexto; nunca copiar compromisos a resultados, indicadores o fechas reales.
    inputs=dict(title=values['title'],biennium=biennium,partners=values.get('partners','') if len(values.get('partners',''))<=500 else '',priority_area='PA'+values['output'][0],
                output=values['output'],key_activity_code=values['key_activity_code'],focal_point_name=values['focal_point'],
                institution=values['institution'],contact_email=values['email'] if re.fullmatch(r'[^\s@;,]+@[^\s@;,]+\.[^\s@;,]+',values['email']) else '',
                save_as_draft='1',links_json=json.dumps(filtered(values.get('links',[]),user)))
    inputs['contributions_json']=json.dumps([{'priority_area':'PA'+values['output'][0],'output':values['output'],'key_activity_code':values['key_activity_code']}]+[{'priority_area':'PA'+o[0],'output':o,'key_activity_code':''} for o in values.get('additional_outputs',[]) if o!=values['output']])
    report=V.save(context,inputs)
    D.insert(D.reports,plan_id=p['id'],report_id=report.id,actor_id=user.id,request_id=request_id)
    return {'id':report.id}


@action('ihpix_group_document_save')
def document_save(context,data):
    user=actor(context);g=access(user,data['group_id'],write=True);plan_id=data.get('plan_id','')
    if plan_id:
        p=plan_access(user,plan_id,write=True,lock=True)
        if p['group_id']!=g['id']:fail('plan_id','Choose an activity of this group')
        if p['review_status']=='submitted':fail('plan_id','Wait for review before editing')
    upload=data.get('upload');filename=os.path.basename(getattr(upload,'filename',''))
    if not filename or filename.rsplit('.',1)[-1].lower() not in P.DOC_EXTENSIONS:fail('file','This file type is not allowed')
    raw=upload.read(20*1024*1024+1)
    if not raw or len(raw)>20*1024*1024:fail('file','The file exceeds the upload limit')
    category=data.get('category','other')
    if category not in P.DOC_CATEGORIES:fail('category','Invalid category')
    title=str(data.get('title') or filename).strip()[:300];replaces_id=data.get('replaces_id','');version=1
    if replaces_id:
        previous=D.row(D.documents,replaces_id,True)
        if not previous or previous['group_id']!=g['id'] or previous['plan_id']!=plan_id:fail('replaces_id','Choose a document of this group and activity')
        version=previous['version']+1
        if D.rows(D.documents,D.documents.c.replaces_id==replaces_id):fail('replaces_id','This document already has a newer version')
    digest=hashlib.sha256(raw).hexdigest()
    model.Session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'document:'+g['id']+plan_id+digest+title})
    duplicate=D.rows(D.documents,D.documents.c.group_id==g['id'],D.documents.c.plan_id==plan_id,D.documents.c.digest==digest,D.documents.c.title==title)
    if duplicate:return dict(id=duplicate[0]['id'],**({'plan_revision':p['revision']} if plan_id else {}))
    id=D.insert(D.documents,group_id=g['id'],plan_id=plan_id,author_id=user.id,title=title,category=category,
                filename=filename,content=raw,digest=digest,version=version,replaces_id=replaces_id,created_at=S.now())
    result={'id':id}
    if plan_id:
        D.put(D.plans,plan_id,review_status='draft' if p['approved'] else p['review_status'],revision=p['revision']+1,updated_at=S.now())
        D.snapshot(D.row(D.plans,plan_id),user,'document')
        result['plan_revision']=p['revision']+1
    return result


def document_access(user,doc):
    if doc['plan_id']:
        p=plan_access(user,doc['plan_id'])
        if not p['can_edit'] and not p['can_review'] and p['approved'] and doc['id'] not in p['approved'].get('document_ids',[]):
            raise tk.NotAuthorized('Document is not part of the agreed plan')
    else:access(user,doc['group_id'])


@action('ihpix_group_document_show',True)
def document_show(context,data):
    user=actor(context);doc=D.row(D.documents,data['id'])
    if not doc:raise tk.ObjectNotFound('Document not found')
    document_access(user,doc)
    # El blob sólo sale por la vista de descarga autorizada, no por la API JSON.
    return {k:v for k,v in doc.items() if k!='content'}


@action('ihpix_group_contact_save')
def contact_save(context,data):
    user=actor(context);g=access(user,data['group_id'],write=True,manage=True)
    old=D.row(D.contacts,data.get('id',''),True) if data.get('id') else None
    if old:
        if old['group_id']!=g['id']:raise tk.NotAuthorized('Not authorized')
        revision(old,data)
    if data.get('id') and not old:raise tk.ObjectNotFound('Contact not found')
    raw=P.unpack(data.get('payload'),{})
    if not isinstance(raw,dict):fail('payload','Invalid request')
    payload=P.validate_contact(dict(raw,outputs=P.unpack(data.get('outputs'),[])));uid=data.get('user_id','')
    if uid:
        person=model.User.get(uid)
        if not person or person.state!='active' or person.email.casefold()!=payload['email'].casefold():fail('user_id','Link only an active account with the same email')
        uid=person.id
    values=dict(payload=json.dumps(payload,ensure_ascii=False),user_id=uid,digest=P.digest(payload))
    if old:D.put(D.contacts,old['id'],**dict(values,revision=old['revision']+1));return {'id':old['id']}
    existing=D.rows(D.contacts,D.contacts.c.group_id==g['id'],D.contacts.c.digest==values['digest'])
    if existing:return {'id':existing[0]['id']}
    return {'id':D.insert(D.contacts,group_id=g['id'],revision=1,**values)}


@action('ihpix_group_item_save')
def item_save(context,data):
    user=actor(context);g=access(user,data['group_id'],write=True);old=D.row(D.items,data.get('id',''),True) if data.get('id') else None
    if old:
        if old['group_id']!=g['id']:raise tk.NotAuthorized('Not authorized')
        revision(old,data)
        if user.id not in (old['author_id'],old['assignee_id']) and not manager(user,g['id']):raise tk.NotAuthorized('Not authorized')
        status=data.get('status')
        if status not in ('pending','ongoing','done'):fail('status','Invalid task status')
        D.put(D.items,old['id'],status=status,revision=old['revision']+1);return {'id':old['id']}
    kind=data.get('kind','post');body=str(data.get('body','')).strip()
    if kind not in ('post','task') or not body or len(body)>20000:fail('body','Add a message of at most 20000 characters')
    parent_id=data.get('parent_id','');plan_id=data.get('plan_id','');document_id=data.get('document_id','')
    if parent_id:
        parent=D.row(D.items,parent_id)
        if not parent or parent['group_id']!=g['id']:fail('parent_id','Choose a conversation of this group')
        plan_id=parent['plan_id'];document_id=parent['document_id']
    if plan_id:
        p=plan_access(user,plan_id)
        if p['group_id']!=g['id']:fail('plan_id','Choose an activity of this group')
    if document_id:
        doc=document_show(context,{'id':document_id})
        if doc['group_id']!=g['id']:fail('document_id','Choose a document of this group')
        if doc['plan_id']:
            if plan_id and plan_id!=doc['plan_id']:fail('plan_id','Choose the document activity')
            plan_id=doc['plan_id']
    assignee_id=data.get('assignee_id','');due=data.get('due_date','')
    if assignee_id:
        assignee=model.User.get(assignee_id)
        if not assignee:fail('assignee_id','Choose an active group member')
        access(assignee,g['id'],write=True)
        if plan_id:plan_access(assignee,plan_id)
        assignee_id=assignee.id
    if due:
        try:datetime.datetime.strptime(due,'%Y-%m-%d')
        except ValueError:fail('due_date','Enter a valid date')
    id=D.insert(D.items,group_id=g['id'],author_id=user.id,parent_id=parent_id,plan_id=plan_id,document_id=document_id,
                kind=kind,title=str(data.get('title',''))[:300],body=body,assignee_id=assignee_id,due_date=due,status='pending',revision=1,created_at=S.now())
    if assignee_id:S.notify(assignee_id,'New working group task',tk.url_for('theme_ejemplo.ihpix_group',slug=g['id'],tab='conversations'))
    if parent_id and parent['author_id']!=user.id:S.notify(parent['author_id'],'New reply in your working group',tk.url_for('theme_ejemplo.ihpix_group',slug=g['id'],tab='conversations'))
    return {'id':id}


@action('ihpix_group_import_preview')
def import_preview(context,data):
    user=actor(context);g=access(user,data['group_id'],write=True,manage=True);kind=data.get('kind','plans')
    if kind not in ('plans','contacts','execution'):fail('kind','Choose plans, contacts or execution reports')
    if len(data.get('workbook',''))>14*1024*1024:fail('file','Workbook is too large')
    try:raw=base64.b64decode(data.get('workbook',''),validate=True)
    except (ValueError,TypeError):fail('file','Choose an XLSX workbook')
    digest=hashlib.sha256(raw).hexdigest()
    model.Session.execute(text('SELECT pg_advisory_xact_lock(hashtext(:key))'),{'key':'import:'+g['id']+user.id+kind+digest})
    previous=D.rows(D.imports,D.imports.c.group_id==g['id'],D.imports.c.actor_id==user.id,D.imports.c.kind==kind,D.imports.c.digest==digest)
    if previous:return import_show(context,{'id':previous[0]['id']})
    rows=({'plans':P.parse_plans,'contacts':P.parse_contacts,'execution':E.parse}[kind])(raw,str(data.get('filename','workbook.xlsx'))[:300])
    existing=[decode_plan(p) for p in D.rows(D.plans,D.plans.c.group_id==g['id'])] if kind=='plans' else [dict(p,payload=P.unpack(p['payload'],{})) for p in D.rows(D.contacts,D.contacts.c.group_id==g['id'])]
    if kind=='execution':
        existing=[{'id':r.id,'payload':r.as_dict()} for r in model.Session.query(IhpixActivity).filter(IhpixActivity.output.in_(g['outputs'])).all() if V.can_read(r,user)]
    for row in rows:
        row['warnings']=[];row['errors']={};row['match']=None
        if kind=='plans':
            try:P.validate(row,g['outputs'],True)
            except P.Invalid as exc:row['warnings']=list(exc.errors.values())
            try:P.validate(row,g['outputs'])
            except P.Invalid as exc:row['errors']=exc.errors
        elif kind=='execution':
            row['warnings']=[row.pop('source_warning')]
            try:E.validate(row,g['outputs'])
            except P.Invalid as exc:row['errors']=exc.errors
        else:
            try:P.validate_contact(row)
            except P.Invalid as exc:row['errors']=exc.errors
        exact=next((p for p in existing if P.digest(p['payload'])==P.digest(row)),None)
        candidates=[p for p in existing if ((kind in ('plans','execution') and p['payload'].get('title','').strip().casefold()==row['title'].strip().casefold() and p['payload'].get('output')==row['output']) or
                    (kind=='contacts' and ((row.get('email') and row['email'].casefold()==p['payload'].get('email','').casefold()) or row['name'].casefold()==p['payload'].get('name','').casefold())))]
        row['match']={'kind':'exact','id':exact['id']} if exact else ({'kind':'conflict','candidates':[p['id'] for p in candidates]} if candidates else None)
    id=D.insert(D.imports,group_id=g['id'],actor_id=user.id,kind=kind,digest=digest,payload=json.dumps(rows,ensure_ascii=False),status='preview',result='[]',created_at=S.now())
    return import_show(context,{'id':id})


@action('ihpix_group_import_show',True)
def import_show(context,data):
    user=actor(context);batch=D.row(D.imports,data['id'])
    if not batch:raise tk.ObjectNotFound('Import not found')
    access(user,batch['group_id'],manage=True)
    if batch['actor_id']!=user.id:raise tk.NotAuthorized('Import belongs to another user')
    return dict(batch,payload=P.unpack(batch['payload'],[]),result=P.unpack(batch['result'],[]))


@action('ihpix_group_import_apply')
def import_apply(context,data):
    user=actor(context);batch=import_show(context,data);access(user,batch['group_id'],write=True,manage=True)
    locked=D.row(D.imports,batch['id'],True)
    if locked['status']=='applied':return {'ids':P.unpack(locked['result'],[])}
    choices=P.unpack(data.get('rows'),[])
    if not isinstance(choices,list) or len(choices)>2000:fail('rows','Invalid import selection')
    ids=[]
    for choice in choices:
        if not isinstance(choice,dict):fail('rows','Invalid row')
        index=choice.get('index');decision=choice.get('decision','skip')
        if not isinstance(index,int) or index<0 or index>=len(batch['payload']):fail('rows','Invalid row')
        if decision=='skip':continue
        if decision not in ('new','replace','existing'):fail('rows','Choose how to reconcile this row')
        row=dict(batch['payload'][index]);updates=choice.get('payload',{})
        if not isinstance(updates,dict):fail('rows','Invalid row')
        row.update({k:v for k,v in updates.items() if k not in ('origin','match','warnings','errors')})
        origin=row.pop('origin',{});match=row.pop('match',None);row.pop('warnings',None);row.pop('errors',None)
        if batch['kind']=='execution':
            if decision=='existing':
                report=IhpixActivity.get(choice.get('target_id',''))
                if not report or not V.can_read(report,user) or report.output not in group(batch['group_id'])['outputs']:raise tk.NotAuthorized('Not authorized')
                if report.id not in (match or {}).get('candidates',[]):fail('rows','Choose an existing matching report')
                id=report.id
            elif decision=='new':
                values=E.validate(row,group(batch['group_id'])['outputs'])
                # Identidad estable por lote/fila: también evita duplicados si se selecciona dos veces.
                id=str(uuid.uuid5(uuid.NAMESPACE_URL,'ihpix-import:'+batch['id']+':'+str(index)))
                if not IhpixActivity.get(id):V.save(context,dict(values,save_as_draft='1'),new_id=id)
            else:fail('rows','Existing execution reports are linked without overwriting them')
        elif batch['kind']=='plans':
            if decision=='existing':fail('rows','Choose how to reconcile this row')
            clean=validate_plan(user,row,group(batch['group_id']))
            old=None
            if decision=='replace':
                old=plan_access(user,choice.get('target_id',''),write=True,lock=True)
                if old['group_id']!=batch['group_id']:raise tk.NotAuthorized('Not authorized')
                revision(old,choice)
                if old['review_status']=='submitted':fail('rows','Wait for review before editing')
            else:
                existing=[p for p in D.rows(D.plans,D.plans.c.group_id==batch['group_id']) if P.digest(P.unpack(p['payload'],{}))==P.digest(clean)]
                if existing:
                    id=existing[0]['id'];old=D.row(D.plans,id,True)
                    previous=P.unpack(old['origin'],{})
                    sources=previous.get('sources') or ([{k:v for k,v in previous.items() if k!='sources'}] if previous else [])
                    if origin and origin not in sources:
                        sources.append(origin)
                        D.put(D.plans,id,origin=json.dumps(dict(previous,sources=sources),ensure_ascii=False),revision=old['revision']+1,updated_at=S.now())
                        D.snapshot(D.row(D.plans,id),user,'import_source')
                    ids.append(id);continue
            if old:
                id=old['id'];D.put(D.plans,id,payload=json.dumps(clean,ensure_ascii=False),origin=json.dumps(origin),revision=old['revision']+1,review_status='draft',updated_at=S.now())
            else:
                id=D.insert(D.plans,group_id=batch['group_id'],author_id=user.id,payload=json.dumps(clean,ensure_ascii=False),approved='{}',review_status='draft',execution_status='planned',execution_note='',review_note='',revision=1,origin=json.dumps(origin),created_at=S.now(),updated_at=S.now())
            D.snapshot(D.row(D.plans,id),user,'import')
        else:
            if decision=='existing':fail('rows','Choose how to reconcile this row')
            row=P.validate_contact(row)
            digest=P.digest(row);existing=D.rows(D.contacts,D.contacts.c.group_id==batch['group_id'],D.contacts.c.digest==digest)
            if existing:ids.append(existing[0]['id']);continue
            if decision=='replace':
                old=D.row(D.contacts,choice.get('target_id',''),True)
                if not old or old['group_id']!=batch['group_id']:raise tk.NotAuthorized('Not authorized')
                revision(old,choice);id=old['id'];D.put(D.contacts,id,payload=json.dumps(dict(row,origin=origin),ensure_ascii=False),digest=digest,revision=old['revision']+1,user_id='')
            else:id=D.insert(D.contacts,group_id=batch['group_id'],payload=json.dumps(dict(row,origin=origin),ensure_ascii=False),digest=digest,revision=1,user_id='')
        ids.append(id)
    D.put(D.imports,batch['id'],status='applied',result=json.dumps(ids));return {'ids':ids}
