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
- `ihpix_forms.py`, `ihpix_links.py`, `ihpix_workspaces.py` — módulos **puros** con la lógica de validación/reglas; testeados sin CKAN.
- `ihpix_i18n_strings.py` — literales de taxonomías para Babel; los templates traducen valores con `h.ihpix_t`.
- Modelos: `IhpixActivity`, `IhpixActivityLink`, `IhpixWorkingGroup`, `IhpixWorkingGroupMember`, `IhpixContribution`, `IhpixCountrySummary`, `IhpixContent` → [[Modulos#model.py]].

## Configuración

`ckanext.theme_ejemplo.ihpix_recompute_on_approve`, `ihpix_geojson_max`, `ihpix_wg_open_join`, `ihpix_wg_auto_contributor`, `ihpix_basemap_url` / `_attribution` / `_max_zoom` (basemap Leaflet; por defecto Esri Light Gray porque CARTO exige API key) → [[Variables de Entorno]].

## Operación

- `ckan ihpix seed-data`, `ckan ihpix recompute-summary`, `ckan ihpix seed-workspaces` → [[Comandos Utiles#IHP-IX: Ingesta de datos]].
- Tests puros: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py` → [[Testing]].

## Pendientes conocidos

Ver DOC-008 (títulos oficiales de Outputs), DOC-018/021 (autor y país de las filas del seed), DOC-020 (columnas de ckanext-pages), DOC-022/023 (alcance del piloto y leads iniciales) en [[Backlog Documentacion]].
