# Búsqueda

> Cómo busca cada superficie del portal, las sugerencias mientras se escribe y qué tocar si "no aparece lo que busco".

---

## Motor por superficie

| Superficie | Motor | ¿Importa el orden de las palabras? | Dónde |
|---|---|---|---|
| `/dataset` y buscador del header/home | Solr dismax (core) + campos n-grama | No | `plugin.py` `before_dataset_search` → `_enable_partial_match` |
| `/organization`, `/group`, `/initiatives`, `/memberstates` | Filtro en Python por tokens sobre un índice en memoria | No | `search.py` + `controller.py` (`_filter_names_by_query`) |
| `/people`, `admin_user_list` | SQL: un `ILIKE '%token%'` por palabra (AND) | No | `search.filter_by_tokens` desde `actions.py` |
| Desplegable de sugerencias | Las dos primeras combinadas | No | `GET /api/theme/suggest` |

> [!warning] Por qué no se usa el `q` de `organization_list` / `group_list`
> El core (`_group_or_org_list`) filtra con `ILIKE '%<frase completa>%'` sobre nombre, título y descripción. "water quality" encontraba 4 organizaciones y "quality water" ninguna. Por eso las vistas del tema **no pasan `q` a la acción**: piden la lista completa de nombres y la filtran con `search.search_entity_names()`. La API (`/api/3/action/organization_list?q=`) sigue con el comportamiento del core.

## Organizaciones, grupos, iniciativas y member states

`search.py` (ver [[Modulos#search.py]]):

1. `get_entity_index()` — una consulta SQL a `group` (activos) cacheada 300 s por proceso. Una entidad recién creada puede tardar hasta 5 min en ser buscable.
2. `match_score()` — normaliza (minúsculas, sin acentos, puntuación → espacio), exige **todos** los tokens en título + slug + descripción, en cualquier orden y como subcadena (sirve una palabra a medias). Puntaje: título exacto > prefijo > inicio de palabra > subcadena > slug > tokens sueltos > sólo en la descripción.
3. La lógica está portada de `ckanext-colab/lib/org_search.py` (el combobox de organización del registro). Se copia en vez de importarse porque colab es un plugin opcional.

### Orden de los resultados

`controller._resolve_entity_sort(q, sort)`:

| `?sort=` | Con `q` | Sin `q` |
|---|---|---|
| vacío o `relevance` | relevancia | contribución (`score desc`) |
| `score desc` | contribución | contribución |
| `title asc` / `title desc` / … | sort real del core | sort real del core |

`relevance` y `score desc` son pseudo-sorts: nunca llegan a la acción (su lista blanca los rechazaría). La opción "Relevance" sólo aparece en el desplegable cuando hay búsqueda.

## Datasets: coincidencia parcial

El `qf` del core (`name^4 title^4 tags^2 groups^2 text`) sólo encuentra palabras completas: "hidro" o "groundw" daban 0 resultados. El schema de Solr ya indexa `title_ngram` y `name_ngram` (n-gramas de 2 a 10 caracteres) pero nada los consultaba. `_enable_partial_match` los suma al `qf` con boost bajo (`title_ngram^0.8 name_ngram^0.5`), así la palabra completa sigue ganando.

- No requiere cambios en `schema.xml` ni reindexar.
- No se aplica si quien llama trae su propio `qf`, si `q` está vacío o si es una consulta de campo (`campo:valor`).
- Se apaga con `ckanext.theme_ejemplo.search_partial_match = false` (ver [[Variables de Entorno]]).

> [!note] Inferencia
> Los n-gramas sólo cubren título y slug. Una palabra a medias que sólo aparezca en la descripción o en los tags sigue sin encontrarse. Un término de más de 10 caracteres escrito a medias tampoco coincide por n-grama (límite `maxGramSize="10"` del schema).

## Sugerencias mientras se escribe

`GET /api/theme/suggest?q=<texto>&scope=<scope>` → `MyLogica.search_suggest`

| `scope` | Fuentes (en este orden) |
|---|---|
| `all` (default) | datasets, organizaciones, iniciativas, member states |
| `dataset` | datasets |
| `organization` | organizaciones |
| `group` | iniciativas, member states |
| `initiative` / `memberstate` | sólo esa |

Respuesta:

```json
{"query": "quali wat", "scope": "all",
 "groups": [{"type": "dataset", "label": "Datasets",
             "items": [{"title": "...", "url": "/dataset/...", "subtitle": "<organización>"}]}]}
```

- Menos de 2 caracteres → `groups: []`. Máximo 6 items por fuente (`SUGGEST_LIMIT`).
- Datasets: `package_search` con `qf` de n-gramas y `mm=100%`, con el usuario de la sesión (respeta datasets privados). `q` pasa por `search.escape_solr()` porque el texto a medio escribir (una comilla sin cerrar, un `:`) rompería la consulta.
- Entidades: mismo índice que los listados, pero **sin** la descripción (`include_description=False`): un resultado cuyo título no contiene lo escrito desconcierta en un desplegable.
- Si una fuente falla se registra un warning y las demás se devuelven igual.
- `Cache-Control: public, max-age=60` sólo para anónimos. `/api` está excluido del [[Modulos#cache.py|caché de respuestas anónimas]].

### Frontend

`public/search-suggest.js` + `public/css/search-suggest.css`, cargados desde `templates/base.html`. El script se activa en cualquier `<input name="q">` que tenga `data-suggest-scope` o esté **dentro** de un elemento que lo tenga. Así no hace falta sobreescribir `snippets/search_form.html` (su marcado difiere entre CKAN 2.9 y 2.10): basta envolver la llamada al snippet.

| Template | Scope |
|---|---|
| `header.html`, `home/snippets/search.html` | `all` |
| `package/search.html` | `dataset` |
| `organization/index.html` | `organization` |
| `group/index.html` | `group` |
| `initiatives/index.html` | `initiative` |
| `memberstates/index.html` | `memberstate` |

Comportamiento: debounce de 200 ms, `AbortController` para descartar respuestas viejas, patrón ARIA combobox/listbox, ↑/↓/Enter/Esc, resaltado insensible a acentos. **Enter sin sugerencia seleccionada envía el formulario normal**; sin JS o si el endpoint falla, el buscador funciona como siempre. La URL del endpoint y los textos llegan por atributos `data-*` del `<script>` (pasan por `url_for` y `_()`, así respetan el idioma).

Las cadenas del desplegable (`See all results for`, `No suggestions found`, `Search suggestions`) están traducidas en ar/es/fr; `Relevance`, `Member States` y las etiquetas de grupo ya existían en los catálogos.

## Tests

- `tests/test_search.py` — lógica pura, corre sin CKAN: `pytest --noconftest ckanext/theme_ejemplo/tests/test_search.py`
- `tests/test_plugin.py` — ruta del endpoint y `_enable_partial_match` (requieren entorno CKAN, ver [[Testing]])

## Ver también

- [[Flujos Importantes]] — flujo de `/people` y ranking por contribución
- [[Troubleshooting]]
