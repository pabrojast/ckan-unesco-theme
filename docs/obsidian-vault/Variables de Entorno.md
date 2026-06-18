# Variables de Entorno

> Todas las claves de configuración y variables de entorno usadas por `ckanext-theme-ejemplo`.

---

## Claves de configuración del plugin

Estas claves se definen en el archivo de configuración de CKAN (`ckan.ini`) y se leen con `toolkit.config.get()`.

### Caching

| Clave | Default | Descripción |
|---|---|---|
| `ckanext.theme_ejemplo.courses_cache_ttl` | `600` (10 min) | TTL del micro-caché en memoria de la lectura de cursos desde BD (helper `get_latest_courses`) |
| `ckanext.theme_ejemplo.groups_cache_ttl` | `300` (5 min) | TTL del caché de estados miembros e iniciativas |
| `ckanext.theme_ejemplo.home_cache_ttl` | `300` (5 min) | TTL del caché de datasets destacados y estadísticas del sitio |
| `ckanext.theme_ejemplo.recently_added_cache_ttl` | `300` (5 min) | TTL del caché de datasets/documentos recientes |
| `ckanext.theme_ejemplo.tracking_cache_ttl` | `300` (5 min) | TTL del caché de estadísticas de tracking (mínimo 60s) |

#### Caché de respuestas anónimas

> [!note]
> Mitiga la "spider trap" de las búsquedas con facetas (`/dataset/?_X_sort=...`). Sólo aplica a `GET`/`HEAD` sin cookie de sesión y respuestas `200` text/JSON/XML. Usa Redis (vía `ckan.lib.redis.connect_to_redis`) con fallback a un LRU local.

| Clave | Default | Descripción |
|---|---|---|
| `ckanext.theme_ejemplo.anon_cache_enabled` | `false` | Activa el caché de respuestas anónimas (recomendado en producción) |
| `ckanext.theme_ejemplo.anon_cache_ttl` | `300` (5 min) | TTL en segundos de cada entrada |
| `ckanext.theme_ejemplo.anon_cache_max_bytes` | `1048576` (1 MB) | Tamaño máximo del body para guardarlo en caché |
| `ckanext.theme_ejemplo.anon_cache_include_paths` | _(vacío = todo)_ | Prefijos de path a cachear (CSV). Si está vacío, se cachea todo lo no excluido |
| `ckanext.theme_ejemplo.anon_cache_exclude_paths` | `/api,/ckan-admin,/user,/dashboard,/feeds,/util,/_tracking,/membership-requests,/bug-tickets` | Prefijos a saltar siempre |

> [!tip]
> Para desactivar puntualmente el caché en una request (debug), añade `?_nocache=1` o el header `Cache-Control: no-cache`. Las respuestas servidas/guardadas exponen `X-Anon-Cache: HIT|MISS`.

### Open Learning (cursos curados)

Ver [[Open Learning]] para el flujo completo de sincronización y curación.

| Clave | Default | Descripción |
|---|---|---|
| `ckanext.theme_ejemplo.openlearning_search_terms` | `water,ihp,hydrology,climate change,groundwater,flood,drought,water management,water governance,wash,sdg6,transboundary,ecohydrology,water education,water quality,aquifer` | Términos de búsqueda contra la API (CSV) |
| `ckanext.theme_ejemplo.openlearning_sync_ttl` | `21600` (6 h) | TTL del sync lazy; `0` desactiva el sync automático (queda solo CLI/botón admin) |
| `ckanext.theme_ejemplo.openlearning_max_pages` | `10` | Tope de páginas a seguir por término de búsqueda |
| `ckanext.theme_ejemplo.openlearning_page_size` | `50` | `page_size` enviado a la API |

### Funcionalidad

| Clave | Default | Descripción |
|---|---|---|
| `ckanext.theme_ejemplo.index_followers` | `false` | Habilitar indexación de seguidores de datasets en Solr |

---

## Variables de entorno del CI

Definidas en `.github/workflows/test.yml` para el entorno de pruebas Docker:

| Variable | Valor en CI | Descripción |
|---|---|---|
| `CKAN_SQLALCHEMY_URL` | `postgresql://ckan_default:pass@postgres/ckan_test` | URL de conexión a PostgreSQL |
| `CKAN_DATASTORE_WRITE_URL` | `postgresql://datastore_write:pass@postgres/datastore_test` | URL de escritura del datastore |
| `CKAN_DATASTORE_READ_URL` | `postgresql://datastore_read:pass@postgres/datastore_test` | URL de lectura del datastore |
| `CKAN_SOLR_URL` | `http://solr:8983/solr/ckan` | URL de conexión a Solr |
| `CKAN_REDIS_URL` | `redis://redis:6379/1` | URL de conexión a Redis |

---

## Configuración del plugin en CKAN

```ini
# Activar el plugin (obligatorio)
ckan.plugins = theme_ejemplo

# Ejemplo de configuración completa
ckanext.theme_ejemplo.courses_cache_ttl = 600
ckanext.theme_ejemplo.groups_cache_ttl = 300
ckanext.theme_ejemplo.home_cache_ttl = 300
ckanext.theme_ejemplo.recently_added_cache_ttl = 300
ckanext.theme_ejemplo.tracking_cache_ttl = 300
ckanext.theme_ejemplo.index_followers = false

# Cursos UNESCO Open Learning (caché curada)
ckanext.theme_ejemplo.openlearning_search_terms = water
ckanext.theme_ejemplo.openlearning_sync_ttl = 21600
ckanext.theme_ejemplo.openlearning_max_pages = 10
ckanext.theme_ejemplo.openlearning_page_size = 50

# Caché de respuestas anónimas (mitiga spider trap)
ckanext.theme_ejemplo.anon_cache_enabled = true
ckanext.theme_ejemplo.anon_cache_ttl = 300
ckanext.theme_ejemplo.anon_cache_max_bytes = 1048576
# Vacío = cachea todo lo no excluido
# ckanext.theme_ejemplo.anon_cache_include_paths =
ckanext.theme_ejemplo.anon_cache_exclude_paths = /api,/ckan-admin,/user,/dashboard,/feeds,/util,/_tracking,/membership-requests,/bug-tickets
```

---

## Variables de entorno del sistema

> [!note] Inferencia
> El plugin no lee variables de entorno del sistema directamente. Toda la configuración se pasa a través del archivo `ckan.ini` usando el mecanismo estándar de CKAN (`toolkit.config`). Sin embargo, CKAN core sí soporta variables de entorno para configuración base (ver documentación de CKAN).

---

## Servicios Docker del CI

| Servicio | Imagen | Puerto |
|---|---|---|
| PostgreSQL | `ckan/ckan-postgres-dev:2.9` | 5432 |
| Solr | `ckan/ckan-solr:2.9` | 8983 |
| Redis | `redis:3` | 6379 |
| CKAN | `openknowledge/ckan-dev:2.9` | — |

---

## Ver también

- [[Setup Local]] — Cómo configurar el entorno
- [[Deployment]] — Pipeline de CI/CD
- [[Arquitectura#Estrategia de caching]] — Detalles de caching
