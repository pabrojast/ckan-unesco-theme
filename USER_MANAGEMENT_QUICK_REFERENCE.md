# User Management - Quick Reference

## 🎯 Current State Summary

| Feature | Status | Location | Comments |
|---------|--------|----------|----------|
| **User Profile Fields** | ✅ Implemented | plugin_extras | job_title, institution, country, phone, website, orcid, expertise_areas, social_links |
| **User Profile Editing** | ✅ Implemented | user/edit_user_form.html | Via CKAN's core user edit (extended by our validators) |
| **People Directory** | ✅ Implemented | /people | Search, filter by country/org/expertise |
| **Org Members View** | ✅ Implemented | /organization/<name>/people | Shows members with profiles |
| **Membership Requests** | ✅ Implemented | /organization/<name>/membership-requests | Org admins approve/reject |
| **Featured Datasets Admin** | ✅ Implemented | /ckan-admin/featured-datasets | Sysadmin panel |
| **Featured Publications Admin** | ✅ Implemented | /ckan-admin/featured-publications | Sysadmin panel |
| **Bug Tickets** | ✅ Implemented | /bug-tickets | Users create/view, sysadmins manage |
| **User Management Admin** | ❌ Missing | N/A | No sysadmin interface to list/edit/delete users |
| **User Directory Admin** | ❌ Missing | N/A | No sysadmin moderation interface |
| **User Role Management** | ❌ Missing | N/A | No interface to manage sysadmin status |

## 📁 File Reference

### Entry Points

| File | Lines | Purpose |
|------|-------|---------|
| `plugin.py` | 942 | Registers routes, helpers, actions, auth functions |
| `controller.py` | 1670 | View functions for rendering templates |
| `actions.py` | 767 | Business logic for user/member/featured operations |
| `auth.py` | 140 | Authorization checks (who can do what) |
| `helpers.py` | 335 | Functions available in templates |
| `validators.py` | 89 | Field validation for user profile data |
| `model.py` | 309 | SQLAlchemy models: MembershipRequest, FeaturedPublication, BugTicket |

### Templates

```
templates/
├── admin/
│   ├── featured_datasets.html
│   └── featured_publications.html
├── user/
│   ├── documents.html
│   ├── organizations.html
│   ├── data_stories.html
│   ├── news.html
│   ├── events.html
│   └── edit_user_form.html
├── people/
│   └── index.html
└── organization/
    ├── people.html
    ├── publications.html
    ├── membership_requests.html
    ├── membership_requests_overview.html
    └── request_membership.html
```

## 🔑 Key Concepts

### User Profile Extension

**Storage Location:** `user.plugin_extras['theme_ejemplo']`

```python
{
    'job_title': string,
    'institution': string,
    'country': string,
    'phone': string,
    'website': string,
    'orcid': string,
    'expertise_areas': JSON array (string in DB),
    'social_links': JSON object (string in DB)
}
```

**Accessed via:**
- Action: `user_show` (returns profile fields)
- Helper: `get_user_profile(user_name)`
- Direct model access: `user_obj.plugin_extras['theme_ejemplo']`

### Custom Database Tables

1. **membership_request** - User requests to join org
   - status: pending → approved/rejected
   - Handled by org admins
   
2. **featured_publication** - Curated homepage publications
   - Managed by sysadmins
   
3. **bug_ticket** - User-reported issues
   - Users create/close own
   - Sysadmins manage all

### Key Actions & Their Auth

```python
# User/People
user_show()                     # Anyone
user_update()                   # User themselves
people_list()                   # Anyone
organization_people()           # Anyone

# Membership
membership_request_create()     # Authenticated
membership_request_list()       # Org admin / sysadmin
membership_request_process()    # Org admin / sysadmin
membership_request_count()      # Authenticated

# Featured
featured_dataset_list/add/remove()          # Sysadmin only
featured_publication_list/create/update()   # Sysadmin only

# Bugs
bug_ticket_create()             # Authenticated
bug_ticket_list()               # Authenticated (filtered)
bug_ticket_show()               # Owner / sysadmin
bug_ticket_update()             # Owner / sysadmin
bug_ticket_api_list()           # Sysadmin only
```

### Key Routes & Controllers

| Route | Method | Controller | Action |
|-------|--------|-----------|--------|
| `/people` | GET | `people_index()` | `people_list` |
| `/organization/<name>/people` | GET | `organization_people(name)` | `organization_people` |
| `/organization/<name>/request-membership` | GET/POST | `request_membership(name)` | `membership_request_create` |
| `/organization/<name>/membership-requests` | GET/POST | `membership_requests(name)` | `membership_request_list/process` |
| `/user/<id>/documents` | GET | `user_documents(id)` | `package_search` |
| `/user/<id>/organizations` | GET | `user_organizations(id)` | - |
| `/ckan-admin/featured-datasets` | GET | `featured_datasets_admin()` | `featured_dataset_list` |
| `/ckan-admin/featured-publications` | GET | `featured_publications_admin()` | `featured_publication_list` |

## 🔐 Permission Model

### Sysadmin
- Manage featured datasets/publications
- View all users (not implemented)
- Manage all org memberships (implicit)
- View/manage all bug tickets

