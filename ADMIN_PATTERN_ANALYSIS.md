# CKAN UNESCO Theme - COMPLETE Admin Editing Pattern

## Quick Reference: Three Admin Modules

| Module | Storage | Routes | Key Methods |
|--------|---------|--------|-------------|
| **Featured Datasets** | CKAN Tags | `/ckan-admin/featured-datasets/*` | List, Add, Remove |
| **Featured Publications** | Custom DB Table | `/ckan-admin/featured-publications/*` | CRUD + Reorder + Upload |
| **User Management** | CKAN User Model | `/ckan-admin/users/*` | CRUD + Reset Password + Toggle Role |

---

## FILE STRUCTURE

```
ckanext/theme_ejemplo/
├── plugin.py              # Routes: get_blueprint() (lines 333-683)
├── controller.py          # Handler methods: MyLogica class
│   ├── featured_datasets_admin (1225)
│   ├── featured_publications_admin (1340)
│   └── users_admin (1675)
├── actions.py             # Business logic & DB operations
│   ├── featured_dataset_* (451-509)
│   ├── featured_publication_* (517-601)
│   └── admin_user_* (781-1108)
├── auth.py                # Access control (sysadmin-only)
├── model.py               # SQLAlchemy ORM models
│   ├── FeaturedPublication (130-163)
│   ├── init_featured_publications_db (165-199)
│   ├── BugTicket (206-266)
│   └── init_bug_tickets_db (268-308)
└── templates/admin/
    ├── featured_datasets.html (733 lines)
    ├── featured_publications.html (944 lines)
    └── users.html (946 lines)
```

---

## PART 1: FEATURED DATASETS ADMIN

### Route Registration (plugin.py:517-540)

```python
# Featured datasets admin panel (sysadmin only)
blueprint.add_url_rule(
    u'/ckan-admin/featured-datasets',
    u'featured_datasets_admin',
    MyLogica.featured_datasets_admin,
    methods=['GET']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-datasets/search',
    u'featured_datasets_search',
    MyLogica.featured_datasets_search,
    methods=['GET']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-datasets/add',
    u'featured_datasets_add',
    MyLogica.featured_datasets_add,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-datasets/remove',
    u'featured_datasets_remove',
    MyLogica.featured_datasets_remove,
    methods=['POST']
)
```

### Controller: View & Search (controller.py:1225-1282)

```python
@staticmethod
def featured_datasets_admin():
    """Render the featured datasets admin panel. Sysadmin only."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_dataset_list', context, {})
    except toolkit.NotAuthorized:
        return base.abort(403, _('Not authorized'))

    featured = toolkit.get_action('featured_dataset_list')(context, {})
    extra_vars = {
        'featured_datasets': featured.get('results', []),
        'featured_count': featured.get('count', 0),
    }
    return base.render('admin/featured_datasets.html', extra_vars=extra_vars)

@staticmethod
def featured_datasets_search():
    """AJAX: Search datasets to add as featured."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_dataset_list', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    q = request.args.get('q', '')
    if not q or len(q) < 2:
        return jsonify({'results': []})

    try:
        search_result = toolkit.get_action('package_search')(
            {'ignore_auth': True},
            {'q': q, 'rows': 10}
        )
        results = []
        for pkg in search_result.get('results', []):
            is_featured = any(
                t['name'] == 'FeaturedDataset'
                for t in pkg.get('tags', [])
            )
            org = pkg.get('organization') or {}
            results.append({
                'id': pkg['id'],
                'name': pkg['name'],
                'title': pkg.get('title', pkg['name']),
                'organization_title': org.get('title', ''),
                'is_featured': is_featured,
            })
        return jsonify({'results': results})
    except Exception as e:
        log.error(f'Error searching datasets: {e}')
        return jsonify({'results': [], 'error': str(e)})
```

### Controller: Add/Remove (controller.py:1283-1335)

