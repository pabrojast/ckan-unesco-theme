# =============================================================================
# Páginas de iniciativa: cuestionario completo y plantilla común con identidad
# de color propia para cada iniciativa.
# Added by Jorgen Van Der Biest (UNESCO-IHP, IHP-WINS), October 2026.
#
# - /initiatives/request ofrece dos opciones: la solicitud estándar (el
#   formulario de siempre) o la página completa (cuestionario de 7 pasos en
#   /initiatives/request/full). La página completa crea la solicitud con la
#   vista de siempre (MyLogica.request_initiative) y guarda las respuestas en la
#   tabla propia initiative_page.
# - Al aprobar la solicitud, el grupo creado (initiative_request.created_group_id)
#   muestra la plantilla común: la del grupo AI for Water Management,
#   generalizada (mismas clases .aiw, ai-water.css), con el contenido del
#   cuestionario y los colores sacados de las imágenes (variables CSS).
# - Una iniciativa estándar puede pasar a página completa más tarde desde
#   /group/<name>/page-setup (administradores del grupo y sysadmins).
# - Estados miembros e iniciativas siguen separados: los grupos de Estados
#   miembros nunca usan esta plantilla.
#
# En los ficheros existentes solo se añaden líneas marcadas con
# "Initiative pages (added by Jorgen Van Der Biest)". Ver
# docs/obsidian-vault/Initiative pages.md.
# =============================================================================
import datetime
import json
import logging
import math
import random
import re
import uuid

import ckan.model as model
import ckan.plugins.toolkit as toolkit
from ckan.common import current_user, request
from flask import g
from sqlalchemy import Column, DateTime, MetaData, Table, UnicodeText, select, text
from sqlalchemy import inspect as sa_inspect

from ckanext.theme_ejemplo import ihpix_constants
from ckanext.theme_ejemplo.utils import get_invalid_user_image_upload_reason

log = logging.getLogger(__name__)

_ = toolkit._

# --------------------------------------------------------------------------
# Listas del cuestionario
# --------------------------------------------------------------------------
INITIATIVE_TYPES = [
    ('flagship', 'IHP flagship initiative'),
    ('project', 'Project'),
    ('task-force', 'Task force or working group'),
    ('network', 'Network or community of practice'),
    ('programme', 'Programme, platform or portal'),
    ('other', 'Other'),
]
STATUSES = [('planned', 'Planned'), ('active', 'Active'), ('completed', 'Completed')]
SCOPES = [
    ('global', 'Global'),
    ('regional', 'Regional'),
    ('transboundary', 'Transboundary basin'),
    ('national', 'National'),
    ('local', 'Local'),
]
HERO_LAYOUTS = [
    ('illustration', 'Illustration beside title'),
    ('photo', 'Photo beside title'),
    ('title', 'Title only'),
]
SDGS = [
    'No poverty', 'Zero hunger', 'Good health and well-being', 'Quality education',
    'Gender equality', 'Clean water and sanitation', 'Affordable and clean energy',
    'Decent work and economic growth', 'Industry, innovation and infrastructure',
    'Reduced inequalities', 'Sustainable cities and communities',
    'Responsible consumption and production', 'Climate action', 'Life below water',
    'Life on land', 'Peace, justice and strong institutions', 'Partnerships for the goals',
]
# Secciones de la portada que se pueden ocultar (las vacías no se muestran nunca)
SECTIONS = [
    ('figures', 'Key figures'),
    ('why', 'Why it matters'),
    ('toc', 'Theory of change'),
    ('objectives', 'Objectives'),
    ('latest', 'News, events, datasets and data stories'),
    ('documents', 'Documents'),
    ('cta', 'Closing call to action'),
]
IMAGE_SLOTS = ('hero', 'band', 'support')

MAX_OBJECTIVES = 8
MAX_FIGURES = 8
MAX_CONTACTS = 6
MAX_FEATURED = 6
MAX_IMAGE_MB = 5

# Semillas por defecto (azul del logo de IHP-WINS) si no hay imágenes con color
DEFAULT_SEEDS = {'primary': '#37B7E7', 'accent': '#F56F36', 'soft': '#A6E2EF'}
HEX = re.compile(r'^#[0-9A-Fa-f]{6}$')
EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


# --------------------------------------------------------------------------
# Tabla initiative_page (una fila por iniciativa con página completa)
# --------------------------------------------------------------------------
_metadata = MetaData()
initiative_page_table = Table(
    'initiative_page', _metadata,
    Column('id', UnicodeText, primary_key=True),
    Column('request_id', UnicodeText, index=True),   # initiative_request.id
    Column('group_id', UnicodeText, index=True),     # group.id (al aprobar o desde page-setup)
    Column('details', UnicodeText),                  # respuestas del cuestionario (JSON)
    Column('palette', UnicodeText),                  # semillas y roles de color (JSON)
    Column('created', DateTime),
    Column('updated', DateTime),
    Column('updated_by', UnicodeText),
)
_db_ready = False


def init_db():
    """Crea la tabla initiative_page si no existe."""
    global _db_ready
    if _db_ready:
        return
    inspector = sa_inspect(model.meta.engine)
    if 'initiative_page' not in inspector.get_table_names():
        initiative_page_table.create(model.meta.engine)
        log.info('initiative_page table created')
    _db_ready = True


def _row_to_page(row):
    if row is None:
        return None
    m = row._mapping if hasattr(row, '_mapping') else row
    try:
        details = json.loads(m['details'] or '{}')
    except ValueError:
        details = {}
    try:
        palette = json.loads(m['palette'] or '{}')
    except ValueError:
        palette = {}
    return {
        'id': m['id'], 'request_id': m['request_id'], 'group_id': m['group_id'],
        'details': normalize_details(details), 'palette': palette,
        'updated': m['updated'],
    }


def _table_exists(name):
    try:
        return name in sa_inspect(model.meta.engine).get_table_names()
    except Exception:
        return False


def get_page_by_request(request_id):
    init_db()
    t = initiative_page_table
    row = model.Session.execute(select(t).where(t.c.request_id == request_id)).first()
    return _row_to_page(row)


