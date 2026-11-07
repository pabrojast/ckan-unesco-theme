"""Reglas y libros de planificación, sin dependencias de CKAN."""
import hashlib
import io
import json
import re
import uuid
import zipfile
from . import ihpix_constants as C

BIENNIA = ('2022-2023', '2024-2025', '2026-2027', '2028-2029')
EXECUTION = ('planned', 'ongoing', 'completed', 'cancelled')
REVIEW = ('draft', 'submitted', 'approved', 'returned')
DOC_CATEGORIES = ('strategy', 'planning', 'presentation', 'report', 'other')
DOC_EXTENSIONS = ('pdf', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'doc', 'docx', 'odt', 'ods', 'txt', 'png', 'jpg', 'jpeg', 'zip')
# Matriz de la diapositiva 6, OETWG 4 IWRM_23Feb.pptx; las identidades no dependen del orden.
CTWG_OUTPUTS = {
 'hydrological-systems': '1.1 1.3 1.6 1.7 1.10 2.1 2.2 2.3 2.4 2.5 2.6 3.1 3.2 3.3 3.4 4.1 4.2 4.4 4.7 4.8 4.9 5.1 5.2 5.3 5.4 5.5',
 'ecohydrology-water-quality': '1.2 1.8 1.10 2.1 2.2 2.3 2.4 2.5 2.6 3.2 3.3 3.4 4.1 4.2 4.3 4.4 4.5 4.6 4.8 4.9 5.1 5.3 5.4 5.5',
 'groundwater-human-settlements': '1.3 1.4 1.5 1.7 1.9 1.10 2.1 2.2 2.3 2.4 2.5 2.6 3.3 4.1 4.2 4.3 4.7 4.8 4.9 5.1 5.2 5.3 5.4 5.5',
}


def seeds():
    result = [dict(id='oetwg-'+pa[-1], kind='oetwg', title='OETWG '+pa[-1]+' · '+title,
                   outputs=[code for code, _ in C.OUTPUTS[pa]], source='IHP-IX Strategic Plan')
              for pa, title in C.PRIORITY_AREAS.items()]
    for slug, title in zip(CTWG_OUTPUTS, C.CROSS_CUTTING_WGS):
        result.append(dict(id='ctwg-'+slug, kind='ctwg', title=title,
                           outputs=CTWG_OUTPUTS[slug].split(), source='OETWG 4 IWRM_23Feb.pptx · slide 6'))
    return result


class Invalid(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(str(errors))


def unpack(value, default=None):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or 'null') or default
    except (ValueError, TypeError):
        return default


def structured(value, default):
    if value is None or value == '':return default
    if isinstance(value,(dict,list)):return value
    try:return json.loads(value)
    except (ValueError,TypeError):raise Invalid({'payload':'Invalid request'})


