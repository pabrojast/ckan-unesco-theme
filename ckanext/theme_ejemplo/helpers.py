from ckan.plugins import toolkit
from markupsafe import Markup
from ckan.lib import helpers as core_helpers
import ckan.model as model
import json
import logging
import time
from sqlalchemy import text

log = logging.getLogger(__name__)

# ── Tracking helpers ──────────────────────────────────────────────────

_tracking_cache = {'dataset': {}, 'resource': {}, 'totals': None, 'popular': None, 'popular_resources': None, 'expires': 0}
_TRACKING_CACHE_TTL = 300  # 5 minutes


def _rollback_session_after_helper_error():
    """Reset the shared ORM session after a helper query fails."""
    try:
        model.Session.rollback()
    except Exception as rollback_error:
        log.warning('Error rolling back session after helper failure: %s',
                    rollback_error)


def _warn_and_rollback_helper_error(message, error):
    """Log helper failures that may leave CKAN's shared ORM session aborted."""
    _rollback_session_after_helper_error()
    log.warning('%s: %s', message, error)


def _is_tracking_enabled():
    """True si hay alguna fuente de tracking activa; si no, evitamos queries.

    Soporta tanto el tracking nativo de CKAN (``ckan.tracking_enabled``) como
    el conteo liviano propio del tema (``ckanext.theme_ejemplo.pageviews_enabled``),
    que escribe en las mismas tablas que estos helpers leen.
    """
    if toolkit.asbool(toolkit.config.get('ckan.tracking_enabled', False)):
        return True
    return toolkit.asbool(
        toolkit.config.get('ckanext.theme_ejemplo.pageviews_enabled', False))


def _get_tracking_cache_ttl():
    try:
        return max(60, int(toolkit.config.get(
            'ckanext.theme_ejemplo.tracking_cache_ttl', _TRACKING_CACHE_TTL)))
    except Exception:
        return _TRACKING_CACHE_TTL


def _invalidate_tracking_cache_if_expired():
    """Invalidate cache if TTL has passed."""
    now = time.time()
    if now > _tracking_cache['expires']:
        _tracking_cache['dataset'].clear()
        _tracking_cache['resource'].clear()
        _tracking_cache['totals'] = None
        _tracking_cache['popular'] = None
        _tracking_cache['popular_resources'] = None
        _tracking_cache['expires'] = now + _get_tracking_cache_ttl()


def _ensure_materialized_views():
    """Create materialized views if they don't exist (idempotent)."""
    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            # Quick existence check
            result = conn.execute(text(
                "SELECT to_regclass('tracking_dataset_stats')"))
            if result.fetchone()[0] is not None:
                return True
    except Exception:
        pass
    return False


def get_dataset_tracking(package_name):
    """
    Get page-view tracking stats for a dataset.
    Returns dict with 'total' and 'recent' views.
    Uses materialized view for speed, falls back to tracking_raw.
    """
    if not _is_tracking_enabled():
        return {'total': 0, 'recent': 0}

    _invalidate_tracking_cache_if_expired()

    if package_name in _tracking_cache['dataset']:
        return _tracking_cache['dataset'][package_name]

    result = {'total': 0, 'recent': 0}
    try:
        engine = model.meta.engine
        if _ensure_materialized_views():
            sql = text("""
                SELECT total_views, recent_views
                FROM tracking_dataset_stats
                WHERE dataset_name = :name
            """)
            with engine.connect() as conn:
                row = conn.execute(sql, {'name': package_name}).fetchone()
                if row:
                    result = {'total': row[0] or 0, 'recent': row[1] or 0}
        else:
            sql = text("""
                SELECT count(*) AS total
                FROM tracking_raw
                WHERE tracking_type = 'page'
                  AND url LIKE :pattern
            """)
            with engine.connect() as conn:
                row = conn.execute(sql, {'pattern': f'/dataset/{package_name}%'}).fetchone()
                if row:
                    result = {'total': row[0] or 0, 'recent': 0}
    except Exception as e:
        log.warning(f"Error fetching tracking for dataset {package_name}: {e}")

    _tracking_cache['dataset'][package_name] = result
    return result


