"""Persistencia aditiva de grupos y planificación; archivos privados fuera del catálogo público."""
import json
from sqlalchemy import Table, Column, UnicodeText as T, Integer, DateTime, LargeBinary, UniqueConstraint, text, select
from ckan.model import meta
from . import ihpix_store as S, ihpix_planning as P


def table(name, *columns):
    return Table('ihpix_'+name, meta.metadata, Column('id',T,primary_key=True), *columns)


groups=table('group',Column('kind',T,nullable=False),Column('title',T,nullable=False),Column('outputs',T,nullable=False),
             Column('source',T),Column('status',T,nullable=False,default='active'),Column('revision',Integer,nullable=False,default=1))
members=table('group_member',Column('group_id',T,nullable=False,index=True),Column('user_id',T,nullable=False),
              Column('role',T,nullable=False),Column('status',T,nullable=False),Column('institutional_role',T,default=''),
              UniqueConstraint('group_id','user_id'))
plans=table('planned_activity',Column('group_id',T,nullable=False,index=True),Column('author_id',T,nullable=False,index=True),
            Column('payload',T,nullable=False),Column('approved',T,nullable=False,default='{}'),
            Column('review_status',T,nullable=False,default='draft'),Column('execution_status',T,nullable=False,default='planned'),
            Column('execution_note',T,default=''),Column('review_note',T,default=''),Column('revision',Integer,nullable=False),
            Column('origin',T,default='{}'),Column('created_at',DateTime,nullable=False),Column('updated_at',DateTime,nullable=False))
versions=table('plan_version',Column('plan_id',T,nullable=False,index=True),Column('revision',Integer,nullable=False),
               Column('actor_id',T,nullable=False),Column('event',T,nullable=False),Column('snapshot',T,nullable=False),
               Column('created_at',DateTime,nullable=False),UniqueConstraint('plan_id','revision'))
reports=table('plan_report',Column('plan_id',T,nullable=False,index=True),Column('report_id',T,nullable=False,unique=True),
              Column('actor_id',T,nullable=False),Column('request_id',T,nullable=False),
              UniqueConstraint('actor_id','request_id'))
contacts=table('group_contact',Column('group_id',T,nullable=False,index=True),Column('payload',T,nullable=False),
               Column('user_id',T,default=''),Column('revision',Integer,nullable=False,default=1),Column('digest',T,nullable=False),
               UniqueConstraint('group_id','digest'))
documents=table('group_document',Column('group_id',T,nullable=False,index=True),Column('plan_id',T,default='',index=True),
                Column('author_id',T,nullable=False),Column('title',T,nullable=False),Column('category',T,nullable=False),
                Column('filename',T,nullable=False),Column('content',LargeBinary,nullable=False),Column('digest',T,nullable=False),
                Column('version',Integer,nullable=False),Column('replaces_id',T,default=''),Column('created_at',DateTime,nullable=False))
items=table('group_item',Column('group_id',T,nullable=False,index=True),Column('author_id',T,nullable=False),
            Column('parent_id',T,default=''),Column('plan_id',T,default=''),Column('document_id',T,default=''),
            Column('kind',T,nullable=False),Column('title',T,default=''),Column('body',T,nullable=False),
            Column('assignee_id',T,default=''),Column('due_date',T,default=''),Column('status',T,nullable=False,default='pending'),
            Column('revision',Integer,nullable=False),Column('created_at',DateTime,nullable=False))
imports=table('group_import',Column('group_id',T,nullable=False,index=True),Column('actor_id',T,nullable=False),
              Column('kind',T,nullable=False),Column('digest',T,nullable=False),Column('payload',T,nullable=False),
              Column('status',T,nullable=False),Column('result',T,default='[]'),Column('created_at',DateTime,nullable=False),
              UniqueConstraint('group_id','actor_id','kind','digest'))
TABLES=[groups,members,plans,versions,reports,contacts,documents,items,imports]


def init_db():
    with meta.engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('ihpix-groups-v1'))"))
        meta.metadata.create_all(connection,tables=TABLES,checkfirst=True)
        for group in P.seeds():
            if not connection.execute(select(groups.c.id).where(groups.c.id==group['id'])).first():
                connection.execute(groups.insert().values(**dict(group,outputs=json.dumps(group['outputs']),status='active',revision=1)))


def row(table, id, lock=False):
    query=select(table).where(table.c.id==id)
    if lock: query=query.with_for_update()
    result=meta.Session.execute(query).first()
    return S.row_dict(result) if result else None


def rows(table, *where):
    return [S.row_dict(r) for r in meta.Session.execute(select(table).where(*where)).fetchall()]


def put(table, id, **values):
    meta.Session.execute(table.update().where(table.c.id==id).values(**values))


def insert(table, **values):
    values.setdefault('id',S.uid());meta.Session.execute(table.insert().values(**values));return values['id']


def snapshot(plan, actor, event):
    insert(versions,plan_id=plan['id'],revision=plan['revision'],actor_id=actor.id,event=event,
           snapshot=json.dumps(plan,default=str,ensure_ascii=False),created_at=S.now())