def get_page_by_group(group_id):
    """Página completa del grupo, o None. Busca por group_id y, si la página
    viene de una solicitud aprobada, por initiative_request.created_group_id."""
    if not group_id:
        return None
    init_db()
    t = initiative_page_table
    row = model.Session.execute(select(t).where(t.c.group_id == group_id)).first()
    if row is None and _table_exists('initiative_request'):
        row = model.Session.execute(text(
            "SELECT p.* FROM initiative_page p "
            "JOIN initiative_request r ON r.id = p.request_id "
            "WHERE r.created_group_id = :gid AND r.status = 'approved' "
            "ORDER BY p.updated DESC LIMIT 1"
        ), {'gid': group_id}).first()
    return _row_to_page(row)


def save_page(details, palette, request_id=None, group_id=None, page_id=None):
    """Crea o actualiza la fila de la página. Devuelve su id."""
    init_db()
    t = initiative_page_table
    now = datetime.datetime.utcnow()
    user = getattr(current_user, 'name', None)
    values = {
        'details': json.dumps(details, ensure_ascii=False),
        'palette': json.dumps(palette, ensure_ascii=False),
        'updated': now, 'updated_by': user,
    }
    if group_id:
        values['group_id'] = group_id
    if page_id:
        model.Session.execute(t.update().where(t.c.id == page_id).values(**values))
    else:
        page_id = str(uuid.uuid4())
        model.Session.execute(t.insert().values(
            id=page_id, request_id=request_id, created=now, **values))
    model.Session.commit()
    _cache_clear()
    return page_id


# Caché por petición (varias plantillas preguntan por el mismo grupo)
def _cache():
    try:
        if not hasattr(g, '_ini_pages'):
            g._ini_pages = {}
        return g._ini_pages
    except RuntimeError:  # sin contexto de petición (CLI, tests)
        return {}


def _cache_clear():
    try:
        g._ini_pages = {}
    except RuntimeError:
        pass


# --------------------------------------------------------------------------
# Iniciativas frente a Estados miembros
# --------------------------------------------------------------------------
def _member_state_names():
    names = {'member-states'}
    try:
        names.update(n for n, _t in (toolkit.h.get_member_states_groups_list() or []))
    except Exception as e:
        log.warning(f'initiative: member states list unavailable: {e}')
    return names


def is_initiative(group_dict):
    """True para grupos de iniciativa (no organizaciones ni Estados miembros)."""
    if not group_dict or group_dict.get('is_organization'):
        return False
    if (group_dict.get('type') or 'group') != 'group':
        return False
    return group_dict.get('name') not in _member_state_names()


def page_for_group(group_dict):
    """Página completa del grupo (dict) o None. Usada por ai_water.group_landing."""
    if not group_dict or not group_dict.get('id'):
        return None
    cache = _cache()
    gid = group_dict['id']
    if gid not in cache:
        page = None
        try:
            if is_initiative(group_dict):
                page = get_page_by_group(gid)
        except Exception as e:
            log.warning(f'initiative: page lookup failed for {group_dict.get("name")}: {e}')
            model.Session.rollback()
        cache[gid] = page
    return cache[gid]


def is_tailored(group_dict):
    """Iniciativas con diseño propio en código (GROUP_LANDINGS de ai_water.py,
    como AI for Water): no usan la plantilla común ni el cuestionario."""
    from ckanext.theme_ejemplo.ai_water import GROUP_LANDINGS
    return (group_dict or {}).get('name') in GROUP_LANDINGS


def can_setup(group_dict):
    """El usuario puede crear o editar la página completa de este grupo."""
    if not current_user or not getattr(current_user, 'is_authenticated', False):
        return False
    if not is_initiative(group_dict) or is_tailored(group_dict):
        return False
    try:
        toolkit.check_access('group_update', {'user': current_user.name}, {'id': group_dict['id']})
        return True
    except toolkit.NotAuthorized:
        return False


# Configuración de la plantilla común para ai_water.group_landing (mismo
# formato que GROUP_LANDINGS). Las URLs del grupo son las de siempre.
GENERIC_LANDING = {
    'overview': 'initiative/landing.html',
    'header': 'initiative/snippets/header.html',
    'credit': 'initiative/snippets/credit.html',
    'intros': {
        'theme_ejemplo.group_members': 'initiative/partners_body.html',
        'group.read': 'initiative/hub_datasets_intro.html',
        'theme_ejemplo.group_data_stories': 'initiative/hub_stories_intro.html',
        'theme_ejemplo.group_publications': 'initiative/hub_documents_intro.html',
        'group.about': 'initiative/about_intro.html',
    },
    'replace': {
        # Vista News & events de AI for Water: no tiene texto propio de AI for Water
        'theme_ejemplo.group_news': 'ai_water_portal/news_events.html',
    },
}


def landing_conf(group_dict):
    """Configuración de la plantilla común si el grupo tiene página completa."""
    page = page_for_group(group_dict)
    if not page:
        return None
    conf = dict(GENERIC_LANDING)
    conf['initiative'] = True
    conf['root_class'] = 'ini'
    conf['root_style'] = palette_style(page.get('palette'))
    return conf


# --------------------------------------------------------------------------
# Colores: roles a partir de tres semillas (mismas reglas que
# public/js/initiative-form.js)
# --------------------------------------------------------------------------
def _to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(c):
    return 255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def _rgb(hx):
    hx = (hx or '#000000').lstrip('#')
    return tuple(int(hx[i:i + 2], 16) for i in (0, 2, 4))


def _lch(hx):
    r, gg, b = (_to_lin(v) for v in _rgb(hx))
    l = (0.4122214708 * r + 0.5363325363 * gg + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * gg + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * gg + 0.6299787005 * b) ** (1 / 3)
    L = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s
    a = 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s
    bb = 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _hex(L, C, h):
    lin = (0.0, 0.0, 0.0)
    for _i in range(60):
        a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
        l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
        m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
        s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
        lin = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
               -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
               -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
        if all(-1e-4 <= v <= 1.0001 for v in lin):
            break
        C *= 0.95
    return '#' + ''.join('%02X' % max(0, min(255, round(_to_srgb(max(0.0, min(1.0, v)))))) for v in lin)


