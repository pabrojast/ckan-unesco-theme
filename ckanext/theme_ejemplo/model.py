# encoding: utf-8
"""SQLAlchemy model for membership requests."""

import datetime
import uuid
import logging

from sqlalchemy import Table, Column, UnicodeText, DateTime, Integer, BigInteger, Boolean, Date, Text, Index

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

    from sqlalchemy import inspect as sa_inspect, text as sa_text
    engine = meta.engine
    inspector = sa_inspect(engine)
    if 'membership_request' not in inspector.get_table_names():
        membership_request_table.create(engine)
        log.info(u'membership_request table created')
    else:
        # Migrate: add 'role' column if missing
        columns = [c['name'] for c in inspector.get_columns('membership_request')]
        if 'role' not in columns:
            with engine.connect() as conn:
                conn.execute(sa_text(
                    "ALTER TABLE membership_request ADD COLUMN role TEXT DEFAULT 'member'"
                ))
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


# ── Portal Card Model ────────────────────────────────────────────────────────

portal_card_table = None

VALID_PORTAL_IDS = ('flood_drought', 'iot', 'citizen_science')


class PortalCard(model.DomainObject):
    """A card displayed on one of the portal pages (IoT, Flood/Drought, Citizen Science)."""

    def __init__(self, portal_id, title, link, description=u'',
                 image_url=u'', display_order=0, is_coming_soon=False,
                 is_archived=False):
        self.id = str(uuid.uuid4())
        self.portal_id = portal_id
        self.title = title
        self.link = link
        self.description = description
        self.image_url = image_url
        self.display_order = display_order
        self.is_coming_soon = is_coming_soon
        self.is_archived = is_archived
        self.created_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_by_portal(cls, portal_id):
        """Return all cards for a portal (including archived)."""
        return meta.Session.query(cls).filter(
            cls.portal_id == portal_id
        ).order_by(cls.display_order.asc(), cls.created_at.desc()).all()

    @classmethod
    def get_active_by_portal(cls, portal_id):
        """Return only non-archived cards for a portal (public view)."""
        return meta.Session.query(cls).filter(
            cls.portal_id == portal_id,
            cls.is_archived == False  # noqa: E712
        ).order_by(cls.display_order.asc(), cls.created_at.desc()).all()

    def as_dict(self):
        return {
            'id': self.id,
            'portal_id': self.portal_id,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'link': self.link,
            'display_order': self.display_order,
            'is_coming_soon': self.is_coming_soon,
            'is_archived': self.is_archived,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def init_portal_cards_db():
    """Create the portal_card table if it doesn't exist."""
    if portal_card_table is None:
        define_portal_card_table()

    from sqlalchemy import inspect as sa_inspect, text as sa_text
    inspector = sa_inspect(meta.engine)
    if 'portal_card' not in inspector.get_table_names():
        portal_card_table.create(meta.engine)
        log.info(u'portal_card table created')
        _seed_default_portal_cards()
    else:
        columns = {col['name'] for col in inspector.get_columns('portal_card')}
        if 'is_archived' not in columns:
            with meta.engine.connect() as conn:
                conn.execute(sa_text(
                    'ALTER TABLE portal_card ADD COLUMN is_archived BOOLEAN DEFAULT FALSE'
                ))
            log.info(u'portal_card: added is_archived column')
        # Fix relative image paths stored in existing rows
        with meta.engine.connect() as conn:
            conn.execute(sa_text(
                "UPDATE portal_card SET image_url = REPLACE(image_url, './Landing_page/', '/Landing_page/') "
                "WHERE image_url LIKE '%./Landing_page/%'"
            ))
        # Re-seed if the table exists but is empty (e.g. created before
        # seeding logic was added, or cards were accidentally purged).
        count = meta.Session.execute(
            sa_text('SELECT count(*) FROM portal_card')
        ).scalar()
        if count == 0:
            log.info(u'portal_card table is empty – seeding defaults')
            _seed_default_portal_cards()
        else:
            log.debug(u'portal_card table already exists with %d cards', count)


def _seed_default_portal_cards():
    """Populate the portal_card table with the original hardcoded cards."""
    defaults = _get_default_portal_cards()
    for card_data in defaults:
        card = PortalCard(
            portal_id=card_data['portal_id'],
            title=card_data['title'],
            link=card_data['link'],
            description=card_data.get('description', u''),
            image_url=card_data.get('image_url', u''),
            display_order=card_data.get('display_order', 0),
            is_coming_soon=card_data.get('is_coming_soon', False),
        )
        meta.Session.add(card)
    meta.Session.commit()
    log.info(u'portal_card table seeded with %d default cards', len(defaults))


def _get_default_portal_cards():
    """Return the list of default portal cards matching the original templates."""
    return [
        # ── Flood & Drought Portal (11 cards) ────────────────────────────
        {
            'portal_id': 'flood_drought',
            'title': 'African Flood and Drought Monitor',
            'description': 'Continental monitoring system for flood and drought conditions across Africa.',
            'image_url': '/Landing_page/Content/african_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/afdm/',
            'display_order': 0,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Botswana Flood and Drought Monitor',
            'description': "National monitoring system for Botswana's flood and drought conditions.",
            'image_url': '/Landing_page/Content/botswana_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/bot_app/',
            'display_order': 1,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Busi-Pungwe-Save (BuPuSa) Flood and Drought Monitor',
            'description': "Regional monitoring system for the Busi-Pungwe-Save river basins' flood and drought conditions.",
            'image_url': '/Landing_page/Content/bupusa_flood_and_drought_monitor.jpg',
            'link': 'https://hydrology.soton.ac.uk/apps/bupusa_app',
            'display_order': 2,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Madagascar Flood and Drought Monitor',
            'description': "National monitoring system for Madagascar's flood and drought conditions.",
            'image_url': '/Landing_page/Content/madagascar_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/mdg_app/',
            'display_order': 3,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Malawi Flood and Drought Monitor',
            'description': "National monitoring system for Malawi's flood and drought conditions.",
            'image_url': '/Landing_page/Content/malawi_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/mal_app/',
            'display_order': 4,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Morocco Flood and Drought Monitor',
            'description': "National monitoring system for Morocco's flood and drought conditions.",
            'image_url': '/Landing_page/Content/morocco_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/mor_app/',
            'display_order': 5,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Mozambique Flood and Drought Monitor',
            'description': "National monitoring system for Mozambique's flood and drought conditions.",
            'image_url': '/Landing_page/Content/mozambique_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/moz_app/',
            'display_order': 6,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Namibia Flood and Drought Monitor',
            'description': "National monitoring system for Namibia's flood and drought conditions.",
            'image_url': '/Landing_page/Content/namibia_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/nam_app/',
            'display_order': 7,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'South Africa Flood and Drought Monitor',
            'description': "National monitoring system for South Africa's flood and drought conditions.",
            'image_url': '/Landing_page/Content/south_africa_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/saf_app/',
            'display_order': 8,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Zambia Flood and Drought Monitor',
            'description': "National monitoring system for Zambia's flood and drought conditions.",
            'image_url': '/Landing_page/Content/zambia_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/zam_app/',
            'display_order': 9,
        },
        {
            'portal_id': 'flood_drought',
            'title': 'Zimbabwe Flood and Drought Monitor',
            'description': 'Access comprehensive flood and drought monitoring data for Zimbabwe.',
            'image_url': '/Landing_page/Content/zimbabwe_flood_and_drought_monitor.avif',
            'link': 'https://hydrology.soton.ac.uk/apps/zim_app/',
            'display_order': 10,
        },
        # ── IoT Portal (3 cards) ─────────────────────────────────────────
        {
            'portal_id': 'iot',
            'title': 'UNESCO Global Internet of Things Portal',
            'description': 'Access comprehensive IoT data and monitoring systems for water resource management globally.',
            'image_url': '/Landing_page/Content/unesco_global_iot.png',
            'link': '#',
            'display_order': 0,
            'is_coming_soon': True,
        },
        {
            'portal_id': 'iot',
            'title': 'Be-Resilient Southern African Biosphere Reserves Portal',
            'description': 'Monitoring and early warning systems for Southern African biosphere reserves.',
            'image_url': '/Landing_page/Content/be_resilient_southern_africa.png',
            'link': 'https://tb.ihp-wins.unesco.org/dashboard/4922c770-13c0-11f0-8913-cf831348fa91?publicId=260967b0-4e9c-11ef-b517-e7921ca0fba9',
            'display_order': 1,
        },
        {
            'portal_id': 'iot',
            'title': 'Be-Resilient BuPuSa Portal (Mozambique and Zimbabwe)',
            'description': 'Regional monitoring portal for Mozambique and Zimbabwe water systems.',
            'image_url': '/Landing_page/Content/be_resilient_bupusa.png',
            'link': '#',
            'display_order': 2,
            'is_coming_soon': True,
        },
        # ── Citizen Science Portal (2 cards) ─────────────────────────────
        {
            'portal_id': 'citizen_science',
            'title': 'Citizens4Water platform',
            'description': 'Centralized digital database with citizen scientist initiatives for water management around the world.',
            'image_url': '/Landing_page/Content/Citizen4Water_platform.png',
            'link': '/citizens4water/',
            'display_order': 0,
        },
        {
            'portal_id': 'citizen_science',
            'title': 'Citizen Science toolbox',
            'description': 'Mobile application and data portal for citizen science data collection and open access data visualization.',
            'image_url': '/Landing_page/Content/Citizen_Science_toolbox.png',
            'link': 'https://cs.ihp-wins.unesco.org/',
            'display_order': 1,
        },
    ]


def define_portal_card_table():
    global portal_card_table

    portal_card_table = Table(
        'portal_card',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('portal_id', UnicodeText, nullable=False),
        Column('title', UnicodeText, nullable=False),
        Column('description', UnicodeText, default=u''),
        Column('image_url', UnicodeText, default=u''),
        Column('link', UnicodeText, nullable=False),
        Column('display_order', Integer, default=0),
        Column('is_coming_soon', Boolean, default=False),
        Column('is_archived', Boolean, default=False),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(PortalCard, portal_card_table)
    except AttributeError:
        meta.mapper(PortalCard, portal_card_table)


# ── IHP-IX Content Model ────────────────────────────────────────────────────

ihpix_content_table = None

VALID_IHPIX_SECTION_TYPES = ('cta_card', 'priority_area', 'hero', 'section_header')

VALID_IHPIX_SECTION_KEYS = (
    'cta_1', 'cta_2', 'cta_3',
    'pa_1', 'pa_2', 'pa_3', 'pa_4', 'pa_5',
    'hero',
    'section_pa', 'section_metrics', 'section_cta',
)


class IhpixContent(model.DomainObject):
    """Editable content section for the IHP-IX page."""

    def __init__(self, section_type, section_key, title=u'',
                 description=u'', image_url=u'', link=u'',
                 badge_text=u'', display_order=0, is_active=True,
                 extra_fields=u''):
        self.id = str(uuid.uuid4())
        self.section_type = section_type
        self.section_key = section_key
        self.title = title
        self.description = description
        self.image_url = image_url
        self.link = link
        self.badge_text = badge_text
        self.display_order = display_order
        self.is_active = is_active
        self.extra_fields = extra_fields
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_by_key(cls, section_key):
        return meta.Session.query(cls).filter(
            cls.section_key == section_key
        ).first()

    @classmethod
    def get_by_type(cls, section_type):
        return meta.Session.query(cls).filter(
            cls.section_type == section_type
        ).order_by(cls.display_order.asc()).all()

    @classmethod
    def get_all(cls):
        return meta.Session.query(cls).order_by(
            cls.section_type.asc(), cls.display_order.asc()
        ).all()

    def as_dict(self):
        return {
            'id': self.id,
            'section_type': self.section_type,
            'section_key': self.section_key,
            'title': self.title,
            'description': self.description,
            'image_url': self.image_url,
            'link': self.link,
            'badge_text': self.badge_text,
            'display_order': self.display_order,
            'is_active': self.is_active,
            'extra_fields': self.extra_fields,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def define_ihpix_content_table():
    global ihpix_content_table

    ihpix_content_table = Table(
        'ihpix_content',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('section_type', UnicodeText, nullable=False),
        Column('section_key', UnicodeText, nullable=False, unique=True),
        Column('title', UnicodeText, default=u''),
        Column('description', UnicodeText, default=u''),
        Column('image_url', UnicodeText, default=u''),
        Column('link', UnicodeText, default=u''),
        Column('badge_text', UnicodeText, default=u''),
        Column('display_order', Integer, default=0),
        Column('is_active', Boolean, default=True),
        Column('extra_fields', UnicodeText, default=u''),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(IhpixContent, ihpix_content_table)
    except AttributeError:
        meta.mapper(IhpixContent, ihpix_content_table)


def init_ihpix_content_db():
    """Create the ihpix_content table if it doesn't exist."""
    if ihpix_content_table is None:
        define_ihpix_content_table()

    from sqlalchemy import inspect as sa_inspect, text as sa_text
    inspector = sa_inspect(meta.engine)
    if 'ihpix_content' not in inspector.get_table_names():
        ihpix_content_table.create(meta.engine)
        log.info(u'ihpix_content table created')
        _seed_default_ihpix_content()
    else:
        count = meta.Session.execute(
            sa_text('SELECT count(*) FROM ihpix_content')
        ).scalar()
        if count == 0:
            log.info(u'ihpix_content table is empty – seeding defaults')
            _seed_default_ihpix_content()
        else:
            log.debug(u'ihpix_content table already exists with %d rows', count)
            _ensure_new_ihpix_sections()


def _seed_default_ihpix_content():
    """Populate ihpix_content with the content currently hardcoded in templates."""
    defaults = _get_default_ihpix_content()
    for item in defaults:
        content = IhpixContent(
            section_type=item['section_type'],
            section_key=item['section_key'],
            title=item.get('title', u''),
            description=item.get('description', u''),
            image_url=item.get('image_url', u''),
            link=item.get('link', u''),
            badge_text=item.get('badge_text', u''),
            display_order=item.get('display_order', 0),
            is_active=item.get('is_active', True),
            extra_fields=item.get('extra_fields', u''),
        )
        meta.Session.add(content)
    meta.Session.commit()
    log.info(u'ihpix_content table seeded with %d default sections', len(defaults))


def _ensure_new_ihpix_sections():
    """Agrega secciones nuevas (hero, section_headers) si no existen en DB.

    Necesario para instancias que ya tenían ihpix_content con solo
    cta_card y priority_area.
    """
    new_keys = ('hero', 'section_pa', 'section_metrics', 'section_cta')
    defaults = {d['section_key']: d for d in _get_default_ihpix_content()
                if d['section_key'] in new_keys}
    added = 0
    for key, item in defaults.items():
        existing = IhpixContent.get_by_key(key)
        if existing is None:
            content = IhpixContent(
                section_type=item['section_type'],
                section_key=item['section_key'],
                title=item.get('title', u''),
                description=item.get('description', u''),
                image_url=item.get('image_url', u''),
                link=item.get('link', u''),
                badge_text=item.get('badge_text', u''),
                display_order=item.get('display_order', 0),
                is_active=item.get('is_active', True),
                extra_fields=item.get('extra_fields', u''),
            )
            meta.Session.add(content)
            added += 1
    if added:
        meta.Session.commit()
        log.info(u'ihpix_content: added %d new sections (hero/headers)', added)


def _get_default_ihpix_content():
    """Return the default IHP-IX page content matching the original templates."""
    return [
        # ── CTA Cards (3) ────────────────────────────────────────────────
        {
            'section_type': 'cta_card',
            'section_key': 'cta_1',
            'title': 'IHP IX Reporting',
            'description': 'Submit your reports and view progress on IHP IX implementation.',
            'image_url': '/Landing_page/Content/ihpix_1.png',
            'link': 'https://forms.office.com/Pages/ResponsePage.aspx?Host=Teams&lang={locale}&groupId={groupId}&tid={tid}&teamsTheme={theme}&upn={upn}&id=Uq5PHbM5-kuwswIpVrERlPV3XlCBEXFBjwvcm5ZTrWNUNlYxQTFQRUgxUjBSNUJNMUlJVTBBTDFBQSQlQCN0PWcu',
            'badge_text': 'Members Only',
            'display_order': 0,
        },
        {
            'section_type': 'cta_card',
            'section_key': 'cta_2',
            'title': 'IHP IX Implementation Progress',
            'description': 'Track implementation progress and view results across priority areas.',
            'image_url': '/Landing_page/Content/ihpix_2.png',
            'link': 'https://unesco.sharepoint.com/sites/IntergovernmentalHydrologicalProgrammeIHP/SitePages/IHP-IX-Implementation-Progress.aspx?OR=Teams-HL&CT=1736211052496&clickparams=eyJBcHBOYW1lIjoiVGVhbXMtRGVza3RvcCIsIkFwcFZlcnNpb24iOiI0OS8yNDEyMDEwMDIxMSJ9',
            'badge_text': 'Members Only',
            'display_order': 1,
        },
        {
            'section_type': 'cta_card',
            'section_key': 'cta_3',
            'title': 'AI Chatbot on IHP-IX Implementation Progress',
            'description': 'Interactive AI assistant for IHP-IX information and progress queries.',
            'image_url': '/Landing_page/Content/ihpix_3.png',
            'link': '#',
            'badge_text': 'Coming Soon',
            'display_order': 2,
        },
        # ── Priority Areas (5) ───────────────────────────────────────────
        {
            'section_type': 'priority_area',
            'section_key': 'pa_1',
            'title': 'Priority Area 1: Scientific Research and Innovation',
            'description': 'Advancing scientific knowledge and developing innovative approaches to understand water cycles, improve water management and address water-related challenges through interdisciplinary research.',
            'image_url': '/Landing_page/Content/area_1.png',
            'link': 'https://unesdoc.unesco.org/in/documentViewer.xhtml?v=2.1.196&id=p%3A%3Ausmarcdef_0000381318&file=/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_9aabb773-6ee5-4fd1-b6a4-6b3a55a7766a%3F_%3D381318eng.pdf&locale=en&multi=true&ark=/ark%3A/48223/pf0000381318/PDF/381318eng.pdf#page=18',
            'display_order': 0,
        },
        {
            'section_type': 'priority_area',
            'section_key': 'pa_2',
            'title': 'Priority Area 2: Water Education in the Fourth Industrial Revolution including Sustainability',
            'description': 'Developing educational approaches that integrate traditional knowledge with emerging technologies to prepare the next generation of water professionals and informed citizens.',
            'image_url': '/Landing_page/Content/priority_area_2_water_education_in_the_fourth_industrial_revolution.png',
            'link': 'https://unesdoc.unesco.org/in/documentViewer.xhtml?v=2.1.196&id=p%3A%3Ausmarcdef_0000381318&file=/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_9aabb773-6ee5-4fd1-b6a4-6b3a55a7766a%3F_%3D381318eng.pdf&locale=en&multi=true&ark=/ark%3A/48223/pf0000381318/PDF/381318eng.pdf#page=24',
            'display_order': 1,
        },
        {
            'section_type': 'priority_area',
            'section_key': 'pa_3',
            'title': 'Priority Area 3: Bridging the Data-Knowledge Gap',
            'description': 'Enhancing data accessibility, interoperability, and knowledge sharing to improve water resource management through open science principles and collaborative information systems.',
            'image_url': '/Landing_page/Content/priority_area_3.png',
            'link': 'https://unesdoc.unesco.org/in/documentViewer.xhtml?v=2.1.196&id=p%3A%3Ausmarcdef_0000381318&file=/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_9aabb773-6ee5-4fd1-b6a4-6b3a55a7766a%3F_%3D381318eng.pdf&locale=en&multi=true&ark=/ark%3A/48223/pf0000381318/PDF/381318eng.pdf#page=28',
            'display_order': 2,
        },
        {
            'section_type': 'priority_area',
            'section_key': 'pa_4',
            'title': 'Priority Area 4: Integrated Water Resources Management under Conditions of Global Change',
            'description': 'Developing holistic approaches to manage water resources considering climate change impacts, growing demands, and environmental pressures through nature-based solutions and adaptive strategies.',
            'image_url': '/Landing_page/Content/area_4.png',
            'link': 'https://unesdoc.unesco.org/in/documentViewer.xhtml?v=2.1.196&id=p%3A%3Ausmarcdef_0000381318&file=/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_9aabb773-6ee5-4fd1-b6a4-6b3a55a7766a%3F_%3D381318eng.pdf&locale=en&multi=true&ark=/ark%3A/48223/pf0000381318/PDF/381318eng.pdf#page=31',
            'display_order': 3,
        },
        {
            'section_type': 'priority_area',
            'section_key': 'pa_5',
            'title': 'Priority Area 5: Water Governance based on Science for Mitigation, Adaptation, and Resilience',
            'description': 'Strengthening water governance frameworks through scientific knowledge to build resilient societies, enhance adaptation capacities, and promote participatory decision-making processes at all levels.',
            'image_url': '/Landing_page/Content/area_5.png',
            'link': 'https://unesdoc.unesco.org/in/documentViewer.xhtml?v=2.1.196&id=p%3A%3Ausmarcdef_0000381318&file=/in/rest/annotationSVC/DownloadWatermarkedAttachment/attach_import_9aabb773-6ee5-4fd1-b6a4-6b3a55a7766a%3F_%3D381318eng.pdf&locale=en&multi=true&ark=/ark%3A/48223/pf0000381318/PDF/381318eng.pdf#page=36',
            'display_order': 4,
        },
        # ── Hero Section (1) ─────────────────────────────────────────────
        {
            'section_type': 'hero',
            'section_key': 'hero',
            'title': 'IHP-IX Strategic Plan',
            'description': 'The ninth phase of the Intergovernmental Hydrological Programme (2022-2029) — UNESCO\'s strategic framework for addressing global water challenges through science, innovation, and cooperation.',
            'display_order': 0,
        },
        # ── Section Headers (3) ──────────────────────────────────────────
        {
            'section_type': 'section_header',
            'section_key': 'section_pa',
            'title': 'Five Priority Areas',
            'display_order': 0,
        },
        {
            'section_type': 'section_header',
            'section_key': 'section_metrics',
            'title': 'Programme Impact',
            'display_order': 1,
        },
        {
            'section_type': 'section_header',
            'section_key': 'section_cta',
            'title': 'Get Involved',
            'display_order': 2,
        },
    ]


# ── IHP-IX Activity Model ───────────────────────────────────────────────────

ihpix_activity_table = None

VALID_PRIORITY_AREAS = ('PA1', 'PA2', 'PA3', 'PA4', 'PA5')


class IhpixActivity(model.DomainObject):
    """An activity reported under an IHP-IX Priority Area / Output."""

    STATUS_DRAFT = u'draft'
    STATUS_PUBLISHED = u'published'
    STATUS_PENDING = u'pending'
    STATUS_REJECTED = u'rejected'
    VALID_STATUSES = (STATUS_DRAFT, STATUS_PUBLISHED, STATUS_PENDING,
                      STATUS_REJECTED)

    def __init__(self, title, priority_area, description=u'', output=u'',
                 country=u'', institution=u'', link=u'', image_url=u'',
                 status=u'published', reported_by=u'', reported_date=None,
                 contact_name=u'', contact_email=u'',
                 start_date=None, end_date=None,
                 key_activity=u'', outcomes=u'', biennium=u'',
                 institution_type=u'', institution_type_other=u'',
                 partners=u'',
                 unesco_participation=u'', flagships=u'',
                 regions=u'', member_states=u'',
                 knowledge_product_type=u'',
                 knowledge_product_type_other=u'',
                 num_knowledge_products=0,
                 scientific_product_type=u'',
                 num_scientific_products=0,
                 training_type=u'', num_training_materials=0,
                 num_curricula=0, num_transboundary_ms=0,
                 knowledge_activity_type=u'',
                 knowledge_activity_type_other=u'',
                 stakeholders_knowledge=0,
                 stakeholders_knowledge_female=0,
                 stakeholders_knowledge_youth=0,
                 stakeholders_awareness=0,
                 stakeholders_awareness_female=0,
                 stakeholders_awareness_youth=0,
                 num_stakeholder_groups=0,
                 stakeholder_group_type=u'',
                 stakeholder_group_type_other=u'',
                 stakeholder_group_name=u'',
                 notes=u'',
                 cross_cutting_wg=u'', synergies=u'',
                 supporting_member_state=u'',
                 # Section I / V conditional gates (PDF 2026)
                 focal_point_name=u'',
                 unesco_secretariat_participation=False,
                 has_member_state_support=False,
                 has_flagship=False,
                 has_synergies=False,
                 regions_benefit=False,
                 kpi_1a_active=False, kpi_1b_active=False,
                 kpi_2_active=False, kpi_3_active=False,
                 kpi_4_active=False, kpi_5_active=False,
                 kpi_6_active=False, kpi_8_active=False,
                 additional_notes=u'',
                 original_timestamp=u'', original_id=u''):
        self.id = str(uuid.uuid4())
        self.title = title
        self.priority_area = priority_area
        self.description = description
        self.output = output
        self.country = country
        self.institution = institution
        self.link = link
        self.image_url = image_url
        self.status = status
        self.reported_by = reported_by
        self.reported_date = reported_date
        self.contact_name = contact_name
        self.contact_email = contact_email
        self.start_date = start_date
        self.end_date = end_date
        self.review_notes = u''
        self.reviewed_by = u''
        self.reviewed_at = None
        # Campos extendidos del Excel
        self.key_activity = key_activity
        self.outcomes = outcomes
        self.biennium = biennium
        self.institution_type = institution_type
        self.institution_type_other = institution_type_other
        self.partners = partners
        self.unesco_participation = unesco_participation
        self.flagships = flagships  # JSON string
        self.regions = regions  # JSON string
        self.member_states = member_states  # JSON string
        self.knowledge_product_type = knowledge_product_type
        self.knowledge_product_type_other = knowledge_product_type_other
        self.num_knowledge_products = num_knowledge_products or 0
        self.scientific_product_type = scientific_product_type
        self.num_scientific_products = num_scientific_products or 0
        self.training_type = training_type
        self.num_training_materials = num_training_materials or 0
        self.num_curricula = num_curricula or 0
        self.num_transboundary_ms = num_transboundary_ms or 0
        self.knowledge_activity_type = knowledge_activity_type
        self.knowledge_activity_type_other = knowledge_activity_type_other
        self.stakeholders_knowledge = stakeholders_knowledge or 0
        self.stakeholders_knowledge_female = stakeholders_knowledge_female or 0
        self.stakeholders_knowledge_youth = stakeholders_knowledge_youth or 0
        self.stakeholders_awareness = stakeholders_awareness or 0
        self.stakeholders_awareness_female = stakeholders_awareness_female or 0
        self.stakeholders_awareness_youth = stakeholders_awareness_youth or 0
        self.num_stakeholder_groups = num_stakeholder_groups or 0
        self.stakeholder_group_type = stakeholder_group_type
        self.stakeholder_group_type_other = stakeholder_group_type_other
        self.stakeholder_group_name = stakeholder_group_name
        self.notes = notes
        self.cross_cutting_wg = cross_cutting_wg  # JSON string
        self.synergies = synergies
        self.supporting_member_state = supporting_member_state
        # PDF 2026 conditional gates
        self.focal_point_name = focal_point_name
        self.unesco_secretariat_participation = bool(unesco_secretariat_participation)
        self.has_member_state_support = bool(has_member_state_support)
        self.has_flagship = bool(has_flagship)
        self.has_synergies = bool(has_synergies)
        self.regions_benefit = bool(regions_benefit)
        self.kpi_1a_active = bool(kpi_1a_active)
        self.kpi_1b_active = bool(kpi_1b_active)
        self.kpi_2_active = bool(kpi_2_active)
        self.kpi_3_active = bool(kpi_3_active)
        self.kpi_4_active = bool(kpi_4_active)
        self.kpi_5_active = bool(kpi_5_active)
        self.kpi_6_active = bool(kpi_6_active)
        self.kpi_8_active = bool(kpi_8_active)
        self.additional_notes = additional_notes
        self.original_timestamp = original_timestamp
        self.original_id = original_id
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_by_priority_area(cls, priority_area, status=None, limit=None):
        q = meta.Session.query(cls).filter(
            cls.priority_area == priority_area
        )
        if status:
            q = q.filter(cls.status == status)
        q = q.order_by(cls.created_at.desc())
        if limit:
            q = q.limit(limit)
        return q.all()

    @classmethod
    def get_published(cls, priority_area=None, output=None, q_text=None,
                      biennium=None, country=None, region=None, flagship=None,
                      organization=None, limit=20, offset=0):
        """Return published activities with optional filters."""
        q = meta.Session.query(cls).filter(cls.status == cls.STATUS_PUBLISHED)
        if priority_area:
            q = q.filter(cls.priority_area == priority_area)
        if output:
            q = q.filter(cls.output == output)
        if biennium:
            q = q.filter(cls.biennium == biennium)
        if country:
            country_pattern = u'%' + country + u'%'
            q = q.filter(
                (cls.country == country) |
                (cls.member_states.ilike(country_pattern)) |
                (cls.supporting_member_state == country)
            )
        if organization:
            # Búsqueda flexible: el título de la org puede diferir del nombre
            # almacenado en institution/partners. Se generan variantes para
            # maximizar coincidencias (ej: "WWF India" vs "World Wide Fund for Nature (WWF)")
            org_variants = cls._build_org_search_variants(organization)
            from sqlalchemy import or_
            org_conditions = []
            for variant in org_variants:
                pattern = u'%' + variant + u'%'
                org_conditions.extend([
                    cls.institution.ilike(pattern),
                    cls.partners.ilike(pattern),
                    cls.country.ilike(pattern),
                    cls.member_states.ilike(pattern),
                    cls.supporting_member_state.ilike(pattern),
                ])
            if org_conditions:
                q = q.filter(or_(*org_conditions))
        if region:
            q = q.filter(cls.regions.ilike(u'%' + region + u'%'))
        if flagship:
            q = q.filter(cls.flagships.ilike(u'%' + flagship + u'%'))
        if q_text:
            like = u'%' + q_text + u'%'
            q = q.filter(
                (cls.title.ilike(like)) | (cls.description.ilike(like))
            )
        total = q.count()
        results = q.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
        return results, total

    @staticmethod
    def _build_org_search_variants(org_name):
        """Genera variantes de búsqueda a partir del nombre de una organización.

        Extrae siglas entre paréntesis, palabras significativas, y normaliza
        guiones para mejorar el matching flexible contra campos de texto libre.
        Ejemplo: "World Wide Fund for Nature (WWF)" → ["World Wide Fund for Nature (WWF)",
        "World Wide Fund for Nature", "WWF", "World Wide Fund Nature"]
        """
        import re
        variants = set()
        name = org_name.strip()
        if not name:
            return []
        variants.add(name)

        # Extraer siglas entre paréntesis: "Org Name (ABC)" → "ABC"
        acronym_match = re.search(r'\(([A-Za-z0-9\-\.]+)\)', name)
        if acronym_match:
            acronym = acronym_match.group(1)
            variants.add(acronym)
            # Nombre sin la sigla entre paréntesis
            clean_name = re.sub(r'\s*\([A-Za-z0-9\-\.]+\)\s*', ' ', name).strip()
            if clean_name and len(clean_name) > 3:
                variants.add(clean_name)

        # Convertir slug a nombre legible: "world-wide-fund-for-nature-wwf" → "world wide fund for nature wwf"
        if '-' in name and ' ' not in name:
            readable = name.replace('-', ' ')
            variants.add(readable)
            # Extraer posible sigla al final del slug
            parts = readable.split()
            if parts and len(parts[-1]) <= 5 and parts[-1].isalpha():
                possible_acronym = parts[-1].upper()
                variants.add(possible_acronym)
                without_acronym = ' '.join(parts[:-1])
                if without_acronym and len(without_acronym) > 3:
                    variants.add(without_acronym)

        # Versión sin stopwords comunes para matching más flexible
        stopwords = {'for', 'of', 'the', 'and', 'in', 'on', 'de', 'la', 'le', 'les', 'des', 'du', 'et'}
        words = name.split()
        significant = [w for w in words if w.lower() not in stopwords and len(w) > 1]
        if len(significant) >= 2 and len(significant) < len(words):
            variants.add(' '.join(significant))

        return [v for v in variants if len(v) >= 2]

    @classmethod
    def get_all(cls, status=None, priority_area=None, limit=100, offset=0):
        """Return activities with optional filters (admin view)."""
        q = meta.Session.query(cls)
        if status:
            q = q.filter(cls.status == status)
        if priority_area:
            q = q.filter(cls.priority_area == priority_area)
        total = q.count()
        results = q.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
        return results, total

    @classmethod
    def get_pending(cls, limit=100, offset=0):
        """Return pending submissions for admin review."""
        q = meta.Session.query(cls).filter(
            cls.status.in_([cls.STATUS_PENDING, cls.STATUS_REJECTED])
        )
        total = q.count()
        results = q.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
        return results, total

    @classmethod
    def get_facets(cls):
        """Return facet counts for priority_area and output (published only)."""
        from sqlalchemy import func
        pa_facets = meta.Session.query(
            cls.priority_area, func.count(cls.id)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED
        ).group_by(cls.priority_area).all()

        output_facets = meta.Session.query(
            cls.output, func.count(cls.id)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.output != u'',
            cls.output != None  # noqa: E711
        ).group_by(cls.output).all()

        return {
            'ihpix_priority_area': {
                'title': 'ihpix_priority_area',
                'items': [{'name': pa, 'count': c, 'display_name': pa}
                          for pa, c in pa_facets],
            },
            'ihpix_output': {
                'title': 'ihpix_output',
                'items': [{'name': out, 'count': c, 'display_name': out}
                          for out, c in output_facets],
            },
        }

    @classmethod
    def get_stats(cls, filters=None):
        """Aggregated statistics for the dashboard.

        Args:
            filters (dict): Optional filters — priority_area, biennium,
                            region, country, output.
        """
        from sqlalchemy import func, distinct
        filters = filters or {}

        def _apply(q):
            """Aplica filtros comunes a una query."""
            pa = filters.get('priority_area')
            if pa:
                q = q.filter(cls.priority_area == pa)
            bi = filters.get('biennium')
            if bi:
                q = q.filter(cls.biennium == bi)
            country = filters.get('country')
            if country:
                q = q.filter(cls.country == country)
            output = filters.get('output')
            if output:
                q = q.filter(cls.output == output)
            region = filters.get('region')
            if region:
                q = q.filter(cls.regions.ilike(u'%' + region + u'%'))
            return q

        base = _apply(meta.Session.query(cls).filter(
            cls.status == cls.STATUS_PUBLISHED
        ))
        total = base.count()

        countries_q = _apply(meta.Session.query(
            func.count(distinct(cls.country))
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.country != u'',
            cls.country != None  # noqa: E711
        ))
        countries = countries_q.scalar() or 0

        institutions_q = _apply(meta.Session.query(
            func.count(distinct(cls.institution))
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.institution != u'',
            cls.institution != None  # noqa: E711
        ))
        institutions = institutions_q.scalar() or 0

        pending = meta.Session.query(cls).filter(
            cls.status == cls.STATUS_PENDING
        ).count()

        pa_q = _apply(meta.Session.query(
            cls.priority_area, func.count(cls.id)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED
        ))
        pa_counts = pa_q.group_by(cls.priority_area).all()

        output_q = _apply(meta.Session.query(
            cls.output, func.count(cls.id)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.output != u'',
            cls.output != None  # noqa: E711
        ))
        output_counts = output_q.group_by(cls.output).order_by(
            func.count(cls.id).desc()
        ).all()

        # Métricas de impacto agregadas
        def _sum(col):
            q = _apply(meta.Session.query(
                func.coalesce(func.sum(col), 0)
            ).filter(cls.status == cls.STATUS_PUBLISHED))
            return q.scalar() or 0

        stakeholders_knowledge_total = _sum(cls.stakeholders_knowledge)
        stakeholders_awareness_total = _sum(cls.stakeholders_awareness)
        knowledge_products_total = _sum(cls.num_knowledge_products)
        scientific_products_total = _sum(cls.num_scientific_products)
        training_materials_total = _sum(cls.num_training_materials)

        # Por biennium
        biennium_q = _apply(meta.Session.query(
            cls.biennium, func.count(cls.id)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.biennium != u'',
            cls.biennium != None  # noqa: E711
        ))
        biennium_counts = biennium_q.group_by(cls.biennium).order_by(
            cls.biennium
        ).all()

        # Opciones disponibles para filtros (siempre sin filtrar)
        all_bienniums = meta.Session.query(
            distinct(cls.biennium)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.biennium != u'',
            cls.biennium != None  # noqa: E711
        ).order_by(cls.biennium).all()

        all_countries = meta.Session.query(
            distinct(cls.country)
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.country != u'',
            cls.country != None  # noqa: E711
        ).order_by(cls.country).all()

        return {
            'total_activities': total,
            'total_countries': countries,
            'total_institutions': institutions,
            'pending_reports': pending,
            'by_priority_area': [
                {'name': pa, 'count': c} for pa, c in pa_counts
            ],
            'by_output': [
                {'name': out or 'Unspecified', 'count': c}
                for out, c in output_counts
            ],
            'stakeholders_knowledge': stakeholders_knowledge_total,
            'stakeholders_awareness': stakeholders_awareness_total,
            'knowledge_products': knowledge_products_total,
            'scientific_products': scientific_products_total,
            'training_materials': training_materials_total,
            'by_biennium': [
                {'name': b, 'count': c} for b, c in biennium_counts
            ],
            'filter_options': {
                'bienniums': [b[0] for b in all_bienniums],
                'countries': [c[0] for c in all_countries],
                'priority_areas': ['PA1', 'PA2', 'PA3', 'PA4', 'PA5'],
            },
        }

    @classmethod
    def get_timeline(cls, filters=None):
        """Monthly activity counts for timeline chart."""
        from sqlalchemy import func, extract
        filters = filters or {}
        q = meta.Session.query(
            extract('year', cls.created_at).label('year'),
            extract('month', cls.created_at).label('month'),
            func.count(cls.id).label('count')
        ).filter(cls.status == cls.STATUS_PUBLISHED)
        pa = filters.get('priority_area')
        if pa:
            q = q.filter(cls.priority_area == pa)
        bi = filters.get('biennium')
        if bi:
            q = q.filter(cls.biennium == bi)
        country = filters.get('country')
        if country:
            q = q.filter(cls.country == country)
        output = filters.get('output')
        if output:
            q = q.filter(cls.output == output)
        region = filters.get('region')
        if region:
            q = q.filter(cls.regions.ilike(u'%' + region + u'%'))
        q = q.group_by('year', 'month').order_by('year', 'month')
        return [
            {'year': int(r.year), 'month': int(r.month), 'count': r.count}
            for r in q.all()
        ]

    @classmethod
    def get_country_stats(cls, filters=None, limit=20):
        """Top countries by activity count."""
        from sqlalchemy import func
        filters = filters or {}
        q = meta.Session.query(
            cls.country, func.count(cls.id).label('count')
        ).filter(
            cls.status == cls.STATUS_PUBLISHED,
            cls.country != u'',
            cls.country != None  # noqa: E711
        )
        pa = filters.get('priority_area')
        if pa:
            q = q.filter(cls.priority_area == pa)
        bi = filters.get('biennium')
        if bi:
            q = q.filter(cls.biennium == bi)
        output = filters.get('output')
        if output:
            q = q.filter(cls.output == output)
        region = filters.get('region')
        if region:
            q = q.filter(cls.regions.ilike(u'%' + region + u'%'))
        q = q.group_by(cls.country).order_by(func.count(cls.id).desc())
        if limit:
            q = q.limit(limit)
        return [{'name': r.country, 'count': r.count} for r in q.all()]

    def as_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority_area': self.priority_area,
            'output': self.output,
            'country': self.country,
            'institution': self.institution,
            'link': self.link,
            'image_url': self.image_url,
            'status': self.status,
            'reported_by': self.reported_by,
            'reported_date': self.reported_date.isoformat() if self.reported_date else None,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'review_notes': self.review_notes,
            'reviewed_by': self.reviewed_by,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'key_activity': self.key_activity or u'',
            'outcomes': self.outcomes or u'',
            'biennium': self.biennium or u'',
            'institution_type': self.institution_type or u'',
            'partners': self.partners or u'',
            'unesco_participation': self.unesco_participation or u'',
            'flagships': self.flagships or u'',
            'regions': self.regions or u'',
            'member_states': self.member_states or u'',
            'knowledge_product_type': self.knowledge_product_type or u'',
            'knowledge_product_type_other': self.knowledge_product_type_other or u'',
            'num_knowledge_products': self.num_knowledge_products or 0,
            'scientific_product_type': self.scientific_product_type or u'',
            'num_scientific_products': self.num_scientific_products or 0,
            'training_type': self.training_type or u'',
            'num_training_materials': self.num_training_materials or 0,
            'num_curricula': self.num_curricula or 0,
            'num_transboundary_ms': self.num_transboundary_ms or 0,
            'knowledge_activity_type': self.knowledge_activity_type or u'',
            'knowledge_activity_type_other': self.knowledge_activity_type_other or u'',
            'stakeholders_knowledge': self.stakeholders_knowledge or 0,
            'stakeholders_knowledge_female': self.stakeholders_knowledge_female or 0,
            'stakeholders_knowledge_youth': self.stakeholders_knowledge_youth or 0,
            'stakeholders_awareness': self.stakeholders_awareness or 0,
            'stakeholders_awareness_female': self.stakeholders_awareness_female or 0,
            'stakeholders_awareness_youth': self.stakeholders_awareness_youth or 0,
            'num_stakeholder_groups': self.num_stakeholder_groups or 0,
            'stakeholder_group_type': self.stakeholder_group_type or u'',
            'notes': self.notes or u'',
            'cross_cutting_wg': self.cross_cutting_wg or u'',
            'synergies': self.synergies or u'',
            'supporting_member_state': self.supporting_member_state or u'',
            'original_timestamp': self.original_timestamp or u'',
            'original_id': self.original_id or u'',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def define_ihpix_activity_table():
    global ihpix_activity_table

    ihpix_activity_table = Table(
        'ihpix_activity',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('title', UnicodeText, nullable=False),
        Column('description', UnicodeText, default=u''),
        Column('priority_area', UnicodeText, nullable=False),
        Column('output', UnicodeText, default=u''),
        Column('country', UnicodeText, default=u''),
        Column('institution', UnicodeText, default=u''),
        Column('link', UnicodeText, default=u''),
        Column('image_url', UnicodeText, default=u''),
        Column('status', UnicodeText, default=u'published'),
        Column('reported_by', UnicodeText, default=u''),
        Column('reported_date', Date, nullable=True),
        Column('contact_name', UnicodeText, default=u''),
        Column('contact_email', UnicodeText, default=u''),
        Column('start_date', Date, nullable=True),
        Column('end_date', Date, nullable=True),
        Column('review_notes', UnicodeText, default=u''),
        Column('reviewed_by', UnicodeText, default=u''),
        Column('reviewed_at', DateTime, nullable=True),
        # Campos extendidos del Excel
        Column('key_activity', UnicodeText, default=u''),
        Column('outcomes', UnicodeText, default=u''),
        Column('biennium', UnicodeText, default=u''),
        Column('institution_type', UnicodeText, default=u''),
        Column('partners', UnicodeText, default=u''),
        Column('unesco_participation', UnicodeText, default=u''),
        Column('flagships', UnicodeText, default=u''),  # JSON
        Column('regions', UnicodeText, default=u''),  # JSON
        Column('member_states', UnicodeText, default=u''),  # JSON
        Column('knowledge_product_type', UnicodeText, default=u''),
        Column('knowledge_product_type_other', UnicodeText, default=u''),
        Column('num_knowledge_products', Integer, default=0),
        Column('scientific_product_type', UnicodeText, default=u''),
        Column('num_scientific_products', Integer, default=0),
        Column('training_type', UnicodeText, default=u''),
        Column('num_training_materials', Integer, default=0),
        Column('num_curricula', Integer, default=0),
        Column('num_transboundary_ms', Integer, default=0),
        Column('knowledge_activity_type', UnicodeText, default=u''),
        Column('knowledge_activity_type_other', UnicodeText, default=u''),
        Column('stakeholders_knowledge', Integer, default=0),
        Column('stakeholders_knowledge_female', Integer, default=0),
        Column('stakeholders_knowledge_youth', Integer, default=0),
        Column('stakeholders_awareness', Integer, default=0),
        Column('stakeholders_awareness_female', Integer, default=0),
        Column('stakeholders_awareness_youth', Integer, default=0),
        Column('num_stakeholder_groups', Integer, default=0),
        Column('stakeholder_group_type', UnicodeText, default=u''),
        Column('stakeholder_group_type_other', UnicodeText, default=u''),
        Column('stakeholder_group_name', UnicodeText, default=u''),
        Column('notes', UnicodeText, default=u''),
        Column('cross_cutting_wg', UnicodeText, default=u''),  # JSON
        Column('synergies', UnicodeText, default=u''),
        Column('supporting_member_state', UnicodeText, default=u''),
        # PDF 2026 conditional gates — Section I / V
        Column('focal_point_name', UnicodeText, default=u''),
        Column('institution_type_other', UnicodeText, default=u''),
        Column('unesco_secretariat_participation', Boolean, default=False),
        Column('has_member_state_support', Boolean, default=False),
        Column('has_flagship', Boolean, default=False),
        Column('has_synergies', Boolean, default=False),
        Column('regions_benefit', Boolean, default=False),
        Column('kpi_1a_active', Boolean, default=False),
        Column('kpi_1b_active', Boolean, default=False),
        Column('kpi_2_active', Boolean, default=False),
        Column('kpi_3_active', Boolean, default=False),
        Column('kpi_4_active', Boolean, default=False),
        Column('kpi_5_active', Boolean, default=False),
        Column('kpi_6_active', Boolean, default=False),
        Column('kpi_8_active', Boolean, default=False),
        Column('additional_notes', UnicodeText, default=u''),
        Column('original_timestamp', UnicodeText, default=u''),
        Column('original_id', UnicodeText, default=u''),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(IhpixActivity, ihpix_activity_table)
    except AttributeError:
        meta.mapper(IhpixActivity, ihpix_activity_table)


def init_ihpix_activities_db():
    """Create the ihpix_activity table if it doesn't exist, then migrate."""
    if ihpix_activity_table is None:
        define_ihpix_activity_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'ihpix_activity' not in inspector.get_table_names():
        ihpix_activity_table.create(meta.engine)
        log.info(u'ihpix_activity table created')
    else:
        _migrate_ihpix_activities(inspector)
        log.debug(u'ihpix_activity table already exists')


def _migrate_ihpix_activities(inspector):
    """Add new columns to existing ihpix_activity table if missing."""
    existing = {col['name'] for col in inspector.get_columns('ihpix_activity')}
    new_columns = [
        ('contact_name', "TEXT DEFAULT ''"),
        ('contact_email', "TEXT DEFAULT ''"),
        ('start_date', 'DATE'),
        ('end_date', 'DATE'),
        ('review_notes', "TEXT DEFAULT ''"),
        ('reviewed_by', "TEXT DEFAULT ''"),
        ('reviewed_at', 'TIMESTAMP'),
        # Campos extendidos del Excel
        ('key_activity', "TEXT DEFAULT ''"),
        ('outcomes', "TEXT DEFAULT ''"),
        ('biennium', "TEXT DEFAULT ''"),
        ('institution_type', "TEXT DEFAULT ''"),
        ('partners', "TEXT DEFAULT ''"),
        ('unesco_participation', "TEXT DEFAULT ''"),
        ('flagships', "TEXT DEFAULT ''"),
        ('regions', "TEXT DEFAULT ''"),
        ('member_states', "TEXT DEFAULT ''"),
        ('knowledge_product_type', "TEXT DEFAULT ''"),
        ('knowledge_product_type_other', "TEXT DEFAULT ''"),
        ('num_knowledge_products', 'INTEGER DEFAULT 0'),
        ('scientific_product_type', "TEXT DEFAULT ''"),
        ('num_scientific_products', 'INTEGER DEFAULT 0'),
        ('training_type', "TEXT DEFAULT ''"),
        ('num_training_materials', 'INTEGER DEFAULT 0'),
        ('num_curricula', 'INTEGER DEFAULT 0'),
        ('num_transboundary_ms', 'INTEGER DEFAULT 0'),
        ('knowledge_activity_type', "TEXT DEFAULT ''"),
        ('knowledge_activity_type_other', "TEXT DEFAULT ''"),
        ('stakeholders_knowledge', 'INTEGER DEFAULT 0'),
        ('stakeholders_knowledge_female', 'INTEGER DEFAULT 0'),
        ('stakeholders_knowledge_youth', 'INTEGER DEFAULT 0'),
        ('stakeholders_awareness', 'INTEGER DEFAULT 0'),
        ('stakeholders_awareness_female', 'INTEGER DEFAULT 0'),
        ('stakeholders_awareness_youth', 'INTEGER DEFAULT 0'),
        ('num_stakeholder_groups', 'INTEGER DEFAULT 0'),
        ('stakeholder_group_type', "TEXT DEFAULT ''"),
        ('notes', "TEXT DEFAULT ''"),
        ('cross_cutting_wg', "TEXT DEFAULT ''"),
        ('synergies', "TEXT DEFAULT ''"),
        ('supporting_member_state', "TEXT DEFAULT ''"),
        # PDF 2026 conditional gates — Section I / V
        ('focal_point_name', "TEXT DEFAULT ''"),
        ('institution_type_other', "TEXT DEFAULT ''"),
        ('stakeholder_group_type_other', "TEXT DEFAULT ''"),
        ('stakeholder_group_name', "TEXT DEFAULT ''"),
        ('unesco_secretariat_participation', 'BOOLEAN DEFAULT FALSE'),
        ('has_member_state_support', 'BOOLEAN DEFAULT FALSE'),
        ('has_flagship', 'BOOLEAN DEFAULT FALSE'),
        ('has_synergies', 'BOOLEAN DEFAULT FALSE'),
        ('regions_benefit', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_1a_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_1b_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_2_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_3_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_4_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_5_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_6_active', 'BOOLEAN DEFAULT FALSE'),
        ('kpi_8_active', 'BOOLEAN DEFAULT FALSE'),
        ('additional_notes', "TEXT DEFAULT ''"),
        ('original_timestamp', "TEXT DEFAULT ''"),
        ('original_id', "TEXT DEFAULT ''"),
    ]
    conn = meta.engine.connect()
    for col_name, col_type in new_columns:
        if col_name not in existing:
            try:
                conn.execute(
                    'ALTER TABLE ihpix_activity ADD COLUMN {} {}'.format(
                        col_name, col_type
                    )
                )
                log.info(u'ihpix_activity: added column %s', col_name)
            except Exception as e:
                log.warning(u'ihpix_activity: could not add column %s: %s',
                            col_name, e)
    try:
        conn.close()
    except Exception:
        pass


# ── IHP-IX Country Summary Model ────────────────────────────────────────────

ihpix_country_summary_table = None


class IhpixCountrySummary(model.DomainObject):
    """Aggregated country data for IHP-IX GeoJSON and dashboard."""

    def __init__(self, country, latitude=0.0, longitude=0.0, region=u'',
                 total_activities=0, pa1_count=0, pa2_count=0, pa3_count=0,
                 pa4_count=0, pa5_count=0,
                 transboundary_all=0, transboundary_pa1=0,
                 transboundary_pa2=0, transboundary_pa3=0,
                 transboundary_pa4=0, transboundary_pa5=0,
                 supporting_all=0, supporting_pa1=0, supporting_pa2=0,
                 supporting_pa3=0, supporting_pa4=0, supporting_pa5=0,
                 flagship_data=u'', pa_output_data=u''):
        self.id = str(uuid.uuid4())
        self.country = country
        self.latitude = latitude
        self.longitude = longitude
        self.region = region
        self.total_activities = total_activities
        self.pa1_count = pa1_count
        self.pa2_count = pa2_count
        self.pa3_count = pa3_count
        self.pa4_count = pa4_count
        self.pa5_count = pa5_count
        self.transboundary_all = transboundary_all
        self.transboundary_pa1 = transboundary_pa1
        self.transboundary_pa2 = transboundary_pa2
        self.transboundary_pa3 = transboundary_pa3
        self.transboundary_pa4 = transboundary_pa4
        self.transboundary_pa5 = transboundary_pa5
        self.supporting_all = supporting_all
        self.supporting_pa1 = supporting_pa1
        self.supporting_pa2 = supporting_pa2
        self.supporting_pa3 = supporting_pa3
        self.supporting_pa4 = supporting_pa4
        self.supporting_pa5 = supporting_pa5
        self.flagship_data = flagship_data  # JSON string
        self.pa_output_data = pa_output_data  # JSON string
        self.created_at = datetime.datetime.utcnow()
        self.updated_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_by_country(cls, country):
        return meta.Session.query(cls).filter(
            cls.country == country
        ).first()

    @classmethod
    def get_all(cls, region=None):
        q = meta.Session.query(cls)
        if region:
            q = q.filter(cls.region == region)
        return q.order_by(cls.total_activities.desc()).all()

    @classmethod
    def get_as_geojson(cls, region=None):
        """Return GeoJSON FeatureCollection."""
        items = cls.get_all(region=region)
        features = []
        for item in items:
            if item.latitude and item.longitude:
                features.append({
                    'type': 'Feature',
                    'geometry': {
                        'type': 'Point',
                        'coordinates': [
                            float(item.longitude),
                            float(item.latitude)
                        ]
                    },
                    'properties': item.as_dict()
                })
        return {
            'type': 'FeatureCollection',
            'features': features
        }

    @classmethod
    def delete_all(cls):
        """Eliminar todos los registros (para re-ingesta).
        No hace commit — el caller debe manejar la transacción.
        """
        meta.Session.query(cls).delete()

    def as_dict(self):
        return {
            'id': self.id,
            'country': self.country,
            'latitude': float(self.latitude) if self.latitude else 0.0,
            'longitude': float(self.longitude) if self.longitude else 0.0,
            'region': self.region or u'',
            'total_activities': self.total_activities or 0,
            'pa1_count': self.pa1_count or 0,
            'pa2_count': self.pa2_count or 0,
            'pa3_count': self.pa3_count or 0,
            'pa4_count': self.pa4_count or 0,
            'pa5_count': self.pa5_count or 0,
            'transboundary_all': self.transboundary_all or 0,
            'transboundary_pa1': self.transboundary_pa1 or 0,
            'transboundary_pa2': self.transboundary_pa2 or 0,
            'transboundary_pa3': self.transboundary_pa3 or 0,
            'transboundary_pa4': self.transboundary_pa4 or 0,
            'transboundary_pa5': self.transboundary_pa5 or 0,
            'supporting_all': self.supporting_all or 0,
            'supporting_pa1': self.supporting_pa1 or 0,
            'supporting_pa2': self.supporting_pa2 or 0,
            'supporting_pa3': self.supporting_pa3 or 0,
            'supporting_pa4': self.supporting_pa4 or 0,
            'supporting_pa5': self.supporting_pa5 or 0,
            'flagship_data': self.flagship_data or u'',
            'pa_output_data': self.pa_output_data or u'',
        }


from sqlalchemy import Float


def define_ihpix_country_summary_table():
    global ihpix_country_summary_table

    ihpix_country_summary_table = Table(
        'ihpix_country_summary',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('country', UnicodeText, nullable=False, unique=True),
        Column('latitude', Float, default=0.0),
        Column('longitude', Float, default=0.0),
        Column('region', UnicodeText, default=u''),
        Column('total_activities', Integer, default=0),
        Column('pa1_count', Integer, default=0),
        Column('pa2_count', Integer, default=0),
        Column('pa3_count', Integer, default=0),
        Column('pa4_count', Integer, default=0),
        Column('pa5_count', Integer, default=0),
        Column('transboundary_all', Integer, default=0),
        Column('transboundary_pa1', Integer, default=0),
        Column('transboundary_pa2', Integer, default=0),
        Column('transboundary_pa3', Integer, default=0),
        Column('transboundary_pa4', Integer, default=0),
        Column('transboundary_pa5', Integer, default=0),
        Column('supporting_all', Integer, default=0),
        Column('supporting_pa1', Integer, default=0),
        Column('supporting_pa2', Integer, default=0),
        Column('supporting_pa3', Integer, default=0),
        Column('supporting_pa4', Integer, default=0),
        Column('supporting_pa5', Integer, default=0),
        Column('flagship_data', UnicodeText, default=u''),  # JSON
        Column('pa_output_data', UnicodeText, default=u''),  # JSON
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(
            IhpixCountrySummary, ihpix_country_summary_table)
    except AttributeError:
        meta.mapper(IhpixCountrySummary, ihpix_country_summary_table)


def init_ihpix_country_summary_db():
    """Create the ihpix_country_summary table if it doesn't exist."""
    if ihpix_country_summary_table is None:
        define_ihpix_country_summary_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'ihpix_country_summary' not in inspector.get_table_names():
        ihpix_country_summary_table.create(meta.engine)
        log.info(u'ihpix_country_summary table created')
    else:
        log.debug(u'ihpix_country_summary table already exists')


# ── Initiative Request Model ─────────────────────────────────────────────────

initiative_request_table = None


class InitiativeRequest(model.DomainObject):
    """Solicitud de un usuario para crear una nueva iniciativa (grupo CKAN)."""

    STATUS_PENDING = u'pending'
    STATUS_APPROVED = u'approved'
    STATUS_REJECTED = u'rejected'

    def __init__(self, user_id, title, description=u'', name=u'',
                 logo_url=u''):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.title = title
        self.name = name
        self.description = description
        self.logo_url = logo_url
        self.status = self.STATUS_PENDING
        self.handled_by = None
        self.handled_at = None
        self.admin_note = u''
        self.created_group_id = None
        self.created_at = datetime.datetime.utcnow()

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_pending(cls):
        return meta.Session.query(cls).filter(
            cls.status == cls.STATUS_PENDING,
        ).order_by(cls.created_at.desc()).all()

    @classmethod
    def get_all(cls, status=None):
        q = meta.Session.query(cls)
        if status:
            q = q.filter(cls.status == status)
        return q.order_by(cls.created_at.desc()).all()

    @classmethod
    def get_pending_for_user(cls, user_id):
        return meta.Session.query(cls).filter(
            cls.user_id == user_id,
            cls.status == cls.STATUS_PENDING,
        ).first()

    @classmethod
    def count_pending(cls):
        return meta.Session.query(cls).filter(
            cls.status == cls.STATUS_PENDING,
        ).count()

    def as_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'name': self.name or u'',
            'description': self.description or u'',
            'logo_url': self.logo_url or u'',
            'status': self.status,
            'handled_by': self.handled_by,
            'handled_at': self.handled_at.isoformat() if self.handled_at else None,
            'admin_note': self.admin_note or u'',
            'created_group_id': self.created_group_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def init_initiative_requests_db():
    """Crea la tabla initiative_request si no existe."""
    if initiative_request_table is None:
        define_initiative_request_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'initiative_request' not in inspector.get_table_names():
        initiative_request_table.create(meta.engine)
        log.info(u'initiative_request table created')
    else:
        log.debug(u'initiative_request table already exists')


def define_initiative_request_table():
    global initiative_request_table

    initiative_request_table = Table(
        'initiative_request',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('user_id', UnicodeText, nullable=False),
        Column('title', UnicodeText, nullable=False),
        Column('name', UnicodeText, default=u''),
        Column('description', UnicodeText, default=u''),
        Column('logo_url', UnicodeText, default=u''),
        Column('status', UnicodeText, default=u'pending'),
        Column('handled_by', UnicodeText, nullable=True),
        Column('handled_at', DateTime, nullable=True),
        Column('admin_note', UnicodeText, default=u''),
        Column('created_group_id', UnicodeText, nullable=True),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(InitiativeRequest, initiative_request_table)
    except AttributeError:
        meta.mapper(InitiativeRequest, initiative_request_table)


# ── Open Learning Course Model ───────────────────────────────────────────────

open_learning_course_table = None

VALID_COURSE_STATUSES = (u'pending', u'approved', u'hidden')
VALID_COURSE_TYPES = (u'permanent', u'scheduled')

OPENLEARNING_COURSE_URL = u'https://openlearning.unesco.org/courses/{course_id}/about'


class OpenLearningCourse(model.DomainObject):
    """Caché curada de un curso de UNESCO Open Learning.

    Los cursos se sincronizan desde la API externa pero las decisiones de
    curación (status, tipo con override, orden) viven solo en esta tabla.
    """

    STATUS_PENDING = u'pending'
    STATUS_APPROVED = u'approved'
    STATUS_HIDDEN = u'hidden'

    TYPE_PERMANENT = u'permanent'
    TYPE_SCHEDULED = u'scheduled'

    def __init__(self, course_id, name, org=u'', short_description=u'',
                 image_url=u'', start=None, end=None, start_display=u'',
                 pacing=u'', raw_json=u'', course_type=u'permanent'):
        now = datetime.datetime.utcnow()
        self.id = str(uuid.uuid4())
        self.course_id = course_id
        self.name = name
        self.org = org
        self.short_description = short_description
        self.image_url = image_url
        self.start = start
        self.end = end
        self.start_display = start_display
        self.pacing = pacing
        self.raw_json = raw_json
        self.course_type = course_type
        self.course_type_override = False
        self.status = self.STATUS_PENDING
        self.is_available = True
        self.display_order = 0
        self.first_seen_at = now
        self.last_seen_at = now
        self.created_at = now
        self.updated_at = now

    @classmethod
    def get(cls, id):
        return meta.Session.query(cls).get(id)

    @classmethod
    def get_by_course_id(cls, course_id):
        return meta.Session.query(cls).filter(
            cls.course_id == course_id
        ).first()

    @classmethod
    def get_all(cls):
        """Todos los cursos para el panel admin (pendientes primero)."""
        from sqlalchemy import case
        status_order = case(
            {u'pending': 0, u'approved': 1, u'hidden': 2},
            value=cls.status, else_=3
        )
        return meta.Session.query(cls).order_by(
            status_order,
            cls.display_order.asc(),
            cls.first_seen_at.desc(),
        ).all()

    @classmethod
    def get_public(cls, course_type=None, limit=None):
        """Cursos aprobados y disponibles, para las vistas públicas."""
        q = meta.Session.query(cls).filter(
            cls.status == cls.STATUS_APPROVED,
            cls.is_available == True,  # noqa: E712
        )
        if course_type:
            q = q.filter(cls.course_type == course_type)
        q = q.order_by(
            cls.display_order.asc(),
            cls.start.desc().nullslast(),
            cls.first_seen_at.desc(),
        )
        if limit:
            q = q.limit(limit)
        return q.all()

    @classmethod
    def last_sync_at(cls):
        """Fecha del último sync exitoso (max last_seen_at) o None."""
        from sqlalchemy import func
        return meta.Session.query(func.max(cls.last_seen_at)).scalar()

    @classmethod
    def counts_by_status(cls):
        from sqlalchemy import func
        rows = meta.Session.query(cls.status, func.count(cls.id)).group_by(
            cls.status
        ).all()
        counts = {status: 0 for status in VALID_COURSE_STATUSES}
        counts.update({row[0]: row[1] for row in rows})
        return counts

    def as_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'name': self.name,
            'org': self.org or u'',
            'short_description': self.short_description or u'',
            'image_url': self.image_url or u'',
            'start': self.start.isoformat() if self.start else None,
            'end': self.end.isoformat() if self.end else None,
            'start_display': self.start_display or u'',
            'pacing': self.pacing or u'',
            'course_type': self.course_type,
            'course_type_override': bool(self.course_type_override),
            'status': self.status,
            'is_available': bool(self.is_available),
            'display_order': self.display_order or 0,
            'course_url': OPENLEARNING_COURSE_URL.format(course_id=self.course_id),
            'first_seen_at': self.first_seen_at.isoformat() if self.first_seen_at else None,
            'last_seen_at': self.last_seen_at.isoformat() if self.last_seen_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


def init_open_learning_courses_db():
    """Crea la tabla open_learning_course si no existe."""
    if open_learning_course_table is None:
        define_open_learning_course_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'open_learning_course' not in inspector.get_table_names():
        open_learning_course_table.create(meta.engine)
        log.info(u'open_learning_course table created')
    else:
        log.debug(u'open_learning_course table already exists')


def define_open_learning_course_table():
    global open_learning_course_table

    open_learning_course_table = Table(
        'open_learning_course',
        meta.metadata,
        Column('id', UnicodeText, primary_key=True,
               default=lambda: str(uuid.uuid4())),
        Column('course_id', UnicodeText, nullable=False, unique=True),
        Column('name', UnicodeText, nullable=False),
        Column('org', UnicodeText, default=u''),
        Column('short_description', UnicodeText, default=u''),
        Column('image_url', UnicodeText, default=u''),
        Column('start', DateTime, nullable=True),
        Column('end', DateTime, nullable=True),
        Column('start_display', UnicodeText, default=u''),
        Column('pacing', UnicodeText, default=u''),
        Column('raw_json', UnicodeText, default=u''),
        Column('course_type', UnicodeText, nullable=False, default=u'permanent'),
        Column('course_type_override', Boolean, default=False),
        Column('status', UnicodeText, nullable=False, default=u'pending'),
        Column('is_available', Boolean, default=True),
        Column('display_order', Integer, default=0),
        Column('first_seen_at', DateTime, default=datetime.datetime.utcnow),
        Column('last_seen_at', DateTime, default=datetime.datetime.utcnow),
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
        Index('idx_olc_status_available', 'status', 'is_available'),
    )

    try:
        meta.registry.map_imperatively(OpenLearningCourse, open_learning_course_table)
    except AttributeError:
        meta.mapper(OpenLearningCourse, open_learning_course_table)


# ── Conteo liviano de vistas/descargas ──────────────────────────────────────
#
# Tablas planas que alimentan los helpers de tracking del tema. Se pueblan desde
# Redis vía ``ckanext.theme_ejemplo.pageview_tracking.flush_to_db`` (CronJob).
# Los nombres y columnas coinciden con lo que ``helpers.py`` ya consulta, así la
# UI se enciende sin tocar templates ni el SQL de los helpers.

tracking_dataset_stats_table = None
tracking_resource_stats_table = None
tracking_site_totals_table = None
tracking_dataset_daily_table = None


def define_pageview_tracking_tables():
    global tracking_dataset_stats_table, tracking_resource_stats_table
    global tracking_site_totals_table, tracking_dataset_daily_table

    if tracking_dataset_stats_table is None:
        tracking_dataset_stats_table = Table(
            'tracking_dataset_stats',
            meta.metadata,
            Column('dataset_name', Text, primary_key=True),
            Column('total_views', BigInteger, nullable=False, default=0),
            Column('recent_views', BigInteger, nullable=False, default=0),
            Column('updated', DateTime, default=datetime.datetime.utcnow),
            Index('idx_tds_total_views', 'total_views'),
        )

    if tracking_resource_stats_table is None:
        tracking_resource_stats_table = Table(
            'tracking_resource_stats',
            meta.metadata,
            Column('resource_id', Text, primary_key=True),
            Column('total_downloads', BigInteger, nullable=False, default=0),
            Column('updated', DateTime, default=datetime.datetime.utcnow),
            Index('idx_trs_total_downloads', 'total_downloads'),
        )

    if tracking_site_totals_table is None:
        tracking_site_totals_table = Table(
            'tracking_site_totals',
            meta.metadata,
            Column('id', Integer, primary_key=True, autoincrement=False),
            Column('total_page_views', BigInteger, nullable=False, default=0),
            Column('total_downloads', BigInteger, nullable=False, default=0),
            Column('updated', DateTime, default=datetime.datetime.utcnow),
        )

    if tracking_dataset_daily_table is None:
        tracking_dataset_daily_table = Table(
            'tracking_dataset_daily',
            meta.metadata,
            Column('dataset_name', Text, primary_key=True),
            Column('day', Date, primary_key=True),
            Column('views', BigInteger, nullable=False, default=0),
            Index('idx_tdd_day', 'day'),
        )


def init_pageview_tracking_db():
    """Crea las tablas de conteo liviano si no existen (idempotente)."""
    define_pageview_tracking_tables()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    existing = set(inspector.get_table_names())
    for table in (tracking_dataset_stats_table, tracking_resource_stats_table,
                  tracking_site_totals_table, tracking_dataset_daily_table):
        if table.name not in existing:
            table.create(meta.engine)
            log.info(u'%s table created', table.name)
        else:
            log.debug(u'%s table already exists', table.name)
