# -*- coding: utf-8 -*-
u"""Taxonomías oficiales del IHP-IX Reporting.

Fuente principal: Guidelines-for-IHP-IX-Reporting-EN.pdf (UNESCO, 2026) +
Operational Implementation Plan de IHP-IX (PA + Outputs).

Estas constantes alimentan tanto el formulario público `/ihpix/report`
como el dashboard admin `/ckan-admin/ihpix/overview`. Cuando una columna
del modelo `IhpixActivity` admita una lista controlada, valida contra los
sets de este módulo.

Convención:
- Cada taxonomía ofrece la opción 'Other' cuando el PDF lo contempla;
  en esos casos existe un campo de texto libre paralelo (`*_other`) en
  el modelo / form para capturar el detalle.
- Identificadores de PA/Output usan dot-notation oficial (`PA1`, `1.1`,
  `1.1.1`).
"""
from __future__ import unicode_literals

from collections import OrderedDict


# ─── Priority Areas (Section II) ─────────────────────────────────────────

PRIORITY_AREAS = OrderedDict([
    ('PA1', 'Scientific Research and Innovation'),
    ('PA2', 'Water Education in the Fourth Industrial Revolution including Sustainability'),
    ('PA3', 'Bridging the Data-Knowledge Gap'),
    ('PA4', 'Integrated Water Resources Management under Conditions of Global Change'),
    ('PA5', 'Water Governance based on Science for Mitigation, Adaptation, and Resilience'),
])


# ─── Outputs (34) — Operational Implementation Plan ──────────────────────
#
# Mapa: PA → lista de (código, título corto). Los títulos provienen del
# Strategic Plan / OIP; cuando no se cuenta con un título oficial el
# slot queda como string vacío (renderizar sólo el código en el form).

OUTPUTS = OrderedDict([
    ('PA1', [
        ('1.1', ''),
        ('1.2', ''),
        ('1.3', ''),
        ('1.4', ''),
        ('1.5', ''),
        ('1.6', ''),
        ('1.7', ''),
        ('1.8', ''),
        ('1.9', ''),
        ('1.10', ''),
    ]),
    ('PA2', [
        ('2.1', ''),
        ('2.2', ''),
        ('2.3', ''),
        ('2.4', ''),
        ('2.5', ''),
        ('2.6', ''),
    ]),
    ('PA3', [
        ('3.1', ''),
        ('3.2', ''),
        ('3.3', ''),
        ('3.4', ''),
    ]),
    ('PA4', [
        ('4.1', ''),
        ('4.2', ''),
        ('4.3', ''),
        ('4.4', ''),
        ('4.5', ''),
        ('4.6', ''),
        ('4.7', ''),
        ('4.8', ''),
        ('4.9', ''),
    ]),
    ('PA5', [
        ('5.1', ''),
        ('5.2', ''),
        ('5.3', ''),
        ('5.4', ''),
        ('5.5', ''),
    ]),
])


def output_codes_for(pa):
    u"""Devuelve la lista de códigos de Output bajo una PA dada."""
    return [code for code, _ in OUTPUTS.get(pa, [])]


def all_output_codes():
    u"""Devuelve la lista plana de los 34 códigos de Output."""
    return [code for pairs in OUTPUTS.values() for code, _ in pairs]


# ─── Cross-cutting Working Groups (Section III, 3) ───────────────────────

CROSS_CUTTING_WGS = (
    'Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus',
    'Ecohydrology and Water Quality',
    'Groundwater and Human Settlements',
)


# ─── UNESCO Regions (Section IV, 7) ──────────────────────────────────────

REGIONS = (
    'Global',
    'Africa',
    'Arab States',
    'Asia and the Pacific',
    'Eastern Europe',
    'Europe and North America',
    'Latin America and the Caribbean',
)


# ─── Flagship Initiatives (Section I, 15) ────────────────────────────────