def _lum(hx):
    r, gg, b = (_to_lin(v) for v in _rgb(hx))
    return 0.2126 * r + 0.7152 * gg + 0.0722 * b


def contrast(x, y):
    a, b = _lum(x), _lum(y)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _fit(C, h, L, against, target, direction):
    hx = _hex(L, C, h)
    while contrast(hx, against) < target and 0.05 < L < 0.98:
        L += 0.005 * direction
        hx = _hex(L, C, h)
    return hx


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def derive_roles(primary, accent, soft):
    """Roles de color de la plantilla a partir de tres semillas (hex).
    Cada rol se oscurece o aclara hasta cumplir su contraste WCAG."""
    P, A, S, W = _lch(primary), _lch(accent), _lch(soft), '#FFFFFF'
    Cp, Ca = _clamp(P[1], 0.07, 0.15), _clamp(A[1], 0.11, 0.19)
    r = {}
    r['primary'] = _fit(Cp, P[2], 0.44, W, 7.0, -1)
    r['ink'] = _fit(0.035, P[2], 0.30, W, 12.0, -1)
    r['muted'] = _fit(0.025, P[2], 0.48, W, 7.0, -1)
    r['soft'] = _hex(_clamp(S[0], 0.84, 0.92), min(S[1], 0.09), S[2])
    r['softer'] = _hex(0.95, min(S[1], 0.03), S[2])
    r['tint'] = _hex(0.975, 0.012, S[2])
    r['line'] = _hex(0.90, 0.025, S[2])
    r['line_soft'] = _hex(0.93, 0.018, S[2])
    r['on_primary_soft'] = _hex(0.92, 0.03, P[2])
    r['primary_deep'] = _hex(max(0.2, _lch(r['primary'])[0] - 0.07), Cp, P[2])
    r['mid'] = _hex(0.58, Cp, P[2])
    r['highlight'] = _fit(min(0.10, Cp), S[2], 0.86, r['primary'], 4.5, +1)
    r['accent'] = _fit(Ca, A[2], 0.70, W, 3.0, -1)
    r['accent_ink'] = _fit(Ca, A[2], 0.55, r['tint'], 4.5, -1)
    return r


def contrast_checks(r):
    W = '#FFFFFF'
    rows = [
        ('White text on the main colour', contrast(W, r['primary']), 7.0),
        ('Body text on white', contrast(r['ink'], W), 7.0),
        ('Eyebrows and links on tinted sections', contrast(r['accent_ink'], r['tint']), 4.5),
        ('Highlighted title on the main colour', contrast(r['highlight'], r['primary']), 4.5),
        ('Key figures on the light band', contrast(r['primary'], r['soft']), 4.5),
        ('Accent lines against white', contrast(r['accent'], W), 3.0),
    ]
    return [{'label': lab, 'value': round(v, 1), 'target': t, 'ok': v >= t} for lab, v, t in rows]


def build_palette(seeds, auto=True):
    seeds = {k: (seeds.get(k) if HEX.match(seeds.get(k) or '') else DEFAULT_SEEDS[k]).upper()
             for k in ('primary', 'accent', 'soft')}
    roles = derive_roles(seeds['primary'], seeds['accent'], seeds['soft'])
    return {'seeds': seeds, 'roles': roles, 'auto': bool(auto), 'version': 1}


# Variables de ai-water.css que la plantilla común redefine en .aiw.ini
_AIW_VARS = [
    ('--aiw-blue', 'primary'), ('--aiw-blue-deep', 'primary_deep'), ('--aiw-mid', 'mid'),
    ('--aiw-cyan', 'soft'), ('--aiw-cyan-title', 'highlight'), ('--aiw-cyan-wash', 'tint'),
    ('--aiw-cyan-soft', 'softer'), ('--aiw-orange', 'accent'), ('--aiw-orange-text', 'accent_ink'),
    ('--aiw-ink', 'ink'), ('--aiw-body', 'muted'), ('--aiw-line', 'line'),
    ('--aiw-line-soft', 'line_soft'), ('--ini-on-primary', 'on_primary_soft'),
]


def palette_style(palette):
    """Atributo style del contenedor .aiw.ini con los colores de la iniciativa."""
    roles = (palette or {}).get('roles')
    if not roles or not all(HEX.match(roles.get(k) or '') for _v, k in _AIW_VARS):
        roles = build_palette(DEFAULT_SEEDS)['roles']
    return '; '.join('%s: %s' % (var, roles[key]) for var, key in _AIW_VARS)


def extract_seeds(upload):
    """Semillas de color de una imagen subida (solo si Pillow está instalado;
    normalmente las calcula el navegador y llegan con el formulario)."""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        stream = getattr(upload, 'stream', upload)
        pos = stream.tell()
        im = Image.open(stream).convert('RGB')
        im.thumbnail((96, 96))
        px = list(im.getdata())
        stream.seek(pos)
    except Exception as e:
        log.info(f'initiative: could not read image colours: {e}')
        return None
    rnd = random.Random(7)
    rnd.shuffle(px)
    pts = [_lab(*p) for p in px[:2000]]
    clusters = _kmeans(pts, 8)
    col = [c for c in clusters if c['C'] >= 0.035 and 0.15 < c['L'] < 0.95]
    if not col:
        return None
    sal = lambda c: c['share'] ** 0.6 * min(c['C'], 0.18)
    primary = max(col, key=sal)
    # El acento: un color vivo (ni muy oscuro ni casi gris) con otro tono
    far = [c for c in col if _hue_dist(c['h'], primary['h']) >= 60 and c['C'] >= 0.05 and 0.35 <= c['L'] <= 0.9]
    accent = max(far, key=lambda c: sal(c) * (0.5 + _hue_dist(c['h'], primary['h']) / 180)) if far else None
    light = [c for c in clusters if c['L'] >= 0.75 and c['C'] >= 0.03]
    soft = max(light, key=lambda c: c['share']) if light else primary
    return {
        'primary': _hex(primary['L'], primary['C'], primary['h']),
        'accent': _hex(accent['L'], accent['C'], accent['h']) if accent else _hex(0.7, 0.14, fallback_accent_hue(primary['h'])),
        'soft': _hex(soft['L'], soft['C'], soft['h']),
    }