def get_resource_downloads(resource_id):
    """
    Get download count for a resource.
    Uses materialized view for speed.
    """
    if not _is_tracking_enabled():
        return {'total': 0}

    _invalidate_tracking_cache_if_expired()

    if resource_id in _tracking_cache['resource']:
        return _tracking_cache['resource'][resource_id]

    result = {'total': 0}
    try:
        engine = model.meta.engine
        if _ensure_materialized_views():
            sql = text("""
                SELECT total_downloads
                FROM tracking_resource_stats
                WHERE resource_id = :rid
            """)
        else:
            sql = text("""
                SELECT count(*) AS total_downloads
                FROM tracking_raw
                WHERE tracking_type = 'resource'
                  AND url LIKE :rid
            """)
        with engine.connect() as conn:
            if _ensure_materialized_views():
                row = conn.execute(sql, {'rid': resource_id}).fetchone()
            else:
                row = conn.execute(sql, {'rid': f'%/resource/{resource_id}/%'}).fetchone()
            if row:
                result = {'total': row[0] or 0}
    except Exception as e:
        log.warning(f"Error fetching downloads for resource {resource_id}: {e}")

    _tracking_cache['resource'][resource_id] = result
    return result


def get_tracking_totals():
    """
    Get aggregated tracking totals for the entire site.
    Uses materialized view for speed.
    """
    if not _is_tracking_enabled():
        return {'page_views': 0, 'downloads': 0}

    _invalidate_tracking_cache_if_expired()

    if _tracking_cache['totals'] is not None:
        return _tracking_cache['totals']

    result = {'page_views': 0, 'downloads': 0}
    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            check = conn.execute(text(
                "SELECT to_regclass('tracking_site_totals')")).fetchone()
            if check[0] is not None:
                row = conn.execute(text(
                    "SELECT total_page_views, total_downloads FROM tracking_site_totals"
                )).fetchone()
                if row:
                    result = {'page_views': row[0] or 0, 'downloads': row[1] or 0}
            else:
                row = conn.execute(text("""
                    SELECT
                        count(*) FILTER (WHERE tracking_type = 'page'),
                        count(*) FILTER (WHERE tracking_type = 'resource')
                    FROM tracking_raw
                    WHERE tracking_type IN ('page', 'resource')
                """)).fetchone()
                if row:
                    result = {'page_views': row[0] or 0, 'downloads': row[1] or 0}
    except Exception as e:
        log.warning(f"Error fetching tracking totals: {e}")

    _tracking_cache['totals'] = result
    return result


def get_popular_datasets(limit=5):
    """Get the most viewed datasets (from materialized view, cached)."""
    if not _is_tracking_enabled():
        return []

    _invalidate_tracking_cache_if_expired()

    if _tracking_cache['popular'] is not None:
        return _tracking_cache['popular'][:limit]

    results = []
    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            check = conn.execute(text(
                "SELECT to_regclass('tracking_dataset_stats')")).fetchone()
            if check[0] is not None:
                sql = text("""
                    SELECT s.dataset_name, s.total_views, p.title, p.id,
                           g.title AS org_title, g.name AS org_name
                    FROM tracking_dataset_stats s
                    JOIN package p ON p.name = s.dataset_name AND p.state = 'active'
                    LEFT JOIN "group" g ON p.owner_org = g.id
                    ORDER BY s.total_views DESC
                    LIMIT 10
                """)
                rows = conn.execute(sql).fetchall()
                for row in rows:
                    org = None
                    if row[4]:
                        org = {'title': row[4], 'name': row[5]}
                    results.append({
                        'name': row[0],
                        'views': row[1],
                        'title': row[2] or row[0],
                        'id': row[3],
                        'organization': org,
                    })
    except Exception as e:
        log.warning(f"Error fetching popular datasets: {e}")

    _tracking_cache['popular'] = results
    return results[:limit]


def get_popular_resources(limit=5):
    """Get the most downloaded resources (from materialized view, cached)."""
    if not _is_tracking_enabled():
        return []

    _invalidate_tracking_cache_if_expired()

    if _tracking_cache['popular_resources'] is not None:
        return _tracking_cache['popular_resources'][:limit]

    results = []
    try:
        engine = model.meta.engine
        with engine.connect() as conn:
            check = conn.execute(text(
                "SELECT to_regclass('tracking_resource_stats')")).fetchone()
            if check[0] is not None:
                sql = text("""
                    SELECT s.resource_id, s.total_downloads,
                           r.name AS resource_name, r.format,
                           p.title AS dataset_title, p.name AS dataset_name
                    FROM tracking_resource_stats s
                    JOIN resource r ON r.id::text = s.resource_id
                         AND r.state = 'active'
                    JOIN package p ON r.package_id = p.id
                         AND p.state = 'active'
                    ORDER BY s.total_downloads DESC
                    LIMIT 10
                """)
                rows = conn.execute(sql).fetchall()
                for row in rows:
                    results.append({
                        'resource_id': row[0],
                        'downloads': row[1],
                        'resource_name': row[2] or 'Unnamed resource',
                        'format': (row[3] or '').upper(),
                        'dataset_title': row[4] or row[5],
                        'dataset_name': row[5],
                    })
    except Exception as e:
        log.warning(f"Error fetching popular resources: {e}")

    _tracking_cache['popular_resources'] = results
    return results[:limit]