def validate(data, outputs, submit=False):
    if not isinstance(data, dict):
        raise Invalid({'payload': 'Invalid request'})
    periods = structured(data.get('periods'), {})
    if not isinstance(periods, dict):
        raise Invalid({'periods': 'Invalid request'})
    clean = {k: str(data.get(k) or '').strip() for k in (
        'title', 'description', 'output', 'key_activity_code', 'focal_point', 'email',
        'institution', 'partners', 'member_state')}
    from .ihpix_calendar import schedule
    clean.update(schedule(data))
    clean['periods'] = {b: str('' if periods.get(b) is None else periods.get(b)).strip() for b in BIENNIA}
    for key in ('additional_outputs', 'associated_groups'):
        values = structured(data.get(key), [])
        if not isinstance(values, list) or len(values) > 100 or any(not isinstance(v, str) for v in values):
            raise Invalid({key: 'Invalid request'})
        clean[key] = sorted(set(values))
    clean['links'] = structured(data.get('links'), [])
    errors = {}
    if not clean['title']:
        errors['title'] = 'This field is required'
    if len(clean['title']) > 300:
        errors['title'] = 'This answer is too long'
    for key in ('description', 'partners'):
        if len(clean[key]) > 20000:
            errors[key] = 'This answer is too long'
    for key in ('focal_point', 'email', 'institution', 'member_state'):
        if len(clean[key]) > 2000:
            errors[key] = 'This answer is too long'
    if any(len(v) > 20000 for v in clean['periods'].values()):
        errors['periods'] = 'This answer is too long'
    if clean['output'] and clean['output'] not in outputs:
        errors['output'] = 'Select an output of this group'
    if clean['key_activity_code'] and not C.is_valid_key_activity(clean['output'], clean['key_activity_code']):
        errors['key_activity_code'] = 'Select a key activity of this output'
    if any(o not in C.all_output_codes() for o in clean['additional_outputs']):
        errors['additional_outputs'] = 'Select a valid output'
    emails = [part.strip() for part in re.split('[;,]',clean['email']) if part.strip()]
    if clean['email'] and (not emails or not all(re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', part) for part in emails)):
        errors['email'] = 'Invalid email address'
    if not isinstance(clean['links'], list) or len(clean['links']) > 100:
        errors['links'] = 'Invalid resources'
    else:
        for link in clean['links']:
            if not isinstance(link, dict) or not re.match(r'^https?://[^\s]+$', str(link.get('url', ''))):
                errors['links'] = 'The URL must start with http:// or https://'
    if submit:
        for key in ('description','output','key_activity_code','focal_point','institution'):
            if not clean[key]:
                errors[key] = 'This field is required'
        if not any(clean['periods'].values()):
            errors['periods'] = 'Add a commitment for at least one biennium'
    if errors:
        raise Invalid(errors)
    return clean


def validate_contact(data):
    if not isinstance(data, dict):
        raise Invalid({'payload': 'Invalid request'})
    clean = {k: str(data.get(k) or '').strip() for k in (
        'name','email','institution','job_title','country','region','language','role')}
    if not clean['name']:
        raise Invalid({'name': 'This field is required'})
    if any(len(v) > 2000 for v in clean.values()):
        raise Invalid({'payload': 'This answer is too long'})
    outputs = unpack(data.get('outputs'), [])
    if not isinstance(outputs, list) or any(o not in C.all_output_codes() for o in outputs):
        raise Invalid({'outputs': 'Select a valid output'})
    clean['outputs'] = sorted(set(outputs))
    return clean


def identity(user_id, request_id):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'ihpix-plan:'+user_id+':'+str(uuid.UUID(request_id))))


def digest(data):
    values = {k: v for k, v in data.items() if k not in ('origin', 'warnings', 'errors', 'selected', 'match', 'decision')}
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def workbook(raw):
    from openpyxl import load_workbook
    if len(raw) > 10 * 1024 * 1024:
        raise Invalid({'file': 'Workbook is too large'})
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if sum(i.file_size for i in z.infolist()) > 80 * 1024 * 1024:
                raise Invalid({'file': 'Workbook is too large'})
        return load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except (ValueError, zipfile.BadZipFile, KeyError):
        raise Invalid({'file': 'Choose an XLSX workbook'})


def parse_plans(raw, filename):
    book = workbook(raw)
    rows = []
    try:
        for sheet in book:
            output = sheet.title.strip().rstrip('.')
            if output not in C.all_output_codes():
                continue
            header = None
            key = ''; exported = False
            for cells in sheet.iter_rows(max_row=min(sheet.max_row, 5000), max_col=17):
                values = [str('' if c.value is None else c.value).strip().replace('\xa0', ' ') for c in cells]
                if values[:4] == ['Activity ID','Key activity','Title','Proposed activity']:
                    header = cells[0].row; exported = True; continue
                if header and exported:
                    if not any(values): continue
                    rows.append(dict(title=values[2],description=values[3],output=output,key_activity_code=values[1],
                                     periods=dict(zip(BIENNIA,values[4:8])),focal_point=values[8],email=values[9],
                                     institution=values[10],partners=values[11],member_state=values[12],
                                     planned_start=values[15],planned_end=values[16],
                                     additional_outputs=[],associated_groups=[],links=[],
                                     origin={'file':filename,'sheet':sheet.title,'row':cells[0].row,'activity_id':values[0]}))
                    if len(rows) > 2000: raise Invalid({'file':'Too many rows'})
                    continue
                if any('proposed activities' in s.lower() for s in values):
                    header = cells[0].row
                    continue
                if not header:
                    continue
                text = values[0].strip()
                if not text:
                    continue
                match = re.match(r'^key\s+activity\s+(\d+)', text, re.I)
                if match:
                    key = output+'.'+match[1]
                    continue
                # Filas de referencia o encabezados no se convierten en propuestas.
                if text.lower().startswith(('output ', 'proposed activities', 'total')):
                    continue
                data = dict(title=text[:300], description=text, output=output, key_activity_code=key,
                            periods=dict(zip(BIENNIA, values[1:5])), focal_point=values[5], email=values[6],
                            institution=values[7], partners=values[8], member_state=values[9],
                            additional_outputs=[], associated_groups=[], links=[],
                            origin={'file':filename, 'sheet':sheet.title, 'row':cells[0].row, 'cells':values})
                rows.append(data)
                if len(rows) > 2000:
                    raise Invalid({'file': 'Too many rows'})
    finally:
        book.close()
    if not rows:
        raise Invalid({'file': 'No planned activities found'})
    return rows


