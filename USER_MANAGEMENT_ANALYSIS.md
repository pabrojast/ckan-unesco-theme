# CKAN UNESCO Theme - User Management Capabilities Analysis

## Executive Summary

The CKAN UNESCO theme extension (`ckanext-theme_ejemplo`) currently has **NO sysadmin user management panel**. However, it includes extensive user profile management, people directory features, and membership request workflows. Below is a comprehensive breakdown of all user-related capabilities.

---

## 1. PLUGIN.py - Interface Implementation & Route Registration

### CKAN Interfaces Implemented
- **IConfigurer** - Configuration management
- **IBlueprint** - Route registration
- **ITemplateHelpers** - Template helper functions
- **IPackageController** - Package/dataset indexing
- **ITranslation** - i18n support
- **IActions** - Custom actions
- **IAuthFunctions** - Authorization functions

### Routes Registered in `get_blueprint()` (Lines 295-595)

**User Profile Routes:**
- `GET /user/<id>/documents` → `user_documents`
- `GET /user/<id>/organizations` → `user_organizations`
- `GET /user/<id>/data-stories` → `user_data_stories`
- `GET /user/<id>/news` → `user_news`
- `GET /user/<id>/events` → `user_events`

**People Directory:**
- `GET /people` → `people_index` - Display all users with filters

**Organization Members:**
- `GET /organization/<name>/people` → `organization_people`
- `GET /organization/<name>/membership-requests` → `membership_requests` - Manage member requests
- `GET /membership-requests` → `membership_requests_overview` - Multi-org landing page

**Membership Request Flow:**
- `GET/POST /organization/<name>/request-membership` → `request_membership`

**Admin Routes (Sysadmin Only):**
- `GET /ckan-admin/featured-datasets` → `featured_datasets_admin`
- `GET /ckan-admin/featured-datasets/search` → `featured_datasets_search`
- `POST /ckan-admin/featured-datasets/add` → `featured_datasets_add`
- `POST /ckan-admin/featured-datasets/remove` → `featured_datasets_remove`
- `GET /ckan-admin/featured-publications` → `featured_publications_admin`
- `POST /ckan-admin/featured-publications/{create,update,delete,reorder,upload-image}`

**Bug Ticket System:**
- `GET /bug-tickets` → `bug_tickets_list`
- `GET/POST /bug-tickets/new` → `bug_tickets_new`
- `GET /bug-tickets/<id>` → `bug_tickets_show`
- `POST /bug-tickets/<id>/close` → `bug_tickets_close`
- `POST /bug-tickets/<id>/update-status` → `bug_tickets_update_status`

### Template Helpers Registered (Lines 598-622)

**User Profile Helpers:**
- `get_user_profile()` - Get single user with extended profile
- `get_people_directory()` - List users with filters (q, country, organization, expertise)
- `get_org_members_with_profiles()` - Get organization members with profiles
- `is_org_member()` - Check if current user is org member
- `is_org_admin()` - Check if current user is org admin
- `get_user_admin_orgs()` - List orgs where current user is admin
- `get_pending_membership_requests_count()` - Count pending requests for user's orgs
- `has_pending_membership_request()` - Check if user has pending request

**Organization Statistics:**
- `get_org_statistics()` - Stats (datasets, publications, members)
- `get_org_publications()` - Get org's publications
- `get_country_list()` - Return country list for dropdowns

**Other Helpers:**
- `get_open_bug_tickets_count()` - User/all tickets (depending on role)

### Actions Registered (Lines 626-648)

**User Management Actions:**
- `user_show` - Override CKAN's user_show to include profile extras
- `user_update` - Override CKAN's user_update to save profile fields
- `people_list` - Custom action to list users with filtering
- `organization_people` - Get organization members with profiles

**Membership Requests:**
- `membership_request_create` - User creates request
- `membership_request_list` - List requests for an org
- `membership_request_process` - Approve/reject requests
- `membership_request_count` - Count pending requests

**Featured Content (Sysadmin):**
- `featured_dataset_list/add/remove`
- `featured_publication_list/create/update/delete/reorder`

**Bug Tickets:**
- `bug_ticket_create/list/show/update/api_list`

### Auth Functions Registered (Lines 651-670)

All actions have corresponding auth functions in `auth.py` that enforce:
- **Sysadmin-only**: Featured datasets/publications
- **Org admin**: Membership request processing
- **Authenticated users**: Membership request creation, bug tickets
- **Auth checks**: All use toolkit.check_access()

---

