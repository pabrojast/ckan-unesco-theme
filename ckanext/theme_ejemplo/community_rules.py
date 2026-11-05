# -*- coding: utf-8 -*-
"""
Intérprete de reglas de seguridad con la sintaxis de Cloud Firestore.

La comunidad de práctica DACS (ver ``community.py``) se escribió para Firebase:
todos sus permisos están en un archivo ``firestore.rules`` de unas 770 líneas.
En lugar de reescribir esa lógica en Python, este módulo ejecuta el mismo
archivo de reglas sobre cada lectura y escritura, de modo que los permisos y
las validaciones de campos siguen siendo exactamente los que definió su autor.

Cubre el subconjunto del lenguaje que usa ese archivo:

- ``match`` anidados con variables de ruta y comodín recursivo ``{x=**}``;
- ``allow read|write|get|list|create|update|delete: if <expr>;``;
- ``function f(a, b) { let x = ...; return ...; }`` con ``let`` perezosos;
- operadores ``&& || ! == != < <= > >= in is + - ?:``, índices y métodos de
  cadenas, listas, mapas, conjuntos y ``MapDiff``;
- ``get``, ``exists``, ``getAfter``, ``existsAfter``, ``int``, ``float``,
  ``duration.value`` y las rutas ``/databases/$(database)/documents/...``.

Semántica de errores como en Firestore: un error en una expresión deniega,
salvo que ``||`` o ``&&`` puedan decidir con el otro operando.
"""
import datetime
import re

__all__ = ['RulesEngine', 'RulesError', 'RulesSyntaxError', 'Resource']


class RulesSyntaxError(Exception):
    """El archivo de reglas no se puede leer."""


class RulesError(Exception):
    """Error de evaluación: equivale a un error en Firestore (deniega)."""


# ---------------------------------------------------------------------------
# Léxico
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r"""
    (?P<ws>\s+)
  | (?P<comment>//[^\n]*)
  | (?P<bcomment>/\*.*?\*/)
  | (?P<num>\d+\.\d+|\d+)
  | (?P<str>'(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")
  | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>==|!=|<=|>=|&&|\|\||\*\*|[{}()\[\],;.:?!=<>+\-*/%$])
""", re.S | re.X)

_ESCAPES = {'n': '\n', 't': '\t', 'r': '\r', '\\': '\\', "'": "'", '"': '"',
            '0': '\0', '/': '/'}


