# Setup Local

> Cómo levantar el entorno de desarrollo para `ckanext-theme-ejemplo`.

---

## Prerrequisitos

Para desarrollo local necesitas una instancia de CKAN 2.9 (o 2.10) funcionando con:

| Servicio | Versión mínima | Propósito |
|---|---|---|
| **CKAN** | 2.9 | Plataforma base |
| **PostgreSQL** | 9.6+ | Base de datos principal y datastore |
| **Solr** | 6.x / 8.x | Motor de búsqueda |
| **Redis** | 3+ | Cola de trabajos en background |
| **Python** | 3.x | Runtime (2.7 legacy en setup.py, pero CI usa Python 3) |

> [!tip] La forma más fácil de tener estos servicios es usando Docker.
> El CI usa `openknowledge/ckan-dev:2.9` con servicios Docker. Ver [[Deployment#CI/CD Pipeline]].

---

## Dependencias del sistema

Paquetes de sistema necesarios (Alpine/Ubuntu):

```bash
# Alpine (como en CI)
apk add gcc libc-dev geos-dev geos gfortran musl-dev python3-dev py3-numpy py3-setuptools

# Ubuntu/Debian (equivalentes)
sudo apt-get install gcc libgeos-dev libgeos++-dev gfortran python3-dev python3-numpy
```

---

## Instalación de la extensión

### 1. Clonar el repositorio

```bash
git clone <url-del-repo> ckan-unesco-theme
cd ckan-unesco-theme
```

### 2. Activar el virtualenv de CKAN

```bash
. /usr/lib/ckan/default/bin/activate
# o el path de tu virtualenv
```

### 3. Instalar la extensión en modo desarrollo

```bash
pip install -e .
pip install -r requirements.txt
```

### 4. Instalar dependencias de testing (opcional)

```bash
pip install -r dev-requirements.txt
```

### 5. Instalar extensiones CKAN requeridas

> [!warning] Forks específicos
> El proyecto requiere forks específicos de estas extensiones, no las versiones oficiales.

```bash
# ckanext-spatial (fork)
pip install -e "git+https://github.com/mjanez/ckanext-spatial.git#egg=ckanext-spatial"

# ckanext-dcat (fork)
pip install -e "git+https://github.com/mjanez/ckanext-dcat.git#egg=ckanext-dcat"

# ckanext-scheming
pip install -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming"

# ckanext-schemingdcat
pip install -e "git+https://github.com/mjanez/ckanext-schemingdcat.git#egg=ckanext-schemingdcat"

# Shapely (versión < 2 obligatoria)
pip install "shapely<2"
```

> [!note] Pendiente por confirmar
> Las URLs exactas de los forks pueden variar. Verificar en `.github/workflows/test.yml` la versión más actualizada.

### 6. Configurar CKAN

Edita tu archivo de configuración CKAN (`/etc/ckan/default/ckan.ini` o equivalente):

```ini
ckan.plugins = theme_ejemplo
```

### 7. Inicializar la base de datos

```bash
ckan -c /etc/ckan/default/ckan.ini db init
```

Las tablas custom del plugin se crean automáticamente al iniciar CKAN (ver [[Arquitectura#Modelos de base de datos]]).

### 8. Reiniciar CKAN

```bash
# Apache
sudo service apache2 reload

# O si usas paster/ckan run
ckan -c /etc/ckan/default/ckan.ini run
```

---

## Verificar la instalación

1. Accede a la homepage de CKAN — deberías ver el tema UNESCO
2. Verifica que los portales responden:
   - `/memberstates`
   - `/ihpix`
   - `/people`
3. Si eres sysadmin, verifica los paneles de admin en `/admin/featured-datasets`

---

## Configuración opcional

Claves de configuración del plugin. Ver lista completa en [[Variables de Entorno]].

```ini
# TTL de caches (en segundos)
ckanext.theme_ejemplo.courses_cache_ttl = 600
ckanext.theme_ejemplo.groups_cache_ttl = 300
ckanext.theme_ejemplo.home_cache_ttl = 300
ckanext.theme_ejemplo.recently_added_cache_ttl = 300
ckanext.theme_ejemplo.tracking_cache_ttl = 300

# Habilitar indexación de seguidores
ckanext.theme_ejemplo.index_followers = false
```

---

## Ver también

- [[Comandos Utiles]] — Comandos de desarrollo y testing
- [[Variables de Entorno]] — Todas las claves de configuración
- [[Testing]] — Cómo ejecutar tests
- [[Deployment]] — Pipeline de CI/CD
