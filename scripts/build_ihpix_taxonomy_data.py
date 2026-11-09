#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Genera taxonomías desde las preguntas públicas oficiales UNESCO (2026-10-21).

El snapshot sólo contiene preguntas/opciones, nunca respuestas personales.
--check verifica que los artefactos reproducibles coinciden. --seed permite
consultar el origen heredado, sin sustituir la fuente oficial por defecto.
"""
from __future__ import unicode_literals

import argparse
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, '..', 'ckanext', 'theme_ejemplo', 'data')
SEED_FILE = os.path.join(DATA_DIR, 'ihpix_seed_data.json')
OUTPUT_TITLES_FILE = os.path.join(DATA_DIR, 'ihpix_output_titles.json')
KEY_ACTIVITIES_FILE = os.path.join(DATA_DIR, 'ihpix_key_activities.json')

# Tokens partidos por un espacio en la extracción del PDF → forma correcta.
# Sólo se corrige lo que aparece en el seed; ante la duda se conserva.
BROKEN_TOKENS = collections.OrderedDict([
    ('UNES CO', 'UNESCO'),
    ('impr oving', 'improving'),
    ('techn icians', 'technicians'),
    ('scient ific', 'scientific'),
    ('Public s awareness', "Public's awareness"),
    ('import ant', 'important'),
    ('wat er', 'water'),
    ('c ommunity', 'community'),
    ('transp ort', 'transport'),
    ('mana gement', 'management'),
    ('ensu re', 'ensure'),
    ('ri sk', 'risk'),
    ('f or', 'for'),
    ('developmen t', 'development'),
    ('Developmen t', 'Development'),
    ('ind ustrial', 'industrial'),
    ('resour ces', 'resources'),
    ('sustain able', 'sustainable'),
    ('implemen tation', 'implementation'),
    ('an d of', 'and of'),
    ('o rganization', 'organization'),
    ('p ublishing', 'publishing'),
    ('res ults', 'results'),
    ('tr ansition', 'transition'),
    ('resea rch', 'research'),
    ('resi lience', 'resilience'),
    ('fo r their', 'for their'),
    ('mitig ation', 'mitigation'),
    ('govern ance', 'governance'),
    ('e cohydrological', 'ecohydrological'),
    ('content s in', 'contents in'),
    ('Management ( and services', 'Management (IWRM) and services'),
    ('in Sites management', "in Sites' management"),
])

CODE_RE = re.compile(r'^\s*(\d+\.\d+\.\d+)\.?\s*(.*)$', re.S)
OUTPUT_PREFIX_RE = re.compile(r'^\s*(\d+\.\d+)\.?\s*(.*)$', re.S)
WS_RE = re.compile(r'\s+')


def clean_text(text):
    """Colapsa espacios, corrige tokens partidos y normaliza comillas."""
    text = WS_RE.sub(' ', (text or '')).strip()
    for broken, fixed in BROKEN_TOKENS.items():
        text = text.replace(broken, fixed)
    # Comillas tipográficas → ASCII sencillo, coherente en todo el fichero
    text = text.replace('’', "'").replace('“', '"').replace('”', '"')
    text = text.rstrip('.').strip()
    return text


def natural_key(code):
    try:
        return tuple(int(p) for p in code.split('.'))
    except ValueError:
        return (999,)


def build_output_titles(activities):
    """{code: title} eligiendo el texto más frecuente por output."""
    counter = collections.defaultdict(collections.Counter)
    for act in activities:
        code = (act.get('output') or '').strip()
        full = clean_text(act.get('output_full') or '')
        if not code or not full:
            continue
        m = OUTPUT_PREFIX_RE.match(full)
        title = m.group(2).strip() if m and m.group(1) == code else full
        if title:
            counter[code][title] += 1
    titles = {}
    for code in sorted(counter, key=natural_key):
        titles[code] = counter[code].most_common(1)[0][0]
    return titles


def build_key_activities(activities):
    """{output: [{"code", "title"}]} deduplicando por código."""
    counter = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for act in activities:
        output = (act.get('output') or '').strip()
        raw = clean_text(act.get('key_activity') or '')
        if not output or not raw:
            continue
        m = CODE_RE.match(raw)
        if not m:
            continue  # texto libre sin código: no es una key activity oficial
        code, title = m.group(1), m.group(2).strip()
        if not code.startswith(output + '.'):
            # El código no pertenece al output declarado: se asigna al output
            # que indica el propio código (dato heredado mal clasificado).
            output = code.rsplit('.', 1)[0]
        if title:
            counter[output][code][title] += 1
    result = collections.OrderedDict()
    for output in sorted(counter, key=natural_key):
        items = []
        for code in sorted(counter[output], key=natural_key):
            items.append({'code': code,
                          'title': counter[output][code].most_common(1)[0][0]})
        result[output] = items
    return result


def dump(path, data):
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=False) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--seed', default=None)
    parser.add_argument('--check', action='store_true',
                        help='No escribe; sale con 1 si los ficheros difieren')
    args = parser.parse_args(argv)

    if args.seed:
        with io.open(args.seed, encoding='utf-8') as fh:
            activities = json.load(fh).get('activities', [])
        titles, kas = build_output_titles(activities), build_key_activities(activities)
    else:
        with io.open(os.path.join(DATA_DIR, 'ihpix_official_taxonomy_source.json'), encoding='utf-8') as fh:
            questions = json.load(fh)['questions']
        titles, kas = {}, {}
        for question in questions:
            match = re.search(r'Key Activity under Output (\d+\.\d+)', question['title'])
            if match:
                items = []
                for choice in question['choices']:
                    code, title = CODE_RE.match(choice).groups()
                    items.append({'code': code, 'title': WS_RE.sub(' ', title).strip()})
                kas[match.group(1)] = items
            elif 'Under the framework of Priority Area' in question['title']:
                for choice in question['choices']:
                    code, title = OUTPUT_PREFIX_RE.match(choice).groups()
                    titles[code] = WS_RE.sub(' ', title).strip()
        assert len(titles) == len(kas) == 34
        assert sum(map(len, kas.values())) == 151
    outputs = {OUTPUT_TITLES_FILE: titles, KEY_ACTIVITIES_FILE: kas}
    changed = False
    for path, data in outputs.items():
        text = dump(path, data)
        current = None
        if os.path.exists(path):
            with io.open(path, encoding='utf-8') as fh:
                current = fh.read()
        if current == text:
            print('sin cambios: %s' % os.path.relpath(path))
            continue
        changed = True
        if args.check:
            print('DIFIERE: %s' % os.path.relpath(path))
            continue
        with io.open(path, 'w', encoding='utf-8') as fh:
            fh.write(text)
        print('escrito: %s' % os.path.relpath(path))

    titles = outputs[OUTPUT_TITLES_FILE]
    kas = outputs[KEY_ACTIVITIES_FILE]
    print('outputs con título: %d · outputs con key activities: %d · key activities: %d'
          % (len(titles), len(kas), sum(len(v) for v in kas.values())))
    return 1 if (args.check and changed) else 0


if __name__ == '__main__':
    sys.exit(main())
