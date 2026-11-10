# Administración limitada de iniciativas

Una cuenta activa puede solicitar administrar una iniciativa existente. Los
administradores directos de esa iniciativa y los sysadmins revisan la solicitud;
si no hay administradores locales, se avisa a los sysadmins. No hay selector de
rol: aprobar concede Admin de esa iniciativa, incluida la gestión de miembros.

## Garantía de alcance

CKAN conserva la capacidad nativa `admin`. La concesión se registra en
`initiative_admin_scope`; un parche comprobado de `ckan.authz` excluye esas
membresías de la evaluación heredada hacia subgrupos. Los permisos directos
previos e independientes siguen vigentes. El marcador permanece con la
membresía para que una posterior reactivación no amplíe su alcance por omisión.

`member_create` recibe `defer_commit=True`: en CKAN 2.10 la acción
`group_member_create` descarta esta opción, por lo que no se usa para la
aprobación. Membresía, marcador y decisión se confirman atómicamente.

## Revisiones

Una solicitud pendiente bloquea otra para el mismo usuario/grupo. Rechazar
permite volver a solicitar. Un reintento de la misma decisión es idempotente;
no reenvía avisos. El destino guardado no se puede sustituir desde el formulario.
La interfaz escapa mensajes y notas, y los formularios conservan CSRF.

Las rutas y acciones verifican cuentas activas, grupo activo y autorización
local del revisor. No se usan permisos heredados para decidir quién revisa.
Las notificaciones se envían después del commit; fallos de correo no revierten
la decisión. La campana muestra únicamente solicitudes revisables.

## Despliegue

Ver [[Deployment]], [[Testing]] y [[Variables de Entorno]]. Mantener el flujo
desactivado hasta que todas las réplicas ejecuten la protección. Para contener
un fallo, desactivar solicitudes y conservar el parche; no borrar el historial.

## Delegación desde las pantallas nativas

Las acciones encadenadas `member_create` y `group_update` conservan el límite
cuando un Admin limitado concede Admin a otra persona desde CKAN. También se
aplican si el flujo de solicitudes está desactivado. Los administradores
previos no se restringen; la concesión derivada se confirma con su marcador.

## Validación de esta entrega

- 20 pruebas con PostgreSQL real: aprobación atómica, concurrencia, duplicados, revocación, aislamiento y conservación de permisos existentes.
- 342 regresiones del tema y 6 de la campana de aprobaciones aprobadas.
- Navegador con solicitante y revisor: solicitud, aprobación, acceso a edición, texto escapado y vista móvil en español.
- API real: edición de la iniciativa autorizada; edición de otra iniciativa y de una hija denegada (403), también después de delegar Admin por la API nativa.
- Formularios sin token CSRF o con token inválido rechazados (400).
