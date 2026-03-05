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
        self.role = u'member'
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
        # Migrate: add 'role' column if missing
        columns = [c['name'] for c in inspector.get_columns('membership_request')]
        if 'role' not in columns:
            engine.execute(
                "ALTER TABLE membership_request ADD COLUMN role TEXT DEFAULT 'member'"
            )
            log.info(u'membership_request table: added role column')
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
        Column('role', UnicodeText, default=u'member'),
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


# ── Bug Ticket Model ─────────────────────────────────────────────────────────

bug_ticket_table = None


class BugTicket(model.DomainObject):
    """A bug/issue ticket submitted by a user."""

    STATUS_OPEN = u'open'
    STATUS_IN_PROGRESS = u'in_progress'
    STATUS_RESOLVED_USER = u'resolved_by_user'
    STATUS_RESOLVED_ADMIN = u'resolved_by_admin'

    VALID_STATUSES = (STATUS_OPEN, STATUS_IN_PROGRESS,
                      STATUS_RESOLVED_USER, STATUS_RESOLVED_ADMIN)

    def __init__(self, user_id, title, description, url=u'',
                 image_filename=u'', browser_info=u'', log_snapshot=u''):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.title = title
        self.description = description
        self.url = url
        self.image_filename = image_filename
        self.browser_info = browser_info
        self.log_snapshot = log_snapshot
        self.status = self.STATUS_OPEN
        self.admin_notes = u''
        self.resolved_by = None
        self.resolved_at = None
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_all(cls, status=None, user_id=None, limit=100, offset=0):
        q = meta.Session.query(cls)
        if status:
            q = q.filter(cls.status == status)
        if user_id:
            q = q.filter(cls.user_id == user_id)
        total = q.count()
        results = q.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
        return results, total

    def as_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'description': self.description,
            'url': self.url,
            'image_filename': self.image_filename,
            'browser_info': self.browser_info,
            'log_snapshot': self.log_snapshot,
            'status': self.status,
            'admin_notes': self.admin_notes,
            'resolved_by': self.resolved_by,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def init_bug_tickets_db():
    """Create the bug_ticket table if it doesn't exist."""
    if bug_ticket_table is None:
        define_bug_ticket_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'bug_ticket' not in inspector.get_table_names():
        bug_ticket_table.create(meta.engine)
        log.info(u'bug_ticket table created')
    else:
        log.debug(u'bug_ticket table already exists')


def define_bug_ticket_table():
    global bug_ticket_table

    bug_ticket_table = Table(
        'bug_ticket',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('user_id', UnicodeText, nullable=False),
        Column('title', UnicodeText, nullable=False),
        Column('description', UnicodeText, nullable=False),
        Column('url', UnicodeText, default=u''),
        Column('image_filename', UnicodeText, default=u''),
        Column('browser_info', UnicodeText, default=u''),
        Column('log_snapshot', UnicodeText, default=u''),
        Column('status', UnicodeText, default=u'open'),
        Column('admin_notes', UnicodeText, default=u''),
        Column('resolved_by', UnicodeText, nullable=True),
        Column('resolved_at', DateTime, nullable=True),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(BugTicket, bug_ticket_table)
    except AttributeError:
        meta.mapper(BugTicket, bug_ticket_table)
