# Admin Editing - Real Request/Response Examples

## 1. Featured Datasets - Add Dataset

### Request
```http
POST /ckan-admin/featured-datasets/add HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=climate-change-impacts-2024
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true
}
```

### Response (Not Authorized - not sysadmin)
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json

{
  "success": false,
  "error": "Not authorized"
}
```

### Code Flow
```
POST /featured-datasets/add
  → controller.featured_datasets_add()
  → check_access('featured_dataset_add')
    → auth.featured_dataset_add()
    → _sysadmin_only() → checks user_obj.sysadmin
  → toolkit.get_action('featured_dataset_add')(context, {'id': dataset_id})
    → actions.featured_dataset_add()
    → package_show to get dataset
    → package_patch to add tag {'name': 'FeaturedDataset'}
    → return {'success': True}
  → jsonify({'success': True})
  → Response
```

---

## 2. Featured Datasets - Search

### Request
```http
GET /ckan-admin/featured-datasets/search?q=climate HTTP/1.1
```

### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "results": [
    {
      "id": "climate-change-impacts-2024",
      "name": "climate-change-impacts-2024",
      "title": "Climate Change Impacts Study 2024",
      "organization_title": "UNESCO Science Division",
      "is_featured": true
    },
    {
      "id": "global-climate-risk",
      "name": "global-climate-risk",
      "title": "Global Climate Risk Assessment",
      "organization_title": "UNEP Collaboration",
      "is_featured": false
    }
  ]
}
```

### Minimum Query
```http
GET /ckan-admin/featured-datasets/search?q=c HTTP/1.1
```

Response: `{"results": []}` (min 2 chars required)

---

## 3. Featured Publications - Create

### Request
```http
POST /ckan-admin/featured-publications/create HTTP/1.1
Content-Type: application/x-www-form-urlencoded

title=World Water Report 2024
&link=https://unesdoc.unesco.org/ark:/48223/pf0000389231
&description=Comprehensive analysis of global water resources
&image_url=https://unesdoc.unesco.org/images/0389/389231/389231e.jpg
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "World Water Report 2024",
  "link": "https://unesdoc.unesco.org/ark:/48223/pf0000389231",
  "description": "Comprehensive analysis of global water resources",
  "image_url": "https://unesdoc.unesco.org/images/0389/389231/389231e.jpg",
  "display_order": 0,
  "created_at": "2024-01-15T10:30:45.123456"
}
```

### Response (Missing Required Field)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "Title and link are required"
}
```

### Response (Server Error)
```http
HTTP/1.1 500 Internal Server Error
Content-Type: application/json

{
  "success": false,
  "error": "Database connection error"
}
```

---

## 4. Featured Publications - Update

### Request
```http
POST /ckan-admin/featured-publications/update HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=550e8400-e29b-41d4-a716-446655440000
&title=World Water Report 2024 - Updated
&description=Revised analysis with latest data
```

### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "World Water Report 2024 - Updated",
  "link": "https://unesdoc.unesco.org/ark:/48223/pf0000389231",
  "description": "Revised analysis with latest data",
  "image_url": "https://unesdoc.unesco.org/images/0389/389231/389231e.jpg",
  "display_order": 0,
  "created_at": "2024-01-15T10:30:45.123456"
}
```

### Response (Not Found)
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "success": false,
  "error": "Not found"
}
```

---

## 5. Featured Publications - Reorder

### Request
```http
POST /ckan-admin/featured-publications/reorder HTTP/1.1
Content-Type: application/json

{
  "order": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ]
}
```

### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true
}
```

### Code Effect
- First publication gets display_order = 0
- Second publication gets display_order = 1
- Third publication gets display_order = 2
- All committed to database in single transaction

---

## 6. Featured Publications - Upload Image

### Request
```http
POST /ckan-admin/featured-publications/upload-image HTTP/1.1
Content-Type: multipart/form-data; boundary=----Boundary123

------Boundary123
Content-Disposition: form-data; name="file"; filename="water-report.jpg"
Content-Type: image/jpeg

[Binary image data here]
------Boundary123--
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "image_url": "/uploads/featured_publications/water-report_abc123.jpg"
}
```

### Response (No File)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": "No file uploaded"
}
```

---

## 7. User Management - List

### Request
```http
GET /ckan-admin/users?q=john&state=active&sysadmin=false&order_by=name&page=1 HTTP/1.1
```

### Response
```http
HTTP/1.1 200 OK
Content-Type: text/html

