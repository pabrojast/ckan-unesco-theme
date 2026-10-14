# Initiative pages

> Página completa para las iniciativas: cuestionario de 7 pasos y plantilla común con una identidad de color propia, sacada de las imágenes de cada iniciativa.
> Añadido por Jorgen Van Der Biest (UNESCO-IHP), octubre de 2026. Generaliza el diseño de [[AI for Water Management]]. Amplía [[Solicitudes de Iniciativas]].

---

## Qué hace

- `/initiatives/request` ofrece dos opciones: **Standard request** (el formulario de siempre, sin cambios) o **Full initiative page** (`/initiatives/request/full`, cuestionario de 7 pasos).
- La página completa crea la solicitud con la vista de siempre (`MyLogica.request_initiative`: validación, logo, aviso por correo a los sysadmins) y guarda las respuestas en la tabla propia `initiative_page`.
- Al aprobar la solicitud, el grupo creado (`initiative_request.created_group_id`) muestra la **plantilla común**: la de AI for Water Management (mismas clases `.aiw`, `ai-water.css`) con el contenido del cuestionario y los colores de la iniciativa.
- Una iniciativa estándar puede pasar a página completa más tarde desde el botón **Set up the full initiative page** (administradores del grupo y sysadmins), en `/group/<name>/page-setup`. La misma página sirve para editarla (**Edit page**).
- Estados miembros e iniciativas siguen separados: los grupos de Estados miembros (miembros de `member-states`) nunca usan esta plantilla ni muestran el botón.
- Las iniciativas que ya existen no cambian.

| URL | Quién | Qué |
|---|---|---|
| `/initiatives/request` | usuario autenticado | Elección + solicitud estándar (plantilla de siempre con una línea añadida) |
| `/initiatives/request/full` | usuario autenticado | Cuestionario completo |
| `/group/<name>/page-setup` | admin del grupo, sysadmin | Crear o editar la página completa |
| `/ckan-admin/initiative-requests/<id>/answers` | sysadmin | Respuestas y colores de una solicitud, para revisarla |

Las páginas del grupo usan las URLs de siempre (`/group/<name>`, `/members`, `/news`, `/events`, `/publications`, `/data-stories`, `/group/about/<name>`), como AI for Water.

## Cuestionario

| Paso | Campos |
|---|---|
| 1 The basics | nombre*, nombre corto, título en dos líneas, tagline*, tipo*, estado y años, organización líder* (organizaciones de IHP-WINS) |
| 2 The story | about*, por qué importa, teoría del cambio, objetivos (1 a 8)*, cifras clave (hasta 8) |
| 3 Scope and alignment | alcance*, Estados miembros (grupos de `member-states`), outputs de IHP-IX (OIP, con su texto), ODS, temas |
| 4 People and partners | contactos (1 a 6)*, socios (organizaciones de IHP-WINS) |
| 5 Visual identity | logo (solo en la solicitud), imagen principal* con crédito y texto alternativo, imagen de banda, imagen de apoyo, disposición del hero, colores |
| 6 Page content and links (opcional) | línea sobre el título, dos botones, llamada final, secciones visibles, datasets destacados, enlaces |
| 7 Review | resumen y envío |

Nombre, descripción y logo son los campos de siempre de la solicitud (y del grupo). En `page-setup` no se editan ahí sino desde Manage.

Datasets destacados: si no se eligen, la portada muestra los más vistos de la iniciativa (`tracking_dataset_stats.total_views`, la misma fuente que `get_popular_datasets`); sin visitas registradas, los más recientes.

## Colores

1. El navegador lee las imágenes (canvas), agrupa los píxeles en 8 colores (k-means en OKLab) y elige tres semillas: color principal, acento (un tono distinto y vivo) y banda clara. Sin segundo color, el acento es naranja (principal frío) o azul agua (resto).
2. De las semillas salen los roles de la plantilla, cada uno con su contraste WCAG mínimo (texto blanco sobre el principal ≥ 7:1, texto ≥ 7:1, enlaces ≥ 4,5:1, líneas de acento ≥ 3:1).
3. El servidor recalcula los roles a partir de las semillas (`initiative.derive_roles`, mismas reglas que `initiative-form.js`) y los guarda en `initiative_page.palette`.
4. La plantilla escribe los roles como variables CSS (`--aiw-blue`, `--aiw-cyan`, `--aiw-orange`...) en el contenedor `.aiw.ini`; `initiative.css` cambia los pocos colores que `ai-water.css` deja fijos.

> [!note] Pillow
> Si el navegador no envía colores (sin JavaScript), el servidor intenta sacarlos de la imagen principal con Pillow, si está instalado; si no, usa el azul de IHP-WINS. Pendiente por confirmar: si Pillow está en la imagen de producción.

## Dónde está el código

Todo el código nuevo está en ficheros propios:

- `ckanext/theme_ejemplo/initiative.py`: tabla `initiative_page`, cuestionario (`parse_form`), colores, datos de la plantilla, vistas y rutas (`add_url_rules`), helpers (`get_helpers`).
- `templates/initiative/`: portada (`landing.html`), cabecera (`snippets/header.html`), Partners & people, About, introducciones del Knowledge hub, cuestionario (`snippets/questionnaire.html`), páginas de solicitud y de `page-setup`, respuestas para el admin, botón y elección estándar/completa.
- `public/css/initiative.css` (bajo `.aiw.ini`, `.ini-form` e `.ini-mode`) y `public/js/initiative-form.js`.

En ficheros existentes solo se añaden líneas, marcadas con `Initiative pages (added by Jorgen Van Der Biest)`:

- `plugin.py`: import, `initiative.add_url_rules(blueprint)` y `initiative.get_helpers()`.
- `templates/initiatives/request.html`: elección estándar / página completa.
- `templates/admin/initiative_requests.html`: enlace a las respuestas de la página completa.
- `templates/group/read_base.html`: botón para crear o editar la página completa.
- Ficheros de AI for Water: `ai_water.py` (la plantilla común como reserva de `GROUP_LANDINGS`), `ai_water_portal/group_frame.html` (clase, colores y créditos por configuración) y `ai_water_portal/snippets/head.html` (`initiative.css`).

## Base de datos

Tabla nueva `initiative_page`, creada por el propio módulo la primera vez (`initiative.init_db`, como las tablas de `model.py`). No cambia ninguna tabla existente.

| Columna | Contenido |
|---|---|
| `id` | uuid |
| `request_id` | `initiative_request.id` (solicitudes completas) |
| `group_id` | `group.id` (al crear o editar desde `page-setup`) |
| `details` | respuestas (JSON, ver `initiative.normalize_details`) |
| `palette` | semillas, roles y modo automático (JSON) |
| `created`, `updated`, `updated_by` | trazabilidad |

Las imágenes se suben con el tipo de subida `group` de CKAN (`/uploads/group/`), sin configuración nueva.

## Personalizar una iniciativa

Las iniciativas que necesitan más que la plantilla común se añaden a `GROUP_LANDINGS` en `ai_water.py` con sus propias plantillas, como AI for Water. `GROUP_LANDINGS` tiene prioridad sobre la plantilla común.
