# -*- coding: utf-8 -*-
"""Tests del módulo puro `ihpix_org_match`: sugerencias de organización para
instituciones heredadas (texto libre) y agrupación de actividades."""
import json
import os

from ckanext.theme_ejemplo import ihpix_org_match as OM

# Muestra de organizaciones reales de dev (2026-10-24): el título suele ser el
# acrónimo y el `name` el nombre largo en slug.
ORGS = [
    {'id': 'o-icharm', 'name': 'international-centre-for-water-hazard-and-risk-management', 'title': 'ICHARM'},
    {'id': 'o-iwssm', 'name': 'international-centre-for-water-security-and-sustainable-management', 'title': 'i-WSSM'},
    {'id': 'o-cershi', 'name': 'regional-centre-on-water-security', 'title': 'CERSHI'},
    {'id': 'o-icwrgc', 'name': 'international-centre-for-water-resources-and-global-change', 'title': 'ICWRGC'},
    {'id': 'o-igrac', 'name': 'igrac', 'title': 'IGRAC'},
    {'id': 'o-ihe', 'name': 'ihe-delft-institute-for-water-education', 'title': ' IHE Delft'},
    {'id': 'o-ukceh', 'name': 'uk-centre-for-ecology-and-hydrology', 'title': 'UK Centre for Ecology and Hydrology'},
    {'id': 'o-htc', 'name': 'regional-humid-tropics-hydrology-and-water-resources-centre-for-south-east-asia-and-the-pacific',
     'title': 'HTC Kuala Lumpur'},
    {'id': 'o-rcirbm', 'name': 'regional-centre-for-integrated-river-basin-management', 'title': 'RC-IRBM'},
    {'id': 'o-ihp', 'name': 'intergovernmental-hydrological-programme', 'title': 'Intergovernmental Hydrological Programme'},
    {'id': 'o-harare', 'name': 'unesco-regional-office-for-southern-africa---harare-natural-science-sector-',
     'title': 'UNESCO Regional Office for Southern Africa - Harare Natural Science Sector '},
    {'id': 'o-nairobi', 'name': 'unesco-nairobi', 'title': 'UNESCO Regional Office for Eastern Africa - Nairobi  Science Sector'},
    {'id': 'o-maghreb', 'name': 'unesco-regional-office-for-the-maghreb', 'title': 'UNESCO Regional Office for the Maghreb'},
    {'id': 'o-jakarta', 'name': 'unesco-jakarta-office', 'title': 'UNESCO Jakarta Office'},
    {'id': 'o-baghdad', 'name': 'unesco-field-office-baghdad-iraq', 'title': 'UNESCO Field Office Baghdad, Iraq'},
    {'id': 'o-gambia', 'name': 'gambia-ihp-national-committee', 'title': 'Gambia IHP National Committee'},
    {'id': 'o-slovenia', 'name': 'republic-of-slovenia-national-ihp-committee', 'title': 'Republic of Slovenia National IHP Committee'},
    {'id': 'o-korea', 'name': 'republic-of-korea-ihp-national-committee', 'title': 'Republic of Korea IHP National Committee'},
    {'id': 'o-dcu', 'name': 'dcu-water-institute', 'title': 'DCU Water Institute'},
    {'id': 'o-wwf', 'name': 'world-wide-fund-for-nature-wwf', 'title': 'World Wide Fund for Nature (WWF)'},
    {'id': 'o-wendi', 'name': 'chair-on-water-energy-and-disaster-management-for-sustainable-development-wendi',
     'title': 'UNESCO Chair on Water, Energy and Disaster Management for Sustainable Development, (WENDI)'},
    {'id': 'o-dws', 'name': 'department-of-water-and-sanitation-south-africa', 'title': 'Department of Water and Sanitation South Africa'},
    {'id': 'o-amsterdam', 'name': 'university-of-amsterdam', 'title': 'University of Amsterdam'},
    {'id': 'o-citizen', 'name': 'citizen-science', 'title': 'Citizen Science'},
    {'id': 'o-sustain', 'name': 'unesco-chair-on-sustainability', 'title': 'UNESCO Chair on Sustainability'},
    {'id': 'o-tehran', 'name': 'unesco-chair-on-water-reuse-at-the-university-of-tehran', 'title': 'UNESCO Chair on Water Reuse at the University of Tehran '},
]
PREPARED = OM.prepare_orgs(ORGS)


