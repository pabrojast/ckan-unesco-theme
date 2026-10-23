# Deployment

> CI/CD, packaging y proceso de release para `ckanext-theme-ejemplo`.

---

## CI/CD Pipeline

### Ubicación
`.github/workflows/test.yml`

### Trigger
`workflow_dispatch` — ejecución manual solamente.

> [!note] Pendiente por confirmar
> No hay triggers automáticos (push, pull_request). El CI se ejecuta solo manualmente.

### Entorno

| Componente | Detalle |
|---|---|
| Runner | `ubuntu-latest` |
| Container | `openknowledge/ckan-dev:2.9` |
| Python | 3.x (del container) |

### Servicios Docker

| Servicio | Imagen | Config |
|---|---|---|
| PostgreSQL | `ckan/ckan-postgres-dev:2.9` | user: postgres, password: postgres |
| Solr | `ckan/ckan-solr:2.9` | — |
| Redis | `redis:3` | — |

### Variables de entorno del CI
Ver [[Variables de Entorno#Variables de entorno del CI]] para la lista completa.

### Pasos del pipeline

```
1. Checkout del código
2. Instalar paquetes del sistema:
   - gcc, libc-dev, geos-dev, geos, gfortran, musl-dev, python3-dev
   - py3-numpy, py3-setuptools
3. Instalar Shapely < 2
4. Instalar forks de extensiones CKAN:
   - ckanext-spatial (fork mjanez)
   - ckanext-dcat (fork mjanez)
   - ckanext-scheming (oficial)
   - ckanext-schemingdcat (fork mjanez)
5. Instalar la extensión:
   - pip install -e .
   - pip install -r requirements.txt
   - pip install -r dev-requirements.txt
6. Configurar test.ini:
   - Actualizar ruta a test-core.ini del container
7. Inicializar DB:
   - ckan -c test.ini db init
8. Ejecutar tests:
   - pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo
```

---

## Dependencias de extensiones CKAN

> [!warning] Forks específicos
> Se usan forks, no las versiones oficiales de PyPI.

| Extensión | Repositorio | Propósito |
|---|---|---|
| ckanext-spatial | `github.com/mjanez/ckanext-spatial` | Búsqueda espacial |
| ckanext-dcat | `github.com/mjanez/ckanext-dcat` | Catálogo DCAT |
| ckanext-scheming | `github.com/ckan/ckanext-scheming` | Schemas custom |
| ckanext-schemingdcat | `github.com/mjanez/ckanext-schemingdcat` | Schemas DCAT |

---

## Proceso de release

### 1. Actualizar versión

Editar `setup.py`:
```python
version='X.Y.Z',
```

### 2. Crear distribución

```bash
python setup.py sdist bdist_wheel && twine check dist/*
```

### 3. Subir a PyPI

```bash
twine upload dist/*
```

### 4. Tag en Git

```bash
git commit -a -m "Release vX.Y.Z"
git tag X.Y.Z
git push && git push --tags
```

---

## Distribución (MANIFEST.in)

Archivos incluidos en el paquete distribuido:

```
README.rst
LICENSE
requirements.txt
ckanext/theme_ejemplo/**/*.html    # Templates
ckanext/theme_ejemplo/**/*.json    # Configuración
ckanext/theme_ejemplo/**/*.js      # JavaScript
ckanext/theme_ejemplo/**/*.less    # Estilos LESS
ckanext/theme_ejemplo/**/*.css     # Estilos CSS
ckanext/theme_ejemplo/**/*.mo      # Traducciones compiladas
ckanext/theme_ejemplo/**/*.yml     # Configuración YAML
ckanext/theme_ejemplo/migration/** # Migraciones (si existen)
```

---

## Despliegue a desarrollo (data.dev-wins.com)

Dev (contexto kubectl `default`, ns `ckan`) corre imágenes construidas a mano
sobre el digest que ya está desplegado, fijadas por digest con `kubectl set
image` sólo en el contenedor `ckan`. La receta para el tema está en el repo de
despliegue: `deploy/docker/Dockerfile.ihpix-dev` + `deploy/docker/ihpix-dev.md`
(rama `feat/ihpix-forms-dev-20260925`). Resumen:

```bash
BASE=$(kubectl --context default -n ckan get deploy ckan -o jsonpath='{.spec.template.spec.containers[?(@.name=="ckan")].image}')
docker build -f deploy/docker/Dockerfile.ihpix-dev --build-arg BASE_IMAGE="$BASE" --build-arg THEME_REF="$(git rev-parse HEAD)" -t pabrojast/ckan-base210:ihpix-forms-dev-<sha7>-<fecha> .
docker push … && DIGEST=$(docker buildx imagetools inspect … --format '{{.Manifest.Digest}}')
kubectl --context default -n ckan set image deployment/ckan ckan=pabrojast/ckan-base210@$DIGEST
kubectl --context default -n ckan rollout status deployment/ckan --timeout=15m
```

> [!warning] Otras líneas de trabajo comparten dev
> El Dockerfile principal instala `ckan-unesco-theme@dev210`, pero dev puede
> llevar el tema en otra rama (el 24/09/2026 corría `feat/learning-catalog`).
> Antes de construir, comprobar el commit del tema en el pod
> (`git -c safe.directory=… -C /app/src/ckanext-theme-ejemplo log -1`) y fusionar
> esa rama en `dev210` si hace falta; nunca retirar trabajo ajeno de dev.

**Validar antes de reconstruir**: `kubectl cp` de los ficheros cambiados al pod y
`kubectl exec -i $POD -c ckan -- python3 - < scripts/ihpix_dev_smoke.py`. El
script arranca un proceso nuevo (el uwsgi en marcha no se entera) y renderiza
las páginas IHP-IX como sysadmin con el cliente de pruebas de Flask. Ver
[[Testing#Humo en dev]] (desde 2026-10 el paquete del pod es de root: usar la
copia en `/tmp/theme-overlay` descrita allí).

> [!warning] La migración de 2026-10 escribe en la tabla de actividades
> La primera vez que arranca un proceso con el modelo de 2026-10-11,
> `_migrate_ihpix_activities()` añade `key_activity_code`, `training_type_other`
> y `legacy_normalized_at` y **normaliza las filas heredadas** (alias de valores,
> puertas KPI derivadas de los conteos; ver
> [[Flujos Importantes#7.5 Normalización de los datos heredados (2026-10)]]).
> Antes de desplegar en producción respaldar `ihpix_activity` (en dev se hizo el
> 2026-10-11 a `~/backups/ckan-dev-ihpix-20261011/ihpix-backup.json` desde el
> pod, sin psql). Es idempotente: el CLI `ckan ihpix normalize-legacy` permite
> ensayar antes (`--apply` para escribir).

### Registro — 2026-10-12 (IHP-IX ciclo 3: formulario completo + progreso)

- Base: `pabrojast/ckan-base210@sha256:7ceef7ffe8f8e3025b5e657603ffb8e3bd4bc5dc19d7b4f365dda657f23fd7a4`
  (dev corría el tema en `9e89d32`, merge del rediseño de la home, PR #3).
- El commit de IHP-IX se rebaseó sobre `origin/dev210` antes de construir
  (`69b0740` → **`64dad73`**, único solape `plugin.py`, sin conflictos) y se
  publicó `dev210`; la imagen `Dockerfile.ihpix-dev` descarga el commit de GitHub.
- Imagen: `pabrojast/ckan-base210:ihpix-progress-dev-64dad73-20261012`, digest
  `sha256:c09610374e415e28bcab05e2120afa91540b770a7136f5d9f8547a86fafc2e5e`.
  Deployment previo guardado fuera de Git para rollback (`kubectl set image` al
  digest base).
- Respaldo previo: `~/backups/ckan-dev-ihpix-20261012/ihpix-backup.json`
  (745 actividades, ya normalizadas el 2026-10-11: el arranque no volvió a
  escribir en `ihpix_activity`, sin trazas de migración en el log).
- Verificación en la imagen desplegada: `scripts/ihpix_dev_smoke.py` en el pod
  (24 páginas 200/302, marcadores completos, `ihpix_progress_stats` 744
  actividades / 191 Member States / KPI 2 = 120 579); HTTP público (`/ihpix`
  200, `/ihpix/progress*` 302 a login para anónimos, `/ihpix/dashboard` 302 a
  `/ihpix/progress`); `scripts/playwright/ihpix_progress.js` contra
  `https://data.dev-wins.com` con tokens temporales (revocados): 30/30 pasos,
  sin errores de consola ni respuestas ≥ 400. Producción no se tocó.

> [!note] Fallos que sólo aparecen con CKAN real (2026-09-25)
> El parseo local de Jinja no detecta: comentarios `{# #}` anidados (dejan
> código vivo), macros importados sin `with context` (`h` indefinido),
> `_('… %(x)s …')` sin kwargs (gettext newstyle hace `texto % kwargs`),
> helpers del tema llamados como `h.x()` en el controller (son `toolkit.h.x()`)
> y `h.pager_url` en rutas con parámetros. Hay tests puros que cubren los tres
> primeros.

## Entorno de producción

> [!note] Pendiente por confirmar
> No hay documentación explícita del entorno de producción en el repositorio. Información inferida:

- **Stack probable**: CKAN 2.9 + Apache/Nginx + PostgreSQL + Solr + Redis
- **Deployment**: Instalación del paquete en virtualenv de CKAN + restart del servidor web
- **Tablas custom**: Se crean automáticamente al iniciar el plugin (idempotente)
- **Migraciones**: Soportadas por `model.py` (agrega columnas nuevas sin perder datos)

---

## Ver también

- [[Setup Local]] — Configuración del entorno de desarrollo
- [[Testing]] — Ejecución de tests
- [[Comandos Utiles#Packaging y distribución]] — Comandos de packaging
- [[Variables de Entorno]] — Configuración completa

## Learning en desarrollo

El catálogo se empaqueta mediante `deploy/docker/Dockerfile.learning-dev` en el
repositorio Docker, con commits fijos del tema y SchemingDCAT sobre la imagen
de desarrollo existente. El destino autorizado es `default/ckan`
(`https://data.dev-wins.com`). La imagen y configuración de producción no forman
parte de este despliegue. Respaldar DB, almacenamiento local y configuración
antes de migrar; conservar la tabla legado y el digest anterior. Ver la guía
`docs/learning-development.md` del repositorio Docker para rollback y verificaciones.

## Búsqueda por abstract en desarrollo (2026-10-02)

En `ckan-unesco-docker`, rama `miserver-2.10`, el workflow `push.yml` admite
`theme_search_only=true`. Usa una imagen base fijada por digest y el commit del
tema publicado en `dev210`; prepara `abstract_ngram` y su copia a `text` mediante
Schema API antes del rollout, conservando los demás campos. Después espera la
readiness y reindexa los datasets activos en lotes de 100.

```bash
gh workflow run push.yml --repo pabrojast/ckan-unesco-docker \
  --ref miserver-2.10 -f theme_search_only=true
```

El destino está limitado a `default/ckan`, host `data.dev-wins.com`, y se comprueba
el digest anterior. Solo cambia la imagen web de CKAN, conservando sidecars,
configuración y volúmenes. La guía y el rollback están en
`deploy/docker/abstract-search-dev.md` del repositorio Docker.

La rama `production` del repositorio Docker usa ahora `THEME_REF=dev210` para
futuras construcciones, en lugar del commit fijo `c7a1a54`. Publicar esa referencia
no despliega producción. Ver [[Busqueda]] y [[Testing#Búsqueda por abstract]].

## IHP-IX revisión de septiembre — DEV 2026-10-21

Destino exclusivo `kubectl --context default -n ckan`, deployment `ckan`, contenedor `ckan`. La imagen se construye sobre el digest **vigente** de DEV con `scripts/docker/Dockerfile.ihpix-dev`, conservando las otras extensiones. Exportar solamente el commit revisado a `theme/` del contexto, sin cambios locales ajenos:

```bash
THEME_REVISION=$(git rev-parse HEAD)
BUILD_DIR=$(mktemp -d /tmp/ihpix-build.XXXXXX)
mkdir "$BUILD_DIR/theme"
git archive "$THEME_REVISION" | tar -x -C "$BUILD_DIR/theme"
cp scripts/docker/Dockerfile.ihpix-dev "$BUILD_DIR/Dockerfile"
BASE_IMAGE=$(kubectl --context default -n ckan get deploy ckan -o jsonpath='{.spec.template.spec.containers[?(@.name=="ckan")].image}')
docker build --build-arg BASE_IMAGE="$BASE_IMAGE" --build-arg THEME_REVISION="$THEME_REVISION" \
  -t "pabrojast/ckan-base210:ihpix-review-${THEME_REVISION:0:7}" "$BUILD_DIR"
```

Antes del rollout: respaldo PostgreSQL de todas las tablas `ihpix_*`, deployment JSON y huellas por ID de actividades/adjuntos/espacios/membresías/contribuciones. Validar el dump y la imagen final en CKAN aislado; publicar la imagen, obtener su digest y actualizar **solo** el contenedor web. Reconsultar el digest base justo antes: si cambió, reconstruir sobre el nuevo. No reutilizar un respaldo marcado `.incomplete`.

La migración agrega seis columnas y cinco tablas; no reejecuta la normalización histórica. Conservar digest anterior para rollback de imagen; no eliminar las columnas/tablas nuevas ni restaurar un dump sobre escrituras posteriores sin evaluarlas. Después: esperar rollout, comparar huellas de las 745 actividades históricas, verificar 744 publicadas/1 pendiente, cuatro contenedores Ready, fuente y rutas públicas/autenticadas. Recomputar únicamente el resumen derivado por país.

No se modifican los sidecars `c4w-archive`, `dashboard-build` o `dashboard-query`, ni configuración/imagen de producción. Evidencia funcional: [[IHP-IX Review September 2026]].

### Evidencia de publicación y despliegue

- Código funcional: `c0822793c33c78cfdf80d255939bcebae0d42182`; ajuste RTL y regresión de administrador: `99216c790381548bad7a60834c8a302b800e8a1c`. Ambos publicados en `origin/dev210`.
- Imagen final: `pabrojast/ckan-base210@sha256:57d5c8146c84da57bd7340791f4e1c4446c87ded85328d53ffec73a92ba4895c` (tag `ihpix-review-99216c7-20261021`). La primera imagen de esta entrega fue `sha256:d9bd8cdc9b2aeefc9e55daa81c3b0ef68cb6edda201b80be90dd25b2b5839ca1`; el ajuste final cambia CSS y prueba de navegador.
- Base anterior a la entrega: `sha256:ffef066904c4aa07753720cf6966b707257c5774ef4b5da8b46c284b17c2f54b`. Se preservaron exactamente los tres sidecars.
- Respaldo: `/home/pabrojast/backups/ckan-dev-ihpix-20261021/ihpix-before-release.dump`, restaurado con éxito en PostgreSQL 17 aislado; 744 publicadas y 1 pendiente. `deployment-before-release.json` y `ihpix-before-fingerprint.json` conservan configuración y huellas. El archivo `.incomplete` de un intento anterior no se usa.
- Comparación por ID/SHA-256: 745 actividades históricas, 34 espacios, 5 contribuciones y sus tablas de adjuntos/membresías idénticos antes/después. Se recalcularon 191 resúmenes derivados de países.
- Fuente desplegada: 657 archivos del tema comparados con Git. Estadísticas coinciden con SQL independiente: 744 actividades publicadas, KPI2 120579, jóvenes 38069 y mujeres 39721.
- QA del código: 146 tests puros, 29 checks HTTP principales, 15 de privacidad/geografía, 4 de rollback/importación y 16 de navegador sobre la imagen final; adicionalmente se verificó que ambas APIs rechazan borrar un reporte de espacio archivado sin perder adjuntos.
- Subida real de publicación, adjuntar dataset y crear/adjuntar evento verificados en la copia local. Para probar almacenamiento LOCAL se instaló `lockfile==0.12.2` solo en el contenedor QA; DEV conserva su proveedor de almacenamiento configurado. El último archivo se escribió en almacenamiento aislado, eliminado al retirar QA. Tres cargas temporales del primer ensayo alcanzaron el proveedor heredado: se verificó su contenido y se eliminaron, comprobando su ausencia antes de continuar con LOCAL.
- HTML/PDF: presentación 16:9 con 27 páginas para el ámbito general; tablas dentro de los límites. Narrativa A4 con márgenes y fuentes enlazadas. Navegador móvil EN/ES/FR/AR a 390×844 y caso admin árabe sin desbordamiento.
- Publicación Git, imagen y rollout se verifican por separado. No se ejecutó el workflow manual histórico de CKAN 2.9 ni se desplegó producción.

Los cinco contenedores QA, su red y el core Solr temporal se retiraron al terminar; el core Solr original quedó intacto. No se crearon reportes ni membresías de prueba en DEV. El único token temporal de lectura para el smoke se revoca al cerrar la verificación.

Durante el cierre se inició otro despliegue de DEV con imagen `sha256:81bbac65adf5550e432be697de462372f3c71b2988935df48f96762a09d7dc25`. Se verificó que conserva exactamente los 657 archivos del tema y `.theme-revision=99216c7`; no se sobrescribió esa actualización concurrente.

Cierre verificado: imagen integrada `81bbac65…`, pod `ckan-74478f6bd5-zdpbm`, cuatro contenedores Ready y cero reinicios; páginas nuevas, cinco ámbitos de progreso, workbook y navegador EN/ES/FR/AR (incluido admin RTL) aprobados. Huellas históricas idénticas también en esa imagen.

La publicación reveló que la regla de GitHub exigía `Theme checks` pero solo existía el workflow manual `Tests`. Se añadió `.github/workflows/theme-checks.yml` con el nombre requerido para ejecutar automáticamente las regresiones puras, taxonomía y sintaxis de JavaScript. No tiene credenciales ni pasos de despliegue.

## IHP-IX usabilidad — DEV 2026-10-22

- Código publicado en `dev210`: `587775fde02476cd332325ed28f70ce2375794b0`. Botones/fichas de relaciones, países sin slugs visibles, mensajes de error comprensibles y perfil de reportes adaptable. Ver [[IHP-IX Review September 2026#Ajustes de usabilidad — 2026-10-22]].
- CI `Theme checks` correcto: [ejecución 39779275016](https://github.com/pabrojast/ckan-unesco-theme/actions/runs/39779275016), 146 pruebas puras, taxonomía y sintaxis JS. La imagen final pasó 34 comprobaciones de navegador en CKAN aislado.
- Imagen base: digest DEV vigente `sha256:81bbac65adf5550e432be697de462372f3c71b2988935df48f96762a09d7dc25`, conservando las otras extensiones. Construcción desde `git archive`, sin los cambios locales ajenos de iniciativas.
- Imagen desplegada en `default/ckan`: `pabrojast/ckan-base210@sha256:9f37b8a9b75b323737ace3183f46849f6cf881bded1241c0e96620c270a34265` (tag `ihpix-ux-587775f-20261022`). Rollout completado; pod `ckan-7d7785dcf4-5q9cj`, 4/4 Ready y cero reinicios. Los tres sidecars mantienen sus imágenes anteriores.
- Los 657 archivos de la extensión en el pod coinciden con la exportación Git. Respaldo `ihpix-before.dump` restaurado en PostgreSQL 17 aislado: 746 reportes. Huellas completas antes/después idénticas para reportes (744 published, 1 pending, 1 draft), adjuntos, 34 grupos de trabajo, membresías y 5 contribuciones; el borrador `TEST` conserva su contenido y fecha.
- Respaldo y evidencia privada en `/home/pabrojast/backups/ckan-dev-ihpix-ux-20261022/`. No se ejecutaron migraciones de contenido ni cambios en producción.

## Comprobación adicional de Progress (2026-10-22)

El workflow vigente `.github/workflows/theme-checks.yml` ejecuta también `node --check` sobre `ihpix-progress.js`, además de las regresiones IHP-IX y la taxonomía. El procedimiento de esta mejora en DEV se documenta en [[IHP-IX Progress UX October 2026]].

## Entrega SLD — procedimiento exclusivo de DEV

Construir con `scripts/docker/Dockerfile.sld-dev` sobre el digest vigente. El
contexto `patch/` contiene exclusivamente los archivos `ckanext/` del diff de
esta entrega y los nuevos; conserva ajustes ajenos de la imagen base. La marca
`.theme-sld-revision` identifica el commit del parche. El Docker clásico puede
rechazar esta base por profundidad de capas: usar Buildx con driver
`docker-container` y snapshotter `native`, exportando directamente al registro.

Antes del rollout, respaldar Deployment, CronJob `pageviews-flush`, contadores
PostgreSQL y pendientes Redis; registrar el digest base y huellas de archivos
ajenos. Revalidar la imagen vigente inmediatamente antes de actualizar. Actualizar
sólo el contenedor web CKAN y la imagen del CronJob, preservando sus restantes
campos y sidecars. Suspender temporalmente el cron durante la reconciliación,
esperar trabajos activos, simular y aplicar con respaldo; reanudar su estado
anterior y verificar al menos dos consolidaciones y el navegador. Renovar sólo
las claves de caché anónima del tema. No tocar producción.
