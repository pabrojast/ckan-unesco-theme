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
- `public/css/ai-water.css` (todo bajo `.aiw`), `public/js/ai-water.js` y `public/ai_water/` (ilustraciones).
  - Franjas de IHP-WINS plegadas por defecto, desde el primer pintado: la barra de la cuenta (solo con sesión iniciada), la cabecera del sitio y las migas.
  - Solo el menú del grupo (Overview, Partners & people...) queda fijo arriba.
  - Botón **IHP-WINS menu**, a la derecha de ese menú: despliega o pliega las franjas.
  - Desde noviembre de 2026 ya no aparecen al pasar el ratón por el borde superior, porque el movimiento resultaba incómodo.
  - Plegadas, quedan `inert`: sin foco ni lectores de pantalla.
  - Sin JavaScript, un `<noscript>` en `snippets/head.html` la deja visible.
  - En el móvil, el menú del grupo es una sola fila que se desliza.
  - `ai-water.js` también hace los filtros de la lista de socios.
  - Lo mismo vale para las páginas de iniciativa con la plantilla común.

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

## Socios y miembros del Expert Group

El grupo de coordinación se llama **AI for Water Expert Group** (antes "Task Force" o "Working Group" en la Estrategia rev4 y el formulario). El contenido sale del formulario de expresión de interés (23 respuestas: 21 expertos de 13 instituciones).

- `templates/ai_water_portal/partners_body.html`: lista de instituciones (`partners`). Cada una tiene un estado (`status`, `tone`):
  - `interest`: Expressed interest;
  - `invited`: Invited;
  - `lead`: Course lead;
  - `partner`: Knowledge partner, Coordination link, Contributor.

  También tiene el número de expertos en el Expert Group (`experts`).
- `templates/ai_water_portal/snippets/expert_members.html`: lista de expertos por institución (nombre, cargo, tema).
  - Un experto solo aparece en público con `'public': True`, cuando ha aceptado figurar con su nombre en la página.
  - Los administradores del grupo y los sysadmins ven la lista completa, con los nombres aún no públicos marcados.
  - Sin ningún nombre público, los visitantes no ven la sección.

> [!note] Pendiente por confirmar
> - Orden nombre/apellido de los expertos de China Three Gorges University y apellido completo de Mariangel García (IWMI).
> - Si la invitación al CIH se envió.
> - El tipo de CBAS: la página lo muestra entre los Category 2 Centres; las respuestas del formulario lo describen como institución de investigación.

## Ilustraciones

De la publicación *Applications of AI for water management*, de Ana Carolina Landi / Diecut is Design. Solo se recortan, sin modificarlas, y se cita la autoría al pie de cada página (`snippets/credit.html`).
