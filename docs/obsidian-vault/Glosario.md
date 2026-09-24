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
| **Priority Area (PA)** | Una de las 5 áreas prioritarias de IHP-IX (`PA1`–`PA5`, ver `ihpix_constants.PRIORITY_AREAS`). Página propia en `/ihpix/priority-area/<pa>` |
| **Output** | Uno de los 34 resultados esperados del Plan Estratégico IHP-IX, codificado `N.M` bajo su PA (`1.1`…`5.5`). Página propia en `/ihpix/outputs/<code>`; los títulos oficiales se cargan desde `data/ihpix_output_titles.json` (DOC-008) |
| **Reporte IHP-IX** | Fila de `ihpix_activity` creada desde `/ihpix/report` (formulario PDF 2026). Estados: `draft` → `pending` → `published` / `rejected` |
| **Gate KPI** | Pregunta Sí/No del formulario (`kpi_*_active`, `has_*`) que habilita sus campos hijos; en "No" los hijos se resetean |
| **Bienio** | Periodo de implementación de dos años (`2022-2023` … `2028-2029`) |
| **Contribuidor** | Usuario de IHP-WINS con reportes IHP-IX publicados (`reported_by`). Directorio en `/ihpix/contributors` |
| **Adjunto (link)** | Publicación, webinar, evento, dataset o enlace asociado a un reporte (`ihpix_activity_link`). Referencia un package CKAN, una página `water-events` o una URL |
| **Webinar** | Tipo de adjunto: no existe como entidad propia; se registra como enlace o página `water-events` |
| **Working group / Workspace** | Espacio colaborativo por Output IHP-IX (`ihpix_working_group`, uno por código). Página en `/ihpix/workspaces/<code>`; piloto de "Collaborative IHP-IX working groups" |
| **Lead** | Miembro que gestiona un workspace (aprueba solicitudes, cambia roles). Lo asigna un sysadmin; también `lead_user_id` del workspace |
| **Contribución (ledger)** | Fila de `ihpix_contribution`: reporte enviado/publicado, adjunto añadido o ingreso a un workspace, por usuario |
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
