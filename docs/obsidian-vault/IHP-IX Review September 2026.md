# IHP-IX Review September 2026

Revisión implementada el 2026-10-21 sobre `dev210`. Fuente: documento y PDF **IHP-WINs Review elements September 2026** (10 páginas), contrastados con texto e imágenes. Alcance aprobado: IHP-IX y sus integraciones; los encabezados vacíos de Data Stories y Learning no añaden requisitos a esta entrega. Destino: desarrollo `default/ckan`, `data.dev-wins.com`.

## Matriz de requisitos y evidencia

| Documento | Resultado implementado | Verificación |
|---|---|---|
| p. 1: texto inicial y datos repetidos | Texto solicitado, nombre/email del perfil, organización única preseleccionada o elección entre organizaciones; lo guardado prevalece sobre valores iniciales | Navegador: crear, recargar, descartar cambios locales y editar borrador |
| p. 1: carga masiva | Plantilla XLSX versionada `IHP-IX/1`, instrucciones, catálogos y seis hojas de datos; validación, vista previa y confirmación explícita de borradores | Tests de valores, fórmulas, XML inválido, referencias; aceptación HTTP de idempotencia y rollback |
| p. 1–2: organización e informe narrativo | IDs de organización verificados, instituciones externas separadas; informe por organización/PA/Output y bienio, fuentes enlazadas y aviso de revisión humana | Publicados únicamente; sin atribución aproximada por nombre; HTML y PDF |
| p. 2: países y regiones | País institucional, países de apoyo y beneficiarios separados; múltiples apoyos financieros/en especie/acogida; grupos electorales distintos de regiones geográficas | Egipto conserva África y Estados Árabes, grupo Vb; filtros, listas y mapa por país |
| p. 2: iniciativas | CRIDA, Youth4Water e IAHR Label for Water Training and Education; se conservan códigos anteriores | Catálogo y normalización; 21 iniciativas |
| p. 2–3: contribuciones y sinergias | Filas dependientes PA → Output → Key Activity; taxonomía completa de 34 Outputs y 151 KA | Validador rechaza combinaciones inconsistentes; pruebas de ámbitos secundarios y deduplicación |
| p. 4–6: números, tipos y porcentajes | Enteros 0–2147483647, sin fracciones; tipos contrastados con formulario oficial; publicaciones distintas de copias; jóvenes/mujeres ≤ total, pueden solaparse; denominador cero sin porcentaje | Pruebas puras y API; no contestado se conserva distinto de No |
| p. 7–8: recursos | Todas las acciones en VII, publicaciones científicas y materiales; modal compartido; guardado antes de editor nativo y botón de adjuntar/regresar | Archivo real, dataset privado y evento privado en navegador; respuestas conservadas |
| p. 9: dashboards | General, PA, Output, iniciativa y grupo transversal; acceso desde IHP-IX; tablas y estadísticas comunes | Conteos globales únicos y por ámbito; advertencia de subtotales superpuestos |
| p. 9: presentaciones | Vista 16:9, teclado, filtros/fecha, tablas paginadas e impresión PDF | PDF generado desde navegador; todas las tablas caben antes del pie |
| p. 9: workspace 1.10 | Membresía, solicitudes, comentarios, tareas, asignación y notificaciones; 34 espacios conservados | Roles author/contributor/observer/outsider/admin; sin lead inventado, administrador procesa solicitudes |
| Robustez acordada | Coedición de borradores/rechazados por invitación, versiones, conflictos explícitos; autor envía, revisor publica | Dos escrituras simultáneas: una gana, otra conflicto; UI conserva y compara respuestas |
| Privacidad y migración | Adjuntos privados filtrados también en feed, historial, conflicto y respuesta de guardado; cambios aditivos | Pruebas de acceso directo; respaldo y huellas por fila antes/después en DEV |

## Fuentes y semántica

- `data/ihpix_official_taxonomy_source.json`: preguntas públicas del formulario oficial UNESCO consultadas el 2026-10-21, sin respuestas personales. `scripts/build_ihpix_taxonomy_data.py --check` verifica 34 Outputs/151 KA. El texto original queda en el snapshot; la generación limpia espacios partidos y conserva códigos.
- `data/ihpix_countries.json`: snapshot del catálogo UNESCO `https://data.unesco.org/explore/dataset/cou001/`, 211 entradas con ISO, nombres traducidos, grupo electoral y una o varias regiones. No requiere red durante el reporte.
- Una actividad cuenta una vez globalmente y una vez en cada ámbito de contribución. Dos KA del mismo Output no duplican el Output. Las sinergias no aumentan los conteos de contribuciones.
- El mapa agregado usa todos los países de los tres roles. Los puntos de actividades individuales conservan la ubicación del país institucional; no representan múltiples sedes verificadas.
- La organización de un perfil es un valor inicial, nunca una atribución automática para una institución externa. El informe de organización usa IDs exactos y avisa de registros históricos sin vínculo verificado.
- Los informes narrativos son plantillas deterministas con indicadores y resultados reportados, no texto generado por IA. La salida de presentación es HTML/PDF, sin exportación PPTX.

