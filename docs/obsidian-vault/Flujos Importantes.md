# Flujos Importantes

> Flujos de negocio clave del sistema `ckanext-theme-ejemplo`.

---

## Controles de los listados del catálogo

El tema controla las acciones de creación en `templates/package/search.html`:
`/dataset/` muestra únicamente **Add Dataset** (`dataset.new`) y `/documents`
muestra únicamente **Add Documents** (`documents.new`). Ambos conservan la
comprobación de permiso `package_create` y las etiquetas traducibles. El override
reemplaza el bloque heredado de `ckanext-schemingdcat`, que ofrece todos los tipos
de contenido registrados.

En `/organization/`, los estilos de `#organization-search-form` en
`public/theme_ejemplo.css` colocan el buscador y **Order by** en una misma fila
en escritorio, con el contador de resultados debajo. En móvil los controles se
apilan. Se mantienen las opciones de orden y el envío de búsqueda existentes.

---

## 1. Indexación de datasets (Pipeline espacial)

**Trigger**: CKAN indexa un dataset en Solr
**Hook**: `before_dataset_index` en `plugin.py`

```
1. CKAN llama before_dataset_index(pkg_dict)
2. Plugin extrae campos extras: xmin, ymin, xmax, ymax
3. Si existen las 4 coordenadas:
   a. Shapely genera: box(xmin, ymin, xmax, ymax)
   b. Convierte a WKT string
   c. Asigna a pkg_dict['spatial_geom']
4. Sanitiza facetas multilingües:
   a. Detecta campos con prefijos de idioma (ej: title_es, title_fr)
   b. Limpia valores que podrían causar errores en Solr atomic update
5. Si index_followers está habilitado:
   a. Cuenta seguidores del dataset
   b. Marca como "featured" si alcanza umbral de admin followers
6. Retorna pkg_dict modificado a Solr
```

---

## 2. Solicitud de membresía a organización

**Ruta**: `/organization/<name>/request-membership`
**Módulos involucrados**: `controller.py`, `actions.py`, `model.py`, `auth.py`

```
1. Usuario visita /organization/<name>/request-membership (GET)
   → controller.py: request_membership() renderiza formulario
2. Usuario envía solicitud con mensaje (POST)
   → actions.py: membership_request_create()
   → model.py: MembershipRequest.create(user_id, org_id, message)
   → Estado: "pending"
3. Admin de la org visita /organization/<name>/membership-requests
   → controller.py: membership_requests() lista solicitudes pendientes
4. Admin aprueba o rechaza
   → actions.py: membership_request_process(id, action="approve"|"reject")
   → Si aprueba: CKAN agrega usuario como miembro de la org
   → Estado: "approved" o "rejected"
```

**Autorización**:
- Crear solicitud: cualquier usuario autenticado
- Listar solicitudes: admin de la org o sysadmin
- Procesar solicitud: admin de la org o sysadmin

---

## 2.1. Solicitud de creación de iniciativa

**Ruta usuario**: `/initiatives/request`
**Ruta admin**: `/ckan-admin/initiative-requests`
**Módulos**: `controller.py`, `actions.py`, `model.py`, `auth.py`, `helpers.py`
**Detalle completo**: ver [[Solicitudes de Iniciativas]]

```
1. Usuario autenticado visita /initiatives o /initiatives/request
   → CTA en /initiatives → formulario en /initiatives/request
2. Sube título + descripción + logo (multipart/form-data)
   → actions.py: initiative_request_create()
   → utils.py: get_invalid_user_image_upload_reason() valida MIME + magic bytes
   → ckan.lib.uploader: guarda logo en uploads/initiative_requests/
   → model.py: InitiativeRequest (status="pending")
   → email a todos los sysadmins
3. Sysadmin ve badge fa-flag con conteo en cabecera
   → helpers.py: get_pending_initiative_requests_count()
4. Sysadmin entra a /ckan-admin/initiative-requests
   → controller.py: initiative_requests_admin() (tabs pending/history)
5. Sysadmin aprueba o rechaza
   → controller.py: initiative_request_process_view() (POST)
   → actions.py: initiative_request_process(id, action)
   → Si aprueba: group_create + member_create(capacity=admin) para el solicitante
   → Email al usuario (aprobación o rechazo + motivo)
```

> [!note] Decisión de diseño
> Las "iniciativas" del portal IHP son grupos CKAN (`type='group'`) que no están bajo `member-states`. Al aprobar, el grupo se crea automáticamente y el solicitante queda como `admin` del grupo (puede editar contenido, agregar miembros, etc.).

---

## 3. Perfil de usuario extendido

**Módulos**: `actions.py`, `validators.py`

