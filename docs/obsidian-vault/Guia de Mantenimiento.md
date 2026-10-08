# Guía de Mantenimiento

> Cómo mantener actualizada esta vault de documentación.

---

## Principios

1. **La vault es la fuente de verdad humana**. `CLAUDE.md` y `AGENTS.md` referencian la vault, no la duplican.
2. **No inventar información**. Si algo no está verificado, marcarlo como "Pendiente por confirmar" o "Inferencia".
3. **Actualizar al cambiar código**. Cualquier cambio en arquitectura, rutas, configuración, modelos o comandos debe reflejarse en la vault.
4. **Priorizar claridad sobre completitud**. Mejor un documento corto y claro que uno largo y confuso.

---

## Cuándo actualizar la vault

| Tipo de cambio | Documentos a actualizar |
|---|---|
| Nueva ruta Flask | [[Flujos Importantes]], [[Modulos#controller.py]] |
| Nueva acción CKAN | [[Modulos#actions.py]], [[Modulos#auth.py]] |
| Nuevo modelo de DB | [[Arquitectura#Modelos de base de datos]], [[Modulos#model.py]] |
| Nueva clave de config | [[Variables de Entorno]] |
| Cambio en CI/CD | [[Deployment]], [[Testing]] |
| Nuevo comando útil | [[Comandos Utiles]] |
| Nuevo template/portal | [[Estructura del Repo]], [[Flujos Importantes]] |
| Cambio en dependencias | [[Setup Local]], [[Deployment]] |
| Nuevo idioma i18n | [[Comandos Utiles#Internacionalización]], [[Estructura del Repo]] |
| Bug resuelto recurrente | [[Troubleshooting]] |
| Nuevo test | [[Testing]] |
| Vacío descubierto | [[Backlog Documentacion]] |

---

## Convenciones de escritura

### Nombres de notas
- Usar español para nombres de notas
- Capitalizar primera palabra: `Flujos Importantes.md`, no `flujos importantes.md`
- Sin prefijos numéricos ni emojis

### Wikilinks
- Usar `[[Nombre de Nota]]` para enlaces internos
- Usar `[[Nombre de Nota#Sección]]` para enlaces a secciones específicas
- Ejemplo: `[[Modulos#controller.py]]`

### Callouts de Obsidian
```markdown
> [!warning] Título de advertencia
> Contenido de la advertencia.

> [!note] Nota informativa
> Contenido de la nota.

> [!tip] Consejo
> Contenido del consejo.
```

### Marcadores de incertidumbre

Para información no verificada:
```markdown
> [!note] Pendiente por confirmar
> [descripción de lo que falta verificar]
```

Para información deducida del código:
```markdown
> [!note] Inferencia
> [descripción de lo inferido y por qué]
```

---

## Proceso de revisión

### Revisión periódica
1. Cada mes, revisar [[Backlog Documentacion]] para vacíos pendientes
2. Verificar que las rutas en [[Flujos Importantes]] coincidan con `plugin.py`
3. Verificar que los módulos en [[Modulos]] reflejen el código actual
4. Verificar que [[Variables de Entorno]] incluya todas las claves de config

### Al hacer un release
1. Actualizar líneas de código en [[Estructura del Repo]] si cambiaron significativamente
2. Verificar que [[Deployment]] refleja el proceso actual
3. Resolver vacíos de [[Backlog Documentacion]] que sean bloqueantes

---

## Estructura de la vault

```
docs/obsidian-vault/
├── Index.md                  # Punto de entrada y navegación
├── Arquitectura.md           # Diseño del sistema
├── Estructura del Repo.md    # Mapa de archivos
├── Setup Local.md            # Instalación de desarrollo
├── Comandos Utiles.md        # Referencia de comandos
├── Variables de Entorno.md   # Configuración
├── Flujos Importantes.md     # Flujos de negocio
├── Modulos.md                # Detalle por módulo Python
├── Testing.md                # Estrategia de testing
├── Deployment.md             # CI/CD y releases
├── Troubleshooting.md        # Problemas comunes
├── Glosario.md               # Terminología
├── Backlog Documentacion.md  # Vacíos conocidos
├── Guia de Mantenimiento.md  # Este documento
└── README.md                 # README de la vault
```

---

## Para asistentes de código

Los asistentes de código (Claude, Codex) deben:
1. Leer `CLAUDE.md` o `AGENTS.md` para sus reglas operativas
2. Consultar la vault para información detallada
3. Actualizar la vault cuando sus cambios afecten la documentación
4. Nunca inventar información ni eliminar marcadores de incertidumbre

---

## Ver también

- [[Backlog Documentacion]] — Vacíos pendientes
- [[Index]] — Punto de entrada de la vault
