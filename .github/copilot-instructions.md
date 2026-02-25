# Copilot Instructions

## Project Overview

CKAN extension providing a custom theme for UNESCO's water-related data portal. The package is named `ckanext-theme-ejemplo` and the plugin is registered as `theme_ejemplo`, but this is a production UNESCO theme — not a generic example.

## Build & Test Commands

```bash
# Install for development
pip install -e .
pip install -r requirements.txt
pip install -r dev-requirements.txt

# Run all tests
pytest --ckan-ini=test.ini

# Run a single test file
pytest --ckan-ini=test.ini ckanext/theme_ejemplo/tests/test_plugin.py

# Run a single test by name
pytest --ckan-ini=test.ini -k "test_plugin"

# Run with coverage (matches CI)
pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo
```

Tests require a running CKAN instance with Solr, PostgreSQL, and Redis. The CI uses `openknowledge/ckan-dev:2.9` Docker containers. See `.github/workflows/test.yml` for the full CI setup.

## Architecture

### Plugin Entry Point

`ckanext/theme_ejemplo/plugin.py` — `ThemeEjemploPlugin` implements six CKAN interfaces:
- **IConfigurer** — registers templates, public assets, and static resources
- **IBlueprint** — registers all custom Flask routes
- **ITemplateHelpers** — exposes template helper functions
- **IPackageController** — hooks into dataset indexing (`before_dataset_index`) for spatial data, facet processing, and Solr field sanitization
- **ITranslation** — enables i18n (Arabic, Spanish, French in `i18n/`)
- **IActions** — overrides `user_show`/`user_update` and adds `people_list`/`organization_people`

### Module Responsibilities

| Module | Role |
|---|---|
| `plugin.py` | Plugin class, CKAN interface implementations, caching, helpers registered on the plugin instance |
| `controller.py` | `MyLogica` class with all Flask view functions (static methods) |
| `helpers.py` | Standalone template helper functions (pagination, markdown, people directory, org stats) |
| `actions.py` | Custom CKAN action overrides — extended user profiles stored in `plugin_extras.theme_ejemplo` |
| `validators.py` | Validators for user profile fields (expertise areas, social links) |

### Custom Routes (all defined in `plugin.py` → `get_blueprint()`)

Portal pages: `/memberstates`, `/initiatives`, `/thematicbuilder`, `/ihpix`, `/ihpix/outputs`, `/iot-portal`, `/flood-drought-portal`, `/citizen-science-portal`

People & Orgs: `/people`, `/organization/<name>/people`, `/organization/<name>/publications`, `/organization/<name>/news`, `/organization/<name>/events`, `/organization/<name>/request-membership`

### Spatial Data Pipeline

The `before_dataset_index` hook converts bounding box fields (`xmin`, `ymin`, `xmax`, `ymax`) to WKT geometry via Shapely for Solr spatial indexing. This also handles multi-language facet sanitization to prevent Solr atomic update errors.

### Caching Strategy

Two patterns are used:
1. **Module-level TTL dicts** (`_courses_cache`, `_member_states_cache`, etc.) — manual expiry check with configurable TTL via `ckan.config`
2. **`@lru_cache` with cache busters** — `int(time.time() / cache_ttl)` as a parameter to expire entries (used for featured datasets, site statistics)

HTTP calls use a shared `requests.Session` at module level with connection pooling.

### User Profile Extension

Extended user fields (`job_title`, `institution`, `country`, `phone`, `website`, `orcid`, `expertise_areas`, `social_links`) are stored in CKAN's `plugin_extras` under the `theme_ejemplo` namespace. The `actions.py` overrides handle serializing/deserializing these fields.

## Key Conventions

- **CKAN 2.9 target** with forward compatibility for 2.10 (both `before_index` and `before_dataset_index` are implemented)
- **Dependencies**: Requires forks of ckanext-spatial, ckanext-dcat, ckanext-scheming, and ckanext-schemingdcat (see CI workflow for exact Git URLs)
- **Shapely < 2** is required (pinned in CI)
- Comments and log messages are in Spanish; code identifiers are in English
- Templates follow CKAN's Jinja2 override pattern — each portal has its own subdirectory under `templates/`
- Config keys use the `ckanext.theme_ejemplo.*` prefix (e.g., `ckanext.theme_ejemplo.courses_cache_ttl`)
