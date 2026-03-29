# encoding: utf-8
"""SQLAlchemy model for membership requests."""

import datetime
import uuid
import logging

from sqlalchemy import Table, Column, UnicodeText, DateTime, Integer, Boolean, Date, Text

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

VALID_IHPIX_SECTION_TYPES = ('cta_card', 'priority_area')

VALID_IHPIX_SECTION_KEYS = (
    'cta_1', 'cta_2', 'cta_3',
    'pa_1', 'pa_2', 'pa_3', 'pa_4', 'pa_5',
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
    ]


# ── IHP-IX Activity Model ───────────────────────────────────────────────────

ihpix_activity_table = None

VALID_PRIORITY_AREAS = ('PA1', 'PA2', 'PA3', 'PA4', 'PA5')


class IhpixActivity(model.DomainObject):
    """An activity reported under an IHP-IX Priority Area / Output."""

    STATUS_DRAFT = u'draft'
    STATUS_PUBLISHED = u'published'

    def __init__(self, title, priority_area, description=u'', output=u'',
                 country=u'', institution=u'', link=u'', image_url=u'',
                 status=u'published', reported_by=u'', reported_date=None):
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
                      limit=20, offset=0):
        """Return published activities with optional filters."""
        q = meta.Session.query(cls).filter(cls.status == cls.STATUS_PUBLISHED)
        if priority_area:
            q = q.filter(cls.priority_area == priority_area)
        if output:
            q = q.filter(cls.output == output)
        if q_text:
            like = u'%{}%'.format(q_text)
            q = q.filter(
                (cls.title.ilike(like)) | (cls.description.ilike(like))
            )
        total = q.count()
        results = q.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
        return results, total

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
        Column('created_at', DateTime, default=datetime.datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.datetime.utcnow),
    )

    try:
        meta.registry.map_imperatively(IhpixActivity, ihpix_activity_table)
    except AttributeError:
        meta.mapper(IhpixActivity, ihpix_activity_table)


def init_ihpix_activities_db():
    """Create the ihpix_activity table if it doesn't exist."""
    if ihpix_activity_table is None:
        define_ihpix_activity_table()

    from sqlalchemy import inspect as sa_inspect
    inspector = sa_inspect(meta.engine)
    if 'ihpix_activity' not in inspector.get_table_names():
        ihpix_activity_table.create(meta.engine)
        log.info(u'ihpix_activity table created')
    else:
        log.debug(u'ihpix_activity table already exists')
