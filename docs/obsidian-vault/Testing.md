# Testing

> Estrategia, infraestructura y ejecución de tests para `ckanext-theme-ejemplo`.

---

## Membresías de iniciativas

`test_initiative_membership.py` usa CKAN, PostgreSQL y servicios de pruebas
aislados. Comprueba permisos por iniciativa, roles, rechazo/reintento, usuarios
inactivos, exclusión de Member States/organizaciones, solicitudes simultáneas,
resoluciones simultáneas, conservación de roles existentes, rollback y correos.

```bash
pytest --ckan-ini=test.ini ckanext/theme_ejemplo/tests/test_initiative_membership.py -q
```

Las pruebas limpian la BD: nunca usar una configuración de desarrollo compartido
o producción. La validación de navegador debe cubrir formulario, panel, historial,
CSRF, móvil/escritorio y la portada especial de AI for Water. Ver
[[Membresias de Iniciativas]].

Verificación local del 2026-10-09 con CKAN 2.10.9, PostgreSQL 15, Solr 9 y
Redis 7 aislados: **19 pruebas nuevas aprobadas**; **44 pruebas existentes
aprobadas** de aprobaciones, plugin, cabecera y constantes IHP-IX. Dos pruebas
IHP-IX existentes fallan también en el commit base `b1b1fe6`, con la misma
configuración:

- `test_ihpix_report_form_uses_kit_components`: el formulario anónimo no trae
  los dos combobox esperados.
- `test_ihpix_course_propose_requires_login`: el cliente sigue la redirección
  al login y obtiene 200; la prueba espera 302/403.

El entorno carga `activity theme_ejemplo`, crea el esquema real de Pages para
la portada AI y neutraliza únicamente los dos helpers opcionales de login de
Citizen Science. Los correos se interceptan en las pruebas, sin envíos externos.
En CKAN 2.10 se usan los plugins pytest incluidos en CKAN
(`ckan.tests.pytest_ckan.ckan_setup` y `ckan.tests.pytest_ckan.fixtures`).

Playwright comprobó login con retorno al formulario, envío con y sin mensaje,
estado pendiente, resumen de dos iniciativas, aprobación como editor, presencia
en Members, rechazo con nota e historial en la portada especial AI. Formulario,
panel e historial se revisaron en escritorio y móvil de 390 px, sin
desbordamiento horizontal; el panel se revisó también en español. Los catálogos
compilados es/fr/ar conservan todas las traducciones anteriores y añaden las
nuevas. Esta verificación es local; no valida un despliegue ni la entrega SMTP.

## Estado actual

> [!warning] Cobertura limitada
> Actualmente solo existen 2 archivos de test con cobertura mínima. La mayoría de los módulos no tienen tests.

| Archivo | Tests | Módulo testeado |
|---|---|---|
| `test_plugin.py` | 1 (placeholder) | `plugin.py` — test básico de carga |
| `test_utils.py` | ~14 | `utils.py` — validación de imágenes de usuario |
| `test_ihpix_forms.py` | 23 | `ihpix_forms.py` — validación del reporte IHP-IX (módulo puro, corre sin CKAN); incluye límites largos, URL, fechas, ratios y `MESSAGES/details` |
| `test_ihpix_links.py` | 15 | `ihpix_links.py` — validación de adjuntos del reporte (módulo puro), tipo `course` y `parse_course_id` |
| `test_ihpix_publications.py` | 18 | `ihpix_publications.py` — modal "Upload a publication": filtrado por esquema (13 vs 29 campos), slugs, autores (subcampos name/orcid/affiliation), contact_email obligatorio, errores del esquema (módulo puro) |
| `test_ihpix_constants.py` | 9 | `ihpix_constants.py` (títulos de Output desde JSON, PA por Output), `ihpix_i18n_strings.py` (cobertura de taxonomías y mensajes de validación) y guardas de plantillas: snippets importables como módulo, sin `{# #}` anidados, sin `_('%(x)s')` sin kwargs |
| `test_ihpix_workspaces.py` | 11 | `ihpix_workspaces.py` — reglas de membresía y permisos de los working groups (módulo puro) |

### Módulos sin tests
- `actions.py` (45 acciones)
- `controller.py` (67 vistas)
- `helpers.py` (25 helpers)
- `model.py` (6 modelos)
- `auth.py` (41 funciones)
- `validators.py` (3 validadores)

---

## Humo en dev

`scripts/ihpix_dev_smoke.py` se ejecuta **dentro del pod** de dev y renderiza
las páginas IHP-IX (públicas, logueadas y admin) como el primer sysadmin activo,
con un token de API temporal que revoca al final. Falla si alguna devuelve 5xx
o si el formulario de reporte no trae los marcadores del kit.

```bash
POD=$(kubectl --context default -n ckan get pods -o name | grep pod/ckan- | grep -v datapusher | head -1)
kubectl --context default -n ckan exec -i $POD -c ckan -- python3 - < scripts/ihpix_dev_smoke.py 2>/dev/null
```

Para validar cambios sin reconstruir la imagen: `kubectl cp` de los ficheros al
pod y volver a lanzar el script (el proceso es nuevo y lee el disco).

## Navegador real (Playwright) contra dev