def _unescape(body):
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch == '\\' and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt == 'u' and i + 5 < len(body):
                out.append(chr(int(body[i + 2:i + 6], 16)))
                i += 6
                continue
            if nxt in _ESCAPES:
                out.append(_ESCAPES[nxt])
            else:
                # Secuencia desconocida (p. ej. \s): se conserva para las regex.
                out.append('\\' + nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


def _tokenize(text):
    tokens, pos = [], 0
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m:
            line = text.count('\n', 0, pos) + 1
            raise RulesSyntaxError('Carácter inesperado en la línea %d: %r' % (line, text[pos]))
        kind = m.lastgroup
        value = m.group(kind)
        pos = m.end()
        if kind in ('ws', 'comment', 'bcomment'):
            continue
        if kind == 'num':
            value = float(value) if '.' in value else int(value)
        elif kind == 'str':
            value = _unescape(value[1:-1])
        tokens.append((kind, value))
    tokens.append(('eof', None))
    return tokens


# ---------------------------------------------------------------------------
# Estructura del archivo de reglas
# ---------------------------------------------------------------------------

class _Function(object):
    __slots__ = ('name', 'params', 'lets', 'body', 'node')

    def __init__(self, name, params, lets, body, node):
        self.name, self.params, self.lets, self.body, self.node = name, params, lets, body, node


class _Match(object):
    """Un bloque ``match``: patrón de ruta, funciones, ``allow`` y hijos."""

    def __init__(self, parent, pattern):
        self.parent = parent
        self.pattern = pattern  # lista de ('lit', s) | ('var', n) | ('rec', n)
        self.functions = {}
        self.allows = []        # lista de (set(métodos), expr | None)
        self.children = []

    def lookup(self, name):
        node = self
        while node is not None:
            fn = node.functions.get(name)
            if fn is not None:
                return fn
            node = node.parent
        return None


_METHOD_GROUPS = {
    'read': ('get', 'list'),
    'write': ('create', 'update', 'delete'),
    'get': ('get',), 'list': ('list',),
    'create': ('create',), 'update': ('update',), 'delete': ('delete',),
}


class _Parser(object):
    def __init__(self, text):
        self.toks = _tokenize(text)
        self.i = 0

    # -- utilidades -------------------------------------------------------
    def peek(self, k=0):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self):
        tok = self.toks[self.i]
        self.i += 1
        return tok

    def at(self, value, k=0):
        kind, v = self.peek(k)
        return kind in ('op', 'id') and v == value

    def expect(self, value):
        kind, v = self.next()
        if v != value or kind not in ('op', 'id'):
            raise RulesSyntaxError('Se esperaba %r y se encontró %r' % (value, v))

    def ident(self):
        kind, v = self.next()
        if kind != 'id':
            raise RulesSyntaxError('Se esperaba un identificador y se encontró %r' % (v,))
        return v

    # -- archivo ------------------------------------------------------------
    def parse(self):
        root = _Match(None, [])
        while self.peek()[0] != 'eof':
            if self.at('rules_version'):
                while not self.at(';'):
                    self.next()
                self.next()
            elif self.at('service'):
                self.next()
                while not self.at('{'):
                    self.next()
                self.next()
                self.block(root)
                self.expect('}')
            elif self.at('function'):
                self.function(root)
            else:
                raise RulesSyntaxError('Instrucción inesperada: %r' % (self.peek()[1],))
        return root

    def block(self, node):
        while not self.at('}'):
            if self.at('match'):
                self.next()
                child = _Match(node, self.pattern())
                self.expect('{')
                self.block(child)
                self.expect('}')
                node.children.append(child)
            elif self.at('allow'):
                self.next()
                methods = set()
                while True:
                    name = self.ident()
                    if name not in _METHOD_GROUPS:
                        raise RulesSyntaxError('Método desconocido en allow: %r' % name)
                    methods.update(_METHOD_GROUPS[name])
                    if self.at(','):
                        self.next()
                        continue
                    break
                cond = None
                if self.at(':'):
                    self.next()
                    self.expect('if')
                    cond = self.expr()
                self.expect(';')
                node.allows.append((methods, cond))
            elif self.at('function'):
                self.function(node)
            else:
                raise RulesSyntaxError('Instrucción inesperada en match: %r' % (self.peek()[1],))

    def pattern(self):
        segs = []
        while self.at('/'):
            self.next()
            if self.at('{'):
                self.next()
                name = self.ident()
                if self.at('='):
                    self.next()
                    self.expect('**')
                    segs.append(('rec', name))
                else:
                    segs.append(('var', name))
                self.expect('}')
            else:
                kind, v = self.next()
                if kind not in ('id', 'num'):
                    raise RulesSyntaxError('Segmento de ruta inválido: %r' % (v,))
                segs.append(('lit', str(v)))
        if not segs:
            raise RulesSyntaxError('Ruta de match vacía')
        return segs

    def function(self, node):
        self.expect('function')
        name = self.ident()
        self.expect('(')
        params = []
        while not self.at(')'):
            params.append(self.ident())
            if self.at(','):
                self.next()
        self.expect(')')
        self.expect('{')
        lets = []
        while self.at('let'):
            self.next()
            var = self.ident()
            self.expect('=')
            lets.append((var, self.expr()))
            self.expect(';')
        self.expect('return')
        body = self.expr()
        if self.at(';'):
            self.next()
        self.expect('}')
        node.functions[name] = _Function(name, params, lets, body, node)

    # -- expresiones ----------------------------------------------------------
    def expr(self):
        cond = self.or_expr()
        if self.at('?'):
            self.next()
            a = self.expr()
            self.expect(':')
            b = self.expr()
            return ('tern', cond, a, b)
        return cond

    def or_expr(self):
        left = self.and_expr()
        while self.at('||'):
            self.next()
            left = ('or', left, self.and_expr())
        return left

    def and_expr(self):
        left = self.rel_expr()
        while self.at('&&'):
            self.next()
            left = ('and', left, self.rel_expr())
        return left

    _REL = ('==', '!=', '<', '<=', '>', '>=')

    def rel_expr(self):
        left = self.add_expr()
        while True:
            kind, v = self.peek()
            if kind == 'op' and v in self._REL:
                self.next()
                left = ('bin', v, left, self.add_expr())
            elif kind == 'id' and v == 'in':
                self.next()
                left = ('in', left, self.add_expr())
            elif kind == 'id' and v == 'is':
                self.next()
                left = ('is', left, self.ident())
            else:
                return left

    def add_expr(self):
        left = self.mul_expr()
        while self.peek()[0] == 'op' and self.peek()[1] in ('+', '-'):
            op = self.next()[1]
            left = ('bin', op, left, self.mul_expr())
        return left

    def mul_expr(self):
        left = self.unary()
        while self.peek()[0] == 'op' and self.peek()[1] in ('*', '/', '%'):
            op = self.next()[1]
            left = ('bin', op, left, self.unary())
        return left

    def unary(self):
        if self.at('!'):
            self.next()
            return ('not', self.unary())
        if self.at('-'):
            self.next()
            return ('neg', self.unary())
        return self.postfix(self.primary())

    def postfix(self, node):
        while True:
            if self.at('.'):
                self.next()
                name = self.ident()
                if self.at('('):
                    node = ('method', node, name, self.args())
                else:
                    node = ('attr', node, name)
            elif self.at('['):
                self.next()
                idx = self.expr()
                self.expect(']')
                node = ('index', node, idx)
            else:
                return node

    def args(self):
        self.expect('(')
        out = []
        while not self.at(')'):
            out.append(self.expr())
            if self.at(','):
                self.next()
        self.expect(')')
        return out

    def primary(self):
        kind, v = self.peek()
        if kind == 'num' or kind == 'str':
            self.next()
            return ('lit', v)
        if kind == 'id':
            self.next()
            if v == 'true':
                return ('lit', True)
            if v == 'false':
                return ('lit', False)
            if v == 'null':
                return ('lit', None)
            if self.at('('):
                return ('call', v, self.args())
            return ('id', v)
        if kind == 'op' and v == '(':
            self.next()
            e = self.expr()
            self.expect(')')
            return e
        if kind == 'op' and v == '[':
            self.next()
            items = []
            while not self.at(']'):
                items.append(self.expr())
                if self.at(','):
                    self.next()
            self.expect(']')
            return ('list', items)
        if kind == 'op' and v == '{':
            self.next()
            pairs = []
            while not self.at('}'):
                key = self.expr()
                self.expect(':')
                pairs.append((key, self.expr()))
                if self.at(','):
                    self.next()
            self.expect('}')
            return ('map', pairs)
        if kind == 'op' and v == '/':
            return self.path_literal()
        raise RulesSyntaxError('Expresión inesperada: %r' % (v,))

    def path_literal(self):
        parts = []
        while self.at('/'):
            self.next()
            if self.at('$'):
                self.next()
                self.expect('(')
                parts.append(('expr', self.expr()))
                self.expect(')')
            else:
                kind, v = self.next()
                if kind not in ('id', 'num'):
                    raise RulesSyntaxError('Segmento de ruta inválido: %r' % (v,))
                parts.append(('lit', str(v)))
        return ('path', parts)