def get_paged_resources(package_id, page=1, items_per_page=20, q='', format_filter=''):
    """
    Get paginated resources for a package with optional search and format filter.
    """
    try:
        package = toolkit.get_action('package_show')({}, {'id': package_id})
        resources = package.get('resources', [])

        # Collect unique formats before filtering
        all_formats = sorted(set(
            (r.get('format') or '').strip()
            for r in resources
            if (r.get('format') or '').strip()
        ), key=str.lower)

        # Apply search filter
        if q:
            q_lower = q.lower()
            resources = [
                r for r in resources
                if q_lower in (r.get('name') or '').lower()
                or q_lower in (r.get('description') or '').lower()
                or q_lower in (r.get('url') or '').lower()
            ]

        # Apply format filter
        if format_filter:
            fmt_lower = format_filter.lower()
            resources = [
                r for r in resources
                if (r.get('format') or '').lower() == fmt_lower
            ]

        total = len(resources)
        start = (page - 1) * items_per_page
        end = start + items_per_page
        paged_resources = resources[start:end]

        return {
            'resources': paged_resources,
            'total': total,
            'formats': all_formats,
        }
    except toolkit.ObjectNotFound:
        return {
            'resources': [],
            'total': 0,
            'formats': [],
        }

def markdown_excerpt(text, length=180, killwords=False, end='...'):
    """
    Render markdown and return a plain-text excerpt without relying on deprecated helpers.
    """
    if not text:
        return ''

    rendered = core_helpers.render_markdown(text)
    plain_text = Markup(rendered).striptags()
    
    # Simple truncation without using Jinja2's do_truncate
    if len(plain_text) <= length:
        return plain_text
    
    if killwords:
        truncated = plain_text[:length]
    else:
        # Find the last space before the limit
        truncated = plain_text[:length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            truncated = truncated[:last_space]
    
    return truncated + end


def get_user_profile(user_name):
    """Get a user with their extended profile fields."""
    try:
        user = toolkit.get_action('user_show')(
            {'ignore_auth': True},
            {'id': user_name, 'include_plugin_extras': True}
        )
        return user
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting user profile for {}'.format(user_name), e
        )
        return None


def get_people_directory(q='', country='', organization='', expertise='', limit=21, offset=0):
    """Get people directory listing with filters."""
    try:
        return toolkit.get_action('people_list')(
            {'ignore_auth': True},
            {
                'q': q,
                'country': country,
                'organization': organization,
                'expertise': expertise,
                'limit': limit,
                'offset': offset,
            }
        )
    except Exception as e:
        _warn_and_rollback_helper_error('Error getting people directory', e)
        return {'results': [], 'count': 0}


def get_org_members_with_profiles(org_id):
    """Get organization members with their extended profiles."""
    try:
        result = toolkit.get_action('organization_people')(
            {'ignore_auth': True},
            {'id': org_id}
        )
        return result.get('members', [])
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting org members for {}'.format(org_id), e
        )
        return []


def get_org_statistics(org_id):
    """Get aggregated statistics for an organization."""
    try:
        stats = {'datasets': 0, 'publications': 0, 'members': 0}

        # Datasets count (excluye documentos para no duplicar)
        search = toolkit.get_action('package_search')(
            {},
            {'fq': f'owner_org:{org_id} -type:documents', 'rows': 0}
        )
        stats['datasets'] = search.get('count', 0)

        # Publications count (sólo el dataset_type "documents")
        pub_search = toolkit.get_action('package_search')(
            {},
            {'fq': f'owner_org:{org_id} +type:documents', 'rows': 0}
        )
        stats['publications'] = pub_search.get('count', 0)

        # Members count
        try:
            org = toolkit.get_action('organization_show')(
                {'ignore_auth': True},
                {'id': org_id, 'include_users': True}
            )
            stats['members'] = len(org.get('users', []))
        except Exception as e:
            _warn_and_rollback_helper_error(
                'Error getting organization members for {}'.format(org_id), e
            )
            stats['members'] = 0

        return stats
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting org statistics for {}'.format(org_id), e
        )
        return {'datasets': 0, 'publications': 0, 'members': 0}


