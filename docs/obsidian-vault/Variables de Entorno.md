# Variables de Entorno

> Todas las claves de configuración y variables de entorno usadas por `ckanext-theme-ejemplo`.

---

## Claves de configuración del plugin

Estas claves se definen en el archivo de configuración de CKAN (`ckan.ini`) y se leen con `toolkit.config.get()`.

### Caching

| Clave | Default | Descripción |
|---|---|---|
| `ckanext.theme_ejemplo.courses_cache_ttl` | `600` (10 min) | TTL del caché de cursos UNESCO Open Learning |
| `ckanext.theme_ejemplo.groups_cache_ttl` | `300` (5 min) | TTL del caché de estados miembros e iniciativas |
| `ckanext.theme_ejemplo.home_cache_ttl` | `300` (5 min) | TTL del caché de datasets destacados y estadísticas del sitio |
| `ckanext.theme_ejemplo.recently_added_cache_ttl` | `300` (5 min) | TTL del caché de datasets/documentos recientes |
| `ckanext.theme_ejemplo.tracking_cache_ttl` | `300` (5 min) | TTL del caché de estadísticas de tracking (mínimo 60s) |

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
