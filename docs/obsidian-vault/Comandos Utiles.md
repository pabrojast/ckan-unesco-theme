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
# (MembershipRequest, FeaturedPublication, BugTicket, PortalCard, IhpixContent, IhpixActivity, IhpixCountrySummary)
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
```

> [!warning] Sin `--append`, el comando elimina actividades con `original_id` y todos los country summaries antes de cargar.

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
