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
| `test_ihpix_forms.py` | 23 | `ihpix_forms.py` — validación del reporte IHP-IX (módulo puro, corre sin CKAN); incluye límites largos, URL, fechas, ratios y `MESSAGES/details` |
| `test_ihpix_links.py` | 15 | `ihpix_links.py` — validación de adjuntos del reporte (módulo puro), tipo `course` y `parse_course_id` |
| `test_ihpix_publications.py` | 18 | `ihpix_publications.py` — modal "Upload a publication": filtrado por esquema (13 vs 29 campos), slugs, autores (subcampos name/orcid/affiliation), contact_email obligatorio, errores del esquema (módulo puro) |
| `test_ihpix_constants.py` | 9 | `ihpix_constants.py` (títulos de Output desde JSON, PA por Output), `ihpix_i18n_strings.py` (cobertura de taxonomías y mensajes de validación) y guardas de plantillas: snippets importables como módulo, sin `{# #}` anidados, sin `_('%(x)s')` sin kwargs |
| `test_ihpix_workspaces.py` | 11 | `ihpix_workspaces.py` — reglas de membresía y permisos de los working groups (módulo puro) |
| `test_ihpix_normalize.py` | 13 | `ihpix_normalize.py` — alias de valores heredados (doble espacio, `2022 - 2023`, `Report`, stakeholder groups con paréntesis, multis con comas, flagship `No`), puertas derivadas, alias de país, idempotencia (módulo puro, 2026-10) |
| `test_ihpix_stats.py` | 12 | `ihpix_stats.py` — totales por ámbito, unión de los tres campos de país, región por índice, filas con puerta en `false` pero conteo > 0, "por tipo", dimensión por ámbito, `Unspecified`, porcentajes con total 0, matriz, no resueltos (módulo puro, 2026-10) |