def _top(text):
    found = OM.suggest(text, PREPARED)
    return (found[0]['id'], found[0]['score'], found[0]['reason']) if found else (None, 0.0, None)


def test_normalization_folds_accents_variants_and_boilerplate():
    assert OM.normalize(u'Regional Center for Water Security under the auspicies of UNESCO') == \
        'regional centre for water security'
    assert OM.key(u'Côte d’Ivoire & Partners') == 'cote d ivoire partners'
    assert OM.key('UNESCO-IHP') == OM.key('UNESCO IHP') == 'unesco ihp'
    assert OM.acronyms('International Centre … Management(i-WSSM) under the auspices of UNESCO') == {'iwssm'}
    assert OM.acronyms('Chair (Portugal) and (2024)') == {'portugal'}
    assert OM.initials('UK Centre for Ecology and Hydrology') == 'ukceh'
    assert OM.initials('HTC Kuala Lumpur') == 'htckl'
    assert OM.initials('Regional Centre for Integrated River Basin Management (RC-IRBM)') == 'rcirbm'
    assert OM.segments('CERSHI, National Autonomous University of Mexico and Embassy of Sweden in Mexico') == [
        'cershi', 'national autonomous university mexico', 'embassy sweden mexico']


def test_exact_and_slug_matches_score_one():
    assert _top('ICWRGC') == ('o-icwrgc', 1.0, 'exact')
    assert _top('IHE Delft Institute for Water Education') == ('o-ihe', 1.0, 'exact')
    assert _top('UNESCO Nairobi') == ('o-nairobi', 1.0, 'exact')
    # Center/Centre, "for"/"on" y la coletilla "under the auspices" no cuentan
    assert _top('Regional Center for Water Security under the auspicies of UNESCO') == ('o-cershi', 1.0, 'exact')
    assert _top('UK Centre for Ecology & Hydrology') == ('o-ukceh', 1.0, 'exact')


def test_acronyms_containment_segments_and_initials():
    assert _top('International Centre for Water hazard and Risk management under the auspices of UNESCO (ICHARM)') == (
        'o-icharm', 0.95, 'acronym')
    # Errata en el nombre largo: el acrónimo sigue resolviendo
    assert _top('International Centre for Water Secutiry and Sustainable Management(i-WSSM) under the auspices of UNESCO') == (
        'o-iwssm', 0.95, 'acronym')
    assert _top('WWF India') == ('o-wwf', 0.9, 'acronym')
    assert _top('UNESCO Chair WENDI') == ('o-wendi', 0.9, 'acronym')
    assert _top('Intergovernmental Hydrological Programme Secretariat') == ('o-ihp', 0.9, 'contains')
    assert _top('UNESCO Regional Office for Southern Africa') == ('o-harare', 0.9, 'contains')
    assert _top('UNESCO Chair on Sustainability at Polytechnical University of Catalonia') == ('o-sustain', 0.9, 'contains')
    assert _top('CERSHI, National Autonomous University of Mexico and Embassy of Sweden in Mexico') == (
        'o-cershi', 0.9, 'segment')
    assert _top('UK CEH') == ('o-ukceh', 0.85, 'initials')
    assert _top('HTC KL') == ('o-htc', 0.85, 'initials')
    # El slug largo coincide: exacto aunque el título sea el acrónimo
    assert _top('Regional Centre for Integrated River Basin Management') == ('o-rcirbm', 1.0, 'exact')
    # "Research" en vez de "Resources": sólo las iniciales coinciden
    assert _top('International Centre for Water Research and Global Change') == ('o-icwrgc', 0.85, 'initials')
    assert _top('IHP') == ('o-ihp', 0.85, 'initials')


def test_generic_fragments_are_suggested_but_not_confident():
    for text in ('Field Office', 'IHP National Committee', 'University of Tehran',
                 'Department of  water and sanitation', 'UNESCO IHP Secretariat', 'IHP-LAC',
                 'Dublin City University, Ireland'):
        found = OM.suggest(text, PREPARED)
        assert found, text
        assert found[0]['score'] < OM.CONFIDENT, (text, found[0])
        assert not found[0]['confident']
    assert _top('UNESCO IHP Secretariat')[0] == 'o-ihp'
    assert _top('Dublin City University, Ireland') == ('o-dcu', 0.7, 'token')
    # La palabra específica desempata entre comités nacionales
    assert _top('Slovenian National Committee IHP')[0] == 'o-slovenia'


