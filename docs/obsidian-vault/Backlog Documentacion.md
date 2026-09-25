# Backlog de Documentación

> Vacíos conocidos en la documentación y el proyecto. Actualizar conforme se resuelvan.

---

## Documentación pendiente

| ID | Área | Descripción | Prioridad |
|---|---|---|---|
| DOC-001 | Setup | Documentar URLs exactas de forks requeridos (verificar en CI workflow) | Alta |
| DOC-002 | Deployment | Documentar entorno de producción (servidor, infraestructura, proceso de deploy) | Alta |
| DOC-003 | API | Documentar endpoints de la API custom (45+ acciones) con ejemplos de request/response | Media |
| DOC-004 | Templates | Documentar convención de templates: qué blocks se pueden override, jerarquía | Media |
| DOC-005 | i18n | Documentar proceso completo de agregar un nuevo idioma | Baja |
| DOC-006 | Config | Documentar todas las claves de config de CKAN core que afectan al plugin | Media |
| DOC-007 | Admin | Crear guía de usuario para cada panel de administración | Media |
| DOC-008 | IHP-IX | Confirmar lista oficial completa de los 34 Outputs (códigos + títulos) con OIP UNESCO; hoy `ihpix_constants.OUTPUTS` solo tiene códigos. | Alta |
| DOC-009 | IHP-IX | Confirmar Key Activities por Output (form acepta texto libre por ahora). | Media |
| ~~DOC-010~~ | IHP-IX | **Resuelto 2026-09-24**: el export CSV del Admin Overview funciona (`?export=csv`, streaming, incluye adjuntos). El enlace XLSX se retiró porque `openpyxl` no es dependencia del plugin. | — |
| DOC-011 | IHP-IX | Guía paso-a-paso para IHP National Committees: cómo migrar del Microsoft Form al `/ihpix/report` interno. | Alta |
| DOC-012 | Módulos | `completeness.py` y `ranking.py` no están descritos en [[Modulos]] (solo el flujo en [[Flujos Importantes]] §13). | Media |
| DOC-013 | i18n | El `.pot` (`i18n/ckanext-theme_ejemplo.pot`) está desactualizado respecto a los templates: le faltan cadenas de los paneles admin (p. ej. `Save Order`) desde antes de este cambio. Los `.po`/`.mo` se editan y compilan a mano; falta regenerar el `.pot` completo con `extract_messages` en un commit aparte. | Media |
| DOC-014 | Helpers | `h.get_featured_datasets` ya no tiene consumidor dentro del repo desde que la portada muestra visores en vez de datasets; sigue registrado y el panel `/ckan-admin/featured-datasets` sigue operativo. Decidir si se retira. | Baja |
| ~~DOC-015~~ | Admin/i18n | **Resuelto 2026-09-24** (fase i IHP-IX): `templates/admin/ihpix_reports.html` ya usa `{{ _("An error occurred.")|tojson }}` en el literal JS; el panel vuelve a funcionar en `/fr`. | — |
| DOC-016 | Deployment | No hay pipeline documentado de CKAN hacia dev (`data.dev-wins.com`): en `ckan-unesco-docker` el workflow `deploy` sólo apunta a producción y `deploy-terria-dev` despliega TerriaMap. Pendiente por confirmar cómo se actualiza dev. | Media |
| ~~DOC-017~~ | IHP-IX/i18n | **Resuelto 2026-09-24** (fase iii): ~390 cadenas IHP-IX traducidas a es/fr/ar (169 añadidas + 224 rellenadas por idioma) directamente en los `.po` con `polib` y compiladas con `msgfmt`. El `.pot` sigue desactualizado (DOC-013). Quedan vacías ~159 cadenas es/fr y ~597 ar **no** relacionadas con IHP-IX. | — |
| DOC-021 | IHP-IX | `ihpix_activity.country` mezcla **slugs** de grupo (formulario) y **nombres** del seed Excel. `actions.ihpix_country_name` normaliza slug → título del grupo al recalcular el mapa, pero títulos distintos al nombre del seed producen filas duplicadas en `ihpix_country_summary` sin coordenadas. Decidir: migrar `country` a slug + resolver nombre en lectura, o cargar coordenadas para los títulos de grupo. | Media |
| DOC-022 | IHP-IX | Working groups: el kind `comment` del ledger está reservado sin UI; no hay notificaciones in-app (solo email + feed). Definir con UNESCO si el piloto necesita comentarios/hilos y si los observers ven borradores ajenos. | Media |
| DOC-023 | IHP-IX | El lead de cada workspace se asigna a mano en `/ckan-admin/ihpix/workspaces`. Pendiente por confirmar con UNESCO la lista inicial de leads por Output (¿focal points del OIP?) y si se auto-asigna al primer reportante publicado. | Alta |
| DOC-024 | IHP-IX/i18n | Cadenas de la fase iv (workspaces, membresías, emails de working group), del kit de formularios y del pase UX del reporte (2026-09-24) traducidas es/fr/ar en los `.po`; el `.pot` sigue sin regenerar (DOC-013). | Baja |
| DOC-027 | IHP-IX/UX | El picker de Member States del **perfil de usuario** sigue siendo la versión a mano; migrarlo al `MultiPicker` del kit para unificar (los del reporte y admin ya lo usan / lo usarán en la fase D). Pendiente también el atajo "Upload training material" de KPI 3 (fase C, modal de publicación con `document_type=educational_material`). | Baja |
| DOC-018 | IHP-IX | `reported_by` de las filas del seed Excel es texto libre o vacío: esas actividades no aparecen en "mis reportes" ni en el futuro directorio de contribuidores. Decidir si se asignan a un usuario "IHP Secretariat" o se dejan sin autor. | Baja |
| DOC-019 | IHP-IX | Los atajos "Create a publication / event" de la Sección VII abren `/documents/new` (scheming, fork externo) y `/water-events/new` (ckanext-pages) en otra pestaña porque esos formularios **no soportan `came_from`**. Si el fork lo añade, bastará cambiar el enlace. | Baja |
| ~~DOC-020~~ | IHP-IX | **Resuelto 2026-09-24**: verificado en el checkout del fork (`ckanext-pages@RapidResponseAndRecovery`): `private`, `submission_status` e `ihp_organization` son **columnas** de `Page`. `_search_water_events` filtra por ellas (fallback por `extras` si faltan). Sigue siendo cierto que "webinar" es solo un tipo de adjunto. | — |
| DOC-025 | IHP-IX | Los enlaces "Create an event/news" apuntaban a `/water-events/new` y `/water-news/new`, rutas que **no existen** en el fork (crear = `/water-events_edit` / `/water-news_edit`, endpoints `pages.water_events_new` / `pages.water_news_new`). Corregido con `h.ihpix_pages_url`. Pendiente: las pestañas de eventos por organización leen `extras.organization_id` mientras el fork guarda la org en la columna `ihp_organization`. | Media |
| DOC-026 | Tema/UX | `public/theme_ejemplo_enhanced.js` bloqueaba en silencio el envío de cualquier form con un `[required]` vacío (clase `.error` sin CSS). Retirado 2026-09-24. Quedan como seguimiento fuera de IHP-IX: `data-module="image-upload2"` referenciado en `macros/form/image_upload.html` pero inexistente (el toggle URL/subida de los forms de grupo no funciona) y los `fetch` sin CSRF de `admin/featured_publications.html` y `admin/portal_cards.html`. | Media |

