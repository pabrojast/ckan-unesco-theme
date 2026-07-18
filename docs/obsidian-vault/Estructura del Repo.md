# Estructura del Repo

> Mapa de carpetas y archivos del repositorio `ckanext-theme-ejemplo`.

---

## Árbol de directorios (nivel 1)

```
ckan-unesco-theme/
├── .github/                    # CI/CD y configuración de GitHub
│   ├── copilot-instructions.md # Instrucciones para GitHub Copilot
│   └── workflows/
│       └── test.yml            # Pipeline de CI (pytest + Docker)
├── ckanext/
│   └── theme_ejemplo/          # ← Código fuente principal
├── docs/
│   └── obsidian-vault/         # ← Esta documentación
├── CLAUDE.md                   # Guía de comportamiento para Claude Code
├── AGENTS.md                   # Guía de comportamiento para Codex
├── LICENSE                     # AGPL v3+
├── MANIFEST.in                 # Archivos incluidos en distribución
├── README.md                   # README público del proyecto
├── dev-requirements.txt        # Dependencias de testing (pytest-ckan)
├── requirements.txt            # Dependencias de producción (shapely)
├── setup.cfg                   # Configuración de Babel para i18n
├── setup.py                    # Configuración del paquete Python
└── test.ini                    # Configuración de pytest para CKAN
```

---

## Código fuente: `ckanext/theme_ejemplo/`

| Archivo | Líneas | Rol |
|---|---|---|
| `plugin.py` | ~1,274 | Clase principal del plugin. Implementa 7 interfaces CKAN, registra rutas, helpers y caches |
| `controller.py` | ~2,896 | Clase `MyLogica` con 67 funciones de vista Flask (portales, admin, personas, datasets) |
| `actions.py` | ~1,879 | 45+ acciones CKAN custom: perfiles, membresías, publicaciones, tickets, IHP-IX |
| `helpers.py` | ~661 | 25 funciones helper: tracking, paginación, directorio de personas, organizaciones |
| `model.py` | ~1,141 | 6 modelos SQLAlchemy + tablas planas de conteo (`tracking_*`): MembershipRequest, FeaturedPublication, BugTicket, PortalCard, IhpixContent, IhpixActivity |
| `pageview_tracking.py` | — | Conteo liviano de vistas/descargas en Redis + volcado a Postgres (reemplazo de `ckan.tracking_enabled`) |
| `auth.py` | ~254 | 41 funciones de autorización (sysadmin-only y role-based) |
| `validators.py` | ~89 | 3 validadores para campos de perfil de usuario |
| `utils.py` | ~273 | 13 funciones de validación/detección de imágenes (MIME, magic bytes, PIL) |
| `__init__.py` | — | Módulo vacío |

---

## Templates: `ckanext/theme_ejemplo/templates/`

135 archivos Jinja2 organizados por portal/funcionalidad:

| Directorio | Contenido |
|---|---|
| `admin/` | Paneles de administración (datasets, publicaciones, portal cards, usuarios, IHP-IX) |
| `bug_tickets/` | Lista, creación y detalle de tickets |
| `citizen_science_portal/` | Portal de ciencia ciudadana |
| `doi/` | Templates relacionados con DOI |
| `email/` | Templates de correo electrónico |
| `flood_drought_portal/` | Portal de inundaciones y sequías |
| `group/` | Vistas de grupos/iniciativas (miembros, noticias, eventos, publicaciones) |
| `home/` | Homepage con snippets UNESCO. `custom_layout.html` orquesta: buscador → slideshow → stats → Featured Datasets → hub "Explore Data" (tabs Recientes/Trending, `explore_tabs.html`) → hub "Tools and Resources" (`tools_hub.html`) → hub "Community and Knowledge" (tabs News/Events/Publications/Courses, `community_tabs.html`) → About. Los tabs son server-side con progressive enhancement (`html.js`); sin JS los paneles se apilan visibles |
| `ihpix/` | Portal IHP-IX (página principal, outputs, dashboard, reportes) |
| `initiatives/` | Portal de iniciativas |
| `iot_portal/` | Portal IoT |
| `macros/` | Macros de formulario reutilizables |
| `memberstates/` | Portal de estados miembros |
| `organization/` | Vistas de organización (personas, publicaciones, noticias, eventos) |
| `package/` | Overrides de vistas de datasets |
| `people/` | Directorio de personas y perfiles |
| `schemingdcat/` | Overrides para ckanext-schemingdcat |
| `snippets/` | Snippets globales reutilizables |
| `thematicbuilder/` | Portal de constructor temático |
| `user/` | Vistas de perfil de usuario (documentos, organizaciones, data stories) |
| `footer.html` | Footer global |

---

## Assets estáticos: `ckanext/theme_ejemplo/public/`

| Archivo/Directorio | Tamaño | Descripción |
|---|---|---|
| `theme_ejemplo.css` | 155 KB | Hoja de estilos principal del tema |
| `ckan210-fixes.css` | 102 KB | Correcciones de compatibilidad CKAN 2.10 |
| `theme_ejemplo_enhanced.js` | 21 KB | JavaScript mejorado del tema |
| `topmenu-responsive.js` | 1.6 KB | Menú responsive |
| `tracking-display.js` | 3.3 KB | Visualización de estadísticas de tracking |
| `robots.txt` | — | Configuración SEO |
| `favicon.ico` | 72 KB | Favicon del sitio |
| Logos (`logo.svg`, `unesco.svg`, etc.) | — | Logos UNESCO e IHP |
| Fuentes (`unesco.ttf`, `unesco.woff`) | — | Tipografía UNESCO |
| `base/images/` | — | Imágenes base del tema |
| `country/` | — | Banderas e imágenes de estados miembros |
| `centers/` | — | Logos de centros UNESCO |
| `Landing_page/` | — | Assets de la landing page |
| `thematicbuilder/` | — | Assets del constructor temático |
| `webassets.yml` | — | Configuración del pipeline de assets |

---

## Internacionalización: `ckanext/theme_ejemplo/i18n/`

| Idioma | Código | Archivos |
|---|---|---|
| Árabe | `ar` | `ar/LC_MESSAGES/ckanext-theme_ejemplo.{po,mo}` |
| Español | `es` | `es/LC_MESSAGES/ckanext-theme_ejemplo.{po,mo}` |
| Francés | `fr` | `fr/LC_MESSAGES/ckanext-theme_ejemplo.{po,mo}` |

Archivo de plantilla: `ckanext-theme_ejemplo.pot`

---

## Tests: `ckanext/theme_ejemplo/tests/`

| Archivo | Líneas | Contenido |
|---|---|---|
| `test_plugin.py` | ~53 | Test básico del plugin (placeholder) |
| `test_utils.py` | ~90 | Tests de validación de imágenes de usuario (14 casos) |

> [!warning] Cobertura de tests limitada
> Solo se testean `plugin.py` (mínimo) y `utils.py`. Los módulos `actions.py`, `controller.py`, `helpers.py`, `model.py`, `auth.py` y `validators.py` no tienen tests. Ver [[Backlog Documentacion]].

---

## Ver también

- [[Arquitectura]] — Diseño del sistema
- [[Modulos]] — Detalle de cada módulo
- [[Setup Local]] — Cómo levantar el proyecto
