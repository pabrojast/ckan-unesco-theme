# IHP-IX

Hub de la implementación del **reporting y gestión del conocimiento IHP-IX** en IHP-WINS (requisito contractual 7, fases i–iv, 2026-09). Esta nota solo orienta: el detalle vive en las notas enlazadas.

> [!info] Qué es
> El portal `/ihpix` permite a los usuarios de IHP-WINS **reportar actividades** del Plan Estratégico IHP-IX (2022–2029) con el formulario oficial (PDF 2026), **adjuntar** publicaciones, webinars, eventos y datos, **explorar** lo reportado por Output / Priority Area / contribuidor, y colaborar en **working groups** (uno por Output).

## Mapa rápido

| Bloque | Qué hace | Dónde está documentado |
|---|---|---|
| **Reporte** (`/ihpix/report`, `/ihpix/report/<id>/edit`, `/user/<id>/ihpix`) | Formulario PDF 2026 con borradores en servidor, edición/reenvío, cola de revisión con email y campana | [[Flujos Importantes#7. Portal IHP-IX]] · [[Modulos#ihpix_forms.py]] |
| **Adjuntos** (Sección VII) | Publicaciones (datasets `documents`), eventos (páginas `water-events`), datasets y enlaces asociados a cada reporte | [[Flujos Importantes#7.1 Adjuntos (Sección VII)]] · [[Modulos#ihpix_links.py]] |
| **Descubribilidad** (`/ihpix/outputs`, `/ihpix/outputs/<code>`, `/ihpix/priority-area/<pa>`, `/ihpix/contributors`, `/ihpix/dashboard`) | Páginas navegables y analítica para usuarios logueados; landing pública | [[Flujos Importantes#7.2 Visibilidad (2026-09)]] · [[Flujos Importantes#7.3 Recompute del resumen por país]] |
| **Working groups** (`/ihpix/workspaces`) | Piloto: un workspace por Output, membresías (lead / contributor / observer) y ledger de contribuciones | [[Flujos Importantes#7.4 Working groups (workspaces por Output)]] · [[Modulos#ihpix_workspaces.py]] |
| **Admin** (`/ckan-admin/ihpix/*`) | Contenido, actividades, cola de revisión, overview (CSV, recompute) y working groups | [[Arquitectura#Paneles de administración]] |

## Módulos

- `ihpix_constants.py` — taxonomías oficiales (5 PA, 34 Outputs, KPIs…) y títulos de Output desde `data/ihpix_output_titles.json`.
- `ihpix_forms.py`, `ihpix_links.py`, `ihpix_workspaces.py`, `ihpix_publications.py` — módulos **puros** con la lógica de validación/reglas; testeados sin CKAN.
- Puentes al ecosistema (2026-09-24): modal "Upload a publication" (crea datasets `documents` y los adjunta), tipo de adjunto `course` + propuesta de cursos Open Learning, "Add a dataset" prellenado → [[Flujos Importantes#7.1 Adjuntos (Sección VII)]].
- `ihpix_i18n_strings.py` — literales de taxonomías para Babel; los templates traducen valores con `h.ihpix_t`.
- Kit de formularios `public/js/ihpix-forms.js` + `public/css/ihpix-forms.css` (Combobox, MultiPicker, MarkdownEditor, CharCounter, Toast, Modal, FileUpload; se carga con `ihpix/snippets/forms_assets.html`) → [[Modulos#Kit de formularios IHP-IX]]. El reporte lo usa desde 2026-09-24 (pase UX: ver [[Flujos Importantes#7. Portal IHP-IX]] punto 3).
- Modelos: `IhpixActivity`, `IhpixActivityLink`, `IhpixWorkingGroup`, `IhpixWorkingGroupMember`, `IhpixContribution`, `IhpixCountrySummary`, `IhpixContent` → [[Modulos#model.py]].

## Configuración

`ckanext.theme_ejemplo.ihpix_recompute_on_approve`, `ihpix_geojson_max`, `ihpix_wg_open_join`, `ihpix_wg_auto_contributor`, `ihpix_basemap_url` / `_attribution` / `_max_zoom` (basemap Leaflet; por defecto Esri Light Gray porque CARTO exige API key), `ihpix_markdown_preview_max_chars`, `ihpix_upload_max_mb`, `ihpix_publication_default_language` / `_default_license` / `_tags`, `ihpix_course_proposals_enabled` / `_per_day` → [[Variables de Entorno]].

## Operación

- `ckan ihpix seed-data`, `ckan ihpix recompute-summary`, `ckan ihpix seed-workspaces` → [[Comandos Utiles#IHP-IX: Ingesta de datos]].
- Tests puros: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py` → [[Testing]].

## Pendientes conocidos

Ver DOC-008 (títulos oficiales de Outputs), DOC-018/021 (autor y país de las filas del seed), DOC-019 (datasets/eventos sin `came_from`), DOC-022/023 (alcance del piloto y leads iniciales), DOC-028 (rol editor para subir publicaciones; verificación en dev del modal) en [[Backlog Documentacion]].
