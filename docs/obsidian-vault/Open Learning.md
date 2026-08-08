# Open Learning

> Caché persistente **curada** de cursos de la plataforma [UNESCO Open Learning](https://openlearning.unesco.org/). Reemplaza el consumo directo de la API en la home (2026-06).

---

## Problema que resuelve

La API de Open Learning (`/api/courses/v1/courses/?search_term=water`) no filtra bien por programa: devuelve cursos que no pertenecen al Intergovernmental Hydrological Programme (IHP) y no distingue cursos permanentes (self-paced) de cursos con fechas fijas. Antes la home mostraba los primeros 8 resultados crudos sin posibilidad de curación.

## Diseño

```
API Open Learning ──sync──► tabla open_learning_course ──get_public()──► home + /courses
                              ▲
                              │ curación (approve/hide/tipo)
                       /ckan-admin/open-learning (sysadmin)
```

- **Tabla** `open_learning_course` ([[Modulos#model.py|model.py]], modelo `OpenLearningCourse`): una fila por curso de la API, con datos de display + campos de curación.
- **Sync** ([[Modulos#openlearning.py|openlearning.py]]): upsert que **preserva la curación** — nunca toca `status` ni `display_order` de filas existentes.
- **Cursos nuevos** entran con `status='pending'` (ocultos) hasta que un sysadmin los aprueba.
- **Cursos que desaparecen de la API** se marcan `is_available=False` (no se borran: si reaparecen, recuperan su curación). Esto **solo ocurre si el fetch fue 100% exitoso** (`full_success`), para que una caída parcial de la API no desactive cursos por error.
- **Tipo de curso**: auto-detectado del campo `pacing` de Open edX (`self` → `permanent`, `instructor` → `scheduled`; fallback por `start_type`/`end`). El admin puede corregirlo manualmente, lo que activa `course_type_override` y el sync deja de recalcularlo.

## Disparadores del sync

| Disparador | Mecanismo |
|---|---|
| Lazy (automático) | `maybe_sync_courses()` en el helper de la home y la vista `/courses`; TTL `openlearning_sync_ttl` (default 6 h) contra `max(last_seen_at)` en BD + cooldown de 5 min en memoria |
| Manual (admin) | Botón "Sync now" en `/ckan-admin/open-learning` (acción `open_learning_sync`) |
| CLI / cron | `ckan -c ckan.ini openlearning sync --force` — ver [[Comandos Utiles]] |

> [!note]
> No hay celery/scheduler en el stack; el sync lazy + cron cubre la actualización periódica.

## Rutas

| Ruta | Vista (`MyLogica`) | Acceso |
|---|---|---|
| `GET /courses` | `courses()` — dos secciones: self-paced y scheduled | Público |
| `GET /ckan-admin/open-learning` | `open_learning_admin()` | Sysadmin |
| `POST /ckan-admin/open-learning/set-status` | `open_learning_set_status()` (AJAX) | Sysadmin |
| `POST /ckan-admin/open-learning/set-type` | `open_learning_set_type()` (AJAX) | Sysadmin |
| `POST /ckan-admin/open-learning/sync` | `open_learning_sync_now()` (AJAX) | Sysadmin |

## Templates

- `templates/snippets/course_card.html` — tarjeta reutilizable (home y `/courses`)
- `templates/courses/index.html` — página pública con secciones "Self-paced courses" y "Scheduled courses"
- `templates/admin/open_learning.html` — panel de curación (filtros por status, badges, select de tipo, sync)
- `templates/home/snippets/community_grid.html` / `community_mini_card.html` — la home muestra 3 cursos curados (`get_latest_courses()[:3]`) como mini-cards en la columna "Courses" del grid Community + enlace "View all courses"

## Configuración

Ver [[Variables de Entorno#Open Learning (cursos curados)]]: `openlearning_search_terms`, `openlearning_sync_ttl`, `openlearning_max_pages`, `openlearning_page_size`, `courses_cache_ttl`.

## Operación

1. Tras el deploy, ejecutar `ckan -c ckan.ini openlearning sync --force` (o pulsar "Sync now").
2. Entrar a `/ckan-admin/open-learning`: los cursos llegan como **Pending**.
3. Aprobar los cursos IHP relevantes; ocultar el resto. Corregir el tipo si la auto-detección falló.
4. La home y `/courses` muestran solo cursos `approved` + `is_available`.

> [!warning]
> Mientras no haya cursos aprobados, la sección de la home queda vacía (solo el enlace "View all courses") y `/courses` muestra un estado vacío con enlace a la plataforma.

> [!note] Inferencia
> El campo `pacing` se verificó contra la API real (2026-06): los cursos de "water" devuelven `self` o `instructor`. Si Open edX cambia el contrato, el fallback usa `start_type`/`end`.

## Ver también

- [[Modulos#openlearning.py]] — detalle del módulo de sync
- [[Flujos Importantes#11. Curación de cursos Open Learning]] — flujo paso a paso
- [[Variables de Entorno]] — claves de configuración
