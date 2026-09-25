# -*- coding: utf-8 -*-
u"""Validación y normalización del formulario de reporte IHP-IX (PDF 2026).

Módulo puro (sin dependencias de CKAN) para poder testearlo con pytest sin
levantar la pila completa. Lo consumen `actions.ihpix_report_submit` y
`actions.ihpix_report_update`, que sólo traducen `ReportValidationError`
a `toolkit.ValidationError`.

Contrato:
- `validate_report_payload(data_dict, is_draft)` recibe el payload
  *completo* del formulario (todos los campos, tal como los envía
  `/ihpix/report`) y devuelve un dict cuyas claves son exactamente
  columnas de `IhpixActivity`, ya saneadas: listas → JSON, 'yes'/'no' →
  bool, fechas → `datetime.date`, hijos de un gate en "no" reseteados.
- `activity_to_form_dict(activity_dict)` hace el camino inverso para
  rellenar el formulario en modo edición (bool → 'yes'/'no', JSON → lista).
"""
from __future__ import unicode_literals

import datetime
import json
import re
from collections import OrderedDict

from ckanext.theme_ejemplo import ihpix_constants as C

# Longitud máxima de los textos cortos del PDF (descripción y outcomes)
SHORT_TEXT_MAX = 250

# Longitud máxima de los demás textos libres (el formulario pone el mismo
# `maxlength`; aquí se refuerza en servidor)
LONG_TEXT_MAX = OrderedDict([
    ('title', 300),
    ('partners', 500),
    ('key_activity', 1000),
    ('synergies', 1500),
    ('additional_notes', 3000),
    ('institution_type_other', 150),
    ('knowledge_product_type_other', 150),
    ('knowledge_activity_type_other', 150),
    ('stakeholder_group_type_other', 150),
    ('stakeholder_group_name', 200),
])

# Estados en los que el propio reportante puede editar y reenviar
OWNER_EDITABLE_STATUSES = ('draft', 'rejected')

# Mensajes de validación (inglés). Las acciones los traducen con
# `toolkit._()` a partir de `ReportValidationError.details`; los literales
# están también en `ihpix_i18n_strings.py` para que Babel los extraiga.
MESSAGES = OrderedDict([
    ('title_required', 'Title is required'),
    ('focal_point_required', 'Focal point name is required'),
    ('contact_email_required', 'Focal point email is required'),
    ('institution_type_required', 'Lead Implementing Institution category is required'),
    ('institution_required', 'Institution name is required'),
    ('biennium_required', 'Biennium is required'),
    ('max_length', '{field} must be {max} characters or fewer'),
    ('choice_invalid', 'Must be one of: {choices}'),
    ('institution_type_invalid', 'Invalid institution type'),
    ('output_not_in_pa', 'Output {output} does not belong to {pa}'),
    ('email_invalid', 'Invalid email address'),
    ('url_invalid', 'Link must be a full URL starting with http:// or https://'),
    ('date_invalid', 'Invalid date format. Use YYYY-MM-DD'),
    ('end_before_start', 'The completion date cannot be earlier than the start date'),
    ('part_exceeds_total', 'Cannot exceed the total number of stakeholders'),
])

# Campos obligatorios sólo al enviar a revisión (un borrador sólo exige título)
# → clave del mensaje en MESSAGES
REQUIRED_FOR_SUBMISSION = OrderedDict([
    ('focal_point_name', 'focal_point_required'),
    ('contact_email', 'contact_email_required'),
    ('institution_type', 'institution_type_required'),
    ('institution', 'institution_required'),
    ('biennium', 'biennium_required'),
])

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
URL_RE = re.compile(r'^https?://\S+$', re.I)

# (parte, total, gate) para las reglas jóvenes/mujeres ≤ total de los KPI 2 y 5
STAKEHOLDER_RATIOS = (
    ('stakeholders_knowledge_youth', 'stakeholders_knowledge', 'kpi_2_active'),
    ('stakeholders_knowledge_female', 'stakeholders_knowledge', 'kpi_2_active'),
    ('stakeholders_awareness_youth', 'stakeholders_awareness', 'kpi_5_active'),
    ('stakeholders_awareness_female', 'stakeholders_awareness', 'kpi_5_active'),
)

# Campos de texto libre (se guardan con strip())
TEXT_FIELDS = (
    'description', 'output', 'country', 'institution', 'link', 'image_url',
    'outcomes', 'contact_email',
    'focal_point_name', 'institution_type', 'institution_type_other',
    'partners', 'biennium', 'supporting_member_state',
    'key_activity', 'synergies',
    'knowledge_product_type_other', 'knowledge_activity_type_other',
    'stakeholder_group_type_other', 'stakeholder_group_name',
    'additional_notes',
)

