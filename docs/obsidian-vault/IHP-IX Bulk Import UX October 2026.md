# IHP-IX: importación Excel guiada (octubre de 2026)

## Formato plano actual (IHP-IX/3)

La descarga predeterminada abre **Actividades**, con una actividad por fila. Sus 62 campos editables reúnen datos generales, contacto/institución, alcance e indicadores en bloques horizontales con colores. El identificador técnico se genera al importar: el usuario no introduce ni conserva códigos A001. Se pueden copiar y ordenar filas completas. Los datos de contacto se repiten explícitamente en cada fila; no hay valores heredados ocultos ni datos del perfil que deban borrarse de la plantilla vacía.

Las hojas separadas Instituciones, Participación y alcance e Indicadores se integraron en Actividades. Cuatro hojas adicionales conservan las relaciones múltiples (contribuciones/sinergias, apoyo, organizaciones y recursos); se usan solo cuando corresponda y vinculan la actividad por su **título**, elegido en una lista. Un título inexistente o ambiguo bloquea esos detalles para evitar asignaciones incorrectas. Las filas sin estos detalles pueden tener títulos repetidos.

El libro incluye una guía breve y listas de referencia de consulta. Las listas desplegables, las fechas y los límites numéricos permanecen; los campos multivalor permiten elegir una opción y también escribir varias separadas por punto y coma. No hay fórmulas que el usuario deba escribir. Los indicadores comparten la fila de su actividad y la vista previa señala su celda real.

Las descargas se llaman `ihpix-import-v3.xlsx` e `ihpix-example-v3.xlsx`. El ejemplo sigue conteniendo tres actividades ficticias completas con exactamente los mismos datos de v2. Se conservan los lectores de IHP-IX/1 y /2, sus vistas previas existentes y la creación transaccional e idempotente de borradores.

`ihpix_bulk_flat.py` define la disposición v3; el generador y el lector compartidos reciben el esquema de la versión. Los nombres de hoja e identificadores técnicos siguen en metadatos ocultos. El flujo web indica completar Actividades y usar extras solo cuando hacen falta.

Validación v3: 192 pruebas puras IHP-IX y 93 comprobaciones de navegador, incluida creación real de borradores y cargas v1/v2/v3. La vuelta por LibreOffice conserva íntegros los ejemplos y las 58 reglas de validación en EN/ES/FR/AR.

## Formato anterior (IHP-IX/2)

`/ihpix/import` ofrece dos descargas distintas: plantilla vacía y ejemplo completo. El flujo es preparar → subir → revisar → crear borradores. Subir un archivo no publica ni envía actividades a revisión. «Mis borradores» abre el perfil con `status=draft`.

La plantilla **IHP-IX/2** conserva los 63 campos originales y las relaciones con contribuciones, sinergias, Estados que apoyan, organizaciones asociadas y recursos. La hoja Actividades pasa de 63 a 11 columnas. Las plantillas IHP-IX/1 existentes siguen aceptándose.

1. Completar «Empieza aquí»: contacto, institución, país y bienio compartidos. Los datos del perfil solo precargan la descarga; la importación v2 usa los valores explícitos del libro.
2. Una fila por actividad, manteniendo la referencia preparada A001, A002… Las filas con solo referencia no se importan.
3. Completar únicamente las hojas pertinentes usando la misma referencia. Instituciones permite excepciones a los valores compartidos. Indicadores usa una fila por actividad e indicador, con respuesta, cantidades y tipos. Las demás hojas son Participación y alcance, Contribuciones y sinergias, Apoyo de un Estado Miembro, Organizaciones asociadas y Publicaciones y recursos.
4. Revisar los valores efectivos y los errores por actividad. Los errores indican hoja y celda; si falta una fila opcional, se solicita agregarla para esa referencia. Las respuestas pendientes para enviar a revisión se presentan plegadas y permiten crear borradores.
5. Corregir Excel y volver a subirlo, o confirmar la creación de todos los borradores. Los enlaces del resultado abren cada borrador en el editor habitual.

