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
`docker-container`, exportando directamente al registro. `COPY --link` agrega
el parche sin desempaquetar la base; incluir `patch/.theme-sld-revision` con el
commit exportado. Compilar y probar la fuente antes de construir la imagen.

Antes del rollout, respaldar Deployment, CronJob `pageviews-flush`, contadores
PostgreSQL y pendientes Redis; registrar el digest base y huellas de archivos
ajenos. Revalidar la imagen vigente inmediatamente antes de actualizar. Actualizar
sólo el contenedor web CKAN y la imagen del CronJob, preservando sus restantes
campos y sidecars. Suspender temporalmente el cron durante la reconciliación,
esperar trabajos activos, simular y aplicar con respaldo; reanudar su estado
anterior y verificar al menos dos consolidaciones y el navegador. Renovar sólo
las claves de caché anónima del tema. No tocar producción.

### Evidencia SLD — 2026-10-23

- Funcionalidad inicial `ba68671`, preparación de imagen/QA `c1a63fa` y
  traducción árabe final `08128a5`. PR [#4](https://github.com/pabrojast/ckan-unesco-theme/pull/4)
  hacia `dev210`; se incorporó además su cambio concurrente `4cf47e1` sin perder
  las secciones de documentación de ninguna entrega.
- Imagen final web y CronJob: `pabrojast/ckan-base210@sha256:2fbf429417c2f71c900c17bb4c9f01c2fd56cec50a34bf17ad0bf2eaa151a1e4`,
  marca `.theme-sld-revision=08128a596445e98442b3d0ccc09e048d5aafbde2`.
  Primer parche funcional `sha256:64a7b03d16dbd2dfe4c9e1f10afb8583f8c5d0b844aa40b40f7c74c11626c7ea`,
  sobre la base vigente `sha256:44d0fc039a69ff8d9ca883819b8682af982e6e7d43ec617d0602558bb6f354d3`.
  Los 23 archivos del parche coinciden con Git y 642 archivos previos permanecen
  idénticos, incluida la plantilla de errores ajena a esta entrega.
- Respaldo privado: `/home/pabrojast/backups/ckan-dev-sld-20261023/`, con
  Deployments, CronJob, cuatro tablas de tracking, pendientes Redis, huellas
  por ID de recursos/vistas, fuentes e informe previo a reconciliar.
- A las 13:18:39 UTC, reconciliación aplicada: **26035 → 25786 descargas**,
  excluyendo **249** correspondientes a 25 contadores SLD. Se conservaron
  exactamente los 1370 contadores originales y las 44497 visitas de ese
  instante; los 1809 recursos y las 19980 vistas mantuvieron sus huellas.
  Las visitas y descargas legítimas posteriores siguen incrementándose.
- Los 27 recursos SLD se muestran con cero descargas en helpers; los diez
  resultados del ranking son archivos de datos. Descarga manual real, fetch
  automático y ruta sin extensión sirvieron los estilos y dejaron invariables
  los contadores SLD y sus pendientes Redis.
- Rollout final completado. CronJob reanudado; un job manual y las corridas
  programadas `pageviews-flush-29879365` y `pageviews-flush-29879370` finalizaron
  correctamente, esta última con la imagen final. Se conservaron los sidecars.
- QA: 200 tests puros después de integrar `dev210`, 8 escenarios PostgreSQL/Redis,
  28 comprobaciones contra CKAN real, navegador EN/ES/FR/AR, móvil 390×844,
  búsqueda por estilo, lista completa, estilos sin asociación, paginación
  20/17 sin duplicados, teclado y ausencia de errores JavaScript.
  Artefactos locales en `output/sld-validation/` y `output/playwright/sld-*.png`.
- Se retiraron las dos bases de prueba y su red, y el builder temporal. No se
  borraron recursos, vistas ni históricos de tracking. Producción no se modificó.

## IHP-IX filtro por organización y panel de instituciones — DEV 2026-10-31

Despliegue lanzado por el usuario con el workflow `deploy` del repositorio Docker (`ckan-unesco-docker`, rama `miserver-2.10`, [run 41146120487](https://github.com/pabrojast/ckan-unesco-docker/actions/runs/41146120487), iniciado 2026-10-30 23:43 UTC, correcto a las 00:13 UTC). Tema en `dev210` hasta `6246c5f` (filtro por organización `5ac2609`, panel de instituciones `fe3806e`, buscador y socias `6246c5f`).

- Imagen: `pabrojast/ckan-base210:20261030234412@sha256:45de691626af2e81afa70cc36e5740724ed1062d98349b50f5ed0977eab0ca7f` (anterior `20261030172803@sha256:17d36116…`); pod `ckan-764c8cf8db-d2lh7`, 1/1 Ready, 0 reinicios. Comprobado dentro del pod que el código contiene `suggest_partners`, `organization_options`, el snippet `admin/snippets/ihpix_admin_tabs.html`, el filtro `ixg-filter-organization` y la interfaz de socias.
- Smoke `scripts/ihpix_dev_smoke.py` desde el pod: 35 páginas 200/302 sin errores Jinja (incluidas `/ihpix/outputs?organization=cazalac&flagship=friend`, `/ihpix/progress?organization=cazalac`, presentación y narrativa con `organization`), marcadores de reporte y progreso presentes, `ihpix_progress_stats` 744 actividades / 191 Member States.
- API en el pod: `options.organizations` = 126 (todas activas, 0 con actividades vinculadas, sin demo/QA), `organization=cazalac` → 0 actividades (no hay vínculos aún), valor desconocido → vacío sin error; `ihpix_institution_link_list`: 311 grupos sin vincular, 73 confiables (213 actividades), una socia sugerida ("CERSHI and Chair on Sustainable Water Security"), 2,9 s.
- Navegador (sesión sysadmin del usuario en `data.dev-wins.com`): pestañas admin con estilo; en el panel, escribir "igr" lista IGRAC y "Add partner organization" abre un combobox que al escribir "cer" lista CeReGAS, CERSHI y una cátedra; en `/ihpix/progress` el filtro de organización lista 127 opciones y escribir "cer" filtra al instante sin aplicar nada; en `/ihpix/outputs?flagship=friend` escribir "ihe" lista IHE Delft, el chip FRIEND-Water se mantiene y el formulario lleva `flagship` oculto. No se aplicó ningún vínculo ni filtro.
- Pendiente: que UNESCO aplique las vinculaciones en `/ckan-admin/ihpix/institutions` para que el filtro tenga organizaciones con datos; recalcular `IhpixCountrySummary` si hace falta. Producción no se modificó.

> [!note] Observado de paso: pods `pageviews-flush-*` en `Failed`
> Revisados el 2026-10-31: son tres Jobs antiguos (2026-10-07 16:10 y 16:15 UTC; 2026-10-20 09:55 UTC) que el CronJob conserva por `failedJobsHistoryLimit: 3`. Los seis pods fallaron igual: timeouts a `solr-headless` y `connection refused` a `postgres` durante el arranque de CKAN (`make_app → load_environment → init_model`), es decir **antes** de tocar Redis, así que no se perdió ningún conteo. Coinciden con reinicios del nodo `ubuntu-2404-noble-amd64-base`, que aloja `postgres-0` y `solr-0` (`c4w-postgres-0` arrancó el 2026-10-07 16:15 UTC y el nodo volvió a `Ready` el 2026-10-20 09:57 UTC). Desde entonces todas las corridas terminan en `Complete`; `tracking_site_totals` se actualiza cada 5 min y el día 2026-10-20 tiene su serie diaria completa. No requiere acción; para limpiarlos basta borrar esos Jobs. Ver [[Comandos Utiles#Conteo liviano de vistas (pageviews)]] y la limitación de conteo anotada en [[Flujos Importantes#12. Conteo liviano de vistas]].

## Verificación de importación IHP-IX (2026-10-23)

`Theme checks` incluye la sintaxis de `scripts/playwright/ihpix_bulk.cjs` además de las regresiones puras. El recorrido que crea borradores y comprueba rollback debe ejecutarse únicamente en CKAN aislado; ver [[Testing]] y [[IHP-IX Bulk Import UX October 2026]].

### Navegación IHP-IX en DEV (2026-11-06)

Aplicada en `default` / `ckan`, deployment `ckan`, con la imagen `pabrojast/ckan-base210:ihpix-navigation-20261106@sha256:8550bd4eba5f2e075888206b1eaf9bc4613f1d94a6ff0f0ecd3e1fc47517ab7e`. Se construyó sobre el digest DEV vigente `325b1fd3…`, copiando sólo los archivos de esta corrección; se verificó que sus fuentes previas coincidían con el checkout. El único cambio al spec del deployment fue la imagen de CKAN. Rollout Ready, cero reinicios; las 12 tablas IHP-IX conservaron conteos y huellas (746 actividades). Validación: 253 pruebas puras, 49 comprobaciones de navegador en la candidata y 14 en la URL pública, más revisión visual EN/ES/FR/AR a 320, 390 y 1440 px. Evidencia local en `output/playwright/ihpix-navigation-20261106/`. Esta publicación de imagen no implica publicación Git de los cambios locales.

### Formulario IHP-IX: autoguardado y tres pasos (2026-11-06)

DEV (`default` / namespace `ckan`) usa `pabrojast/ckan-base210:ihpix-autosave-steps-20261106@sha256:72a1c07b0af877f28da1a3ede5939e25d6da034c13345c99e89ac8fb1ff34aad`, sobre la imagen de navegación del mismo día. Overlay de 15 archivos de aplicación, sin migraciones ni cambios de configuración. Sólo cambió la imagen del deployment. Rollout completado, pod Ready con cero reinicios. Los fingerprints de las 12 tablas IHP-IX permanecieron idénticos (746 actividades). La comprobación pública autenticada aprobó 14 verificaciones de pasos, validación del endpoint sin crear reportes, móvil es/fr/ar y ausencia de excepciones JS. Las escrituras de prueba, PDF y conflictos se probaron en una base local desechable; producción no cambió.

Token temporal de QA revocado y comprobado contra Progress protegido (redirección a login). Sesiones de navegador y contenedores/red de la base aislada eliminados; credenciales temporales retiradas.

### DEV — adjuntos inline IHP-IX (2026-11-06)

Imagen `pabrojast/ckan-base210:ihpix-inline-resources-20261106`, digest `sha256:a2ef51e88053be8854c7fa89cb0af8fd3d94a28ab56fdcee882d5da66ad452b2`, basada en la imagen de autoguardado `72a1c07b0af877f28da1a3ede5939e25d6da034c13345c99e89ac8fb1ff34aad`. Overlay de 17 archivos de aplicación; los 14 archivos existentes de la línea base coincidían con la imagen anterior y los 17 archivos de la candidata se verificaron por hash dentro del pod nuevo.

Despliegue `ckan`, contexto `default`, namespace `ckan`; sólo cambió la imagen. Rollout completado, pod `ckan-58765f9577-qrrvm` Ready y sin reinicios, respetando el retraso inicial de las probes. Validación: 283 pruebas puras, 19 de servicio de recursos, 21 de regresión de autoguardado, 53 comprobaciones funcionales de navegador local, 16 revisiones visuales y 24 comprobaciones en la URL pública de DEV.

Las 12 tablas IHP-IX conservan exactamente sus fingerprints antes/después (746 actividades). Las altas reales de datasets, eventos y publicaciones se probaron sólo en CKAN desechable con almacenamiento local; en DEV se probaron formularios y peticiones incompletas rechazadas. Sin migraciones ni cambios en producción. Evidencia: `output/playwright/ihpix-inline-20261106/`.

Token temporal de DEV revocado y verificado rechazado (403). Se retiraron los contenedores, la red y el túnel propios de QA, y se cerraron las sesiones de navegador y eliminaron las credenciales temporales.

## Despliegue DEV de espacios por grupo IHP-IX

Destino autorizado: contexto `default`, namespace `ckan`, deployment/contenedor `ckan`. La migración es aditiva y se ejecuta al inicializar el plugin, bajo un bloqueo PostgreSQL: nueve tablas nuevas y ocho grupos iniciales. Antes de desplegar, guardar snapshot de deployment, dump de `ihpix_*` y fingerprints de las doce tablas históricas. Después, comparar esas tablas y verificar la nueva interfaz, descargas y permisos, además de esperar Ready. No cambiar probes, credenciales ni configuración de servicios.

El rollback de aplicación consiste en restaurar la imagen anterior; deja las tablas nuevas para conservar cualquier trabajo realizado. No eliminar tablas ni restaurar un dump sobre datos nuevos automáticamente. Los miembros, contactos, planes y archivos reales se incorporan mediante decisiones explícitas en la interfaz; el despliegue no concede roles de grupo a leads antiguos. No hay despliegue de producción autorizado para este cambio.

La imagen de overlay debe copiar los archivos con propietario `ckan:ckan` y verificar su lectura ejecutándose como el usuario final. Una comprobación sólo como root no detecta archivos locales con modo `0600`; esto se detectó y corrigió en el arranque de la réplica candidata, manteniéndose disponible la réplica anterior.

Verificado el 6 de noviembre de 2026 (hora de Santiago): DEV quedó en `pabrojast/ckan-base210@sha256:347e47ed6d62c9e47cdac42bd99ad58c504adee5d873236f57687461e7829db1`, pod `ckan-799484d744-rnz29`, Ready y sin reinicios. La especificación sólo cambió la imagen. Los fingerprints de las doce tablas históricas coinciden, incluidos los 746 registros de actividades; las nueve tablas nuevas contienen únicamente los ocho grupos iniciales. No se importaron datos reales ni se concedieron membresías. Token temporal revocado y rechazo HTTP 403 comprobado. Evidencias y dump privado: `/tmp/ihpix-groups-20261106/`.

### Calendario y demo IHP-IX en DEV (2026-11-07)

- Contexto `default`, namespace `ckan`; se cambió únicamente la imagen de `deployment/ckan`. La versión de calendario `ihpix-calendar-20261107-r2` usa digest `sha256:04418bb38b1ac0a994ab8662cb077a9bb0a420e37852a48d5723b78541f43355`.
- Durante la comprobación coincidió una actualización de Terria. Su imagen final conserva las capas y los 22 archivos del calendario (hashes verificados como usuario de ejecución). Imagen activa: `pabrojast/ckan-base210@sha256:3f3f539ac0f5376e0db87d29e24476dcadbb574fab4b2e5efd45deb65f412698`; pod `ckan-7967c96b87-shmzg`, Ready, sin reinicios. Se mantienen los probes y el resto de la configuración.
- Backup previo de las 21 tablas IHP-IX en `/tmp/ihpix-calendar-20261107/ihpix-before.dump`, con SHA-256 y manifiestos en el mismo directorio privado. Antes de la carga, todas las tablas seguían idénticas tras actualizar la imagen.
- Demo: 247 planes de 249 filas, 249 versiones con procedencias, 164 contactos, siete documentos privados y cinco lotes de importación. Las 199 filas de ejecución quedan en vista previa (135 posibles coincidencias en el libro PA4); no se crean reportes nuevos ni se aprueban planes. Los 746 reportes existentes conservan su fingerprint. Sólo cambian las cinco tablas de planes/versiones/contactos/documentos/importaciones.
- Verificación: 313 pruebas puras IHP-IX, 39 controles del servicio de grupos y 12 del calendario; recorrido navegador de planificación → aprobación → reporte/reanudación, agenda móvil ES/FR/AR, 22 verificaciones HTTP de fuentes privadas y 22 de navegador DEV, más nueve comprobaciones de la imagen final (incluida versión de assets y filtros).
- Los archivos CSS/JS de grupos usan `v=20261107-1` para renovar la caché de clientes existentes. No hay DDL, nueva configuración ni dependencias.

La comparación final tras la imagen combinada mantuvo idénticos los fingerprints de las 21 tablas respecto de la carga verificada. Se revocó el token temporal (HTTP 403 comprobado), se cerró el navegador y se retiraron los cuatro contenedores y la red de QA creados para esta tarea. Evidencia y manifiesto: `/tmp/ihpix-calendar-20261107/result.json`.

## Release coordinada de Azure (2026-11-09)

Se preparó `release/azure-20261109` integrando `production` con `dev210` (`6eee194af203b03ef495d87db0f47111e1763dd8`). La integración conserva la carga diferida del slideshow y el guard de sobrecarga de producción. No se copian los datos de demostración de Hetzner.

La imagen se construye desde el digest vigente de Azure y fija cada extensión en `ckan-unesco-docker/deploy/docker/release-20261109.json`. Learning y dashboards nativos requieren las migraciones aditivas y sus colas dedicadas; Terria usa un digest fijo y conserva sus valores Helm de Azure. MapLibre, Graphic Walker, Chart.js y ChartsCha no se habilitan como extensiones CKAN.

La publicación de esta rama no acredita un despliegue. La ejecución y la evidencia corresponden al procedimiento `deploy/releases/20261109.md` del repositorio Docker, mediante `scripts/manual-deploy.sh` con contexto `ckan`, namespace `ckan`, más el despliegue Helm de Terria. El rollback conserva las tablas nuevas y restaura las imágenes/configuraciones previas; no borra datos recibidos después de la migración.

## Admin limitado de iniciativas

Instalar el parche `patches/initiative-admin-scope/apply.py` de Docker junto al
tema, aplicar tablas aditivas y completar el rollout con el flujo desactivado.
Activar después en DEV y Azure. Nunca volver a una imagen sin la protección
si existen concesiones limitadas: desactivar la funcionalidad conservando el
parche y ambas tablas. No cambia la herencia de organizaciones ni los permisos
anteriores de iniciativas.