`scripts/playwright/ihpix_dev.js` recorre con Chromium headless el flujo
completo del ecosistema IHP-IX en `data.dev-wins.com` con sesión por **token de
API** (cabecera `Authorization`, sólo hacia el sitio; no se teclean
contraseñas): combobox de país por teclado, picker de Member States, editor
Markdown con preview, curso del catálogo adjuntado, modal "Upload a
publication" con subida de PDF, autosave por usuario tras recargar, validación
de fechas, guardado del borrador, viewport móvil 390 px (sin desbordamiento),
árabe RTL, modal en el workspace y páginas admin (acordeón, MultiPicker,
descripción Markdown, autocompletado de lead). Registra errores de consola y
respuestas 4xx/5xx.

```bash
# tokens: api_token_create desde el pod para un editor no sysadmin y un sysadmin
(cd /ruta/privada && npm i playwright)   # el repo no lleva node_modules
export NODE_PATH=/ruta/privada/node_modules IHPIX_PW_TOKENS=/ruta/privada/tokens.json
node scripts/playwright/ihpix_dev.js
# validar un cambio del kit sin reconstruir la imagen:
LOCAL_KIT=ckanext/theme_ejemplo/public/js/ihpix-forms.js node scripts/playwright/ihpix_dev.js
```

Crea un borrador "Playwright IHP-IX draft (delete me)" y una publicación
"…smoke publication (delete me)" del usuario editor: borrarlos después
(`ihpix_report_delete` / `dataset_purge`) y revocar los tokens. Ejecutada en
verde el 2026-09-25 (16 pasos, 0 errores de consola).

## Cómo ejecutar tests

### Historial de licencias

`test_license_history_template.py` renderiza el override
`templates/overrides/snippets/changes/license.html` con títulos/URLs ausentes y combinaciones
con y sin enlaces. También verifica el escape HTML y los cierres de enlaces.
Estas pruebas no necesitan servicios CKAN:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_license_history_template.py
```

El override permite leer actividades antiguas sin título de licencia sin
modificar los metadatos del dataset ni el registro histórico.
Se registra en `extra_template_paths` porque `activity` precede al tema en
la lista de plugins de dev. Sólo ese directorio tiene prioridad; los overrides
configurados por el operador conservan su posición.

### Búsqueda por abstract

`test_search.py` cubre la extracción de todas las traducciones, notas antiguas,
extras, JSON inválido y conservación de los metadatos originales. Corre sin CKAN:

```bash
python3 -m pytest --noconftest ckanext/theme_ejemplo/tests/test_search.py -q
```

`test_dataset_abstract_search.py` prueba búsquedas y sugerencias reales, palabras
repartidas entre título/abstract, relevancia, filtros, privacidad, edición/borrado
del abstract y reindexación de datasets existentes sin cambiar metadatos.
Requiere CKAN/PostgreSQL/Redis y un Solr **de pruebas**
con el `schema.xml` actualizado de `ckan-unesco-docker` (`abstract_ngram` de tipo
`text_ngram` y su copia a `text`). Usa fixtures que limpian la BD y el índice:

```bash
pytest --ckan-ini=test.ini ckanext/theme_ejemplo/tests/test_dataset_abstract_search.py -q
```

Verificación local del 2026-10-02: 54 pruebas enfocadas aprobadas (31 de lógica
pura, 17 de integración y 6 del plugin) con CKAN 2.10.9, Solr 9, PostgreSQL 15
y Redis 7 en contenedores aislados. No implica despliegue ni reindexación del portal.

Verificación posterior en dev (2026-10-02): workflow Docker
`37088211301` completado; tema `68393c7`, 655 datasets activos reindexados y
515 documentos del índice con abstract. La búsqueda pública `groundw` pasó de
30 a 68 resultados, `hydrogeo` de 2 a 13 y `subterr` de 15 a 33. Excluyendo
título y nombre, `groundw` pasó de 0 a 38. Playwright confirmó las sugerencias
por abstract y el envío del formulario, con el catálogo contenido en el viewport
en escritorio y móvil. Producción no se desplegó; ver [[Deployment]].

### Prerrequisitos generales

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

## Catálogo learning

La suite del nuevo plugin prueba contra CKAN/PostgreSQL/Solr/Redis aislados:
permisos, aprobación, re-revisión, archivos, facetas multivalor, relaciones,
idempotencia, curación, disponibilidad parcial, migración y formularios con CSRF.
No ejecutarla contra desarrollo o producción. Las regresiones del tema incluyen
`test_openlearning.py` y `test_search.py`; SchemingDCAT incluye el aislamiento
de auditoría de permisos cuando se consulta un nombre aún no creado.
La validación en navegador cubre catálogo, edición, relaciones y tamaño móvil.

## Encabezado responsive (2026-10-01)

Verificar inicio, catálogo y Rapid Response entre 320 y 1920 px, incluyendo 768/800/820/991/992/1024/1199/1366. En catálogo y Rapid Response, el ancho del documento debe coincidir con el viewport. En inicio, comparar además con la versión previa: la auditoría detectó desbordamiento preexistente fuera del encabezado (480 px de documento a 320 px), idéntico antes y después del parche. Comprobar el menú móvil abierto/cerrado, la navegación que pasa a varias líneas, el foco del buscador y su panel de sugerencias. Repetir con traducciones. La prueba del candidato debe cargar el CSS real del checkout en el orden de producción y repetirse con los assets de la imagen final y las URLs públicas. Ver [[Troubleshooting]].
