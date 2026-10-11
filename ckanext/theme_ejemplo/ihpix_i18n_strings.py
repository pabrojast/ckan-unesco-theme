# -*- coding: utf-8 -*-
u"""Cadenas de las taxonomías IHP-IX para que Babel las extraiga.

Los valores de `ihpix_constants` (regiones, tipos de institución, KPIs…) se
pintan en los templates con `h.ihpix_t(valor)` en tiempo de ejecución. Como
Babel sólo extrae literales, aquí se repiten envueltos en `_()` (un no-op)
para que aparezcan en el `.pot` y puedan traducirse en los `.po`.

No importar desde código de producción: no hace nada en runtime.
"""
from __future__ import unicode_literals


def _(s):
    return s


PRIORITY_AREA_TITLES = [
    _('Scientific Research and Innovation'),
    _('Water Education in the Fourth Industrial Revolution including Sustainability'),
    _('Bridging the Data-Knowledge Gap'),
    _('Integrated Water Resources Management under Conditions of Global Change'),
    _('Water Governance based on Science for Mitigation, Adaptation, and Resilience'),
]

REGIONS = [
    _('Global'),
    _('Africa'),
    _('Arab States'),
    _('Asia and the Pacific'),
    _('Eastern Europe'),
    _('Europe and North America'),
    _('Latin America and the Caribbean'),
]

CROSS_CUTTING_WGS = [
    _('Hydrological Systems, Rivers, Climate Risk and Water-Food-Energy Nexus'),
    _('Ecohydrology and Water Quality'),
    _('Groundwater and Human Settlements'),
]

LEAD_INSTITUTION_TYPES = [
    _('UNESCO IHP Secretariat'),
    _('UNESCO Field Office'),
    _('IHP National Committee'),
    _('UNESCO Category I Center'),
    _('UNESCO Category II Center'),
    _('UNESCO Chair or UNITWIN'),
    _('Non-Governmental Organization'),
    _('Governmental Organization'),
    _('University'),
    _('Private Partner'),
    _('Research Institution'),
    _('Other'),
]

KNOWLEDGE_PRODUCT_TYPES = [
    _('Book'), _('Report or paper'), _('Assessment'),
    _('Statistic or data source'), _('Tool'), _('Methodology'),
    _('Website'), _('Brochure'),
]

SCIENTIFIC_PRODUCT_TYPES = [
    _('Peer-reviewed articles'), _('Patents'),
    _('Scientific journal editions'), _('Scientific conference proceedings'),
]

KNOWLEDGE_ACTIVITY_TYPES = [
    _('Workshop or physical/online training course'),
    _('Seminar or online webinar'),
    _('International Conference'),
    _('Conference session or roundtable discussion'),
]

TRAINING_TYPES = [
    _('Physical training material (hard copy)'),
    _('Physical training material (soft copy)'),
    _('Physical training course'),
    _('Online training course'),
    _('Presentation'), _('Lecture'), _('Training video'), _('Manual'),
    _('Module'), _('Handout'), _('Textbook'),
]

TRAINING_TYPE_GROUPS = [
    _('Training materials'), _('Training courses'),
]

FLAGSHIP_LABELS = [
    _('FRIEND-Water'), _('LaSII'),
]

STAKEHOLDER_GROUP_TYPES = [
    _('River Basin Organizations or Regional Water Management Bodies'),
    _('Community Groups'),
    _('Government Agencies'),
    _('Water Utilities'),
    _('Private Sector'),
    _('Non-Governmental Organizations (NGOs)'),
    _('Research and Academic Institutions'),
    _('International Organizations'),
]

KPI_TITLES = [
    _('Knowledge generation'),
    _('Scientific products'),
    _('Knowledge improvement'),
    _('Training materials'),
    _('Educational curricula'),
    _('Awareness raising'),
    _('Transboundary water systems'),
    _('Capacity support and strengthening'),
]

# Preguntas de cabecera del dashboard de progreso (página oficial Power BI)
KPI_QUESTIONS = [
    _('How many knowledge/scientific products did the activities produce?'),
    _('How many key stakeholders had their knowledge improved?'),
    _('How much training material did the activities produce?'),
    _('How many curricula were produced/revised to include sustainable water management?'),
    _('How many key stakeholders have been informed?'),
    _('What number of member states were supported in improving their transboundary water systems management and governance?'),
    _('What number of member states and stakeholder groups have been supported/strengthened in their capacity?'),
]