```python
@staticmethod
def featured_datasets_add():
    """AJAX: Add a dataset as featured."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_dataset_add', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    dataset_id = request.form.get('id', '')
    if not dataset_id:
        return jsonify({'success': False, 'error': 'Missing dataset id'}), 400

    try:
        result = toolkit.get_action('featured_dataset_add')(
            context, {'id': dataset_id}
        )
        return jsonify(result)
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'Dataset not found'}), 404
    except Exception as e:
        log.error(f'Error adding featured dataset: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def featured_datasets_remove():
    """AJAX: Remove a dataset from featured."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_dataset_remove', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    dataset_id = request.form.get('id', '')
    if not dataset_id:
        return jsonify({'success': False, 'error': 'Missing dataset id'}), 400

    try:
        result = toolkit.get_action('featured_dataset_remove')(
            context, {'id': dataset_id}
        )
        return jsonify(result)
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'Dataset not found'}), 404
    except Exception as e:
        log.error(f'Error removing featured dataset: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
```

### Actions: Featured Dataset Logic (actions.py:451-509)

```python
FEATURED_TAG = u'FeaturedDataset'

def featured_dataset_list(context, data_dict):
    """List all datasets tagged as featured. Sysadmin only."""
    toolkit.check_access('featured_dataset_list', context, data_dict)

    search_result = toolkit.get_action('package_search')(
        {'ignore_auth': True},
        {'fq': 'tags:{}'.format(FEATURED_TAG), 'rows': 100}
    )
    results = []
    for pkg in search_result.get('results', []):
        org = pkg.get('organization') or {}
        results.append({
            'id': pkg['id'],
            'name': pkg['name'],
            'title': pkg.get('title', pkg['name']),
            'notes': pkg.get('notes', ''),
            'organization_title': org.get('title', ''),
            'metadata_modified': pkg.get('metadata_modified', ''),
        })
    return {'results': results, 'count': search_result.get('count', 0)}


def featured_dataset_add(context, data_dict):
    """Add the FeaturedDataset tag to a dataset. Sysadmin only."""
    toolkit.check_access('featured_dataset_add', context, data_dict)
    dataset_id = toolkit.get_or_bust(data_dict, 'id')

    pkg = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': dataset_id}
    )

    tags = pkg.get('tags', [])
    if any(t['name'] == FEATURED_TAG for t in tags):
        return {'success': True, 'message': 'Already featured'}

    tags.append({'name': FEATURED_TAG})
    toolkit.get_action('package_patch')(
        {'ignore_auth': True},
        {'id': pkg['id'], 'tags': tags}
    )
    return {'success': True}


def featured_dataset_remove(context, data_dict):
    """Remove the FeaturedDataset tag from a dataset. Sysadmin only."""
    toolkit.check_access('featured_dataset_remove', context, data_dict)
    dataset_id = toolkit.get_or_bust(data_dict, 'id')

    pkg = toolkit.get_action('package_show')(
        {'ignore_auth': True}, {'id': dataset_id}
    )

    tags = [t for t in pkg.get('tags', []) if t['name'] != FEATURED_TAG]
    toolkit.get_action('package_patch')(
        {'ignore_auth': True},
        {'id': pkg['id'], 'tags': tags}
    )
    return {'success': True}
```

### Auth: Featured Datasets (auth.py:64-82)

```python
def _sysadmin_only(context, data_dict):
    user_obj = context.get('auth_user_obj')
    if user_obj and user_obj.sysadmin:
        return {'success': True}
    return {'success': False, 'msg': toolkit._('Only sysadmins can manage featured datasets')}


def featured_dataset_list(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_dataset_add(context, data_dict):
    return _sysadmin_only(context, data_dict)


def featured_dataset_remove(context, data_dict):
    return _sysadmin_only(context, data_dict)
```

---

## PART 2: FEATURED PUBLICATIONS ADMIN

### Route Registration (plugin.py:543-578)

```python
# Featured publications admin panel (sysadmin only)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications',
    u'featured_publications_admin',
    MyLogica.featured_publications_admin,
    methods=['GET']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications/create',
    u'featured_publications_create',
    MyLogica.featured_publications_create,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications/update',
    u'featured_publications_update',
    MyLogica.featured_publications_update,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications/delete',
    u'featured_publications_delete',
    MyLogica.featured_publications_delete,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications/reorder',
    u'featured_publications_reorder',
    MyLogica.featured_publications_reorder,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/featured-publications/upload-image',
    u'featured_publications_upload_image',
    MyLogica.featured_publications_upload_image,
    methods=['POST']
)
```