FLAGSHIPS = (
    'FRIEND',
    'GRAPHIC',
    'G-WADI',
    'HELP',
    'IDI',
    'IFI',
    'IIWQ',
    'ISARM',
    'ISI',
    'LASII',
    'MAR',
    'PCCP',
    'WHYMAP',
    'WLRI',
    'WAMU-NET',
)


# ─── Biennia del programa IHP-IX 2022-2029 (Section I, 4) ────────────────

BIENNIA = (
    '2022-2023',
    '2024-2025',
    '2026-2027',
    '2028-2029',
)


# ─── Lead Implementing Institution (Section I, 12 + Other) ───────────────

LEAD_INSTITUTION_TYPES = (
    'UNESCO IHP Secretariat',
    'UNESCO Field Office',
    'IHP National Committee',
    'UNESCO Category I Center',
    'UNESCO Category II Center',
    'UNESCO Chair or UNITWIN',
    'Non-Governmental Organization',
    'Governmental Organization',
    'University',
    'Private Partner',
    'Research Institution',
    'Other',
)


# ─── KPI 1a: Knowledge Products (Section V, 7) ───────────────────────────

KNOWLEDGE_PRODUCT_TYPES = (
    'Book',
    'Report',
    'Assessment',
    'Statistic',
    'Tool',
    'Methodology',
    'Other',
)


# ─── KPI 1b: Scientific Products (Section V, 4) ──────────────────────────

SCIENTIFIC_PRODUCT_TYPES = (
    'Peer-reviewed articles',
    'Patents',
    'Scientific journal editions',
    'Scientific conference proceedings',
)


# ─── KPI 2: Knowledge generating activity (Section V, 5) ─────────────────

KNOWLEDGE_ACTIVITY_TYPES = (
    'Workshop or physical/online training course',
    'Seminar or online webinar',
    'International Conference',
    'Conference session or roundtable discussion',
    'Other',
)


# ─── KPI 3: Training materials / courses (Section V, 4) ──────────────────

TRAINING_TYPES = (
    'Physical training material (hard copy)',
    'Physical training material (soft copy)',
    'Physical training course',
    'Online training course',
)


# ─── KPI 8: Stakeholder Groups (Section V, 9) ────────────────────────────
#
# Los descriptores parentéticos del PDF se conservan para mostrar tooltips
# en el form; el value persistido en BD es la frase sin paréntesis (índice 0).

STAKEHOLDER_GROUP_TYPES = (
    ('River Basin Organizations or Regional Water Management Bodies',
     'River basin orgs / regional water management bodies.'),
    ('Community Groups',
     'Local communities, resident organizations, Community-Based Organizations, '
     'indigenous and traditional water management groups.'),
    ('Government Agencies',
     'National water departments or ministries, environmental protection agencies, '
     'local government authorities responsible for water management.'),
    ('Water Utilities',
     'Organizations responsible for water supply and distribution, wastewater '
     'treatment plants.'),
    ('Private Sector',
     'Private companies involved in water-related services, investors in water '
     'infrastructure, water-related industry.'),
    ('Non-Governmental Organizations (NGOs)',
     'Environmental groups working on water conservation, NGOs focused on '
     'community development and access to clean water.'),
    ('Research and Academic Institutions',
     'Universities and research institutions studying water issues, scientists '
     'and researchers specializing in hydrology and water management.'),
    ('International Organizations',
     'United Nations (UN) or other international organizations involved in '
     'global water issues.'),
    ('Other', ''),
)

STAKEHOLDER_GROUP_TYPE_VALUES = tuple(value for value, _ in STAKEHOLDER_GROUP_TYPES)


# ─── KPIs (descriptores para tabla / dashboard) ──────────────────────────
#
# Mapa estable id → metadata para alimentar tablas del overview admin.
# Cada KPI se almacena en el modelo con `kpi_<id>_active` (Boolean) y
# `num_<target_column>` (Integer) o `stakeholders_*` (Integer + sub-tot).