def fallback_accent_hue(primary_hue):
    """Tono del acento si las imágenes no tienen un segundo color: naranja
    (como AI for Water) para principales fríos, azul agua para el resto."""
    return 45.0 if 150 <= primary_hue <= 330 else 235.0


def _lab(r, gg, b):
    r, gg, b = _to_lin(r), _to_lin(gg), _to_lin(b)
    l = (0.4122214708 * r + 0.5363325363 * gg + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * gg + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * gg + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _hue_dist(a, b):
    d = abs(a - b) % 360
    return min(d, 360 - d)


def _kmeans(pts, k, iters=12):
    rnd = random.Random(11)
    centers = [pts[rnd.randrange(len(pts))] for _i in range(k)]
    groups = []
    for _it in range(iters):
        groups = [[] for _c in centers]
        for p in pts:
            j = min(range(len(centers)), key=lambda j: sum((p[i] - centers[j][i]) ** 2 for i in range(3)))
            groups[j].append(p)
        centers = [tuple(sum(p[i] for p in gr) / len(gr) for i in range(3)) if gr else centers[j]
                   for j, gr in enumerate(groups)]
    out = []
    for c, gr in zip(centers, groups):
        if gr:
            out.append({'L': c[0], 'C': math.hypot(c[1], c[2]),
                        'h': math.degrees(math.atan2(c[2], c[1])) % 360, 'share': len(gr) / len(pts)})
    return out


# --------------------------------------------------------------------------
# Listas para los selectores (organizaciones, Estados miembros, outputs)
# --------------------------------------------------------------------------
def organizations():
    """[(name, title)] de las organizaciones activas de IHP-WINS."""
    try:
        rows = (model.Session.query(model.Group.name, model.Group.title)
                .filter(model.Group.is_organization.is_(True), model.Group.state == 'active')
                .order_by(model.Group.title).all())
        return [(r.name, r.title or r.name) for r in rows]
    except Exception as e:
        log.warning(f'initiative: organization list unavailable: {e}')
        model.Session.rollback()
        return []


def member_states():
    """[(name, title)] de los grupos de Estados miembros."""
    try:
        return list(toolkit.h.get_member_states_groups_list() or [])
    except Exception as e:
        log.warning(f'initiative: member states unavailable: {e}')
        return []


def outputs_by_area():
    """[(pa, título del área, [(code, título del output)])] del OIP de IHP-IX."""
    titles = ihpix_constants.load_output_titles()
    return [(pa, ihpix_constants.PRIORITY_AREAS.get(pa, pa),
             [(code, titles.get(code, '')) for code, _t in pairs])
            for pa, pairs in ihpix_constants.OUTPUTS.items()]


def _output_codes():
    return {code for _pa, _n, items in outputs_by_area() for code, _t in items}


def group_datasets(group_name, rows=500):
    """[(name, title)] de los datasets del grupo, para elegir los destacados."""
    try:
        res = toolkit.get_action('package_search')(
            {'ignore_auth': True},
            {'fq': f'groups:"{group_name}" -type:documents -type:learning',
             'rows': rows, 'sort': 'title_string asc', 'fl': 'name,title'})
        return [(p['name'], p.get('title') or p['name']) for p in res.get('results', [])]
    except Exception as e:
        log.warning(f'initiative: datasets of {group_name} unavailable: {e}')
        return []


def form_lists(group_name=None):
    return {
        'types': INITIATIVE_TYPES, 'statuses': STATUSES, 'scopes': SCOPES,
        'layouts': HERO_LAYOUTS, 'sections': SECTIONS,
        'sdgs': list(enumerate(SDGS, start=1)),
        'organizations': organizations(), 'member_states': member_states(),
        'outputs': outputs_by_area(),
        'datasets': group_datasets(group_name) if group_name else [],
        'limits': {'objectives': MAX_OBJECTIVES, 'figures': MAX_FIGURES,
                   'contacts': MAX_CONTACTS, 'featured': MAX_FEATURED, 'image_mb': MAX_IMAGE_MB},
    }


# --------------------------------------------------------------------------
# Respuestas del cuestionario
# --------------------------------------------------------------------------
def empty_details():
    return normalize_details({})


def normalize_details(d):
    """Completa las respuestas con valores por defecto (formato versión 1)."""
    d = dict(d or {})
    out = {
        'version': 1,
        'short_name': d.get('short_name') or '',
        'title_line1': d.get('title_line1') or '', 'title_line2': d.get('title_line2') or '',
        'tagline': d.get('tagline') or '',
        'type': d.get('type') or '', 'status': d.get('status') or '',
        'start_year': d.get('start_year') or '', 'end_year': d.get('end_year') or '',
        'lead_org': d.get('lead_org') or '',
        'why_title': d.get('why_title') or '', 'why_text': d.get('why_text') or '',
        'toc': dict({'if': '', 'then': '', 'so_that': ''}, **(d.get('toc') or {})),
        'objectives_heading': d.get('objectives_heading') or '',
        'objectives_intro': d.get('objectives_intro') or '',
        'objectives': [dict({'title': '', 'text': '', 'tag': '', 'items': [], 'image': ''}, **o)
                       for o in (d.get('objectives') or [])][:MAX_OBJECTIVES],
        'figures': [dict({'value': '', 'label': ''}, **f) for f in (d.get('figures') or [])][:MAX_FIGURES],
        'scope': d.get('scope') or '',
        'member_states': list(d.get('member_states') or []),
        'outputs': list(d.get('outputs') or []),
        'sdgs': [int(x) for x in (d.get('sdgs') or []) if str(x).isdigit()],
        'themes': list(d.get('themes') or []),
        'contacts': [dict({'name': '', 'role': '', 'email': '', 'public': True}, **c)
                     for c in (d.get('contacts') or [])][:MAX_CONTACTS],
        'partners': list(d.get('partners') or []),
        'images': {slot: dict({'url': '', 'credit': '', 'alt': ''}, **((d.get('images') or {}).get(slot) or {}))
                   for slot in IMAGE_SLOTS},
        'hero_layout': d.get('hero_layout') or 'illustration',
        'content_skipped': bool(d.get('content_skipped')),
        'eyebrow': d.get('eyebrow') or '',
        'cta': dict({'label': '', 'url': ''}, **(d.get('cta') or {})),
        'cta2': dict({'label': '', 'url': ''}, **(d.get('cta2') or {})),
        'cta_heading': d.get('cta_heading') or '', 'cta_text': d.get('cta_text') or '',
        'sections': list(d['sections']) if isinstance(d.get('sections'), list) else [k for k, _l in SECTIONS],
        'featured_datasets': list(d.get('featured_datasets') or [])[:MAX_FEATURED],
        'links': list(d.get('links') or []),
        'image_rights': bool(d.get('image_rights')),
    }
    return out


def _txt(form, key, maxlen=600):
    return (form.get(key) or '').strip()[:maxlen]


def _rows(form, prefix, fields, with_index=False):
    """Filas de un bloque repetible: campos <prefix>-<i>-<campo>, en orden.
    Con with_index devuelve [(i, fila)] (i es el número usado en el formulario)."""
    rx = re.compile(r'^%s-(\d+)-(%s)$' % (re.escape(prefix), '|'.join(fields)))
    rows = {}
    for key in form.keys():
        m = rx.match(key)
        if m:
            rows.setdefault(int(m.group(1)), {})[m.group(2)] = (form.get(key) or '').strip()
    if with_index:
        return [(i, rows[i]) for i in sorted(rows)]
    return [rows[i] for i in sorted(rows)]


def _safe_local_url(url):
    """Solo rutas locales para imágenes ya subidas (evita URLs externas)."""
    url = (url or '').strip()
    return url if url.startswith('/') and not url.startswith('//') and '..' not in url else ''


def _safe_link(url):
    url = (url or '').strip()
    return url if re.match(r'^(https?://|/)', url) and not url.startswith('//') else ''


def parse_form(form, files, mode='request'):
    """Lee el cuestionario. Devuelve (details, palette, uploads, errors).

    uploads: [(ruta, FileStorage)] para guardar tras validar; ruta es
    ('images', slot) o ('objectives', índice).
    errors: {etiqueta: [mensajes]} con nombres de campo legibles.
    """
    errors = {}
    uploads = []

    def err(label, msg):
        errors.setdefault(label, []).append(msg)

    org_names = {n for n, _t in organizations()}
    ms_names = {n for n, _t in member_states()}
    codes = _output_codes()

    d = {
        'short_name': _txt(form, 'ini_short_name', 24),
        'title_line1': _txt(form, 'ini_title_line1', 60),
        'title_line2': _txt(form, 'ini_title_line2', 60),
        'tagline': _txt(form, 'ini_tagline', 200),
        'type': _txt(form, 'ini_type', 30),
        'status': _txt(form, 'ini_status', 20),
        'start_year': _txt(form, 'ini_start_year', 4),
        'end_year': _txt(form, 'ini_end_year', 4),
        'lead_org': _txt(form, 'ini_lead_org', 120),
        'why_title': _txt(form, 'ini_why_title', 80),
        'why_text': _txt(form, 'ini_why_text', 1200),
        'toc': {'if': _txt(form, 'ini_toc_if', 300), 'then': _txt(form, 'ini_toc_then', 300),
                'so_that': _txt(form, 'ini_toc_so_that', 300)},
        'objectives_heading': _txt(form, 'ini_objectives_heading', 80),
        'objectives_intro': _txt(form, 'ini_objectives_intro', 400),
        'scope': _txt(form, 'ini_scope', 20),
        'member_states': [n for n in form.getlist('ini_member_states') if n in ms_names],
        'outputs': [c for c in form.getlist('ini_outputs') if c in codes],
        'sdgs': sorted({int(x) for x in form.getlist('ini_sdgs') if x.isdigit() and 1 <= int(x) <= 17}),
        'themes': [t.strip()[:60] for t in _txt(form, 'ini_themes', 400).split(',') if t.strip()][:12],
        'partners': [n for n in dict.fromkeys(form.getlist('ini_partners')) if n in org_names],
        'hero_layout': _txt(form, 'ini_hero_layout', 20) or 'illustration',
        'content_skipped': form.get('ini_skip_content') == '1',
        'image_rights': form.get('ini_image_rights') == '1',
    }
    if d['type'] not in dict(INITIATIVE_TYPES):
        d['type'] = ''
    if d['status'] not in dict(STATUSES):
        d['status'] = ''
    if d['scope'] not in dict(SCOPES):
        d['scope'] = ''
    if d['hero_layout'] not in dict(HERO_LAYOUTS):
        d['hero_layout'] = 'illustration'
    for key in ('start_year', 'end_year'):
        if d[key] and not re.match(r'^(19|20)\d\d$', d[key]):
            err(_('Start and end year'), _('Use a four-digit year.'))
            d[key] = ''
    if d['lead_org'] and d['lead_org'] not in org_names:
        err(_('Lead organisation'), _('Choose an organisation from the list.'))
        d['lead_org'] = ''

    # Objetivos (1 a 8)
    objectives = []
    for i, row in _rows(form, 'ini_obj', ['title', 'text', 'tag', 'items', 'image_url'], with_index=True):
        if not any(row.get(k) for k in ('title', 'text', 'tag', 'items')):
            continue
        obj = {
            'title': row.get('title', '')[:60], 'text': row.get('text', '')[:300],
            'tag': row.get('tag', '')[:30],
            'items': [x.strip()[:120] for x in row.get('items', '').splitlines() if x.strip()][:6],
            'image': _safe_local_url(row.get('image_url')),
        }
        objectives.append((i, obj))
    d['objectives'] = []
    for pos, (i, obj) in enumerate(objectives[:MAX_OBJECTIVES]):
        # Imagen del objetivo: fichero ini_obj-<i>-image (mismo número de fila)
        f = files.get(f'ini_obj-{i}-image')
        if f is not None and getattr(f, 'filename', ''):
            reason = get_invalid_user_image_upload_reason(f)
            if reason:
                err(_('Objective images'), _('Objective %(n)s: the file is not a valid image (%(r)s).') % {'n': pos + 1, 'r': reason})
            else:
                uploads.append((('objectives', pos), f))
        if not obj['title']:
            err(_('Objectives'), _('Objective %(n)s needs a title.') % {'n': pos + 1})
        d['objectives'].append(obj)
    if len(objectives) > MAX_OBJECTIVES:
        err(_('Objectives'), _('Up to %(n)s objectives.') % {'n': MAX_OBJECTIVES})
    if not d['objectives']:
        err(_('Objectives'), _('Add at least one objective.'))

    # Cifras clave (hasta 8)
    d['figures'] = [{'value': r.get('value', '')[:16], 'label': r.get('label', '')[:80]}
                    for r in _rows(form, 'ini_fig', ['value', 'label'])
                    if r.get('value') or r.get('label')][:MAX_FIGURES]

    # Personas de contacto (al menos una)
    d['contacts'] = []
    for r in _rows(form, 'ini_contact', ['name', 'role', 'email', 'public']):
        if not any(r.get(k) for k in ('name', 'role', 'email')):
            continue
        c = {'name': r.get('name', '')[:80], 'role': r.get('role', '')[:100],
             'email': r.get('email', '')[:120], 'public': r.get('public') == '1'}
        if not c['name'] or not EMAIL.match(c['email']):
            err(_('Contact people'), _('Each contact needs a name and a valid email address.'))
        d['contacts'].append(c)
    d['contacts'] = d['contacts'][:MAX_CONTACTS]
    if not d['contacts']:
        err(_('Contact people'), _('Add at least one contact person.'))

    # Imágenes
    d['images'] = {}
    for slot in IMAGE_SLOTS:
        img = {'url': _safe_local_url(form.get(f'ini_{slot}_image_url')),
               'credit': _txt(form, f'ini_{slot}_credit', 160),
               'alt': _txt(form, f'ini_{slot}_alt', 200)}
        f = files.get(f'ini_{slot}_image')
        if f is not None and getattr(f, 'filename', ''):
            reason = get_invalid_user_image_upload_reason(f)
            if reason:
                err(_('Images'), _('%(slot)s image: the file is not a valid image (%(r)s).') % {'slot': slot.capitalize(), 'r': reason})
            else:
                uploads.append((('images', slot), f))
                img['url'] = img['url'] or 'pending'
        d['images'][slot] = img
    hero = d['images']['hero']
    if not hero['url']:
        err(_('Hero image'), _('Upload a hero image.'))
    if not hero['credit'] or not hero['alt']:
        err(_('Hero image'), _('Give the hero image a credit and a short description (alt text).'))
    if not d['image_rights']:
        err(_('Images'), _('Confirm that you have the right to publish the images.'))

    # Paso 6 (opcional)
    if not d['content_skipped']:
        d['eyebrow'] = _txt(form, 'ini_eyebrow', 80)
        d['cta'] = {'label': _txt(form, 'ini_cta_label', 40), 'url': _safe_link(form.get('ini_cta_url'))}
        d['cta2'] = {'label': _txt(form, 'ini_cta2_label', 40), 'url': _safe_link(form.get('ini_cta2_url'))}
        d['cta_heading'] = _txt(form, 'ini_cta_heading', 100)
        d['cta_text'] = _txt(form, 'ini_cta_text', 400)
        d['sections'] = [s for s in form.getlist('ini_sections') if s in dict(SECTIONS)]
        d['featured_datasets'] = list(dict.fromkeys(n for n in form.getlist('ini_featured_datasets') if n))[:MAX_FEATURED]
        d['links'] = [u for u in (_safe_link(x) for x in _txt(form, 'ini_links', 2000).splitlines()) if u][:8]
    else:
        d['sections'] = [k for k, _l in SECTIONS]

    # Obligatorios
    for key, label in (('tagline', _('Tagline')), ('type', _('Type of initiative')),
                       ('lead_org', _('Lead organisation')), ('scope', _('Geographic scope'))):
        if not d[key] and label not in errors:
            err(label, _('This field is required.'))

    # Colores: semillas del navegador; si faltan, de la imagen principal (Pillow) o por defecto
    seeds = {k: _txt(form, f'ini_seed_{k}', 7) for k in ('primary', 'accent', 'soft')}
    auto = form.get('ini_seed_auto', '1') == '1'
    if not all(HEX.match(v) for v in seeds.values()):
        hero_file = next((f for (kind, slot), f in uploads if kind == 'images' and slot == 'hero'), None)
        seeds = (extract_seeds(hero_file) if hero_file is not None else None) or {}
        auto = True
    palette = build_palette(seeds, auto=auto)

    return normalize_details(d), palette, uploads, errors


def store_image(upload):
    """Guarda una imagen del cuestionario y devuelve su URL local. Usa el tipo
    de subida 'group' de CKAN (el de las imágenes de grupo: tipos de imagen
    permitidos por defecto, servido en /uploads/group/), sin configuración nueva."""
    import ckan.lib.helpers as h_core
    import ckan.lib.uploader as uploader
    up = uploader.get_uploader('group')
    up.update_data_dict({'upload': upload, 'url': '', 'clear_upload': ''}, 'url', 'upload', 'clear_upload')
    up.upload(max_size=MAX_IMAGE_MB)
    return h_core.url_for_static('uploads/group/{}'.format(up.filename), qualified=False)


def apply_uploads(details, uploads):
    for (kind, key), f in uploads:
        url = store_image(f)
        if kind == 'images':
            details['images'][key]['url'] = url
        elif kind == 'objectives' and key < len(details['objectives']):
            details['objectives'][key]['image'] = url
    return details


# --------------------------------------------------------------------------
# Datos para la plantilla común
# --------------------------------------------------------------------------
def _org_dicts(names):
    if not names:
        return {}
    rows = (model.Session.query(model.Group)
            .filter(model.Group.name.in_(list(names)), model.Group.state == 'active').all())
    out = {}
    for grp in rows:
        image = grp.image_url or ''
        if image and not image.startswith(('http', '/')):
            image = '/uploads/group/' + image
        out[grp.name] = {'name': grp.name, 'title': grp.title or grp.name, 'image': image,
                         'description': grp.description or '',
                         'url': toolkit.url_for('organization.read', id=grp.name)}
    return out


def _search(fq, rows, sort='metadata_modified desc'):
    try:
        return toolkit.get_action('package_search')({'ignore_auth': True}, {'fq': fq, 'rows': rows, 'sort': sort})
    except Exception as e:
        log.warning(f'initiative: package_search failed ({fq}): {e}')
        return {'count': 0, 'results': []}


def most_viewed_names(group_id, limit=MAX_FEATURED):
    """Nombres de los datasets del grupo con más visitas (tracking_dataset_stats)."""
    if not _table_exists('tracking_dataset_stats'):
        return []
    try:
        rows = model.Session.execute(text(
            "SELECT p.name FROM tracking_dataset_stats s "
            "JOIN package p ON p.name = s.dataset_name AND p.state = 'active' AND p.private = false "
            "JOIN member m ON m.table_id = p.id AND m.table_name = 'package' "
            "  AND m.state = 'active' AND m.group_id = :gid "
            "WHERE s.total_views > 0 AND coalesce(p.type, 'dataset') NOT IN ('documents', 'learning') "
            "ORDER BY s.total_views DESC LIMIT :n"
        ), {'gid': group_id, 'n': limit}).fetchall()
        return [r[0] for r in rows]
    except Exception as e:
        log.warning(f'initiative: most viewed datasets unavailable: {e}')
        model.Session.rollback()
        return []


def featured_datasets(group_dict, names, limit=MAX_FEATURED):
    """Datasets destacados elegidos; si no hay, los más vistos del grupo;
    si no hay visitas registradas, los más recientes. Devuelve (lista, modo)."""
    gname = group_dict['name']
    mode = 'chosen'
    if not names:
        names, mode = most_viewed_names(group_dict['id'], limit), 'most_viewed'
    if names:
        quoted = ' OR '.join('"%s"' % n.replace('"', '') for n in names)
        res = _search(f'groups:"{gname}" +name:({quoted})', len(names))
        by_name = {p['name']: p for p in res.get('results', [])}
        found = [by_name[n] for n in names if n in by_name]
        if found:
            return found[:limit], mode
    res = _search(f'groups:"{gname}" -type:documents -type:learning', limit)
    return res.get('results', []), 'newest'


def initiative_data(group_dict):
    """Todo lo que necesita la plantilla común, a partir de la página guardada."""
    page = page_for_group(group_dict) or {'details': empty_details(), 'palette': build_palette({})}
    d = page['details']
    types = dict(INITIATIVE_TYPES)
    titles = ihpix_constants.load_output_titles()
    ms_titles = dict(member_states())
    orgs = _org_dicts(([d['lead_org']] if d['lead_org'] else []) + d['partners'])
    short = d['short_name'] or group_dict.get('display_name') or group_dict.get('title') or group_dict['name']

    outputs = [{'code': c, 'text': titles.get(c, ''),
                'pa': ihpix_constants.priority_area_for_output(c) or ''} for c in d['outputs']]
    out_codes = ' · '.join(d['outputs'])
    eyebrow = d['eyebrow']
    if not eyebrow:
        bits = [types.get(d['type'], '')]
        if d['outputs']:
            bits.append(('IHP-IX Output ' if len(d['outputs']) == 1 else 'IHP-IX Outputs ') + out_codes)
        eyebrow = ' · '.join(b for b in bits if b)

    datasets, datasets_mode = featured_datasets(group_dict, d['featured_datasets'])
    sections = set(d['sections'])
    images = d['images']
    credits = sorted({img['credit'] for img in images.values() if img.get('credit') and img.get('url')})
    opener = images['support']['url'] and images['support'] or images['hero']

    return {
        'page': page, 'details': d, 'short_name': short,
        'title1': d['title_line1'] or group_dict.get('display_name') or group_dict.get('title'),
        'title2': d['title_line2'] if d['title_line1'] else '',
        'eyebrow': eyebrow, 'type_label': types.get(d['type'], ''),
        'status_label': dict(STATUSES).get(d['status'], ''),
        'scope_label': dict(SCOPES).get(d['scope'], ''),
        'lead': orgs.get(d['lead_org']),
        'partners': [orgs[n] for n in d['partners'] if n in orgs],
        'member_states': [{'name': n, 'title': ms_titles.get(n, n),
                           'url': toolkit.url_for('group.read', id=n)} for n in d['member_states']],
        'outputs': outputs, 'output_codes': out_codes,
        'sdgs': [{'n': n, 'name': SDGS[n - 1]} for n in d['sdgs'] if 1 <= n <= 17],
        'contacts': [c for c in d['contacts'] if c.get('public')],
        'objectives': d['objectives'],
        'figures': [f for f in d['figures'] if f.get('value') or f.get('label')],
        'show': {k: (k in sections) for k, _l in SECTIONS},
        'datasets': datasets, 'datasets_mode': datasets_mode,
        'images': images, 'opener': opener, 'credits': credits,
        'can_setup': can_setup(group_dict),
    }


def setup_link(group_dict):
    """Botón para administradores: crear o editar la página completa."""
    if not can_setup(group_dict):
        return None
    has_page = bool(page_for_group(group_dict))
    return {'url': toolkit.url_for('theme_ejemplo.initiative_page_setup', name=group_dict['name']),
            'label': _('Edit the initiative page') if has_page else _('Set up the full initiative page'),
            'has_page': has_page}


def request_page(request_id):
    """Para la lista de solicitudes (admin): respuestas de la página completa."""
    try:
        return get_page_by_request(request_id)
    except Exception:
        model.Session.rollback()
        return None


# --------------------------------------------------------------------------
# Vistas
# --------------------------------------------------------------------------
def _flash_errors(errors):
    for label, msgs in errors.items():
        for m in msgs:
            toolkit.h.flash_error(f'{label}: {m}')


def _render_form(template, details, palette, errors=None, form=None, **extra):
    return toolkit.render(template, extra_vars=dict(
        details=details, palette=palette, errors=errors or {},
        form=form or {}, lists=form_lists(extra.get('group', {}).get('name') if extra.get('group') else None),
        checks=contrast_checks(palette['roles']), **extra))


def request_full_view():
    """GET/POST /initiatives/request/full: solicitud con página completa."""
    if not current_user.is_authenticated:
        return toolkit.redirect_to('user.login')
    from ckanext.theme_ejemplo.controller import MyLogica
    from ckanext.theme_ejemplo.model import InitiativeRequest

    if InitiativeRequest.get_pending_for_user(current_user.id):
        toolkit.h.flash_notice(_('You already have an initiative request waiting for review. '
                                 'Please wait until an administrator has processed it.'))
        return toolkit.redirect_to('theme_ejemplo.initiatives')

    if request.method != 'POST':
        return _render_form('initiative/request_full.html', empty_details(), build_palette({}), mode='request')

    details, palette, uploads, errors = parse_form(request.form, request.files, mode='request')
    if not (request.form.get('title') or '').strip():
        errors.setdefault(_('Initiative name'), []).append(_('This field is required.'))
    if not (request.form.get('description') or '').strip():
        errors.setdefault(_('About the initiative'), []).append(_('This field is required.'))
    if errors:
        _flash_errors(errors)
        return _render_form('initiative/request_full.html', details, palette, errors, request.form, mode='request')

    # La solicitud se crea con la vista de siempre (validación, logo, aviso a sysadmins)
    response = MyLogica.request_initiative()
    req = InitiativeRequest.get_pending_for_user(current_user.id)
    if not req:
        # La vista estándar rechazó los datos (sus mensajes ya están en flash)
        return _render_form('initiative/request_full.html', details, palette, {}, request.form, mode='request')
    try:
        apply_uploads(details, uploads)
    except toolkit.ValidationError as e:
        log.warning(f'initiative: image upload failed for request {req.id}: {e}')
        toolkit.h.flash_error(_('Some images could not be saved. You can add them after approval.'))
    save_page(details, palette, request_id=req.id)
    return response


def page_setup_view(name):
    """GET/POST /group/<name>/page-setup: crear (desde la solicitud estándar)
    o editar la página completa de una iniciativa."""
    if not current_user.is_authenticated:
        return toolkit.redirect_to('user.login')
    try:
        group = toolkit.get_action('group_show')({'ignore_auth': True}, {'id': name, 'include_datasets': False})
    except toolkit.ObjectNotFound:
        return toolkit.abort(404, _('Initiative not found'))
    if not can_setup(group):
        return toolkit.abort(403, _('Only the initiative administrators can set up its page.'))
    page = get_page_by_group(group['id'])

    if request.method != 'POST':
        details = page['details'] if page else empty_details()
        palette = page['palette'] if page and page.get('palette') else build_palette({})
        return _render_form('initiative/page_setup.html', details, palette, mode='setup', group=group, page=page)

    details, palette, uploads, errors = parse_form(request.form, request.files, mode='setup')
    if errors:
        _flash_errors(errors)
        return _render_form('initiative/page_setup.html', details, palette, errors, request.form,
                            mode='setup', group=group, page=page)
    try:
        apply_uploads(details, uploads)
    except toolkit.ValidationError as e:
        toolkit.h.flash_error(_('Some images could not be saved: %s') % e)
        return _render_form('initiative/page_setup.html', details, palette, {}, request.form,
                            mode='setup', group=group, page=page)
    save_page(details, palette, group_id=group['id'], page_id=page['id'] if page else None)
    toolkit.h.flash_success(_('The initiative page was saved.'))
    return toolkit.redirect_to('group.read', id=group['name'])


def request_answers_view(request_id):
    """GET /ckan-admin/initiative-requests/<id>/answers (sysadmin): respuestas
    del cuestionario y colores, para revisar la solicitud."""
    if not current_user.is_authenticated or not current_user.sysadmin:
        return toolkit.abort(403, _('Only administrators can review initiative requests.'))
    from ckanext.theme_ejemplo.model import InitiativeRequest
    req = InitiativeRequest.get(request_id)
    page = get_page_by_request(request_id) if req else None
    if not req or not page:
        return toolkit.abort(404, _('No full-page answers for this request.'))
    palette = page['palette'] or build_palette({})
    return toolkit.render('initiative/request_answers.html', extra_vars={
        'req': req.as_dict(), 'details': page['details'], 'palette': palette,
        'checks': contrast_checks(palette['roles']), 'lists': form_lists(),
        'orgs': _org_dicts(([page['details']['lead_org']] if page['details']['lead_org'] else []) + page['details']['partners']),
        'ms_titles': dict(member_states()),
        'labels': {'type': dict(INITIATIVE_TYPES), 'status': dict(STATUSES), 'scope': dict(SCOPES)},
        'aiw_style': palette_style(palette),
    })


def add_url_rules(blueprint):
    """Rutas de este módulo (se registran en plugin.get_blueprint)."""
    blueprint.add_url_rule('/initiatives/request/full', 'initiative_request_full',
                           request_full_view, methods=['GET', 'POST'])
    blueprint.add_url_rule('/group/<name>/page-setup', 'initiative_page_setup',
                           page_setup_view, methods=['GET', 'POST'])
    blueprint.add_url_rule('/ckan-admin/initiative-requests/<request_id>/answers',
                           'initiative_request_answers', request_answers_view, methods=['GET'])


def get_helpers():
    """Helpers de plantilla de este módulo (se registran en plugin.py)."""
    return {
        'theme_ejemplo_initiative_data': initiative_data,
        'theme_ejemplo_initiative_page': page_for_group,
        'theme_ejemplo_initiative_setup_link': setup_link,
        'theme_ejemplo_initiative_request_page': request_page,
        'theme_ejemplo_initiative_json': lambda v: json.dumps(v, ensure_ascii=False),
    }
