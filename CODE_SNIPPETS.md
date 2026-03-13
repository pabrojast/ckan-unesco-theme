# CKAN UNESCO Theme - Key Code Snippets

## 1. TRACKING DATA IN CONTROLLER (controller.py:1140-1165)

```python
# Fetch dataset with tracking data included
context = {
    u'model': model,
    u'session': model.Session,
    u'user': current_user.name,
    u'for_view': True,
    u'auth_user_obj': current_user,
}
data_dict = {u'id': id, u'include_tracking': True}  # ← KEY LINE

try:
    pkg_dict = get_action(u'package_show')(context, data_dict)
    pkg = context[u'package']
except NotFound:
    return base.abort(404, _(u'Dataset not found or you have no permission to view it'))
```

## 2. DISPLAY RESOURCE VIEWS (resource_item.html:46-54)

```html
<li class="resource-item" data-id="{{ res.id }}">
  {% block resource_item_title %}
  <div class="resource-title-row">
    <span class="format-label" property="dc:format" data-format="{{ res.format.lower() or 'data' }}">
      {{ h.get_translated(res, 'format') }}
    </span>
    <a class="heading" href="{{ url }}" title="{{ res.name or res.description }}">
      {{ h.resource_display_name(res) }}
      {{ h.popular('views', res.tracking_summary.total, min=10) if res.tracking_summary }}
      {# ↑ Shows popularity badge if tracking data exists #}
    </a>
  </div>
  {% endblock %}
```

## 3. POPULARITY SORT IN SEARCH (search.html:43-51)

```jinja2
{% set sorting = [
  (_('Relevance'), 'score desc, metadata_modified desc'),
  (_('Name Ascending'), 'title_string asc'),
  (_('Name Descending'), 'title_string desc'),
  (_('Last Modified'), 'metadata_modified desc'),
  (_('Publicador'), 'publisher_name asc'),
  (_('Popular'), 'views_recent desc') if g.tracking_enabled else (false, false)
  {# ↑ Conditionally show "Popular" sort if tracking_enabled #}
] %}
```

## 4. ORGANIZATION STATISTICS (helpers.py:131-163)

```python
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
```

## 5. SITE STATISTICS (plugin.py:949-965)

```python
def _get_site_statistics_uncached(self):
    stats = {}
    stats['dataset_count'] = toolkit.get_action('package_search')(
        {}, {'rows': 1}
    ).get('count', 0)
    stats['group_count'] = len(toolkit.get_action('group_list')({}, {}))
    stats['organization_count'] = len(toolkit.get_action('organization_list')({}, {}))
    return stats

def _get_site_statistics_cached(self, cache_buster):
    return self._get_site_statistics_uncached()

def get_site_statistics_cached(self):
    try:
        cache_buster = toolkit.config.get(
            'ckanext.theme_ejemplo.site_stats_cache_buster', 
            str(int(time.time()))
        )
        return self._get_site_statistics_cached(cache_buster)
    except Exception:
        return self._get_site_statistics_uncached()
```

## 6. REGISTER HELPERS (plugin.py:647-672)

```python
def get_helpers(self):
    return {
        # Statistics & Analytics
        'theme_ejemplo_site_statistics': self.get_site_statistics_cached,
        'get_org_statistics': helpers.get_org_statistics,
        'get_org_publications': helpers.get_org_publications,
        
        # Featured Content
        'get_featured_datasets': self.get_featured_datasets,
        'get_featured_datasets_filtered': self.get_featured_datasets_filtered,
        'get_featured_publications': helpers.get_featured_publications,
        'get_recently_added': self.get_recently_added,
        
        # People Directory
        'get_people_directory': helpers.get_people_directory,
        'get_user_profile': helpers.get_user_profile,
        'get_org_members_with_profiles': helpers.get_org_members_with_profiles,
        
        # Resource Display
        'theme_ejemplo_get_paged_resources': helpers.get_paged_resources,
        'theme_ejemplo_markdown_excerpt': helpers.markdown_excerpt,
        
        # Other
        'get_country_list': helpers.get_country_list,
        'is_org_member': helpers.is_org_member,
        'is_org_admin': helpers.is_org_admin,
        'get_pending_membership_requests_count': helpers.get_pending_membership_requests_count,
        'get_user_admin_orgs': helpers.get_user_admin_orgs,
        'has_pending_membership_request': helpers.has_pending_membership_request,
        'get_open_bug_tickets_count': helpers.get_open_bug_tickets_count,
        'get_member_states_groups_list': self.get_member_states_groups_list,
        'get_initiatives_groups_list': self.get_initiatives_groups_list,
        'get_organization_image_by_name': self.get_organization_image_by_name,
    }
```

## 7. SITE STATISTICS DISPLAY (stats.html)