## 2. CONTROLLER.py - View Functions (1670 lines)

### User/People Related Views

**Line 378-451: `people_index()`**
- Displays people directory with search & filters
- Supports: `q`, `country`, `organization`, `expertise`
- Calls `people_list` action with pagination (21 items/page)
- Gets organizations & countries for filter dropdowns
- Returns: `people/index.html`

**Line 453-475: `organization_people(name)`**
- Displays members of an organization
- Calls `organization_people` action
- Returns: `organization/people.html`
- Returns 404 if org not found

**Line 891-898: `_get_user_context(id)` (Helper)**
- Retrieves user object or 404
- Used by multiple user profile views

**Line 899-940: `user_documents(id)`**
- User's published documents/datasets
- Calls `package_search` with owner filter
- Paginates results (20/page)
- Returns: `user/documents.html`

**Line 942-963: `user_organizations(id)`**
- User's organization memberships
- Filters by org type
- Returns: `user/organizations.html`

**Line 965-991: `user_data_stories(id)`**
- User's data stories (pages with type='data-story')
- Returns: `user/data_stories.html`

**Line 993-1029: `user_news(id)`**
- User's news items (pages with type='water-news')
- Returns: `user/news.html`

**Line 1031-1067: `user_events(id)`**
- User's events (pages with type='water-events')
- Returns: `user/events.html`

### Membership Request Views

**Line 634-732: `request_membership(name)`**
- GET: Display request form
- POST: Submit membership request
- Auth: Check `auth_user_obj` exists
- Calls `membership_request_create` action
- Returns: `organization/request_membership.html`

**Line 734-830: `membership_requests(name)` (Org Admin View)**
- GET: List pending requests for org
- POST: Process request (approve/reject)
- Auth: Check if user is org admin
- Calls `membership_request_list` and `membership_request_process` actions
- Returns: `organization/membership_requests.html`

**Line 833-889: `membership_requests_overview()` (Multi-Org Landing)**
- GET: Show pending requests across all admin orgs
- Auth: For authenticated users
- Calls `membership_request_count` for badge
- Returns: `organization/membership_requests_overview.html`

### Admin Views (Sysadmin Only)

**Line 1225-1242: `featured_datasets_admin()`**
- GET: Display sysadmin panel for featured datasets
- Auth: Sysadmin check
- Lists all featured datasets
- Returns: `admin/featured_datasets.html`

**Line 1244-1282: `featured_datasets_search()`**
- GET: Search for datasets to feature
- Returns: `admin/featured_datasets.html` (template)

**Line 1284-1309: `featured_datasets_add()`**
- POST: Add dataset to featured
- Calls `featured_dataset_add` action

**Line 1311-1338: `featured_datasets_remove()`**
- POST: Remove dataset from featured
- Calls `featured_dataset_remove` action

**Similar for Featured Publications** (Lines 1340-1438+)

### Bug Ticket Views

**Line 1451+: `bug_tickets_list()`, `bug_tickets_new()`, `bug_tickets_show()`, `bug_tickets_close()`, `bug_tickets_update_status()`**
- Users can create, view, and close their tickets
- Sysadmins can view all and change status
- Returns: `bug_tickets/*.html`

---

## 3. ACTIONS.py - Custom Action Functions (767 lines)

### User Profile Actions

**Line 20-42: `user_show(context, data_dict)`**
- Override CKAN's core `user_show`
- Exposes profile fields from `plugin_extras['theme_ejemplo']`
- **Profile fields exposed:**
  - `job_title`, `institution`, `country`, `phone`
  - `website`, `orcid`, `expertise_areas`, `social_links`
- Returns parsed JSON for expertise_areas and social_links
- Also returns `profile` dict for convenience

**Line 45-95: `user_update(context, data_dict)`**
- Override CKAN's core `user_update`
- Extracts profile fields before calling core
- Handles expertise_areas as comma-separated or JSON
- Assembles social_links from form fields (`social_links_linkedin`, etc.)
- Saves to `plugin_extras['theme_ejemplo']`
- Uses `flag_modified()` for SQLAlchemy tracking

**Line 99-193: `people_list(context, data_dict)`**
- **Parameters:**
  - `q` - Search by name/fullname
  - `country` - Filter by country
  - `organization` - Filter by org membership
  - `expertise` - Filter by expertise area
  - `limit`, `offset` - Pagination
- **Process:**
  1. Queries CKAN model for active users
  2. Filters by country (case-insensitive)
  3. Filters by expertise (JSON list matching)
  4. Filters by organization membership
  5. Applies limit/offset
