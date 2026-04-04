# Testing

> Estrategia, infraestructura y ejecución de tests para `ckanext-theme-ejemplo`.

---

## Estado actual

> [!warning] Cobertura limitada
> Actualmente solo existen 2 archivos de test con cobertura mínima. La mayoría de los módulos no tienen tests.

| Archivo | Tests | Módulo testeado |
|---|---|---|
| `test_plugin.py` | 1 (placeholder) | `plugin.py` — test básico de carga |
| `test_utils.py` | ~14 | `utils.py` — validación de imágenes de usuario |

### Módulos sin tests
- `actions.py` (45 acciones)
- `controller.py` (67 vistas)
- `helpers.py` (25 helpers)
- `model.py` (6 modelos)
- `auth.py` (41 funciones)
- `validators.py` (3 validadores)

---

## Cómo ejecutar tests

### Prerrequisitos

Los tests requieren una instancia CKAN con servicios de infraestructura:
- PostgreSQL
- Solr
- Redis

En CI, esto se logra con Docker containers. Ver [[Deployment#CI/CD Pipeline]].

### Comandos

```bash
# Ejecutar todos los tests
pytest --ckan-ini=test.ini

# Ejecutar un archivo específico
pytest --ckan-ini=test.ini ckanext/theme_ejemplo/tests/test_plugin.py

# Ejecutar un test por nombre
pytest --ckan-ini=test.ini -k "test_normalize_user_image_url"

# Con cobertura (como en CI)
pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo
```

---

## Configuración de test

### test.ini

```ini
[app:main]
use = config:../ckan/test-core.ini
ckan.plugins = theme_ejemplo
```

> [!note] Ruta relativa
> `test.ini` referencia `../ckan/test-core.ini`. En CI, esto apunta al test-core.ini del contenedor CKAN. En local, necesitas ajustar la ruta o tener CKAN instalado en la ubicación esperada.

### .coveragerc

```ini
[report]
omit =
    */site-packages/*
    */python?.?/*
    ckan/*
```

---

## Dependencias de testing

Definidas en `dev-requirements.txt`:

```
pytest-ckan
```

`pytest-ckan` proporciona:
- Fixture `ckan_config` para cargar configuración
- Fixture `clean_db` para reset de base de datos
- Soporte para `--ckan-ini` flag
- Integración con CKAN test factories

---

## Tests existentes en detalle

### test_utils.py — Tests de validación de imagen

| Test | Verifica |
|---|---|
| `test_normalize_user_image_url_keeps_external_urls` | URLs externas (http/https) no se modifican |
| `test_normalize_user_image_url_prefixes_uploaded_filenames` | Filenames se prefijan con `/uploads/user/` |
| `test_normalize_user_image_url_preserves_existing_uploads_path` | Paths existentes con `/uploads/user/` no se duplican |
| `test_normalize_user_image_url_rejects_html_uploads` | Archivos .html se rechazan |
| `test_normalize_user_image_url_rejects_non_image_data_urls` | Data URIs no-imagen se rechazan |
| + ~9 tests adicionales | Validación de extensiones, MIME types, magic bytes |

### Clase helper: DummyUpload

Mock de objeto upload con: `filename`, `content_type`, `stream`

---

## CI Pipeline

El workflow de CI está en `.github/workflows/test.yml`. Ver [[Deployment#CI/CD Pipeline]] para detalles completos.

Resumen del job de tests en CI:
1. Levanta PostgreSQL, Solr, Redis como services Docker
2. Instala dependencias del sistema (gcc, geos-dev, etc.)
3. Instala Shapely < 2 y forks de extensiones CKAN
4. Instala la extensión en modo desarrollo
5. Inicializa base de datos CKAN
6. Ejecuta pytest con cobertura

---

## Ver también

- [[Comandos Utiles#Testing]] — Comandos de testing
- [[Deployment]] — CI/CD completo
- [[Backlog Documentacion]] — Tests pendientes de crear