### Org Admin
- Approve/reject member requests
- View org members
- Manage org (standard CKAN)

### Org Member
- See other members
- Request to join other orgs
- Create/manage own bug tickets

### Authenticated User
- See people directory
- Update own profile
- Create membership requests
- Create bug tickets

### Anonymous
- See people directory (read-only)
- See org members (read-only)

## 💡 Code Patterns

### Checking if User is Sysadmin
```python
from ckan.authz import is_sysadmin
if is_sysadmin(current_user):
    # ...
```

### Getting User Profile
```python
user_obj = model.User.get(user_id)
profile = (user_obj.plugin_extras or {}).get('theme_ejemplo', {})
job_title = profile.get('job_title', '')
```

### Getting Admin Org IDs
```python
from ckanext.theme_ejemplo.actions import _get_admin_org_ids
org_ids = _get_admin_org_ids(user_id)  # List of org IDs
```

### Calling Custom Action
```python
result = toolkit.get_action('people_list')(
    {'ignore_auth': True},
    {
        'q': 'john',
        'country': 'France',
        'limit': 21,
        'offset': 0
    }
)
# result['results'] = [user1, user2, ...]
# result['count'] = total
```

### Using in Template
```jinja2
{{ get_user_profile('username') }}
{{ get_people_directory(q='water', country='France') }}
{{ get_org_members_with_profiles('org_id') }}
{{ is_org_admin('org_id') }}
```

## 🚀 Planning New Sysadmin User Management Panel

### Suggested Implementation Order

1. **List all users** → `/ckan-admin/users`
   - Search by name/email
   - Sort by created/modified
   - Filter by sysadmin status
   - Pagination

2. **User detail page** → `/ckan-admin/users/<id>`
   - Show all profile fields
   - Organizations they belong to
   - Datasets they own
   - Activity/timeline

3. **User edit page** → `/ckan-admin/users/<id>/edit`
   - Edit core fields
   - Edit profile fields (job_title, country, etc.)
   - Toggle sysadmin status
   - Delete account button

4. **User delete** → POST `/ckan-admin/users/<id>/delete`
   - Soft delete (mark inactive)
   - Transfer ownership option

### Required New Code

**In plugin.py:**
```python
blueprint.add_url_rule(
    u'/ckan-admin/users',
    u'admin_users_list',
    MyLogica.admin_users_list,
    methods=['GET']
)
# ... more routes
```

**In controller.py:**
```python
@staticmethod
def admin_users_list():
    # Sysadmin check
    # Call admin_user_list action
    # Render admin/users.html
    
@staticmethod
def admin_user_show(user_id):
    # Call admin_user_show action
    # Render admin/user.html

@staticmethod
def admin_user_edit(user_id):
    # GET: Display form
    # POST: Call admin_user_update action
    # Render admin/user_edit.html
```

**In actions.py:**
```python
def admin_user_list(context, data_dict):
    toolkit.check_access('admin_user_list', context, data_dict)
    # Query users with filters
    # Return paginated list

def admin_user_show(context, data_dict):
    toolkit.check_access('admin_user_show', context, data_dict)
    # Get user with all profile info
    # Get user's orgs/datasets
    
def admin_user_update(context, data_dict):
    toolkit.check_access('admin_user_update', context, data_dict)
    # Update user fields
    # Update profile fields
    # Handle sysadmin toggle
```

**In auth.py:**
```python
def admin_user_list(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_show(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_update(context, data_dict):
    return _sysadmin_only(context, data_dict)
```

**In templates:**
```
templates/admin/users.html       # List page
templates/admin/user_show.html   # Detail page
templates/admin/user_edit.html   # Edit form
```

## 📊 Data Model

### Core User Fields (CKAN)
- id (UUID)
- name (username, unique)
- fullname (display name)
- email
- password (hashed)
- created (datetime)
- about (bio)
- image_url (profile picture)
- sysadmin (boolean) ← Can edit via admin panel
- state (active/deleted)

### Extended Profile Fields (Our Extension)
Stored in `user.plugin_extras['theme_ejemplo']`:
- job_title (text)
- institution (text)
- country (text)
- phone (text)
- website (url)
- orcid (text)
- expertise_areas (JSON array)
- social_links (JSON object)

### Related Records

**Org Membership** (CKAN's `member` table):
- table_id = user.id
- group_id = organization.id
- capacity = 'member' | 'editor' | 'admin'

**Membership Request** (Our `membership_request` table):
- user_id
- organization_id
- status = 'pending' | 'approved' | 'rejected'
- message (user's request message)
- role = 'member' | 'editor' | 'admin'
- handled_by (sysadmin/org-admin who processed)
- admin_note

**Bug Ticket** (Our `bug_ticket` table):
- user_id
- title, description
- status = 'open' | 'in_progress' | 'resolved_by_user' | 'resolved_by_admin'

## 🔍 Important Caveats

1. **User self-service model** - This extension assumes users manage their own profiles, not admins
2. **Org-centric** - Membership & permissions are organization-focused, not user-focused
3. **No user deletion UI** - Core CKAN doesn't have built-in user deletion (soft delete only)
4. **Limited audit trail** - No activity log for who edited user profiles
5. **No bulk operations** - Each action is individual (no bulk edit/delete)