- **Returns:**
  ```python
  {
    'results': [{
      'id', 'name', 'fullname', 'image_url',
      'job_title', 'institution', 'country', 'orcid',
      'expertise_areas' (list), 'social_links' (dict),
      'organizations' (list of {name, title})
    }],
    'count': total
  }
  ```

**Line 196-247: `organization_people(context, data_dict)`**
- Gets members of an organization with profiles
- Uses `member_list` action to get user-org relationships
- Returns each member's capacity (member/editor/admin)
- Returns:
  ```python
  {
    'organization': org_dict,
    'members': [{
      'id', 'name', 'fullname', 'image_url',
      'job_title', 'institution', 'country', 'expertise_areas',
      'capacity'
    }]
  }
  ```

### Membership Request Actions

**Line 255-306: `membership_request_create(context, data_dict)`**
- User requests to join organization
- **Params:** `organization_id` (required), `message` (optional)
- **Validation:**
  - User must be authenticated
  - User cannot already be a member
  - No pending request already exists
- **Returns:** Request object with id, status='pending'
- **Stored in:** Custom `membership_request` table

**Line 310-353: `membership_request_list(context, data_dict)`**
- Lists requests for an organization
- **Params:** `organization_id`, `status` (optional)
- **Auth:** Org admin or sysadmin only
- **Returns:** Organization + list of requests with user details

**Line 356-412: `membership_request_process(context, data_dict)`**
- Approve or reject membership request
- **Params:** `id`, `action` ('approve'/'reject'), `admin_note`, `role` ('member'/'editor'/'admin')
- **Process:**
  - Sets status to APPROVED/REJECTED
  - Records handler (who processed it)
  - If approved: adds user to organization via `member_create`
- **Returns:** Updated request object

**Line 415-431: `membership_request_count(context, data_dict)`**
- Counts pending requests for user's admin orgs
- Used for badges in navigation
- **Returns:** `{'count': int}`

**Line 434-442: `_get_admin_org_ids(user_id)` (Helper)**
- Queries orgs where user has 'admin' capacity

### Featured Dataset Actions

**Line 451-470: `featured_dataset_list(context, data_dict)`**
- List all datasets with 'FeaturedDataset' tag
- **Returns:** Results + count

**Line 473-491: `featured_dataset_add(context, data_dict)`**
- Tag dataset as featured
- **Params:** `id` (dataset)
- Uses CKAN `package_patch`

**Line 494-508: `featured_dataset_remove(context, data_dict)`**
- Remove featured tag
- Uses CKAN `package_patch`

### Featured Publication Actions

**Line 516-545: `featured_publication_create(context, data_dict)`**
- Create custom publication record
- **Params:** `title`, `link`, `description`, `image_url`, `display_order`
- **Stored in:** Custom `featured_publication` table
- **Returns:** Publication object

**Line 548-565: `featured_publication_update(context, data_dict)`**
- Update publication fields
- **Params:** `id`, then any fields to update

**Line 568-600: `featured_publication_delete/reorder(context, data_dict)`**
- Delete or reorder publications
- `reorder` expects `order` param with list of IDs

### Bug Ticket Actions

**Line 608-638: `bug_ticket_create(context, data_dict)`**
- Create bug report
- **Params:** `title`, `description` (required), `url`, `image_filename`, `browser_info`, `log_snapshot`
- **Auth:** Authenticated users only
- **Stored in:** Custom `bug_ticket` table

**Line 642-669: `bug_ticket_list(context, data_dict)`**
- List tickets (users see own, sysadmins see all)
- **Params:** `status`, `limit`, `offset`
- **Auth:** Authenticated users only

**Line 673-693: `bug_ticket_show(context, data_dict)`**
- Show single ticket
- **Auth:** User who created it or sysadmin

**Line 696-737: `bug_ticket_update(context, data_dict)`**
- Update ticket status/notes
- Users can only close their own (`STATUS_RESOLVED_USER`)
- Sysadmins can set any status
- **Params:** `id`, `status`, `admin_notes`

**Line 741-767: `bug_ticket_api_list(context, data_dict)`**
- API endpoint for external AI systems
- **Params:** `status`, `limit`, `offset`
- **Auth:** Sysadmin only
- **Returns:** Tickets with image URLs

---

## 4. AUTH.py - Authorization Functions (140 lines)

### Membership Request Auth

**Line 9-13: `membership_request_create()`**
- Any authenticated user can create
- Returns `{'success': False, 'msg': 'Must be logged in'}` if not