El ejemplo contiene tres actividades ficticias: estudio de ríos, capacitación y cooperación regional. Incluye indicadores, varios países, contribuciones, sinergias, apoyo y enlaces externos. Puede importarse para practicar y está identificado como ejemplo en el libro y la vista previa.

## Libro y conservación de datos

- Encabezados legibles, instrucciones, comentarios, paneles inmovilizados, referencias y listas desplegables. Fechas ISO o fechas de Excel; números enteros no negativos; códigos como `1.10` permanecen texto.
- `0` y `No` se conservan como respuestas explícitas. Una respuesta `No` contradictoria con cantidades o relaciones proporcionadas bloquea la importación para evitar descartarlas.
- La clasificación principal vive en Actividades. Las contribuciones adicionales nunca la sustituyen; requieren un Output principal.
- Se rechazan referencias duplicadas o huérfanas, fórmulas en celdas de entrada, columnas/hojas alteradas y valores no válidos. Los límites siguen siendo 5 MB comprimidos, 30 MB descomprimidos y 2.000 actividades; Indicadores admite ocho filas por actividad.
- Antes de cargar se comprueban las coordenadas XML reales. Se recalculan las dimensiones, incluso para v1, para que metadatos XLSX incorrectos no oculten filas. Las etiquetas del bloque común se cotejan con su snapshot dentro del libro.
- `_IHP_META` guarda versión, idioma, marca de ejemplo y nombres estables de hojas/campos. `_IHP_OPTIONS` conserva las correspondencias de etiquetas y valores originales. No son datos que el usuario deba editar.
- Las descargas y la interfaz están en EN/ES/FR/AR; el libro árabe usa RTL. Los títulos oficiales sin traducción disponible conservan su idioma original, indicado en las instrucciones. No se inventan traducciones de la taxonomía oficial.

## Implementación

- `ihpix_bulk_schema.py`: estructura, etiquetas y traducción independiente de CKAN.
- `ihpix_bulk_workbook.py`: generación v2 y adaptación al validador común.
- `ihpix_bulk.py`: lectura segura, compatibilidad v1 y validación de registros/relaciones.
- `ihpix_bulk_display.py`: presentación legible, referencias/celdas, valores compartidos y paginación de 20 actividades.
- `ihpix_reporting.py`: acciones existentes `ihpix_import_preview/show/create`; claves API conservadas y metadatos de origen aditivos. Validación de instituciones y recursos visibles para el usuario.
- `ihpix_views.py`, `templates/ihpix/import.html`, `public/css/ihpix-import.css`: descargas y flujo web. Un fallo al confirmar conserva la vista previa autorizada.
- Nueva ruta autenticada GET `/ihpix/import/example.xlsx`; `/ihpix/import/template.xlsx` entrega v2. Ambas usan `Cache-Control: private, no-store`.

No hay migración de base de datos ni nuevas dependencias de ejecución. Se mantiene el control de propietario, el guardado transaccional y la confirmación idempotente. Las vistas previas guardadas con la versión anterior siguen mostrando sus advertencias.

## Verificación

178 pruebas puras IHP-IX aprobadas, incluidos conservación de los 63 campos, indicadores/cero/No, localización real, v1, coordenadas XML y errores de relaciones. Ejemplos de los cuatro idiomas abiertos y guardados con LibreOffice: los datos importados son idénticos y sobreviven 40 reglas de validación por libro. Revisión visual del libro y del flujo web.

La prueba de navegador usa CKAN/PostgreSQL/Redis aislados y usuarios autor/ajeno/admin. Comprueba creación real, equivalencia de campos guardados, recursos, permisos, repetición, compatibilidad v1, archivo roto, borrador mínimo, rollback al fallar la segunda fila y recuperación. Comprueba 1440/768/390/320 px en EN/ES/FR/AR, traducción del encabezado, contraste de botones y barra de administrador RTL. Ver [[Testing]].

Los artefactos de navegador y libros generados se guardan fuera de Git. Las plantillas se generan al descargarlas para incluir opciones e idioma actuales.
