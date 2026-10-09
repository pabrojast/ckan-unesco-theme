# Membresías de iniciativas

Permite solicitar la incorporación a una iniciativa existente. Es independiente
de [[Solicitudes de Iniciativas]], que gestiona la creación de nuevos grupos.

## Flujo

1. Un usuario autenticado no miembro pulsa **Request to Join** en la iniciativa.
2. Envía un mensaje opcional. La página pasa a **Request Pending**.
3. Un administrador activo de esa iniciativa, o un sysadmin, revisa la solicitud
   desde **Requests** o desde la campana de revisiones.
4. Puede aprobar con rol `member` (predeterminado), `editor` o `admin`, o rechazar
   con una nota opcional. La aprobación crea una membresía CKAN mediante
   `member_create`; aparece en la pestaña pública **Members**.
5. El historial registra quién resolvió, cuándo, el rol y la nota. Tras un rechazo
   se permite otra solicitud. Si una membresía ya se concedió por otra vía,
   la aprobación conserva ese rol.

Las iniciativas elegibles son grupos CKAN activos de tipo `group`, excluyendo
`member-states` y sus hijos activos, igual que el directorio de iniciativas.
Los administradores de otras iniciativas y los editores no pueden revisar.

El flujo se muestra también en la portada y las pestañas de AI for Water.
Un visitante que accede al formulario es enviado al login con retorno al mismo.
Las organizaciones mantienen sus acciones, tabla y URLs existentes.

## Interfaz HTTP y API

| Ruta | Métodos | Uso |
|---|---|---|
| `/group/<name>/request-membership` | GET, POST | Solicitar membresía |
| `/group/<name>/membership-requests` | GET, POST | Pendientes e historial (`tab=history`), aprobar/rechazar |
| `/initiative-membership-requests` | GET | Resumen de iniciativas con pendientes; si hay una, redirige a ella |

| Acción | Entradas | Autorización |
|---|---|---|
| `initiative_membership_request_create` | `group_id` (UUID/nombre), `message` opcional | Usuario activo autenticado, no miembro, sin pendiente |
| `initiative_membership_request_list` | `group_id`, `status` opcional | Admin de la iniciativa o sysadmin |
| `initiative_membership_request_process` | `group_id`, `id` de solicitud, `action=approve/reject`, `role=member/editor/admin`, `admin_note` opcional | Admin de esa iniciativa o sysadmin |
| `initiative_membership_request_count` | Sin parámetros | Conteo de pendientes que puede gestionar el usuario actual |

`create` y `process` devuelven el registro de solicitud. `list` devuelve
`{group, results, count}` y `count` devuelve `{count}`. La identidad del solicitante
sale del contexto autenticado; no se acepta un usuario ni un rol elegido por él.
Los mensajes y notas sólo se muestran en las pantallas administrativas.

## Persistencia y protección

`InitiativeMembershipRequest` usa la tabla `initiative_membership_request`:
`id`, `user_id`, `group_id`, `message`, `status`, `role`, `created_at`,
`handled_by`, `handled_at` y `admin_note`. El plugin la crea de forma idempotente
al iniciar. No transforma ni copia solicitudes de organizaciones.

Un índice único parcial evita dos pendientes para el mismo usuario/iniciativa.
Los cambios bloquean la fila del grupo y la resolución bloquea además la
solicitud. La aprobación y `member_create(defer_commit=True)` comparten commit;
una segunda decisión se rechaza. Las vistas POST comprueban CSRF explícitamente,
incluso cuando CKAN permite exenciones a extensiones antiguas, y las páginas de
solicitudes se sirven con `Cache-Control: private, no-store`.

## Avisos

La cola `initiative_membership` de la campana es por usuario: sólo cuenta sus
iniciativas administradas; sysadmins ven todas las elegibles. Crear y resolver
invalida la caché de los revisores.

El email de nueva solicitud se envía a los administradores locales activos;
si no hay ninguno, a los sysadmins activos. El solicitante recibe la resolución.
Los envíos ocurren después del commit; un fallo de SMTP se registra y no revierte
la operación. Usa la configuración de correo existente, sin claves nuevas.

## Validación y publicación

Ver [[Testing#Membresías de iniciativas]]. El cambio se publica en la rama `dev`
del tema; publicarlo no ejecuta un despliegue de CKAN.
