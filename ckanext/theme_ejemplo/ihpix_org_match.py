# -*- coding: utf-8 -*-
u"""Sugerencias de vinculación entre la institución heredada (texto libre) de
una actividad IHP-IX y las organizaciones de IHP-WINS. Módulo **puro**.

La atribución de actividades a organizaciones es por id (DOC-036); este
módulo sólo *propone* coincidencias con una puntuación y una razón. La
decisión la toma un sysadmin en `/ckan-admin/ihpix/institutions` y la aplica
la acción `ihpix_institution_link`, que deja una revisión por actividad.

Razones (de mayor a menor confianza):

- ``exact``     el texto normalizado coincide con el título o el slug.
- ``acronym``   el acrónimo entre paréntesis coincide ("… (ICHARM)" ↔ ICHARM).
- ``contains``  uno de los nombres contiene al otro
                ("UNESCO Regional Office for Southern Africa" ↔ "… - Harare …").
- ``segment``   el primer tramo de un texto compuesto coincide
                ("CERSHI, National Autonomous University…" ↔ CERSHI).
- ``initials``  las iniciales coinciden ("UK CEH" ↔ UK Centre for Ecology and
                Hydrology; "Regional Centre for Integrated River Basin
                Management" ↔ RC-IRBM).
- ``token``     una palabra del texto es el acrónimo o las iniciales de la
                organización ("UNESCO IHP" ↔ Intergovernmental Hydrological
                Programme).
- ``similar``   solape de palabras o parecido de cadena (erratas).
"""
import re
import unicodedata
from collections import OrderedDict
from difflib import SequenceMatcher

from ckanext.theme_ejemplo import ihpix_normalize as N

# Umbrales de la interfaz: por debajo de THRESHOLD no se muestra; a partir de
# CONFIDENT la sugerencia se preselecciona en el formulario.
THRESHOLD = 0.6
CONFIDENT = 0.9
MAX_SUGGESTIONS = 3

# Palabras vacías en inglés, español, francés y portugués (títulos de dev).
STOPWORDS = frozenset((
    'the', 'of', 'for', 'and', 'on', 'in', 'at', 'to', 'a', 'an', 'by', 'with',
    'de', 'del', 'la', 'las', 'los', 'el', 'y', 'e', 'en', 'para', 'por',
    'du', 'des', 'le', 'les', 'et', 'da', 'do', 'das', 'dos', 'pour', 'sur',
))
# Palabras tan frecuentes en los títulos que pesan la mitad en el solape.
GENERIC = frozenset((
    'unesco', 'regional', 'office', 'chair', 'centre', 'international',
    'national', 'institute', 'university', 'water', 'research', 'department',
    'programme', 'committee', 'agency', 'ministry', 'management', 'resources',
    'sciences', 'science', 'development', 'sustainable', 'global',
    'environment', 'environmental', 'technology', 'hydrology', 'hydrological',
))
# Grafías equivalentes (inglés británico / americano).
VARIANTS = {
    'center': 'centre', 'centers': 'centres', 'program': 'programme',
    'programs': 'programmes', 'organisation': 'organization',
    'organisations': 'organizations',
}
# Coletillas que no identifican a la institución.
BOILERPLATE = (
    re.compile(r'\bunder the auspic\w* of (the )?unesco\b', re.I),
    re.compile(r'\bunesco (c2c|category (2|ii|two) (centre|center))\b', re.I),
    re.compile(r'\bcategory (2|ii|two) (centre|center)\b', re.I),
    re.compile(r'\bc2c\b', re.I),
)
PAREN_RE = re.compile(r'\(([^()]{2,40})\)')
SEGMENT_RE = re.compile(r',|;|/|\s[-–—]\s|\band\b|&', re.I)
NON_ALNUM_RE = re.compile(r'[^a-z0-9]+')
WORD_RE = re.compile(r'[A-Za-z0-9]+')
MIN_CONTAINS_CHARS = 12


def _ascii(text):
    u"""Minúsculas sin diacríticos; `&` como "and" y apóstrofos plegados."""
    text = N._key(text)
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    return text.replace('&', ' and ')


