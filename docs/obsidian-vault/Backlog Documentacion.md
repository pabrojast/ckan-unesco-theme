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
| DOC-010 | IHP-IX | Documentar export XLSX del Admin Overview cuando se implemente (hoy solo CSV). | Baja |
| DOC-011 | IHP-IX | Guía paso-a-paso para IHP National Committees: cómo migrar del Microsoft Form al `/ihpix/report` interno. | Alta |
| DOC-012 | Módulos | `completeness.py` y `ranking.py` no están descritos en [[Modulos]] (solo el flujo en [[Flujos Importantes]] §13). | Media |
| DOC-013 | i18n | El `.pot` (`i18n/ckanext-theme_ejemplo.pot`) está desactualizado respecto a los templates: le faltan cadenas de los paneles admin (p. ej. `Save Order`) desde antes de este cambio. Los `.po`/`.mo` se editan y compilan a mano; falta regenerar el `.pot` completo con `extract_messages` en un commit aparte. | Media |
| DOC-014 | Helpers | `h.get_featured_datasets` ya no tiene consumidor dentro del repo desde que la portada muestra visores en vez de datasets; sigue registrado y el panel `/ckan-admin/featured-datasets` sigue operativo. Decidir si se retira. | Baja |
| DOC-015 | Admin/i18n | **Bug preexistente**: `templates/admin/ihpix_reports.html` interpola `{{ _("An error occurred.") }}` dentro de un literal JS entre comillas simples; la traducción francesa («Une erreur s'est produite.») rompe el parseo y deja el panel sin JS en `/fr`. Se arregla igual que en los otros paneles: `' + {{ _("An error occurred.")|tojson }}`. | Alta |

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