---

## Tests pendientes

| ID | Módulo | Descripción | Prioridad |
|---|---|---|---|
| TEST-001 | `actions.py` | Tests para las 45 acciones custom | Alta |
| TEST-002 | `controller.py` | Tests de integración para rutas principales | Alta |
| TEST-003 | `helpers.py` | Tests unitarios para los 25 helpers | Media |
| TEST-004 | `model.py` | Tests para los 6 modelos y sus métodos | Media |
| TEST-005 | `auth.py` | Tests para funciones de autorización | Media |
| TEST-006 | `validators.py` | Tests para los 3 validadores | Baja |
| TEST-007 | IHP-IX | Hecho: `test_ihpix_forms.py` (17), `test_ihpix_links.py` (12), `test_ihpix_constants.py` (5), `test_ihpix_workspaces.py` (10) y rutas/visibilidad en `test_plugin.py`. Pendiente: tests con BD (`clean_db`) para `ihpix_report_update` (transiciones owner/sysadmin), `ihpix_report_review` (email, transiciones, recompute, ledger + auto-contributor), `_sync_activity_links` (full replace), `get_contributor_stats`, `recompute_from_activities`, join/approve de workspaces y la migración `_migrate_ihpix_reported_by`. | Media |

---

## Mejoras técnicas pendientes

| ID | Área | Descripción | Prioridad |
|---|---|---|---|
| TECH-001 | CI | Agregar triggers automáticos (push, PR) al workflow de CI | Alta |
| TECH-002 | README | Actualizar README.md con información real del proyecto (aún tiene TODOs del template) | Alta |
| TECH-003 | setup.py | Actualizar metadata: author, author_email, description, url | Media |
| TECH-004 | MANIFEST.in | Referencia a `README.rst` pero el archivo es `README.md` | Baja |

---

## Información por confirmar

Elementos marcados como "Pendiente por confirmar" en la documentación:

| Ubicación | Qué falta confirmar |
|---|---|
| [[Setup Local]] | URLs exactas de los forks de extensiones |
| [[Deployment]] | Stack y proceso de producción |
| [[Variables de Entorno]] | Si existen variables de entorno adicionales no documentadas en el código |

---

## Cómo contribuir

1. Verificar un ítem de esta lista
2. Actualizar la nota correspondiente en la vault
3. Marcar el ítem como resuelto aquí
4. Si descubres un nuevo vacío, agregarlo a esta lista

---

## Ver también

- [[Guia de Mantenimiento]] — Cómo mantener esta documentación
- [[Testing]] — Estado actual de tests
