# CKAN UNESCO Theme Extension - Complete Analysis

## Project Location
`/home/pabrojast/Proyectos/ckan-unesco-theme`

---

## 1. DIRECTORY STRUCTURE

### Main Extension Directory
```
/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/
├── __init__.py                 # Package initialization
├── plugin.py                   # Main plugin file (1006 lines)
├── controller.py               # Custom controllers (1907 lines)
├── helpers.py                  # Template helper functions (335 lines)
├── actions.py                  # Custom actions API (1108 lines)
├── auth.py                     # Authorization functions
├── model.py                    # SQLAlchemy data models
├── validators.py               # Custom validators
├── tests/                      # Test files
├── templates/                  # Jinja2 templates (103 HTML files)
├── public/                     # Static assets (CSS, JS)
├── fanstatic/                  # Fanstatic asset management
└── i18n/                       # Internationalization (French, Spanish, Arabic)
```

---

## 2. EXISTING TRACKING & ANALYTICS FUNCTIONALITY

### A. CKAN Built-in Tracking References

**Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/controller.py:1149`**
```python
data_dict = {u'id': id, u'include_tracking': True}
```
- When retrieving dataset details, the extension requests tracking data from CKAN's built-in tracking feature
- This is used in the package read (dataset view) controller

### B. Tracking Display in Templates

**File: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resource_item.html:52`**
```html
{{ h.popular('views', res.tracking_summary.total, min=10) if res.tracking_summary }}
```
- Displays popularity badges based on resource tracking_summary data
- Shows view count for each resource using the `h.popular()` helper

**File: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html:49`**
```jinja2
(_('Popular'), 'views_recent desc') if g.tracking_enabled else (false, false)
```
- Adds a "Popular" sort option in dataset search results if tracking is enabled
- Uses `g.tracking_enabled` to conditionally show the sort option
- Sorts by `views_recent` field (CKAN's tracking metric)

### C. Tracking Summary Data Structure
Resources have `tracking_summary` attribute with `total` field containing total views/downloads.

### D. Statistics Functions in Plugin

**File: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/plugin.py`**

1. **Site-wide statistics** (lines 949-965):
```python
def _get_site_statistics_uncached(self):
    stats = {}
    stats['dataset_count'] = toolkit.get_action('package_search')({}, {'rows': 1}).get('count', 0)
    stats['group_count'] = len(toolkit.get_action('group_list')({}, {}))
    stats['organization_count'] = len(toolkit.get_action('organization_list')({}, {}))
    return stats

def get_site_statistics_cached(self):
    # Returns cached site statistics
    return self._get_site_statistics_cached(cache_buster)
```

2. **Organization statistics** (in helpers.py, lines 131-163):
```python
def get_org_statistics(org_id):
    """Get aggregated statistics for an organization."""
    stats = {'datasets': 0, 'publications': 0, 'members': 0}
    # Counts datasets, publications, and members per organization
```

3. **Helper registered in plugin.py:647-672**:
```python
'theme_ejemplo_site_statistics': self.get_site_statistics_cached,
'get_org_statistics': helpers.get_org_statistics,
```

---

## 3. TEMPLATE STRUCTURE FOR DATASET PAGES

### Dataset/Package Display Templates

**Primary Dataset Read Template** (inherited from CKAN core):
- Default: `package/read.html` (set in controller.py line 1208)
- Package type override: `pkg_plugin.read_template()`

**Dataset Search/Listing Template**:
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html`
- Extends CKAN's default search template
- Features:
  - Spatial query widget (line 14)
  - Faceted search with schemingdcat facets (lines 18-28)
  - Sorting options including "Popular" by views_recent (line 49)
  - Results list using schemingdcat package_list snippet (line 32)

**Dataset Base Template**:
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/base.html`
- Provides base structure for all package-related pages