**Line 16-35: `membership_request_list()`**
- Sysadmin: Always allowed
- Org admin: Can list for their orgs
- Others: Denied

**Line 38-54: `membership_request_process()`**
- Sysadmin: Always allowed
- Org admin: Can process for their orgs
- Others: Denied

**Line 57-61: `membership_request_count()`**
- Any authenticated user

### Featured Content Auth

**Line 66-70: `_sysadmin_only(context, data_dict)` (Helper)**
- Returns success only if `auth_user_obj.sysadmin`
- Used by featured datasets/publications

**Lines 73-104: All featured_* functions**
- Call `_sysadmin_only`

### Bug Ticket Auth

**Line 109-113: `bug_ticket_create()`**
- Any authenticated user

**Line 116-120: `bug_ticket_list()`**
- Any authenticated user

**Line 123-127: `bug_ticket_show()`**
- Any authenticated user (enforcement in action)

**Line 130-134: `bug_ticket_update()`**
- Any authenticated user (enforcement in action)

**Line 137-139: `bug_ticket_api_list()`**
- Sysadmin only

---

## 5. HELPERS.py - Template Helper Functions (335 lines)

### User Profile Helpers

**Line 86-96: `get_user_profile(user_name)`**
- Get single user with profile extras
- Action: `user_show` with `include_plugin_extras: True`
- Returns user dict or None

**Line 99-115: `get_people_directory(q='', country='', organization='', expertise='', limit=21, offset=0)`**
- Call `people_list` action
- Returns: `{'results': [], 'count': 0}`

**Line 118-128: `get_org_members_with_profiles(org_id)`**
- Call `organization_people` action
- Returns: `members` list from result

**Line 131-163: `get_org_statistics(org_id)`**
- Aggregates org statistics
- **Returns:** `{'datasets': count, 'publications': count, 'members': count}`

**Line 166-181: `get_org_publications(org_id, limit=20, offset=0)`**
- Search packages filtered by org and document type
- Used for org publications tab

### Organization/Membership Helpers

**Line 184-196: `is_org_member(org_id)`**
- Check if current user is member
- Uses `member_list` action
- Returns: Boolean

**Line 246-258: `is_org_admin(org_id)`**
- Check if current user is admin
- Checks capacity == 'admin'
- Returns: Boolean

**Line 261-273: `get_pending_membership_requests_count()`**
- Get badge count for current user
- Calls `membership_request_count` action
- Returns: Integer count

**Line 276-288: `get_user_admin_orgs()`**
- Get list of orgs where current user is admin
- Action: `organization_list_for_user` with `permission: 'admin'`
- Returns: List of org dicts

**Line 291-302: `has_pending_membership_request(org_id)`**
- Check if user already has pending request for org
- Uses MembershipRequest model directly
- Returns: Boolean

### Utilities

**Line 199-243: `get_country_list()`**
- Hardcoded list of ~195 countries
- Returns: List of strings

**Line 10-84: `get_paged_resources()`, `markdown_excerpt()`**
- Resource pagination
- Markdown text rendering

---

## 6. VALIDATORS.py - User Field Validators (89 lines)

### Profile Fields
```python
PROFILE_FIELDS = [
    'job_title', 'institution', 'country', 'phone',
    'website', 'orcid', 'expertise_areas', 'social_links',
]
```

### Validators

**Line 23-29: `user_profile_field(key, data, errors, context)`**
- Generic validator for simple string fields
- Trims whitespace
- Sets empty string as default

**Line 32-58: `user_expertise_areas(key, data, errors, context)`**
- Accepts CSV or JSON list
- Converts to JSON for storage
- Default: `'[]'`

**Line 61-89: `user_social_links(key, data, errors, context)`**
- Validates social media links
- Allowed keys: `linkedin`, `twitter`, `researchgate`, `github`, `website`
- Converts to JSON dict for storage
- Default: `'{}'`

---

## 7. MODEL.py - Custom Database Models (309 lines)

### MembershipRequest Model (Lines 18-96)

**Table:** `membership_request`

**Fields:**
- `id` (UUID, PK)
- `user_id` (text, FK to user)
- `organization_id` (text, FK to organization)
- `message` (text)
- `status` ('pending', 'approved', 'rejected')
- `handled_by` (text, user ID who processed)
- `handled_at` (datetime)
- `admin_note` (text)
- `role` ('member', 'editor', 'admin')
- `created_at` (datetime)

