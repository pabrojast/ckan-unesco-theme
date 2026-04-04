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