def test_no_false_positives_for_unrelated_or_generic_names():
    for text in ('UNESCO', 'Coventry University', 'Federal University of Rio de Janeiro',
                 'UNESCO Cairo Office', 'UNESCO Khartoum Office', 'Water Research Commission', ''):
        assert OM.suggest(text, PREPARED) == [], text
    # La similitud de cadena no empareja oficinas distintas de UNESCO
    assert OM.score(OM.prepare_institution('UNESCO Regional Office in Cairo'),
                    OM.prepare_org(ORGS[12])) == (0.0, None)


def test_suggest_orders_limits_and_marks_confident():
    found = OM.suggest('IHP', PREPARED, limit=2)
    assert [item['id'] for item in found] == ['o-ihp', 'o-gambia']
    assert found[0]['confident'] is False and found[0]['score'] == 0.85
    assert OM.suggest('ICWRGC', PREPARED)[0]['confident'] is True
    assert all(0.6 <= item['score'] <= 1.0 for item in OM.suggest('IHP', PREPARED, limit=None))


def test_group_activities_merges_variants_and_splits_linked_rows():
    rows = [
        {'id': 'a1', 'institution': 'UNESCO IHP', 'institution_org_id': '', 'status': 'published'},
        {'id': 'a2', 'institution': 'UNESCO-IHP', 'institution_org_id': '', 'status': 'published'},
        {'id': 'a3', 'institution': ' unesco  ihp ', 'institution_org_id': None, 'status': 'draft'},
        {'id': 'a4', 'institution': 'IGRAC', 'institution_org_id': 'o-igrac', 'status': 'published'},
        {'id': 'a5', 'institution': 'IGRAC', 'institution_org_id': '', 'status': 'pending'},
        {'id': 'a6', 'institution': '', 'institution_org_id': '', 'status': 'published'},
        {'id': 'a7', 'institution': 'of the', 'institution_org_id': '', 'status': 'published'},
    ]
    groups = OM.group_activities(rows)
    assert groups['totals'] == {'unlinked_groups': 2, 'unlinked_activities': 4,
                                'linked_groups': 1, 'linked_activities': 1, 'without_institution': 2}
    first = groups['unlinked'][0]
    assert first['key'] == 'unesco ihp' and first['count'] == 3
    assert first['institution'] == 'UNESCO IHP'            # variante más frecuente (empate → primera)
    assert first['variants'] == ['UNESCO-IHP', 'unesco ihp']
    assert first['ids'] == ['a1', 'a2', 'a3'] and first['statuses'] == {'published': 2, 'draft': 1}
    assert groups['unlinked'][1]['institution'] == 'IGRAC' and groups['unlinked'][1]['ids'] == ['a5']
    linked = groups['linked'][0]
    assert linked['organization_id'] == 'o-igrac' and linked['ids'] == ['a4']
    assert OM.filter_groups(groups['unlinked'], 'ihp') == [first]
    assert OM.filter_groups(groups['unlinked'], 'UNESCO-IHP') == [first]
    assert OM.filter_groups(groups['unlinked'], '') == groups['unlinked']
    assert OM.filter_groups(groups['unlinked'], 'nothing here') == []


def test_seed_institutions_resolve_quickly_with_the_dev_sample():
    """Las 744 filas del seed (332 instituciones) deben agruparse y puntuarse
    en bien menos de un segundo; ninguna sugerencia confiable apunta a una
    organización que no comparta ninguna palabra con el texto."""
    import time
    path = os.path.join(os.path.dirname(__file__), '..', 'data', 'ihpix_seed_data.json')
    seed = json.load(open(path, encoding='utf-8'))
    seed = seed if isinstance(seed, list) else seed.get('activities', [])
    rows = [{'id': str(i), 'institution': row.get('institution'), 'institution_org_id': '',
             'status': 'published'} for i, row in enumerate(seed)]
    started = time.time()
    groups = OM.group_activities(rows)
    confident = 0
    for group in groups['unlinked']:
        for item in OM.suggest(group['institution'], PREPARED):
            if item['confident']:
                confident += 1
                org = next(o for o in PREPARED if o['id'] == item['id'])
                inst = OM.prepare_institution(group['institution'])
                assert (inst['tokens'] & org['tokens']) or (inst['acronyms'] & (org['acronyms'] | {org['compact']})), (
                    group['institution'], org['title'])
    assert time.time() - started < 1.0
    assert groups['totals']['unlinked_activities'] == len(rows) and groups['totals']['unlinked_groups'] >= 300
    assert confident >= 25