**Dataset Group Listing**:
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/group_list.html`

---

## 4. TEMPLATE STRUCTURE FOR RESOURCE PAGES

**Resource Item Snippet**:
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resource_item.html` (133 lines)
- Displays individual resource with:
  - Format icon (lines 19-44): Maps file formats to Font Awesome icons
  - Resource title and tracking views/downloads (lines 46-54)
  - Markdown description excerpt with read-more toggle (lines 56-81)
  - "Explore" dropdown menu with Preview/Download/Edit options (lines 82-128)
  - Tracking summary display: `{{ h.popular('views', res.tracking_summary.total, min=10) if res.tracking_summary }}`

**Resource List Components**:
- `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resources_list.html`
- `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resources_list_items.html`

---

## 5. PLUGIN HELPER REGISTRATION (plugin.py:647-672)

**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/plugin.py`

```python
def get_helpers(self):
    return {
        # Site & Organization Statistics
        'theme_ejemplo_site_statistics': self.get_site_statistics_cached,
        'get_org_statistics': helpers.get_org_statistics,
        'get_org_publications': helpers.get_org_publications,
        
        # Featured Content
        'get_featured_datasets': self.get_featured_datasets,
        'get_featured_datasets_filtered': self.get_featured_datasets_filtered,
        'get_featured_publications': helpers.get_featured_publications,
        'get_recently_added': self.get_recently_added,
        
        # People & Organizations
        'get_people_directory': helpers.get_people_directory,
        'get_user_profile': helpers.get_user_profile,
        'get_org_members_with_profiles': helpers.get_org_members_with_profiles,
        'get_country_list': helpers.get_country_list,
        'is_org_member': helpers.is_org_member,
        'is_org_admin': helpers.is_org_admin,
        
        # Membership Management
        'get_pending_membership_requests_count': helpers.get_pending_membership_requests_count,
        'get_user_admin_orgs': helpers.get_user_admin_orgs,
        'has_pending_membership_request': helpers.has_pending_membership_request,
        
        # Resources & Display
        'theme_ejemplo_get_paged_resources': helpers.get_paged_resources,
        'theme_ejemplo_markdown_excerpt': helpers.markdown_excerpt,
        
        # Bug Tracking
        'get_open_bug_tickets_count': helpers.get_open_bug_tickets_count,
        
        # Groups
        'get_member_states_groups_list': self.get_member_states_groups_list,
        'get_initiatives_groups_list': self.get_initiatives_groups_list,
        
        # Organization Branding
        'get_organization_image_by_name': self.get_organization_image_by_name,
    }
```

**Total: 20 registered helpers for templates**

---

## 6. JAVASCRIPT FILES (Public/Fanstatic)

**Location**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/public/`

### JavaScript Files:
1. **`theme_ejemplo_enhanced.js`** - Main theme enhancements
2. **`topmenu-responsive.js`** - Responsive top menu functionality
3. **`thematicbuilder/javascript/main.js`** - Thematic builder UI

### CSS Files:
1. **`theme_ejemplo.css`** - Main theme styles
2. **`ckan210-fixes.css`** - CKAN 2.10 compatibility fixes
3. **`css/people-orgs.css`** - People & Organizations UI styles
4. **`thematicbuilder/css/main.css`** - Thematic builder styles

**Fanstatic Directory**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/fanstatic/`
- Contains only `.gitignore` (empty asset directory)

---

## 7. HELPERS.PY FUNCTIONS (335 lines)

**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/helpers.py`

### Core Functions:

1. **`get_paged_resources(package_id, page=1, items_per_page=20, q='', format_filter='')`** (lines 10-58)
   - Paginate resources with search and format filtering
   - Returns: `{'resources': [...], 'total': int, 'formats': [...]}`

2. **`markdown_excerpt(text, length=180, killwords=False, end='...')`** (lines 60-83)
   - Render markdown to plain text excerpt
   - Uses `core_helpers.render_markdown()` and `Markup.striptags()`

3. **`get_user_profile(user_name)`** (lines 86-96)
   - Retrieve user with extended profile fields from plugin_extras

4. **`get_people_directory(q='', country='', organization='', expertise='', limit=21, offset=0)`** (lines 99-115)
   - List people with filters (search, country, organization, expertise)
   - Action: `people_list`

