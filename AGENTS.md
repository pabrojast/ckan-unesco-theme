# AGENTS.md

Guía operativa para Codex y otros agentes de código que trabajan en este repositorio.

## Alcance

Extensión CKAN (`ckanext-theme-ejemplo`) que implementa el tema de producción del portal de datos hídricos de UNESCO. Plugin: `theme_ejemplo`. Target: CKAN 2.9/2.10.

## Documentación

- **Fuente de verdad humana**: `docs/obsidian-vault/` (abrir `Index.md` para navegar)
- **Guía para Claude Code**: `CLAUDE.md`
- **Este archivo**: reglas operativas para Codex

Ante dudas sobre arquitectura, flujos o configuración, consulta la vault antes de asumir.

## Orden de trabajo recomendado

1. **Explorar** — Leer los módulos relevantes antes de actuar. Consultar `docs/obsidian-vault/Modulos.md` y `Arquitectura.md` para contexto.
2. **Planificar** — Identificar archivos a modificar y efectos secundarios.
3. **Implementar** — Hacer cambios mínimos y focalizados.
4. **Verificar** — Ejecutar tests si es posible: `pytest --ckan-ini=test.ini`
5. **Documentar** — Actualizar vault si el cambio afecta documentación (ver abajo).

## Cuándo actualizar la vault

Si tu cambio afecta alguno de estos aspectos, actualiza los documentos correspondientes en `docs/obsidian-vault/`:

| Cambio | Documentos a actualizar |
|---|---|
| Nueva ruta/vista | `Flujos Importantes.md`, `Modulos.md` |
| Nueva acción o auth | `Modulos.md` |
| Nuevo modelo de DB | `Arquitectura.md`, `Modulos.md` |
| Nueva clave de config | `Variables de Entorno.md` |
| Cambio en CI/CD | `Deployment.md`, `Testing.md` |
| Nuevo comando | `Comandos Utiles.md` |
| Nueva dependencia | `Setup Local.md`, `Deployment.md` |

## Reglas para cambios

- **No inventar comportamiento**. Si algo no está claro, documenta la duda.
- **Cambios mínimos y focalizados**. No refactorizar código no relacionado.
- **Mantener convenciones**: comentarios en español, código en inglés, config con prefijo `ckanext.theme_ejemplo.*`.
- **Mantener consistencia con `CLAUDE.md`**. Si un cambio requiere actualizar reglas operativas, actualizar ambos archivos.
- **No eliminar marcadores de incertidumbre** ("Pendiente por confirmar", "Inferencia") a menos que puedas verificar la información.

## Convenciones para documentar dudas

En código (comentarios):
```python
# TODO: verificar si este comportamiento es correcto cuando X
# SUPUESTO: asumimos que Y porque Z
```

En la vault, usar callouts de Obsidian. Ver formato y convenciones en `docs/obsidian-vault/Guia de Mantenimiento.md`.

## Checklist antes de cerrar una tarea

- [ ] Los cambios compilan/cargan sin errores
- [ ] No se rompieron tests existentes (si se pueden ejecutar)
- [ ] Si se agregó configuración nueva, está documentada en `Variables de Entorno.md`
- [ ] Si se agregaron rutas nuevas, están documentadas en `Flujos Importantes.md` y `Modulos.md`
- [ ] Si se modificó arquitectura, `Arquitectura.md` refleja el cambio
- [ ] `CLAUDE.md` y `AGENTS.md` siguen siendo consistentes entre sí
- [ ] No se inventó información ni se eliminaron marcadores de incertidumbre

## Estructura del código

El código fuente está en `ckanext/theme_ejemplo/` (8 módulos Python, 135 templates, 3 idiomas).
Para el mapa completo de módulos y roles, ver `CLAUDE.md` § "Estructura del código" o `docs/obsidian-vault/Modulos.md`.
