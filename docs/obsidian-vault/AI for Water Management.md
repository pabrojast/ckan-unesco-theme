# AI for Water Management

> Diseño propio para las páginas del grupo `artificial-intelligence-for-water-management`.
> Añadido por Jorgen Van Der Biest (UNESCO-IHP), octubre de 2026. Piloto para un futuro diseño de grupo reutilizable.

---

## Qué hace

Todas las páginas del grupo usan un diseño propio, alineado con la publicación *Applications of AI for water management* (UNESCO/Deltares, 2025). Las URLs son las de siempre; no se crea ninguna ruta nueva. El resto de grupos no cambia.

| URL | Sección del menú del grupo | Contenido |
|---|---|---|
| `/group/<name>` (sin parámetros) | Overview | Portada (`landing.html`) |
| `/group/<name>?q=…` (búsqueda, filtros, página) | Knowledge hub › Datasets & tools | Lista estándar de CKAN con introducción |
| `/group/<name>/data-stories` | Knowledge hub › Case studies | Pestaña estándar con introducción |
| `/group/<name>/publications` | Knowledge hub › Documents | Pestaña estándar con introducción |
| `/group/<name>/members` | Partners & people | Personas, lista de instituciones con filtros y miembros |
| `/group/<name>/news` | News & events | Noticias y eventos juntos (`news_events.html`) |
| `/group/<name>/events` | News & events › All events | Pestaña estándar |
| `/group/about/<name>` | About | Pestaña estándar |

## Dónde está el código

Todo el código nuevo está en ficheros propios:

- `ckanext/theme_ejemplo/ai_water.py`: `GROUP_LANDINGS` (configuración por grupo) y los helpers `theme_ejemplo_group_landing`, `theme_ejemplo_group_landing_data` y `theme_ejemplo_group_pages`.
- `templates/group/read.html`: muestra la portada en `/group/<name>` sin parámetros.
- `templates/ai_water_portal/`: portada, marco de las pestañas (`group_frame.html`), cabecera y menú (`snippets/header.html`), introducciones de pestañas y vista News & events.
- `public/css/ai-water.css` (todo bajo `.aiw`), `public/js/ai-water.js` (la cabecera del sitio se oculta al bajar y el menú del grupo queda fijo; filtros de la lista de socios) y `public/ai_water/` (ilustraciones).

En ficheros existentes solo se añaden líneas, marcadas con `AI for Water Management (added by Jorgen Van Der Biest)`:

- `plugin.py`: `from . import ai_water` y `**ai_water.get_helpers(),` en `get_helpers()`.
- `templates/group/read_base.html`: bloques `styles` y `content` al final del fichero. Solo actúan para los grupos de `GROUP_LANDINGS`; los demás pasan por `super()`.

## Configuración

`GROUP_LANDINGS` en `ai_water.py`, por grupo:

- `overview`: plantilla de la portada
- `header`: cabecera común (migas, menú y título de sección)
- `intros`: contenido que se añade encima de una pestaña, por endpoint
- `replace`: contenido que sustituye al de una pestaña, por endpoint

Para dar este tratamiento a otro grupo basta con añadirlo a `GROUP_LANDINGS` con sus plantillas. No necesita variables de configuración ni migraciones.

## Ilustraciones

De la publicación *Applications of AI for water management*, de Ana Carolina Landi / Diecut is Design. Solo se recortan, sin modificarlas, y se cita la autoría al pie de cada página (`snippets/credit.html`).