```html
{% set stats = h.theme_ejemplo_site_statistics() %}

<div class="box stats">
  <div class="inner">
    <h3>{{ _('{0} statistics').format(g.site_title) }}</h3>
    <ul>
      {% block stats_group %}
      <li>
        <a href="{{ h.url_for('dataset.search') }}">
          <strong>{{ h.SI_number_span(stats.dataset_count) }}</strong>
          {{ _('dataset') if stats.dataset_count == 1 else _('datasets') }}
        </a>
      </li>
      <li>
        <a href="{{ h.url_for(controller='organization', action='index') }}">
          <strong>{{ h.SI_number_span(stats.organization_count) }}</strong>
          {{ _('organization') if stats.organization_count == 1 else _('organizations') }}
        </a>
      </li>
      <li>
        <a href="{{ h.url_for(controller='group', action='index') }}">
          <strong>{{ h.SI_number_span(stats.group_count) }}</strong>
          {{ _('group') if stats.group_count == 1 else _('groups') }}
        </a>
      </li>
      {% endblock %}
    </ul>
  </div>
</div>
```

## 8. PEOPLE DIRECTORY WITH FILTERING (actions.py:99-193)

```python
@toolkit.side_effect_free
def people_list(context, data_dict):
    """List active users with their profile information for the people directory."""
    toolkit.check_access('user_list', context, data_dict)

    q = data_dict.get('q', '')
    organization = data_dict.get('organization', '')
    country = data_dict.get('country', '')
    expertise = data_dict.get('expertise', '')
    limit = int(data_dict.get('limit', 21))
    offset = int(data_dict.get('offset', 0))

    query = model.Session.query(model.User).filter(
        model.User.state == 'active',
        model.User.name != 'default',
        model.User.name != 'harvest',
    )

    if q:
        q_like = f'%{q}%'
        query = query.filter(
            model.User.name.ilike(q_like) |
            model.User.fullname.ilike(q_like)
        )

    users = query.order_by(model.User.fullname.asc()).all()

    results = []
    for user_obj in users:
        extras = user_obj.plugin_extras or {}
        profile = extras.get('theme_ejemplo', {})

        # Filter by country
        if country and profile.get('country', '').lower() != country.lower():
            continue

        # Filter by expertise
        if expertise:
            user_expertise = profile.get('expertise_areas', '[]')
            if isinstance(user_expertise, str):
                try:
                    user_expertise = json.loads(user_expertise)
                except (json.JSONDecodeError, TypeError):
                    user_expertise = []
            if not any(expertise.lower() in e.lower() for e in user_expertise):
                continue

        # ... build results with profile data
        results.append({...})

    total = len(results)
    results = results[offset:offset + limit]

    return {
        'results': results,
        'count': total,
    }
```

## 9. ADMIN USER MANAGEMENT (actions.py:781-871)

```python
def admin_user_list(context, data_dict):
    """List users with optional filters and sorting."""
    toolkit.check_access('user_list', context, data_dict)

    q = data_dict.get('q', '')
    created_after = data_dict.get('created_after', None)
    created_before = data_dict.get('created_before', None)
    state = data_dict.get('state', 'active')
    sort = data_dict.get('sort', 'name')
    limit = int(data_dict.get('limit', 50))
    offset = int(data_dict.get('offset', 0))

    query = model.Session.query(model.User)

    if q:
        q_like = f'%{q}%'
        query = query.filter(
            (model.User.name.ilike(q_like)) |
            (model.User.fullname.ilike(q_like)) |
            (model.User.email.ilike(q_like))
        )

    # Date range filtering, sorting logic...

    total = query.count()
    users_query = query.limit(limit).offset(offset).all()

    users = [{
        'id': u.id,
        'name': u.name,
        'fullname': u.fullname or u.name,
        'email': u.email,
        'created': u.created.isoformat() if u.created else None,
        'about': u.about,
        'state': u.state,
    } for u in users_query]

    return {
        'users': users,
        'count': total,
    }
```

## 10. RESOURCE PAGINATION (helpers.py:10-58)

```python
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
```

---

## USAGE IN TEMPLATES

### In HTML Templates:
```html
{# Display statistics #}
{% set stats = h.theme_ejemplo_site_statistics() %}
<p>{{ stats.dataset_count }} datasets</p>

{# Display resource views #}
{{ h.popular('views', res.tracking_summary.total, min=10) if res.tracking_summary }}

{# Get organization stats #}
{% set org_stats = h.get_org_statistics(org.id) %}
<p>{{ org_stats.datasets }} datasets in this organization</p>

{# Get paginated resources #}
{% set resources = h.theme_ejemplo_get_paged_resources(pkg.id, page=1) %}
{% for res in resources.resources %}
  {# ... #}
{% endfor %}
```

### In API Calls:
```python
# Get people directory
result = toolkit.get_action('people_list')(
    context={},
    data_dict={
        'q': 'water',
        'country': 'France',
        'expertise': 'hydrology',
        'limit': 20,
        'offset': 0,
    }
)

# Get organization members
members = toolkit.get_action('organization_people')(
    context={'ignore_auth': True},
    data_dict={'id': org_id}
)

# Get admin users
users = toolkit.get_action('admin_user_list')(
    context={...},
    data_dict={
        'q': 'admin',
        'sort': 'created desc',
        'limit': 50,
    }
)
```