def get_org_publications(org_id, limit=20, offset=0):
    """Get publications (document-type datasets) for an organization."""
    try:
        search = toolkit.get_action('package_search')(
            {},
            {
                'fq': f'owner_org:{org_id} +type:documents',
                'rows': limit,
                'start': offset,
                'sort': 'metadata_modified desc',
            }
        )
        return search
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting org publications for {}'.format(org_id), e
        )
        return {'results': [], 'count': 0}


def is_org_member(org_id):
    """Check if the current user is already a member of the given organization."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return False
        members = toolkit.get_action('member_list')(
            {'ignore_auth': True},
            {'id': org_id, 'object_type': 'user'}
        )
        return any(m[0] == current_user.id for m in members)
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error checking organization membership for {}'.format(org_id), e
        )
        return False


def get_country_list():
    """Return a list of countries for dropdowns."""
    return [
        'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola',
        'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria',
        'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados',
        'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan',
        'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei',
        'Bulgaria', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia',
        'Cameroon', 'Canada', 'Central African Republic', 'Chad', 'Chile',
        'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica',
        "Côte d'Ivoire", 'Croatia', 'Cuba', 'Cyprus', 'Czech Republic',
        'Democratic Republic of the Congo', 'Denmark', 'Djibouti', 'Dominica',
        'Dominican Republic', 'Ecuador', 'Egypt', 'El Salvador',
        'Equatorial Guinea', 'Eritrea', 'Estonia', 'Eswatini', 'Ethiopia',
        'Fiji', 'Finland', 'France', 'Gabon', 'Gambia',
        'Georgia', 'Germany', 'Ghana', 'Greece', 'Grenada',
        'Guatemala', 'Guinea', 'Guinea-Bissau', 'Guyana', 'Haiti',
        'Honduras', 'Hungary', 'Iceland', 'India', 'Indonesia',
        'Iran', 'Iraq', 'Ireland', 'Israel', 'Italy',
        'Jamaica', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya',
        'Kiribati', 'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia',
        'Lebanon', 'Lesotho', 'Liberia', 'Libya', 'Liechtenstein',
        'Lithuania', 'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia',
        'Maldives', 'Mali', 'Malta', 'Marshall Islands', 'Mauritania',
        'Mauritius', 'Mexico', 'Micronesia', 'Moldova', 'Monaco',
        'Mongolia', 'Montenegro', 'Morocco', 'Mozambique', 'Myanmar',
        'Namibia', 'Nauru', 'Nepal', 'Netherlands', 'New Zealand',
        'Nicaragua', 'Niger', 'Nigeria', 'North Korea', 'North Macedonia',
        'Norway', 'Oman', 'Pakistan', 'Palau', 'Palestine',
        'Panama', 'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines',
        'Poland', 'Portugal', 'Qatar', 'Romania', 'Russia',
        'Rwanda', 'Saint Kitts and Nevis', 'Saint Lucia',
        'Saint Vincent and the Grenadines', 'Samoa', 'San Marino',
        'Sao Tome and Principe', 'Saudi Arabia', 'Senegal', 'Serbia',
        'Seychelles', 'Sierra Leone', 'Singapore', 'Slovakia', 'Slovenia',
        'Solomon Islands', 'Somalia', 'South Africa', 'South Korea',
        'South Sudan', 'Spain', 'Sri Lanka', 'Sudan', 'Suriname',
        'Sweden', 'Switzerland', 'Syria', 'Tajikistan', 'Tanzania',
        'Thailand', 'Timor-Leste', 'Togo', 'Tonga', 'Trinidad and Tobago',
        'Tunisia', 'Turkey', 'Turkmenistan', 'Tuvalu', 'Uganda',
        'Ukraine', 'United Arab Emirates', 'United Kingdom',
        'United States of America', 'Uruguay', 'Uzbekistan', 'Vanuatu',
        'Vatican City', 'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe',
    ]


def get_member_state_title(slug):
    """Resolve a member state slug (group name) to its display title.

    Uses the cached member states list from the plugin so no extra DB query
    is needed.  Falls back to a title-cased slug when the group is not found.
    """
    if not slug:
        return ''
    try:
        ms_list = toolkit.h.get_member_states_groups_list()
        for name, title in ms_list:
            if name == slug:
                return title
    except Exception:
        pass
    # Fallback: prettify the slug
    return slug.replace('-', ' ').title()


def get_user_organizations(user_id):
    """Return the list of active organisations a user belongs to.

    Each entry is a dict with ``name``, ``title``, ``image_url`` and
    ``capacity`` (member/editor/admin).
    """
    try:
        user_obj = model.User.get(user_id)
        if not user_obj:
            return []

        # Build a map of org_id → capacity from member_list calls
        capacity_map = {}
        for g in user_obj.get_groups('organization'):
            try:
                members = toolkit.get_action('member_list')(
                    {'ignore_auth': True},
                    {'id': g.id, 'object_type': 'user'},
                )
                for uid, _otype, cap in members:
                    if uid == user_obj.id:
                        capacity_map[g.id] = cap
                        break
            except Exception as e:
                _warn_and_rollback_helper_error(
                    'Error getting organization capacity for {}'.format(g.id), e
                )

        orgs = []
        for g in user_obj.get_groups('organization'):
            orgs.append({
                'id': g.id,
                'name': g.name,
                'title': g.title or g.name,
                'image_url': g.image_url or '',
                'capacity': capacity_map.get(g.id, 'member'),
            })
        return orgs
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting organizations for user {}'.format(user_id), e
        )
        return []


def is_org_admin(org_id):
    """Check if the current user is an admin of the given organization."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return False
        members = toolkit.get_action('member_list')(
            {'ignore_auth': True},
            {'id': org_id, 'object_type': 'user'}
        )
        return any(m[0] == current_user.id and m[2] == 'admin' for m in members)
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error checking organization admin status for {}'.format(org_id), e
        )
        return False