5. **`get_org_members_with_profiles(org_id)`** (lines 118-128)
   - Get organization members with extended profiles
   - Action: `organization_people`

6. **`get_org_statistics(org_id)`** (lines 131-163)
   - **[STATISTICS]** Get organization statistics
   - Returns: `{'datasets': int, 'publications': int, 'members': int}`
   - Uses Solr facet queries: `owner_org:{org_id}` and type filters

7. **`get_org_publications(org_id, limit=20, offset=0)`** (lines 166-181)
   - Get publications (document-type datasets) for organization
   - Uses Solr query: `fq: owner_org:{org_id} AND (type:documents OR dcat_type:*marcgt*)`

8. **`is_org_member(org_id)`** (lines 184-196)
   - Check if current user is organization member
   - Uses `member_list` action

9. **`is_org_admin(org_id)`** (lines 246-258)
   - Check if current user is organization admin
   - Checks member role == 'admin'

10. **`get_country_list()`** (lines 199-243)
    - Return list of 200+ countries for dropdowns

11. **`get_pending_membership_requests_count()`** (lines 261-273)
    - **[DB QUERY]** Get pending membership requests for current user's admin orgs
    - Action: `membership_request_count`

12. **`get_user_admin_orgs()`** (lines 276-288)
    - List organizations where current user is admin
    - Action: `organization_list_for_user` with permission='admin'

13. **`has_pending_membership_request(org_id)`** (lines 291-302)
    - **[DB QUERY]** Check if current user has pending request for org
    - Model: `MembershipRequest.get_pending_for_user_and_org()`

14. **`get_featured_publications()`** (lines 305-314)
    - **[DB QUERY]** Get featured publications for homepage
    - Model: `FeaturedPublication.get_all()`

15. **`get_open_bug_tickets_count()`** (lines 317-334)
    - **[DB QUERY]** Get open bug tickets for current user
    - Model: `BugTicket.get_all(status=STATUS_OPEN)`
    - Sysadmins see all tickets, regular users see only theirs

---

## 8. ACTIONS.PY FUNCTIONS (1108 lines)

