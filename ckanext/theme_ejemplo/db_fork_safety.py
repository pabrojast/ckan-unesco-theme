# encoding: utf-8
"""Protección del pool de SQLAlchemy frente al fork de uWSGI.

uWSGI carga la app CKAN en el proceso master (``paste = config:...`` sin
``lazy-apps``) y varios plugins tocan la base de datos durante esa carga
(creación/verificación de tablas, ``system_info``...), así que al momento
del fork el pool ya tiene conexiones Postgres abiertas. Los 16 workers
heredan copias de LOS MISMOS sockets y, en cuanto dos de ellos los usan a
la vez, el protocolo se corrompe::

    psycopg2.OperationalError: lost synchronization with server:
        got message type "f", length 1698062950

El daño además se vuelve permanente por un segundo problema: CKAN 2.10 sólo
limpia la sesión en ``after_request`` (``ckan_after_request`` →
``Session.remove()``), y Flask NO ejecuta los ``after_request`` cuando el
propio error handler revienta — que es exactamente lo que pasa, porque la
página de error renderiza el header y éste consulta la DB con la misma
sesión rota. Resultado: cada worker queda con su sesión en estado
``prepared``/``PendingRollback`` para siempre y responde 500 a todo.

Dos remedios complementarios:

1. ``init_postfork()``: registra un hook ``postfork`` de uWSGI que descarta
   el pool heredado en cada worker (``engine.dispose(close=False)`` — sin
   cerrar los FDs, que siguen siendo del master y de los hermanos). Cada
   worker abre entonces sus propias conexiones. Es la receta oficial de
   SQLAlchemy para "connections and forks".
2. ``init_app(app)``: registra un ``teardown_appcontext``, que Flask ejecuta
   SIEMPRE (incluso cuando el error handler falla), y que hace
   rollback + remove de la sesión scoped. Con esto un error transitorio de
   DB cuesta un 500, no un worker envenenado.
"""
import logging

log = logging.getLogger(__name__)

_postfork_registered = False
_teardown_registered = False


def _dispose_engines():
    """Descarta los pools de conexiones heredados del master (idempotente)."""
    try:
        from ckan.model import meta
        if meta.engine is not None:
            try:
                meta.engine.dispose(close=False)
            except TypeError:  # SQLAlchemy < 1.4.33
                meta.engine.dispose()
    except Exception:
        log.exception('theme_ejemplo: no se pudo descartar el engine principal')
    # El datastore cachea sus engines (lectura/escritura) en un dict de módulo.
    try:
        from ckanext.datastore.backend import postgres as _ds_pg
        for _eng in list(getattr(_ds_pg, '_engines', {}).values()):
            try:
                _eng.dispose(close=False)
            except TypeError:
                _eng.dispose()
    except Exception:
        pass


def init_postfork():
    """Registra el hook postfork si corremos bajo uWSGI (idempotente).

    Debe invocarse durante la carga de la app EN EL MASTER (import del
    plugin), que es cuando uWSGI aún acepta registrar hooks. Fuera de uWSGI
    (CLI ``ckan``, tests, jobs worker) el import falla y no hacemos nada:
    esos procesos no forkean después de abrir conexiones.

    La imagen instala uWSGI como binario pelado, SIN el módulo
    ``uwsgidecorators`` que trae el paquete pip, así que se intenta primero
    el decorator y si no está se usa directamente ``uwsgi.post_fork_hook``
    (el módulo ``uwsgi`` es built-in del plugin python y siempre existe
    dentro de uWSGI), encadenando cualquier hook previo.
    """
    global _postfork_registered
    if _postfork_registered:
        return
    try:
        from uwsgidecorators import postfork
        postfork(_dispose_engines)
        _postfork_registered = True
        log.info('theme_ejemplo: dispose post-fork registrado (uwsgidecorators)')
        return
    except Exception:
        pass
    try:
        import uwsgi
    except Exception:
        # Proceso normal fuera de uWSGI (CLI, tests, jobs worker): no-op.
        return
    _prev_hook = getattr(uwsgi, 'post_fork_hook', None)

    def _chained_post_fork():
        if _prev_hook is not None:
            try:
                _prev_hook()
            except Exception:
                log.exception('theme_ejemplo: fallo en post_fork_hook previo')
        _dispose_engines()

    try:
        uwsgi.post_fork_hook = _chained_post_fork
    except Exception:
        log.warning('theme_ejemplo: uWSGI presente pero no se pudo registrar '
                    'post_fork_hook; los workers heredan el pool del master')
        return
    _postfork_registered = True
    log.info('theme_ejemplo: dispose post-fork registrado (uwsgi built-in)')


def _cleanup_session(exc):
    if exc is None:
        return
    try:
        from ckan import model
        try:
            model.Session.rollback()
        except Exception:
            pass
        model.Session.remove()
    except Exception:
        # Nunca propagar desde un teardown: sólo perderíamos el error real.
        log.exception('theme_ejemplo: fallo saneando la sesión de SQLAlchemy')


def init_app(app):
    """Registra el saneador de sesión como ``teardown_appcontext``."""
    global _teardown_registered
    if _teardown_registered:
        return
    if not hasattr(app, 'teardown_appcontext'):
        # No es la Flask app (wrapper WSGI legacy).
        return
    app.teardown_appcontext(_cleanup_session)
    _teardown_registered = True
    log.info('theme_ejemplo: saneador de sesión DB registrado')