def normalize(text):
    u"""Texto comparable: ASCII, sin puntuación, grafías unificadas y sin
    coletillas ("under the auspices of UNESCO"). Conserva las palabras vacías."""
    words = NON_ALNUM_RE.sub(' ', _ascii(text)).split()
    text = ' '.join(VARIANTS.get(word, word) for word in words)
    for pattern in BOILERPLATE:
        text = pattern.sub(' ', text)
    return ' '.join(text.split())


def key(text):
    u"""Clave de agrupación/comparación: `normalize` sin palabras vacías."""
    return ' '.join(word for word in normalize(text).split() if word not in STOPWORDS)


def compact(text):
    return key(text).replace(' ', '')


def tokens(text):
    return frozenset(key(text).split())


def acronyms(text):
    u"""Siglas entre paréntesis, compactadas ("(i-WSSM)" → "iwssm")."""
    found = set()
    for inner in PAREN_RE.findall(str(text or '')):
        inner = inner.strip()
        if len(inner.split()) > 2:
            continue
        value = NON_ALNUM_RE.sub('', _ascii(inner))
        if 2 <= len(value) <= 12 and not value.isdigit():
            found.add(value)
    return frozenset(found)


def initials(text):
    u"""Iniciales del texto sin paréntesis ni palabras vacías; una palabra ya
    escrita en mayúsculas (≤ 5 letras) se conserva entera: "UK Centre for
    Ecology and Hydrology" → "ukceh"; "HTC Kuala Lumpur" → "htckl"."""
    plain = PAREN_RE.sub(' ', str(text or ''))
    for pattern in BOILERPLATE:
        plain = pattern.sub(' ', plain)
    parts = []
    for word in WORD_RE.findall(plain):
        low = _ascii(word)
        if low in STOPWORDS or not low:
            continue
        if word.isupper() and len(word) <= 5:
            parts.append(low)
        else:
            parts.append(low[0])
    return ''.join(parts)


def pieces(text):
    u"""Tramos crudos de un texto compuesto ("CERSHI, UNAM and …")."""
    return [piece.strip() for piece in SEGMENT_RE.split(str(text or '')) if piece and piece.strip()]


def segments(text):
    u"""Claves de los tramos de un texto compuesto, sin repetidos."""
    out = []
    for piece in pieces(text):
        piece_key = key(piece)
        if piece_key and piece_key not in out:
            out.append(piece_key)
    return out


def prepare_org(org):
    u"""Precalcula las formas comparables de una organización CKAN
    (`{id, name, title}`)."""
    title = N.clean_text(org.get('title') or org.get('display_name') or org.get('name'))
    name = N.clean_text(org.get('name'))
    slug_text = name.replace('-', ' ').replace('_', ' ')
    title_key, slug_key = key(title), key(slug_text)
    return {
        'id': org.get('id'), 'name': name, 'title': title,
        'key': title_key, 'slug_key': slug_key,
        'compact': title_key.replace(' ', ''), 'slug_compact': slug_key.replace(' ', ''),
        'tokens': frozenset(title_key.split()) | frozenset(slug_key.split()),
        'acronyms': acronyms(title),
        'initials': initials(title), 'slug_initials': initials(slug_text),
    }


def prepare_orgs(orgs):
    return [prepare_org(org) for org in orgs or [] if org.get('id')]


def prepare_institution(text):
    text = N.clean_text(text)
    text_key = key(text)
    parts = pieces(text)
    # Iniciales del texto completo y del primer tramo ("Dublin City
    # University, Ireland" → "dcui" y "dcu").
    inits = {initials(text)}
    if parts:
        inits.add(initials(parts[0]))
    return {
        'text': text, 'key': text_key, 'compact': text_key.replace(' ', ''),
        'tokens': frozenset(text_key.split()), 'acronyms': acronyms(text),
        'initials': initials(text), 'initials_set': frozenset(i for i in inits if len(i) >= 3),
        'segments': segments(text),
    }


def _weight(token):
    return 0.5 if token in GENERIC else 1.0