(Rendered HTML template with table of users)
```

### AJAX Request (from template)
```http
GET /ckan-admin/users/search?q=jo HTTP/1.1
```

### AJAX Response
```json
{
  "results": [
    {
      "id": "user-uuid-1",
      "name": "john_doe",
      "fullname": "John Doe",
      "email": "john@example.com",
      "image_url": "/uploads/user/avatar.jpg",
      "state": "active",
      "sysadmin": false,
      "created": "2023-06-15T14:23:00",
      "job_title": "Water Scientist",
      "institution": "UNESCO",
      "country": "France",
      "organizations": [
        {"name": "unesco-hq", "title": "UNESCO Headquarters"}
      ],
      "num_datasets": 5
    }
  ],
  "count": 1
}
```

### Full List Response (HTML)
URL: `GET /ckan-admin/users?page=1`
Query: Renders 25 users per page with:
- User details (name, email, state, role)
- Organization affiliations
- Dataset count
- Action buttons (Edit, Reset Password, Delete, etc)
- Pagination links

---

## 8. User Management - Create

### Request
```http
POST /ckan-admin/users/create HTTP/1.1
Content-Type: application/x-www-form-urlencoded

name=jane_smith
&email=jane@example.com
&fullname=Jane Smith
&password=SecurePass123
&sysadmin=false
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user": {
    "id": "user-uuid-new",
    "name": "jane_smith",
    "email": "jane@example.com",
    "fullname": "Jane Smith",
    "created": "2024-01-15T10:30:00",
    "state": "active",
    "sysadmin": false
  },
  "message": "User jane_smith created successfully"
}
```

### Response (Invalid Password)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "password": [
      "Password must be at least 8 characters"
    ]
  }
}
```

---

## 9. User Management - Reset Password

### Request
```http
POST /ckan-admin/users/reset-password HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-target
&password=NewSecurePass456
&sysadmin_password=AdminPass789
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user_name": "jane_smith",
  "message": "Password updated for jane_smith"
}
```

### Response (Invalid Sysadmin Password)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "sysadmin_password": [
      "Invalid sysadmin password"
    ]
  }
}
```

---

## 10. User Management - Delete (Soft-Delete)

### Request
```http
POST /ckan-admin/users/delete HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-jane
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user_name": "jane_smith",
  "message": "User jane_smith has been deleted"
}
```

### Database Effect
User state changes from 'active' to 'deleted'
User account is preserved and can be reactivated

### Response (Try to Delete Self)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "id": [
      "Cannot delete your own account"
    ]
  }
}
```

---

## 11. User Management - Purge (Permanent Delete)

### Request
```http
POST /ckan-admin/users/purge HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-jane
&sysadmin_password=AdminPass789
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user_name": "jane_smith",
  "message": "User jane_smith has been permanently purged"
}
```

### Response (User Not in Deleted State)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "id": [
      "User must be in deleted state before purging. Delete the user first."
    ]
  }
}
```

### Database Effect
- User completely removed from user table
- All group/organization memberships deleted
- IRREVERSIBLE - cannot undo

---

## 12. User Management - Reactivate

### Request
```http
POST /ckan-admin/users/reactivate HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-jane
```

### Response (Success)
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user_name": "jane_smith",
  "message": "User jane_smith has been reactivated"
}
```

### Database Effect
User state changes from 'deleted' to 'active'
User can immediately log in again

---

## 13. User Management - Toggle Sysadmin

### Promote User (to Sysadmin)
```http
POST /ckan-admin/users/toggle-sysadmin HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-jane
&sysadmin=true
```

### Response
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "success": true,
  "user_name": "jane_smith",
  "sysadmin": true,
  "message": "User jane_smith promoted to sysadmin"
}
```

### Demote User (from Sysadmin)
```http
POST /ckan-admin/users/toggle-sysadmin HTTP/1.1
Content-Type: application/x-www-form-urlencoded

id=user-uuid-jane
&sysadmin=false
```

### Response (But User is Last Sysadmin!)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "id": [
      "Cannot remove the last sysadmin"
    ]
  }
}
```

### Response (Try to Self-Demote)
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "success": false,
  "error": {
    "id": [
      "Cannot remove your own sysadmin privileges"
    ]
  }
}
```

---

## Authentication Context

All requests require Flask context with:
```python
context = {
    'user': c.user,                    # Username string
    'auth_user_obj': c.userobj,        # User object
    'model': model,
    'session': model.Session,
}
```

If not sysadmin:
```
toolkit.check_access() → auth function → _sysadmin_only()
→ return {'success': False}
→ Controller catches NotAuthorized
→ base.abort(403)
```

---

## Error Response Patterns

### 403 - Not Authorized
```json
{
  "success": false,
  "error": "Not authorized"
}
```

### 404 - Not Found
```json
{
  "success": false,
  "error": "Dataset not found"
}
```

### 400 - Validation Error
```json
{
  "success": false,
  "error": {
    "field_name": ["Error message", "Another error"]
  }
}
```

### 500 - Server Error
```json
{
  "success": false,
  "error": "Database connection error"
}
```

