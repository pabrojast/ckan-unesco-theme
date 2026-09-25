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
- `IMiddleware` — `make_middleware()`: registra los hooks Flask del [[Modulos#pageview_tracking.py|conteo liviano de vistas]] (primero) y del [[Modulos#cache.py|caché de respuestas anónimas]]

### Caches definidos a nivel de módulo
- `_courses_cache` — cursos UNESCO (micro-caché de la lectura de BD; la API se consume en [[Modulos#openlearning.py|openlearning.py]])
- `_member_states_cache` — estados miembros
- `_initiatives_cache` — iniciativas
- `_recently_added_datasets_cache` — datasets recientes
- `_recently_added_documents_cache` — documentos recientes

> [!note]
> La antigua `http_session` compartida de plugin.py se eliminó (2026-06): la única llamada HTTP externa (cursos) vive ahora en [[Modulos#openlearning.py|openlearning.py]] con sesión propia.

### Métodos de instancia con @lru_cache
- `_get_featured_datasets_filtered_cached(cache_buster)` — datasets destacados filtrados
- `_get_site_statistics_cached(cache_buster)` — estadísticas del sitio

---

## controller.py (~3,960 líneas)

**Rol**: Todas las funciones de vista Flask.

**Clase**: `MyLogica` (métodos estáticos)

### Categorías de vistas (72 funciones)

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

**Admin** (40 funciones):
Ver [[Flujos Importantes#Paneles de administración]] para la lista completa.

De ellas, 5 son el panel de visores destacados —`featured_viewers_admin`,
`_search`, `_add`, `_remove`, `_reorder`— apoyadas en los auxiliares
`_fv_admin_guard`, `_fv_anon_context`, `_fv_card`, `_fv_patch` y
`_fv_featured_list`. No tocan ninguna tabla de este repo: hablan con las
acciones de **ckanext-pages**. Ver la advertencia en
[[Flujos Importantes#Paneles de administración]].

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

**Visores destacados** (0):
- **Ninguna acción ni auth propia**. El panel `/ckan-admin/featured-viewers`
  consume `featured_viewer_list` / `_show` / `_update` de **ckanext-pages**.
  Registrar aquí un nombre `featured_viewer_*` haría fallar el arranque de CKAN.

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
- `ihpix_activity_list` acepta `priority_area, output, q, biennium, country, region, flagship, organization, ctwg, status` (este último solo sysadmin; el resto siempre ve `published`). Usa `IhpixActivity.get_filtered()`.

**IHP-IX reportes** (8) — workflow completo en [[Flujos Importantes#7. Portal IHP-IX]]:
- `ihpix_report_submit` — crea un reporte desde el formulario PDF 2026 (6 secciones, gates Y/N, listas JSON). `save_as_draft=1` → `draft` (solo exige título); si no → `pending`. La validación vive en [[Modulos#ihpix_forms.py]]. Guarda `reported_by` = **id** de usuario.
- `ihpix_report_update` — edita y (re)envía un reporte propio (`draft`/`rejected`) o cualquiera (sysadmin; un `published` se corrige sin volver a la cola). Payload completo del form + `id`.
- `ihpix_report_show` — propietario o sysadmin; devuelve `as_dict()` + `form` (prefill) + `reporter` + `can_edit`.
- `ihpix_report_delete` — propietario solo `draft`; sysadmin cualquiera.
- `ihpix_my_reports_list` — reportes del usuario autenticado con `counts_by_status`.
- `ihpix_report_review` — approve/reject por sysadmin. Valida la transición (`pending → published|rejected`, `rejected → published` para "Re-approve"), exige `review_notes` al rechazar y **envía email** al reportante (best effort, `mailer.mail_user`).
- `ihpix_dashboard_stats` — público; KPI cards + breakdowns base para `/ihpix/dashboard` (incluye `links_by_type`).
- `ihpix_admin_overview_stats` — **sysadmin only**; metrics extendidas para `/ckan-admin/ihpix/overview`: KPI targets totals (Σ + youth/female), breakdowns por flagship/CTWG/institution_type, completeness histogram, recent pending.

**IHP-IX adjuntos** (4) — ver [[Flujos Importantes#7.1 Adjuntos (Sección VII)]]:
- `ihpix_activity_link_list` — adjuntos de una actividad (publicada, o propia / sysadmin).
- `ihpix_activity_link_create` / `ihpix_activity_link_delete` — alta/baja individual (propietario o sysadmin). El formulario **no** los usa: envía `links_json` y `_sync_activity_links()` hace *full replace* dentro de la misma transacción que el reporte.
- `ihpix_link_search` — busca objetos existentes para adjuntar: `kind=publication` (datasets `type:documents`), `dataset`/`output_data` (`type:dataset`) vía `package_search`; `event`/`webinar` → páginas `water-events` de ckanext-pages (`_search_water_events`, devuelve `search_available=False` si la extensión no está); `course` → `OpenLearningCourse.search_public()` (cursos `approved` + disponibles; incluye `can_propose`).
- `ihpix_publication_create` (2026-09-24) — crea una publicación desde IHP-IX: comprueba que el usuario sea editor/admin de la organización (`ihpix_publication_orgs` → `organization_list_for_user(permission='create_dataset')`), valida con [[Modulos#ihpix_publications.py]], lee los campos disponibles del esquema con `scheming_dataset_schema_show` (`ihpix_documents_schema_fields`, con fallback), llama a `package_create` (reintenta con sufijo si el `name` colisiona y **sin `groups`** si CKAN niega el Member State → `warnings`), luego `resource_create` (fichero `upload` o URL; si falla, `package_delete` best effort). Con `activity_id` adjunta vía `ihpix_activity_link_create`; siempre registra `publication_created` en el ledger del workspace del Output. Vista: `POST /ihpix/publications` (`controller.ihpix_publication_create_view`, multipart → JSON `{package, link, attached, warnings}`; 400 `{errors}` mapeados al modal, 403 `reason=no_org`).
- `ihpix_course_propose` (2026-09-24) — propone un curso de Open Learning: `course_url`/`course_id` → `ihpix_links.parse_course_id`; rate limit `ihpix_course_proposals_per_day`; `openlearning.fetch_and_upsert_course` (nuevo → `pending`, guarda `proposed_by/proposed_at/proposal_note`); si ya está `approved` devuelve el adjunto listo; `hidden` → error. Email a sysadmins + cola `open_learning` de la campana + ledger `course_proposed`. Vista: `POST /ihpix/courses/propose` (XHR → JSON; form → redirect + flash; la usa `/courses`).

**Taxonomías centralizadas** (nuevo módulo `ihpix_constants.py`, 2026-05):
`PRIORITY_AREAS` (5), `OUTPUTS` (34, dict por PA), `FLAGSHIPS` (15), `REGIONS` (7),
`CROSS_CUTTING_WGS` (3), `LEAD_INSTITUTION_TYPES` (12), `KNOWLEDGE_PRODUCT_TYPES` (7),
`SCIENTIFIC_PRODUCT_TYPES` (4), `KNOWLEDGE_ACTIVITY_TYPES` (5), `TRAINING_TYPES` (4),
`STAKEHOLDER_GROUP_TYPES` (9), `BIENNIA` (4: 2022-2023 → 2028-2029),
`MEMBER_STATES` (195 ISO-2), `KPIS` (8 con metadata para tablas).
Helpers: `is_valid_*`, `normalize_bool`, `filter_valid`.

**Títulos de Output** (`ihpix_constants`, 2026-09): `OUTPUTS` sigue trayendo solo códigos (DOC-008). `load_output_titles()` lee `data/ihpix_output_titles.json` (`{"1.1": "…"}`) si existe y lo cachea; `output_title(code)`, `output_label(code)` ("1.3 – Título" o solo el código), `priority_area_for_output(code)`. Helpers de template: `h.ihpix_output_title`, `h.ihpix_output_label`, `h.ihpix_priority_area_for_output`.

**IHP-IX descubribilidad y analítica** (2, 2026-09):
- `ihpix_contributor_list` — usuarios con reportes publicados (`GROUP BY reported_by`) con conteos y `reporter` resuelto. Filtros: `q` (nombre), `priority_area`, `output`, `biennium`, `region`, `country`, `flagship`. Autenticado.
- `ihpix_country_summary_recompute` — recalcula `ihpix_country_summary` desde actividades publicadas (`country` opcional). Sysadmin. También corre solo para el país afectado al aprobar un reporte (`ihpix_recompute_on_approve`).
- `ihpix_dashboard_stats` devuelve además `contributors_total`, `top_institutions`, `output_biennium_matrix` y `links_by_type`; acepta `flagship`.

**IHP-IX working groups — piloto** (8, 2026-09) — ver [[Flujos Importantes#7.4 Working groups (workspaces por Output)]]:
- `ihpix_working_group_list` / `ihpix_working_group_show` — workspaces (uno por Output) con conteos de miembros, actividades publicadas, último movimiento, `my_membership` y `can_manage`. Autenticado.
- `ihpix_working_group_update` — título/descripción/settings (lead o sysadmin); `lead_user_id` (id o username; se le crea membresía lead) y `status` (`active|archived`) solo sysadmin.
- `ihpix_working_group_join` — solicita ingreso (`pending`, o `active` si `ihpix_wg_open_join`); reactiva una membresía `removed`; email a los leads.
- `ihpix_working_group_leave` — abandona (un lead activo no puede: debe reasignarlo un sysadmin).
- `ihpix_working_group_member_process` — `approve|reject|remove|set_role|reinstate` sobre `membership_id` (lead o sysadmin). Reglas en `ihpix_workspaces.validate_member_action`; email al afectado.
- `ihpix_working_group_member_list` — miembros; los `pending`/`removed` solo para quien gestiona.
- `ihpix_contribution_list` — feed del ledger por workspace (`working_group_id`, id o código) o por usuario (`user_id`), con actividad y workspace resueltos.
- `people_list` acepta `ihpix_workspace` (código o id) para filtrar el directorio por miembros activos.

**IHP-IX GeoJSON y datos geográficos** (3):
- `ihpix_geojson` — GeoJSON FeatureCollection de países con coordenadas y datos por PA. Filtro `region` sobre el snapshot; con `priority_area`, `biennium`, `output` o `flagship` los conteos se calculan **en vivo** (`IhpixActivity.get_country_counts`) sobre las coordenadas del snapshot
- `ihpix_activity_geojson` — GeoJSON de actividades geolocalizadas via coordenadas de país. Filtros: `priority_area`, `output`, `biennium`, `country`, `flagship`, `region`. Sin el tope de 20 de antes: máximo `ckanext.theme_ejemplo.ihpix_geojson_max` (5000)
- `ihpix_country_summary_list` — Datos tabulares de países. Filtro: `region`

**Cursos Open Learning** (4) — ver [[Open Learning]]:
- `open_learning_course_list` — listado completo para el panel admin, con counts por status y fecha de último sync
- `open_learning_course_set_status` — cambia status de curación (`pending`/`approved`/`hidden`)
- `open_learning_course_set_type` — corrige el tipo (`permanent`/`scheduled`) con override manual; `reset_override` vuelve a la auto-detección
- `open_learning_sync` — fuerza sincronización con la API

---

## ihpix_forms.py

**Rol**: Validación y normalización del formulario de reporte IHP-IX (PDF 2026). Módulo **puro** (sin imports de CKAN, como `completeness.py`) para testearlo con pytest sin la pila CKAN (`tests/test_ihpix_forms.py`).

- `validate_report_payload(data_dict, is_draft)` → dict `{columna: valor}` listo para `setattr` sobre `IhpixActivity`: listas → JSON, `'yes'/'no'` → bool, fechas → `date`, hijos de un gate en "no" reseteados (`GATE_RESETS`). Lanza `ReportValidationError` con **todos** los errores a la vez. Valida también `output` ∈ PA (`is_valid_output_for_pa`) y el email del focal point al enviar.
- Reglas añadidas en el pase UX (2026-09-24): `LONG_TEXT_MAX` (title 300, partners 500, key_activity 1000, synergies 1500, additional_notes 3000, `*_other` 150, `stakeholder_group_name` 200), `link` debe ser URL http(s) (`URL_RE`), `end_date ≥ start_date`, jóvenes/mujeres ≤ total en KPI 2 y 5 (`STAKEHOLDER_RATIOS`, solo con el gate activo) y email con `EMAIL_RE`. El formulario pone los mismos `maxlength` y valida en vivo; el servidor es la autoridad.
- **Mensajes traducibles**: `MESSAGES = {clave: 'Texto inglés {param}'}`; `ReportValidationError(errors, details)` expone `.errors` (inglés, compatibilidad) y `.details = {campo: (clave, params)}`. `actions._ihpix_translate_errors()` hace `toolkit._(MESSAGES[clave]).format(**params)` antes de lanzar `ValidationError`. Los literales están en `ihpix_i18n_strings.VALIDATION_MESSAGES` (test de cobertura en `test_ihpix_constants.py`).
- `activity_to_form_dict(activity_dict)` → inverso para el modo edición (bool → `'yes'/'no'`, JSON → lista, None → `''`).
- Listas que comparte con el controller: `SINGLE_FORM_FIELDS`, `MULTI_FORM_FIELDS` (única fuente de nombres de campo del form), `BOOL_FIELDS`, `OWNER_EDITABLE_STATUSES = ('draft', 'rejected')`.
- Las fechas solo se tocan si vienen en el payload (`reported_date` la fija el servidor al enviar).

---

## ihpix_links.py

**Rol**: Adjuntos de un reporte IHP-IX (publicaciones, webinars, eventos, datasets). Módulo **puro**, testeado en `tests/test_ihpix_links.py`.

- `LINK_TYPES` = publication · webinar · event · dataset · output_data · **course** · other; `TARGET_KINDS` = package (dataset CKAN, `target_id` = id) · page (página `water-events`, `target_id` = name) · **course** (`OpenLearningCourse`, `target_id` = `course_id` de Open edX; URL `COURSE_URL_TEMPLATE`) · url (enlace plano). `TYPE_ICONS` centraliza los iconos (helper `h.ihpix_link_type_icon`); `parse_course_id(url)` extrae `course-v1:…` de una URL de Open Learning.
- `ALLOWED_KINDS` — coherencia tipo↔kind (una publicación no puede apuntar a una page; un evento no a un package). `SEARCH_KIND_FOR_TYPE` — qué busca cada tipo en IHP-WINS.
- `parse_links_json(raw)` (tolerante con `''`/`[]`), `validate_link(d)` (título ≤300, URL http(s) obligatoria en `url`, `event_date` ISO, descripción ≤500), `link_public_url(link)` (`/documents/<id>`, `/dataset/<id>`, `/water-events/<name>` o la URL), `dedupe_key(link)`.
- `LinkValidationError(errors, details)` con el mismo esquema `MESSAGES`/`.details` que `ihpix_forms` (se traduce en `actions._ihpix_translate_errors`).

> [!note] Creación inline
> Este módulo sigue sin crear objetos CKAN; la creación inline de **publicaciones** vive en `ihpix_publications.py` + `actions.ihpix_publication_create` (2026-09-24). Datasets y eventos siguen abriéndose en su formulario propio (otra pestaña, sin `came_from`).

---

## ihpix_publications.py

**Rol**: Reglas del modal "Upload a publication" (reporte, workspaces y páginas por Output). Módulo **puro**, testeado en `tests/test_ihpix_publications.py`.

- `validate_publication_input(form, allowed_org_ids, max_upload_mb, upload_filename, upload_size)` → dict limpio (título ≤300, organización ∈ permitidas, `document_type` ∈ `DOCUMENT_TYPES` (13 valores del esquema `documents`, default `other`, `educational_material` para KPI 3), año 1900–2100, DOI `^10\.\d{4,9}/\S+$` (acepta URL doi.org), resumen ≤2000 Markdown, autores "Nombre; Afiliación" por línea → `authors_json`, palabras clave, fuente `file` (extensiones `ALLOWED_EXTENSIONS`, tamaño ≤ `ihpix_upload_max_mb`) o `url`). `MESSAGES` + `PublicationValidationError(errors, details)` como en `ihpix_forms`.
- `build_package_dict(clean, schema_field_names, defaults, name, identifier)` — payload de `package_create` **filtrado por los campos que existen en el esquema instalado** (`dev210` = 29 campos, `production` = 13): `type='documents'`, `title_translated={'en'}`, `notes_translated`, `owner_org`, `access_level='public'`, `language` (default ENG), `identifier=uuid4` (el validador `schemingdcat_clean_identifier` **no** lo autogenera), `contact_email` (del usuario), `tag_string`/`tags` (siempre `ihp-ix` + `ihp-ix-output-<code>`), `groups` (Member State / Iniciativa).
- `build_resource_dict(clean, resource_field_names, package_id)` (`url_type='upload'` + `format` por extensión, o URL), `map_schema_errors(error_dict)` (campo del esquema → campo del modal; el resto a `__all__`), `slugify_title(title, taken)`, `parse_authors`, `parse_keywords`, `link_item_for_package(pkg)` (adjunto listo para la Sección VII), `prefilled_dataset_url(...)` (query string de `/dataset/new`).

---

## ihpix_workspaces.py

**Rol**: Reglas del piloto de working groups. Módulo **puro** (`tests/test_ihpix_workspaces.py`).

- Constantes: `ROLES` (lead / contributor / observer), `MEMBER_STATUSES` (pending / active / removed), `WG_STATUSES` (active / archived), `CONTRIBUTION_KINDS` (report_submitted, report_published, link_added, **publication_created**, **course_proposed**, member_joined, comment — este último sin UI) + `CONTRIBUTION_ICONS` (helper `h.ihpix_contribution_icon`), `MEMBER_ACTIONS` (acción → estados de origen y destino).
- `can_manage(wg, user_id, membership, is_sysadmin)` — sysadmin, `lead_user_id` o miembro lead activo.
- `validate_member_action(membership, action, actor_user_id, actor_can_manage, role)` → `(new_status, new_role)`; un lead no puede quitarse ni degradarse a sí mismo.
- `validate_join(wg, membership)` — workspace activo y sin membresía pendiente/activa; devuelve `True` si hay que reactivar una `removed`.
- `resolve_join_status(open_join)`, etiquetas (`role_label`, `contribution_label`, `member_status_label`), `workspace_title(code, title)`.

---

## Kit de formularios IHP-IX (`public/js/ihpix-forms.js` + `public/css/ihpix-forms.css`)

**Rol**: componentes de UI reutilizables en vanilla JS (sin jQuery ni dependencias nuevas), opt-in por atributos `data-ihpix-*`. Se cargan con las macros de `templates/ihpix/snippets/forms_assets.html` (`forms_styles()` + `forms_scripts()`, que inyecta cadenas traducidas y la URL del preview en `#ihpix-forms-i18n`). Bundle webassets `theme/ihpix-forms-js`.

| Componente | Opt-in | Notas |
|---|---|---|
| `MarkdownEditor` | `textarea[data-ihpix-markdown]` | barra (negrita, cursiva, título, listas, enlace; Ctrl+B/I/K), pestañas Write/Preview (`POST /ihpix/markdown-preview`), inserta con `setRangeText` y dispara `input` |
| `Combobox` | `select[data-ihpix-combobox]` · `input[data-ihpix-combobox=remote][data-source-url]` | patrón WAI-ARIA combobox; búsqueda sin diacríticos sobre label + `data-search`; ≤60 filas |
| `MultiPicker` | `[data-ihpix-multipicker][data-value-mode=checkboxes|json]` | buscador + chips + contador sobre checkboxes nativos |
| `CharCounter` | `textarea[maxlength][data-ihpix-counter]` | `n / max`, `aria-describedby`, avisa al 80/95/100 % |
| `Toast` | `window.ihpixToast(msg, type)` | `#ixf-toasts` `role=status`; errores `role=alert` |
| `ConfirmDialog` | `[data-ihpix-confirm="…"]` en form/botón | retira el `onsubmit="return confirm()"` inline (fallback sin JS) |
| `FileUpload` | `[data-ihpix-upload][data-max-mb][data-accept]` | zona botón + drag&drop, `role=progressbar`, validación tamaño/tipo; `IhpixForms.upload()` (XHR con progreso) |
| `Modal` | `.ixf-modal[role=dialog]` + `[data-ihpix-modal-open="#id"]` | focus trap, Esc, backdrop, devuelve el foco |

Principio: **nunca se elimina el control nativo**; se oculta (`.ixf-visually-hidden`) y se sincroniza, de modo que `collectFormData/restoreFormData/highlightServerErrors` del reporte siguen funcionando. `IhpixForms.refresh(root)` relee los valores tras una restauración (lo llama `refreshDerivedUI()` del reporte). Helpers: `csrfToken()`, `postForm()`, `applyFieldErrors()`, `markInvalid()`.

**Dónde se usa (2026-09-24)** — `templates/ihpix/report.html`: `country` y `supporting_member_state` son `Combobox` (búsqueda por nombre e ISO-2 vía `data-search`); Member States (Sección IV) es un `MultiPicker` en modo `checkboxes` (reemplaza el picker a mano, `memberPicker` queda a `null`); `key_activity`, `synergies` y `additional_notes` son `MarkdownEditor` + `CharCounter`; `partners` es textarea con contador; `institution` tiene un `<datalist>` con las instituciones de actividades publicadas (`controller._ihpix_institution_suggestions()`, caché en proceso 10 min, ≤300). Los grupos Sí/No y los grids de checkboxes van en `<fieldset><legend>`; cada `.ihpix-report-help` tiene `id` y el control `aria-describedby`. Sección VII: confirmación al quitar (`IhpixForms.confirm`), flechas ↓/↑ en los resultados, botón "Refresh search" y API pública `window.ihpixLinks = {reload, add, getLinks}`. Autosave por usuario: clave `ihpix-report-draft-v1:<user_id>` (migra la clave global antigua). Los textos Markdown se renderizan con `h.ihpix_markdown()` en `ihpix/outputs.html`, `group|organization/ihpix.html`, `admin/ihpix_reports.html` y la descripción de `ihpix/workspace_detail.html`.

**Formularios admin (fase D, 2026-09-24)** — `admin/ihpix_activities.html`: cabeceras del acordeón como `<button aria-expanded aria-controls>`, `label for` en todos los campos, `country`/`supporting_member_state` con `<datalist>` de Member States (slug como valor, igual que el formulario público), Member States → `MultiPicker` modo `json` (hidden `member_states`), los 5 tipos KPI (`knowledge_product_type`, `scientific_product_type`, `knowledge_activity_type`, `training_type`, `stakeholder_group_type`) pasan de select único a **grids de checkboxes serializados en JSON** (mismo formato que el reporte; `parseJsonArray` acepta el valor suelto legacy), radios Sí/No para `unesco_secretariat_participation` (el texto `unesco_participation` queda como legacy), `key_activity`/`synergies`/`additional_notes` con Markdown + contador (`notes` = notas internas legacy), `description`/`outcomes` con `maxlength=250`; todos los `fetch` POST pasan por `IhpixForms.postForm` (token CSRF), `alert/confirm` → Toast/ConfirmDialog, modal de edición con `role=dialog`, Esc y devolución del foco. `admin/ihpix_content.html`: CSRF en `fetch`, `label for` generados, drop zones operables con teclado, acordeón con `aria-expanded`. `admin/ihpix_workspaces.html`: HTML válido (un `<form id="ws-form-<id>">` por fila fuera de la tabla y controles con `form=`), descripción en un `Modal` del kit con editor Markdown, lead con `Combobox` remoto sobre `/api/2/util/user/autocomplete`, confirmación al archivar, tabla responsive. `admin/ihpix_reports.html`: aprobación con `ConfirmDialog`, `label for` + contador en las notas de rechazo, CSRF. `ihpix/workspace_members.html` y `workspace_detail.html`: confirmaciones vía `data-ihpix-confirm` (el `onsubmit` inline queda como fallback sin JS), "Set role" desactivado hasta cambiar el valor y confirmación al degradar a un lead, nota de ingreso con placeholder y contador.

> [!note] Bug global corregido (2026-09)
> `public/theme_ejemplo_enhanced.js` `enhanceForms()` bloqueaba el submit de **cualquier** form con un `[required]` vacío añadiendo `.error` (sin CSS ni mensaje). Se retiró ese bloqueo; la validación nativa de `required` ya lo cubre.

---

## ihpix_i18n_strings.py

**Rol**: Lista de literales de las taxonomías (`ihpix_constants`) envueltos en un `_()` no-op para que Babel los extraiga al `.pot`. Los templates traducen los valores en runtime con `h.ihpix_t(valor)`. No se importa desde producción; `tests/test_ihpix_constants.py` comprueba que cubre las constantes.

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

**IHP-IX working groups** (5):
`get_pending_ihpix_wg_members_count()` (cola `ihpix_wg_members` de la campana: pendientes de los workspaces que el usuario lidera; sysadmin todos), `get_user_ihpix_summary(user_id)` (reportes por estado, workspaces activos, contribuciones por tipo; caché 60 s; alimenta el perfil y `/user/<id>/ihpix`), `ihpix_wg_role_label()`, `ihpix_member_status_label()`, `ihpix_contribution_label()`

**IHP-IX UI** (2):
`ihpix_pages_url(endpoint, fallback)` (URL de endpoints de otras extensiones con fallback si el blueprint no está: `pages.water_events_new` → `/water-events_edit`), `ihpix_markdown(text)` (Markdown → HTML saneado con `render_markdown`, envuelto en `.ixf-md-body`), `ihpix_link_type_icon(type)`, `ihpix_link_types()` ([(valor, etiqueta, icono)] para el widget de adjuntos), `ihpix_contribution_icon(kind)`, `get_pending_open_learning_count()` (cola `open_learning` de la campana, solo sysadmin), `ihpix_list_display(value)` (lista JSON o texto legacy de los tipos KPI → 'A, B' traducido; lo usan `ihpix/outputs.html` y las pestañas de grupo/organización)

**IHP-IX** (9):
`get_pending_ihpix_reports_count()` (cola `ihpix_reports` de la campana, sysadmin), `get_ihpix_reporter(reported_by)` → `{id, name, display_name, url}` resolviendo id o username (caché 5 min; texto libre del seed → solo `display_name`), `ihpix_link_url(link)` y `ihpix_link_type_label(link_type)` (adjuntos; usados por el macro `ihpix/snippets/activity_links.html`), `get_ihpix_taxonomies()` (todas las listas de `ihpix_constants` para los `<select>` de los templates: **única fuente**, sustituye las listas hardcodeadas que se habían desincronizado), `ihpix_output_title()`, `ihpix_output_label()`, `ihpix_priority_area_for_output()`, `ihpix_t(valor)` (traducción runtime de valores de taxonomía)

**Contenido destacado** (4):
`get_featured_publications()`, `get_open_bug_tickets_count()`,
`get_featured_viewers(limit=6)` y `featured_viewers_available()` — registrados como
`h.theme_ejemplo_get_featured_viewers` y `h.theme_ejemplo_featured_viewers_available`.

> [!note] Por qué van prefijados
> Las colisiones de nombres de *helpers* entre plugins son **silenciosas** (a
> diferencia de acciones y auth, que revientan el arranque). Como los datos son
> de ckanext-pages, un `get_featured_viewers` sin prefijo se pisaría con el suyo
> el día que lo añada. Ver [[Arquitectura#Paneles de administración]].

> [!note] Caché y sesión ORM
> `get_featured_viewers` consulta Postgres a través de `featured_viewer_list`
> (no Solr, a diferencia de los datasets destacados), así que su `except` llama
> a `_warn_and_rollback_helper_error`: sin el rollback, un fallo dejaría la
> sesión abortada y se caería el resto de la portada. El caché
> (`_featured_viewers_cache`, TTL de `ckanext.theme_ejemplo.home_cache_ttl`) usa
> un contexto **sin usuario**, lo que hace el resultado idéntico para todo el
> mundo y por tanto seguro de compartir.

### Cache interno
- `_tracking_cache` — dict con claves: dataset, resource, totals, popular, popular_resources, expires
- TTL configurable vía `ckanext.theme_ejemplo.tracking_cache_ttl`
- Leen las tablas `tracking_dataset_stats`, `tracking_resource_stats`, `tracking_site_totals` (con fallback a `tracking_raw`). Esas tablas las crea y puebla [[Modulos#pageview_tracking.py]] (conteo liviano); ya **no** son vistas materializadas externas.
- `_is_tracking_enabled()` se enciende con `ckan.tracking_enabled` **o** con `ckanext.theme_ejemplo.pageviews_enabled`.

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
- Auto-migración: `_ensure_new_ihpix_sections()` agrega secciones nuevas (hero, section_header) a instancias existentes; `_migrate_ihpix_cta_links()` cambia el CTA `cta_1` del Microsoft Form externo a `/ihpix/report` (solo si aún apunta a `forms.office.com`)

**IhpixActivity**: Actividades del programa IHP-IX
- Campos base: id, title, priority_area, description, output, stakeholders (JSON), partner_organizations, start_date, end_date, status (planned/ongoing/completed), responsible_party, responsible_country, url, country_stats (JSON), created_at, updated_at
- Campos expandidos (v2): biennium, flagships (JSON), regions (JSON), member_states (JSON), original_id, stakeholders_knowledge, stakeholders_awareness, knowledge_products, scientific_products, training_materials, among others (30+ columnas)
- Gates PDF 2026 (booleanos): `unesco_secretariat_participation`, `has_member_state_support`, `has_flagship`, `has_synergies`, `regions_benefit`, `kpi_{1a,1b,2,3,4,5,6,8}_active`; textos `focal_point_name`, `*_other`, `stakeholder_group_name`, `additional_notes`
- Workflow (2026-09): `submitted_at` (último envío a revisión); `reported_by` guarda el **id** de usuario (antes mezclaba username e id; `_migrate_ihpix_reported_by()` normaliza filas viejas)
- Índices: `idx_ihpix_activity_{status,pa,output,biennium,reported_by}` (`_IHPIX_ACTIVITY_INDEXES`)
- Métodos: `get()`, `get_by_priority_area()`, `get_filtered(status=None, …, limit=None)` (base de listados/export; `get_published()` es `get_filtered(status='published')`), `get_all()`, `get_pending()`, `get_facets()`, `get_stats()` (+ `links_by_type`), `get_timeline()` (por **fecha de la actividad**: `coalesce(start_date, reported_date, created_at)`), `get_country_stats()`, `get_country_counts(filters)`, `count_distinct_reporters()`, `get_contributor_stats(filters, q_text, limit, offset)`, `get_top_institutions()`, `get_output_biennium_matrix()`, `as_dict()` (incluye todos los gates), `get_by_reporter(user_obj, status, limit, offset)`, `count_by_status_for_reporter(user_obj)`, `count_by_status(status)`, `is_owned_by(user_obj)`
- Auto-migración: `_migrate_ihpix_activities()` aplica `_IHPIX_ACTIVITY_ADDED_COLUMNS` con `ADD COLUMN IF NOT EXISTS` + `CREATE INDEX IF NOT EXISTS` dentro de `engine.begin()` (patrón de `init_contribution_scores_db`)

**IhpixActivityLink**: Adjuntos de una actividad IHP-IX (tabla `ihpix_activity_link`, 2026-09)
- Campos: id, activity_id, link_type, target_kind (package/page/url), target_id, title, url, description, event_date, added_by, display_order, created_at. Sin FK (patrón del repo); índices en activity_id, link_type y (target_kind, target_id)
- Métodos: `get()`, `get_by_activity()`, `get_for_activities(ids)` (una query para listados), `count_by_type(filters, status)` (join con actividades publicadas; alimenta `get_stats()['links_by_type']`), `delete_for_activity()`, `as_dict()` (incluye `public_url`)
- Init: `init_ihpix_activity_links_db()` (tupla `_IHPIX_LINK_ADDED_COLUMNS` vacía + `CREATE INDEX IF NOT EXISTS`)

**IhpixWorkingGroup**: Workspace colaborativo por Output IHP-IX (tabla `ihpix_working_group`, 2026-09)
- Campos: id, output_code (**unique**), priority_area, title, description, lead_user_id, status (active/archived), settings (JSON), created_at, updated_at
- Métodos: `get()`, `get_by_output()`, `get_by_id_or_output()`, `get_all(status, priority_area)` (orden natural de códigos), `member_counts(ids)`, `as_dict()`
- Seed: `_seed_ihpix_working_groups()` crea los que falten desde `ihpix_constants.OUTPUTS` (34) en cada arranque, sin tocar los existentes

**IhpixWorkingGroupMember**: Membresía usuario ↔ workspace (tabla `ihpix_working_group_member`)
- Campos: id, working_group_id, user_id, role (lead/contributor/observer), status (pending/active/removed), joined_at, invited_by, note, created_at, updated_at. Índice único `(working_group_id, user_id)`
- Métodos: `get_membership()`, `get_for_group(status)`, `get_for_user(status)`, `count_pending_for_groups(ids)`, `lead_group_ids_for_user()`

**IhpixContribution**: Ledger de participación (tabla `ihpix_contribution`)
- Campos: id, user_id, kind, working_group_id (puede ser ''), activity_id, link_id, meta (JSON), created_at
- Métodos: `get_for_group()`, `get_for_user()`, `counts_for_user()`, `counts_for_group()`, `last_activity_for_groups()`, `exists()` (dedupe)
- Init común: `init_ihpix_working_groups_db()` (3 tablas, índices con `IF NOT EXISTS`, tuplas `_IHPIX_WG_ADDED_COLUMNS` para futuras columnas, seed)

**IhpixCountrySummary**: Datos geográficos agregados por país para GeoJSON y dashboard IHP-IX
- Campos: id, country, latitude, longitude, region, total_activities, pa1_count–pa5_count, transboundary_all, transboundary_pa1–pa5, supporting_all, supporting_pa1–pa5, flagship_data (JSON), pa_output_data (JSON), created_at, updated_at
- Métodos: `get()`, `get_by_country()`, `get_all(region)`, `get_as_geojson(region)`, `delete_all()`, `recompute_from_activities(country=None, resolve_name=None)` (recalcula conteos desde actividades publicadas conservando lat/lng/region; `flagship_data` pasa a `{flagship: n}` y `pa_output_data` a `{'paN_outputs': {code: n}}`), `as_dict()`

**InitiativeRequest**: Solicitudes de creación de iniciativas (grupos CKAN) enviadas por usuarios
- Campos: id, user_id, title, name (slug), description, logo_url, status (pending/approved/rejected), handled_by, handled_at, admin_note, created_group_id, created_at
- Métodos: `get()`, `get_pending()`, `get_all(status)`, `get_pending_for_user()`, `count_pending()`, `as_dict()`
- Ver flujo en [[Solicitudes de Iniciativas]]

**OpenLearningCourse**: Caché persistente curada de cursos UNESCO Open Learning — ver [[Open Learning]]. Desde 2026-09-24 tiene `proposed_by`, `proposed_at`, `proposal_note` (propuestas desde IHP-IX; columnas añadidas con `ADD COLUMN IF NOT EXISTS` en `init_open_learning_courses_db`) y los métodos `search_public(q, limit)`, `count_pending()`, `count_proposed_since(user_id, since)`.
- Campos: id, course_id (unique, de la API), name, org, short_description, image_url, start, end, start_display, pacing, raw_json, course_type (permanent/scheduled), course_type_override, status (pending/approved/hidden), is_available, display_order, first_seen_at, last_seen_at, created_at, updated_at
- Índice compuesto `(status, is_available)` para la query pública
- Métodos: `get()`, `get_by_course_id()`, `get_all()` (pendientes primero), `get_public(course_type, limit)`, `last_sync_at()`, `counts_by_status()`, `as_dict()` (incluye `course_url` calculada)

### Inicialización
Cada modelo tiene `init_*_db()` y `define_*_table()`. Son idempotentes (verifican schema con inspector). Incluyen lógica de migración para agregar columnas nuevas a tablas existentes (e.g., `_migrate_ihpix_activities()`).

### Tablas de conteo liviano (sin ORM)
`init_pageview_tracking_db()` / `define_pageview_tracking_tables()` crean cuatro tablas planas (sin clase `DomainObject`, se leen/escriben por SQL): `tracking_dataset_stats` (dataset_name, total_views, recent_views), `tracking_resource_stats` (resource_id, total_downloads), `tracking_site_totals` (fila única id=1), `tracking_dataset_daily` (dataset_name, day, views — soporte de `recent_views`). Las puebla [[Modulos#pageview_tracking.py]].

---

## auth.py (~254 líneas)

**Rol**: Funciones de autorización para acciones custom.

### Patrones de autorización

| Patrón | Acciones |
|---|---|
| **Sysadmin only** | featured_dataset_*, featured_publication_*, portal_card_*, admin_user_*, ihpix_content_*, ihpix_activity_create/update/delete, ihpix_report_review, ihpix_admin_overview_stats, ihpix_country_summary_recompute, bug_ticket_api_list, open_learning_* |
| **Autenticado** | membership_request_create, membership_request_count, initiative_request_create, initiative_request_count, bug_ticket_create/list/show/update, ihpix_report_submit, ihpix_my_reports_list, ihpix_link_search, ihpix_contributor_list, **ihpix_activity_list, ihpix_activity_show, ihpix_dashboard_stats, ihpix_geojson, ihpix_activity_geojson, ihpix_country_summary_list** (eran públicas hasta 2026-09; la landing `/ihpix` obtiene sus stats en servidor con `ignore_auth`) |
| **Propietario del reporte o sysadmin** | ihpix_report_show, ihpix_report_update, ihpix_report_delete, ihpix_activity_link_create, ihpix_activity_link_delete (`_ihpix_report_owner_or_sysadmin`: compara `reported_by` con id y username; si el reporte no existe autoriza para que la acción devuelva 404) |
| **Publicada, o propietario/sysadmin** | ihpix_activity_link_list |
| **Lead del workspace o sysadmin** | ihpix_working_group_update, ihpix_working_group_member_process (`_ihpix_wg_manager_or_sysadmin`) |
| **Autenticado (working groups)** | ihpix_working_group_list/show/join/leave/member_list, ihpix_contribution_list |
| **Admin de org o sysadmin** | membership_request_list, membership_request_process |
| **Sysadmin only (iniciativas)** | initiative_request_list, initiative_request_process |
| **Público** | _(ninguna acción IHP-IX desde 2026-09)_ |

### Funciones helper
- `_sysadmin_only(context, data_dict)` — verifica `context['auth_user_obj'].sysadmin`
- `_logged_in_only(context, data_dict)` — cualquier usuario autenticado
- `_ihpix_report_owner_or_sysadmin(context, data_dict)` — ver tabla

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

## pageview_tracking.py

**Rol**: Conteo liviano de vistas/descargas — reemplazo de `ckan.tracking_enabled`, que colapsaba la CPU bajo alto tráfico. Se registra vía `IMiddleware` (un `before_request` Flask, espejo de [[Modulos#cache.py]]). Ver el flujo completo en [[Flujos Importantes#Conteo liviano de vistas]].

### Registro (hot path, barato)
- `init_app(app)` registra `_record` como `before_request`, **antes** que el de la caché anónima (Flask corta en el primer hook que devuelve respuesta; así contamos también los HIT de caché).
- `_record()` nunca corta el request. En rutas que matchean dataset/descarga (solo `GET`): filtra bots por `User-Agent`, deduplica por IP+URL (clave Redis TTL) e incrementa contadores en Redis (`HINCRBY`). Sin DB, sin request extra.
- **Gate de navegación para descargas** (`_is_user_download`): solo cuentan navegaciones reales (`Sec-Fetch-Mode: navigate` con dest `document`/`empty`, sin `Range` ni prefetch). Los visores embebidos (Terria, MapLibre, PDF) fetchean `/download` en cada render e inflaban el contador; ahora se descartan antes del dedup (para no quemar la ventana del clic real). Fallback sin `Sec-Fetch-*` (Safari < 16.4): se excluyen los `Referer` de `pageviews_excluded_referrer_hosts`. El `_BOT_RE` cubre además herramientas server-side (`CKAN-TerriaView`, `python-urllib`, `node-fetch`, `okhttp`, …). Kill-switch: `pageviews_downloads_navigation_only = false`.
- Claves Redis (namespace `theme_ejemplo:pv:`): `views` (hash dataset→delta), `downloads` (hash resource→delta), `daily:<fecha>` + set `daily_dates` (para `recent_views`), `seen:<hash>` (dedup), `flush:lock`.

### Volcado (cron)
- `flush_to_db()` toma un lock, hace `RENAME` atómico de los hashes a `*:flush` (los nuevos incrementos van a un hash fresco), y UPSERTea a las tablas `tracking_*`. Recalcula `recent_views` desde `tracking_dataset_daily` (suma últimos N días) y poda buckets viejos.
- `get_status()` reporta pendientes en Redis y totales en Postgres.
- Si Redis no está disponible, el registro es no-op y el serving sigue intacto.

> [!note]
> Por defecto está **desactivado** (`pageviews_enabled = false`). Requiere `ckan.tracking_enabled = false` y un CronJob que corra `ckan pageviews flush` (ver `deploy/cronjob-pageviews-flush.yaml`). Ver [[Variables de Entorno#Conteo liviano de vistas (pageviews)]].

---

## cli.py

**Rol**: Comandos CLI del plugin. Registrado vía interfaz `IClick` (grupos `ihpix`, `openlearning` y `pageviews`).

### Grupo `ihpix`

| Comando | Descripción |
|---|---|
| `ckan ihpix seed-data -f <json>` | Carga actividades y country summaries desde JSON |
| `ckan ihpix seed-data --from-excel <xlsx>` | Genera seed desde Excel y carga directamente |
| `ckan ihpix seed-data` (sin args) | Busca `data/ihpix_seed_data.json` por defecto |
| `--append` | Flag para agregar sin borrar datos existentes |
| `ckan ihpix recompute-summary [--country X] [--dry-run]` | Recalcula `ihpix_country_summary` desde las actividades publicadas (conserva coordenadas). `--dry-run` imprime los conteos por país sin escribir |
| `ckan ihpix seed-workspaces` | Crea los workspaces que falten (uno por Output). Lo mismo ocurre en cada arranque vía `init_ihpix_working_groups_db()` |

### Grupo `openlearning`

| Comando | Descripción |
|---|---|
| `ckan openlearning sync` | Sincroniza la caché curada de cursos con la API de Open Learning |
| `--force` | Ignora el TTL (hoy el comando siempre sincroniza; el TTL aplica al sync lazy) |

Cron sugerido en producción: `0 */6 * * * ckan -c /etc/ckan/default/ckan.ini openlearning sync --force`

### Grupo `pageviews`

| Comando | Descripción |
|---|---|
| `ckan pageviews flush` | Vuelca los contadores de Redis a las tablas `tracking_*` (crea las tablas si faltan). Imprime resumen |
| `ckan pageviews status` | Muestra pendientes en Redis y totales acumulados en Postgres |

Se ejecuta por CronJob de Kubernetes cada ~5 min (ver `deploy/cronjob-pageviews-flush.yaml`). Sin ese cron, los conteos se acumulan en Redis pero no aparecen en la UI. Ver [[Flujos Importantes#Conteo liviano de vistas]].

### Flujo interno
1. Inicializa tablas (`init_ihpix_activities_db()`, `init_ihpix_country_summary_db()`)
2. Si `--from-excel`: llama `generate_seed()` de `scripts/generate_seed.py`
3. Sin `--append`: elimina actividades con `original_id` y todos los country summaries
4. Itera sobre `activities` y `country_summaries` del JSON, crea registros en DB

---

## openlearning.py

**Rol**: Sincronización de cursos de UNESCO Open Learning hacia la caché persistente curada (`open_learning_course`). Ver flujo completo en [[Open Learning]].

### Funciones principales
- `_fetch_all_courses(search_terms)` — fetch paginado por término (sigue `pagination.next`, salta cursos `hidden`, deduplica por `course_id`). Devuelve `(courses_by_id, full_success)`
- `_detect_course_type(api_course)` — `pacing == 'self'` → permanent; `'instructor'` → scheduled; fallback por `start_type`/`end`
- `sync_courses(force)` — upsert transaccional que preserva la curación (nunca toca `status` ni `display_order`); marca `is_available=False` **solo si el fetch fue completo** y tras re-verificar cada curso ausente por ID (`OpenLearningCourse.get_not_in()` + `_fetch_course_by_id`)
- `_fetch_course_by_id(course_id)` — endpoint de detalle `<API>/<course_id>/`; devuelve `None` si 404 o `hidden`, lanza `RuntimeError` si la API falla
- `_course_fields()` / `_apply_api_course()` — mapeo API → columnas de display y refresco de una fila existente (compartidos por el sync y el alta manual)
- `search_courses_api(query)` / `fetch_and_upsert_course(course_id)` — búsqueda y alta manual desde el panel admin
- `maybe_sync_courses()` — gatillo lazy con TTL contra `max(last_seen_at)` en BD + cooldown de 5 min en memoria; nunca lanza excepción

### Notas
- Sesión `requests.Session` propia (timeout `(5, 10)`) para evitar import circular con plugin.py
- API: `https://openlearning.unesco.org/api/courses/v1/courses/` (Open edX courses v1)

---

## search.py

**Rol**: Búsqueda de organizaciones/grupos insensible al orden de las palabras y a los acentos, y utilidades compartidas por los buscadores. Ver [[Busqueda]].

### Funciones principales
- `normalize_text()` / `match_score()` / `filter_ranked()` — matching por tokens (AND, cualquier orden) y puntaje de relevancia. Puras: no importan CKAN, se testean sin entorno
- `get_entity_index()` / `clear_entity_index()` — índice en memoria de `group` activos (TTL 300 s, por proceso)
- `search_entities()` / `search_entity_names()` — búsqueda sobre el índice con filtros `is_organization`, `ckan_type`, `allowed`, `excluded`, `include_description`
- `filter_by_tokens(sa_query, q, columns)` — AND de `ILIKE '%token%'` para tablas grandes (usuarios); escapa `%` y `_`
- `escape_solr()` — neutraliza la sintaxis de Solr en el texto de las sugerencias

### Notas
- Portado de `ckanext-colab/lib/org_search.py`; se copia porque colab es opcional
- Se importa como `theme_search` en `controller.py` y `actions.py` (en `controller.py` el nombre `search` ya es `ckan.lib.search`)

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
