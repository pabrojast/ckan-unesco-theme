# CLAUDE.md

Guía de comportamiento para Claude Code al trabajar en este repositorio.

## Propósito del repo

Extensión CKAN (`ckanext-theme-ejemplo`, plugin `theme_ejemplo`) que implementa el tema de producción para el portal de datos hídricos de UNESCO (IHP). A pesar del nombre "ejemplo", es código de producción.

## Documentación principal

La fuente de verdad humana es `docs/obsidian-vault/`. Consulta la vault antes de asumir cómo funciona algo. Archivos clave:
- `Index.md` — mapa de navegación
- `Arquitectura.md` — diseño del sistema
- `Modulos.md` — detalle de cada módulo Python
- `Variables de Entorno.md` — claves de configuración
- `Flujos Importantes.md` — flujos de negocio

## Comandos esenciales

```bash
# Setup
pip install -e . && pip install -r requirements.txt

# Tests (requiere CKAN + PostgreSQL + Solr + Redis)
pytest --ckan-ini=test.ini

# Tests con cobertura
pytest --ckan-ini=test.ini --cov=ckanext.theme_ejemplo --disable-warnings ckanext/theme_ejemplo

# i18n: compilar traducciones
python setup.py compile_catalog
```

## Reglas operativas

### Código
- **CKAN 2.9** target con compatibilidad forward para 2.10
- Comentarios y logs en **español**; identificadores de código en **inglés**
- Config keys usan prefijo `ckanext.theme_ejemplo.*`
- Templates siguen patrón de override Jinja2 de CKAN, organizados por portal
- Requiere **Shapely < 2** y forks específicos de extensiones (ver CI workflow)

### Documentación
- **No inventar información**. Si no puedes verificar algo, márcalo como "Pendiente por confirmar"
- Si deduces algo del código, márcalo como "Inferencia"
- Cuando cambies arquitectura, rutas, config, modelos, variables de entorno o comandos: **actualiza `docs/obsidian-vault/`**
- No dupliques contenido extenso de la vault en este archivo. Referencia con rutas relativas

### Notas de la vault
- Nombres en español, capitalización de primera palabra: `Flujos Importantes.md`
- Usar wikilinks `[[Nombre]]` para enlaces internos
- Usar callouts de Obsidian: `> [!warning]`, `> [!note]`, `> [!tip]`
- Marcar incertidumbre con callouts: `> [!note] Pendiente por confirmar` o `> [!note] Inferencia`

### Prioridades
- Mantener onboarding simple y útil
- Priorizar claridad sobre completitud
- No romper wikilinks existentes al renombrar notas
- Registrar vacíos descubiertos en `Backlog Documentacion.md`

## Estructura del código

| Módulo | Rol |
|---|---|
| `plugin.py` | Clase principal, 7 interfaces CKAN, rutas, helpers, caches |
| `controller.py` | Clase `MyLogica`, 67 funciones de vista Flask |
| `actions.py` | 45+ acciones CKAN custom y overrides |
| `helpers.py` | 25 helpers de template (tracking, personas, orgs) |
| `model.py` | 6 modelos SQLAlchemy (membresías, publicaciones, tickets, portal cards, IHP-IX) |
| `auth.py` | 41 funciones de autorización |
| `validators.py` | 3 validadores de perfil de usuario |
| `utils.py` | Validación de imágenes (MIME, magic bytes) |