def get_pending_membership_requests_count():
    """Get the total number of pending membership requests for orgs where current user is admin."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return 0
        result = toolkit.get_action('membership_request_count')(
            {'auth_user_obj': current_user, 'user': current_user.name},
            {}
        )
        return result.get('count', 0)
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error getting pending membership requests count', e
        )
        return 0


def get_user_admin_orgs():
    """Return list of organizations where the current user is admin."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return []
        orgs = toolkit.get_action('organization_list_for_user')(
            {'user': current_user.name},
            {'permission': 'admin'}
        )
        return orgs
    except Exception as e:
        _warn_and_rollback_helper_error('Error getting admin organizations', e)
        return []


def has_pending_membership_request(org_id):
    """Check if the current user already has a pending request for an org."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return False
        from ckanext.theme_ejemplo.model import MembershipRequest
        return MembershipRequest.get_pending_for_user_and_org(
            current_user.id, org_id
        ) is not None
    except Exception as e:
        _warn_and_rollback_helper_error(
            'Error checking pending membership request for {}'.format(org_id), e
        )
        return False


def get_featured_publications():
    """Get featured publications for the homepage."""
    try:
        from ckanext.theme_ejemplo.model import FeaturedPublication
        pubs = FeaturedPublication.get_all()
        return [p.as_dict() for p in pubs]
    except Exception as e:
        _rollback_session_after_helper_error()
        log.error(f'Error getting featured publications: {e}')
        return []


# ── Featured viewers (datos en ckanext-pages) ─────────────────────────

# Nº de visores que caben en la sección de la home (3 columnas x 2 filas).
FEATURED_VIEWERS_LIMIT = 6
_HOME_CACHE_TTL = 300
_featured_viewers_cache = {'data': None, 'expires': 0, 'limit': None}


def _get_home_cache_ttl():
    """Mismo TTL que usa el resto de secciones de la home."""
    try:
        return max(0, int(toolkit.config.get(
            'ckanext.theme_ejemplo.home_cache_ttl', _HOME_CACHE_TTL)))
    except Exception:
        return _HOME_CACHE_TTL


def featured_viewers_available():
    """True si ckanext-pages tiene el módulo de featured viewers activo.

    Hay que comprobar las dos condiciones: los helpers `get_viewer_*` de
    ckanext-pages se registran siempre que el módulo importe, incluso con el
    flag apagado, así que su presencia no sirve como test. La acción, en
    cambio, sólo se registra si el flag está encendido.
    """
    try:
        if not toolkit.asbool(toolkit.config.get(
                'ckanext.featured_viewers.enabled', False)):
            return False
        toolkit.get_action('featured_viewer_list')
    except KeyError:
        return False
    except Exception as e:
        log.warning('Could not determine featured viewers availability: %s', e)
        return False
    return True


def _get_featured_viewers_uncached(limit):
    if not featured_viewers_available():
        return []
    list_action = toolkit.get_action('featured_viewer_list')
    # Contexto anónimo explícito: `featured_viewer_list` filtra por usuario
    # internamente, así que forzamos usuario vacío para que el resultado sea
    # idéntico para todo el mundo y se pueda cachear sin riesgo de filtrar
    # borradores de un sysadmin al resto de visitantes.
    base_ctx = {'user': '', 'auth_user_obj': None, 'ignore_auth': True}
    try:
        result = list_action(dict(base_ctx), {
            'is_featured': True,
            'status': 'published',
            'sort': 'order',
            'limit': limit,
        }) or {}
        viewers = result.get('viewers') or []
        if not viewers:
            # Fallback: si nadie ha destacado nada todavía, mostrar los últimos
            # publicados en vez de dejar la sección vacía.
            result = list_action(dict(base_ctx), {
                'status': 'published',
                'sort': 'recent',
                'limit': limit,
            }) or {}
            viewers = result.get('viewers') or []
        # `sort=order` no tiene desempate y hoy todos comparten order_index=0;
        # estabilizamos aquí para que el orden no baile entre peticiones.
        viewers = sorted(viewers, key=lambda v: (v.get('order_index') or 0,
                                                 v.get('created_at') or ''))
        return viewers[:limit]
    except Exception as e:
        # A diferencia de los datasets destacados (Solr), esta acción consulta
        # Postgres: si falla deja la sesión ORM abortada y rompería el resto de
        # secciones de la home.
        _warn_and_rollback_helper_error('Error getting featured viewers', e)
        return []


def get_featured_viewers(limit=FEATURED_VIEWERS_LIMIT):
    """Visores destacados para la home, con el mismo TTL que el resto."""
    cache_ttl = _get_home_cache_ttl()
    if cache_ttl <= 0:
        return _get_featured_viewers_uncached(limit)

    now = time.time()
    if (_featured_viewers_cache['data'] is not None
            and _featured_viewers_cache['limit'] == limit
            and _featured_viewers_cache['expires'] > now):
        return _featured_viewers_cache['data']

    viewers = _get_featured_viewers_uncached(limit)
    _featured_viewers_cache['data'] = viewers
    _featured_viewers_cache['limit'] = limit
    _featured_viewers_cache['expires'] = now + cache_ttl
    return viewers


def get_open_bug_tickets_count():
    """Get count of open bug tickets for the current user (or all for sysadmin)."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return 0
        from ckanext.theme_ejemplo.model import BugTicket
        if current_user.sysadmin:
            _, total = BugTicket.get_all(status=BugTicket.STATUS_OPEN)
        else:
            _, total = BugTicket.get_all(
                status=BugTicket.STATUS_OPEN, user_id=current_user.id
            )
        return total
    except Exception as e:
        _rollback_session_after_helper_error()
        log.error(f'Error getting open bug tickets count: {e}')
        return 0


def get_pending_initiative_requests_count():
    """Cantidad de solicitudes de iniciativa pendientes (solo para sysadmins, 0 si no)."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return 0
        if not current_user.sysadmin:
            return 0
        from ckanext.theme_ejemplo.model import InitiativeRequest
        return InitiativeRequest.count_pending()
    except Exception as e:
        _rollback_session_after_helper_error()
        log.error(f'Error getting pending initiative requests count: {e}')
        return 0


def get_my_pending_initiative_request():
    """Devuelve la solicitud pendiente del usuario actual, o None."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return None
        from ckanext.theme_ejemplo.model import InitiativeRequest
        req = InitiativeRequest.get_pending_for_user(current_user.id)
        return req.as_dict() if req else None
    except Exception as e:
        _rollback_session_after_helper_error()
        log.error(f'Error getting my pending initiative request: {e}')
        return None