Los tests puros IHP-IX (`test_ihpix_*.py`, 112 el 2026-10-11) corren sin CKAN: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py`. `test_ihpix_constants.py` comprueba además que los JSON de títulos y key activities cargan, que hay 18 flagships con slug de ida y vuelta y que cada literal nuevo está en `ihpix_i18n_strings.py`.

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

> [!warning] El paquete del pod es de root (2026-10-11)
> Desde el despliegue del 2026-10 `/app/src/ckanext-theme-ejemplo` pertenece a
> root y el contenedor corre como `ckan`: `kubectl cp` no puede sobrescribir.
> Alternativa que funcionó: copiar el árbol a `/tmp/theme-overlay`
> (`kubectl exec … -- cp -r /app/src/ckanext-theme-ejemplo/ckanext /tmp/theme-overlay/`),
> extraer ahí un tarball con los ficheros cambiados y lanzar los procesos con
> `PYTHONPATH=/tmp/theme-overlay` más un `sitecustomize.py` en esa carpeta que
> haga `ckanext.__path__.insert(0, '/tmp/theme-overlay/ckanext')` (el namespace
> `ckanext` de pkg_resources no respeta el orden de PYTHONPATH por sí solo).
> El smoke se lanza entonces con `python3 -c "import sys; sys.path.insert(0,
> '/tmp/theme-overlay'); import ckanext; ckanext.__path__.insert(0,
> '/tmp/theme-overlay/ckanext'); exec(open('/tmp/theme-overlay/scripts/ihpix_dev_smoke.py').read())"`.
> Ojo: cualquier proceso nuevo con el modelo nuevo aplica la migración (y la
> normalización de heredados) a la base de dev: respaldar antes
> (ver [[Deployment#Despliegue a desarrollo (data.dev-wins.com)]]).

El smoke incluye desde 2026-10-11 las cinco rutas de progreso, la redirección
de `/ihpix/dashboard`, los marcadores del formulario rediseñado
(`key_activity_code`, `training_type_other`, `UWMP`, `section-review`) y una
llamada a `ihpix_progress_stats` cuyos totales deben coincidir con la SQL
directa (`sum(stakeholders_knowledge)` de las publicadas, etc.).

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

### Formulario rediseñado y dashboards de progreso (2026-10-11)

`scripts/playwright/ihpix_progress.js` solo hace GET (no crea datos): comprueba
el formulario (23 obligatorios, 18 flagships, 12 tipos de formación, 13 puertas
sin valor por defecto, key activities filtradas por Output, tabla de revisión,
resumen de errores al enviar incompleto), móvil 390 px, árabe RTL, los cinco
ámbitos de progreso (tiles, ≥ 8 gráficos, franja de 34 outputs, mapa con
marcadores, filtro de bienio vía API, "Show as table") y la redirección del
dashboard antiguo; guarda capturas y `results.json`.

Para verificar **sin desplegar**: servidor de desarrollo en el pod con la copia
de `/tmp/theme-overlay` (`kubectl exec … -- env PYTHONPATH=/tmp/theme-overlay
ckan -c /srv/app/production.ini run -H 0.0.0.0 -p 5001 -r -t`) y
`kubectl port-forward pod/<ckan> 5001:5001`. El port-forward se cae con las
peticiones en paralelo del navegador, así que el script acepta
`IHPIX_PW_TUNNEL` (comando del port-forward) e `IHPIX_PW_SERVER` (comando que
reinicia el servidor) y los relanza él mismo cuando el sitio deja de responder:

```bash
NODE_PATH=/ruta/privada/node_modules IHPIX_PW_TOKENS=/ruta/privada/tokens.json \
IHPIX_PW_BASE=http://127.0.0.1:5001 \
IHPIX_PW_TUNNEL="kubectl --context default -n ckan port-forward pod/<ckan> 5001:5001" \
IHPIX_PW_SERVER=/ruta/privada/restart-server.sh \
node scripts/playwright/ihpix_progress.js
```

Playwright 1.58 necesita Chromium 1208 en `~/.cache/ms-playwright`; una
instalación 1.57 pide la 1200 y falla aunque haya otras builds.

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

## Aceptación IHP-IX de septiembre (2026-10-21)

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py
python3 scripts/build_ihpix_taxonomy_data.py --check
IHPIX_QA_TOKENS=/ruta/privada/tokens.json python3 scripts/ihpix_review_acceptance.py
```

El script HTTP exige localhost, cinco usuarios QA (`admin`, `author`, `collaborator`, `observer`, `outsider`) y tokens en JSON privado. El administrador QA es sysadmin; el espacio 1.10 debe existir, activo y sin lead. Usa copia aislada de DEV, registra baseline de publicados y elimina sus reportes al terminar. No apuntarlo a un port-forward de un entorno compartido: modifica membresías y estados de espacios durante las pruebas.

Resultados: 146 tests puros, 29 checks HTTP y pruebas adicionales de privacidad, rollback y navegador. Matriz y límites de la evidencia en [[IHP-IX Review September 2026]]. Estas comprobaciones no equivalen a ejecutar todo el CI histórico de CKAN 2.9.

El recorrido de navegador reproducible está en `scripts/playwright/ihpix_review.cjs` (Node + Playwright):

```bash
IHPIX_QA_TOKENS=/ruta/privada/tokens.json IHPIX_QA_OUTPUT=/tmp/ihpix-browser \
  node scripts/playwright/ihpix_review.cjs
```

Guarda capturas/PDF fuera de Git y elimina el reporte que crea al finalizar correctamente. `IHPIX_QA_BASE` permite otro puerto local; exige la misma instancia aislada del script HTTP. Los recorridos de archivos/eventos y Excel se validaron además con fixtures locales privados.

Regresiones reproducibles adicionales: `scripts/ihpix_review_privacy.py` (15 checks; además exige `IHPIX_QA_FIXTURES` con `package`/`package_name` de un dataset privado del autor, inaccesible al colaborador) y `scripts/ihpix_review_rollback.py` (4 checks; archiva/restaura 1.10 para provocar fallo en la segunda fila). Ejecutarlas secuencialmente en la instancia aislada, con `IHPIX_QA_TOKENS` definido. No usan archivos reales de usuarios.

## Control automático Theme checks

`.github/workflows/theme-checks.yml` ejecuta las 146 regresiones puras IHP-IX, verifica el snapshot oficial y la sintaxis de los tres scripts del navegador. Corre al publicar `dev210`, en pull requests y manualmente, con Python 3.11, permisos de lectura y acciones fijadas por SHA. Su job se llama exactamente `Theme checks`, como el control requerido por GitHub. Complementa las pruebas HTTP/navegador contra CKAN real; no sustituye al workflow manual `Tests` de CKAN 2.9 ni despliega entornos.

## Progress IHP-IX: países y navegación

`scripts/playwright/ihpix_progress_filters.cjs` prueba selección geográfica, coherencia de exportaciones, recuperación ante fallos, borradores y 80 combinaciones de página/idioma/viewport. La fixture aislada y las variables de ejecución se documentan en [[IHP-IX Progress UX October 2026]]. La suite pura incluye una regresión para impedir que un alias vacío resuelva a un país con nombre no latino.

## Importación guiada IHP-IX v2 (2026-10-23)

La suite pura suma 178 pruebas. `test_ihpix_bulk_v2.py` cubre mapeo completo, datos compartidos, indicadores, relaciones, archivos alterados, coordenadas XML reales, traducciones y compatibilidad. No requiere CKAN ni Babel; usa los catálogos MO incluidos.

`scripts/playwright/ihpix_bulk.cjs` requiere un CKAN local **desechable**: usa autor, usuario ajeno y admin, y archiva/restaura temporalmente el workspace 1.10 para comprobar rollback. No ejecutarlo mediante port-forward contra un entorno compartido. `scripts/playwright/fixtures/ihpix_bulk.py` genera fixtures y vacía únicamente las tablas de reportes/importaciones de la base local `ihpix_bulk`; exige `/qa/app.ini` y el host `ihpix-bulk-db`. Los usuarios y tokens se preparan separadamente en esa instancia.

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py
IHPIX_QA_FILES=/ruta/spreadsheets IHPIX_QA_TOKENS=/ruta/privada/tokens.json \
  IHPIX_QA_OUTPUT=/tmp/ihpix-bulk-browser node scripts/playwright/ihpix_bulk.cjs
```

`IHPIX_QA_BASE` admite otro puerto local (por defecto 5013). El JSON de tokens contiene `author`, `other` y `admin`; nunca se versiona. Se guardan resultados incluso si una comprobación falla. Las pruebas comparan valores persistidos, owner-only, idempotencia, rollback y retry, v1/v2, ejemplos/minimal/errores y cuatro idiomas entre 320 y 1440 px. La evidencia y las limitaciones de traducción oficial están en [[IHP-IX Bulk Import UX October 2026]].
