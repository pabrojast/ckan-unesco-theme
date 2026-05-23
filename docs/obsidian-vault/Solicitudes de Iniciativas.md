# Solicitudes de Iniciativas

Flujo end-to-end que permite a usuarios autenticados solicitar la creación de nuevas **iniciativas** (grupos CKAN) sujeto a aprobación de un sysadmin.

> [!info] ¿Qué es una iniciativa?
> En el portal UNESCO IHP, las **iniciativas** son grupos CKAN regulares (`type='group'`, `state='active'`) que **no** son miembros de `member-states`. Se listan en `/initiatives` y aparecen junto a otros grupos temáticos del IHP.

## Componentes

### Modelo
- **Tabla**: `initiative_request`
- **Clase**: `InitiativeRequest` en `ckanext/theme_ejemplo/model.py`
- **Estados**: `pending` → `approved` | `rejected`
- **Campos clave**:
  - `user_id` — solicitante
  - `title`, `description`, `name` (slug propuesto), `logo_url`
  - `status`, `handled_by`, `handled_at`, `admin_note`
  - `created_group_id` — id del grupo creado al aprobar (trazabilidad)

### Acciones (CKAN Action API)
Definidas en `actions.py`, registradas en `plugin.py:get_actions()`:

| Acción | Auth | Propósito |
|---|---|---|
| `initiative_request_create` | Autenticado | Crear solicitud + subir logo |
| `initiative_request_list` | Sysadmin | Listar (filtro opcional `status`) |
| `initiative_request_process` | Sysadmin | Aprobar (crea grupo) o rechazar |
| `initiative_request_count` | Autenticado | Conteo de pendientes (0 si no es sysadmin) |

### Rutas Flask
Definidas en `plugin.py:get_blueprint()`:

| Ruta | Método | Vista |
|---|---|---|
| `/initiatives/request` | GET/POST | `controller.MyLogica.request_initiative` |
| `/ckan-admin/initiative-requests` | GET | `controller.MyLogica.initiative_requests_admin` |
| `/ckan-admin/initiative-requests/<id>/process` | POST | `controller.MyLogica.initiative_request_process_view` |

### Templates
- `templates/initiatives/request.html` — formulario usuario (multipart/form-data)
- `templates/admin/initiative_requests.html` — panel admin con tabs pending/history
- `templates/initiatives/index.html` — agrega CTA visible si `c.userobj`
- `templates/header.html` — badge sysadmin con ícono `fa-flag` y conteo

### Helpers
Definidos en `helpers.py`, registrados en `plugin.py:get_helpers()`:
- `get_pending_initiative_requests_count()` — para badge sysadmin (devuelve 0 si no es sysadmin)
- `get_my_pending_initiative_request()` — para CTA en `/initiatives` (estado de la solicitud del usuario actual)

### Auth
Definidas en `auth.py`, registradas en `plugin.py:get_auth_functions()`:
- `initiative_request_create` — autenticado
- `initiative_request_list` / `initiative_request_process` — `_sysadmin_only` (helper compartido)
- `initiative_request_count` — autenticado

## Flujo end-to-end

```
┌──────────────────────────────────────────────────────────────┐
│ Usuario autenticado                                          │
└──────────────────────────────────────────────────────────────┘
   │
   │ 1. Visita /initiatives → ve CTA "Request a new initiative"
   │    (CTA condicionado a c.userobj y a no tener solicitud pendiente)
   ▼
   /initiatives/request (GET) → formulario
   │
   │ 2. POST con title, description, logo_upload (file)
   ▼
   controller.request_initiative()
   │ → actions.initiative_request_create()
   │   ├─ Valida que no exista pending del mismo usuario
   │   ├─ utils.get_invalid_user_image_upload_reason() — MIME + magic bytes
   │   ├─ ckan.lib.uploader.get_uploader('initiative_requests') — guarda en uploads/
   │   ├─ munge_name(title) → slug propuesto
   │   └─ INSERT initiative_request (status=pending)
   │ → mailer.mail_user() a todos los sysadmins
   ▼
┌──────────────────────────────────────────────────────────────┐
│ Sysadmin                                                     │
└──────────────────────────────────────────────────────────────┘
   │
   │ 3. Ve badge fa-flag con número en cabecera (sólo si _ir_count > 0)
   │    → helpers.get_pending_initiative_requests_count()
   ▼
   /ckan-admin/initiative-requests (GET) → panel con tabs
   │
   │ 4a. Aprueba (puede ajustar el slug en el formulario)
   ▼
   POST /ckan-admin/initiative-requests/<id>/process?tab=pending
   │ → actions.initiative_request_process(action='approve')
   │   ├─ toolkit.get_action('group_create')(...) — type='group'
   │   ├─ toolkit.get_action('member_create')(capacity='admin') — solicitante
   │   ├─ UPDATE initiative_request SET status='approved', created_group_id=...
   │   └─ Email al usuario con link al grupo creado
   │
   │ 4b. Rechaza con motivo (admin_note)
   ▼
   POST /ckan-admin/initiative-requests/<id>/process?tab=pending
   │ → actions.initiative_request_process(action='reject')
   │   ├─ UPDATE initiative_request SET status='rejected', admin_note=...
   │   └─ Email al usuario con el motivo
```

## Patrones reutilizados

| Pieza | Patrón fuente |
|---|---|
| Modelo con `status`+`handled_*` | [[Modulos#MembershipRequest]] |
| Acciones create/list/process/count | `actions.py:membership_request_*` |
| Auth sysadmin-only | `auth.py:_sysadmin_only` (helper compartido) |
| Badge sysadmin en header | `header.html` patrón inline-style de `colab` y `thingsboard` |
| Subida de imagen validada | `utils.py:get_invalid_user_image_upload_reason` + `ckan.lib.uploader` (igual que `featured_publications_upload_image`) |
| Plantilla admin con tabs | `templates/organization/membership_requests.html` (clases `.membership-tab-btn`, `.membership-request-card`, etc.) |

> [!tip] Storage de logos
> Los logos quedan en `storage/uploads/initiative_requests/` (`ckan.lib.uploader.get_uploader('initiative_requests')`). La URL pública se construye con `h.url_for_static('uploads/initiative_requests/<filename>')`.

## i18n

Los strings del feature están marcados con `{% trans %}` / `_()` en templates y `toolkit._()` en Python. Para regenerar el catálogo (CKAN venv):

```bash
python setup.py extract_messages
python setup.py update_catalog
# editar es/LC_MESSAGES/ckanext-theme_ejemplo.po con traducciones
python setup.py compile_catalog
```

## Notas operativas

- La tabla `initiative_request` se crea automáticamente al cargar el plugin (`plugin.configure()` llama a `init_initiative_requests_db()`). Es idempotente.
- Si al aprobar el slug colisiona con un grupo existente, `group_create` lanza `ValidationError`; el sysadmin puede editar el campo `Slug` en el panel y reintentar.
- El feature **no envía notificación push**; solo emails (vía `ckan.lib.mailer.mail_user`). Si fallan los emails, el flujo continúa y queda en logs.

## Pendientes / mejoras

> [!note] Inferencia
> - No hay endpoint para que un usuario **vea el historial** de sus propias solicitudes (rechazadas, etc.). Si se necesita, agregar `/user/<id>/initiative-requests` similar al patrón de tabs de perfil.
> - No hay paginación en el panel admin; con muchas solicitudes podría hacerse lento. Agregar `limit`/`offset` a `initiative_request_list` si crece.
