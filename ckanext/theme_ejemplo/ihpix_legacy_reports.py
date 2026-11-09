"""Adaptador de los libros históricos de implementación a borradores revisables."""
import datetime
import re
from . import ihpix_planning as P, ihpix_forms as F, ihpix_constants as C, ihpix_normalize as N

# Los encabezados originales quedan íntegros en la procedencia del lote.
HEADERS = {
 'Name of the Implemented Activity':'title', 'Name of the ongoing Activity':'title',
 'Description of the Implemented Activity':'description',
 'Key outputs and outcomes of the Implemented Activity':'outcomes',
 'Biennium of Implementation':'biennium','Completion date':'end_date','Focal point':'focal_point_name',
 'Email address of the focal point':'contact_email','Type of leading institution':'institution_type',
 'Name of the lead institution':'institution','Other partners':'partners','Key Activity':'key_activity',
 'UNESCO participation':'unesco_secretariat_participation','Flagship involvement':'flagships',
 'Region of Implementation':'regions','Member State(s) of Implementation':'member_states',
 'Knowledge product type':'knowledge_product_type','Knowledge Product Type (Other)':'knowledge_product_type_other',
 'Number of knowledge product':'num_knowledge_products','Scientific product type':'scientific_product_type',
 'Number of scientific product':'num_scientific_products','Training Materials type':'training_type',
 'Number of Training Materials':'num_training_materials','Number of produce and revised curricula':'num_curricula',
 'Number of Member States with improved transboundary water systems management and governance':'num_transboundary_ms',
 'Type of knowledge activity':'knowledge_activity_type','Type of knowledge Activity (Other)':'knowledge_activity_type_other',
 'Stakeholders with improved knowledge':'stakeholders_knowledge','Stakeholders with improved knowledge (Female)':'stakeholders_knowledge_female',
 'Stakeholders with improved knowledge (Youth 18-35)':'stakeholders_knowledge_youth',
 'Stakeholders raised awareness':'stakeholders_awareness','Stakeholders raised awareness (Female)':'stakeholders_awareness_female',
 'Stakeholders raised awareness (Youth 18-35)':'stakeholders_awareness_youth',
 'Number of Stakeholders (Groups) with strenghten capacity':'num_stakeholder_groups',
 'Stakeholder Group Type':'stakeholder_group_type','Notes':'additional_notes',
 'Cross-Cutting Working Group':'cross_cutting_wg','Synergies':'synergies','Supporting Member State':'supporting_member_state',
}
FIELDS = list(dict.fromkeys(['title','output','key_activity_code']+list(HEADERS.values())+list(F.BOOL_FIELDS)))


def label(value):
    return re.sub(r'\s+', ' ',str(value or '')).strip().casefold()


def text(value):
    if isinstance(value,(datetime.date,datetime.datetime)):return value.strftime('%Y-%m-%d')
    return '' if value is None else str(value).strip()


def parse(raw, filename):
    book=P.workbook(raw);rows=[];mapping={label(k):v for k,v in HEADERS.items()}
    try:
        for sheet in book:
            headers=None
            for cells in sheet.iter_rows(max_row=min(sheet.max_row,5000),max_col=50):
                values=[text(c.value) for c in cells];labels=[label(v) for v in values]
                if 'name of the implemented activity' in labels or 'name of the ongoing activity' in labels:
                    headers=values;continue
                if not headers:continue
                original={h:v for h,v in zip(headers,values) if h}
                data={mapping[label(h)]:v for h,v in original.items() if label(h) in mapping}
                if not data.get('title'):continue
                explicit=next((v for h,v in original.items() if label(h)=='output'),sheet.title.rstrip('.'))
                outputs=list(dict.fromkeys(re.findall(r'(?<!\d)\d\.\d+(?!\d)',explicit)))
                outputs=[o for o in outputs if o in C.all_output_codes()]
                data['output']=outputs[0] if outputs else ''
                data['priority_area']='PA'+outputs[0][0] if outputs else ''
                codes=re.findall(r'(?<!\d)\d\.\d+\.\d+(?!\d)',data.get('key_activity',''))
                codes=[k for k in codes if C.is_valid_key_activity('.'.join(k.split('.')[:2]),k)]
                data['key_activity_code']=next((k for k in codes if k.startswith(data['output']+'.')),'')
                if outputs:
                    data['contributions_json']=[{'priority_area':'PA'+o[0],'output':o,'key_activity_code':next((k for k in codes if k.startswith(o+'.')),'')} for o in outputs]
                # Un año sólo determina el bienio; no afirma ejecución ni finalización.
                year=data.get('biennium','')
                if re.fullmatch(r'202[2-9]',year):data['biennium']=next(b for b in P.BIENNIA if int(b[:4])<=int(year)<=int(b[-4:]))
                for field,allowed in F.MULTI_FIELDS.items():
                    raw_value=data.get(field,'')
                    if allowed:
                        valid,unknown=N.normalize_multi(field,raw_value,allowed)
                        data[field]=valid+unknown
                    else:data[field]=N.split_legacy_multi(raw_value)
                for field in ('institution_type','biennium'):
                    if data.get(field):data[field]=N.normalize_choice(field,data[field]) or data[field]
                if data.get('unesco_secretariat_participation'):
                    data['unesco_secretariat_participation']=data['unesco_secretariat_participation'].lower()
                # Sólo evidencia positiva activa una puerta; vacío sigue sin respuesta.
                for gate,resets in F.GATE_RESETS.items():
                    if any(data.get(k) not in ('',None,[],0,'0') for k in resets):data[gate]='yes'
                rows.append(dict(data,origin={'file':filename,'sheet':sheet.title,'row':cells[0].row,'cells':original},
                                 source_warning='Historical rows require review. The worksheet year does not prove completion.'))
                if len(rows)>2000:raise P.Invalid({'file':'Too many rows'})
    finally:book.close()
    if not rows:raise P.Invalid({'file':'No execution reports found'})
    return rows


def validate(data,outputs):
    values={k:v for k,v in data.items() if k in FIELDS or k in F.MULTI_FIELDS or k=='contributions_json'}
    values['priority_area']='PA'+str(values.get('output',''))[:1] if values.get('output') else ''
    if values.get('output') and values['output'] not in outputs:raise P.Invalid({'output':'Select an output of this group'})
    # Al corregir el output principal, conservar las otras contribuciones originales.
    contributions=P.unpack(values.get('contributions_json'),[]) or []
    values['contributions_json']=[{'priority_area':values['priority_area'],'output':values.get('output',''),'key_activity_code':values.get('key_activity_code','')}]+[r for r in contributions if r.get('output')!=values.get('output')] if values.get('output') else []
    for field in F.MULTI_FIELDS:
        if isinstance(values.get(field),str):values[field]=[v.strip() for v in values[field].split(';') if v.strip()]
    try:F.validate_report_payload(values,True)
    except F.ReportValidationError as exc:raise P.Invalid(exc.errors)
    return values