def _same_token(a, b):
    u"""Palabras iguales o una prefijo de la otra a partir de 6 letras
    ("slovenia" ~ "slovenian", "hydrology" ~ "hydrological")."""
    if a == b:
        return True
    return len(a) >= 6 and len(b) >= 6 and (a.startswith(b) or b.startswith(a))


def _shared(a, b):
    u"""Palabras de `a` con equivalente en `b`."""
    return frozenset(x for x in a if any(_same_token(x, y) for y in b))


def _overlap(a, b):
    u"""Jaccard ponderado (las palabras genéricas pesan la mitad) y número de
    palabras compartidas."""
    shared = _shared(a, b)
    if not shared:
        return 0.0, 0
    union = sum(_weight(t) for t in a) + sum(_weight(t) for t in b - _shared(b, a))
    return (sum(_weight(t) for t in shared) / union if union else 0.0), len(shared)


def _contains(inner, outer, min_tokens):
    u"""`inner` aparece como secuencia de palabras completas dentro de `outer`.
    Devuelve 0.9 cuando `inner` es específico (≥ `min_tokens` palabras) y 0.75
    cuando es un fragmento genérico ("Field Office", "IHP National Committee")."""
    if len(inner) < MIN_CONTAINS_CHARS or ' ' not in inner or len(outer) <= len(inner):
        return 0.0
    if (' ' + inner + ' ') not in (' ' + outer + ' '):
        return 0.0
    return 0.9 if len(inner.split()) >= min_tokens else 0.75


def _ratio(a, b):
    if not a or not b:
        return 0.0
    matcher = SequenceMatcher(None, a, b)
    if matcher.real_quick_ratio() < 0.8 or matcher.quick_ratio() < 0.8:
        return 0.0
    return matcher.ratio()


def score(inst, org):
    u"""`(puntuación 0..1, razón)` entre una institución y una organización
    preparadas; `(0.0, None)` cuando no hay nada que sugerir."""
    if not inst['key'] or not (org['key'] or org['slug_key']):
        return 0.0, None
    org_keys = {k for k in (org['key'], org['slug_key']) if k}
    org_compacts = {k for k in (org['compact'], org['slug_compact']) if k}
    if inst['key'] in org_keys or inst['compact'] in org_compacts:
        return 1.0, 'exact'
    best = [0.0, None]

    def consider(value, reason):
        if value > best[0]:
            best[:] = [value, reason]

    if inst['acronyms'] & (org['acronyms'] | org_compacts):
        consider(0.95, 'acronym')
    if org['acronyms'] & ({inst['compact']} | inst['tokens']):
        consider(0.9, 'acronym')
    for org_key in org_keys:
        # Organización dentro del texto ("… at CERSHI …") o texto dentro del
        # título de la organización ("UNESCO Regional Office for Southern
        # Africa" ↔ "… - Harare Natural Science Sector").
        consider(_contains(org_key, inst['key'], 3), 'contains')
        consider(_contains(inst['key'], org_key, 4), 'contains')
    first = inst['segments'][0] if inst['segments'] else ''
    if first and first != inst['key']:
        if first in org_keys or first.replace(' ', '') in org_compacts:
            consider(0.9, 'segment')
        elif any(seg in org_keys or seg.replace(' ', '') in org_compacts
                 for seg in inst['segments'][1:]):
            consider(0.8, 'segment')
    org_initials = {k for k in (org['initials'], org['slug_initials']) if len(k) >= 3}
    if inst['compact'] in org_initials:
        consider(0.85, 'initials')
    if inst['initials_set'] & (org_compacts | org['acronyms']):
        consider(0.85, 'initials')
    short_org = {k for k in org_compacts if 3 <= len(k) <= 8}
    if short_org & inst['tokens']:
        consider(0.8, 'token')
    if org_initials & inst['tokens'] or inst['initials_set'] & org['tokens']:
        consider(0.7, 'token')
    jaccard, shared = _overlap(inst['tokens'], org['tokens'])
    if shared >= 2 and jaccard >= 0.5:
        consider(min(0.85, 0.6 + 0.25 * jaccard), 'similar')
    # Parecido de cadena (erratas) sólo si comparten alguna palabra específica:
    # evita emparejar "UNESCO Cairo Office" con "UNESCO Jakarta Office".
    specific = _shared(inst['tokens'] - GENERIC, org['tokens'] - GENERIC)
    if specific:
        ratio = max(_ratio(inst['key'], org_key) for org_key in org_keys)
        if ratio >= 0.8:
            consider(min(0.8, 0.6 + (ratio - 0.8)), 'similar')
    return (round(best[0], 2), best[1]) if best[0] >= THRESHOLD else (0.0, None)