```
1. Usuario edita su perfil
2. actions.py: user_update() (override de CKAN core)
   a. Recibe campos estándar de CKAN + campos extendidos
   b. Valida campos con validators.py:
      - user_profile_field: acepta texto, trim whitespace
      - user_expertise_areas: valida JSON list o CSV
      - user_social_links: valida JSON dict con claves permitidas
   c. Serializa campos extendidos a JSON
   d. Almacena en user.plugin_extras['theme_ejemplo']
   e. Si cambió 'country', sincroniza membresía al grupo member-state
3. actions.py: user_show() (override de CKAN core)
   a. Llama user_show original
   b. Extrae campos de plugin_extras['theme_ejemplo']
   c. Los expone como campos de primer nivel en el resultado
```

**Campos extendidos**: `job_title`, `institution`, `country`, `phone`, `website`, `orcid`, `expertise_areas`, `social_links`

---

## 4. Paneles de administración

**Patrón común**: Todas las rutas `/ckan-admin/*` siguen este flujo.

```
1. Verificación de autorización:
   → auth.py: _sysadmin_only() verifica rol sysadmin
   → Si no es sysadmin: abort(403)
2. Renderización del panel:
   → controller.py: renderiza template con datos actuales
   → Templates en templates/admin/
3. Operaciones CRUD vía AJAX:
   → Endpoints separados para create/update/delete/reorder
   → Retornan JSON con resultado
4. Upload de imágenes (publicaciones y portal cards):
   → utils.py: validación de imagen (extensión, MIME, magic bytes)
   → Almacenamiento en directorio público de CKAN
```

> [!warning] Excepción: visores destacados
> `/ckan-admin/featured-viewers` **no** usa `auth._sysadmin_only`, porque no
> puede registrar auth functions con nombres de ckanext-pages sin romper el
> arranque de CKAN. Comprueba `c.userobj.sysadmin` directamente en cada vista
> (`controller.py`, `MyLogica._fv_admin_guard`).
>
> Además, `featured_viewer_update` valida contra un schema donde `title` es
> `not_empty`: un update parcial `{'id', 'is_featured'}` falla con
> *Missing value*. Por eso `MyLogica._fv_patch` relee el visor y reenvía su
> título; el resto de campos del schema son `ignore_missing` y no se tocan.

### Paneles disponibles

| Panel | Modelo de datos | Operaciones |
|---|---|---|
| Datasets destacados | Tag `FeaturedDataset` en datasets | search, add, remove |
| Visores destacados | `featured_viewers` de **ckanext-pages** | search, add, remove, reorder |
| Publicaciones destacadas | `FeaturedPublication` | CRUD, reorder, upload image, import legacy |
| Tarjetas de portal | `PortalCard` | CRUD, reorder, upload image |
| Tickets de errores | `BugTicket` | create, list, show, close, update status |
| Gestión de usuarios | CKAN users | search, create, reset pwd, delete, purge, reactivate, toggle sysadmin |
| Contenido IHP-IX | `IhpixContent` | list, update |
| Actividades IHP-IX | `IhpixActivity` | CRUD |
| Reportes IHP-IX | IHP-IX reports | list, review |

---

## 5. Sistema de caching (ciclo de vida)

```
1. Primera petición:
   a. Cache miss → se ejecuta la función original
   b. Resultado se almacena en cache con timestamp
   c. Se retorna el resultado

2. Peticiones subsiguientes (dentro de TTL):
   a. Cache hit → se retorna resultado cacheado directamente
   b. No hay llamada a API/DB

3. Expiración (TTL superado):
   a. Siguiente petición detecta cache expirado
   b. Se ejecuta la función original
   c. Se actualiza el cache con nuevo resultado y timestamp

Patrón LRU con buster:
   cache_buster = int(time.time() / cache_ttl)
   → Cambia cada cache_ttl segundos
   → @lru_cache ve un nuevo argumento → cache miss automático
```

---

## 6. Directorio de personas

**Ruta**: `/people`
**Módulos**: `controller.py`, `helpers.py`, `actions.py`

```
1. Usuario visita /people con filtros opcionales (query params):
   - q: búsqueda por nombre
   - country: filtro por estado miembro
   - organization: filtro por organización
   - expertise: filtro por área de expertise
2. controller.py: people_index() extrae query params
3. helpers.py: get_people_directory(q, country, organization, expertise)
   → actions.py: people_list() ejecuta búsqueda con filtros
     (q se parte en palabras: cada una debe aparecer en name o fullname,
      en cualquier orden — search.filter_by_tokens, ver [[Busqueda]])
   → Consulta users con plugin_extras.theme_ejemplo
4. Renderiza template people/directory.html con resultados paginados
```

---

## 7. Portal IHP-IX

**Rutas**: `/ihpix` (pública), `/ihpix/outputs`, `/ihpix/outputs/<code>`, `/ihpix/priority-area/<pa>`, `/ihpix/contributors`, `/ihpix/workspaces`, `/ihpix/workspaces/<code>` (+ `/join`, `/leave`, `/members`, `/members/process`), `/ihpix/report`, `/ihpix/report/<id>/edit`, `/ihpix/my-reports`, `/user/<id>/ihpix`, `/ihpix/dashboard` (todas las demás: **usuarios logueados**), `/ckan-admin/ihpix/overview`, `/ckan-admin/ihpix/workspaces`

