# Admin Editing Pattern - Quick Reference

## Architecture at a Glance

```
REQUEST FLOW:
Browser → Controller (check_access) → Action (auth check + DB op) → Response JSON

ADMIN PANELS:
1. /ckan-admin/featured-datasets        → Add/Remove datasets via TAGS
2. /ckan-admin/featured-publications    → Full CRUD for custom DB table
3. /ckan-admin/users                    → User management (CKAN core table)
```

## Three Admin Modules

### 1. Featured Datasets
**What**: Select which datasets appear on homepage  
**Where**: Tags on dataset packages  
**Mechanism**: Append/remove `FeaturedDataset` tag  
**Query**: Solr search with `fq='tags:FeaturedDataset'`  
**Routes**:
- GET `/ckan-admin/featured-datasets` → Render panel
- GET `/ckan-admin/featured-datasets/search?q=term` → Search AJAX
- POST `/ckan-admin/featured-datasets/add` → Add to featured
- POST `/ckan-admin/featured-datasets/remove` → Remove from featured

### 2. Featured Publications
**What**: UNESDOC/Water publications on homepage  
**Where**: Custom `featured_publication` database table  
**Fields**: id, title, link, description, image_url, display_order, created_at  
**Operations**: Full CRUD + reorder + image upload  
**Routes**:
- GET `/ckan-admin/featured-publications` → Render panel
- POST `/ckan-admin/featured-publications/create` → Create
- POST `/ckan-admin/featured-publications/update` → Update
- POST `/ckan-admin/featured-publications/delete` → Delete
- POST `/ckan-admin/featured-publications/reorder` → Reorder with display_order
- POST `/ckan-admin/featured-publications/upload-image` → Upload image

### 3. User Management
**What**: Create/delete/manage users, reset passwords, control sysadmin access  
**Where**: CKAN core `user` table  
**Pagination**: 25 users per page  
**Filters**: Search (name/email/fullname), State (active/deleted), Role (sysadmin/regular)  
**Routes**:
- GET `/ckan-admin/users?q=...&state=...&sysadmin=...&page=1` → List with filters
- GET `/ckan-admin/users/search?q=term` → Typeahead search AJAX
- POST `/ckan-admin/users/create` → Create new user
- POST `/ckan-admin/users/reset-password` → Reset password (needs verification)
- POST `/ckan-admin/users/delete` → Soft-delete
- POST `/ckan-admin/users/purge` → Permanent deletion (needs verification)
- POST `/ckan-admin/users/reactivate` → Reactivate deleted user
- POST `/ckan-admin/users/toggle-sysadmin` → Promote/demote

## Auth: Always Sysadmin-Only

```python
def _sysadmin_only(context, data_dict):
    user_obj = context.get('auth_user_obj')
    if user_obj and user_obj.sysadmin:
        return {'success': True}
    return {'success': False}
```

All actions check this first. Returns 403 if user not sysadmin.

## Key Data Flows

### Add Featured Dataset
```
Form → POST /featured-datasets/add {id: "dataset-123"}
    → Controller: featured_datasets_add()
    → Action: featured_dataset_add()
    → Gets package, appends tag {'name': 'FeaturedDataset'}
    → package_patch() to update
    ← JSON: {success: true}
```

### Create Featured Publication
```
Form → POST /featured-publications/create
  {title, link, description, image_url}
    → Controller: featured_publications_create()
    → Action: featured_publication_create()
    → Creates FeaturedPublication object
    → Session.add + commit
    ← JSON: {id, title, link, ..., created_at}
```

### Reset User Password
```
Form → POST /users/reset-password
  {id: "user-123", password: "newpass", sysadmin_password: "verify123"}
    → Controller: users_admin_reset_password()
    → Action: admin_user_reset_password()
    → Verify sysadmin password: sysadmin_obj.validate_password()
    → target_user.password = new_password
    → Session.commit()
    ← JSON: {success: true, message: "..."}
```

## Security Measures

| Measure | Where | How |
|---------|-------|-----|
| **Sysadmin-only** | auth.py | Check `user_obj.sysadmin` |
| **Password verification** | admin_user_reset_password, admin_user_purge | `sysadmin_obj.validate_password()` |
| **Self-protection** | admin_user_delete, admin_user_toggle_sysadmin | Compare `target_user.id` with `sysadmin_obj.id` |
| **System integrity** | admin_user_toggle_sysadmin | Row lock `.with_for_update()` on sysadmin count |
| **Soft vs hard delete** | admin_user_delete/purge | Delete sets state→'deleted', Purge removes from DB |

