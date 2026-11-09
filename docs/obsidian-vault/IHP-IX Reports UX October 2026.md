# IHP-IX Reports UX — octubre 2026

Rediseño de las dos salidas verificables de IHP-IX (2026-10-23, rama `dev210`, **sin desplegar**): el informe narrativo `/ihpix/reports/generate` y la presentación `/ihpix/presentation`. Antes eran texto plano y tablas HTML; ahora comparten un registro de secciones con fichas, gráficos SVG generados en servidor y anexo de fuentes opcional.

## Decisiones

- **Gráficos SVG en servidor** (`ihpix_charts.py`, módulo puro): se imprimen nítidos en PDF, no dependen de JavaScript ni de Chart.js, se prueban con pytest sin CKAN y el mismo gráfico sirve para documento y diapositiva. Los dashboards de Progress siguen con Chart.js; la paleta es la misma (`PA_COLORS`, categórica de 8 tonos, neutro para Other/Unspecified).
- **Sin mapa**: barras por región UNESCO + tabla de países por rol (reporta / apoya / beneficiario). `ihpix_stats` añade `overview.countries` y `kpi_6.countries` porque el mapa omite los países sin coordenadas.
- **Anexo de fuentes opcional y compacto**: tabla agrupada por PA → Output (título enlazado al detalle, institución, Outputs, bienio). Va **marcado por defecto** (informe verificable; `DEFAULT_SOURCES` en `ihpix_views.py`); la descripción y los resultados sólo con "Include descriptions and outcomes".
- **Secciones modulares**: `ihpix_report_sections.build_sections` produce la lista ordenada; el formulario tiene un checkbox por sección (todas marcadas) y la selección viaja en la URL (`sections`, multivalor, con `sections_given=1`). La presentación acepta el mismo `sections`.
- **Traducción inyectada**: la vista pasa `tk._` a los módulos puros (el texto del SVG se genera en Python). Claves en `ihpix_i18n_strings.REPORT_LABELS`.
- **Sin JavaScript nuevo**: "Show as table" en el documento es `<details>`; `ihpix-presentation.js` no cambia. CI sin cambios.

## Secciones (D = dimensión del ámbito: PA / Output / Key Activity)

| id | Título | Series | Figuras | Documento | Diapositivas |
|---|---|---|---|---|---|
| overview | Implementation overview | `overview.*` | fichas | portada + fichas + resumen | fichas grandes |
| dimension | Activities by priority area / Output / key activity | `by_dimension`; `by_output` en overall/flagship/ctwg | donut (3–8 PA) o barras; barras de Outputs con leyenda PA | ambas + tabla | una por figura |
| geography | Where the activities take place | `by_region`, `countries` | barras por región | barras + tabla de países | barras + top 4 |
| timeline | Activities per biennium | `by_biennium` (4 bienios), `output_biennium_matrix` | columnas | columnas + matriz Output × bienio | columnas |
| kpi_1 | Knowledge and scientific products | `kpi_1.*` | apiladas por D; barras por tipo ×2 (sólo doc) | todo | apiladas |
| kpi_2 | Knowledge exchange | `kpi_2.*` | barras por D; % jóvenes/mujeres; por tipo de actividad (doc) | todo | barras |
| kpi_34 | Training and education | `kpi_3.*` + `kpi_4.*` | apiladas (materiales, currículos); por tipo (doc) | todo | apiladas |
| kpi_5 | Awareness raising | `kpi_5.*` | barras por D; % | todo | barras |
| kpi_6 | Transboundary water systems | `kpi_6.*`, `kpi_6.countries` | barras por D | barras + tabla países | barras |
| kpi_8 | Stakeholder groups with strengthened capacity | `kpi_8.*` | barras por D; por tipo (doc) | todo | barras |
| produced_reached | What was produced and who was reached | `produced_by_dimension`, `reached_by_dimension` | apiladas ×2 | ambas | dos diapositivas |
| institutions | Institutions with most activities | `top_institutions` | barras (≤ 10) | barras | barras + top 4 |
| sources | Appendix: source activities | fuentes de la acción | — | tabla compacta (+ detalle) | nunca |

Con 0 actividades cada figura muestra "No data" y el documento un único aviso.

## Reglas de dibujo

Barras ≤ 24 px con extremo redondeado y base cuadrada, sin gridlines (valor directo en tinta al final de la barra), hueco de 2 px en color de superficie entre segmentos apilados y rebanadas, leyenda siempre con ≥ 2 series, texto nunca en color de serie, `<title>` y `<desc>` con todos los valores. Validador dataviz sobre la paleta categórica: todas las comprobaciones pasan; el peor par adyacente (PA5/PA4, ΔE 8,6 deutan) obliga a etiquetas directas, que siempre se dibujan. Documento: viewBox 680 px, máximo 15 filas por gráfico (el resto en la tabla); diapositivas: viewBox 520 px escalado por el navegador, 8 filas y etiquetas cortas de PA.

> [!note] Pendiente por confirmar
> El anexo marcado por defecto en `overall` (744 filas ≈ 15 páginas A4) y la revisión del árabe en DEV con datos reales. En el render local con los catálogos compilados el árabe dentro de los SVG se ve correcto (la raíz fuerza `direction:ltr`; los glifos se ligan y las etiquetas mixtas "PA1 – …" conservan el orden). DOC-035.

## Traducciones

84 claves nuevas por idioma (`REPORT_LABELS` + literales de las plantillas + etiquetas de filtro) añadidas directamente a los `.po` de es/fr/ar con el comentario `#: IHP-IX reports October 2026`, al `.pot`, y compiladas con `msgfmt` (Babel no está instalado localmente). Terminología alineada con el catálogo existente (Output → Producto / Produit / المخرج, Priority Area → Área prioritaria…). Las filas destacadas de las diapositivas se recortan a 80 caracteres (`ihpix_presentation.LABEL_LIMIT`) porque los títulos de Output llegan a 300.

## Verificación reproducible

- Suite pura (216 pruebas): `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q ckanext/theme_ejemplo/tests/test_ihpix_*.py` (incluye `test_ihpix_charts.py`, `test_ihpix_report_sections.py`, el snippet `report_section.html` en el test de código vivo y la cobertura i18n de `REPORT_LABELS`).
- Taxonomía: `python3 scripts/build_ihpix_taxonomy_data.py --check`.
- Navegador: `scripts/playwright/ihpix_review.cjs` (SVG en diapositivas, `sections` limita a 2 páginas, anexo en el informe, PDFs) y `scripts/playwright/ihpix_progress_filters.cjs` (SVG en el informe, 12 secciones sin anexo, selección `sections_given`, presentación con `sections`); ambos restringidos a localhost.
- Sin CKAN: las plantillas se renderizaron con Jinja2 y helpers simulados (`page.html`, `forms_assets`, `country_options` sustituidos) y datos sintéticos de 80 actividades; capturas a 1200/390 px sin desbordamiento horizontal, 14 diapositivas (overall) y 13 (output), PDF A4 de 22 páginas con anexo y PDF 16:9 de una diapositiva por página; informe y diapositivas también en es y ar (RTL) con los `.mo` compilados. Esta comprobación no sustituye la prueba en dev con datos reales (744 filas).

## Estado

Código en `dev210` sin desplegar en DEV. Receta de despliegue en [[Deployment#Despliegue a desarrollo (data.dev-wins.com)]]; no requiere migraciones (los campos nuevos de `ihpix_stats` se calculan al vuelo y la caché de `ihpix_progress_stats` versiona el payload).