**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/actions.py`

### Custom Action Functions:

#### User & Profile Management
1. **`user_show(context, data_dict)`** (lines 21-42)
   - Override: Exposes profile fields from `plugin_extras.theme_ejemplo`
   - Profile fields: `job_title`, `institution`, `country`, `phone`, `website`, `orcid`, `expertise_areas`, `social_links`

2. **`user_update(context, data_dict)`** (lines 45-95)
   - Override: Saves profile fields to `plugin_extras`
   - Handles expertise_areas as JSON array
   - Handles social_links from individual form fields (LinkedIn, Twitter, etc.)

3. **`people_list(context, data_dict)`** (lines 99-193)
   - **[STATISTICS]** List active users with profile info and filters
   - Filters: `q` (search), `country`, `organization`, `expertise`
   - Returns: `{'results': [...], 'count': int}`
   - DB Query: Direct SQL query to model.User

4. **`organization_people(context, data_dict)`** (lines 197-254)
   - Get organization members with profile information

#### Membership Management
5. **`membership_request_create(context, data_dict)`** (lines 255-308)
   - Create membership request from user to organization

6. **`membership_request_list(context, data_dict)`** (lines 310-354)
   - List membership requests with filtering

7. **`membership_request_process(context, data_dict)`** (lines 356-414)
   - Approve/reject membership requests

8. **`membership_request_count(context, data_dict)`** (lines 416-432)
   - Count pending requests for admin orgs

#### Featured Content Management
9. **`featured_dataset_list(context, data_dict)`** (lines 451-471)
   - List featured datasets

10. **`featured_dataset_add(context, data_dict)`** (lines 473-492)
    - Add dataset to featured list

11. **`featured_dataset_remove(context, data_dict)`** (lines 494-515)
    - Remove dataset from featured list

12. **`featured_publication_list(context, data_dict)`** (lines 517-523)
    - List featured publications

13. **`featured_publication_create(context, data_dict)`** (lines 525-546)
    - Create featured publication

14. **`featured_publication_update(context, data_dict)`** (lines 548-566)
    - Update featured publication

15. **`featured_publication_delete(context, data_dict)`** (lines 568-581)
    - Delete featured publication

16. **`featured_publication_reorder(context, data_dict)`** (lines 583-606)
    - Reorder featured publications

#### Bug Tracking
17. **`bug_ticket_create(context, data_dict)`** (lines 608-640)
    - Create bug ticket

18. **`bug_ticket_list(context, data_dict)`** (lines 642-671)
    - List bug tickets with filtering

19. **`bug_ticket_show(context, data_dict)`** (lines 673-694)
    - Get single bug ticket

20. **`bug_ticket_update(context, data_dict)`** (lines 696-739)
    - Update bug ticket

21. **`bug_ticket_api_list(context, data_dict)`** (lines 741-770)
    - API endpoint for bug tickets

#### Admin User Management
22. **`admin_user_list(context, data_dict)`** (lines 781-871)
    - **[STATISTICS]** List users with optional filters and sorting
    - Filters: `q` (search), `created`, `state`, `sort`
    - Returns user count and list

23. **`admin_user_reset_password(context, data_dict)`** (lines 873-909)
    - Reset user password

24. **`admin_user_delete(context, data_dict)`** (lines 911-943)
    - Delete user

25. **`admin_user_purge(context, data_dict)`** (lines 945-989)
    - Permanently purge user data

26. **`admin_user_reactivate(context, data_dict)`** (lines 991-1016)
    - Reactivate deleted user

27. **`admin_user_toggle_sysadmin(context, data_dict)`** (lines 1018-1061)
    - Toggle user sysadmin status

28. **`admin_user_create(context, data_dict)`** (lines 1063-1108)
    - Create new user (admin only)

**Total: 31 custom actions**

---

## 9. CONTROLLER.PY FUNCTIONS (1907 lines)

**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/controller.py`

### Main Controller Classes & Views:

#### MyLogica Class
1. **`initiatives()`** (lines 90-183)
   - Display initiatives/groups with pagination
   - Caching: Uses `get_member_states_groups()` and `get_all_groups_cached()`
   - Features: Search, sorting, 21 items per page

2. **`memberstates()`** (lines 194-286)
   - Display member states with pagination
   - Excludes 'member-states' parent from child list

3. **`redirect_to_group(name)`** (lines 185-187)
   - Redirect `/paises/<nombre>` to `/group/<nombre>`

4. **`thematicbuilder()`** (lines 288-293)
   - Display thematic builder interface

5. **`ihpix()`** (lines 295-315)
   - Display IHP-IX portal with priority areas
   - Retrieves 3 datasets per priority area (PA1-PA5)

6. **`ihpix_outputs()`** (lines 317-353)
   - List IHP-IX outputs with filters (priority area, search)
   - Pagination and faceted search

#### Package Read View (Dataset Detail Page)
**`read(id, resource_id=None, activity_id=None)`** (lines ~1130-1220)
- **Tracking enabled**: Uses `include_tracking=True` in package_show call (line 1149)
- Features:
  - Batch query for resource views (optimized, lines 1175-1197)
  - Sets `has_views` flag on each resource
  - Renders template with package dict

### Utility Functions:
- **`get_member_states_groups()`** (lines 50-75)
  - **[CACHED]** Get member-states child groups
  - Cache TTL: 5 minutes
  - Direct DB query to avoid N+1

- **`get_all_groups_cached(sort_by=None)`** (lines 77-86)
  - **[CACHED]** Get all groups with dataset count
  - Cache TTL: 5 minutes

- **`timed_lru_cache(seconds, maxsize)`** (lines 25-48)
  - Custom cache decorator with expiration TTL

---

## 10. CKAN TRACKING FEATURE INTEGRATION

