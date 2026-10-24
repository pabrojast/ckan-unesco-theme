# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_entities`: ámbito de la pestaña IHP-IX de un
grupo CKAN y fichas enlazables de una actividad."""
import json

from ckanext.theme_ejemplo import ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_entities as E
from ckanext.theme_ejemplo import ihpix_stats as S

# Muestra real de grupos de dev (2026-10-23): países bajo `member-states` e
# iniciativas sueltas; algunas iniciativas coinciden con flagships IHP-IX.
MEMBER_STATES = [('chile', 'Chile'), ('kenya', 'Kenya'),
                 ('venezuela-bolivarian-republic-of-', 'Venezuela (Bolivarian Republic of)'),
                 ('c-te-d-ivoire', "Côte d'Ivoire"), ('netherlands', 'Netherlands')]
INITIATIVES = [('friend-water', 'FRIEND-Water'), ('g-wadi', 'G-WADI'), ('lasii', 'LaSII'),
               ('iwrm', 'IWRM'), ('help', 'HELP'), ('mar', 'MAR'), ('c4water', 'C4Water'),
               ('ecohydrology-and-water-quality', 'Ecohydrology and Water Quality'),
               ('be-resilient', 'Be Resilient')]
SUMMARIES = [{'country': 'Chile', 'region': 'Latin America and the Caribbean'},
             {'country': 'Kenya', 'region': 'Africa'},
             {'country': 'Venezuela', 'region': 'Latin America and the Caribbean'},
             {'country': u'Côte d’Ivoire', 'region': 'Africa'}]


def _index():
    return S.build_country_index(SUMMARIES, MEMBER_STATES)


def test_group_scope_distinguishes_member_states_from_initiatives():
    names = {slug for slug, _title in MEMBER_STATES}
    assert E.group_scope('chile', 'Chile', names) == ('country', 'chile')
    # Un país que no cuelga de member-states se reconoce por su título oficial
    assert E.group_scope('kenya', 'Kenya', set()) == ('country', 'kenya')
    assert E.group_scope('friend-water', 'FRIEND-Water', names) == ('flagship', 'FRIEND')
    assert E.group_scope('lasii', 'LaSII', names) == ('flagship', 'LASII')
    assert E.group_scope('g-wadi', 'G-WADI', names) == ('flagship', 'G-WADI')
    assert E.group_scope('ecohydrology-and-water-quality', 'Ecohydrology and Water Quality', names) == (
        'ctwg', 'Ecohydrology and Water Quality')
    # 'MAR' es flagship antes que ISO3 de Marruecos; una iniciativa ajena no se atribuye
    assert E.group_scope('mar', 'MAR', names) == ('flagship', 'MAR')
    assert E.group_scope('c4water', 'C4Water', names) == (None, None)
    assert E.group_scope('', '', names) == (None, None)


def test_scope_slug_matches_progress_and_explorer_urls():
    assert E.scope_slug('flagship', 'G-WADI') == 'g-wadi'
    assert E.scope_slug('ctwg', 'Ecohydrology and Water Quality') == 'ecohydrology-and-water-quality'
    assert E.scope_slug('country', 'chile') == 'chile'
    assert E.scope_slug(None, None) == ''


def test_group_maps_use_canonical_names_and_codes():
    index = _index()
    slugs = E.member_state_slugs(MEMBER_STATES, index)
    # El slug del grupo y el nombre heredado 'Venezuela' comparten canónico
    assert slugs['Venezuela'] == 'venezuela-bolivarian-republic-of-'
    assert slugs[u'Côte d’Ivoire'] == 'c-te-d-ivoire'
    assert slugs['Chile'] == 'chile'
    assert E.flagship_groups(INITIATIVES) == {'FRIEND': 'friend-water', 'G-WADI': 'g-wadi',
                                              'LASII': 'lasii', 'IWRM': 'iwrm', 'HELP': 'help',
                                              'MAR': 'mar'}
    assert E.ctwg_groups(INITIATIVES) == {'Ecohydrology and Water Quality': 'ecohydrology-and-water-quality'}


def test_activity_links_resolve_slugs_legacy_names_and_roles():
    index = _index()
    slugs = E.member_state_slugs(MEMBER_STATES, index)
    activity = {
        'id': 'a1', 'country': 'venezuela-bolivarian-republic-of-',  # el formulario guarda el slug
        'institution': 'Inst A', 'institution_org_id': 'org-1',
        'supporting_member_state': 'Kenya', 'supporters_json': json.dumps([{'country': 'CL', 'types': ['financial']}]),
        'member_states': 'Chile, Atlantis', 'flagships': 'FRIEND-Water; GWADI',
        'cross_cutting_wg': '["Ecohydrology and Water Quality"]', 'regions': '["Africa"]',
        'partner_org_ids': '["org-2", "org-3"]',
    }
    links = E.activity_links(activity, index, slugs, E.flagship_groups(INITIATIVES), E.ctwg_groups(INITIATIVES))
    assert links['country'] == {'label': 'Venezuela', 'group': 'venezuela-bolivarian-republic-of-', 'resolved': True}
    assert [(x['label'], x['group']) for x in links['supporters']] == [('Kenya', 'kenya'), ('Chile', 'chile')]
    assert [(x['label'], x['group'], x['resolved']) for x in links['beneficiaries']] == [
        ('Chile', 'chile', True), ('Atlantis', None, False)]
    assert [(x['code'], x['label'], x['slug'], x['group']) for x in links['flagships']] == [
        ('FRIEND', 'FRIEND-Water', 'friend', 'friend-water'), ('G-WADI', 'G-WADI', 'g-wadi', 'g-wadi')]
    assert links['cross_cutting_wg'] == [{'label': 'Ecohydrology and Water Quality',
                                          'slug': 'ecohydrology-and-water-quality',
                                          'group': 'ecohydrology-and-water-quality'}]
    assert links['regions'] == ['Africa']
    assert links['institution'] == {'label': 'Inst A', 'org_id': 'org-1'}
    assert links['partners'] == ['org-2', 'org-3']


def test_activity_links_tolerate_empty_and_invalid_fields():
    links = E.activity_links({'id': 'x', 'title': 't', 'partner_org_ids': 'not json',
                              'flagships': 'No', 'supporting_member_state': 'No'})
    assert links['country'] is None
    assert links['supporters'] == [] and links['beneficiaries'] == []
    assert links['flagships'] == [] and links['partners'] == []
    assert links['institution'] == {'label': '', 'org_id': ''}


def test_every_flagship_label_round_trips_through_flagship_for_group():
    for code in C.FLAGSHIPS:
        label = C.flagship_label(code)
        assert C.flagship_for_group(C.slugify(label), label) == code
        assert C.flagship_for_group(C.slugify(code)) == code
    assert C.flagship_for_group('chile', 'Chile') is None
    assert C.ctwg_for_group('groundwater-and-human-settlements') == 'Groundwater and Human Settlements'
    assert C.ctwg_for_group('chile') is None