### Controller: CRUD Operations (controller.py:1340-1505)

```python
@staticmethod
def featured_publications_admin():
    """Render the featured publications admin panel. Sysadmin only."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_list', context, {})
    except toolkit.NotAuthorized:
        return base.abort(403, _('Not authorized'))

    pubs = toolkit.get_action('featured_publication_list')(context, {})
    extra_vars = {
        'publications': pubs.get('results', []),
        'publications_count': pubs.get('count', 0),
    }
    return base.render('admin/featured_publications.html', extra_vars=extra_vars)

@staticmethod
def featured_publications_create():
    """AJAX: Create a featured publication."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_create', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    data = {
        'title': request.form.get('title', ''),
        'link': request.form.get('link', ''),
        'description': request.form.get('description', ''),
        'image_url': request.form.get('image_url', ''),
    }

    if not data['title'] or not data['link']:
        return jsonify({'success': False, 'error': 'Title and link are required'}), 400

    try:
        result = toolkit.get_action('featured_publication_create')(context, data)
        return jsonify(result)
    except Exception as e:
        log.error(f'Error creating featured publication: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def featured_publications_update():
    """AJAX: Update a featured publication."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_update', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    pub_id = request.form.get('id', '')
    if not pub_id:
        return jsonify({'success': False, 'error': 'Missing id'}), 400

    data = {'id': pub_id}
    for field in ('title', 'link', 'description', 'image_url'):
        if field in request.form:
            data[field] = request.form[field]

    try:
        result = toolkit.get_action('featured_publication_update')(context, data)
        return jsonify(result)
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    except Exception as e:
        log.error(f'Error updating featured publication: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def featured_publications_delete():
    """AJAX: Delete a featured publication."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_delete', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    pub_id = request.form.get('id', '')
    if not pub_id:
        return jsonify({'success': False, 'error': 'Missing id'}), 400

    try:
        result = toolkit.get_action('featured_publication_delete')(context, {'id': pub_id})
        return jsonify(result)
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    except Exception as e:
        log.error(f'Error deleting featured publication: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def featured_publications_reorder():
    """AJAX: Reorder featured publications."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_reorder', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        order = request.get_json(force=True).get('order', [])
    except Exception:
        order = request.form.getlist('order[]')

    try:
        result = toolkit.get_action('featured_publication_reorder')(
            context, {'order': order}
        )
        return jsonify(result)
    except Exception as e:
        log.error(f'Error reordering featured publications: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def featured_publications_upload_image():
    """AJAX: Upload an image for a featured publication.
    Uses CKAN's storage to save the file and returns the URL.
    """
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('featured_publication_create', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400

    upload_file = request.files['file']
    if not upload_file.filename:
        return jsonify({'success': False, 'error': 'Empty filename'}), 400

    try:
        import ckan.lib.uploader as uploader
        upload = uploader.get_uploader('featured_publications')
        upload.update_data_dict(
            {'upload': upload_file, 'url': '', 'clear_upload': ''},
            'url', 'upload', 'clear_upload'
        )
        upload.upload()
        image_url = h.url_for_static(
            'uploads/featured_publications/{}'.format(upload.filename),
            qualified=False
        )
        return jsonify({'success': True, 'image_url': image_url})
    except Exception as e:
        log.error(f'Error uploading image: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
```

### Model: FeaturedPublication Table (model.py:130-199)

```python
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
```

### Actions: Featured Publications (actions.py:517-601)

