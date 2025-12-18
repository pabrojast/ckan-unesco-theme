# CKAN 2.10 Compatibility Fixes - UNESCO Theme

Este documento describe las correcciones aplicadas al tema UNESCO para asegurar la compatibilidad con CKAN 2.10 y el plugin ckanext-schemingdcat.

## Problemas Identificados y Solucionados

### 1. Imágenes de Facetas No Se Muestran en Sidebar

**Problema:** Las imágenes de iconos de facetas (categorías, temas, ubicaciones geográficas) no se estaban mostrando en la barra lateral de la página de búsqueda de datasets.

**Causa:**
- CKAN 2.10 cambió la estructura HTML de las facetas
- Falta de especificidad CSS suficiente para sobrescribir estilos predeterminados de CKAN 2.10
- Algunas propiedades CSS como `overflow: hidden` estaban ocultando las imágenes

**Solución:**
- Creado archivo `ckan210-fixes.css` con reglas CSS de alta especificidad
- Forzado `display: inline-block !important` y `visibility: visible !important` en todos los iconos de facetas
- Ajustado padding y overflow en contenedores padre para permitir visualización de imágenes
- Aplicado flexbox layout a los enlaces de facetas para alineación correcta

**CSS Afectado:**
```css
.secondary img.facet-icon,
.filters img.facet-icon,
nav.nav-facet li a img.facet-icon {
  display: inline-block !important;
  width: 1.3em !important;
  height: 1.3em !important;
  opacity: 1 !important;
  visibility: visible !important;
}
```

### 2. Texto Cortado en Elementos de la Lista de Datasets

**Problema:** Los títulos y descripciones de datasets aparecían truncados excesivamente, cortando información importante.

**Causa:**
- Reglas `white-space: nowrap` combinadas con `text-overflow: ellipsis` estaban cortando texto en una sola línea
- Límites de `max-height` muy restrictivos en descripciones

**Solución:**
- Cambiado `white-space: nowrap` a `white-space: normal` para permitir text wrapping
- Eliminado restricciones excesivas de `max-height`
- Implementado `-webkit-line-clamp` para limitar a 3 líneas completas en descripciones
- Mejorado `line-height` para mejor legibilidad

**CSS Afectado:**
```css
.nav-facet .item-label {
  white-space: normal !important;
  line-height: 1.4 !important;
}

.dataset-item .dataset-content {
  display: -webkit-box !important;
  -webkit-line-clamp: 3 !important;
  -webkit-box-orient: vertical !important;
}
```

### 3. Problemas de Layout en Sidebar

**Problema:** Los módulos de la barra lateral no tenían el espaciado y estilo correcto en CKAN 2.10.

**Solución:**
- Ajustado padding de `.module-content` en sidebar
- Mejorado estilos de `.module-heading` con flexbox
- Agregado bordes y sombras apropiadas
- Configurado responsive design para móviles

## Archivos Modificados

### Archivos Nuevos:
1. **ckanext/theme_ejemplo/public/ckan210-fixes.css**
   - Nuevo archivo con todas las correcciones CSS para CKAN 2.10
   - Contiene ~450 líneas de CSS específico
   - Organizado por secciones temáticas

### Archivos Editados:
1. **ckanext/theme_ejemplo/templates/base.html**
   - Agregada referencia al nuevo archivo CSS `ckan210-fixes.css`
   - Línea añadida: `<link rel="stylesheet" href="{{ h.url_for_static('/ckan210-fixes.css') }}" />`

## Cómo Probar los Cambios

### 1. Desplegar los Cambios

```bash
# Navegar al directorio del proyecto
cd /path/to/ckan-unesco-theme

# Reiniciar CKAN para cargar los nuevos archivos
sudo supervisorctl restart ckan

# O si usas systemd:
sudo systemctl restart ckan
```

### 2. Limpiar Cache (Importante)

```bash
# Limpiar cache de Webassets
ckan asset build

# Limpiar cache de navegador
# En Chrome/Firefox: Ctrl+Shift+Delete y seleccionar "Imágenes y archivos en caché"
```

### 3. Verificar los Fixes

1. **Verificar Iconos de Facetas:**
   - Ir a http://data210.dev-wins.com/dataset
   - Verificar que en la barra lateral aparezcan iconos junto a las categorías
   - Los iconos deben ser círculos de ~20px con las banderas/símbolos correspondientes

