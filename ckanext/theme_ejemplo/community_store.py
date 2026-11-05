# -*- coding: utf-8 -*-
"""
Almacén de documentos y protocolo de la comunidad de práctica DACS.

La aplicación React de la comunidad (``public/dacs-community``) se escribió
para Cloud Firestore. El cliente ``firebase/firestore`` fue sustituido por un
cliente compatible (``frontend/dacs-community/shims``) que llama a esta API;
aquí se guardan los mismos documentos, en la base PostgreSQL de CKAN, en una
sola tabla ``dacs_community_document`` (un JSON por documento).

Cada lectura y escritura pasa por ``community_rules.RulesEngine`` con el
archivo de reglas de la comunidad (``community_data/dacs.rules``).

Este módulo no importa CKAN: sólo SQLAlchemy. ``community.py`` conecta las
vistas Flask de CKAN; las pruebas locales usan el mismo código con SQLite.

Protocolo (JSON, siempre POST):

- ``me``: el usuario conectado.
- ``read``: ``{"targets": [{"kind": "doc", "path": ...} |
  {"kind": "query", "collection": ..., "where": [[campo, op, valor]],
  "orderBy": [[campo, "asc"|"desc"]], "limit": n}]}``.
- ``commit``: ``{"writes": [{"op": "set"|"update"|"delete", "path": ...,
  "data": {...}, "merge": bool}], "preconditions": [{"path", "version"}]}``.

Valores especiales en JSON: ``{"$ts": milisegundos}`` es una marca de tiempo;
``{"$sv": "serverTimestamp"|"arrayUnion"|"arrayRemove"|"delete"|"increment",
"v": ...}`` son los valores de servidor de Firestore.
"""
import copy
import datetime
import json
import logging
import re

from sqlalchemy import (Column, DateTime, Index, Integer, MetaData, Table,
                        UnicodeText, and_, inspect as sa_inspect)

from .community_rules import RulesError  # noqa: F401  (reexportado)

log = logging.getLogger(__name__)

TABLE_NAME = 'dacs_community_document'
MAX_DOC_BYTES = 1200 * 1024        # Firestore: 1 MiB por documento
MAX_WRITES = 500                    # Firestore: 500 escrituras por lote
MAX_TARGETS = 60
MAX_LIMIT = 1000

_metadata = MetaData()
documents = Table(
    TABLE_NAME, _metadata,
    Column('space', UnicodeText, primary_key=True),
    Column('path', UnicodeText, primary_key=True),
    Column('parent', UnicodeText, nullable=False),
    Column('doc_id', UnicodeText, nullable=False),
    Column('data', UnicodeText, nullable=False),
    Column('version', Integer, nullable=False, default=1),
    Column('created', DateTime, nullable=False),
    Column('updated', DateTime, nullable=False),
    Index('idx_dacs_community_parent', 'space', 'parent'),
)


class ApiError(Exception):
    """Error devuelto al cliente con un código de Firestore."""
    STATUS = {'permission-denied': 403, 'not-found': 404, 'invalid-argument': 400,
              'aborted': 409, 'unauthenticated': 401, 'resource-exhausted': 413,
              'failed-precondition': 400, 'internal': 500}

    def __init__(self, code, message):
        super(ApiError, self).__init__(message)
        self.code = code
        self.message = message

    @property
    def status(self):
        return self.STATUS.get(self.code, 400)

    def as_dict(self):
        return {'code': self.code, 'message': self.message}