# Preguntas Sí/No de cada KPI (guía oficial)
KPI_GATE_QUESTIONS = [
    _('Did the activity generate (or improve) and/or disseminate knowledge products?'),
    _('Did the activity generate scientific products?'),
    _('Did the activity improve knowledge of stakeholders?'),
    _('Did the activity produce any training materials or was a training course implemented?'),
    _('Did the activity produce or revise educational curricula on sustainable water management?'),
    _('Did the activity contribute to awareness-raising of target stakeholders?'),
    _('Did the activity support Member States in improving their transboundary water systems (surface water and groundwater) management and governance?'),
    _('Did the activity strengthen the capacity of certain Stakeholder Groups (river basin groups, communities, sectors)?'),
]

KPI_TARGETS = [
    _('How many knowledge products were generated?'),
    _('How many scientific products were generated?'),
    _('How many key stakeholders improved their knowledge as a result of the activity?'),
    _('How many training materials were produced or how many training courses were implemented?'),
    _('How many educational curricula were produced or revised?'),
    _('How many key stakeholders have been reached by the awareness-raising activity?'),
    _('How many Member States were supported in improving their transboundary water systems?'),
    _('What is the number of Stakeholder Groups that benefitted from the Activity?'),
]

# Etiquetas de dimensión y buckets del dashboard de progreso
PROGRESS_LABELS = [
    _('Overall'), _('Priority Area'), _('Output'), _('Key Activity'),
    _('Flagship Initiative'), _('Cross-cutting Working Group'),
    _('Unspecified'),
]

LINK_TYPE_LABELS = [
    _('Publication'), _('Webinar'), _('Event'), _('Dataset'),
    _('Output data'), _('Other link'),
]

REPORT_STATUS_LABELS = [
    _('Draft'), _('Pending review'), _('Published'), _('Needs changes'),
]

# Mensajes de validación de ihpix_forms.MESSAGES e ihpix_links.MESSAGES
VALIDATION_MESSAGES = [
    _('Title is required'),
    _('Focal point name is required'),
    _('Focal point email is required'),
    _('Lead Implementing Institution category is required'),
    _('Institution name is required'),
    _('Biennium is required'),
    _('{field} must be {max} characters or fewer'),
    _('Must be one of: {choices}'),
    _('Invalid institution type'),
    _('Output {output} does not belong to {pa}'),
    _('Invalid email address'),
    _('Link must be a full URL starting with http:// or https://'),
    _('Invalid date format. Use YYYY-MM-DD'),
    _('The completion date cannot be earlier than the start date'),
    _('Cannot exceed the total number of stakeholders'),
    _('Description is required'),
    _('Key outputs and outcomes are required'),
    _('Priority Area is required'),
    _('Output is required'),
    _('Please answer yes or no'),
    _('Key activity {code} does not belong to output {output}'),
    _('Invalid JSON'),
    _('Expected a list of links'),
    _('{link_type} cannot point to a {target_kind}'),
    _('URL is required'),
    _('URL must start with http:// or https://'),
    _('URL must be absolute (http/https) or site-relative'),
    _('URL is too long'),
    _('target_id is required for a {target_kind}'),
    # ihpix_publications.MESSAGES (modal "Upload a publication")
    _('Choose the organization that will own the publication'),
    _('You cannot create publications in this organization'),
    _('Invalid document type'),
    _('Publication year must be between {min} and {max}'),
    _('Enter a valid DOI (e.g. 10.1000/xyz123)'),
    _('Upload a file or enter the URL of the publication'),
    _('The URL must start with http:// or https://'),
    _('This file type is not allowed ({ext})'),
    _('The file is too large (max. {max} MB)'),
    _('A contact email is required (your account has no email)'),
    _('At most {max} authors'),
    _('At most {max} keywords'),
]

# ihpix_links.TYPE_LABELS / ihpix_workspaces.CONTRIBUTION_KINDS nuevos
LINK_AND_LEDGER_LABELS = [
    _('Course'),
    _('Publication uploaded to IHP-WINS'),
    _('Course proposed for the catalogue'),
]