def suggest(institution, prepared_orgs, limit=MAX_SUGGESTIONS, threshold=THRESHOLD):
    u"""Mejores organizaciones para un texto (o institución preparada):
    `[{id, name, title, score, reason, confident}]` de mayor a menor."""
    inst = institution if isinstance(institution, dict) else prepare_institution(institution)
    found = []
    for org in prepared_orgs:
        value, reason = score(inst, org)
        if value >= threshold:
            found.append({'id': org['id'], 'name': org['name'], 'title': org['title'],
                          'score': value, 'reason': reason, 'confident': value >= CONFIDENT})
    found.sort(key=lambda item: (-item['score'], item['title'].lower(), item['name']))
    return found[:limit] if limit else found


def _variant_display(variants):
    u"""Texto representativo del grupo: el más frecuente; a igualdad, el primero."""
    best, best_count = None, -1
    for text, count in variants.items():
        if count > best_count:
            best, best_count = text, count
    return best or ''


def group_activities(rows):
    u"""Agrupa actividades (`{id, institution, institution_org_id, status}`) por
    clave de institución. Devuelve `{'unlinked': [...], 'linked': [...],
    'totals': {...}}`; cada grupo trae `key`, `institution`, `variants`,
    `count`, `ids` y `statuses`; los vinculados añaden `organization_id`."""
    unlinked, linked = OrderedDict(), OrderedDict()
    without_institution = 0
    for row in rows or []:
        text = N.clean_text(row.get('institution'))
        text_key = key(text)
        if not text_key:
            without_institution += 1
            continue
        org_id = N.clean_text(row.get('institution_org_id'))
        bucket, group_key = (linked, (text_key, org_id)) if org_id else (unlinked, text_key)
        group = bucket.get(group_key)
        if group is None:
            group = bucket[group_key] = {'key': text_key, 'variants': OrderedDict(), 'count': 0,
                                         'ids': [], 'statuses': OrderedDict()}
            if org_id:
                group['organization_id'] = org_id
        group['variants'][text] = group['variants'].get(text, 0) + 1
        group['count'] += 1
        group['ids'].append(row.get('id'))
        status = row.get('status') or ''
        group['statuses'][status] = group['statuses'].get(status, 0) + 1

    def finish(bucket):
        out = []
        for group in bucket.values():
            display = _variant_display(group['variants'])
            group['institution'] = display
            group['variants'] = [text for text in group['variants'] if text != display]
            group['statuses'] = dict(group['statuses'])
            out.append(group)
        out.sort(key=lambda g: (-g['count'], g['institution'].lower()))
        return out

    unlinked_list, linked_list = finish(unlinked), finish(linked)
    return {
        'unlinked': unlinked_list, 'linked': linked_list,
        'totals': {
            'unlinked_groups': len(unlinked_list),
            'unlinked_activities': sum(g['count'] for g in unlinked_list),
            'linked_groups': len(linked_list),
            'linked_activities': sum(g['count'] for g in linked_list),
            'without_institution': without_institution,
        },
    }


def filter_groups(groups, query):
    u"""Filtra grupos por texto (institución, variantes o clave)."""
    needle = key(query)
    if not needle:
        return list(groups)
    out = []
    for group in groups:
        haystack = ' '.join([group['key']] + [key(v) for v in group.get('variants', [])])
        if needle in haystack or needle.replace(' ', '') in haystack.replace(' ', ''):
            out.append(group)
    return out
