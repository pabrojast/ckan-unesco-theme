# IHP-IX Entity Links — octubre 2026

Reporte de UNESCO (2026-10-23): en `/ihpix/outputs` las actividades muestran Member States, flagships y organizaciones, pero no aparecían en las pestañas IHP-IX correspondientes (`/group/<name>/ihpix`, `/organization/<name>/ihpix`). Código en `dev210`, **sin desplegar**.

## Causas encontradas (por código y con los grupos reales de dev vía API pública)

1. **Iniciativas**: `group_ihpix` filtraba siempre por `country=<slug del grupo>`; para `friend-water`, `g-wadi`, `lasii`… nunca había coincidencia y la pestaña salía vacía. Además el filtro `flagship` del modelo usaba `ILIKE` sobre el texto crudo (`GWADI` heredado no casaba con `G-WADI`).
2. **Member States**: el índice de países indexaba el título del grupo sin pasar por los alias. Para seis países (Venezuela, Palestina, Micronesia, Côte d’Ivoire, RPD Corea, Lao) el slug del formulario y el nombre heredado normalizado caían en canónicos distintos, así que la pestaña (que filtra por slug) perdía las filas heredadas. Los apóstrofos tipográficos (`’` vs `'`) separaban también Côte d’Ivoire.
3. **Organizaciones**: el botón "Full Explorer" pasaba el **título** de la organización y el explorador lo resolvía con `Group.get` (id o nombre) → 0 resultados sin chip visible. La pestaña en sí sólo lista actividades vinculadas por id; las filas heredadas no lo están (DOC-036).
4. **Sin enlaces**: las fichas del explorador eran texto; el país sede salía como slug en las filas del formulario.

## Arreglos

- `ihpix_entities.group_scope` clasifica el grupo (Member State / flagship / CTWG / sin atribución) y `group_ihpix` filtra en consecuencia; `IhpixActivity._scope_ids` aplica la misma normalización que Progress a flagship y CTWG (`get_filtered` y `_apply_stat_filters`). Enlaces "Progress" y "Full Explorer" por ámbito; aviso claro en iniciativas sin equivalente.
- `ihpix_stats.build_country_index` pasa el título del grupo por los alias y `ihpix_normalize._key` pliega apóstrofos: slug y heredado comparten canónico (test en `test_ihpix_stats.py`).
- Explorador: filtros `organization` (nombre o id), `flagship` y `ctwg` (código o slug) con chips legibles; macro `explorer_url` conserva los filtros en chips y paginación. El enlace de la pestaña de organización pasa `name`.
- Fichas enlazadas en explorador y pestañas (`ihpix/snippets/entity_chips.html`): institución → pestaña de la organización (si hay id), país sede y Member States beneficiarios/de apoyo → pestaña del grupo, flagships → pestaña de la iniciativa (18 de 21 en dev) o panel de progreso, CTWG → panel de progreso. Países no resueltos se muestran atenuados sin enlace.
- Traducciones: 7 literales nuevos en es/fr/ar (+ el aviso vacío de Member State que estaba sin traducir), `.pot` y `.mo` compilados con `msgfmt`.

## Verificación

- Suite pura: 223 pruebas (`test_ihpix_entities.py`, `test_ihpix_stats.py`, `test_ihpix_constants.py`).
- Simulación del índice de dev (205 resúmenes + 211 grupos de país de la API pública) antes/después del arreglo: 6 slugs resolvían a un canónico distinto; 0 tras el cambio.
- Render Jinja2 con helpers simulados de `ihpix/outputs.html`, `group/ihpix.html` (country / flagship / sin atribución) y `organization/ihpix.html`, capturas Playwright a 1200 px sin desbordes.
- `scripts/ihpix_dev_smoke.py` añade las pestañas y los filtros nuevos a su lista de páginas.

## Vinculación asistida de instituciones (admin, 2026-10-24)

