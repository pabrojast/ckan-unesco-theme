# Glosario

> Terminología del dominio y del proyecto `ckanext-theme-ejemplo`.

---

## Términos de CKAN

| Término | Definición |
|---|---|
| **Plugin** | Extensión de CKAN que implementa una o más interfaces para modificar comportamiento |
| **Interface** | Contrato que un plugin implementa para integrarse con CKAN (ej: IConfigurer, IBlueprint) |
| **Action** | Función de la API de CKAN que ejecuta una operación (ej: `package_search`, `user_show`) |
| **Dataset / Package** | Unidad principal de datos en CKAN. Contiene metadata y recursos |
| **Resource** | Archivo o enlace asociado a un dataset |
| **Organization** | Entidad que publica datasets. Los usuarios son miembros con roles |
| **Group** | Colección de datasets por tema. En este proyecto, los estados miembros e iniciativas son groups |
| **Facet** | Filtro de búsqueda basado en campos del dataset (ej: organización, formato, idioma) |
| **Solr** | Motor de búsqueda que CKAN usa para indexar y buscar datasets |
| **plugin_extras** | Campo JSON en la tabla de usuarios de CKAN para almacenar datos de extensiones |
| **Sysadmin** | Rol de administrador global con acceso total |
| **Fanstatic** | Framework de gestión de assets estáticos usado por CKAN |
| **Blueprint** | Componente de Flask que agrupa rutas bajo un prefijo |

---

## Términos de UNESCO / IHP

| Término | Definición |
|---|---|
| **IHP** | International Hydrological Programme — programa intergubernamental de UNESCO sobre agua |
| **IHP-IX** | Novena fase del IHP (2022-2029), "Science for a Water Secure World" |
| **Priority Area (PA)** | Área prioritaria de IHP-IX (ej: research, capacity, advocacy) |
| **Output** | Resultado esperado dentro de una Priority Area |
| **Member State** | País miembro de UNESCO. En el portal, representado como un group de CKAN |
| **Initiative** | Programa o proyecto hídrico de UNESCO. Representado como group |
| **Center** | Centro de categoría 2 de UNESCO (institutos asociados) |
| **ORCID** | Identificador persistente para investigadores (Open Researcher and Contributor ID) |

---

## Términos del portal

| Término | Definición |
|---|---|
| **Portal Card** | Tarjeta configurable que aparece en los portales temáticos (IoT, inundaciones, ciencia ciudadana) |
| **Featured Dataset** | Dataset marcado como destacado por un sysadmin. Se muestra en la homepage |
| **Featured Publication** | Publicación externa destacada, gestionada desde el panel de admin |
| **Featured Viewer** | Visor de mapa interactivo destacado en la portada. El modelo vive en **ckanext-pages**; este tema sólo controla `is_featured` y `order_index` desde `/ckan-admin/featured-viewers` |
| **Bug Ticket** | Reporte de error creado por usuarios autenticados |
| **Thematic Builder** | Herramienta para construir vistas temáticas de datos |
| **Data Story** | Narrativa basada en datos publicada por una organización o grupo |
| **Membership Request** | Solicitud de un usuario para unirse a una organización |
| **People Directory** | Directorio público de usuarios con perfiles extendidos |
| **Tracking** | Sistema de CKAN para contar vistas y descargas de datasets/recursos |

---

## Términos técnicos

| Término | Definición |
|---|---|
| **WKT** | Well-Known Text — formato estándar para representar geometrías espaciales |
| **Bounding Box (bbox)** | Rectángulo geográfico definido por xmin, ymin, xmax, ymax |
| **LRU Cache** | Least Recently Used — caché que descarta los elementos menos usados |
| **TTL** | Time To Live — tiempo de vida de una entrada en cache (en segundos) |
| **Cache Buster** | Técnica para invalidar cache: `int(time.time() / ttl)` cambia cada TTL segundos |
| **Magic Bytes** | Primeros bytes de un archivo que identifican su formato real |
| **Materialized View** | Vista de PostgreSQL que almacena resultados precalculados para consultas rápidas |

---

## Ver también

- [[Arquitectura]] — Diseño del sistema
- [[Modulos]] — Detalle técnico por módulo