KPIS = OrderedDict([
    ('1a', {
        'title': 'Knowledge generation',
        'question': 'Did the activity generate (or improve) and/or disseminated knowledge products?',
        'target': 'How many knowledge products were generated?',
        'count_column': 'num_knowledge_products',
        'type_column': 'knowledge_product_type',  # CSV / JSON list
        'type_choices': KNOWLEDGE_PRODUCT_TYPES,
        'has_youth_female': False,
    }),
    ('1b', {
        'title': 'Knowledge improvement',
        'question': 'Did the activity generate scientific products?',
        'target': 'How many scientific products were generated?',
        'count_column': 'num_scientific_products',
        'type_column': 'scientific_product_type',
        'type_choices': SCIENTIFIC_PRODUCT_TYPES,
        'has_youth_female': False,
    }),
    ('2', {
        'title': 'Education material (stakeholder knowledge)',
        'question': 'Did the activity improve knowledge of stakeholders?',
        'target': 'How many key stakeholders improved their knowledge?',
        'count_column': 'stakeholders_knowledge',
        'type_column': 'knowledge_activity_type',
        'type_choices': KNOWLEDGE_ACTIVITY_TYPES,
        'has_youth_female': True,
    }),
    ('3', {
        'title': 'Curricula (training)',
        'question': 'Did the activity produce any training materials or training course?',
        'target': 'How many training materials/courses were produced?',
        'count_column': 'num_training_materials',
        'type_column': 'training_type',
        'type_choices': TRAINING_TYPES,
        'has_youth_female': False,
    }),
    ('4', {
        'title': 'Educational curricula',
        'question': 'Did the activity produce or revise educational curricula on sustainable water management?',
        'target': 'How many educational curricula were produced or revised?',
        'count_column': 'num_curricula',
        'type_column': None,
        'type_choices': None,
        'has_youth_female': False,
    }),
    ('5', {
        'title': 'Awareness training',
        'question': 'Did the activity contribute to awareness-raising of target stakeholders?',
        'target': 'How many key stakeholders have been reached by the awareness-raising activity?',
        'count_column': 'stakeholders_awareness',
        'type_column': None,
        'type_choices': None,
        'has_youth_female': True,
    }),
    ('6', {
        'title': 'Water cooperation (transboundary)',
        'question': 'Did the activity support Member States in improving their transboundary water systems management and governance?',
        'target': 'How many Member States were supported in improving their transboundary water systems?',
        'count_column': 'num_transboundary_ms',
        'type_column': None,
        'type_choices': None,
        'has_youth_female': False,
    }),
    ('8', {
        'title': 'Capacity support and strengthening',
        'question': 'Did the activity strengthen the capacity of certain Stakeholder Groups?',
        'target': 'Number of Stakeholder Groups that benefitted from the Activity?',
        'count_column': 'num_stakeholder_groups',
        'type_column': 'stakeholder_group_type',
        'type_choices': STAKEHOLDER_GROUP_TYPE_VALUES,
        'has_youth_female': False,
    }),
])


# ─── Member States (UNESCO IHP, 195) — ISO-3166 alpha-2 ─────────────────