### Tracking Configuration Check
**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html:49`**
```jinja2
if g.tracking_enabled else (false, false)
```
- Checks if CKAN tracking is enabled via config `ckan.tracking_enabled`

### Tracking Data Usage
1. **In Dataset Pages** (controller.py:1149):
   - `include_tracking=True` parameter in package_show() action
   - Includes tracking_summary data with total views

2. **In Resource Display** (resource_item.html:52):
   - Shows popularity badges based on `res.tracking_summary.total`
   - Only displays if `res.tracking_summary` exists

3. **In Search Results** (search.html:49):
   - "Popular" sorting option sorts by `views_recent` field
   - Conditionally shown if `g.tracking_enabled` is True

### Tracking Summary Schema
- **Field**: `tracking_summary` (object on resources and datasets)
- **Sub-field**: `total` (integer) - total views/downloads
- **Used for**: Popularity indicators, sorting, analytics display

---

## 11. DATASET LISTING TEMPLATES

### Homepage Featured Datasets
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/home/snippets/`
- Files:
  - `featureddata.html` - Featured datasets display
  - `FeaturedPublications.html` - Featured publications carousel
  - `recently_added.html` - Recently added datasets
  - `stats.html` - Site statistics box

### Search & Browse
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html`
- Features:
  - Schemingdcat spatial query widget
  - Faceted search sidebar
  - Sorting: Relevance, Name, Last Modified, Publisher, **Popular (views_recent)**
  - Package list with snippets

### Organization Datasets
- Location: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/organization/`
- Files:
  - `publications.html` - Organization publications listing
  - `people.html` - Organization members
  - `events.html` - Organization events
  - `news.html` - Organization news
  - `data_stories.html` - Organization data stories

---

## 12. MODEL.PY - DATABASE MODELS

**File**: `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/model.py`

### Defined Database Tables:

1. **`MembershipRequest`** (lines 18-73)
   - user_id, organization_id, message, status (pending/approved/rejected)
   - handled_by, handled_at, admin_note, role, created_at
   - Methods: `get()`, `get_pending_for_org()`, `get_for_org()`, `get_pending_for_user_and_org()`, `count_pending_for_orgs()`

2. **`FeaturedPublication`** (additional table)
   - Methods: `get_all()`, `as_dict()`
   - Used for homepage featured content

3. **`BugTicket`** (additional table)
   - STATUS_OPEN, STATUS_CLOSED
   - Methods: `get_all()` with status filtering
   - Tracks user_id and ticket status

---

## SUMMARY: KEY STATISTICS & TRACKING POINTS

### Statistics Collection:
- **Site-wide**: Dataset count, organization count, group count
- **Organization**: Datasets, publications, members
- **User**: Pending membership requests, bug tickets
- **Resource**: Views (tracking_summary.total)

### Caching Strategy:
- Site statistics: Configurable TTL
- Member states groups: 5 minutes
- Initiatives groups: 5 minutes
- Featured datasets: Configurable TTL
- Courses (external API): 10 minutes

### Tracking/Views References:
- ✅ `res.tracking_summary.total` - Resource views
- ✅ `views_recent` - Dataset popularity sort field
- ✅ `g.tracking_enabled` - Conditional feature flag
- ✅ `include_tracking=True` - API parameter for tracking data

### Custom Tracking Models:
- MembershipRequest (join tracking)
- BugTicket (issue tracking)
- FeaturedPublication (content curation)

---

## FILE PATHS SUMMARY

| Component | File Path |
|-----------|-----------|
| Main Plugin | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/plugin.py` |
| Helpers | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/helpers.py` |
| Actions | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/actions.py` |
| Controller | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/controller.py` |
| Models | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/model.py` |
| Dataset Search | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/search.html` |
| Resource Item | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/package/snippets/resource_item.html` |
| Site Stats | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/home/snippets/stats.html` |
| Organization | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/organization/` |
| Base Template | `/home/pabrojast/Proyectos/ckan-unesco-theme/ckanext/theme_ejemplo/templates/base.html` |

