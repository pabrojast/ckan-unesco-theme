# -*- coding: utf-8 -*-
"""Plantilla XLSX y validación sin acceso a CKAN ni escrituras de datos."""
import datetime
import io
import json
import zipfile
from xml.etree.ElementTree import ParseError

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font
from ckanext.theme_ejemplo import ihpix_forms as F, ihpix_constants as C
from ckanext.theme_ejemplo import ihpix_relations as R, ihpix_links as L

VERSION = 'IHP-IX/1'
MAX_ROWS = 2000
FIELDS = ['row_ref'] + list(dict.fromkeys(
    ['title', 'priority_area'] + list(F.TEXT_FIELDS) + list(F.INT_FIELDS) +
    list(F.BOOL_FIELDS) + list(F.FORM_DATE_FIELDS) + list(F.MULTI_FORM_FIELDS)))
SHEETS = {
    'Activities': FIELDS,
    'Contributions': ['row_ref', 'priority_area', 'output', 'key_activity_code'],
    'Synergies': ['row_ref', 'priority_area', 'output', 'key_activity_code'],
    'Supporters': ['row_ref', 'country', 'types'],
    'Partners': ['row_ref', 'organization_id'],
    'Resources': ['row_ref', 'link_type', 'target_kind', 'target_id', 'title', 'url', 'description', 'event_date'],
}


def template(organizations=()):
    workbook = Workbook()
    instructions = workbook.active
    instructions.title = 'Instructions'
    instructions.append(['Template version', VERSION])
    for text in (
        'One activity per row. row_ref must be unique (e.g. A001).',
        'Use row_ref on relation sheets to link multiple entries to an activity.',
        'Use yes/no for gates. Empty answers remain unanswered.',
        'Separate multiple choices or support types with semicolons.',
        'Use ISO dates YYYY-MM-DD and nonnegative whole numbers up to 2147483647.',
        'The first Contributions entry is the primary classification. Synergies do not increase contribution counts.',
        'Support types: financial;in_kind;hosting. Country codes are in Countries.',
        'Organization identifiers are in Organizations. External institutions and partners use free text.',
        'Resources can reference an existing item or an external HTTP(S) URL. Upload binary files after importing drafts.',
        'Upload, validate and preview before confirming. Import creates drafts only. Repeated confirmation is idempotent.',
        'Incomplete submission fields are warnings; malformed values prevent import.',
    ):
        instructions.append([text])
    for name, headers in SHEETS.items():
        workbook.create_sheet(name).append(headers)
    vocabulary = workbook.create_sheet('Catalogs')
    vocabulary.append(['field', 'value', 'label'])
    for field, choices in list(F.MULTI_FIELDS.items()) + [
        ('priority_area', C.PRIORITY_AREAS), ('biennium', C.BIENNIA),
        ('institution_type', C.LEAD_INSTITUTION_TYPES)]:
        for choice in choices or ():
            vocabulary.append([field, choice, C.flagship_label(choice) if field == 'flagships' else choice])
    taxonomy = workbook.create_sheet('Taxonomy')
    taxonomy.append(['priority_area', 'output', 'output_title', 'key_activity_code', 'key_activity_title'])
    for output, entries in C.load_key_activities().items():
        for item in entries:
            taxonomy.append([C.priority_area_for_output(output), output, C.output_title(output), item['code'], item['title']])
    countries = workbook.create_sheet('Countries')
    countries.append(['iso2', 'name', 'electoral_group', 'regions'])
    for country in R.countries():
        countries.append([country['iso2'], country['country_title_en'], country['electoral_group'], ';'.join(country['regional_group'] or [])])
    orgs = workbook.create_sheet('Organizations')
    orgs.append(['organization_id', 'title'])
    for org in organizations:
        orgs.append([org['id'], org.get('title') or org.get('name')])
    for sheet in workbook:
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for col in sheet.columns:
            sheet.column_dimensions[col[0].column_letter].width = 28
        for row in sheet:
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = 's'  # Una etiqueta nunca debe ejecutarse como fórmula.
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def parse(raw, defaults=None):
    try:
        return _parse(raw, defaults)
    except (zipfile.BadZipFile, KeyError, OSError, ParseError, SyntaxError,
            RuntimeError, NotImplementedError) as exc:
        # Las hojas se leen de forma diferida; también pueden fallar al iterar.
        raise ValueError('Upload a valid XLSX workbook') from exc


