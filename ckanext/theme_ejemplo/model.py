# encoding: utf-8
"""SQLAlchemy model for membership requests."""

import datetime
import uuid
import logging

from sqlalchemy import Table, Column, UnicodeText, DateTime, Integer

import ckan.model as model
import ckan.model.meta as meta

log = logging.getLogger(__name__)

membership_request_table = None


class MembershipRequest(model.DomainObject):
    """A request from a user to join an organization."""

    STATUS_PENDING = u'pending'
    STATUS_APPROVED = u'approved'
    STATUS_REJECTED = u'rejected'

    def __init__(self, user_id, organization_id, message=u''):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.organization_id = organization_id
        self.message = message
        self.status = self.STATUS_PENDING
        self.handled_by = None
        self.handled_at = None
        self.admin_note = u''
        self.created_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_pending_for_org(cls, organization_id):
        return meta.Session.query(cls).filter(
            cls.organization_id == organization_id,
            cls.status == cls.STATUS_PENDING,
        ).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_for_org(cls, organization_id, status=None):
        q = meta.Session.query(cls).filter(
            cls.organization_id == organization_id,
        )
        if status:
            q = q.filter(cls.status == status)
        return q.order_by(cls.created_at.desc()).all()

    @classmethod
    def get_pending_for_user_and_org(cls, user_id, organization_id):
        return meta.Session.query(cls).filter(
            cls.user_id == user_id,
            cls.organization_id == organization_id,
            cls.status == cls.STATUS_PENDING,
        ).first()

    @classmethod
    def count_pending_for_orgs(cls, org_ids):
        """Count pending requests across multiple organizations."""
        if not org_ids:
            return 0
        return meta.Session.query(cls).filter(
            cls.organization_id.in_(org_ids),
            cls.status == cls.STATUS_PENDING,
        ).count()


def init_db():
    """Create the membership_request table if it doesn't exist."""
    if membership_request_table is None:
        define_membership_request_table()

    from sqlalchemy import inspect as sa_inspect
    engine = meta.engine
    inspector = sa_inspect(engine)
    if 'membership_request' not in inspector.get_table_names():
        membership_request_table.create(engine)
        log.info(u'membership_request table created')
    else:
        log.debug(u'membership_request table already exists')


def define_membership_request_table():
    global membership_request_table

    membership_request_table = Table(
        'membership_request',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('user_id', UnicodeText, nullable=False),
        Column('organization_id', UnicodeText, nullable=False),
        Column('message', UnicodeText, default=u''),
        Column('status', UnicodeText, default=u'pending'),
        Column('handled_by', UnicodeText, nullable=True),
        Column('handled_at', DateTime, nullable=True),
        Column('admin_note', UnicodeText, default=u''),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
    )

    # Use registry mapper if available (SQLAlchemy 1.4+/CKAN 2.10),
    # fall back to classic mapper for CKAN 2.9
    try:
        meta.registry.map_imperatively(MembershipRequest, membership_request_table)
    except AttributeError:
        meta.mapper(MembershipRequest, membership_request_table)


# ── Featured Publication Model ───────────────────────────────────────────────

featured_publication_table = None


class FeaturedPublication(model.DomainObject):
    """A featured UNESDOC publication for the homepage."""

    def __init__(self, title, link, description=u'', image_url=u'',
                 display_order=0):
        self.id = str(uuid.uuid4())
        self.title = title
        self.link = link
        self.description = description
        self.image_url = image_url
        self.display_order = display_order
        self.created_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_all(cls):
        return meta.Session.query(cls).order_by(
            cls.display_order.asc(), cls.created_at.desc()
        ).all()

    def as_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'link': self.link,
            'display_order': self.display_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def init_featured_publications_db():
    """Create the featured_publication table if it doesn't exist."""
    if featured_publication_table is None:
        define_featured_publication_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'featured_publication' not in inspector.get_table_names():
        featured_publication_table.create(meta.engine)
        log.info(u'featured_publication table created')
    else:
        log.debug(u'featured_publication table already exists')


def define_featured_publication_table():
    global featured_publication_table

    featured_publication_table = Table(
        'featured_publication',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('title', UnicodeText, nullable=False),
        Column('description', UnicodeText, default=u''),
        Column('image_url', UnicodeText, default=u''),
        Column('link', UnicodeText, nullable=False),
        Column('display_order', Integer, default=0),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(FeaturedPublication, featured_publication_table)
    except AttributeError:
        meta.mapper(FeaturedPublication, featured_publication_table)
