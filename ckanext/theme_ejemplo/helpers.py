from ckan.plugins import toolkit
from markupsafe import Markup
from ckan.lib import helpers as core_helpers
import ckan.model as model
import json
import logging

log = logging.getLogger(__name__)

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
        log.warning(f"Error getting user profile for {user_name}: {e}")
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
        log.warning(f"Error getting people directory: {e}")
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
        log.warning(f"Error getting org members for {org_id}: {e}")
        return []


def get_org_statistics(org_id):
    """Get aggregated statistics for an organization."""
    try:
        stats = {'datasets': 0, 'publications': 0, 'members': 0}

        # Datasets count
        search = toolkit.get_action('package_search')(
            {},
            {'fq': f'owner_org:{org_id}', 'rows': 0}
        )
        stats['datasets'] = search.get('count', 0)

        # Publications count (documents type)
        pub_search = toolkit.get_action('package_search')(
            {},
            {'fq': f'owner_org:{org_id} AND (type:documents OR dcat_type:*marcgt*)', 'rows': 0}
        )
        stats['publications'] = pub_search.get('count', 0)

        # Members count
        try:
            org = toolkit.get_action('organization_show')(
                {'ignore_auth': True},
                {'id': org_id, 'include_users': True}
            )
            stats['members'] = len(org.get('users', []))
        except Exception:
            stats['members'] = 0

        return stats
    except Exception as e:
        log.warning(f"Error getting org statistics for {org_id}: {e}")
        return {'datasets': 0, 'publications': 0, 'members': 0}


def get_org_publications(org_id, limit=20, offset=0):
    """Get publications (document-type datasets) for an organization."""
    try:
        search = toolkit.get_action('package_search')(
            {},
            {
                'fq': f'owner_org:{org_id} AND (type:documents OR dcat_type:*marcgt*)',
                'rows': limit,
                'start': offset,
                'sort': 'metadata_modified desc',
            }
        )
        return search
    except Exception as e:
        log.warning(f"Error getting org publications for {org_id}: {e}")
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
        return False


def get_featured_publications():
    """Get featured publications for the homepage."""
    try:
        from ckanext.theme_ejemplo.model import FeaturedPublication, init_featured_publications_db
        init_featured_publications_db()
        pubs = FeaturedPublication.get_all()
        return [p.as_dict() for p in pubs]
    except Exception as e:
        log.error(f'Error getting featured publications: {e}')
        return []


def get_open_bug_tickets_count():
    """Get count of open bug tickets for the current user (or all for sysadmin)."""
    try:
        from ckan.common import current_user
        if not current_user or not current_user.is_authenticated:
            return 0
        from ckanext.theme_ejemplo.model import BugTicket, init_bug_tickets_db
        init_bug_tickets_db()
        if current_user.sysadmin:
            _, total = BugTicket.get_all(status=BugTicket.STATUS_OPEN)
        else:
            _, total = BugTicket.get_all(
                status=BugTicket.STATUS_OPEN, user_id=current_user.id
            )
        return total
    except Exception as e:
        log.error(f'Error getting open bug tickets count: {e}')
        return 0
