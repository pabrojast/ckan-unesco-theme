# ckanext-theme-ejemplo — Base de Conocimiento

Bienvenido a la documentación interna de **ckanext-theme-ejemplo**, la extensión CKAN que implementa el tema de producción para el portal de datos hídricos de UNESCO (IHP).

> [!info] Cómo usar esta vault
> Esta vault está diseñada para abrirse con [Obsidian](https://obsidian.md). Navega usando los wikilinks a continuación o desde el grafo de relaciones.

---

## Navegación rápida

### Onboarding
- [[Setup Local]] — Cómo levantar el entorno de desarrollo
- [[Comandos Utiles]] — Referencia rápida de comandos
- [[Estructura del Repo]] — Mapa de carpetas y archivos

### Arquitectura
- [[Arquitectura]] — Diseño general del plugin y sus capas
- [[Modulos]] — Detalle de cada módulo Python
- [[Flujos Importantes]] — Flujos clave del sistema
- [[Variables de Entorno]] — Configuración y claves de config
- [[Solicitudes de Iniciativas]] — Flujo de solicitud + aprobación sysadmin

### Operación
- [[Testing]] — Estrategia y ejecución de tests
- [[Deployment]] — CI/CD y proceso de release
- [[Troubleshooting]] — Problemas comunes y soluciones

### Referencia
- [[Glosario]] — Terminología del dominio
- [[Guia de Mantenimiento]] — Cómo mantener esta documentación
- [[Backlog Documentacion]] — Vacíos conocidos por documentar

---

## Contexto del proyecto

| Aspecto | Valor |
|---|---|
| Paquete | `ckanext-theme-ejemplo` |
| Plugin CKAN | `theme_ejemplo` |
| Target CKAN | 2.9 (compatible con 2.10) |
| Licencia | AGPL v3+ |
| Idiomas UI | Árabe, Español, Francés |
| Dependencias clave | Shapely, ckanext-spatial, ckanext-dcat, ckanext-scheming, ckanext-schemingdcat |

---

## Para asistentes de código

- Las reglas operativas para **Claude Code** están en `CLAUDE.md` (raíz del repo).
- Las reglas operativas para **Codex** están en `AGENTS.md` (raíz del repo).
- Esta vault es la **fuente de verdad humana**. Los archivos de agentes deben referenciarla, no duplicarla.
