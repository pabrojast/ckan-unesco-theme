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

## Evidencia de entrega — 2026-10-22

Código: `bd3bf16ac74919bc1241405c7f53d65863ec8c16`. Suite pura: **147 pruebas**. Imagen candidata: **138 comprobaciones de navegador**, incluidos los cuatro idiomas y las anchuras documentadas. [Theme checks aprobado](https://github.com/pabrojast/ckan-unesco-theme/actions/runs/39796770852).

DEV: `pabrojast/ckan-base210@sha256:524e8bd7d90a91f79c8c464fdd18843ee0e4bf7ddd96ea7084a245e767910237`, pod `ckan-565fb576b-vt8mn`, 4/4 Ready y cero reinicios. Los 26 archivos modificados de la extensión coinciden por SHA-256 con el commit. Se conservaron las imágenes de los tres contenedores auxiliares y las demás extensiones de la imagen base vigente. No se desplegó en producción.

La comprobación funcional en `data.dev-wins.com` encontró **42 actividades vinculadas a Chile**, coincidentes entre gráficos, descarga y fuentes narrativas; también verificó presentación/regreso, búsqueda de países y enlace a borradores. Las capturas y resultados del recorrido visual están en `output/playwright/ihpix-progress-20261022-live/`.

Backup restaurado con 746 reportes. Huellas completas antes/después idénticas: 746 reportes (744 publicados, 1 pendiente, 1 borrador), 34 workspaces, 5 contribuciones, 0 vínculos y 0 membresías. Evidencia operativa privada: `/home/pabrojast/backups/ckan-dev-ihpix-progress-20261022/`; pruebas y logs en `qa-evidence/`.

### Ajuste final de selectores

La revisión móvil detectó que el input del combobox heredaba la flecha de fondo del select además de su botón propio; en árabe aparecían en extremos opuestos. `505a183bc4060b56f90cfccc22458ae703185d10` elimina ese fondo únicamente en el input del combobox. [Theme checks aprobado](https://github.com/pabrojast/ckan-unesco-theme/actions/runs/39800112437).

Imagen final de DEV: `pabrojast/ckan-base210@sha256:94547fbb3344ae58a5a5bebf60c462f903553c042cd5352f24b6cb5f5dc81e1c`, pod `ckan-8bf96d45b-bz9km`, 4/4 Ready y cero reinicios. Los 27 archivos comprobados coinciden por SHA-256 con el código publicado; las imágenes auxiliares y las huellas completas de datos siguen iguales. Esta imagen sustituye a la indicada arriba e incorpora el mismo cambio funcional.

El recorrido en DEV completó **108 comprobaciones funcionales y visuales** sobre el cambio principal, más **13 comprobaciones** del ajuste final de selectores en Progress, explorador y formulario, en EN/ES/FR/AR a 390 px. No hubo excepciones JavaScript. El token temporal de verificación fue revocado y una petición protegida confirmó HTTP 403; los contenedores y credenciales de las pruebas aisladas se retiraron.
