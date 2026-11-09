# IHP-IX

Hub de la implementación del **reporting y gestión del conocimiento IHP-IX** en IHP-WINS (requisito contractual 7, fases i–iv, 2026-09). Esta nota solo orienta: el detalle vive en las notas enlazadas.

> [!info] Qué es
> El portal `/ihpix` permite a los usuarios de IHP-WINS **reportar actividades** del Plan Estratégico IHP-IX (2022–2029) con el formulario oficial (PDF 2026), **adjuntar** publicaciones, webinars, eventos y datos, **explorar** lo reportado por Output / Priority Area / contribuidor, y colaborar en **working groups** (uno por Output).

## Mapa rápido

| Bloque | Qué hace | Dónde está documentado |
|---|---|---|
| **Reporte** (`/ihpix/report`, `/ihpix/report/<id>/edit`, `/user/<id>/ihpix`) | Formulario PDF 2026 con borradores en servidor, edición/reenvío, cola de revisión con email y campana | [[Flujos Importantes#7. Portal IHP-IX]] · [[Modulos#ihpix_forms.py]] |
| **Adjuntos** (Sección VII) | Publicaciones (datasets `documents`), eventos (páginas `water-events`), datasets y enlaces asociados a cada reporte | [[Flujos Importantes#7.1 Adjuntos (Sección VII)]] · [[Modulos#ihpix_links.py]] |
| **Descubribilidad** (`/ihpix/outputs`, `/ihpix/outputs/<code>`, `/ihpix/priority-area/<pa>`, `/ihpix/contributors`) | Páginas navegables para usuarios logueados; landing pública | [[Flujos Importantes#7.2 Visibilidad (2026-09)]] · [[Flujos Importantes#7.3 Recompute del resumen por país]] |
| **Progreso** (`/ihpix/progress`, `/pa/<pa>`, `/output/<code>`, `/flagship/<slug>`, `/ctwg/<slug>`) | Dashboards que replican los Power BI oficiales (KPI 1–8, mapa, % mujeres/jóvenes) por ámbito, con filtros de bienio, región, país y organización; `/ihpix/dashboard` redirige | [[Flujos Importantes#7. Portal IHP-IX]] punto 4 · [[Modulos#ihpix_stats.py]] |
| **Informes y presentación** (`/ihpix/reports/generate`, `/ihpix/presentation`) | Documento A4 y diapositivas 16:9 con gráficos SVG generados en servidor, secciones seleccionables y anexo de fuentes; mismo registro de secciones para ambas salidas | [[IHP-IX Reports UX October 2026]] · [[Modulos#Informes y presentación con gráficos SVG (2026-10-23)]] |
| **Working groups** (`/ihpix/workspaces`) | Piloto: un workspace por Output, membresías (lead / contributor / observer) y ledger de contribuciones | [[Flujos Importantes#7.4 Working groups (workspaces por Output)]] · [[Modulos#ihpix_workspaces.py]] |
| **Admin** (`/ckan-admin/ihpix/*`) | Contenido, actividades, cola de revisión, overview (CSV, recompute) y working groups | [[Arquitectura#Paneles de administración]] |

## Módulos

- `ihpix_constants.py` — taxonomías oficiales (5 PA, 34 Outputs, 21 flagships, KPIs…), títulos de Output desde `data/ihpix_output_titles.json` y key activities desde `data/ihpix_key_activities.json` (generados del snapshot oficial con `scripts/build_ihpix_taxonomy_data.py`).
- `ihpix_forms.py`, `ihpix_links.py`, `ihpix_workspaces.py`, `ihpix_publications.py`, `ihpix_normalize.py` (alias y puertas de los datos heredados), `ihpix_stats.py` (agregación de los dashboards de progreso) — módulos **puros** con la lógica de validación/reglas; testeados sin CKAN.
- Puentes al ecosistema (2026-09-24): modal "Upload a publication" (crea datasets `documents` y los adjunta), tipo de adjunto `course` + propuesta de cursos Open Learning, "Add a dataset" prellenado → [[Flujos Importantes#7.1 Adjuntos (Sección VII)]].
- `ihpix_charts.py` (SVG puro) e `ihpix_report_sections.py` (registro de secciones del informe y de las diapositivas, 2026-10-23) → [[Modulos#Informes y presentación con gráficos SVG (2026-10-23)]].
- `ihpix_entities.py` (puro, 2026-10-23): ámbito de la pestaña IHP-IX de cada grupo (Member State → país; iniciativa → flagship/CTWG) y fichas enlazables de cada actividad → [[Modulos#ihpix_entities.py (2026-10-23)]], [[IHP-IX Entity Links October 2026]].
- `ihpix_org_match.py` (puro, 2026-10-24): sugerencias para vincular instituciones heredadas (texto) con organizaciones CKAN; las aplica el sysadmin en `/ckan-admin/ihpix/institutions` → [[Modulos#ihpix_org_match.py (2026-10-24)]], [[IHP-IX Entity Links October 2026]].
- `ihpix_i18n_strings.py` — literales de taxonomías para Babel; los templates traducen valores con `h.ihpix_t`.
- Kit de formularios `public/js/ihpix-forms.js` + `public/css/ihpix-forms.css` (Combobox, MultiPicker, MarkdownEditor, CharCounter, Toast, Modal, FileUpload; se carga con `ihpix/snippets/forms_assets.html`) → [[Modulos#Kit de formularios IHP-IX]]. El reporte lo usa desde 2026-09-24 (pase UX: ver [[Flujos Importantes#7. Portal IHP-IX]] punto 3).
- Rediseño 2026-10-11 (línea IHP, tokens: tinta `#0B2A4A`, azul UNESCO `#0069B4`/`#004E8C`, papel `#F4F8FC`, radio 6px, sin sombras): `public/css/ihpix-report.css` + `public/js/ihpix-report.js` (formulario) y `public/css/ihpix-progress.css` + `public/js/ihpix-progress.js` (dashboards). Mockup en el artefacto Design "IHP-IX reporting redesign".
- Modelos: `IhpixActivity`, `IhpixActivityLink`, `IhpixWorkingGroup`, `IhpixWorkingGroupMember`, `IhpixContribution`, `IhpixCountrySummary`, `IhpixContent` → [[Modulos#model.py]].

## Configuración

`ckanext.theme_ejemplo.ihpix_recompute_on_approve`, `ihpix_geojson_max`, `ihpix_wg_open_join`, `ihpix_wg_auto_contributor`, `ihpix_basemap_url` / `_attribution` / `_max_zoom` (basemap Leaflet; por defecto Esri Light Gray porque CARTO exige API key), `ihpix_markdown_preview_max_chars`, `ihpix_upload_max_mb`, `ihpix_publication_default_language` / `_default_license` / `_tags`, `ihpix_course_proposals_enabled` / `_per_day`, `ihpix_stats_cache_ttl`, `ihpix_key_activities_file` → [[Variables de Entorno]].

## Operación

- `ckan ihpix seed-data`, `ckan ihpix recompute-summary`, `ckan ihpix seed-workspaces`, `ckan ihpix normalize-legacy` → [[Comandos Utiles#IHP-IX: Ingesta de datos]].
- Tests puros: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py` → [[Testing]].

## Pestañas IHP-IX de grupos y organizaciones (2026-10-23, sin desplegar)

Reporte de UNESCO: las actividades del explorador no aparecían en las pestañas
IHP-IX de iniciativas, Member States y organizaciones. Causas y arreglos en
[[IHP-IX Entity Links October 2026]]; código en `dev210` sin desplegar.

**Vinculación asistida de instituciones (2026-10-24, sin desplegar)**: la pestaña
de cada organización sólo lista actividades con `institution_org_id`. El panel
sysadmin `/ckan-admin/ihpix/institutions` agrupa las instituciones heredadas
(texto) sin organización, propone coincidencias (`ihpix_org_match`) y aplica la
selección con `ihpix_institution_link` (una revisión por actividad; reversible
con "Unlink"). Ver [[IHP-IX Entity Links October 2026]] y
[[Flujos Importantes#7. Portal IHP-IX]].

## Informes y presentación rediseñados (2026-10-23, sin desplegar)

`/ihpix/reports/generate` y `/ihpix/presentation` pasan de texto y tablas a
fichas, gráficos SVG en servidor y secciones modulares. Código en `dev210`
**sin desplegar** (ni imagen ni `kubectl set image`); verificado con la suite
pura (216 pruebas) y un render con helpers simulados + Playwright local
(escritorio, móvil, 14 diapositivas y PDF A4/16:9). Ver
[[IHP-IX Reports UX October 2026]].

## Revisión de septiembre implementada (2026-10-21)

Ver [[IHP-IX Review September 2026]] para formulario, relaciones múltiples, colaboración, XLSX, narrativas, presentaciones y evidencia. El estado de despliegue actualizado está en [[Deployment]]. Las notas anteriores se conservan como historial.

## Estado en dev (2026-10-11): ciclo 3 verificado sin desplegar

Formulario completo rediseñado, dashboards de progreso y normalización de
heredados están en `dev210` **sin desplegar** (ni imagen ni `kubectl set
image`). Verificado contra la base real de dev con una copia del tema en
`/tmp/theme-overlay` del pod (el paquete del pod es de root; ver
[[Testing#Humo en dev]]): smoke de 24 páginas en verde (las 5 rutas de
progreso incluidas, `/ihpix/dashboard` → 302), migración aplicada en dev
(3 columnas, 745 filas revisadas, 744 normalizadas; respaldo previo en
`~/backups/ckan-dev-ihpix-20261011/`), `ihpix_progress_stats` cuadra con la
SQL (744 publicadas, 191 Member States, KPI 2 = 120 579) y navegador real
con `scripts/playwright/ihpix_progress.js` por `port-forward` (formulario
desktop/móvil/RTL, los cinco ámbitos de progreso, filtro de bienio vía API,
"Show as table", redirección). Para llevarlo a dev: receta de
[[Deployment#Despliegue a desarrollo (data.dev-wins.com)]] con respaldo
previo de `ihpix_activity`.

## Estado en dev (2026-09-25)

Desplegado en `data.dev-wins.com` (tema `dev210`, que fusionó
`feat/learning-catalog`). Verificado desde el pod: las 22 páginas IHP-IX
renderizan como sysadmin; `ihpix_publication_create` creó de verdad un dataset
`documents` público (tags `ihp-ix`/`ihp-ix-output-1.3`, grupo del Member State,
`document_type`, idioma, identificador, recurso PDF subido y variante por URL),
registró `publication_created` en el ledger y los datos de prueba se purgaron.
Traducciones es/fr/ar y RTL comprobadas. También verificado con un **editor
no sysadmin** (crea en su organización, otra se rechaza) y en **navegador
real** con Playwright (16 pasos: kit, modal con subida de PDF, autosave,
móvil, RTL, workspace, admin; ver [[Testing#Navegador real (Playwright) contra dev]]).
Cursos vía el plugin `learning` cuando está cargado (DOC-030). Ver
[[Deployment#Despliegue a desarrollo (data.dev-wins.com)]].

## Pendientes conocidos

Ver DOC-008 (títulos de Outputs derivados del Excel, cotejar con el OIP), DOC-031 (lista oficial de key activities), DOC-032 (etiquetas canónicas de los tipos KPI), DOC-033 (paleta por PA y daltonismo), DOC-034 (regenerar `.pot`), DOC-018/021 (autor y país de las filas del seed), DOC-019 (datasets/eventos sin `came_from`), DOC-022/023 (alcance del piloto y leads iniciales), DOC-028 (rol editor para subir publicaciones) en [[Backlog Documentacion]].

## Formulario guiado y recuperación (2026-11-06)

El reporte distribuye las secciones I–VI en **Datos de la actividad**, la sección VII en **Archivos y recursos** y el resumen/envío en **Revisar y enviar**. Los adjuntos siguen siendo opcionales. El borrador se guarda automáticamente en la cuenta al introducir un título; las respuestas incompletas o sin conexión mantienen respaldo local e indicador de sincronización. Enviar sigue siendo una acción explícita del paso 3. Ver [[Flujos Importantes#Formulario IHP-IX en tres pasos y guardado automático (2026-11-06)]].

### Subidas uniformes en el paso 2 (2026-11-06)

Dataset y evento usan ahora el mismo patrón de ventana dentro del reporte que los tres tipos de publicación. Cada ventana permite completar los datos, adjuntar un archivo o URL y recibir errores sin navegar fuera. Las respuestas y el archivo seleccionado se conservan al cerrar/reabrir durante la misma visita; tras crear el recurso, su asociación se guarda con el borrador del reporte. Los campos del modal todavía sin enviar no se recuperan tras recargar toda la página.

Los datasets exigen los metadatos mínimos reales del catálogo y respetan la visibilidad elegida (privado por defecto). Los eventos admiten agenda/folleto opcional y pasan por revisión antes de publicarse. La navegación atrás y los tres pasos del reporte se mantienen. Ver [[Modulos#Recursos inline en el reporte IHP-IX (2026-11-06)]] y [[Flujos Importantes#Crear todos los adjuntos dentro del paso 2 (2026-11-06)]].

## Espacios por grupo y planificación (noviembre de 2026)

La entrada `/ihpix/workspaces` organiza cinco OETWG y tres CTWG. Cada grupo contiene Outputs, plan por bienio, seguimiento, documentos privados, miembros/contactos y conversaciones con tareas. Las rutas históricas por Output continúan disponibles y conservan sus permisos.

Una **actividad planificada** es distinta de un reporte `IhpixActivity`. Su propuesta recoge descripción, Output/actividad clave, responsable, institución, socios y cuatro compromisos textuales (2022–2023, 2024–2025, 2026–2027, 2028–2029). Vacío significa sin compromiso informado. El formulario ofrece tres pasos: actividad/compromisos, documentos/recursos, revisión/envío. Guarda borradores en servidor y mantiene una copia local por usuario para recuperación; revisiones concurrentes producen un conflicto visible.

La revisión recorre `draft → submitted → approved/returned`. Aprueban responsables del grupo o leads del Output correspondiente. El seguimiento independiente usa `planned/ongoing/completed/cancelled`. Editar un plan aprobado conserva su fotografía acordada hasta aprobar la nueva versión, incluidos los documentos aprobados. Los planes nunca alimentan los indicadores de Progress. **Report execution** crea un borrador del formulario existente, vinculado al plan, sin copiar compromisos como resultados, indicadores o fechas reales.

Los roles de grupo son responsable, colaborador y observador. Un lead de Output no se convierte automáticamente en responsable del grupo. Las membresías antiguas se muestran a responsables para conciliarlas explícitamente. Importar contactos no crea cuentas, concede permisos ni envía invitaciones; vincular una cuenta existente exige correo coincidente.

### Libros de referencia e importación

La importación siempre presenta filas corregibles y decisiones antes de confirmar. Se admiten los libros de planes originales y la exportación de la plataforma; contactos; y reportes históricos de ejecución/en curso. Estos últimos utilizan la validación y guardado del formulario de reportes existente y se crean como borradores. Las coincidencias con reportes accesibles se pueden vincular sin sobrescribirlas. El año de una hoja no demuestra que una actividad haya finalizado.

La inspección local de las fuentes entregadas identificó 185 propuestas en OETWG1, 64 en OETWG IV, 164 contactos consolidados, 141 filas en Priority_Area_4_Report y 58 en RCTWS. En contactos, las hojas por Output contienen copias del padrón con filas ocultas; sólo se asignan Outputs con una marca explícita, consolidando personas y conservando las filas de procedencia. Las cantidades corresponden a lectura de fuentes, no a datos importados en DEV.

Cada lote conserva archivo, hoja, fila y valores originales (en reportes). Repetir la confirmación devuelve los mismos registros. Los archivos modificados muestran coincidencias para conciliación; no sustituyen automáticamente datos existentes. La exportación del plan crea una hoja por Output y escribe respuestas como texto para impedir fórmulas de Excel.

### Documentos y colaboración

Los documentos internos se suben en el mismo modal del kit de formularios, hasta 20 MB, con categorías y versiones. Se guardan en PostgreSQL y se descargan mediante una ruta autorizada, como adjuntos, sin caché pública. La creación de recursos del catálogo es una acción separada y usa sus permisos/publicación habituales. Conversaciones y tareas admiten responsable, fecha, estado y vínculo con una actividad/documento. No se implementan chat en tiempo real, videollamadas ni coedición Office.

## Calendario y paso del plan al reporte (2026-11-07)

Cada grupo tiene una pestaña Calendario: mes navegable, agenda accesible en móvil y actividades «Por programar». Las fechas `planned_start`/`planned_end` son opcionales; un bienio o un año del Excel nunca genera una fecha exacta. Se muestran intervalos explícitos de planes y vencimientos de tareas autorizadas. Los filtros se conservan al navegar meses. El XLSX exportado incluye las fechas al final, sin cambiar las columnas originales.

El recorrido visible es **1. Planificar y programar → 2. Reportar ejecución**. Tras la aprobación se elige un bienio con compromiso; se crea o retoma el borrador propio de ese plan y bienio. Se copian título, clasificación (incluidas contribuciones adicionales), focal point, institución, correo válido y partners si cumplen el límite oficial. Resultados, indicadores y fechas reales se completan en el formulario oficial. El reporte permite consultar los compromisos del plan acordado actual, sin sincronización que sobrescriba respuestas. Una nueva revisión del plan no modifica reportes existentes.

La demo autorizada conserva siete archivos privados y sus hashes: 185 filas de OETWG I y 64 de OETWG IV (247 actividades distintas), 164 contactos sin cuentas/permisos nuevos y 199 filas históricas en vista previa para conciliación. Los planes permanecen en borrador y sin fechas inventadas. Dos filas idénticas de OETWG IV comparten una actividad y mantienen ambas procedencias. Un correo inválido queda vacío en el campo editable; el original permanece íntegro en la procedencia y el XLSX. Las 141 filas del reporte PA4 y 58 del libro RCTWS se consultan en Seguimiento; aún no se convierten en resultados publicados.