def _parse(raw, defaults=None):
    errors, warnings, activities = [], [], {}
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError('Workbook exceeds 5 MB')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(info.file_size for info in archive.infolist()) > 30 * 1024 * 1024:
                raise ValueError('Expanded workbook exceeds 30 MB')
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
    except (zipfile.BadZipFile, KeyError, OSError, ParseError, SyntaxError,
            RuntimeError, NotImplementedError) as exc:
        raise ValueError('Upload a valid XLSX workbook') from exc
    if 'Instructions' not in workbook or workbook['Instructions']['B1'].value != VERSION:
        raise ValueError('Unsupported template version; download the current template')
    def error(sheet, row, field, message, target=errors):
        headers = SHEETS[sheet]
        from openpyxl.utils import get_column_letter
        cell = get_column_letter(headers.index(field) + 1) + str(row) if field in headers else str(row)
        target.append({'sheet': sheet, 'row': row, 'cell': cell, 'field': field, 'message': message})
    records = {}
    try:
        for name, headers in SHEETS.items():
            if name not in workbook:
                raise ValueError('Missing worksheet: ' + name)
            sheet = workbook[name]
            if (sheet.max_row or 0) > MAX_ROWS + 1 or (sheet.max_column or 0) > len(headers):
                raise ValueError('Worksheet dimensions exceed template limits: ' + name)
            rows = sheet.iter_rows()
            first = next(rows, ())
            if [c.value for c in first] != headers:
                raise ValueError('Column headers do not match template: ' + name)
            records[name] = []
            for number, cells in enumerate(rows, 2):
                if not any(c.value is not None for c in cells):
                    continue
                values = {}
                for field, cell in zip(headers, cells):
                    if cell.data_type == 'f':
                        error(name, number, field, 'Formulas are not allowed; paste values')
                    value = cell.value
                    if isinstance(value, datetime.datetime):
                        value = value.date().isoformat()
                    elif isinstance(value, datetime.date):
                        value = value.isoformat()
                    elif isinstance(value, float) and value.is_integer():
                        value = int(value)
                    values[field] = '' if value is None else str(value).strip()
                records[name].append((number, values))
        for number, data in records['Activities']:
            ref = data.pop('row_ref')
            if not ref or ref in activities:
                error('Activities', number, 'row_ref', 'Use a unique, nonempty row reference')
                continue
            for field, value in (defaults or {}).items():
                if field in ('institution', 'institution_org_id'):
                    continue
                if not data.get(field):
                    data[field] = value
            # No atribuir una institución externa al perfil por completar sólo el ID.
            if not data.get('institution') and not data.get('institution_org_id'):
                for field in ('institution', 'institution_org_id'):
                    data[field] = (defaults or {}).get(field, '')
            for field in F.MULTI_FORM_FIELDS:
                data[field] = [v.strip() for v in data[field].split(';') if v.strip()]
            activities[ref] = {'row': number, 'data': data, 'resource_rows': [], 'partner_rows': []}
        for name, field in [('Contributions','contributions_json'), ('Synergies','synergies_json'),
                            ('Supporters','supporters_json'), ('Partners','partner_org_ids'), ('Resources','links_json')]:
            for number, entry in records[name]:
                ref = entry.pop('row_ref')
                if ref not in activities:
                    error(name, number, 'row_ref', 'No matching activity row')
                    continue
                if name == 'Supporters':
                    entry['types'] = [v.strip() for v in entry['types'].split(';') if v.strip()]
                if name == 'Partners':
                    activities[ref]['partner_rows'].append(number)
                    entry = entry['organization_id']
                if name == 'Resources':
                    activities[ref]['resource_rows'].append(number)
                    try:
                        L.validate_link(entry)
                    except L.LinkValidationError as exc:
                        for key, message in exc.errors.items():
                            error(name, number, key, message)
                else:
                    _, invalid = R.validate({field: [entry]})
                    invalid_field = 'row_ref'
                    if name in ('Contributions', 'Synergies'):
                        invalid_field = ('priority_area' if entry['priority_area'] not in C.PRIORITY_AREAS else
                            'output' if not C.is_valid_output_for_pa(entry['priority_area'], entry['output']) else 'key_activity_code')
                    elif name == 'Supporters':
                        invalid_field = 'country' if not R.country_metadata(entry['country']) else 'types'
                    elif name == 'Partners':
                        invalid_field = 'organization_id'
                    for message in invalid.values():
                        error(name, number, invalid_field, message)
                activities[ref]['data'].setdefault(field, []).append(entry)
        for ref, item in activities.items():
            data, row = item['data'], item['row']
            try:
                F.validate_report_payload(data, True)
            except F.ReportValidationError as exc:
                for key, message in exc.errors.items():
                    error('Activities', row, key, message)
            try:
                F.validate_report_payload(data, False)
            except F.ReportValidationError as exc:
                for key, message in exc.errors.items():
                    error('Activities', row, key, message, warnings)
            data['save_as_draft'] = '1'
        if not activities:
            errors.append({'sheet': 'Activities', 'row': 2, 'cell': 'A2', 'field': 'row_ref', 'message': 'Add at least one activity'})
        return {'version': VERSION, 'rows': [{'ref': ref, **item} for ref, item in activities.items()],
                'errors': errors, 'warnings': warnings}
    finally:
        workbook.close()
