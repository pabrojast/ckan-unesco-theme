# Comandos Útiles

> Referencia rápida de comandos para desarrollo, testing, i18n y packaging.

---

## Desarrollo

```bash
# Instalar en modo desarrollo
pip install -e .
pip install -r requirements.txt

# Instalar dependencias de testing
pip install -r dev-requirements.txt

# Ejecutar CKAN en modo desarrollo
ckan -c /etc/ckan/default/ckan.ini run
```

---

## Testing

```bash
# Ejecutar todos los tests
pytest --ckan-ini=test.ini

# Ejecutar un archivo de test específico
pytest --ckan-ini=test.ini ckanext/theme_ejemplo/tests/test_plugin.py

# Ejecutar un test por nombre
pytest --ckan-ini=test.ini -k "test_plugin"

# Ejecutar con cobertura (como en CI)
pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo
```

> [!warning] Requisitos para tests
> Los tests requieren una instancia CKAN con Solr, PostgreSQL y Redis funcionando. Ver [[Setup Local]] y [[Testing]] para más detalles.

---

## Índice de búsqueda

Después de actualizar el esquema Solr y desplegar el tema, regenerar los
documentos del índice para incluir los abstracts de datasets existentes:

```bash
ckan -c /ruta/ckan.ini search-index rebuild
```