```python
@toolkit.side_effect_free
def featured_publication_list(context, data_dict):
    """List all featured publications."""
    toolkit.check_access('featured_publication_list', context, data_dict)
    init_featured_publications_db()
    pubs = FeaturedPublication.get_all()
    return {'results': [p.as_dict() for p in pubs], 'count': len(pubs)}


def featured_publication_create(context, data_dict):
    """Create a new featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_create', context, data_dict)
    init_featured_publications_db()

    title = toolkit.get_or_bust(data_dict, 'title')
    link = toolkit.get_or_bust(data_dict, 'link')
    description = data_dict.get('description', u'')
    image_url = data_dict.get('image_url', u'')
    display_order = int(data_dict.get('display_order', 0))

    pub = FeaturedPublication(
        title=title,
        link=link,
        description=description,
        image_url=image_url,
        display_order=display_order,
    )
    model.Session.add(pub)
    model.Session.commit()
    return pub.as_dict()


def featured_publication_update(context, data_dict):
    """Update a featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_update', context, data_dict)
    init_featured_publications_db()

    pub_id = toolkit.get_or_bust(data_dict, 'id')
    pub = FeaturedPublication.get(pub_id)
    if not pub:
        raise toolkit.ObjectNotFound('Featured publication not found')

    for field in ('title', 'link', 'description', 'image_url'):
        if field in data_dict:
            setattr(pub, field, data_dict[field])
    if 'display_order' in data_dict:
        pub.display_order = int(data_dict['display_order'])

    model.Session.commit()
    return pub.as_dict()


def featured_publication_delete(context, data_dict):
    """Delete a featured publication. Sysadmin only."""
    toolkit.check_access('featured_publication_delete', context, data_dict)
    init_featured_publications_db()

    pub_id = toolkit.get_or_bust(data_dict, 'id')
    pub = FeaturedPublication.get(pub_id)
    if not pub:
        raise toolkit.ObjectNotFound('Featured publication not found')

    model.Session.delete(pub)
    model.Session.commit()
    return {'success': True}


def featured_publication_reorder(context, data_dict):
    """Reorder featured publications. Sysadmin only.
    Expects 'order': list of publication IDs in desired order.
    """
    toolkit.check_access('featured_publication_reorder', context, data_dict)
    init_featured_publications_db()

    order = data_dict.get('order', [])
    if not order:
        return {'success': True}

    for idx, pub_id in enumerate(order):
        pub = FeaturedPublication.get(pub_id)
        if pub:
            pub.display_order = idx

    model.Session.commit()
    return {'success': True}
```

---

## PART 3: USER MANAGEMENT ADMIN

### Route Registration (plugin.py:612-660)

```python
# Sysadmin user management panel
blueprint.add_url_rule(
    u'/ckan-admin/users',
    u'users_admin',
    MyLogica.users_admin,
    methods=['GET']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/search',
    u'users_admin_search',
    MyLogica.users_admin_search,
    methods=['GET']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/create',
    u'users_admin_create',
    MyLogica.users_admin_create,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/reset-password',
    u'users_admin_reset_password',
    MyLogica.users_admin_reset_password,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/delete',
    u'users_admin_delete',
    MyLogica.users_admin_delete,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/purge',
    u'users_admin_purge',
    MyLogica.users_admin_purge,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/reactivate',
    u'users_admin_reactivate',
    MyLogica.users_admin_reactivate,
    methods=['POST']
)
blueprint.add_url_rule(
    u'/ckan-admin/users/toggle-sysadmin',
    u'users_admin_toggle_sysadmin',
    MyLogica.users_admin_toggle_sysadmin,
    methods=['POST']
)
```

### Controller: User Management (controller.py:1675-1907)