## Permisos y transacciones

| Actor | Capacidades |
|---|---|
| Público | Actividades publicadas y recursos públicos; nunca borradores o versiones privadas |
| Miembro observador activo | Lee el espacio; no comenta ni edita reportes |
| Contributor/lead activo | Comenta y crea tareas; coedita borradores/rechazados solo con invitación del autor |
| Autor | Invita/revoca colaboradores elegibles y envía su reporte a revisión |
| Lead | Modera el espacio; no recibe permiso implícito para publicar reportes |
| Revisor autorizado/sysadmin | Revisa/publica según la autorización existente; sus ediciones también generan versión |

Salir, revocar o degradar la membresía elimina la capacidad correspondiente inmediatamente. Un espacio archivado bloquea escrituras. El destinatario de una tarea debe poder leer su actividad y recurso; un asignado puede cambiar el estado sin modificar el contenido ajeno. El autor puede revocar una invitación aun después de enviar el reporte.

Las escrituras usan el servicio común, bloqueo de fila y `expected_revision`; cada cambio guarda snapshot en la misma transacción. Un registro histórico obtiene versión 0 antes de su primera edición. La respuesta de conflicto y el historial filtran recursos según el lector. Los adjuntos que el colaborador no puede ver se conservan al guardar.

El importador limita archivos a 5 MB, contenido expandido a 30 MB y 2000 filas por hoja. Las hojas Contributions, Synergies, Supporters, Partners y Resources se vinculan por `row_ref`. Los errores incluyen hoja/celda; los campos obligatorios incompletos son advertencias de borrador. El lote es privado, atómico e idempotente por usuario y contenido. Se vuelve a validar al confirmar: un cambio de permisos entre vista previa e importación revierte todo el lote.

## Hallazgos de revisión corregidos

Revisión de código con tres perspectivas (aceptación, casos límite y lectura independiente), seguida de comprobaciones específicas:

- Autorización de recursos en lecturas, historial, conflictos, feed y respuestas de mutación; conservación de adjuntos invisibles.
- Revocación de miembros/leads, tareas con destinatarios sin acceso, revocación de invitación tras envío y espacios archivados.
- Versionado uniforme para admin/adjuntos, snapshot histórico inicial y serialización de invitaciones concurrentes.
- Autofill de organización sin atribuir instituciones externas; precisión de celdas en relaciones XLSX; error controlado de XML inválido.
- Borrador local posterior a datos del servidor, descarte que restaura servidor y guardado previo al editor externo.
- DDL repetido que bloqueaba la propia transacción al sincronizar adjuntos; índices ahora se crean solo si faltan.
- Migración de columnas nuevas sin volver a normalizar los 745 reportes históricos; inicialización de tablas protegida contra arranque simultáneo.
- Filtros y estadísticas de PA/Output secundarios y países de apoyo, sin heredar una KA primaria en otro Output.
- Registro correcto del helper de retorno, enlaces legibles de tareas y detalle de actividad suficiente para verificar cifras de informes.

## Evidencia de aceptación

Entorno CKAN aislado en `127.0.0.1:5011`, DB/Redis/core Solr separados, cinco usuarios de prueba y sumidero SMTP local. Copia de los datos IHP-IX de DEV; no se ejecutó `clean_db` sobre DEV.

- 146 pruebas puras pasan (incluyen límites numéricos, taxonomía, relaciones, importación y presentación).
- 29 comprobaciones HTTP pasan: permisos, membresía, coedición, concurrencia, submit/reject/publish, caché/estadísticas, privacidad e importación idempotente.
- Regresiones adicionales de recursos privados y un lote de dos filas con fallo en la segunda: rollback completo y reintento correcto.
- Navegador real: guardar/reabrir, conflictos, historial, modal de publicación con archivo, editor de dataset y evento con retorno; escritorio y móvil 390×844 en EN/ES/FR/AR sin desbordamiento, árabe RTL.
- Catálogos ES/FR/AR compilados sin errores; nuevos textos de herramientas traducidos. El `.pot` incorpora los literales extraídos; esto no implica traducción completa de todos los textos históricos.
- Capturas, PDFs y logs locales en `/tmp/ihpix-implementation-20261021/`; no se publican tokens ni datos privados en Git.

El detalle del despliegue y la preservación final está en [[Deployment#IHP-IX revisión de septiembre — DEV 2026-10-21]].
