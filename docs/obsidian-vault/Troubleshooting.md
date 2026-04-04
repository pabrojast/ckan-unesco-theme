# Troubleshooting

> Problemas comunes y soluciones para `ckanext-theme-ejemplo`.

---

## Problemas de instalación

### Error: `shapely` no compila

**Síntoma**: Error al instalar shapely, menciona `geos_c.h` no encontrado.

**Solución**: Instalar las dependencias de sistema de GEOS:
```bash
# Ubuntu/Debian
sudo apt-get install libgeos-dev libgeos++-dev

# Alpine
apk add geos-dev geos
```

**Importante**: Usar `shapely<2` — la versión 2.x tiene cambios incompatibles.

---

### Error: `test.ini` no encuentra `test-core.ini`

**Síntoma**: `IOError: File not found: ../ckan/test-core.ini`

**Causa**: `test.ini` usa una ruta relativa a la instalación de CKAN.

**Solución**: Ajustar la ruta en `test.ini` o crear un symlink:
```bash
# Opción 1: Editar test.ini
use = config:/path/to/your/ckan/test-core.ini

# Opción 2: Symlink (si CKAN está en un virtualenv)
ln -s /usr/lib/ckan/default/src/ckan ../ckan
```

---

### Error: Extensiones CKAN no encontradas

**Síntoma**: `ckan.plugins.PluginNotFoundException: theme_ejemplo`

**Causas posibles**:
1. No se ejecutó `pip install -e .`
2. El virtualenv no está activado
3. El nombre del plugin en `ckan.ini` está mal escrito (debe ser `theme_ejemplo`)

---

## Problemas de runtime

### Templates no se cargan / errores 500

**Causa probable**: Falta alguna extensión dependiente.

**Verificar**: Que todas las extensiones estén instaladas:
- ckanext-spatial
- ckanext-dcat
- ckanext-scheming
- ckanext-schemingdcat

---

### Cache devuelve datos obsoletos

**Síntoma**: Cambios en datos no se reflejan en la interfaz.

**Causa**: Los caches TTL no se invalidan al cambiar datos.

**Solución temporal**: Reiniciar CKAN para limpiar todos los caches en memoria.

**Configuración**: Reducir TTL en `ckan.ini`:
```ini
ckanext.theme_ejemplo.groups_cache_ttl = 60
ckanext.theme_ejemplo.home_cache_ttl = 60
```

Ver [[Variables de Entorno]] para todas las claves de cache.

---

### Solr: Error en atomic update con facetas multilingües

**Síntoma**: Error de Solr al indexar datasets con campos en múltiples idiomas.

**Causa**: Caracteres o formatos inesperados en campos de faceta.

**Mitigación**: El plugin sanitiza estos campos en `before_dataset_index`. Si el error persiste, verificar que el schema de Solr soporte los campos multilingües.

---

### Datos espaciales no se indexan

**Síntoma**: Búsqueda espacial no retorna resultados esperados.

**Verificar**:
1. Que el dataset tenga extras `xmin`, `ymin`, `xmax`, `ymax` con valores numéricos válidos
2. Que Shapely esté instalado (`pip show shapely`)
3. Que `before_dataset_index` se esté ejecutando (revisar logs de CKAN)
4. Que Solr tenga el campo `spatial_geom` en su schema

---

### Tablas custom no se crean

**Síntoma**: Error al acceder a funcionalidad de membresías, publicaciones, etc.

**Causa**: Las tablas se crean al iniciar el plugin. Si hubo un error durante la inicialización, pueden no haberse creado.

**Solución**: Reiniciar CKAN. Las funciones `init_*_db()` son idempotentes y crearán las tablas si no existen. Verificar en PostgreSQL:
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_name IN ('membership_request', 'featured_publication', 'bug_ticket', 'portal_card', 'ihpix_content', 'ihpix_activity');
```

---

## Problemas de testing

### Tests fallan con servicios no disponibles

**Síntoma**: `ConnectionError` o timeout al ejecutar pytest.

**Causa**: Los tests requieren PostgreSQL, Solr y Redis funcionando.

**Solución**: Levantar los servicios antes de ejecutar tests. El CI usa Docker containers (ver [[Deployment#CI/CD Pipeline]]).

---

### Import errors al ejecutar tests

**Síntoma**: `ModuleNotFoundError` al importar extensiones.

**Solución**: Asegurarse de que todas las dependencias estén instaladas en el mismo virtualenv:
```bash
pip install -e .
pip install -r requirements.txt
pip install -r dev-requirements.txt
```

---

## Problemas de i18n

### Traducciones no aparecen

**Verificar**:
1. Que los archivos `.mo` estén compilados:
   ```bash
   python setup.py compile_catalog
   ```
2. Que el idioma esté soportado (`ar`, `es`, `fr`)
3. Que `ITranslation` esté implementada en el plugin

---

## Ver también

- [[Setup Local]] — Configuración del entorno
- [[Comandos Utiles]] — Referencia de comandos
- [[Variables de Entorno]] — Configuración
- [[Testing]] — Ejecución de tests