MEMBER_STATES = (
    ('AF', 'Afghanistan'), ('AL', 'Albania'), ('DZ', 'Algeria'),
    ('AD', 'Andorra'), ('AO', 'Angola'), ('AG', 'Antigua and Barbuda'),
    ('AR', 'Argentina'), ('AM', 'Armenia'), ('AU', 'Australia'),
    ('AT', 'Austria'), ('AZ', 'Azerbaijan'), ('BS', 'Bahamas'),
    ('BH', 'Bahrain'), ('BD', 'Bangladesh'), ('BB', 'Barbados'),
    ('BY', 'Belarus'), ('BE', 'Belgium'), ('BZ', 'Belize'),
    ('BJ', 'Benin'), ('BT', 'Bhutan'), ('BO', 'Bolivia'),
    ('BA', 'Bosnia and Herzegovina'), ('BW', 'Botswana'), ('BR', 'Brazil'),
    ('BN', 'Brunei'), ('BG', 'Bulgaria'), ('BF', 'Burkina Faso'),
    ('BI', 'Burundi'), ('CV', 'Cabo Verde'), ('KH', 'Cambodia'),
    ('CM', 'Cameroon'), ('CA', 'Canada'), ('CF', 'Central African Republic'),
    ('TD', 'Chad'), ('CL', 'Chile'), ('CN', 'China'),
    ('CO', 'Colombia'), ('KM', 'Comoros'), ('CG', 'Congo'),
    ('CD', 'Congo (Democratic Republic)'), ('CR', 'Costa Rica'),
    ('CI', "Côte d'Ivoire"), ('HR', 'Croatia'), ('CU', 'Cuba'),
    ('CY', 'Cyprus'), ('CZ', 'Czechia'), ('DK', 'Denmark'),
    ('DJ', 'Djibouti'), ('DM', 'Dominica'), ('DO', 'Dominican Republic'),
    ('EC', 'Ecuador'), ('EG', 'Egypt'), ('SV', 'El Salvador'),
    ('GQ', 'Equatorial Guinea'), ('ER', 'Eritrea'), ('EE', 'Estonia'),
    ('SZ', 'Eswatini'), ('ET', 'Ethiopia'), ('FJ', 'Fiji'),
    ('FI', 'Finland'), ('FR', 'France'), ('GA', 'Gabon'),
    ('GM', 'Gambia'), ('GE', 'Georgia'), ('DE', 'Germany'),
    ('GH', 'Ghana'), ('GR', 'Greece'), ('GD', 'Grenada'),
    ('GT', 'Guatemala'), ('GN', 'Guinea'), ('GW', 'Guinea-Bissau'),
    ('GY', 'Guyana'), ('HT', 'Haiti'), ('HN', 'Honduras'),
    ('HU', 'Hungary'), ('IS', 'Iceland'), ('IN', 'India'),
    ('ID', 'Indonesia'), ('IR', 'Iran'), ('IQ', 'Iraq'),
    ('IE', 'Ireland'), ('IL', 'Israel'), ('IT', 'Italy'),
    ('JM', 'Jamaica'), ('JP', 'Japan'), ('JO', 'Jordan'),
    ('KZ', 'Kazakhstan'), ('KE', 'Kenya'), ('KI', 'Kiribati'),
    ('KP', 'Korea (North)'), ('KR', 'Korea (South)'), ('KW', 'Kuwait'),
    ('KG', 'Kyrgyzstan'), ('LA', 'Laos'), ('LV', 'Latvia'),
    ('LB', 'Lebanon'), ('LS', 'Lesotho'), ('LR', 'Liberia'),
    ('LY', 'Libya'), ('LI', 'Liechtenstein'), ('LT', 'Lithuania'),
    ('LU', 'Luxembourg'), ('MG', 'Madagascar'), ('MW', 'Malawi'),
    ('MY', 'Malaysia'), ('MV', 'Maldives'), ('ML', 'Mali'),
    ('MT', 'Malta'), ('MH', 'Marshall Islands'), ('MR', 'Mauritania'),
    ('MU', 'Mauritius'), ('MX', 'Mexico'), ('FM', 'Micronesia'),
    ('MD', 'Moldova'), ('MC', 'Monaco'), ('MN', 'Mongolia'),
    ('ME', 'Montenegro'), ('MA', 'Morocco'), ('MZ', 'Mozambique'),
    ('MM', 'Myanmar'), ('NA', 'Namibia'), ('NR', 'Nauru'),
    ('NP', 'Nepal'), ('NL', 'Netherlands'), ('NZ', 'New Zealand'),
    ('NI', 'Nicaragua'), ('NE', 'Niger'), ('NG', 'Nigeria'),
    ('MK', 'North Macedonia'), ('NO', 'Norway'), ('OM', 'Oman'),
    ('PK', 'Pakistan'), ('PW', 'Palau'), ('PS', 'Palestine'),
    ('PA', 'Panama'), ('PG', 'Papua New Guinea'), ('PY', 'Paraguay'),
    ('PE', 'Peru'), ('PH', 'Philippines'), ('PL', 'Poland'),
    ('PT', 'Portugal'), ('QA', 'Qatar'), ('RO', 'Romania'),
    ('RU', 'Russia'), ('RW', 'Rwanda'), ('KN', 'Saint Kitts and Nevis'),
    ('LC', 'Saint Lucia'), ('VC', 'Saint Vincent and the Grenadines'),
    ('WS', 'Samoa'), ('SM', 'San Marino'), ('ST', 'Sao Tome and Principe'),
    ('SA', 'Saudi Arabia'), ('SN', 'Senegal'), ('RS', 'Serbia'),
    ('SC', 'Seychelles'), ('SL', 'Sierra Leone'), ('SG', 'Singapore'),
    ('SK', 'Slovakia'), ('SI', 'Slovenia'), ('SB', 'Solomon Islands'),
    ('SO', 'Somalia'), ('ZA', 'South Africa'), ('SS', 'South Sudan'),
    ('ES', 'Spain'), ('LK', 'Sri Lanka'), ('SD', 'Sudan'),
    ('SR', 'Suriname'), ('SE', 'Sweden'), ('CH', 'Switzerland'),
    ('SY', 'Syria'), ('TJ', 'Tajikistan'), ('TZ', 'Tanzania'),
    ('TH', 'Thailand'), ('TL', 'Timor-Leste'), ('TG', 'Togo'),
    ('TO', 'Tonga'), ('TT', 'Trinidad and Tobago'), ('TN', 'Tunisia'),
    ('TR', 'Turkey'), ('TM', 'Turkmenistan'), ('TV', 'Tuvalu'),
    ('UG', 'Uganda'), ('UA', 'Ukraine'), ('AE', 'United Arab Emirates'),
    ('GB', 'United Kingdom'), ('US', 'United States'), ('UY', 'Uruguay'),
    ('UZ', 'Uzbekistan'), ('VU', 'Vanuatu'), ('VA', 'Vatican City'),
    ('VE', 'Venezuela'), ('VN', 'Viet Nam'), ('YE', 'Yemen'),
    ('ZM', 'Zambia'), ('ZW', 'Zimbabwe'),
)