Usar la configuración de la instancia elegida y comprobar que el proceso termina
sin errores. No ejecutar `clear` ni eliminar la colección. El orden completo de
activación está en [[Busqueda#Activación en una instancia existente]].

---

## Internacionalización (i18n)

```bash
# Extraer strings traducibles a .pot
python setup.py extract_messages

# Inicializar un nuevo idioma (ej: portugués)
python setup.py init_catalog -l pt

# Actualizar catálogos existentes con nuevos strings
python setup.py update_catalog

# Compilar archivos .po a .mo (necesario para que las traducciones funcionen)
python setup.py compile_catalog
```

**Idiomas activos**: Árabe (`ar`), Español (`es`), Francés (`fr`)

**Archivos**:
- Plantilla: `ckanext/theme_ejemplo/i18n/ckanext-theme_ejemplo.pot`
- Traducciones: `ckanext/theme_ejemplo/i18n/<lang>/LC_MESSAGES/ckanext-theme_ejemplo.po`
- Compilados: `ckanext/theme_ejemplo/i18n/<lang>/LC_MESSAGES/ckanext-theme_ejemplo.mo`

---

## Base de datos

```bash
# Inicializar la base de datos de CKAN
ckan -c /etc/ckan/default/ckan.ini db init

# Las tablas custom del plugin se crean automáticamente al iniciar CKAN
# (MembershipRequest, FeaturedPublication, BugTicket, PortalCard, IhpixContent, IhpixActivity, IhpixCountrySummary, InitiativeRequest, OpenLearningCourse)
```

---

## IHP-IX: Ingesta de datos

```bash
# Cargar seed desde JSON (archivo por defecto)
ckan ihpix seed-data -f ckanext/theme_ejemplo/data/ihpix_seed_data.json

# Cargar directamente desde Excel
ckan ihpix seed-data --from-excel All_Priority_Areas_Reporting.xlsx

# Cargar sin archivo (busca data/ihpix_seed_data.json automáticamente)
ckan ihpix seed-data

# Agregar datos sin borrar los existentes
ckan ihpix seed-data -f data.json --append

# Regenerar JSON seed desde Excel
cd ckanext/theme_ejemplo && python scripts/generate_seed.py

# Recalcular el resumen por país (mapa) desde las actividades publicadas
ckan ihpix recompute-summary            # todos los países, conserva coordenadas
ckan ihpix recompute-summary --dry-run  # solo imprime los conteos
ckan ihpix recompute-summary --country france

# Crear los workspaces (working groups) que falten, uno por Output
ckan ihpix seed-workspaces

# Normalizar los datos heredados del Excel (alias de valores, puertas KPI
# derivadas de los conteos, key_activity_code). Ensayo por defecto; con
# --apply escribe, recalcula el resumen por país e invalida la caché de stats.
# Se ejecuta solo al arrancar cuando la migración añade columnas nuevas.
ckan ihpix normalize-legacy
ckan ihpix normalize-legacy --apply
ckan ihpix normalize-legacy --apply --status published --all   # también las ya marcadas

# Regenerar títulos de Output y key activities desde el seed (JSON derivados
# del Excel; --check solo comprueba que están al día, para CI)
python3 -I scripts/build_ihpix_taxonomy_data.py
python3 -I scripts/build_ihpix_taxonomy_data.py --check
```

> [!warning] Sin `--append`, el comando elimina actividades con `original_id` y todos los country summaries antes de cargar.

---

## Open Learning: sincronización de cursos

```bash
# Sincronizar la caché curada de cursos con la API de Open Learning
ckan -c /etc/ckan/default/ckan.ini openlearning sync --force

# Cron sugerido en producción (cada 6 horas)
# 0 */6 * * * ckan -c /etc/ckan/default/ckan.ini openlearning sync --force
```

Ver [[Open Learning]] para el flujo de curación completo.

---

## Conteo liviano de vistas (pageviews)

```bash
# Volcar contadores de Redis a Postgres (lo corre el CronJob cada ~5 min)
ckan -c /etc/ckan/default/ckan.ini pageviews flush

# Ver pendientes en Redis y totales acumulados en Postgres
ckan -c /etc/ckan/default/ckan.ini pageviews status
```

En Kubernetes el volcado lo ejecuta un CronJob (`deploy/cronjob-pageviews-flush.yaml`):

```bash
kubectl -n ckan apply -f deploy/cronjob-pageviews-flush.yaml
kubectl -n ckan get cronjobs
# Corrida manual de prueba:
kubectl -n ckan create job pv-flush-test --from=cronjob/pageviews-flush
```

Requiere `ckanext.theme_ejemplo.pageviews_enabled = true` y `ckan.tracking_enabled = false`. Ver [[Flujos Importantes#Conteo liviano de vistas]] y [[Variables de Entorno#Conteo liviano de vistas (pageviews)]].

---

## Packaging y distribución

```bash
# Crear distribución source
python setup.py sdist

# Crear distribución source + wheel y verificar
python setup.py sdist bdist_wheel && twine check dist/*

# Subir a PyPI
twine upload dist/*
```

---

## Git

```bash
# Ver estado
git status

# Crear tag de release
git tag <version>
git push --tags
```

---

## Ver también

- [[Setup Local]] — Instalación completa del entorno
- [[Testing]] — Estrategia y detalles de testing
- [[Deployment]] — Proceso completo de release

## Recursos de formación

```bash
ckan -c /app/production.ini learning init
ckan -c /app/production.ini learning migrate-openlearning  # informe sin cambios
ckan -c /app/production.ini learning migrate-openlearning --apply
ckan -c /app/production.ini learning sync --due
```

El comando anterior `openlearning sync --force` sigue funcionando cuando
el plugin está habilitado y delega a su fuente IHP.

## IHP-IX: taxonomía y aceptación de revisión

`python3 scripts/build_ihpix_taxonomy_data.py --check` comprueba que los JSON generados coinciden con el snapshot oficial (34 Outputs/151 KA). Sin `--check` los regenera; `--seed` es la opción explícita para datos legados.

`scripts/ihpix_review_acceptance.py` ejecuta aceptación HTTP solo en un CKAN local aislado: requisitos y variables en [[Testing#Aceptación IHP-IX de septiembre (2026-10-21)]].

## Reconciliar descargas excluyendo SLD

```bash
ckan -c /srv/app/production.ini pageviews reconcile-downloads
ckan -c /srv/app/production.ini pageviews reconcile-downloads --apply --backup /ruta/privada/sld-before.json
```

Por defecto sólo informa total anterior/resultante y recursos excluidos. Aplicar
requiere Redis disponible, el bloqueo compartido con `pageviews flush` y un
archivo de respaldo nuevo (0600, no sobrescribe). La transacción modifica sólo
`tracking_site_totals.total_downloads`, conservando visitas e histórico por
recurso. El respaldo incluye los contadores originales y pendientes en Redis;
`applied=false`/`snapshot_phase=before` identifica que es la captura previa.
Repetir recalcula el mismo agregado; no resta dos veces. Los incrementos nuevos
en Redis permanecen pendientes para el siguiente flush.

Para revertir la política, restaurar la imagen anterior y recalcular la suma
completa de `tracking_resource_stats`, conservando las visitas y las nuevas
descargas; no restaurar valores viejos encima de incrementos posteriores.
