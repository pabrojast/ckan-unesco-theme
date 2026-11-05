# Comunidad de Practica DACS

Plataforma de miembros de la **Década de Acción para las Ciencias Criosféricas 2025–2034** (DACS Community 3.29, escrita por Alexandre Germouty para Firebase), integrada en IHP-WINS sin Firebase. Añadida por Jorgen Van Der Biest (noviembre de 2026).

- **URL:** `/group/dacs/community-of-practice` (p. ej. https://preview.dev-wins.com/group/dacs/community-of-practice)
- **Inicio de sesión:** la cuenta y la sesión de IHP-WINS (CKAN). No hay cuentas propias.
- **Datos:** tabla `dacs_community_document` en la base de CKAN, creada en el primer uso (sin migración).
- **Permisos:** el mismo archivo de reglas de la versión Firebase, ejecutado en Python.

## Piezas

| Pieza | Archivo | Rol |
|---|---|---|
| Rutas | `community.py` | Página (`GET /group/<name>/community-of-practice[/...]`) y API (`POST .../api/<accion>`); registradas con una línea en `plugin.py` |
| Almacén y protocolo | `community_store.py` | Documentos JSON por ruta (`events/abc/agenda/1`), consultas, lotes y transacciones; no importa CKAN |
| Reglas | `community_rules.py` | Intérprete del lenguaje de reglas de Firestore (subconjunto que usa la aplicación) |
| Archivo de reglas | `community_data/dacs.rules` | Copia de `firestore.rules` de la versión Firebase; solo cambia `secretariatOwner()` |
| Interfaz compilada | `public/dacs-community/` | `index.html`, `bundle/` (JS/CSS) y `logo-desk/`; `assets/` y `favicon.png` son archivos estáticos (fotos, vídeo, logotipos, plantillas) |
| Código fuente | `frontend/dacs-community/` (raíz del repo, fuera de la imagen Docker) | Aplicación React; `shims/` sustituye `firebase/app`, `firebase/auth` y `firebase/firestore` |

## Flujo de una petición

1. CKAN sirve `index.html` en la URL del grupo e inyecta `window.__DACS__` (rutas, URL de login/registro/logout, token CSRF). Respuesta `Cache-Control: no-store` (fuera del caché anónimo de `cache.py`).
2. La aplicación llama a la API con `fetch` (misma sesión): `me` (usuario), `read` (documentos y consultas), `commit` (escrituras atómicas).
3. Cada lectura y escritura pasa por `RulesEngine` con la identidad de CKAN: `request.auth.uid` = id del usuario CKAN, `request.auth.token.email` = su correo, `request.auth.token.platform_admin` = sysadmin o administrador del grupo CKAN.
4. Las consultas siguen la semántica de Firestore: las reglas no filtran; una consulta que no se puede probar con sus filtros se rechaza entera.
5. Las escuchas en vivo (`onSnapshot`) se sirven por sondeo cada 20 s y se refrescan al escribir.

> [!note] Administradores
> El rol "propietario" de la versión Firebase (acceso completo de la Secretaría de UNESCO, moderación de mensajes) correspondía a una dirección de correo fija. En IHP-WINS lo tienen los **sysadmins** y los **administradores del grupo CKAN** `dacs`. Las demás funciones se asignan dentro de la aplicación (Governance → Manage access & badges), como antes.

## Seguridad de la API

- Solo `POST` con cuerpo JSON y cabecera `X-DACS-Request: 1`; se rechaza un `Origin`/`Referer` de otro sitio.
- Se envía el token CSRF de CKAN (`X-CSRFToken`) cuando existe.
- Tamaño máximo de petición: 24 MB; de documento: 1,2 MB (Firestore: 1 MiB).

## Compilar y probar

```bash
cd frontend/dacs-community
npm ci
npm run build:ckan     # tsc + vite build en ckanext/theme_ejemplo/public/dacs-community
npm test               # 59 pruebas unitarias de la aplicación
npm run test:rules     # pruebas de reglas de la versión Firebase contra esta API (SQLite)
```

`npm run test:rules` arranca `tests/support/harness.py` (mismo código Python que CKAN, SQLite en memoria) y ejecuta `tests/rules.test.mjs` sin cambios. Resultado actual: **72 de 76**.

> [!note] Inferencia
> Las 4 pruebas que fallan esperan el comportamiento anterior a dos cambios de reglas de la propia versión Firebase: el acceso a la revisión de logotipos por nombramiento (retirado en 3.26) y la edición del proyecto de una actividad por quien la propuso (añadida en 3.24). Con el emulador de Firebase fallarían igual.

## Pendiente por confirmar

> [!note] Pendiente por confirmar
> - Si `ckan.csrf_protection.ignore_extensions` está a `false` en producción: la API envía el token, pero no se ha probado en ese modo.
> - Límite de tamaño de cuerpo del ingress (los adjuntos de hasta 10 MB se guardan en trozos de 900 kB por escritura).
> - Si el grupo `dacs` existe en preview y producción; la página funciona sin él, pero entonces solo los sysadmins son administradores.

## Límites conocidos

- Los archivos y fotos se guardan dentro de la base (como en la versión Firebase), no en el almacenamiento de CKAN.
- Las consultas leen todos los documentos de una colección y filtran en Python: adecuado para una comunidad de cientos de miembros.
- Las cuentas se gestionan en IHP-WINS: restablecer contraseña y borrar cuentas se hacen en las páginas de usuario de CKAN.