**Taxonomías oficiales**: ver [[Modulos]] → `ihpix_constants.py` (5 Priority Areas, 34 Outputs, 15 Flagships, 7 Regions, 3 CTWGs, 12 Institution Types, 8 KPIs, 195 Member States, 4 Biennia 2022-2029).

```
1. Página principal (/ihpix):
   → Carga contenido editable de IhpixContent (12 secciones)
   → Hero (título y subtítulo) editable desde admin
   → Títulos de sección (Priority Areas, Metrics, CTA) editables desde admin
   → Priority Areas: título, descripción e imagen editables desde admin
   → Muestra mapa mundial Leaflet con estadísticas globales
   → Métricas de impacto con contadores animados
2. Outputs (/ihpix/outputs) — usuarios logueados:
   → Lista actividades publicadas de IhpixActivity
   → Filtros: biennium, region, country, organization, priority_area, output
     (listas desde h.get_ihpix_taxonomies(), ya no hardcodeadas)
   → Vistas expandibles con detalle (incl. adjuntos), exportación CSV
   → Los chips PA / Output enlazan a las páginas por PA y por Output
2b. Páginas navegables (fase iii, usuarios logueados):
   → /ihpix/outputs/<code>: stats del Output, actividades paginadas,
     contribuidores, adjuntos agrupados por tipo, instituciones líderes,
     mini-timeline, botón "Report an activity for this output"
     (prellena ?pa=&output=), otros Outputs de la PA
   → /ihpix/priority-area/<pa>: descripción (IhpixContent pa_N), grid de
     Outputs con conteos, stats, actividades recientes, top contribuidores
   → /ihpix/contributors: directorio de reportantes (GROUP BY reported_by,
     usuario resuelto + perfil) con filtros nombre / PA / Output / bienio
3. Reporte (/ihpix/report) — alineado al PDF UNESCO 2026:
   → 7 secciones (I General, II Priority Areas, III CTWGs, IV Region,
     V KPIs, VI Notes, VII Attachments), ~50 campos con lógica
     condicional Y/N
   → Char counters 250 chars (description, outcomes); límites largos
     con contador en partners 500 / key_activity 1000 / synergies 1500 /
     additional_notes 3000 (los tres últimos con editor Markdown + preview)
   → Selectores de país con buscador (Combobox), Member States con
     buscador y chips (MultiPicker), datalist de instituciones ya
     reportadas; grupos Sí/No en fieldset/legend (accesibilidad)
   → Validación en vivo: URL del enlace, fin ≥ inicio, jóvenes/mujeres ≤
     total (KPI 2 y 5). El servidor repite las reglas (ihpix_forms.py) y
     devuelve los mensajes traducidos
   → Sticky section nav con barra de progreso (7 campos obligatorios),
     indicadores por sección (✓ completa, ! error, ✓ tenue = opcional con
     respuestas); en móvil la barra es horizontal con scroll-snap
   → Autoguardado en localStorage (clave `ihpix-report-draft-v1:<user_id>`,
     migra la clave global anterior) solo en reporte nuevo; en modo
     edición la BD es la única fuente de verdad
   → Acepta ?pa=PA1&output=1.1 para prellenar (páginas por Output)
   → CSRF: {{ h.csrf_input() }} dentro del form (viaja en el FormData)
   → Validación inline al salir de cada campo + resumen de errores
     con enlaces de salto tras un envío inválido
   → Member States: buscador con etiquetas removibles (checkboxes
     name="member_states", contrato POST sin cambios)
   → Botones: "Save as draft" (status=draft) y "Submit for review" (status=pending)
   → POST (fetch/JSON): ihpix_report_submit(); la validación vive en
     ihpix_forms.validate_report_payload(). Errores → {errors: {campo: msg}}
     que el JS resalta (highlightServerErrors)
   → Tras guardar borrador → redirige a /ihpix/report/<id>/edit;
     tras enviar → /user/<me>/ihpix?status=pending con flash
   → Sección VII "Publications, events & data": adjuntos (ver 7.1)
3b. Mis reportes (/user/<id>/ihpix, atajo /ihpix/my-reports):
   → Pestaña "IHP-IX" del perfil (user/ihpix.html); el propio usuario y
     sysadmin ven todos los estados con contadores; terceros solo published
   → Editar (/ihpix/report/<id>/edit): mismo template en edit_mode con
     prefill desde ihpix_report_show()['form']; POST → ihpix_report_update()
   → Propietario edita solo draft/rejected; pending/published se abren en
     solo lectura (READ_ONLY deshabilita los inputs)
   → Eliminar (POST /ihpix/report/<id>/delete): solo borradores propios
4. Dashboard (/ihpix/dashboard) — usuarios logueados:
   → ihpix_dashboard_stats() genera estadísticas expandidas (+ contributors_total,
     top_institutions, output_biennium_matrix, links_by_type)
   → Mapa interactivo Leaflet con GeoJSON de países; PA/bienio se aplican en
     servidor (conteos en vivo), el país en cliente
   → Tablas "Top Lead Institutions" y "Activities by Output and Biennium"
     que se refrescan con los filtros (AJAX)
   → Gráficas por biennium, paneles de región e impacto
5. Admin Overview (/ckan-admin/ihpix/overview) — sysadmin:
   → ihpix_admin_overview_stats() expone métricas extendidas
   → 5 tabs: KPI Targets, Distributions, Geography, Completeness, Pending queue
   → Filtros: biennium · PA · region · flagship · CTWG · status
   → Charts.js (PA donut, biennium/output/flagship/CTWG/institution bars)
   → Exportación CSV/XLSX (en pipeline)
6. Admin Reports (/ckan-admin/ihpix/reports):
   → Cola de revisión approve/reject/re-approve (+ "Open full report")
   → Filtros pending / rejected / published / draft / all con contadores
   → Muestra gates Y/N y KPIs activos, focal point, reportante resuelto
     (h.get_ihpix_reporter) y notas adicionales
   → Aparece en la campana de aprobaciones (approvals.QUEUE_DEFS
     'ihpix_reports', helper get_pending_ihpix_reports_count)
7. Admin Content/Activities (/ckan-admin/ihpix, /activities):
   → Edición de hero, CTA cards, priority areas
   → CRUD completo de actividades, importación bulk Excel
```

