# IHP-IX Progress UX — octubre 2026

## Comportamiento

Progress selecciona un país desde el mapa, su tabla accesible o el combobox. El país se combina con bienio y región y se conserva en URL, historial, pestañas, selectores de ámbito, descarga JSON, presentación y reporte narrativo. Se incluyen actividades donde el país es sede de quien reporta, beneficiario o colaborador; las cifras pertenecen a las actividades completas y no se reparten entre países. Otros países asociados siguen visibles en el mapa, con menor énfasis. Quitar el país conserva los demás filtros.

Las actualizaciones descartan respuestas antiguas. Un fallo conserva los datos y controles de la última selección válida y permite reintentar la selección fallida. El total de la franja y del centro del gráfico circular cuenta actividades únicas; los subtotales por PA se calculan sin sumar Outputs. Las participaciones superpuestas no muestran porcentajes que puedan confundirse con porcentajes del total único. La cola de revisión se identifica como global.

El explorador utiliza el combobox de países con búsqueda localizada y conserva Apply. My drafts lleva al perfil con `status=draft`; antes de salir se vacía el guardado pendiente del navegador. Un error de almacenamiento impide perder respuestas modificadas, sin bloquear la salida si no hay cambios pendientes.

## Interfaces y presentación

`ihpix_progress_stats` conserva su contrato y su parámetro `country` existente. La vista ahora lo lee y normaliza nombres/ISO conocidos. `ihpix_narrative_data` añade los ámbitos `overall`, `flagship`, `ctwg` y los filtros opcionales `country`, `region`, manteniendo `pa`, `output`, `organization`. Las fuentes y las cifras usan el mismo filtrado. El ámbito general admite `value` vacío.

`ihpix_constants.PA_COLORS` es la fuente compartida para PA1 azul, PA2 ámbar, PA3 violeta, PA4 verde y PA5 rojo. `PA_DARK_COLORS` proporciona variantes para texto y fondos con letras blancas. Las áreas, Outputs, explorador, landing, organizaciones, grupos y gráficos usan la misma correspondencia. Las tarjetas de Output tienen como máximo cuatro columnas; las actividades muestran títulos enlazados, metadatos separados, resumen de tres líneas y enlace al detalle completo.

Los alias vacíos no se registran en `ihpix_relations.country_index`: algunos títulos árabes producen un slug ASCII vacío. Una selección vacía nunca debe resolverse como un país.

## Verificación reproducible

- Suite pura: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py`.
- Taxonomía: `python3 scripts/build_ihpix_taxonomy_data.py --check`.
- Navegador: `scripts/playwright/ihpix_progress_filters.cjs`, restringido a localhost. Variables: `IHPIX_QA_BASE`, `IHPIX_QA_TOKENS` (admin), `IHPIX_QA_FIXTURE`, `IHPIX_QA_OUTPUT`.
- Fixture: `scripts/playwright/fixtures/ihpix_progress.py`, con `/qa/app.ini`, una base vacía `ihpix_ux` en `ihpix-ux-db` y el usuario aislado `ihpix-ux-author`. Crea actividades internacionales con relaciones múltiples, una organización, resúmenes de coordenadas y estados de reporte; escribe `/qa/fixture.json`.
- La prueba cubre mapa/tabla/teclado, roles de países, alias ISO, restauración, ámbitos, respuestas desordenadas, error/reintento, filtros vacíos, JSON/presentaciones/narrativas, países en el explorador, borradores y almacenamiento fallido. Revisa cinco páginas en EN/ES/FR/AR a 1440/768/390/320 px, con sesión de administrador.

No requiere migraciones ni proveedores de mapas nuevos. El despliegue se limita a DEV, conservando las otras extensiones de su imagen vigente. La copia previa se restaura en una base aislada y se contrastan huellas de datos antes y después.