# ---------------------------------------------------------------------------
# Valores
# ---------------------------------------------------------------------------

class RPath(str):
    """Una ruta de documento (``/databases/(default)/documents/...``)."""


class Resource(object):
    """Un documento tal como lo ven las reglas: ``resource.data``, ``resource.id``."""
    __slots__ = ('data', 'path')

    def __init__(self, data, path):
        self.data = data
        self.path = path

    @property
    def id(self):
        return self.path.rsplit('/', 1)[-1]


class _Auth(object):
    __slots__ = ('uid', 'token')

    def __init__(self, uid, token):
        self.uid = uid
        self.token = token


class _Request(object):
    __slots__ = ('auth', 'time', 'resource', 'method', 'path')

    def __init__(self, auth, time, resource, method, path):
        self.auth, self.time, self.resource, self.method, self.path = auth, time, resource, method, path


def _freeze(v):
    if isinstance(v, bool):
        return ('B', v)
    if isinstance(v, (int, float)):
        return ('N', float(v))
    if isinstance(v, str):
        return ('S', str(v))
    if v is None:
        return ('Z',)
    if isinstance(v, list):
        return ('L', tuple(_freeze(x) for x in v))
    if isinstance(v, dict):
        return ('M', tuple(sorted((k, _freeze(x)) for k, x in v.items())))
    if isinstance(v, RSet):
        return ('X', frozenset(v._items))
    if isinstance(v, datetime.datetime):
        return ('T', v)
    if isinstance(v, datetime.timedelta):
        return ('D', v)
    raise RulesError('Valor no apto para un conjunto')


class RSet(object):
    """Conjunto de las reglas (``list.toSet()``)."""
    __slots__ = ('_items',)

    def __init__(self, values=()):
        self._items = {}
        for v in values:
            self._items.setdefault(_freeze(v), v)

    def values(self):
        return list(self._items.values())

    def __contains__(self, v):
        return _freeze(v) in self._items

    def __len__(self):
        return len(self._items)


