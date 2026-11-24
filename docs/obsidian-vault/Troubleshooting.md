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

### Cursos Open Learning aprobados no aparecen en la home ni en `/courses`

Las vistas públicas exigen `status='approved'` **y** `is_available=true`. Si el panel muestra los cursos como aprobados pero la home dice "No courses available", revisar la disponibilidad:

```sql
select status, is_available, count(*), max(last_seen_at)
from open_learning_course group by 1, 2;
```

- Filas `approved | f`: el sync las marcó como no disponibles. Ejecutar `ckan -c ckan.ini openlearning sync --force` (o "Sync now") y volver a consultar.
- Si un curso concreto sigue en `f`, consultar `https://openlearning.unesco.org/api/courses/v1/courses/<course_id>/`: un 404 o `"hidden": true` significa que Open Learning lo retiró del catálogo.
- La home anónima pasa por caché (Varnish `s-maxage=300`): esperar ~5 min tras el sync.

Detalle del mecanismo en [[Open Learning]].

### La sección «Featured Viewers» no aparece en la portada

**Síntoma**: la home no muestra el bloque de visores destacados.

**Causa y solución**, en orden de comprobación:

1. `pages` está en `ckan.plugins` y `ckanext.featured_viewers.enabled = true`
   en el `.ini`. Sin esto la acción `featured_viewer_list` ni siquiera se
   registra y `h.theme_ejemplo_featured_viewers_available()` devuelve `False`.
2. Hay al menos un visor con `status = 'published'`. Si no hay ninguno, ni la
   consulta de destacados ni el fallback a los más recientes devuelven nada y
   la sección se oculta a propósito (no es un error).
   ```bash
   curl -s -X POST -H 'Content-Type: application/json' \
     -d '{"status":"published","limit":6}' \
     http://localhost:5000/api/3/action/featured_viewer_list
   ```
3. Acabas de cambiar los destacados y no se reflejan: el caché de la portada es
   de `ckanext.theme_ejemplo.home_cache_ttl` (300 s por defecto). Espera o baja
   el TTL a `0` mientras pruebas.
4. Si aparecen visores que **no** marcaste, es el fallback funcionando: ningún
   visor tiene `is_featured = true`. Márcalos desde `/ckan-admin/featured-viewers`.

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

## Desbordamiento del buscador del encabezado

El menú sin salto de línea y el buscador con ancho rígido pueden superar el viewport entre tablet y escritorio. El ajuste de 2026-10-01 permite repartir navegación y buscador en varias líneas, limita el campo al espacio disponible incluso al enfocarlo y mantiene la ocultación prevista del buscador entre 768 y 991 px con la especificidad correcta. No se oculta el desbordamiento del documento para disimularlo. La URL de `theme_ejemplo.css` incorporó entonces la versión `20261001-header-1`; la vigente está en la sección siguiente.

Ver [[Testing]]; después del despliegue, comprobar la URL CSS versionada y las páginas sin parámetros de consulta.

## Desplazamiento lateral de la portada en móvil

Las tres bandas claras de la portada (`.homepage-section-alt::before`) se extendían con `left`/`right` en `-50vw`, y el documento medía 1,5 veces el viewport: `scrollWidth` 2088 con 1440 px de ancho y 618 con 412 px. `html` lleva `overflow-x: hidden`, que en escritorio frena la rueda y el teclado, pero en móvil la página se podía arrastrar de lado (`visualViewport.pageLeft` 206 tras deslizar en un Pixel 7).

Desde 2026-11-24 el pseudo-elemento mide lo que su sección y el sangrado lateral son dos copias suyas desplazadas ±50vw con `box-shadow`, que es solo tinta y no crea overflow desplazable. A partir de 3840 px de viewport la sección ya no alcanza 50vw y se usa una sombra expandida recortada con `clip-path`. No se añadió `overflow: hidden`. La URL de `theme_ejemplo.css` incorporó entonces la versión `20261124-home-overflow-1`; la vigente está en la sección siguiente.

Comprobación en la portada: `document.documentElement.scrollWidth === document.documentElement.clientWidth`; con un perfil móvil, `innerWidth === clientWidth` y un deslizamiento horizontal deja `visualViewport.pageLeft` en 0.

> [!warning] No pintar este sangrado con `border-image`
> Reproduce la banda píxel a píxel, pero el modo oscuro automático de Chrome y el modo de colores forzados no lo tratan como fondo: el texto se aclara y queda sobre una banda casi blanca.

## Desborde de 5 px de la página de dataset en móvil

El campo URIRef del módulo Social (`input.permalink-input`, snippet `permanent_url.html` de schemingdcat) ensanchaba el documento en las páginas de dataset: `scrollWidth` 395 con 390 px de viewport (iPhone 13) y 418 con 412 px (Pixel 7). schemingdcat le da `margin-left: 5px` con `width: calc(100% - 10px)`; el tema imponía `width: 100% !important` y el margen se conservaba, así que la caja salía 5 px por la derecha de su tarjeta. En móvil el aside ocupa todo el ancho y esos 5 px pasaban del viewport. En escritorio el campo también sobresalía de la tarjeta, sin ensanchar el documento.

Desde 2026-11-24 `.module .permanav input.permalink-input` vuelve a `width: calc(100% - 10px) !important`. No se añadió `overflow: hidden`. La URL de `theme_ejemplo.css` incorpora la versión `20261124-dataset-mobile-1`.

Comprobación en una página de dataset: `document.documentElement.scrollWidth === document.documentElement.clientWidth` con 390, 412 y 1440 px.

> [!note] `a.info_text` no ensancha el documento
> El enlace del tema DCAT-AP del aside (`schemingdcat/snippets/schemingdcat_info.html`) también pasa del viewport en móvil por su margen negativo, pero lo recorta `ul.scrollable-list` (`overflow-x: hidden`).

> [!warning] Pendiente: descripciones de recursos en móvil
> Con 390 px, la descripción de cada recurso (`li.resource-item > div.description-wrapper`) queda en una columna muy estrecha junto al título (7 px en el peor caso medido) y el texto se parte casi letra a letra: `/dataset/boreholes-kenya-rural-focus` mide 28 284 px de alto en producción. Visible también en dev el 2026-11-24. Sin corregir.