### Modelo de gates condicionales (PDF 2026)

Para preservar la diferencia entre "no aplica" y "no se contestó", el modelo guarda **booleanos explícitos**:
- `unesco_secretariat_participation`, `has_member_state_support`, `has_flagship`,
  `has_synergies`, `regions_benefit`.
- 8 gates KPI: `kpi_1a_active`, `kpi_1b_active`, `kpi_2_active`, `kpi_3_active`,
  `kpi_4_active`, `kpi_5_active`, `kpi_6_active`, `kpi_8_active`.

Cuando el gate es `False`, los campos hijos se resetean al submit (`num_*=0`,
listas `JSON=''`). Esto permite reportar fielmente "actividad NO contribuyó al KPI X".
La tabla gate → hijos es `ihpix_forms.GATE_RESETS`.

### Estados del reporte (workflow 2026-09)

```
draft ──submit──▶ pending ──approve──▶ published
  ▲                  │                    ▲
  │                reject                 │
  └──save as draft── rejected ──re-approve┘
                       │
                       └──edit + submit──▶ pending
```

- `ihpix_report_submit` / `ihpix_report_update` fijan `submitted_at` y
  `reported_date` al pasar a `pending`, y limpian `reviewed_by/reviewed_at`
  (las `review_notes` se conservan como última observación).
- `ihpix_report_review` valida la transición (`approve` desde pending o
  rejected; `reject` solo desde pending, con `review_notes` obligatorias)
  y envía un email al reportante (`mailer.mail_user`, nunca bloquea).
- El propietario solo puede editar `draft`/`rejected` y borrar `draft`;
  el sysadmin puede editar cualquier estado (un `published` no vuelve a la cola).

> [!note] Inferencia
> `reviewed_by` guarda el username del revisor (contexto `user`), mientras que
> `reported_by` guarda el id del reportante. Se resuelven en UI con `h.get_ihpix_reporter`.

### 7.1 Adjuntos (Sección VII)

**Módulos**: `ihpix_links.py`, `model.py` (`IhpixActivityLink`), `actions.py`,
`templates/ihpix/snippets/report_links_section.html` (widget),
`templates/ihpix/snippets/activity_links.html` (macro de listado).

```
1. El widget de la Sección VII mantiene la lista de adjuntos en el campo
   oculto links_json (JSON). Va en el FormData del reporte, así que:
   → se guarda con el borrador (misma transacción) y
   → viaja en el autoguardado de localStorage sin código extra.
2. Añadir un adjunto:
   a. "Search in IHP-WINS" → GET /api/3/action/ihpix_link_search?kind=&q=
      · publication → datasets type:documents · dataset/output_data →
      type:dataset · event/webinar → páginas water-events (si ckanext-pages
      no está, search_available=false y el widget abre la entrada manual)
      · course → OpenLearningCourse.search_public (cursos aprobados)
   b. "Add an external link manually" → title + URL http(s) (+ fecha, descr.)
   c. Puentes (2026-09-24): "Upload a publication" abre el modal (7.1.a);
      "Add a dataset" abre /dataset/new prellenado (tag_string=ihp-ix,
      ihp-ix-output-<code>, owner_org si el usuario sólo tiene una) y
      "Create an event" abre /water-events_edit, ambos en otra pestaña
      (sin came_from) → botón "Refresh search" al volver. Con el tipo
      Course aparece "Propose this course" (7.1.b).
3. POST del reporte → actions._sync_activity_links(activity, links_json):
   → valida cada item (ihpix_links.validate_link), upsert por id, crea los
     nuevos, borra los ausentes (full replace), deduplica por objeto/URL
   → errores: ValidationError {'links[i].campo': msg}
4. Lectura: IhpixActivityLink.get_for_activities(ids) en una query →
   links_by_activity → macro render_links() en outputs, tabs org/grupo y
   cola admin. Contadores: get_stats()['links_by_type'] (dashboard, overview)
```