Petición de UNESCO: una opción de administración para hacer *match* entre las instituciones heredadas y las organizaciones de IHP-WINS. Implementado en `dev210`, **sin desplegar**.

- **Panel** `/ckan-admin/ihpix/institutions` (sysadmin; pestaña "Institutions" en el admin IHP-IX, botón "Link institutions" en Overview y atajo desde la pestaña vacía de una organización). KPIs (instituciones sin organización, actividades afectadas, ya vinculadas, sin institución), filtro `q`, una fila por institución (variantes de escritura agrupadas por clave normalizada, conteo y estados) con hasta 3 sugerencias (título, % y razón) y un selector de organización; las sugerencias ≥ 90 % quedan preseleccionadas y el botón "Select all confident suggestions" las marca de golpe. Sección plegable "Already linked institutions" con "Unlink".
- **Sugerencias** (`ihpix_org_match`, puro): exacto por título o `name` (el slug suele ser el nombre largo: `international-centre-for-water-resources-and-global-change` ↔ "ICWRGC"), acrónimo entre paréntesis, nombre contenido, primer tramo de un texto compuesto, iniciales, palabra clave y parecido. Con las 746 filas reales de dev (lectura del 2026-10-24; 311 grupos, las mismas claves que el seed; 0 filas con `institution_org_id`) y sus 134 organizaciones activas: 72 grupos confiables (212 actividades), 29 con alguna sugerencia (193) y 210 sin ninguna (340: universidades y entidades sin organización en el portal); ~2,5 s de cálculo.
- **Acción** `ihpix_institution_link` (`links: [{key | institution, organization_id, current_organization_id}]`): rellena `institution_org_id` en todas las actividades (cualquier estado) cuya institución comparte clave y no tenía organización; con `organization_id` vacío desvincula las que apuntan a `current_organization_id`. Cada actividad tocada se bloquea (`with_for_update`), conserva su baseline y recibe un snapshot (`ihpix_store`), es decir, una revisión en su historial; después se invalidan las cachés de estadísticas y se recalcula `IhpixCountrySummary`. El texto de la institución no se modifica. `ihpix_institution_link_list` (side-effect-free) devuelve los grupos y sugerencias para la API.
- **Verificación**: `test_ihpix_org_match.py` (8 pruebas, suite pura 231), render Jinja2 del panel con las 744 filas del seed y las organizaciones reales de dev + Playwright a 1280/390 px (sin desbordes; clic en sugerencia rellena el selector y marca la fila; "Deselect all" deja el envío deshabilitado; "Select all confident" marca 71). Página añadida a `scripts/ihpix_dev_smoke.py`. 40 literales nuevos en es/fr/ar.

> [!note] Inferencia
> Qué hacer con "IHP-LAC" (76 filas), "UNESCO IHP Secretariat" (41), "UNESCO IHP" (27) o "UNESCO" (11) es una decisión de UNESCO: el panel sugiere "Intergovernmental Hydrological Programme" al 70 % (sin preseleccionar) y no existe organización para IHP-LAC. Los `partners` en texto libre no se vinculan (sólo la institución líder).

> [!note] Verificado en dev (2026-10-24, sólo lectura)
> Con las 744 filas publicadas de dev y sus 210 grupos `member-states` (índice construido con y sin el arreglo): la pestaña de Venezuela pasa de 0 a 8 actividades, Micronesia de 0 a 3 y Palestina de 0 a 9; Côte d’Ivoire (24), RPD Corea (1), Lao (15) y los países de control (Chile 42, Kenya 47, Brasil 65, República de Corea 83) no cambian. 19 flagships tienen grupo de iniciativa (FRIEND 52 filas, G-WADI 28, IWRM 22, HELP 9, PCCP 2, LaSII 0); no hay grupos CTWG en dev. Ninguna de las 746 filas tiene `institution_org_id` (DOC-036). Falta la comprobación en el navegador tras desplegar y recalcular `IhpixCountrySummary`.