2. **Verificar Texto Completo:**
   - Los títulos de datasets deben mostrarse completos (no cortados arbitrariamente)
   - Las descripciones deben mostrar hasta 3 líneas completas de texto

3. **Verificar Layout:**
   - La barra lateral debe tener fondos blancos con sombras sutiles
   - El espaciado debe ser consistente
   - Los badges de conteo deben aparecer alineados a la derecha

### 4. Pruebas en Diferentes Navegadores

Probar en:
- Chrome/Edge (última versión)
- Firefox (última versión)
- Safari (si está disponible)
- Dispositivos móviles (responsive)

### 5. Pruebas Responsive

```bash
# En Chrome DevTools:
# 1. F12 para abrir DevTools
# 2. Ctrl+Shift+M para modo responsive
# 3. Probar en diferentes tamaños:
#    - Mobile: 375x667 (iPhone)
#    - Tablet: 768x1024 (iPad)
#    - Desktop: 1920x1080
```

## Comparación: Antes vs Después

### Antes (CKAN 2.10 sin fixes):
- ❌ No se ven iconos de facetas en sidebar
- ❌ Texto de títulos cortado abruptamente con "..."
- ❌ Descripciones truncadas en 1 línea
- ❌ Sidebar sin estilos consistentes

### Después (Con ckan210-fixes.css):
- ✅ Iconos de facetas visibles y bien alineados
- ✅ Títulos completos con word wrapping inteligente
- ✅ Descripciones muestran hasta 3 líneas
- ✅ Sidebar con diseño limpio y profesional

## Configuración de Referencia

### Sitios de Comparación:
- **Funcionando correctamente (CKAN 2.9):** http://data.dev-wins.com/dataset
- **Con problemas (CKAN 2.10 sin fixes):** http://data210.dev-wins.com/dataset (antes de aplicar)
- **Con fixes (CKAN 2.10 corregido):** http://data210.dev-wins.com/dataset (después de aplicar)

## Rollback (Si es necesario)

Si los cambios causan problemas, puedes hacer rollback fácilmente:

```bash
# 1. Editar templates/base.html y eliminar la línea:
# <link rel="stylesheet" href="{{ h.url_for_static('/ckan210-fixes.css') }}" />

# 2. O renombrar el archivo CSS:
mv ckanext/theme_ejemplo/public/ckan210-fixes.css ckanext/theme_ejemplo/public/ckan210-fixes.css.bak

# 3. Reiniciar CKAN
sudo supervisorctl restart ckan
```

## Mantenimiento Futuro

### Actualización de Estilos de Schemingdcat

Si actualizas ckanext-schemingdcat, verifica que los estilos sigan siendo compatibles:

1. Revisar cambios en `ckanext-schemingdcat/assets/css/schemingdcat.css`
2. Comparar con `ckan210-fixes.css`
3. Actualizar si es necesario

### Adición de Nuevos Iconos

Para agregar nuevos iconos de categorías:

1. Agregar imagen a carpeta apropiada en `/images/icons/`
2. Los estilos ya están configurados para mostrar automáticamente
3. Verificar que el icono tenga dimensiones apropiadas (preferiblemente 40x40px o SVG)

## Soporte y Troubleshooting

### Problema: Los iconos aún no se ven

**Verificar:**
1. Cache del navegador limpiado
2. Archivo CSS cargado correctamente (verificar en DevTools → Network)
3. Paths de imágenes correctos en ckanext-schemingdcat
4. Permisos de archivos correctos (644 para CSS)

### Problema: Layout se rompe en móvil

**Verificar:**
1. Las media queries en ckan210-fixes.css están cargándose
2. No hay CSS conflictivo con mayor especificidad
3. Viewport meta tag está presente en base template

### Logs Útiles

```bash
# Ver logs de CKAN
tail -f /var/log/ckan/ckan.log

# Ver logs de Apache/Nginx
tail -f /var/log/apache2/error.log
# o
tail -f /var/log/nginx/error.log
```

## Contacto

Para preguntas o problemas con estas correcciones, contactar al equipo de desarrollo del tema UNESCO.

## Changelog

### v1.0 (2025-12-18)
- ✨ Inicial: Correcciones para compatibilidad CKAN 2.10
- ✨ Fix: Iconos de facetas en sidebar
- ✨ Fix: Truncamiento de texto en datasets
- ✨ Fix: Layout y estilos de módulos en sidebar
- 📱 Mejoras responsive para móviles y tablets