```python
@staticmethod
def users_admin():
    """Render the sysadmin user management panel."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_list', context, {})
    except toolkit.NotAuthorized:
        return base.abort(403, _('Not authorized'))

    # Leer parámetros de filtro desde query string
    q = request.args.get('q', '')
    state = request.args.get('state', '')
    sysadmin = request.args.get('sysadmin', '')
    order_by = request.args.get('order_by', 'created')
    page = max(int(request.args.get('page', 1)), 1)
    limit = 25
    offset = (page - 1) * limit

    data_dict = {
        'q': q,
        'state': state,
        'order_by': order_by,
        'limit': limit,
        'offset': offset,
    }
    if sysadmin:
        data_dict['sysadmin'] = sysadmin

    result = toolkit.get_action('admin_user_list')(context, data_dict)
    total = result.get('count', 0)
    total_pages = max(1, (total + limit - 1) // limit)

    extra_vars = {
        'users': result.get('results', []),
        'total': total,
        'q': q,
        'state': state,
        'sysadmin_filter': sysadmin,
        'order_by': order_by,
        'page': page,
        'limit': limit,
        'total_pages': total_pages,
    }
    return base.render('admin/users.html', extra_vars=extra_vars)

@staticmethod
def users_admin_search():
    """AJAX: Search users for autocomplete/quick search."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_list', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    q = request.args.get('q', '')
    if not q or len(q) < 2:
        return jsonify({'results': []})

    try:
        result = toolkit.get_action('admin_user_list')(
            context,
            {'q': q, 'limit': 10, 'offset': 0}
        )
        return jsonify({
            'results': result.get('results', []),
            'count': result.get('count', 0),
        })
    except Exception as e:
        log.error(f'Error searching users: {e}')
        return jsonify({'results': [], 'error': str(e)})

@staticmethod
def users_admin_create():
    """AJAX: Create a new user."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_create', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {
            'name': request.form.get('name', ''),
            'email': request.form.get('email', ''),
            'fullname': request.form.get('fullname', ''),
            'password': request.form.get('password', ''),
            'sysadmin': request.form.get('sysadmin', 'false'),
        }
        result = toolkit.get_action('admin_user_create')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except Exception as e:
        log.error(f'Error creating user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def users_admin_reset_password():
    """AJAX: Reset a user's password."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_reset_password', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {
            'id': request.form.get('id', ''),
            'password': request.form.get('password', ''),
            'sysadmin_password': request.form.get('sysadmin_password', ''),
        }
        result = toolkit.get_action('admin_user_reset_password')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        log.error(f'Error resetting password: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def users_admin_delete():
    """AJAX: Soft-delete a user."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_delete', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {'id': request.form.get('id', '')}
        result = toolkit.get_action('admin_user_delete')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        log.error(f'Error deleting user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def users_admin_purge():
    """AJAX: Permanently purge a deleted user."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_purge', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {
            'id': request.form.get('id', ''),
            'sysadmin_password': request.form.get('sysadmin_password', ''),
        }
        result = toolkit.get_action('admin_user_purge')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        log.error(f'Error purging user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def users_admin_reactivate():
    """AJAX: Reactivate a deleted user."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_reactivate', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {'id': request.form.get('id', '')}
        result = toolkit.get_action('admin_user_reactivate')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        log.error(f'Error reactivating user: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@staticmethod
def users_admin_toggle_sysadmin():
    """AJAX: Promote or demote a user as sysadmin."""
    context = {
        'user': c.user,
        'auth_user_obj': c.userobj,
    }
    try:
        toolkit.check_access('admin_user_toggle_sysadmin', context, {})
    except toolkit.NotAuthorized:
        return jsonify({'success': False, 'error': 'Not authorized'}), 403

    try:
        data = {
            'id': request.form.get('id', ''),
            'sysadmin': request.form.get('sysadmin', 'false'),
        }
        result = toolkit.get_action('admin_user_toggle_sysadmin')(context, data)
        return jsonify(result)
    except toolkit.ValidationError as e:
        return jsonify({'success': False, 'error': e.error_dict}), 400
    except toolkit.ObjectNotFound:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    except Exception as e:
        log.error(f'Error toggling sysadmin: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500
```

### Actions: User Management (actions.py:781-1108)

**admin_user_list()** - List with pagination and filtering