def parse_contacts(raw, filename):
    book = workbook(raw)
    result = []
    seen = {}
    try:
        for sheet in book:
            header = None
            for cells in sheet.iter_rows(max_row=min(sheet.max_row, 5000), max_col=30):
                vals = [str('' if c.value is None else c.value).strip() for c in cells]
                lower = [re.sub(r'\s+', ' ',v.lower()) for v in vals]
                if any(v in ('full name','name','name of official representative') for v in lower):
                    header = lower
                    continue
                if header is None:
                    continue
                def value(*names):
                    return next((vals[header.index(n)] for n in names if n in header), '')
                name = value('full name','name','name of official representative')
                if not name:
                    continue
                email = value('email address','email','email of official representative')
                role = value('category of oetwg 4','role (chairperson - cp, vice-chairperson - vcp)')
                output_headers=[v.split()[0] for v in header if v.split() and v.split()[0] in C.all_output_codes()]
                # Las hojas Output del original contienen copias ocultas de todo el padrón.
                # Una celda vacía no asigna al contacto a ese Output.
                source=value('output') if output_headers else sheet.title+' '+value('output')
                outputs = [o for o in C.all_output_codes() if re.search(r'(?<!\d)'+re.escape(o)+r'(?!\d)',source)]
                for index, label in enumerate(header):
                    code = label.split()[0] if label.split() else ''
                    if code in C.all_output_codes() and vals[index].lower() not in ('', 'no', '0', 'false'):
                        outputs.append(code)
                row = dict(name=name, email=email, institution=value('organization','institution'),
                           job_title=value('job title'), country=value('country','member state'),
                           region=value('ihp region'), language=value('language'), role=role,
                           outputs=sorted(set(outputs)), origin={'file':filename,'sheet':sheet.title,'row':cells[0].row})
                marker = (email.lower(), name.casefold())
                if marker in seen:
                    previous=seen[marker]
                    previous['outputs']=sorted(set(previous['outputs']+row['outputs']))
                    roles=list(dict.fromkeys([v for v in previous['role'].split('; ') + [role] if v]))
                    previous['role']='; '.join(roles)
                    for field in ('institution','job_title','country','region','language'):
                        if not previous[field]:previous[field]=row[field]
                    previous['origin']['sources'].append(row['origin'])
                else:
                    row['origin']['sources']=[dict(row['origin'])]
                    seen[marker]=row;result.append(row)
                if len(result) > 2000:
                    raise Invalid({'file': 'Too many rows'})
    finally:
        book.close()
    if not result:
        raise Invalid({'file': 'No contacts found'})
    return result


def export_plans(plans, outputs):
    from openpyxl import Workbook
    book = Workbook(); book.remove(book.active)
    for code in outputs:
        sheet = book.create_sheet(code)
        sheet.append(['Activity ID','Key activity','Title','Proposed activity']+list(BIENNIA)+[
            'Responsible focal point','Email','Lead Institution','Other partners','Lead Member State','Review','Execution','Planned start','Planned end'])
        for plan in plans:
            p = plan.get('approved') or plan['payload']
            if p.get('output') != code:
                continue
            cells = [plan['id'],p['key_activity_code'],p['title'],p['description']]+[p['periods'].get(b,'') for b in BIENNIA]+[
                p['focal_point'],p['email'],p['institution'],p['partners'],p['member_state'],plan['review_status'],plan['execution_status'],p.get('planned_start',''),p.get('planned_end','')]
            sheet.append(cells)
            # Todas las respuestas se exportan como texto, incluso si comienzan con '='.
            for cell in sheet[sheet.max_row]:
                cell.data_type = 's'
        sheet.freeze_panes='E2';sheet.auto_filter.ref=sheet.dimensions
    if not book.sheetnames:
        book.create_sheet('Plan')
    output=io.BytesIO();book.save(output);return output.getvalue()
