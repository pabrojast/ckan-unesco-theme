# -*- coding: utf-8 -*-
"""Tablas aditivas para versiones, colaboración e importaciones IHP-IX.

Las escrituras usan la misma Session del reporte; no hacen commit implícito.
"""
import datetime
import json
import uuid

from sqlalchemy import (Table, Column, UnicodeText, Integer, Boolean, Date, select, text,
                        DateTime, UniqueConstraint, Index)
from ckan.model import meta

revisions = Table('ihpix_report_revision', meta.metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('activity_id', UnicodeText, nullable=False, index=True),
    Column('revision', Integer, nullable=False),
    Column('user_id', UnicodeText, nullable=False),
    Column('snapshot', UnicodeText, nullable=False),
    Column('created_at', DateTime, nullable=False),
    UniqueConstraint('activity_id', 'revision'))

collaborators = Table('ihpix_report_collaborator', meta.metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('activity_id', UnicodeText, nullable=False, index=True),
    Column('user_id', UnicodeText, nullable=False),
    Column('invited_by', UnicodeText, nullable=False),
    Column('active', Boolean, nullable=False, default=True),
    Column('created_at', DateTime, nullable=False),
    UniqueConstraint('activity_id', 'user_id'))

items = Table('ihpix_workspace_item', meta.metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('working_group_id', UnicodeText, nullable=False, index=True),
    Column('kind', UnicodeText, nullable=False),
    Column('activity_id', UnicodeText, default=''),
    Column('link_id', UnicodeText, default=''),
    Column('author_id', UnicodeText, nullable=False),
    Column('title', UnicodeText, default=''),
    Column('body', UnicodeText, nullable=False),
    Column('assignee_id', UnicodeText, default=''),
    Column('due_date', Date, nullable=True),
    Column('status', UnicodeText, default='pending'),
    Column('revision', Integer, nullable=False, default=1),
    Column('deleted', Boolean, nullable=False, default=False),
    Column('created_at', DateTime, nullable=False),
    Column('updated_at', DateTime, nullable=False))

notifications = Table('ihpix_notification', meta.metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('user_id', UnicodeText, nullable=False, index=True),
    Column('message', UnicodeText, nullable=False),
    Column('url', UnicodeText, nullable=False),
    Column('is_read', Boolean, nullable=False, default=False),
    Column('created_at', DateTime, nullable=False))

imports = Table('ihpix_import_batch', meta.metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('user_id', UnicodeText, nullable=False),
    Column('digest', UnicodeText, nullable=False),
    Column('payload', UnicodeText, nullable=False),
    Column('result', UnicodeText, nullable=False, default='[]'),
    Column('status', UnicodeText, nullable=False, default='preview'),
    Column('created_at', DateTime, nullable=False),
    UniqueConstraint('user_id', 'digest'))


def init_db():
    # Se llama durante el arranque/migración, antes de abrir transacciones.
    with meta.engine.begin() as connection:
        if connection.dialect.name == 'postgresql':
            connection.execute(text("SELECT pg_advisory_xact_lock(hashtext('ihpix-review-schema-v1'))"))
        meta.metadata.create_all(connection, tables=[revisions, collaborators, items,
                                                    notifications, imports], checkfirst=True)


def now():
    return datetime.datetime.utcnow()


def uid():
    return str(uuid.uuid4())


def row_dict(row):
    return dict(row._mapping) if hasattr(row, '_mapping') else dict(row)


def notify(user_id, message, url):
    meta.Session.execute(notifications.insert().values(
        id=uid(), user_id=user_id, message=message, url=url,
        is_read=False, created_at=now()))


def ensure_baseline(activity, links):
    """Conserva el estado heredado antes de su primera modificación; requiere bloqueo."""
    if activity.revision or meta.Session.execute(select(revisions.c.id).where(
            revisions.c.activity_id == activity.id)).first():
        return
    payload = activity.as_dict()
    payload['links'] = links
    meta.Session.execute(revisions.insert().values(
        id=uid(), activity_id=activity.id, revision=0,
        user_id=activity.reported_by or '', snapshot=json.dumps(payload, ensure_ascii=False),
        created_at=activity.updated_at or activity.created_at or now()))


def snapshot(activity, user_id, links):
    activity.revision = (activity.revision or 0) + 1
    payload = activity.as_dict()
    payload['links'] = links
    meta.Session.execute(revisions.insert().values(
        id=uid(), activity_id=activity.id, revision=activity.revision,
        user_id=user_id, snapshot=json.dumps(payload, ensure_ascii=False),
        created_at=now()))