**Class Methods:**
- `get(id)` - Fetch by ID
- `get_pending_for_org(org_id)` - Get pending requests
- `get_for_org(org_id, status=None)` - Get requests filtered by status
- `get_pending_for_user_and_org(user_id, org_id)` - Check for existing pending
- `count_pending_for_orgs(org_ids)` - Count across multiple orgs

**Status Constants:**
- `STATUS_PENDING = 'pending'`
- `STATUS_APPROVED = 'approved'`
- `STATUS_REJECTED = 'rejected'`

### FeaturedPublication Model (Lines 130-198)

**Table:** `featured_publication`

**Fields:**
- `id` (UUID, PK)
- `title` (text, required)
- `description` (text)
- `image_url` (text)
- `link` (text, required)
- `display_order` (int)
- `created_at` (datetime)

**Class Methods:**
- `get(id)`, `get_all()` - Fetch publications
- `as_dict()` - Serialize to dict

### BugTicket Model (Lines 206-308)

**Table:** `bug_ticket`

**Fields:**
- `id` (UUID, PK)
- `user_id` (text, FK to user)
- `title` (text, required)
- `description` (text, required)
- `url` (text)
- `image_filename` (text)
- `browser_info` (text)
- `log_snapshot` (text)
- `status` (text)
- `admin_notes` (text)
- `resolved_by` (text, user ID)
- `resolved_at` (datetime)
- `created_at` (datetime)
- `updated_at` (datetime)

**Status Constants:**
- `STATUS_OPEN = 'open'`
- `STATUS_IN_PROGRESS = 'in_progress'`
- `STATUS_RESOLVED_USER = 'resolved_by_user'`
- `STATUS_RESOLVED_ADMIN = 'resolved_by_admin'`

**Class Methods:**
- `get(id)` - Fetch by ID
- `get_all(status=None, user_id=None, limit=100, offset=0)` - Query with filters
- `as_dict()` - Serialize to dict

---

## 8. TEMPLATES DIRECTORY STRUCTURE

```
templates/
├── admin/
│   ├── featured_datasets.html       ← Sysadmin panel
│   └── featured_publications.html   ← Sysadmin panel
├── user/
│   ├── new.html
│   ├── edit_user_form.html
│   ├── read.html
│   ├── dashboard.html
│   ├── read_base.html
│   ├── documents.html              ← User's documents
│   ├── organizations.html          ← User's orgs
│   ├── data_stories.html
│   ├── news.html
│   ├── events.html
│   └── snippets/
├── people/
│   ├── index.html                  ← People directory
│   └── snippets/person_card.html
├── organization/
│   ├── read_base.html
│   ├── publications.html           ← Org publications
│   ├── news.html
│   ├── events.html
│   ├── data_stories.html
│   ├── people.html                 ← Org members
│   ├── request_membership.html     ← Request form
│   ├── membership_requests.html    ← Admin view
│   ├── membership_requests_overview.html ← Multi-org view
│   └── snippets/
├── bug_tickets/
│   ├── new.html
│   ├── list.html
│   └── show.html
└── ... other templates
```

**NO existing templates for:**
- User management admin panel
- User listing admin panel
- User deletion/editing admin panel
- User role/permission management panel

---

## 9. EXISTING ADMIN/MANAGEMENT UI FEATURES

### ✅ Currently Implemented

1. **Featured Datasets Admin** (`/ckan-admin/featured-datasets`)
   - Sysadmin can list featured datasets
   - Search datasets
   - Add/remove featured tag
   - Template: `admin/featured_datasets.html`

2. **Featured Publications Admin** (`/ckan-admin/featured-publications`)
   - Create/update/delete publications
   - Reorder publications
   - Upload publication images
   - Template: `admin/featured_publications.html`

3. **Organization Membership Requests** (`/organization/<name>/membership-requests`)
   - Org admins see pending requests
   - Can approve/reject with role assignment
   - Add admin notes
   - Template: `organization/membership_requests.html`

4. **Bug Ticket System** (User-facing, Sysadmin API)
   - Users create/view/close own tickets
   - Sysadmins can access API endpoint
   - No admin UI for ticket management

### ❌ NOT Implemented

- **User Management Admin Panel** - No sysadmin interface to:
  - List all users
  - View user details
  - Edit user profiles (job title, country, expertise, etc.)
  - Delete users
  - Manage user roles/sysadmin status
  - View user activity

- **User Directory Admin** - No interface to:
  - Moderate profile information
  - Flag inappropriate profiles
  - Bulk edit user metadata

