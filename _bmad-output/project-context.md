---
project_name: 'ckan-unesco-theme'
user_name: 'Pablo'
date: '2026-06-17'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'code_quality_rules', 'workflow_rules', 'critical_rules']
status: 'complete'
rule_count: 50
optimized_for_llm: true
---

# Project Context for AI Agents

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

- **CKAN 2.9** target with forward compat for 2.10 (use `before_dataset_index`, `before_dataset_search` for 2.10; `before_index`, `before_search` aliases for 2.9)
- **Python 3.x** — namespace package under `ckanext/`
- **Flask** — Blueprint-based routing via `IBlueprint` interface
- **SQLAlchemy** — ORM via `ckan.model`, 8 custom tables in `model.py`
- **PostgreSQL** — primary DB, materialized views for tracking stats
- **Shapely < 2** — spatial bbox→WKT pipeline for Solr; v2 breaks API
- **ckanext-schemingdcat** — facet dicts (`utils.get_facets_dict()`)
- **ckanext-scheming** — dataset form view (`SchemingCreateView`)
- **Redis** — anonymous response cache via `IMiddleware` (`cache.py`)
- **Solr** — search backend, multi-language facet sanitization for atomic updates
- **Babel** — i18n message extraction (AR, ES, FR via `setup.cfg`)
- **MarkupSafe** — safe HTML in template helpers
- **CI Docker images**: `ckan/ckan-postgres-dev:2.9`, `ckan/ckan-solr:2.9`, `redis:3`, `openknowledge/ckan-dev:2.9`
- **Tests**: `pytest --ckan-ini=test.ini`

### Critical version constraints
- `shapely<2` **required** — will not install/run with Shapely ≥ 2
- Forks of scheming extensions specified in CI workflow

## Critical Implementation Rules

### Language-Specific Rules (Python / CKAN)

- MUST inherit `plugins.SingletonPlugin, DefaultTranslation` for the main plugin class
- Register CKAN interfaces with `plugins.implements(plugins.IXxx)` at class body level
- Decorate read-only actions with `@toolkit.side_effect_free`
- All config keys use prefix `ckanext.theme_ejemplo.*`; read via `toolkit.config.get(key, default)` with `toolkit.asint()`/`toolkit.asbool()` for coercion
- NEVER let exceptions escape top-level handlers — catch, log, return safe defaults (empty list, empty dict, original input)
- Rollback `model.Session` on helper/query failures with `_rollback_session_after_helper_error()`
- Use module-level TTL dicts for simple caches: `{'data': ..., 'expires': time.time() + ttl}`
- Use `@lru_cache` with cache buster pattern: `int(time.time() / ttl)` as extra positional arg
- Comments and log messages in **Spanish**; code identifiers in **English**
- Model convention: `get()`, `get_all()`, `get_by_*()`, `as_dict()`, `init_*_db()` (idempotent via SQLAlchemy inspector)

### Framework-Specific Rules (CKAN / Flask)

- Routes via `Blueprint(self.name, self.__module__)` with `add_url_rule(path, endpoint, view_func, methods)`
- All view functions are `@staticmethod` on `MyLogica` class in `controller.py`
- Use `toolkit.render('template.html', extra_vars={...})` or `render_template()` for responses
- CKAN API calls: `toolkit.get_action('action_name')(context, data_dict)` — NEVER bypass this for CKAN core ops
- Admin endpoints: gate with `context.get('ignore_auth', True)` and auth function check
- Every action in `get_actions()` MUST have a matching auth function in `get_auth_functions()`
- Auth functions return `{'success': bool, 'msg': str}` dict
- Template helpers registered in `get_helpers()` as `{'name': callable}` dict
- Return `Markup(str)` (from `markupsafe`) for helpers that output HTML
- DB models: define table with `define_*_table()`, init idempotently with `init_*_db()` using `inspector.has_table()`
- Migrations: `_migrate_*()` methods use `inspector.get_columns()` to check for missing columns and `ALTER TABLE`

### Testing Rules

- Framework: `pytest --ckan-ini=test.ini` (requires CKAN + PostgreSQL + Solr + Redis via Docker)
- Test files live in `ckanext/theme_ejemplo/tests/` (parallel to source)
- `test.ini` enables only `theme_ejemplo` plugin, inherits from `test-core.ini`
- Coverage: `pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo`
- Mock heavy search/Solr calls when testing business logic in isolation
- Test new DB models with `init_*_db()` setup/teardown within test functions

### Code Quality & Style Rules

- **Spanish** comments, docstrings, log messages; **English** code identifiers
- Naming: `snake_case` files/vars/functions, `PascalCase` classes, `UPPER_SNAKE` constants
- Private internals prefixed with `_` (e.g., `_process_spatial_data`, `_member_states_cache`)
- Module-level logger: `log = logging.getLogger(__name__)` at top of each file
- One concern per module — model, actions, auth, helpers, controllers are separate files
- No cross-imports in `__init__.py`; import modules explicitly where used
- Uncertainty markers in code: `# TODO:`, `# SUPUESTO:`
- Vault markdown: Spanish titles, `[[wikilinks]]`, `> [!note/warning/tip]` callouts

### Development Workflow Rules

- Setup: `pip install -e . && pip install -r requirements.txt`
- i18n compilation: `python setup.py compile_catalog` (domain: `ckanext-theme_ejemplo`)
- CLI commands: `ckan ihpix seed-data` (seed IHP-IX data), `ckan openlearning sync` (sync UNESCO courses)
- After changing routes/views → update `docs/obsidian-vault/Flujos Importantes.md` and `Modulos.md`
- After changing actions/auth → update `docs/obsidian-vault/Modulos.md`
- After changing DB models → update `docs/obsidian-vault/Arquitectura.md` and `Modulos.md`
- After changing config keys → update `docs/obsidian-vault/Variables de Entorno.md`
- After changing dependencies → update `docs/obsidian-vault/Setup Local.md` and `Deployment.md`

### Critical Don't-Miss Rules

- **DON'T use `toolkit.get_action('group_show')` with `include_groups=True`** — causes N+1; use direct SQLAlchemy queries instead
- **DON'T let exceptions reach Jinja2** — all helpers must catch and return safe defaults
- **MUST sanitize multi-language dicts to JSON strings** before Solr indexing — dicts with 2-letter keys (`en`, `es`, `fr`, `de`, etc.) break atomic updates
- **MUST pair every action with an auth function** — even public reads get explicit `{'success': True}` auth
- **DON'T use `ignore_auth: True` in user-facing contexts** — reserved for internal/system operations only
- **Session rollback required** after helper DB failures — call `model.Session.rollback()`
- **Open Learning sync preserves manual curation** — upsert never touches `status` or `display_order`
- **IHP-IX seed**: use `--append` to add without deleting existing data; structure must match `IhpixActivity`/`IhpixCountrySummary` schema
- **Config access ONLY via `toolkit.config.get(key, default)`** — never import or access INI files directly

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code
- Follow ALL rules exactly as documented
- When in doubt, prefer the more restrictive option
- Update this file if new patterns emerge

**For Humans:**
- Keep this file lean and focused on agent needs
- Update when technology stack changes
- Review quarterly for outdated rules
- Remove rules that become obvious over time

Last Updated: 2026-06-17