# Multi-selects: nombre → vocabulario permitido (None = sin filtro)
MULTI_FIELDS = OrderedDict([
    ('flagships', C.FLAGSHIPS),
    ('cross_cutting_wg', C.CROSS_CUTTING_WGS),
    ('regions', C.REGIONS),
    ('member_states', None),
    ('knowledge_product_type', C.KNOWLEDGE_PRODUCT_TYPES),
    ('scientific_product_type', C.SCIENTIFIC_PRODUCT_TYPES),
    ('knowledge_activity_type', C.KNOWLEDGE_ACTIVITY_TYPES),
    ('training_type', C.TRAINING_TYPES),
    ('stakeholder_group_type', C.STAKEHOLDER_GROUP_TYPE_VALUES),
])

INT_FIELDS = (
    'num_knowledge_products', 'num_scientific_products',
    'num_training_materials', 'num_curricula', 'num_transboundary_ms',
    'num_stakeholder_groups',
    'stakeholders_knowledge', 'stakeholders_knowledge_youth',
    'stakeholders_knowledge_female',
    'stakeholders_awareness', 'stakeholders_awareness_youth',
    'stakeholders_awareness_female',
)

# Gates Y/N del PDF: se guardan como booleanos explícitos
BOOL_FIELDS = (
    'unesco_secretariat_participation', 'has_member_state_support',
    'has_flagship', 'has_synergies', 'regions_benefit',
    'kpi_1a_active', 'kpi_1b_active', 'kpi_2_active', 'kpi_3_active',
    'kpi_4_active', 'kpi_5_active', 'kpi_6_active', 'kpi_8_active',
)

# `reported_date` la fija el servidor al enviar a revisión; el formulario
# sólo edita las fechas de la actividad.
DATE_FIELDS = ('reported_date', 'start_date', 'end_date')
FORM_DATE_FIELDS = ('start_date', 'end_date')

# Gate → valores a los que se resetean sus hijos cuando el gate es False.
# Preserva la semántica del PDF: "no aplica" ≠ "no contestado".
GATE_RESETS = OrderedDict([
    ('kpi_1a_active', {'num_knowledge_products': 0,
                       'knowledge_product_type': ''}),
    ('kpi_1b_active', {'num_scientific_products': 0,
                       'scientific_product_type': ''}),
    ('kpi_2_active', {'stakeholders_knowledge': 0,
                      'stakeholders_knowledge_youth': 0,
                      'stakeholders_knowledge_female': 0}),
    ('kpi_3_active', {'num_training_materials': 0, 'training_type': ''}),
    ('kpi_4_active', {'num_curricula': 0}),
    ('kpi_5_active', {'stakeholders_awareness': 0,
                      'stakeholders_awareness_youth': 0,
                      'stakeholders_awareness_female': 0}),
    ('kpi_6_active', {'num_transboundary_ms': 0}),
    ('kpi_8_active', {'num_stakeholder_groups': 0,
                      'stakeholder_group_type': ''}),
    ('has_member_state_support', {'supporting_member_state': ''}),
    ('has_flagship', {'flagships': ''}),
    ('has_synergies', {'synergies': ''}),
    ('regions_benefit', {'regions': '', 'member_states': ''}),
])

# Nombres de campo que el formulario envía como valor único / múltiple.
# Los usa el controller para extraer `request.form` sin duplicar listas.
SINGLE_FORM_FIELDS = (
    ('title', 'priority_area', 'contact_name', 'save_as_draft')
    + TEXT_FIELDS + INT_FIELDS + BOOL_FIELDS + FORM_DATE_FIELDS
)
MULTI_FORM_FIELDS = tuple(MULTI_FIELDS.keys())


class ReportValidationError(Exception):
    u"""Errores de validación del reporte.

    `.errors` es {campo: mensaje en inglés} (compatibilidad) y `.details`
    es {campo: (clave de MESSAGES, params)} para traducir en la acción.
    """

    def __init__(self, errors, details=None):
        self.errors = dict(errors)
        self.details = dict(details or {})
        super(ReportValidationError, self).__init__(
            json.dumps(self.errors, sort_keys=True))


def _text(data_dict, field):
    val = data_dict.get(field)
    if val is None:
        return ''
    return str(val).strip()


def as_list(value):
    u"""Acepta list/tuple, string JSON o CSV. Devuelve strings no vacíos."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    s = str(value).strip()
    if not s:
        return []
    if s.startswith('['):
        try:
            return [str(v).strip() for v in json.loads(s) if str(v).strip()]
        except (ValueError, TypeError):
            pass
    return [p.strip() for p in s.split(',') if p.strip()]


def _json_list(value, allowed=None):
    items = as_list(value)
    if allowed is not None:
        items = C.filter_valid(items, allowed)
    return json.dumps(items) if items else ''


def _int(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _date(value):
    u"""'YYYY-MM-DD' → date; ''/None → None; formato inválido → ValueError."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    return datetime.datetime.strptime(s, '%Y-%m-%d').date()


