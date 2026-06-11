# Flujos Importantes

> Flujos de negocio clave del sistema `ckanext-theme-ejemplo`.

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

**Patrón común**: Todas las rutas `/admin/*` siguen este flujo.

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

### Paneles disponibles

| Panel | Modelo de datos | Operaciones |
|---|---|---|
| Datasets destacados | Tag `FeaturedDataset` en datasets | search, add, remove |
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
   → Consulta users con plugin_extras.theme_ejemplo
4. Renderiza template people/directory.html con resultados paginados
```

---

## 7. Portal IHP-IX

**Rutas**: `/ihpix`, `/ihpix/outputs`, `/ihpix/report`, `/ihpix/dashboard`, `/ckan-admin/ihpix/overview`

**Taxonomías oficiales**: ver [[Modulos]] → `ihpix_constants.py` (5 Priority Areas, 34 Outputs, 15 Flagships, 7 Regions, 3 CTWGs, 12 Institution Types, 8 KPIs, 195 Member States, 4 Biennia 2022-2029).

```
1. Página principal (/ihpix):
   → Carga contenido editable de IhpixContent (12 secciones)
   → Hero (título y subtítulo) editable desde admin
   → Títulos de sección (Priority Areas, Metrics, CTA) editables desde admin
   → Priority Areas: título, descripción e imagen editables desde admin
   → Muestra mapa mundial Leaflet con estadísticas globales
   → Métricas de impacto con contadores animados
2. Outputs (/ihpix/outputs):
   → Lista actividades publicadas de IhpixActivity
   → Filtros avanzados: biennium, region, country, priority_area, output
   → Vistas expandibles con detalle, exportación CSV
3. Reporte (/ihpix/report) — alineado al PDF UNESCO 2026:
   → 6 secciones (I General, II Priority Areas, III CTWGs, IV Region,
     V KPIs, VI Notes), ~50 campos con lógica condicional Y/N
   → Char counters 250 chars (description, outcomes)
   → Sticky section nav con barra de progreso (7 campos obligatorios)
     e indicadores de estado por sección
   → Autoguardado en localStorage (clave `ihpix-report-draft-v1`);
     restaura respuestas no enviadas al recargar y se limpia al enviar
   → Validación inline al salir de cada campo + resumen de errores
     con enlaces de salto tras un envío inválido
   → Member States: buscador con etiquetas removibles (checkboxes
     name="member_states", contrato POST sin cambios)
   → Botones: "Save as draft" (status=draft) y "Submit for review" (status=pending)
   → POST: ihpix_report_submit() persiste con todas las flags KPI activas
4. Dashboard público (/ihpix/dashboard):
   → ihpix_dashboard_stats() genera estadísticas expandidas
   → Mapa interactivo Leaflet con GeoJSON de países
   → Gráficas por biennium, paneles de región e impacto
5. Admin Overview (/ckan-admin/ihpix/overview) — sysadmin:
   → ihpix_admin_overview_stats() expone métricas extendidas
   → 5 tabs: KPI Targets, Distributions, Geography, Completeness, Pending queue
   → Filtros: biennium · PA · region · flagship · CTWG · status
   → Charts.js (PA donut, biennium/output/flagship/CTWG/institution bars)
   → Exportación CSV/XLSX (en pipeline)
6. Admin Reports (/ckan-admin/ihpix/reports):
   → Cola de revisión approve/reject/re-approve
   → Stats pending/rejected, paginación, filtro por status
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
1. Request → API action ihpix_geojson (público)
2. Filtro opcional: region
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

## Ver también

- [[Arquitectura]] — Diseño general del sistema
- [[Modulos]] — Detalle por módulo
- [[Open Learning]] — Caché curada de cursos
- [[Variables de Entorno]] — Configuración de TTL de caches
