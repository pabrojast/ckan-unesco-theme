# Módulos

> Detalle de cada módulo Python en `ckanext/theme_ejemplo/`.

---

## plugin.py (~1,274 líneas)

**Rol**: Clase principal del plugin. Punto de entrada de CKAN.

**Clase**: `ThemeEjemploPlugin`

### Interfaces implementadas
- `IConfigurer` — `update_config()`: registra templates, public dir, fanstatic
- `IBlueprint` — `get_blueprint()`: registra 30+ rutas Flask
- `ITemplateHelpers` — `get_helpers()`: expone ~30 funciones helper
- `IPackageController` — `before_dataset_index()`: pipeline espacial + facetas
- `ITranslation` — `i18n_directory()`, `i18n_locales()`, `i18n_domain()`: i18n
- `IActions` — `get_actions()`: registra acciones custom
- `IAuthFunctions` — `get_auth_functions()`: registra funciones de autorización
- `IClick` — `get_commands()`: registra comandos CLI (ver [[#cli.py]])
- `IMiddleware` — `make_middleware()`: registra los hooks Flask del [[Modulos#cache.py|caché de respuestas anónimas]]

### Caches definidos a nivel de módulo
- `_courses_cache` — cursos UNESCO
- `_member_states_cache` — estados miembros
- `_initiatives_cache` — iniciativas
- `_recently_added_datasets_cache` — datasets recientes
- `_recently_added_documents_cache` — documentos recientes
- `http_session` — `requests.Session()` compartida

### Métodos de instancia con @lru_cache
- `_get_featured_datasets_filtered_cached(cache_buster)` — datasets destacados filtrados
- `_get_site_statistics_cached(cache_buster)` — estadísticas del sitio

---

## controller.py (~2,896 líneas)

**Rol**: Todas las funciones de vista Flask.

**Clase**: `MyLogica` (métodos estáticos)

### Categorías de vistas (67 funciones)

**Portales** (11 funciones):
`initiatives()`, `redirect_to_group()`, `memberstates()`, `thematicbuilder()`, `ihpix()`, `ihpix_outputs()`, `ihpix_report()`, `ihpix_dashboard()`, `iot_portal()`, `flood_drought_portal()`, `citizen_science_portal()`

**Directorio de personas** (1):
`people_index()` — con filtros: q, country, organization, expertise

**Vistas de organización** (5):
`organization_people()`, `organization_publications()`, `organization_news()`, `organization_events()`, `organization_data_stories()`

**Vistas de grupo** (5):
`group_members()`, `group_news()`, `group_events()`, `group_publications()`, `group_data_stories()`

**Vistas de usuario** (5):
`user_documents()`, `user_organizations()`, `user_data_stories()`, `user_news()`, `user_events()`

**Membresías** (3):
`request_membership()`, `membership_requests()`, `membership_requests_overview()`

**Solicitudes de iniciativas** (3):
`request_initiative()`, `initiative_requests_admin()`, `initiative_request_process_view()` — ver [[Solicitudes de Iniciativas]]

**Dataset** (2):
`dataset_resources_ajax()`, `dataset_read()`

**Admin** (35 funciones):
Ver [[Flujos Importantes#Paneles de administración]] para la lista completa.

### Funciones auxiliares del módulo
- `timed_lru_cache(seconds, maxsize)` — decorador de cache TTL
- `get_member_states_groups()` — cache de subgrupos (query DB directo)
- `get_all_groups_cached()` — cache de todos los grupos
- `_get_pages_by_initiative()` — consulta extensión Pages
- `_get_pages_by_organization()` — consulta extensión Pages
- `_get_data_stories_by_group()` — consulta data stories

---

## actions.py (~1,879 líneas)

**Rol**: Acciones CKAN custom y overrides.

### Acciones por categoría (45 acciones)

**Overrides de CKAN core** (2):
- `user_show` — expone campos extendidos de `plugin_extras`
- `user_update` — guarda campos extendidos en `plugin_extras`

**Personas y organizaciones** (2):
- `people_list` — búsqueda de usuarios con filtros
- `organization_people` — miembros de org con perfiles

**Solicitudes de membresía** (4):
- `membership_request_create`, `membership_request_list`, `membership_request_process`, `membership_request_count`

**Solicitudes de iniciativas** (4):
- `initiative_request_create`, `initiative_request_list`, `initiative_request_process`, `initiative_request_count` — ver [[Solicitudes de Iniciativas]]

**Datasets destacados** (3):
- `featured_dataset_list`, `featured_dataset_add`, `featured_dataset_remove`

**Publicaciones destacadas** (6):
- `featured_publication_list`, `featured_publication_create`, `featured_publication_update`, `featured_publication_delete`, `featured_publication_reorder`, `featured_publication_import_legacy`

**Portal cards** (5):
- `portal_card_list`, `portal_card_create`, `portal_card_update`, `portal_card_delete`, `portal_card_reorder`

**Bug tickets** (5):
- `bug_ticket_create`, `bug_ticket_list`, `bug_ticket_show`, `bug_ticket_update`, `bug_ticket_api_list`

**Admin de usuarios** (8):
- `admin_user_list`, `admin_user_create`, `admin_user_reset_password`, `admin_user_request_password_reset`, `admin_user_delete`, `admin_user_purge`, `admin_user_reactivate`, `admin_user_toggle_sysadmin`

**IHP-IX contenido** (2):
- `ihpix_content_list`, `ihpix_content_update`

**IHP-IX actividades** (5):
- `ihpix_activity_list`, `ihpix_activity_show`, `ihpix_activity_create`, `ihpix_activity_update`, `ihpix_activity_delete`

**IHP-IX reportes** (4):
- `ihpix_report_submit` — captura formulario PDF 2026 completo (6 secciones, gates Y/N, lista JSON multi-select). Soporta `save_as_draft=1`.
- `ihpix_report_review` — approve/reject por sysadmin.
- `ihpix_dashboard_stats` — público; KPI cards + breakdowns base para `/ihpix/dashboard`.
- `ihpix_admin_overview_stats` — **sysadmin only**; metrics extendidas para `/ckan-admin/ihpix/overview`: KPI targets totals (Σ + youth/female), breakdowns por flagship/CTWG/institution_type, completeness histogram, recent pending.

**Taxonomías centralizadas** (nuevo módulo `ihpix_constants.py`, 2026-05):
`PRIORITY_AREAS` (5), `OUTPUTS` (34, dict por PA), `FLAGSHIPS` (15), `REGIONS` (7),
`CROSS_CUTTING_WGS` (3), `LEAD_INSTITUTION_TYPES` (12), `KNOWLEDGE_PRODUCT_TYPES` (7),
`SCIENTIFIC_PRODUCT_TYPES` (4), `KNOWLEDGE_ACTIVITY_TYPES` (5), `TRAINING_TYPES` (4),
`STAKEHOLDER_GROUP_TYPES` (9), `BIENNIA` (4: 2022-2023 → 2028-2029),
`MEMBER_STATES` (195 ISO-2), `KPIS` (8 con metadata para tablas).
Helpers: `is_valid_*`, `normalize_bool`, `filter_valid`.

**IHP-IX GeoJSON y datos geográficos** (3):
- `ihpix_geojson` — GeoJSON FeatureCollection de países con coordenadas y datos por PA. Filtro: `region`
- `ihpix_activity_geojson` — GeoJSON de actividades geolocalizadas via coordenadas de país. Filtros: `priority_area`, `output`, `biennium`, `country`, `flagship`, `region`
- `ihpix_country_summary_list` — Datos tabulares de países. Filtro: `region`

---

## helpers.py (~661 líneas)

**Rol**: Funciones helper independientes para templates Jinja2.

### Funciones por categoría (25 funciones)

**Tracking y analíticas** (9):
`_is_tracking_enabled()`, `_get_tracking_cache_ttl()`, `_invalidate_tracking_cache_if_expired()`, `_ensure_materialized_views()`, `get_dataset_tracking()`, `get_resource_downloads()`, `get_tracking_totals()`, `get_popular_datasets()`, `get_popular_resources()`

**Paginación** (1):
`get_paged_resources(package_id, page, items_per_page, q, format_filter)`

**Formato de contenido** (1):
`markdown_excerpt(text, length, killwords, end)`

**Personas y organizaciones** (5):
`get_user_profile()`, `get_people_directory()`, `get_org_members_with_profiles()`, `get_org_statistics()`, `get_org_publications()`

**Permisos** (4):
`is_org_member()`, `is_org_admin()`, `get_user_organizations()`, `get_user_admin_orgs()`

**Estados miembros** (2):
`get_country_list()`, `get_member_state_title()`

**Membresías** (2):
`get_pending_membership_requests_count()`, `has_pending_membership_request()`

**Solicitudes de iniciativas** (2):
`get_pending_initiative_requests_count()` (sysadmin badge), `get_my_pending_initiative_request()` (CTA en `/initiatives`)

**Contenido destacado** (2):
`get_featured_publications()`, `get_open_bug_tickets_count()`

### Cache interno
- `_tracking_cache` — dict con claves: dataset, resource, totals, popular, popular_resources, expires
- TTL configurable vía `ckanext.theme_ejemplo.tracking_cache_ttl`
- Vistas materializadas de PostgreSQL para estadísticas de tracking

---

## model.py (~1,141 líneas)

**Rol**: Modelos SQLAlchemy para tablas custom.

### Modelos (6)

**MembershipRequest**: Solicitudes de membresía a organizaciones
- Campos: id, user_id, organization_id, message, status (pending/approved/rejected), handled_by, handled_at, admin_note, role, created_at
- Métodos: `get()`, `get_pending_for_org()`, `get_for_org()`, `get_pending_for_user_and_org()`, `count_pending_for_orgs()`

**FeaturedPublication**: Publicaciones destacadas en homepage
- Campos: id, title, link, description, image_url, display_order, created_at
- Métodos: `get()`, `get_all()`, `as_dict()`

**BugTicket**: Tickets de errores reportados por usuarios
- Campos: id, user_id, title, description, url, image_filename, browser_info, log_snapshot, status (open/in_progress/resolved_by_user/resolved_by_admin), admin_notes, resolved_by, resolved_at, created_at, updated_at
- Métodos: `get()`, `get_all()`, `as_dict()`

**PortalCard**: Tarjetas configurables para portales temáticos
- Campos: id, portal_id (flood_drought/iot/citizen_science), title, link, description, image_url, display_order, is_coming_soon, is_archived, created_at
- Métodos: `get()`, `get_by_portal()`, `get_active_by_portal()`, `as_dict()`
- Auto-seed: 27 tarjetas por defecto

**IhpixContent**: Contenido editable del portal IHP-IX
- Campos: id, section_type, section_key (unique), title, description, content (JSON), created_at, updated_at
- Métodos: `get()`, `get_by_key()`, `get_by_type()`, `get_all()`, `as_dict()`
- section_types: `cta_card`, `priority_area`, `hero`, `section_header`
- section_keys: `cta_1`–`cta_3`, `pa_1`–`pa_5`, `hero`, `section_pa`, `section_metrics`, `section_cta`
- Auto-seed: 12 secciones por defecto (8 originales + 4 nuevas: hero, section headers)
- Auto-migración: `_ensure_new_ihpix_sections()` agrega secciones nuevas (hero, section_header) a instancias existentes

**IhpixActivity**: Actividades del programa IHP-IX
- Campos base: id, title, priority_area, description, output, stakeholders (JSON), partner_organizations, start_date, end_date, status (planned/ongoing/completed), responsible_party, responsible_country, url, country_stats (JSON), created_at, updated_at
- Campos expandidos (v2): biennium, flagships (JSON), regions (JSON), member_states (JSON), original_id, stakeholders_knowledge, stakeholders_awareness, knowledge_products, scientific_products, training_materials, among others (30+ columnas)
- Métodos: `get()`, `get_by_priority_area()`, `get_published()`, `get_all()`, `get_pending()`, `get_facets()`, `get_stats()`, `get_timeline()`, `get_country_stats()`, `as_dict()`
- Auto-migración: `_migrate_ihpix_activities()` agrega columnas nuevas a tablas existentes

**IhpixCountrySummary**: Datos geográficos agregados por país para GeoJSON y dashboard IHP-IX
- Campos: id, country, latitude, longitude, region, total_activities, pa1_count–pa5_count, transboundary_all, transboundary_pa1–pa5, supporting_all, supporting_pa1–pa5, flagship_data (JSON), pa_output_data (JSON), created_at, updated_at
- Métodos: `get()`, `get_by_country()`, `get_all(region)`, `get_as_geojson(region)`, `delete_all()`, `as_dict()`

**InitiativeRequest**: Solicitudes de creación de iniciativas (grupos CKAN) enviadas por usuarios
- Campos: id, user_id, title, name (slug), description, logo_url, status (pending/approved/rejected), handled_by, handled_at, admin_note, created_group_id, created_at
- Métodos: `get()`, `get_pending()`, `get_all(status)`, `get_pending_for_user()`, `count_pending()`, `as_dict()`
- Ver flujo en [[Solicitudes de Iniciativas]]

### Inicialización
Cada modelo tiene `init_*_db()` y `define_*_table()`. Son idempotentes (verifican schema con inspector). Incluyen lógica de migración para agregar columnas nuevas a tablas existentes (e.g., `_migrate_ihpix_activities()`).

---

## auth.py (~254 líneas)

**Rol**: Funciones de autorización para acciones custom.

### Patrones de autorización

| Patrón | Acciones |
|---|---|
| **Sysadmin only** | featured_dataset_*, featured_publication_*, portal_card_*, admin_user_*, ihpix_content_*, ihpix_activity_create/update/delete, ihpix_report_review, bug_ticket_api_list |
| **Autenticado** | membership_request_create, membership_request_count, initiative_request_create, initiative_request_count, bug_ticket_create/list/show/update, ihpix_report_submit |
| **Admin de org o sysadmin** | membership_request_list, membership_request_process |
| **Sysadmin only (iniciativas)** | initiative_request_list, initiative_request_process |
| **Público** | ihpix_activity_list, ihpix_activity_show, ihpix_dashboard_stats, ihpix_geojson, ihpix_activity_geojson, ihpix_country_summary_list |

### Función helper
- `_sysadmin_only(context, data_dict)` — verifica `context['auth_user_obj'].sysadmin`

---

## validators.py (~89 líneas)

**Rol**: Validadores para campos de perfil de usuario extendido.

| Validador | Input | Output | Comportamiento |
|---|---|---|---|
| `user_profile_field` | string | string | Strip whitespace, Missing/None → "" |
| `user_expertise_areas` | list, JSON string, o CSV | JSON array string | Normaliza a JSON array, default `[]` |
| `user_social_links` | dict o JSON string | JSON dict string | Filtra a claves permitidas (linkedin, twitter, researchgate, github, website), elimina vacíos, default `{}` |

---

## utils.py (~273 líneas)

**Rol**: Validación y detección de imágenes para uploads de usuario.

### Constantes
- **Extensiones permitidas**: PNG, JPG, JPEG, JPE, JFIF, GIF, WEBP, BMP, TIF, TIFF, AVIF
- **MIME types permitidos**: image/png, image/jpeg, image/gif, image/webp, image/bmp, image/tiff, image/avif
- **Aliases MIME**: image/jpg → image/jpeg, image/pjpeg → image/jpeg, image/x-png → image/png, image/x-ms-bmp → image/bmp

### Funciones principales
- `is_valid_user_image_reference(image_url)` — valida URLs almacenadas de avatar
- `get_invalid_user_image_upload_reason(upload)` — retorna código de error para uploads inválidos
- `normalize_user_image_url(image_url, url_resolver)` — convierte filenames a URLs completas

### Pipeline de detección
1. Verificar extensión del archivo
2. Verificar MIME type declarado (con normalización)
3. Detectar MIME real vía magic bytes del header
4. Fallback: PIL/Pillow para casos no concluyentes

---

## cache.py

**Rol**: Caché de respuestas anónimas para mitigar la "spider trap" de búsquedas con facetas/orden/paginación. Se registra vía `IMiddleware`.

### Comportamiento
- Sólo cachea peticiones `GET`/`HEAD` sin cookie de sesión (`auth_tkt`, `ckan`, `ckan.flask.session`, `session`).
- Sólo cachea respuestas `200` con `Content-Type` text/JSON/XML, sin `Set-Cookie`, sin `Cache-Control: private|no-store`.
- Backend: Redis (vía `ckan.lib.redis.connect_to_redis`) con fallback a un LRU local (max 1000 entradas).
- Clave: `theme_ejemplo:anon_cache:{lang}|{enc}|{method}|{path}?{query_ordenada}`.
- Headers preservados: `Content-Type`, `Content-Encoding`, `Content-Language`, `Vary`.
- Las respuestas servidas/guardadas exponen `X-Anon-Cache: HIT|MISS` (útil para diagnóstico).

### Bypass
- Cookie de sesión presente.
- `?_nocache=1` en query string.
- Header `Cache-Control: no-cache`.
- Path en `anon_cache_exclude_paths` (default: `/api`, `/ckan-admin`, `/user`, `/dashboard`, `/feeds`, `/util`, `/_tracking`, `/membership-requests`, `/bug-tickets`).

> [!warning]
> Por defecto está **desactivado** (`anon_cache_enabled = false`). Activarlo en producción una vez verificado el comportamiento. Ver [[Variables de Entorno#Caché de respuestas anónimas]].

---

## cli.py

**Rol**: Comandos CLI para gestión de datos IHP-IX. Registrado vía interfaz `IClick`.

### Grupo `ihpix`

| Comando | Descripción |
|---|---|
| `ckan ihpix seed-data -f <json>` | Carga actividades y country summaries desde JSON |
| `ckan ihpix seed-data --from-excel <xlsx>` | Genera seed desde Excel y carga directamente |
| `ckan ihpix seed-data` (sin args) | Busca `data/ihpix_seed_data.json` por defecto |
| `--append` | Flag para agregar sin borrar datos existentes |

### Flujo interno
1. Inicializa tablas (`init_ihpix_activities_db()`, `init_ihpix_country_summary_db()`)
2. Si `--from-excel`: llama `generate_seed()` de `scripts/generate_seed.py`
3. Sin `--append`: elimina actividades con `original_id` y todos los country summaries
4. Itera sobre `activities` y `country_summaries` del JSON, crea registros en DB

---

## scripts/generate_seed.py

**Rol**: Script de conversión Excel → JSON para el pipeline de datos IHP-IX.

**Función principal**: `generate_seed(excel_path)` — lee archivo Excel con datos de Priority Areas, genera estructura JSON con `activities` (744) y `country_summaries` (205 países con coordenadas).

**Uso directo**: `cd ckanext/theme_ejemplo && python scripts/generate_seed.py`

**Archivo de salida**: `ckanext/theme_ejemplo/data/ihpix_seed_data.json`

---

## Ver también

- [[Arquitectura]] — Diseño general y relaciones
- [[Flujos Importantes]] — Flujos de negocio
- [[Estructura del Repo]] — Organización de archivos