```python
def admin_user_list(context, data_dict):
    """Lista paginada de usuarios con filtros para el panel de administración."""
    toolkit.check_access('admin_user_list', context, data_dict)

    q = data_dict.get('q', '').strip()
    state_filter = data_dict.get('state', '')
    sysadmin_filter = data_dict.get('sysadmin', None)
    limit = min(int(data_dict.get('limit', 25)), 100)
    offset = max(int(data_dict.get('offset', 0)), 0)
    order_by = data_dict.get('order_by', 'created')

    query = model.Session.query(model.User).filter(
        model.User.name != 'default',
        model.User.name != 'harvest',
    )

    if state_filter:
        query = query.filter(model.User.state == state_filter)

    if sysadmin_filter is not None:
        if isinstance(sysadmin_filter, str):
            sysadmin_filter = sysadmin_filter.lower() in ('true', '1', 'yes')
        query = query.filter(model.User.sysadmin == sysadmin_filter)

    if q:
        q_like = f'%{q}%'
        query = query.filter(
            model.User.name.ilike(q_like) |
            model.User.fullname.ilike(q_like) |
            model.User.email.ilike(q_like)
        )

    # Ordenamiento
    order_map = {
        'name': model.User.name.asc(),
        'name_desc': model.User.name.desc(),
        'created': model.User.created.desc(),
        'created_asc': model.User.created.asc(),
        'email': model.User.email.asc(),
    }
    query = query.order_by(order_map.get(order_by, model.User.created.desc()))

    total = query.count()
    users = query.offset(offset).limit(limit).all()

    results = []
    for user_obj in users:
        extras = user_obj.plugin_extras or {}
        profile = extras.get('theme_ejemplo', {})

        orgs = []
        try:
            for g in user_obj.get_groups('organization'):
                orgs.append({'name': g.name, 'title': g.title or g.name})
        except Exception:
            pass

        num_datasets = 0
        try:
            num_datasets = model.Session.query(model.Package).filter(
                model.Package.creator_user_id == user_obj.id,
                model.Package.state == 'active',
            ).count()
        except Exception:
            pass

        results.append({
            'id': user_obj.id,
            'name': user_obj.name,
            'fullname': user_obj.fullname or '',
            'email': user_obj.email or '',
            'image_url': user_obj.image_url or '',
            'state': user_obj.state,
            'sysadmin': user_obj.sysadmin,
            'created': user_obj.created.isoformat() if user_obj.created else '',
            'job_title': profile.get('job_title', ''),
            'institution': profile.get('institution', ''),
            'country': profile.get('country', ''),
            'organizations': orgs,
            'num_datasets': num_datasets,
        })

    return {
        'results': results,
        'count': total,
    }
```

**admin_user_reset_password()** - Password reset with verification

```python
def admin_user_reset_password(context, data_dict):
    """Permite a un sysadmin cambiar la contraseña de cualquier usuario."""
    toolkit.check_access('admin_user_reset_password', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    new_password = toolkit.get_or_bust(data_dict, 'password')
    sysadmin_password = toolkit.get_or_bust(data_dict, 'sysadmin_password')

    if len(new_password) < 8:
        raise toolkit.ValidationError(
            {'password': ['Password must be at least 8 characters']}
        )

    # Verificar la contraseña del sysadmin que ejecuta la acción
    sysadmin_obj = _get_sysadmin_context(context)
    if not sysadmin_obj.validate_password(sysadmin_password):
        raise toolkit.ValidationError(
            {'sysadmin_password': ['Invalid sysadmin password']}
        )

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    target_user.password = new_password
    model.Session.commit()

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'Password updated for {target_user.name}',
    }
```

**admin_user_delete()** - Soft delete

```python
def admin_user_delete(context, data_dict):
    """Soft-delete de un usuario (estado -> deleted)."""
    toolkit.check_access('admin_user_delete', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state == 'deleted':
        raise toolkit.ValidationError(
            {'id': ['User is already deleted']}
        )

    # No permitir eliminar al propio sysadmin
    sysadmin_obj = _get_sysadmin_context(context)
    if target_user.id == sysadmin_obj.id:
        raise toolkit.ValidationError(
            {'id': ['Cannot delete your own account']}
        )

    # Usar la acción core de CKAN para soft-delete
    toolkit.get_action('user_delete')(
        {'user': sysadmin_obj.name, 'ignore_auth': True},
        {'id': target_user.id}
    )

    return {
        'success': True,
        'user_name': target_user.name,
        'message': f'User {target_user.name} has been deleted',
    }
```

**admin_user_purge()** - Permanent deletion

```python
def admin_user_purge(context, data_dict):
    """Eliminación permanente de un usuario de la base de datos.
    Solo se permite purgar usuarios que ya están en estado 'deleted'.
    Esta acción es IRREVERSIBLE.
    """
    toolkit.check_access('admin_user_purge', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    sysadmin_password = toolkit.get_or_bust(data_dict, 'sysadmin_password')

    sysadmin_obj = _get_sysadmin_context(context)
    if not sysadmin_obj.validate_password(sysadmin_password):
        raise toolkit.ValidationError(
            {'sysadmin_password': ['Invalid sysadmin password']}
        )

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    if target_user.state != 'deleted':
        raise toolkit.ValidationError(
            {'id': ['User must be in deleted state before purging. Delete the user first.']}
        )

    user_name = target_user.name

    # Eliminar membresías de grupos/organizaciones residuales
    model.Session.query(model.Member).filter(
        model.Member.table_id == target_user.id,
        model.Member.table_name == 'user',
    ).delete(synchronize_session=False)

    # Eliminar el usuario permanentemente
    model.Session.delete(target_user)
    model.Session.commit()

    return {
        'success': True,
        'user_name': user_name,
        'message': f'User {user_name} has been permanently purged',
    }
```