#### 7.1.a Publicaciones inline (modal "Upload a publication")

`templates/ihpix/snippets/publication_modal.html` (macro; se abre con
`[data-ihpix-publication-open]`, opcional `data-document-type`), contexto
`controller._ihpix_publication_context(output_code, activity)`.

```
1. Dónde: Sección VII y KPI 3 del reporte ("Upload training material" →
   document_type=educational_material), cabecera de /ihpix/workspaces/<code>
   y /ihpix/outputs/<code> (usuarios logueados).
2. Requisito: rol editor/admin en ≥1 organización (production.ini:
   create_unowned_dataset=false). Sin orgs → estado vacío con enlace a
   /organization (no se puede subir).
3. Campos: título*, tipo de documento, organización* (preseleccionada si
   sólo hay una), año, autores, resumen (Markdown), fichero (drag&drop,
   ≤ ihpix_upload_max_mb, extensiones de ihpix_publications.ALLOWED_EXTENSIONS)
   o URL, DOI, Member State, Iniciativa, palabras clave. El modal oculta
   los campos que el esquema `documents` instalado no tenga.
4. POST multipart /ihpix/publications → actions.ihpix_publication_create
   → package_create (type=documents, private=false, tags ihp-ix +
   ihp-ix-output-<code>) + resource_create (upload/URL) → ledger
   `publication_created` en el workspace del Output.
   · En el reporte: la respuesta se añade a la Sección VII con
     ihpixLinks.add() (se guarda con el reporte); en edición además se
     adjunta en servidor (activity_id).
   · En workspace/Output: select "Attach to my report" con los reportes
     propios del Output (0 → sólo se crea; 1 → preseleccionado).
5. Errores: 400 {errors} mapeados a los campos del modal
   (map_schema_errors); 403 reason=no_org; si resource_create falla se
   borra el package (best effort) y se muestra el error en "Document".
```

#### 7.1.b Cursos Open Learning

- Tipo de adjunto `course`: busca en la caché curada (`approved` +
  `is_available`); el enlace público es la página del curso en
  openlearning.unesco.org.
- "Propose this course" (Sección VII, tipo Course) y el formulario de
  `/courses` → `POST /ihpix/courses/propose` → `ihpix_course_propose`:
  el curso entra `pending` con `proposed_by/proposed_at/proposal_note`,
  email a sysadmins, cola `open_learning` en la campana, ledger
  `course_proposed`. Si ya estaba aprobado, se adjunta directamente.
- Materiales de formación (PDF, diapositivas) = publicación con
  `document_type=educational_material` (atajo en KPI 3).

#### 7.1.c Datasets y eventos

Siguen creándose en su formulario propio (otra pestaña): `/dataset/new`
prellenado por query string (la `CreateView` de CKAN 2.10 lee
`request.args`) y `/water-events_edit`. Al volver, "Refresh search".

> [!warning] Sin `came_from`
> Ni scheming ni ckanext-pages devuelven al reporte tras crear; el borrador
> sigue en localStorage (autosave por usuario), así que no se pierde nada.

#### 7.1.d Formularios admin alineados (fase D)