def utcnow_ms():
    """Hora del servidor truncada a milisegundos (lo que conserva un Date de JS)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.replace(microsecond=(now.microsecond // 1000) * 1000)


# ---------------------------------------------------------------------------
# Codificación
# ---------------------------------------------------------------------------

def _ms_to_dt(ms):
    if not isinstance(ms, (int, float)) or isinstance(ms, bool):
        raise ApiError('invalid-argument', 'Marca de tiempo inválida')
    return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc) + \
        datetime.timedelta(milliseconds=int(ms))


def _dt_to_ms(dt):
    delta = dt - datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    return int(delta.days * 86400000 + delta.seconds * 1000 + delta.microseconds // 1000)


class Sentinel(object):
    """Valor de servidor (serverTimestamp, arrayUnion, ...) aún sin resolver."""
    __slots__ = ('kind', 'value')

    def __init__(self, kind, value=None):
        self.kind, self.value = kind, value


def decode(v, allow_sentinels=False):
    if isinstance(v, dict):
        if len(v) == 1 and '$ts' in v:
            return _ms_to_dt(v['$ts'])
        if '$sv' in v and set(v) <= {'$sv', 'v'}:
            if not allow_sentinels:
                raise ApiError('invalid-argument', 'Valor de servidor fuera de una escritura')
            kind = v['$sv']
            if kind not in ('serverTimestamp', 'arrayUnion', 'arrayRemove', 'delete', 'increment'):
                raise ApiError('invalid-argument', 'Valor de servidor desconocido')
            inner = v.get('v')
            if kind in ('arrayUnion', 'arrayRemove'):
                inner = [decode(x) for x in (inner or [])]
            return Sentinel(kind, inner)
        return dict((str(k), decode(x, allow_sentinels)) for k, x in v.items())
    if isinstance(v, list):
        return [decode(x) for x in v]
    return v


def encode(v):
    if isinstance(v, datetime.datetime):
        return {'$ts': _dt_to_ms(v)}
    if isinstance(v, dict):
        return dict((k, encode(x)) for k, x in v.items())
    if isinstance(v, list):
        return [encode(x) for x in v]
    return v


def _dumps(data):
    return json.dumps(encode(data), ensure_ascii=False, separators=(',', ':'), sort_keys=True)


def _loads(text):
    return decode(json.loads(text))


# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------

_SEGMENT_RE = re.compile(r'^[^/\x00-\x1f]{1,400}$')


def split_path(path, want_doc):
    if not isinstance(path, str) or len(path) > 1500:
        raise ApiError('invalid-argument', 'Ruta inválida')
    segs = path.strip('/').split('/')
    for s in segs:
        if not _SEGMENT_RE.match(s) or s in ('.', '..') or (s.startswith('__') and s.endswith('__')):
            raise ApiError('invalid-argument', 'Segmento de ruta inválido')
    if want_doc and len(segs) % 2 != 0:
        raise ApiError('invalid-argument', 'La ruta no es la de un documento')
    if not want_doc and len(segs) % 2 != 1:
        raise ApiError('invalid-argument', 'La ruta no es la de una colección')
    return segs


# ---------------------------------------------------------------------------
# Almacén
# ---------------------------------------------------------------------------

class DocumentStore(object):
    """Documentos de un espacio (una comunidad, p. ej. el grupo 'dacs')."""

    _ready_engines = set()

    def __init__(self, engine, space):
        self.engine = engine
        self.space = space
        self.ensure_table(engine)

    @classmethod
    def ensure_table(cls, engine):
        key = id(engine)
        if key in cls._ready_engines:
            return
        if TABLE_NAME not in sa_inspect(engine).get_table_names():
            documents.create(engine, checkfirst=True)
            log.info(u'Tabla %s creada', TABLE_NAME)
        cls._ready_engines.add(key)

    def _row(self, conn, path):
        row = conn.execute(documents.select().where(and_(
            documents.c.space == self.space, documents.c.path == path))).fetchone()
        return None if row is None else row._mapping

    def get(self, path, conn=None):
        """(datos, versión) o None."""
        if conn is None:
            with self.engine.connect() as c:
                return self.get(path, c)
        row = self._row(conn, path)
        if row is None:
            return None
        return _loads(row['data']), row['version']

    def children(self, parent):
        with self.engine.connect() as conn:
            rows = conn.execute(documents.select().where(and_(
                documents.c.space == self.space, documents.c.parent == parent))).fetchall()
        return [(r._mapping['path'], r._mapping['doc_id'], _loads(r._mapping['data']),
                 r._mapping['version']) for r in rows]

    def apply(self, final_states, preconditions, now):
        """Escribe el estado final de cada documento en una transacción."""
        naive_now = now.replace(tzinfo=None)
        with self.engine.begin() as conn:
            for path, version in preconditions:
                row = self._row(conn, path)
                current = 0 if row is None else row['version']
                if current != version:
                    raise ApiError('aborted', 'El documento cambió durante la transacción')
            for path, data in final_states.items():
                row = self._row(conn, path)
                if data is None:
                    if row is not None:
                        conn.execute(documents.delete().where(and_(
                            documents.c.space == self.space, documents.c.path == path)))
                    continue
                text = _dumps(data)
                if len(text.encode('utf-8')) > MAX_DOC_BYTES:
                    raise ApiError('invalid-argument', 'El documento supera el tamaño máximo')
                if row is None:
                    segs = path.split('/')
                    conn.execute(documents.insert().values(
                        space=self.space, path=path, parent='/'.join(segs[:-1]), doc_id=segs[-1],
                        data=text, version=1, created=naive_now, updated=naive_now))
                else:
                    conn.execute(documents.update().where(and_(
                        documents.c.space == self.space, documents.c.path == path)).values(
                        data=text, version=row['version'] + 1, updated=naive_now))

    def clear(self):
        with self.engine.begin() as conn:
            conn.execute(documents.delete().where(documents.c.space == self.space))


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

_MISSING = object()


def _field(data, path):
    cur = data
    for part in path.split('.'):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _type_rank(v):
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1
    if isinstance(v, (int, float)):
        return 2
    if isinstance(v, datetime.datetime):
        return 3
    if isinstance(v, str):
        return 4
    if isinstance(v, list):
        return 8
    if isinstance(v, dict):
        return 9
    return 10


def _sort_key(v):
    rank = _type_rank(v)
    if rank in (1, 2, 3, 4):
        return (rank, v)
    if rank == 8:
        return (rank, tuple(_sort_key(x) for x in v))
    if rank == 9:
        return (rank, tuple(sorted((k, _sort_key(x)) for k, x in v.items())))
    return (rank, 0)


def _veq(a, b):
    from .community_rules import _eq
    return _eq(a, b)


def _matches(data, field, op, value):
    v = _field(data, field)
    if v is _MISSING:
        return False
    if op == '==':
        return _veq(v, value)
    if op == '!=':
        return v is not None and not _veq(v, value)
    if op in ('<', '<=', '>', '>='):
        if _type_rank(v) != _type_rank(value) or _type_rank(v) not in (2, 3, 4):
            return False
        a, b = _sort_key(v), _sort_key(value)
        return {'<': a < b, '<=': a <= b, '>': a > b, '>=': a >= b}[op]
    if op == 'in':
        return isinstance(value, list) and any(_veq(v, x) for x in value)
    if op == 'not-in':
        return isinstance(value, list) and v is not None and not any(_veq(v, x) for x in value)
    if op == 'array-contains':
        return isinstance(v, list) and any(_veq(x, value) for x in v)
    if op == 'array-contains-any':
        return isinstance(v, list) and isinstance(value, list) and \
            any(_veq(x, y) for x in v for y in value)
    raise ApiError('invalid-argument', 'Operador de consulta desconocido: %s' % op)


def _probes(filters, cap=64):
    """Documentos de prueba que cumplen los filtros de igualdad de una consulta."""
    probes = [{}]
    for field, op, value in filters:
        if op == '==':
            options = [value]
        elif op == 'array-contains':
            options = [[value]]
        elif op == 'in' and isinstance(value, list) and value:
            options = list(value)
        else:
            continue
        nxt = []
        for base in probes:
            for opt in options:
                d = copy.deepcopy(base)
                cur = d
                parts = field.split('.')
                for part in parts[:-1]:
                    cur = cur.setdefault(part, {})
                cur[parts[-1]] = opt
                nxt.append(d)
        probes = nxt[:cap]
    return probes


# ---------------------------------------------------------------------------
# Escrituras
# ---------------------------------------------------------------------------

def _resolve(value, existing, now):
    """Sustituye los valores de servidor en ``value`` (escritura de un campo)."""
    if isinstance(value, Sentinel):
        if value.kind == 'serverTimestamp':
            return now
        if value.kind == 'arrayUnion':
            base = list(existing) if isinstance(existing, list) else []
            for item in value.value:
                if not any(_veq(item, x) for x in base):
                    base.append(item)
            return base
        if value.kind == 'arrayRemove':
            base = list(existing) if isinstance(existing, list) else []
            return [x for x in base if not any(_veq(x, y) for y in value.value)]
        if value.kind == 'increment':
            inc = value.value if isinstance(value.value, (int, float)) else 0
            return (existing if isinstance(existing, (int, float)) and not isinstance(existing, bool) else 0) + inc
        if value.kind == 'delete':
            return _MISSING
    if isinstance(value, dict):
        out = {}
        for k, x in value.items():
            r = _resolve(x, None, now)
            if r is not _MISSING:
                out[k] = r
        return out
    return value


def _merge(target, incoming, now):
    """``set(..., {merge: true})``: mezcla profunda de mapas."""
    out = dict(target or {})
    for k, v in incoming.items():
        if isinstance(v, Sentinel):
            r = _resolve(v, out.get(k), now)
            if r is _MISSING:
                out.pop(k, None)
            else:
                out[k] = r
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v, now)
        else:
            out[k] = _resolve(v, None, now)
    return out


def _update_fields(target, updates, now):
    """``update()``: las claves son rutas de campo con puntos."""
    out = copy.deepcopy(target)
    for field_path, v in updates.items():
        parts = field_path.split('.')
        cur = out
        for p in parts[:-1]:
            if not isinstance(cur.get(p), dict):
                cur[p] = {}
            cur = cur[p]
        last = parts[-1]
        r = _resolve(v, cur.get(last), now)
        if r is _MISSING:
            cur.pop(last, None)
        else:
            cur[last] = r
    return out


# ---------------------------------------------------------------------------
# Protocolo
# ---------------------------------------------------------------------------

class CommunityApi(object):
    """Ejecuta las acciones de la API con un almacén y un motor de reglas."""

    def __init__(self, store, rules):
        self.store = store
        self.rules = rules

    def _getter(self):
        cache = {}

        def get(path):
            if path not in cache:
                found = self.store.get(path)
                cache[path] = None if found is None else found[0]
            return cache[path]
        return get

    # -- lecturas -----------------------------------------------------------------
    def read(self, payload, auth, now, bypass=False):
        targets = payload.get('targets')
        if not isinstance(targets, list) or len(targets) > MAX_TARGETS:
            raise ApiError('invalid-argument', 'Lecturas inválidas')
        get = self._getter()
        results = []
        for t in targets:
            try:
                if not isinstance(t, dict):
                    raise ApiError('invalid-argument', 'Lectura inválida')
                if t.get('kind') == 'doc':
                    results.append(self._read_doc(t, auth, now, get, bypass))
                elif t.get('kind') == 'query':
                    results.append(self._read_query(t, auth, now, get, bypass))
                else:
                    raise ApiError('invalid-argument', 'Tipo de lectura desconocido')
            except ApiError as exc:
                results.append({'error': exc.as_dict()})
        return {'results': results}

    def _read_doc(self, t, auth, now, get, bypass):
        path = '/'.join(split_path(t.get('path'), True))
        found = self.store.get(path)
        data, version = (None, 0) if found is None else found
        if not bypass and not self.rules.allowed('get', path, auth, data, None, now, get):
            raise ApiError('permission-denied', 'Missing or insufficient permissions.')
        if data is None:
            return {'exists': False, 'path': path, 'version': 0}
        return {'exists': True, 'path': path, 'data': encode(data), 'version': version}

    def _read_query(self, t, auth, now, get, bypass):
        collection = '/'.join(split_path(t.get('collection'), False))
        wheres = t.get('where') or []
        orders = t.get('orderBy') or []
        limit = t.get('limit')
        if not isinstance(wheres, list) or not isinstance(orders, list):
            raise ApiError('invalid-argument', 'Consulta inválida')
        if limit is not None and (not isinstance(limit, int) or limit < 0 or limit > MAX_LIMIT):
            raise ApiError('invalid-argument', 'Límite inválido')
        filters = []
        for w in wheres:
            if not isinstance(w, list) or len(w) != 3 or not isinstance(w[0], str):
                raise ApiError('invalid-argument', 'Filtro inválido')
            filters.append((w[0], w[1], decode(w[2])))
        sort = []
        for o in orders:
            if not isinstance(o, list) or len(o) != 2 or o[1] not in ('asc', 'desc'):
                raise ApiError('invalid-argument', 'Orden inválido')
            sort.append((o[0], o[1] == 'desc'))
        # Como en Firestore, las reglas no filtran: una consulta que devolvería
        # un documento no legible se rechaza entera.
        rows = []
        for path, doc_id, data, version in self.store.children(collection):
            if not all(_matches(data, f, op, v) for f, op, v in filters):
                continue
            if any(_field(data, f) is _MISSING for f, _ in sort):
                continue
            rows.append((path, doc_id, data, version))
        if not bypass:
            # 1) Como el análisis estático de Firestore: la regla debe cumplirse
            #    para un documento formado sólo por los filtros de la consulta
            #    (un campo no filtrado es desconocido y no prueba nada).
            for probe in _probes(filters):
                verdict = self.rules.decide('list', collection + '/__query__', auth, probe,
                                            None, now, get)
                if verdict is not True:
                    raise ApiError('permission-denied', 'Missing or insufficient permissions.')
            # 2) Red de seguridad: cada documento devuelto debe ser legible.
            for path, doc_id, data, version in rows:
                if not self.rules.allowed('list', path, auth, data, None, now, get):
                    raise ApiError('permission-denied', 'Missing or insufficient permissions.')
        rows.sort(key=lambda r: r[1])
        for f, desc in reversed(sort):
            rows.sort(key=lambda r: _sort_key(_field(r[2], f)), reverse=desc)
        if limit is not None:
            rows = rows[:limit]
        return {'docs': [{'id': doc_id, 'path': path, 'data': encode(data), 'version': version}
                         for path, doc_id, data, version in rows]}

    # -- escrituras ---------------------------------------------------------------
    def commit(self, payload, auth, now, bypass=False):
        writes = payload.get('writes')
        if not isinstance(writes, list) or not writes or len(writes) > MAX_WRITES:
            raise ApiError('invalid-argument', 'Escrituras inválidas')
        pre = []
        for p in payload.get('preconditions') or []:
            if not isinstance(p, dict) or not isinstance(p.get('version'), int):
                raise ApiError('invalid-argument', 'Condición previa inválida')
            pre.append(('/'.join(split_path(p.get('path'), True)), p['version']))

        before, after, plan = {}, {}, []
        for w in writes:
            if not isinstance(w, dict) or w.get('op') not in ('set', 'update', 'delete'):
                raise ApiError('invalid-argument', 'Escritura inválida')
            path = '/'.join(split_path(w.get('path'), True))
            if path not in before:
                found = self.store.get(path)
                before[path] = None if found is None else found[0]
                after[path] = copy.deepcopy(before[path])
            current = after[path]
            op = w['op']
            if op == 'delete':
                new = None
            else:
                raw = w.get('data')
                if not isinstance(raw, dict):
                    raise ApiError('invalid-argument', 'Datos de escritura inválidos')
                data = decode(raw, allow_sentinels=True)
                if op == 'set':
                    new = _merge(current or {}, data, now) if w.get('merge') else _merge({}, data, now)
                else:
                    if current is None:
                        new = _update_fields({}, data, now)
                    else:
                        new = _update_fields(current, data, now)
            plan.append((op, path, current, new))
            after[path] = new

        if not bypass:
            get_before = self._getter()

            def get_after(p):
                if p in after:
                    return after[p]
                return get_before(p)

            for op, path, current, new in plan:
                existing = before[path]
                if op == 'delete':
                    method = 'delete'
                elif existing is None:
                    method = 'update' if op == 'update' else 'create'
                else:
                    method = 'update'
                if not self.rules.allowed(method, path, auth, existing, new, now,
                                          get_before, get_after):
                    raise ApiError('permission-denied', 'Missing or insufficient permissions.')
                if op == 'update' and existing is None:
                    raise ApiError('not-found', 'No document to update: %s' % path)
        else:
            for op, path, current, new in plan:
                if op == 'update' and before[path] is None:
                    raise ApiError('not-found', 'No document to update: %s' % path)
        self.store.apply(after, pre, now)
        return {'ok': True, 'time': _dt_to_ms(now)}

    # -- entrada única ---------------------------------------------------------------
    def handle(self, action, payload, auth, now=None, bypass=False):
        now = now or utcnow_ms()
        if not isinstance(payload, dict):
            raise ApiError('invalid-argument', 'Petición inválida')
        if action == 'read':
            return self.read(payload, auth, now, bypass)
        if action == 'commit':
            return self.commit(payload, auth, now, bypass)
        raise ApiError('not-found', 'Acción desconocida')