**admin_user_toggle_sysadmin()** - Promote/demote with safeguards

```python
def admin_user_toggle_sysadmin(context, data_dict):
    """Promover o degradar un usuario como sysadmin."""
    toolkit.check_access('admin_user_toggle_sysadmin', context, data_dict)

    user_id = toolkit.get_or_bust(data_dict, 'id')
    make_sysadmin = data_dict.get('sysadmin', False)
    if isinstance(make_sysadmin, str):
        make_sysadmin = make_sysadmin.lower() in ('true', '1', 'yes')

    target_user = model.User.get(user_id)
    if not target_user:
        raise toolkit.ObjectNotFound('User not found')

    sysadmin_obj = _get_sysadmin_context(context)

    # Protección contra auto-degradación
    if target_user.id == sysadmin_obj.id and not make_sysadmin:
        raise toolkit.ValidationError(
            {'id': ['Cannot remove your own sysadmin privileges']}
        )

    # Verificar que no se quede sin sysadmins (con lock para evitar race conditions)
    if not make_sysadmin and target_user.sysadmin:
        from sqlalchemy import func
        sysadmin_count = model.Session.query(func.count(model.User.id)).filter(
            model.User.sysadmin == True,
            model.User.state == 'active',
        ).with_for_update().scalar()
        if sysadmin_count <= 1:
            raise toolkit.ValidationError(
                {'id': ['Cannot remove the last sysadmin']}
            )

    target_user.sysadmin = make_sysadmin
    model.Session.commit()

    action_label = 'promoted to' if make_sysadmin else 'removed from'
    return {
        'success': True,
        'user_name': target_user.name,
        'sysadmin': make_sysadmin,
        'message': f'User {target_user.name} {action_label} sysadmin',
    }
```

---

## PART 4: AUTHORIZATION (auth.py)

```python
def _sysadmin_only(context, data_dict):
    user_obj = context.get('auth_user_obj')
    if user_obj and user_obj.sysadmin:
        return {'success': True}
    return {'success': False, 'msg': toolkit._('Only sysadmins can manage featured datasets')}

# Featured Dataset Auth
def featured_dataset_list(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_dataset_add(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_dataset_remove(context, data_dict):
    return _sysadmin_only(context, data_dict)

# Featured Publication Auth
def featured_publication_list(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_publication_create(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_publication_update(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_publication_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)

def featured_publication_reorder(context, data_dict):
    return _sysadmin_only(context, data_dict)

# User Management Auth
def admin_user_list(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_reset_password(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_delete(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_purge(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_reactivate(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_toggle_sysadmin(context, data_dict):
    return _sysadmin_only(context, data_dict)

def admin_user_create(context, data_dict):
    return _sysadmin_only(context, data_dict)
```

---

## STORAGE SUMMARY

| Component | Storage Type | Location | Query Method |
|-----------|--------------|----------|--------------|
| **Featured Datasets** | CKAN Tags | dataset.tags[] | Solr: `fq='tags:FeaturedDataset'` |
| **Featured Publications** | Custom DB Table | featured_publication | `FeaturedPublication.get_all()` |
| **Users** | CKAN Core Table | ckan.public.user | `model.Session.query(model.User)` |
| **User Profile Extras** | JSON in user table | user.plugin_extras | `user.plugin_extras['theme_ejemplo']` |

---

## KEY SECURITY PATTERNS

1. **Auth Check First**: Every action/controller checks `toolkit.check_access()` before processing
2. **Sysadmin Only**: All admin operations use `_sysadmin_only()` auth function
3. **Password Verification**: Critical ops (purge, reset password) require sysadmin password re-entry
4. **Self-Protection**: Users cannot delete/demote themselves
5. **System Integrity**: Cannot remove last sysadmin (row lock prevents race conditions)
6. **Soft Deletes**: User deletion is reversible (state → deleted); purge is permanent & requires verification