def validate_report_payload(data_dict, is_draft):
    u"""Valida y normaliza el payload completo del formulario.

    Devuelve un dict {columna: valor} listo para `setattr` sobre
    `IhpixActivity`. Lanza `ReportValidationError` con *todos* los errores
    encontrados (no sólo el primero) para que la UI los resalte a la vez.
    """
    errors = OrderedDict()
    details = OrderedDict()

    def add(fname, key, **params):
        if fname in errors:
            return
        errors[fname] = MESSAGES[key].format(**params)
        details[fname] = (key, params)

    title = _text(data_dict, 'title')
    if not title:
        add('title', 'title_required')

    # El maxlength del cliente es saltable; se refuerza en servidor
    for fname in ('description', 'outcomes'):
        if len(_text(data_dict, fname)) > SHORT_TEXT_MAX:
            add(fname, 'max_length', field=fname, max=SHORT_TEXT_MAX)
    for fname, max_len in LONG_TEXT_MAX.items():
        if len(_text(data_dict, fname)) > max_len:
            add(fname, 'max_length', field=fname, max=max_len)

    priority_area = _text(data_dict, 'priority_area')
    output = _text(data_dict, 'output')
    biennium = _text(data_dict, 'biennium')
    inst_type = _text(data_dict, 'institution_type')
    contact_email = _text(data_dict, 'contact_email')
    link = _text(data_dict, 'link')

    if not is_draft:
        for fname, key in REQUIRED_FOR_SUBMISSION.items():
            if not _text(data_dict, fname):
                add(fname, key)
        if priority_area not in C.PRIORITY_AREAS:
            add('priority_area', 'choice_invalid',
                choices=', '.join(C.PRIORITY_AREAS))
        if contact_email and not EMAIL_RE.match(contact_email):
            add('contact_email', 'email_invalid')

    # Vocabularios: se validan también en borrador si el valor viene informado,
    # para no persistir nunca un valor fuera de la taxonomía oficial.
    if priority_area and priority_area not in C.PRIORITY_AREAS:
        add('priority_area', 'choice_invalid', choices=', '.join(C.PRIORITY_AREAS))
    if biennium and not C.is_valid_biennium(biennium):
        add('biennium', 'choice_invalid', choices=', '.join(C.BIENNIA))
    if inst_type and not C.is_valid_institution_type(inst_type):
        add('institution_type', 'institution_type_invalid')
    if (output and priority_area in C.PRIORITY_AREAS
            and not C.is_valid_output_for_pa(priority_area, output)):
        add('output', 'output_not_in_pa', output=output, pa=priority_area)
    if link and not URL_RE.match(link):
        add('link', 'url_invalid')

    # Las fechas sólo se tocan si vienen en el payload: así una edición
    # parcial (API) o el formulario (que no envía reported_date) no las borra.
    dates = {}
    for field in DATE_FIELDS:
        if field not in data_dict:
            continue
        try:
            dates[field] = _date(data_dict.get(field))
        except (ValueError, TypeError):
            add(field, 'date_invalid')
    if dates.get('start_date') and dates.get('end_date') \
            and dates['end_date'] < dates['start_date']:
        add('end_date', 'end_before_start')

    # Jóvenes / mujeres no pueden superar el total (solo con el gate activo)
    for part, total, gate in STAKEHOLDER_RATIOS:
        if not C.normalize_bool(data_dict.get(gate)):
            continue
        if _int(data_dict.get(part)) > _int(data_dict.get(total)):
            add(part, 'part_exceeds_total')

    if errors:
        raise ReportValidationError(errors, details)

    values = {
        'title': title,
        # Un borrador puede no tener PA todavía; PA1 mantiene el NOT NULL
        'priority_area': priority_area or 'PA1',
    }
    for field in TEXT_FIELDS:
        values[field] = _text(data_dict, field)
    values['contact_name'] = (_text(data_dict, 'contact_name')
                              or values['focal_point_name'])
    for field, allowed in MULTI_FIELDS.items():
        values[field] = _json_list(data_dict.get(field), allowed)
    for field in INT_FIELDS:
        values[field] = _int(data_dict.get(field))
    for field in BOOL_FIELDS:
        values[field] = C.normalize_bool(data_dict.get(field))
    values.update(dates)

    # Gate en "no" → sus hijos vuelven al valor neutro
    for gate, resets in GATE_RESETS.items():
        if not values[gate]:
            values.update(resets)

    return values


def activity_to_form_dict(activity_dict):
    u"""Convierte `IhpixActivity.as_dict()` al formato que consume el form.

    - booleanos → 'yes'/'no' (los gates son radios con esos valores)
    - listas JSON → list (checkboxes)
    - None → '' (inputs vacíos)
    """
    form = {}
    for key, value in activity_dict.items():
        if key in BOOL_FIELDS:
            form[key] = 'yes' if value else 'no'
        elif key in MULTI_FIELDS:
            form[key] = as_list(value)
        elif value is None:
            form[key] = ''
        else:
            form[key] = value
    return form