`/ckan-admin/ihpix/activities` envía ahora los mismos formatos que el
reporte público: tipos KPI como listas JSON, `member_states` JSON,
`unesco_secretariat_participation` como booleano y `additional_notes`
(Markdown). El controller acepta esos dos campos nuevos en
`_IHPIX_FORM_FIELDS`. Detalle de los cambios de UI en
[[Modulos#Kit de formularios IHP-IX]] ("Formularios admin").

> [!note] Markdown en los textos largos (2026-09-24)
> `key_activity`, `synergies` y `additional_notes` (reporte) y
> `ihpix_working_group.description` se guardan como **Markdown** (texto,
> nunca HTML) y se renderizan con `h.ihpix_markdown()` → `render_markdown`
> de CKAN (sanitiza). Los emails los envían como texto plano.

### 7.2 Visibilidad (2026-09)

- La landing `/ihpix` sigue siendo **pública**; sus contadores se calculan
  en servidor (`ihpix()` llama a `ihpix_dashboard_stats` con `ignore_auth`)
  y se inyectan en `<script id="ihpix-stats-initial">` (sin fetch a la API).
- Todo lo demás (explorador, dashboard, páginas por Output/PA, contribuidores,
  pestañas IHP-IX de org/grupo) exige sesión: `controller._require_login()`
  redirige a `/user/login?came_from=…`. Las acciones de lectura pasan a
  `_logged_in_only`.
- `cache.py` excluye `/ihpix/report`, `/ihpix/outputs`, `/ihpix/dashboard`,
  `/ihpix/priority-area`, `/ihpix/contributors`, `/ihpix/workspaces`,
  `/ihpix/my-reports`, `/ihpix/markdown-preview`, `/ihpix/publications` de la
  caché anónima (la landing sí se cachea).
- `POST /ihpix/markdown-preview` (login): `{text}` → `{html}` con
  `h.render_markdown` (CKAN 2.10 no expone `/api/util/markdown`). Lo usa el
  editor Markdown del kit de formularios ([[Modulos#Kit de formularios IHP-IX]]).
- Eventos: los enlaces "Create an event/news" usan `h.ihpix_pages_url` →
  `pages.water_events_new` (`/water-events_edit`); antes apuntaban a
  `/water-events/new`, inexistente en el fork. `_search_water_events` filtra
  por las columnas `private` y `submission_status` del fork.

### 7.3 Recompute del resumen por país

`IhpixCountrySummary` era un snapshot del Excel que nunca se actualizaba.

```
1. IhpixCountrySummary.recompute_from_activities(country=None, resolve_name)
   → agrega actividades published por país: total, paN_count,
     transboundary_* (KPI 6 activo o num_transboundary_ms>0),
     supporting_* (supporting_member_state), flagship_data {flagship: n},
     pa_output_data {'paN_outputs': {code: n}}
   → conserva latitude/longitude/region; países nuevos quedan en 0/0
     (no salen en el mapa hasta cargarles coordenadas con el seed)
   → resolve_name = actions.ihpix_country_name: slug de grupo → título;
     los nombres del seed se dejan tal cual
2. Disparadores:
   → CLI: ckan ihpix recompute-summary [--country X] [--dry-run]
   → Admin Overview: botón "Recompute map counts" (POST
     /ckan-admin/ihpix/recompute-summary → ihpix_country_summary_recompute)
   → Al aprobar un reporte (ihpix_report_review) se recalcula solo su país
     si ckanext.theme_ejemplo.ihpix_recompute_on_approve = true (default)
```

> [!warning] País: slug vs nombre
> El formulario guarda el **slug** del grupo Member State en `country`; el seed
> Excel guarda el **nombre**. `ihpix_country_name` normaliza slug → título,
> pero si el título del grupo no coincide exactamente con el nombre del seed
> ("Republic of Korea" vs "Korea, Republic of") se crean dos filas. Ver DOC-021.

### 7.4 Working groups (workspaces por Output)

**Módulos**: `ihpix_workspaces.py` (reglas), `model.py` (`IhpixWorkingGroup`,
`IhpixWorkingGroupMember`, `IhpixContribution`), `actions.py`, templates
`ihpix/workspaces.html`, `ihpix/workspace_detail.html`,
`ihpix/workspace_members.html`, `admin/ihpix_workspaces.html`.

```
1. Arranque: init_ihpix_working_groups_db() crea las 3 tablas y siembra un
   workspace por Output (34) con título "Output N.M – Título" (sin lead).
2. Sysadmin asigna lead en /ckan-admin/ihpix/workspaces (username):
   → ihpix_working_group_update(lead_user_id) crea/activa su membresía lead.
3. Un usuario logueado abre /ihpix/workspaces/<code> y pide unirse (nota
   opcional) → ihpix_working_group_join:
   → status pending (default) o active si ihpix_wg_open_join=true
   → email a los leads; contador en la campana (cola ihpix_wg_members,
     scope user: pendientes de los workspaces que el usuario lidera)
4. El lead gestiona en /ihpix/workspaces/<code>/members:
   → approve / reject / remove / set_role / reinstate
     (ihpix_working_group_member_process; reglas en
     ihpix_workspaces.validate_member_action; un lead no se quita a sí mismo)
   → email al afectado
5. Ledger de participación (ihpix_contribution), escrito por las acciones
   de las fases i/ii (misma transacción que el reporte):
   → report_submitted  al enviar/reenviar a revisión
   → report_published  al aprobar; además, si ihpix_wg_auto_contributor
     (default true) el reportante pasa a contributor activo del workspace
     del Output (member_joined con meta.auto=true) — una membresía removed
     no se reactiva sola
   → link_added        por cada adjunto nuevo (_sync_activity_links)
   → member_joined     al aprobar/ingresar
   → comment           reservado (sin UI en el piloto)
6. Lectura:
   → /ihpix/workspaces: grid por PA con miembros, publicados, último
     movimiento y "My working groups"
   → /ihpix/workspaces/<code>: stats, actividades publicadas del Output +
     "tus reportes en curso", miembros activos, adjuntos agrupados, feed
     (ihpix_contribution_list), botones Join/Leave/Report/Manage
   → /user/<id>/ihpix y la tarjeta del perfil: h.get_user_ihpix_summary
     (reportes publicados, workspaces, contribuciones) + feed personal
   → /people?ihpix_workspace=<code>: directorio filtrado por miembros
   → /ihpix/outputs/<code>: enlace "Working group"
```

> [!note] Alcance del piloto
> Sin comentarios ni notificaciones in-app (solo email y feed). El lead se
> asigna manualmente (sysadmin); no hay auto-asignación al primer reportante.
> Pendiente por confirmar con UNESCO si los observers deben ver los borradores
> ajenos (hoy solo cada autor ve sus reportes en curso).

---

## 8. Validación de imágenes de usuario

**Módulo**: `utils.py`

```
1. Usuario sube imagen de perfil
2. Validación en 3 capas:
   a. Extensión del archivo (whitelist: PNG, JPG, GIF, WebP, etc.)
   b. MIME type declarado (whitelist + normalización de aliases)
   c. Magic bytes del archivo (detección real del formato)
   d. Fallback: PIL/Pillow si magic bytes no son concluyentes
3. Si la validación falla:
   → Retorna código de error específico
   → No se almacena el archivo
4. Si la validación pasa:
   → Se almacena en el directorio de uploads de CKAN
```

---

## 9. Ingesta de datos IHP-IX (Seed pipeline)

**Módulos**: `cli.py`, `scripts/generate_seed.py`, `model.py`

```
Pipeline completo:
1. Se recibe archivo Excel con datos de Priority Areas por país
2. generate_seed.py procesa el Excel:
   a. Lee hojas de actividades y datos geográficos
   b. Genera JSON con estructura {activities: [...], country_summaries: [...]}
   c. Escribe ckanext/theme_ejemplo/data/ihpix_seed_data.json
3. CLI carga el JSON en la DB:
   a. ckan ihpix seed-data -f <path.json>
   b. Sin --append: elimina registros previos con original_id
   c. Crea registros IhpixActivity (744 actividades)
   d. Crea registros IhpixCountrySummary (205 países con coordenadas)

Re-ingesta con datos actualizados:
1. Obtener nuevo Excel
2. cd ckanext/theme_ejemplo && python scripts/generate_seed.py
3. ckan ihpix seed-data -f data/ihpix_seed_data.json
   (o directamente: ckan ihpix seed-data --from-excel <path.xlsx>)
```

> [!tip] Flag `--append`
> Usar `--append` para agregar datos sin eliminar los existentes. Sin este flag, el comando elimina todas las actividades con `original_id` y todos los country summaries antes de cargar.

---

## 10. API GeoJSON de IHP-IX

**Módulos**: `actions.py`, `auth.py`, `model.py`

```
ihpix_geojson (datos de país):
1. Request → API action ihpix_geojson (usuarios autenticados)
2. Filtro opcional: region (sobre el snapshot)
   Con priority_area / biennium / output / flagship: conteos en vivo con
   IhpixActivity.get_country_counts() cruzados con las coordenadas
3. IhpixCountrySummary.get_as_geojson(region)
4. Retorna GeoJSON FeatureCollection con Point por país
   → coordinates: [lng, lat]
   → properties: total_activities, pa1–5_count, transboundary, flagship_data

ihpix_activity_geojson (actividades individuales):
1. Request → API action ihpix_activity_geojson (público)
2. Filtros: priority_area, output, biennium, country, flagship, region
3. Consulta IhpixActivity + join con IhpixCountrySummary para coordenadas
4. Retorna GeoJSON FeatureCollection con actividades geolocalizadas

ihpix_country_summary_list (datos tabulares):
1. Request → API action ihpix_country_summary_list (público)
2. Filtro opcional: region
3. IhpixCountrySummary.get_all(region)
4. Retorna lista de dicts con datos por país
```

---

## 11. Curación de cursos Open Learning

**Módulos**: `openlearning.py`, `model.py`, `actions.py`, `controller.py` — ver [[Open Learning]]

```
1. Sync (lazy con TTL 6h / botón admin / cron `ckan openlearning sync --force`)
   → _fetch_all_courses(): API Open edX paginada, por término de búsqueda
   → upsert en tabla open_learning_course:
     · curso nuevo → status='pending' + tipo auto-detectado (pacing)
     · curso existente → actualiza display, last_seen_at, is_available=True
       (recalcula tipo solo si NO hay override admin; nunca toca status/orden)
     · curso ausente → is_available=False, SOLO si el fetch fue completo
2. Sysadmin en /ckan-admin/open-learning
   → aprueba (approved) / oculta (hidden) / corrige tipo (permanent/scheduled)
3. Vistas públicas leen get_public() (approved + is_available):
   → home: hasta 8 cursos (helper get_latest_courses, micro-caché 10 min)
   → /courses: secciones separadas self-paced y scheduled
```

> [!warning] Fallo parcial de la API
> Si cualquier página de cualquier término falla, `full_success=False` y **ningún** curso se marca como no disponible en ese sync. Evita falsos negativos cuando la API está inestable.

---

## 12. Conteo liviano de vistas

Reemplaza el `ckan.tracking_enabled` nativo, que bajo alto tráfico colapsaba la CPU: cada vista disparaba un request extra a `/_tracking` + un `INSERT` síncrono en `tracking_raw`, más un cron que agregaba toda la tabla y empujaba conteos a Solr. Aquí el conteo vive en Redis y se vuelca a Postgres en lotes. Implementado en [[Modulos#pageview_tracking.py]].

```
Request /dataset/<name> (GET)  ──┐
.../resource/<id>/download       ┘
   │  before_request _record() (registrado ANTES que la caché anónima)
   │    · solo GET; filtra bots por User-Agent
   │    · descargas: solo navegaciones de usuario (Sec-Fetch navigate,
   │      sin Range/prefetch) — excluye fetch de visores Terria/MapLibre/PDF
   │    · dedup IP+URL en ventana corta (clave Redis TTL)
   ▼
 [Redis]  HINCRBY pv:views <name>  (+ pv:daily:<fecha>)  |  HINCRBY pv:downloads <rid>
   │   (O(1), sin DB, sin request extra; cuenta incluso en HIT de caché anónima)
   ▼
 CronJob k8s cada ~5 min:  ckan pageviews flush
   │   RENAME atómico pv:* → pv:*:flush ; UPSERT ; recalcula recent_views ; poda diario
   ▼
 [Postgres]  tracking_dataset_stats / tracking_resource_stats / tracking_site_totals
             + tracking_dataset_daily
   ▲
   │  helpers de tracking (caché TTL en memoria, sin cambios de SQL)
 UI: badge de vistas en dataset, "más vistos / más descargados" en home, totales del sitio
```

> [!note] Activación
> Requiere `ckanext.theme_ejemplo.pageviews_enabled = true`, `ckan.tracking_enabled = false` y el CronJob `deploy/cronjob-pageviews-flush.yaml`. Sin el cron, los conteos se acumulan en Redis pero no llegan a la UI. Claves en [[Variables de Entorno#Conteo liviano de vistas (pageviews)]].

> [!tip] Resiliencia
> Redis caído → el registro es no-op y el serving sigue intacto. Postgres es la fuente durable; una caída de Redis sólo pierde los deltas aún no volcados (aceptable para conteos de vistas; el flush frecuente lo minimiza). El `RENAME` atómico evita perder incrementos durante el volcado.

---

## 13. Completitud de metadatos y orden por defecto en /dataset

`completeness.py` puntúa cada dataset/documento (0–100) con pesos por campo, sin persistir nada en el paquete: el score se inyecta al leer y se envía a Solr al indexar (`before_dataset_index` en `plugin.py`).

```
Indexación (before_dataset_index)
   │  completeness.for_index() → score, categoría
   ▼
 [Solr]  metadata_completeness          (score, para stats/ranking)
         metadata_completeness_category (facet full/medium/limited)
         metadata_completeness_sort     (score con cero-padding: '085.3')
   ▼
 /dataset sin búsqueda ni orden elegido (before_dataset_search)
   → sort = 'metadata_completeness_sort desc, metadata_modified desc'
   → el dropdown de orden marca "Metadata completeness" (package/search.html)
```

> [!warning] Cero-padding obligatorio
> Los campos dinámicos del esquema Solr estándar de CKAN se indexan como *string*, así que ordenar por `metadata_completeness` a secas es lexicográfico y queda mal ("9.5" > "85.3"). Por eso existe `metadata_completeness_sort` con padding (`completeness.sort_value()`). Con búsqueda de texto (`q`) se mantiene la relevancia como orden por defecto.

> [!warning] Requiere reindexar
> El campo `metadata_completeness_sort` solo existe para datasets indexados después del deploy: ejecutar `ckan search-index rebuild`. Los documentos sin el campo quedan al final del orden descendente.

Umbrales de categoría configurables: `ckanext.theme_ejemplo.completeness_full_threshold` (75) y `completeness_medium_threshold` (40).

---

## Ver también

- [[Arquitectura]] — Diseño general del sistema
- [[Modulos]] — Detalle por módulo
- [[Open Learning]] — Caché curada de cursos
- [[Variables de Entorno]] — Configuración de TTL de caches

## Catálogo de recursos de formación

`/learning` → filtros/búsqueda → ficha → acceso en el proveedor o materiales.
Editor de organización → alta/edición/archivos/relaciones → pendiente y privado.
Sysadmin → `/ckan-admin/learning` → aprobar/ocultar → publicación según disponibilidad.
Sync → upsert por fuente + ID externo → nuevos pendientes; existentes conservan curación.
Las relaciones resuelven permisos de datasets, publicaciones, herramientas e iniciativas
en cada lectura. `/courses` conserva acceso al subconjunto de cursos. Ver [[Open Learning]].