MEMBER_STATE_CODES = frozenset(code for code, _ in MEMBER_STATES)


# ─── Helpers de validación ───────────────────────────────────────────────


def normalize_bool(value):
    u"""Acepta 'yes'/'no', True/False, 1/0, 'true'/'false'. Devuelve bool.

    None → False; cualquier truthy desconocido → False (estricto).
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    if s in ('yes', 'true', '1', 'y', 'on'):
        return True
    if s in ('no', 'false', '0', 'n', 'off', ''):
        return False
    return False


def is_valid_priority_area(value):
    return value in PRIORITY_AREAS


def is_valid_biennium(value):
    return value in BIENNIA


def is_valid_region(value):
    return value in REGIONS


def is_valid_flagship(value):
    return value in FLAGSHIPS


def is_valid_cross_cutting_wg(value):
    return value in CROSS_CUTTING_WGS


def is_valid_institution_type(value):
    return value in LEAD_INSTITUTION_TYPES


def is_valid_output_for_pa(pa, code):
    u"""True si `code` es un Output válido bajo la PA dada."""
    return code in output_codes_for(pa)


def is_valid_member_state(value):
    u"""Acepta ISO-2 (preferido) o nombre completo."""
    if value in MEMBER_STATE_CODES:
        return True
    return value in {name for _, name in MEMBER_STATES}


def filter_valid(values, allowed):
    u"""Devuelve sólo los items de `values` que estén en `allowed`.

    Útil para sanear multi-selects antes de persistir como JSON.
    """
    if not values:
        return []
    allowed_set = set(allowed)
    return [v for v in values if v in allowed_set]