class _MapDiff(object):
    __slots__ = ('new', 'old')

    def __init__(self, new, old):
        self.new, self.old = new, old

    def added(self):
        return RSet(k for k in self.new if k not in self.old)

    def removed(self):
        return RSet(k for k in self.old if k not in self.new)

    def changed(self):
        return RSet(k for k in self.new if k in self.old and not _eq(self.new[k], self.old[k]))

    def unchanged(self):
        return RSet(k for k in self.new if k in self.old and _eq(self.new[k], self.old[k]))

    def affected(self):
        return RSet(self.added().values() + self.removed().values() + self.changed().values())


class _Namespace(object):
    __slots__ = ('name',)

    def __init__(self, name):
        self.name = name


_DURATION_UNITS = {
    'w': datetime.timedelta(weeks=1), 'd': datetime.timedelta(days=1),
    'h': datetime.timedelta(hours=1), 'm': datetime.timedelta(minutes=1),
    's': datetime.timedelta(seconds=1), 'ms': datetime.timedelta(milliseconds=1),
    'us': datetime.timedelta(microseconds=1), 'ns': datetime.timedelta(microseconds=0.001),
}


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _eq(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b
    if _is_num(a) and _is_num(b):
        return a == b
    if isinstance(a, str) and isinstance(b, str):
        return str(a) == str(b)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return set(a) == set(b) and all(_eq(a[k], b[k]) for k in a)
    if isinstance(a, RSet) and isinstance(b, RSet):
        return set(a._items) == set(b._items)
    if isinstance(a, datetime.datetime) and isinstance(b, datetime.datetime):
        return a == b
    if isinstance(a, datetime.timedelta) and isinstance(b, datetime.timedelta):
        return a == b
    if isinstance(a, Resource) and isinstance(b, Resource):
        return a.path == b.path and _eq(a.data, b.data)
    return False


def _cmp(a, b):
    if _is_num(a) and _is_num(b):
        pass
    elif isinstance(a, str) and isinstance(b, str):
        pass
    elif isinstance(a, datetime.datetime) and isinstance(b, datetime.datetime):
        pass
    elif isinstance(a, datetime.timedelta) and isinstance(b, datetime.timedelta):
        pass
    else:
        raise RulesError('Comparación entre tipos incompatibles')
    return (a > b) - (a < b)


_TYPE_CHECKS = {
    'string': lambda v: isinstance(v, str) and not isinstance(v, RPath),
    'int': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'float': lambda v: isinstance(v, float),
    'number': _is_num,
    'bool': lambda v: isinstance(v, bool),
    'list': lambda v: isinstance(v, list),
    'map': lambda v: isinstance(v, dict),
    'timestamp': lambda v: isinstance(v, datetime.datetime),
    'duration': lambda v: isinstance(v, datetime.timedelta),
    'path': lambda v: isinstance(v, RPath),
    'set': lambda v: isinstance(v, RSet),
    'null': lambda v: v is None,
    'bytes': lambda v: False,
    'latlng': lambda v: False,
}


def _bool(v):
    if not isinstance(v, bool):
        raise RulesError('Se esperaba un booleano')
    return v


def _members(v):
    """Elementos de una lista o conjunto, para hasAll/hasOnly/hasAny."""
    if isinstance(v, list):
        return v
    if isinstance(v, RSet):
        return v.values()
    raise RulesError('Se esperaba una lista o un conjunto')


def _contains(container, v):
    if isinstance(container, list):
        return any(_eq(x, v) for x in container)
    if isinstance(container, RSet):
        try:
            return v in container
        except RulesError:
            return False
    if isinstance(container, dict):
        if not isinstance(v, str):
            raise RulesError('Las claves de un mapa son cadenas')
        return v in container
    raise RulesError("'in' requiere una lista, un conjunto o un mapa")


_DOC_PREFIX = 'databases/(default)/documents/'


def _doc_path(p):
    p = str(p).lstrip('/')
    if p.startswith(_DOC_PREFIX):
        return p[len(_DOC_PREFIX):]
    raise RulesError('Ruta de documento fuera de la base de datos')


# ---------------------------------------------------------------------------
# Evaluación
# ---------------------------------------------------------------------------

class _Thunk(object):
    __slots__ = ('expr', 'env', 'done', 'value', 'error')

    def __init__(self, expr, env):
        self.expr, self.env, self.done, self.value, self.error = expr, env, False, None, None

    def force(self, ev):
        if not self.done:
            try:
                self.value = ev.eval(self.expr, self.env)
            except RulesError as exc:
                self.error = exc
            self.done = True
        if self.error is not None:
            raise self.error
        return self.value


class _Env(object):
    __slots__ = ('vars', 'node')

    def __init__(self, vars_, node):
        self.vars, self.node = vars_, node


class _Evaluator(object):
    MAX_DEPTH = 40
    MAX_LOOKUPS = 20  # Firestore permite 10 get() por petición simple; aquí margen.

    def __init__(self, request, get_doc, get_after):
        self.request = request
        self.resource = None
        self._get = get_doc
        self._get_after = get_after
        self.depth = 0

    # -- documentos ---------------------------------------------------------
    def fetch(self, path, after=False):
        doc_path = _doc_path(path)
        data = (self._get_after if after else self._get)(doc_path)
        return None if data is None else Resource(data, doc_path)

    # -- nodos ----------------------------------------------------------------
    def eval(self, node, env):
        t = node[0]
        if t == 'lit':
            return node[1]
        if t == 'id':
            return self.ident(node[1], env)
        if t == 'and':
            return self.logical(node, env, False)
        if t == 'or':
            return self.logical(node, env, True)
        if t == 'not':
            return not _bool(self.eval(node[1], env))
        if t == 'neg':
            v = self.eval(node[1], env)
            if not _is_num(v):
                raise RulesError('Negación de un valor no numérico')
            return -v
        if t == 'tern':
            return self.eval(node[2] if _bool(self.eval(node[1], env)) else node[3], env)
        if t == 'bin':
            return self.binary(node[1], self.eval(node[2], env), self.eval(node[3], env))
        if t == 'in':
            return _contains(self.eval(node[2], env), self.eval(node[1], env))
        if t == 'is':
            check = _TYPE_CHECKS.get(node[2])
            if check is None:
                raise RulesError('Tipo desconocido: %s' % node[2])
            return check(self.eval(node[1], env))
        if t == 'attr':
            return self.attr(self.eval(node[1], env), node[2])
        if t == 'index':
            return self.index(self.eval(node[1], env), self.eval(node[2], env))
        if t == 'method':
            target = self.eval(node[1], env)
            return self.method(target, node[2], [self.eval(a, env) for a in node[3]])
        if t == 'call':
            return self.call(node[1], node[2], env)
        if t == 'list':
            return [self.eval(x, env) for x in node[1]]
        if t == 'map':
            out = {}
            for k, v in node[1]:
                key = self.eval(k, env)
                if not isinstance(key, str):
                    raise RulesError('Clave de mapa no textual')
                out[key] = self.eval(v, env)
            return out
        if t == 'path':
            segs = []
            for kind, part in node[1]:
                if kind == 'lit':
                    segs.append(part)
                else:
                    v = self.eval(part, env)
                    if isinstance(v, bool) or v is None or isinstance(v, (list, dict)):
                        raise RulesError('Segmento de ruta inválido')
                    segs.append(str(v).strip('/'))
            return RPath('/'.join(segs))
        raise RulesError('Nodo desconocido: %s' % t)

    def logical(self, node, env, is_or):
        decisive = is_or  # True decide un ||, False decide un &&
        first_error = None
        for operand in (node[1], node[2]):
            try:
                v = _bool(self.eval(operand, env))
            except RulesError as exc:
                if first_error is None:
                    first_error = exc
                continue
            if v is decisive:
                return decisive
        if first_error is not None:
            raise first_error
        return not decisive

    def ident(self, name, env):
        if name in env.vars:
            v = env.vars[name]
            return v.force(self) if isinstance(v, _Thunk) else v
        if name == 'request':
            return self.request
        if name == 'resource':
            return self.resource
        if name in ('duration', 'timestamp', 'math'):
            return _Namespace(name)
        raise RulesError('Variable desconocida: %s' % name)

    def call(self, name, arg_nodes, env):
        fn = env.node.lookup(name) if env.node is not None else None
        if fn is not None:
            if len(arg_nodes) != len(fn.params):
                raise RulesError('Número de argumentos incorrecto para %s' % name)
            if self.depth >= self.MAX_DEPTH:
                raise RulesError('Recursión demasiado profunda')
            # Argumentos perezosos, como en Firestore: manages(resource.data.wg)
            # es verdadero para admin() aunque el campo no se conozca.
            args = [_Thunk(a, env) for a in arg_nodes]
            local = dict(self._path_vars)
            local.update(zip(fn.params, args))
            fenv = _Env(local, fn.node)
            for var, expr in fn.lets:
                local[var] = _Thunk(expr, fenv)
            self.depth += 1
            try:
                return self.eval(fn.body, fenv)
            finally:
                self.depth -= 1
        args = [self.eval(a, env) for a in arg_nodes]
        if name in ('get', 'getAfter'):
            self.count_lookup()
            return self.fetch(self.path_arg(args), after=(name == 'getAfter'))
        if name in ('exists', 'existsAfter'):
            self.count_lookup()
            return self.fetch(self.path_arg(args), after=(name == 'existsAfter')) is not None
        if name == 'int':
            return self.to_int(args)
        if name == 'float':
            try:
                return float(args[0])
            except (TypeError, ValueError, IndexError):
                raise RulesError('float() inválido')
        if name == 'string':
            if len(args) != 1:
                raise RulesError('string() espera un argumento')
            v = args[0]
            if isinstance(v, bool):
                return 'true' if v else 'false'
            if v is None:
                return 'null'
            return str(v)
        if name == 'path':
            return RPath(str(args[0]).lstrip('/'))
        if name == 'debug':
            return args[0] if args else None
        raise RulesError('Función desconocida: %s' % name)

    def count_lookup(self):
        self.lookups = getattr(self, 'lookups', 0) + 1
        if self.lookups > 200:
            raise RulesError('Demasiadas lecturas de documentos en las reglas')

    @staticmethod
    def path_arg(args):
        if len(args) != 1 or not isinstance(args[0], RPath):
            raise RulesError('Se esperaba una ruta')
        return args[0]

    @staticmethod
    def to_int(args):
        if len(args) != 1:
            raise RulesError('int() espera un argumento')
        v = args[0]
        if isinstance(v, bool):
            raise RulesError('int() de un booleano')
        try:
            return int(v)
        except (TypeError, ValueError):
            raise RulesError('int() inválido')

    def attr(self, obj, name):
        if isinstance(obj, dict):
            if name not in obj:
                raise RulesError('Campo inexistente: %s' % name)
            return obj[name]
        if isinstance(obj, Resource):
            if name == 'data':
                return obj.data
            if name == 'id':
                return obj.id
            if name == '__name__':
                return RPath(_DOC_PREFIX + obj.path)
            raise RulesError('Atributo de recurso desconocido: %s' % name)
        if isinstance(obj, _Request):
            if name in ('auth', 'time', 'resource', 'method', 'path'):
                return getattr(obj, name)
            raise RulesError('Atributo de request desconocido: %s' % name)
        if isinstance(obj, _Auth):
            if name == 'uid':
                return obj.uid
            if name == 'token':
                return obj.token
            raise RulesError('Atributo de auth desconocido: %s' % name)
        if isinstance(obj, _Namespace):
            return (obj.name, name)
        if obj is None:
            raise RulesError('Acceso a %s de null' % name)
        raise RulesError('Acceso a atributo no permitido: %s' % name)

    def index(self, obj, idx):
        if isinstance(obj, list):
            if not isinstance(idx, int) or isinstance(idx, bool):
                raise RulesError('Índice de lista no entero')
            if idx < 0 or idx >= len(obj):
                raise RulesError('Índice fuera de rango')
            return obj[idx]
        if isinstance(obj, dict):
            if not isinstance(idx, str) or idx not in obj:
                raise RulesError('Clave inexistente')
            return obj[idx]
        if isinstance(obj, Resource) and idx == 'data':
            return obj.data
        raise RulesError('Índice no permitido')

    # -- operadores -------------------------------------------------------------
    def binary(self, op, a, b):
        if op == '==':
            return _eq(a, b)
        if op == '!=':
            return not _eq(a, b)
        if op in ('<', '<=', '>', '>='):
            c = _cmp(a, b)
            return {'<': c < 0, '<=': c <= 0, '>': c > 0, '>=': c >= 0}[op]
        if op == '+':
            if _is_num(a) and _is_num(b):
                return a + b
            if isinstance(a, str) and isinstance(b, str) and not isinstance(a, RPath):
                return a + b
            if isinstance(a, list) and isinstance(b, list):
                return a + b
            if isinstance(a, datetime.datetime) and isinstance(b, datetime.timedelta):
                return a + b
            if isinstance(a, datetime.timedelta) and isinstance(b, datetime.timedelta):
                return a + b
            raise RulesError('Suma entre tipos incompatibles')
        if op == '-':
            if _is_num(a) and _is_num(b):
                return a - b
            if isinstance(a, datetime.datetime) and isinstance(b, datetime.datetime):
                return a - b
            if isinstance(a, datetime.datetime) and isinstance(b, datetime.timedelta):
                return a - b
            if isinstance(a, datetime.timedelta) and isinstance(b, datetime.timedelta):
                return a - b
            raise RulesError('Resta entre tipos incompatibles')
        if op in ('*', '/', '%'):
            if not (_is_num(a) and _is_num(b)):
                raise RulesError('Operación aritmética no numérica')
            if op == '*':
                return a * b
            if b == 0:
                raise RulesError('División por cero')
            if op == '/':
                return a // b if isinstance(a, int) and isinstance(b, int) else a / b
            return a % b
        raise RulesError('Operador desconocido: %s' % op)

    # -- métodos ----------------------------------------------------------------
    def method(self, target, name, args):
        if isinstance(target, _Namespace):  # duration.value(...)
            return self.namespace_call((target.name, name), args)
        if isinstance(target, tuple) and len(target) == 2:
            return self.namespace_call(target, args)
        if isinstance(target, RPath):
            raise RulesError('Método de ruta no soportado: %s' % name)
        if isinstance(target, str):
            return self.string_method(target, name, args)
        if isinstance(target, list):
            return self.list_method(target, name, args)
        if isinstance(target, RSet):
            return self.set_method(target, name, args)
        if isinstance(target, dict):
            return self.map_method(target, name, args)
        if isinstance(target, _MapDiff):
            fn = {'affectedKeys': target.affected, 'addedKeys': target.added,
                  'removedKeys': target.removed, 'changedKeys': target.changed,
                  'unchangedKeys': target.unchanged}.get(name)
            if fn is None or args:
                raise RulesError('Método de MapDiff desconocido: %s' % name)
            return fn()
        if isinstance(target, datetime.datetime):
            if name == 'toMillis':
                return int(target.timestamp() * 1000)
            if name == 'year':
                return target.year
            raise RulesError('Método de timestamp no soportado: %s' % name)
        if isinstance(target, datetime.timedelta):
            if name == 'seconds':
                return int(target.total_seconds())
            raise RulesError('Método de duración no soportado: %s' % name)
        raise RulesError('Método %s sobre un valor no soportado' % name)

    @staticmethod
    def namespace_call(target, args):
        ns, name = target
        if ns == 'duration' and name == 'value':
            if len(args) != 2 or not _is_num(args[0]) or args[1] not in _DURATION_UNITS:
                raise RulesError('duration.value inválido')
            return _DURATION_UNITS[args[1]] * args[0]
        if ns == 'duration' and name == 'time':
            h, m, s, ns_ = (list(args) + [0, 0, 0, 0])[:4]
            return datetime.timedelta(hours=h, minutes=m, seconds=s, microseconds=ns_ / 1000.0)
        if ns == 'math' and name == 'abs':
            return abs(args[0])
        raise RulesError('Función %s.%s no soportada' % (ns, name))

    @staticmethod
    def string_method(s, name, args):
        if name == 'size' and not args:
            return len(s)
        if name == 'matches' and len(args) == 1 and isinstance(args[0], str):
            try:
                return re.fullmatch(args[0], s, re.S) is not None
            except re.error:
                raise RulesError('Expresión regular inválida')
        if name == 'lower' and not args:
            return s.lower()
        if name == 'upper' and not args:
            return s.upper()
        if name == 'trim' and not args:
            return s.strip()
        if name == 'split' and len(args) == 1 and isinstance(args[0], str):
            try:
                return re.split(args[0], s)
            except re.error:
                raise RulesError('Expresión regular inválida')
        if name == 'replace' and len(args) == 2:
            try:
                return re.sub(args[0], args[1], s)
            except re.error:
                raise RulesError('Expresión regular inválida')
        raise RulesError('Método de cadena no soportado: %s' % name)

    @staticmethod
    def list_method(lst, name, args):
        if name == 'size' and not args:
            return len(lst)
        if name == 'hasAll' and len(args) == 1:
            return all(_contains(lst, x) for x in _members(args[0]))
        if name == 'hasAny' and len(args) == 1:
            return any(_contains(lst, x) for x in _members(args[0]))
        if name == 'hasOnly' and len(args) == 1:
            allowed = _members(args[0])
            return all(any(_eq(x, y) for y in allowed) for x in lst)
        if name == 'toSet' and not args:
            return RSet(lst)
        if name == 'join' and len(args) == 1 and isinstance(args[0], str):
            if not all(isinstance(x, str) for x in lst):
                raise RulesError('join() sobre elementos no textuales')
            return args[0].join(lst)
        if name == 'concat' and len(args) == 1 and isinstance(args[0], list):
            return lst + args[0]
        if name == 'removeAll' and len(args) == 1:
            drop = _members(args[0])
            return [x for x in lst if not any(_eq(x, y) for y in drop)]
        raise RulesError('Método de lista no soportado: %s' % name)

    @staticmethod
    def set_method(st, name, args):
        if name == 'size' and not args:
            return len(st)
        if name == 'hasAll' and len(args) == 1:
            return all(_contains(st, x) for x in _members(args[0]))
        if name == 'hasAny' and len(args) == 1:
            return any(_contains(st, x) for x in _members(args[0]))
        if name == 'hasOnly' and len(args) == 1:
            allowed = _members(args[0])
            return all(any(_eq(x, y) for y in allowed) for x in st.values())
        if name in ('difference', 'union', 'intersection') and len(args) == 1:
            other = RSet(_members(args[0]))
            if name == 'difference':
                return RSet(v for v in st.values() if v not in other)
            if name == 'union':
                return RSet(st.values() + other.values())
            return RSet(v for v in st.values() if v in other)
        raise RulesError('Método de conjunto no soportado: %s' % name)

    @staticmethod
    def map_method(mp, name, args):
        if name == 'size' and not args:
            return len(mp)
        if name == 'keys' and not args:
            return list(mp.keys())
        if name == 'values' and not args:
            return list(mp.values())
        if name == 'get' and len(args) == 2:
            key = args[0]
            if isinstance(key, list):
                cur = mp
                for k in key:
                    if not isinstance(cur, dict) or k not in cur:
                        return args[1]
                    cur = cur[k]
                return cur
            if not isinstance(key, str):
                raise RulesError('Clave de mapa no textual')
            return mp.get(key, args[1])
        if name == 'diff' and len(args) == 1:
            other = args[0]
            if not isinstance(other, dict):
                raise RulesError('diff() requiere un mapa')
            return _MapDiff(mp, other)
        raise RulesError('Método de mapa no soportado: %s' % name)


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------

def _match_path(node, segments):
    """Devuelve [(nodo, variables)] para cada bloque que aplica a la ruta."""
    found = []

    def walk(current, segs, bound):
        for child in current.children:
            pat = child.pattern
            vars_ = dict(bound)
            i = 0
            ok = True
            rec = False
            for kind, val in pat:
                if kind == 'rec':
                    if i > len(segs):
                        ok = False
                        break
                    vars_[val] = RPath('/'.join(segs[i:]))
                    i = len(segs)
                    rec = True
                    break
                if i >= len(segs):
                    ok = False
                    break
                if kind == 'lit':
                    if segs[i] != val:
                        ok = False
                        break
                else:
                    vars_[val] = segs[i]
                i += 1
            if not ok:
                continue
            if i == len(segs):
                found.append((child, vars_))
            elif not rec:
                walk(child, segs[i:], vars_)

    walk(node, segments, {})
    return found


class RulesEngine(object):
    """Evalúa un archivo de reglas con la sintaxis de Firestore.

    ``allowed(method, path, auth, resource_data, request_data, now, get_doc,
    get_after)`` devuelve True si alguna regla ``allow`` aplicable permite la
    operación. ``path`` es la ruta del documento sin prefijo
    (p. ej. ``events/abc/agenda/1``); ``auth`` es None o
    ``{'uid': ..., 'token': {...}}``.
    """

    def __init__(self, text):
        self.root = _Parser(text).parse()

    def allowed(self, method, path, auth, resource_data, request_data, now,
                get_doc, get_after=None):
        return self.decide(method, path, auth, resource_data, request_data, now,
                           get_doc, get_after) is True

    def decide(self, method, path, auth, resource_data, request_data, now,
               get_doc, get_after=None):
        """True si alguna regla permite; False si todas niegan; None si alguna
        condición dio error sin que otra permitiera (resultado indeterminado,
        p. ej. al evaluar una consulta vacía con datos incompletos)."""
        if method not in ('get', 'list', 'create', 'update', 'delete'):
            raise ValueError(method)
        segments = (_DOC_PREFIX + path).split('/')
        matches = _match_path(self.root, segments)
        if not matches:
            return False
        auth_obj = None
        if auth is not None:
            auth_obj = _Auth(auth.get('uid'), dict(auth.get('token') or {}))
        req_resource = None
        if request_data is not None:
            req_resource = Resource(request_data, path)
        request = _Request(auth_obj, now, req_resource, method, RPath(_DOC_PREFIX + path))
        ev = _Evaluator(request, get_doc, get_after or get_doc)
        ev.resource = None if resource_data is None else Resource(resource_data, path)
        errored = False
        for node, path_vars in matches:
            ev._path_vars = path_vars
            env = _Env(dict(path_vars), node)
            for methods, cond in node.allows:
                if method not in methods:
                    continue
                if cond is None:
                    return True
                try:
                    if ev.eval(cond, env) is True:
                        return True
                except RulesError:
                    errored = True
        return None if errored else False