## File Map

| File | Purpose | Key Methods |
|------|---------|-------------|
| `plugin.py:333-683` | Routes registration | `get_blueprint()` |
| `controller.py:1225+` | HTTP handlers | `featured_*_admin()`, `users_admin()`, etc |
| `actions.py:451+` | Business logic | `featured_dataset_*()`, `admin_user_*()` |
| `auth.py:64+` | Access control | `_sysadmin_only()`, `featured_*()`, `admin_user_*()` |
| `model.py:130+` | ORM models | `FeaturedPublication` class, `init_featured_publications_db()` |
| `templates/admin/*.html` | UI + JS | Form submission, AJAX, drag-reorder |

## Response Formats

### Success
```json
{
  "success": true,
  "id": "550e8400-...",
  "title": "...",
  "message": "Operation completed"
}
```

### Error
```json
{
  "success": false,
  "error": "Error message",
  "error_dict": {"field": ["validation error"]}
}
```

HTTP Status:
- 200: OK
- 400: Validation error
- 403: Not authorized (not sysadmin)
- 404: Not found
- 500: Server error

## Database Schema

### featured_publication table
```sql
CREATE TABLE featured_publication (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  link TEXT NOT NULL,
  description TEXT DEFAULT '',
  image_url TEXT DEFAULT '',
  display_order INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Query examples
```python
# Get all ordered by display
pubs = FeaturedPublication.get_all()

# Get single
pub = FeaturedPublication.get('550e8400-...')

# Create
pub = FeaturedPublication(title='...', link='...', image_url='...')
model.Session.add(pub)
model.Session.commit()

# Update
pub.title = 'New Title'
model.Session.commit()

# Delete
model.Session.delete(pub)
model.Session.commit()
```

## Template Structure

### featured_datasets.html (733 lines)
```
- Breadcrumb
- Header banner
- Search section (input + results container)
- Featured list (with delete button on each)
- JavaScript IIFE with AJAX handlers
```

### featured_publications.html (944 lines)
```
- Breadcrumb
- Header banner
- Add form (drag-drop image, title, link, description)
- Publications list (drag-sortable)
- JavaScript: AJAX + drag/drop handlers
```

### users.html (946 lines)
```
- Breadcrumb
- Header banner (user count)
- Toolbar (search, filters, create button)
- Users table (paginated, 25/page)
- Action buttons (Edit, Reset PW, Delete, etc)
- Modal forms (Create, Reset PW, Delete confirmation, etc)
- JavaScript: AJAX + modal management
```

## Common AJAX Patterns

### Send form data
```javascript
var formData = new FormData();
formData.append('id', 'dataset-123');
formData.append('title', 'My Publication');

fetch('/ckan-admin/featured-publications/create', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => {
  if (data.success) {
    // Update DOM
    document.getElementById('list').innerHTML += createCard(data);
  }
});
```

### Send JSON
```javascript
fetch('/ckan-admin/featured-publications/reorder', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({order: ['id1', 'id2', 'id3']})
})
.then(r => r.json())
.then(data => console.log(data));
```

### Upload file
```javascript
var formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('/ckan-admin/featured-publications/upload-image', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => {
  if (data.success) {
    imageUrlInput.value = data.image_url;
    previewImg.src = data.image_url;
  }
});
```

## Debugging Tips

1. **Check auth first**: Add `print(user_obj.sysadmin)` in action to verify user status
2. **Session not committing?**: Make sure `model.Session.commit()` is called
3. **Tag not adding?**: Check if tag object is formatted as `{'name': 'FeaturedDataset'}`
4. **Image upload failing?**: Check uploader type matches 'featured_publications'
5. **Race conditions on sysadmin toggle?**: Ensure `.with_for_update()` row lock is used

## Extension Points

To add a new admin module:
1. Define model class (if custom storage) in `model.py`
2. Create routes in `plugin.py:get_blueprint()`
3. Add controller methods
4. Add action functions
5. Add auth functions
6. Add template with HTML + JavaScript
7. Register actions in `plugin.py:get_actions()`
8. Register auth in `plugin.py:get_auth_functions()`

