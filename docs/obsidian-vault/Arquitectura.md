# Arquitectura

> Diseño general de `ckanext-theme-ejemplo`, la extensión CKAN para el portal de datos hídricos de UNESCO.

---

## Visión general

El plugin es una extensión monolítica de CKAN que extiende el portal con:
- Tema visual UNESCO
- 9+ portales temáticos (IHP-IX, IoT, Inundaciones, Ciencia ciudadana, etc.)
- Perfiles de usuario extendidos
- Paneles de administración personalizados
- Pipeline de datos espaciales
- Sistema de caching multicapa

```
┌──────────────────────────────────────────────────┐
│                  CKAN Core 2.9                    │
├──────────────────────────────────────────────────┤
│           ThemeEjemploPlugin                      │
│  ┌──────────┬──────────┬──────────┬────────────┐ │
│  │IConfigurer│IBlueprint│IActions  │IPackage    │ │
│  │ITranslat. │ITemplate │IAuthFunc │ Controller │ │
│  └──────────┴──────────┴──────────┴────────────┘ │
│  ┌──────────┬──────────┬──────────┬────────────┐ │
│  │plugin.py │controller│actions.py│ model.py   │ │
│  │          │  .py     │          │            │ │
│  │helpers.py│auth.py   │validators│ utils.py   │ │
│  └──────────┴──────────┴──────────┴────────────┘ │
├──────────────────────────────────────────────────┤
│  templates/ (135 archivos)  │ public/ (assets)   │
│  i18n/ (AR, ES, FR)        │ fanstatic/          │
└──────────────────────────────────────────────────┘
```

---

## Interfaces CKAN implementadas

| Interfaz | Propósito |
|---|---|
| **IConfigurer** | Registra templates, directorio público y recursos Fanstatic |
| **IBlueprint** | Registra todas las rutas Flask personalizadas (30+ rutas) |
| **ITemplateHelpers** | Expone ~30 funciones helper para templates Jinja2 |
| **IPackageController** | Hook en indexación de datasets (`before_dataset_index`) para datos espaciales y facetas |
| **ITranslation** | Habilita i18n (árabe, español, francés) |
| **IActions** | Sobrescribe `user_show`/`user_update` y agrega 45+ acciones custom |
| **IAuthFunctions** | 41 funciones de autorización para acciones custom |

---

## Pipeline de datos espaciales

El hook `before_dataset_index` convierte campos de bounding box a geometría WKT para indexación en Solr:

```
Dataset extras (xmin, ymin, xmax, ymax)
    │
    ▼
Shapely: box(xmin, ymin, xmax, ymax)
    │
    ▼
WKT string → campo Solr `spatial_geom`
```

También sanitiza facetas multilingües para prevenir errores de Solr atomic update.

> **Nota**: Requiere Shapely < 2 (restricción del CI).

---

## Estrategia de caching

El sistema usa tres patrones de cache. Ver detalles de configuración en [[Variables de Entorno]].

### 1. Diccionarios TTL a nivel de módulo
Caché manual con expiración configurable:
- `_courses_cache` → Cursos de UNESCO Open Learning
- `_member_states_cache` → Lista de estados miembros
- `_initiatives_cache` → Lista de iniciativas
- `_recently_added_datasets_cache` → Datasets recientes
- `_recently_added_documents_cache` → Documentos recientes

### 2. `@lru_cache` con cache buster
```python
cache_buster = int(time.time() / cache_ttl)
```
Usado para:
- Datasets destacados filtrados (`maxsize=64`)
- Estadísticas del sitio (`maxsize=16`)

### 3. Sesión HTTP compartida
`requests.Session()` a nivel de módulo con connection pooling. Timeout: 5s conexión + 10s lectura.

---

## Modelos de base de datos

6 modelos SQLAlchemy en [[Modulos#model.py]]:

| Modelo | Tabla | Propósito |
|---|---|---|
| `MembershipRequest` | membership_request | Solicitudes de membresía a organizaciones |
| `FeaturedPublication` | featured_publication | Publicaciones destacadas en homepage |
| `BugTicket` | bug_ticket | Sistema de tickets de errores |
| `PortalCard` | portal_card | Tarjetas configurables para portales |
| `IhpixContent` | ihpix_content | Contenido editable de IHP-IX |
| `IhpixActivity` | ihpix_activity | Actividades del programa IHP-IX |

Las tablas se crean automáticamente con `init_db()` idempotente y soporte de migraciones.

---

## Extensión de perfiles de usuario

8 campos adicionales almacenados en `plugin_extras.theme_ejemplo`:

| Campo | Tipo | Descripción |
|---|---|---|
| `job_title` | texto | Cargo del usuario |
| `institution` | texto | Institución/organización |
| `country` | texto | Slug de estado miembro |
| `phone` | texto | Teléfono |
| `website` | texto | Sitio web personal |
| `orcid` | texto | Identificador ORCID |
| `expertise_areas` | JSON lista | Áreas de experiencia |
| `social_links` | JSON dict | LinkedIn, Twitter, ResearchGate, GitHub, website |

---

## Paneles de administración

Todos bajo `/admin/*`, requieren rol sysadmin. Ver rutas completas en [[Flujos Importantes#Paneles de administración]].

| Panel | Ruta | Función |
|---|---|---|
| Datasets destacados | `/admin/featured-datasets` | Marcar/desmarcar datasets |
| Publicaciones | `/admin/featured-publications` | CRUD + reordenar + imágenes |
| Tarjetas de portales | `/admin/portal-cards/<portal_id>` | CRUD + reordenar + imágenes |
| Tickets de errores | `/admin/bug-tickets` | Ver y gestionar tickets |
| Usuarios | `/admin/users` | Gestión completa de usuarios |
| Contenido IHP-IX | `/admin/ihpix/content` | Editar secciones IHP-IX |
| Actividades IHP-IX | `/admin/ihpix/activities` | CRUD actividades |
| Reportes IHP-IX | `/admin/ihpix/reports` | Revisar reportes |

---

## Relaciones entre módulos

```
plugin.py ─── registra ──→ controller.py (vistas)
    │                          │
    ├── registra ──→ helpers.py (helpers de template)
    │                          │
    ├── registra ──→ actions.py (acciones CKAN)
    │                    │
    │                    └── usa ──→ model.py (DB)
    │                    └── usa ──→ validators.py
    │
    ├── registra ──→ auth.py (autorización)
    │
    └── usa ──→ utils.py (utilidades de imagen)
```

---

## Ver también

- [[Modulos]] — Detalle de cada archivo Python
- [[Flujos Importantes]] — Flujos de negocio clave
- [[Variables de Entorno]] — Configuración completa
- [[Estructura del Repo]] — Organización de archivos