- **User Role Management** - No panel for:
  - Assigning/removing sysadmin status
  - Managing organization admin roles
  - Viewing user permission matrix

---

## 10. KEY CODE PATTERNS FOR NEW SYSADMIN PANEL

### Authentication Pattern
```python
from ckan.common import current_user
from ckan.authz import is_sysadmin

if not is_sysadmin(current_user):
    abort(403, 'Only sysadmins can access this')
```

### Action Pattern
```python
@toolkit.side_effect_free
def user_management_list(context, data_dict):
    toolkit.check_access('user_management_list', context, data_dict)
    # Implementation
    return {'results': [], 'count': 0}
```

### Template Base Inheritance
- Admin templates extend CKAN's `admin base.html`
- Use CKAN's form macros for consistency
- Located in: `templates/admin/*.html`

### Database Query Pattern
```python
users = model.Session.query(model.User).filter(
    model.User.state == 'active'
).order_by(model.User.fullname).all()
```

### Plugin Extras Access Pattern
```python
user_obj = model.User.get(user_id)
extras = user_obj.plugin_extras or {}
profile = extras.get('theme_ejemplo', {})
value = profile.get('job_title', '')
```

---

## RECOMMENDATIONS FOR NEW SYSADMIN PANEL

### Suggested Features (Priority Order)

1. **User List Page** (`/ckan-admin/users`)
   - Sort by: name, created, last active
   - Filter by: sysadmin status, active/deleted
   - Quick actions: View profile, Edit, Delete
   - Pagination: 50 per page

2. **User Edit Page** (`/ckan-admin/users/<id>/edit`)
   - Edit core fields: name, fullname, email
   - Edit profile fields: job_title, country, institution, expertise_areas
   - Manage sysadmin status (checkbox)
   - Delete account button

3. **User Profile View** (`/ckan-admin/users/<id>`)
   - Read-only profile summary
   - Organizations they belong to
   - Datasets they own
   - Activity timeline

4. **Bulk Actions**
   - Export user list (CSV)
   - Bulk deactivate accounts
   - Bulk modify sysadmin status

### Implementation Checklist

```python
# 1. New actions in actions.py
- admin_user_list()
- admin_user_show()
- admin_user_update()
- admin_user_delete()

# 2. New auth functions in auth.py
- admin_user_list()
- admin_user_show()
- admin_user_update()
- admin_user_delete()

# 3. New routes in plugin.py get_blueprint()
/ckan-admin/users
/ckan-admin/users/<id>
/ckan-admin/users/<id>/edit

# 4. New controller methods in controller.py
- admin_users_list()
- admin_user_show()
- admin_user_edit()
- admin_user_delete()

# 5. New templates
- templates/admin/users_list.html
- templates/admin/user_show.html
- templates/admin/user_edit.html

# 6. Update helpers.py if needed for UI support
```

---

## FILE SIZES & COMPLEXITY

| File | Lines | Focus |
|------|-------|-------|
| plugin.py | 942 | Routing, helpers, DB init |
| controller.py | 1670 | View logic, template rendering |
| actions.py | 767 | Custom business logic |
| auth.py | 140 | Permission checks |
| helpers.py | 335 | Template-accessible functions |
| validators.py | 89 | Field validation |
| model.py | 309 | SQLAlchemy models |

---

## USER PROFILE DATA STORAGE

**Core CKAN User Table (`user`):**
- id, name, fullname, email, password, created, about, image_url

**Extended Profile (plugin_extras):**
```python
user_obj.plugin_extras = {
    'theme_ejemplo': {
        'job_title': 'Data Scientist',
        'institution': 'UNESCO',
        'country': 'France',
        'phone': '+33123456789',
        'website': 'https://example.com',
        'orcid': '0000-0001-2345-6789',
        'expertise_areas': '["Water Management", "Data Analysis"]',  # JSON
        'social_links': '{"linkedin": "...", "twitter": "..."}',    # JSON
    }
}
```

---

## KEY OBSERVATIONS

1. **No User Management Admin UI** - The extension is designed around *user self-service* and *organizational workflows*, not sysadmin centralized control

2. **Decentralized Membership** - Org admins manage who joins their org via membership requests, not sysadmins

3. **Profile-First Design** - Users enrich their own profiles with extended fields; no admin editing

4. **Action-Driven Architecture** - Heavy use of custom actions for complex logic (good for APIs)

5. **Model-Based Tracking** - Custom tables for requests, featured items, and bug tickets

6. **Sysadmin Limited Role** - Currently only manages featured datasets/publications; not general user administration

