"""Contratos de planificación y formatos heredados, sin servidor CKAN."""
import io
import pytest
from openpyxl import Workbook,load_workbook
from ckanext.theme_ejemplo import ihpix_planning as P, ihpix_legacy_reports as E


def raw(sheets):
    book=Workbook();book.remove(book.active)
    for name,rows in sheets.items():
        sheet=book.create_sheet(name)
        for row in rows:sheet.append(row)
    out=io.BytesIO();book.save(out);return out.getvalue()


def plan(**kw):
    return dict(title='Research',description='Future work',output='4.1',key_activity_code='4.1.1',
                focal_point='Focal',institution='Institute',periods={'2026-2027':'Assess pilot sites'},**kw)


def test_seeds_and_taxonomy():
    seeds=P.seeds()
    assert len(seeds)==8 and len({s['id'] for s in seeds})==8
    assert len([o for s in seeds if s['kind']=='oetwg' for o in s['outputs']])==34
    assert all(set(s['outputs'])<=set(P.C.all_output_codes()) for s in seeds)


def test_empty_commitment_is_not_zero_and_submission_requires_commitment():
    p=P.validate(plan(),['4.1'],True)
    assert p['periods']['2022-2023']==''
    p['periods']={}
    with pytest.raises(P.Invalid):P.validate(p,['4.1'],True)
    assert P.validate(p,['4.1'])['periods']['2024-2025']==''


@pytest.mark.parametrize('key,value',[('periods',[]),('additional_outputs',[{}]),('associated_groups','bad'),('links',[{'url':'javascript:1'}]),('email',';;'),('output','3.1'),('key_activity_code','3.1.1')])
def test_invalid_payload_does_not_bypass_validation(key,value):
    p=plan();p[key]=value
    with pytest.raises(P.Invalid):P.validate(p,['4.1'])


def test_plan_source_sections_empty_formatting_and_four_biennia():
    data=raw({'4.1':[['Header'],[],['Proposed activities','2022-2023','2024-2025','2026-2027','2028-2029'],['Key activity 1. Research'],['Proposal',None,'Milestone',None,'Delivery','Jane','jane@example.test','Institute']], 'Outputs':[['Reference']]})
    rows=P.parse_plans(data,'source.xlsx')
    assert len(rows)==1
    assert rows[0]['key_activity_code']=='4.1.1'
    assert rows[0]['periods']==dict(zip(P.BIENNIA,['','Milestone','','Delivery']))
    assert rows[0]['origin']['row']==5


def test_export_roundtrip_and_formula_safety():
    p=P.validate(plan(),['4.1']);p['title']='=HYPERLINK("x")'
    data=P.export_plans([{'id':'test','payload':p,'approved':{},'review_status':'draft','execution_status':'planned'}],['4.1'])
    book=load_workbook(io.BytesIO(data));assert book['4.1']['C2'].data_type=='s'
    rows=P.parse_plans(data,'export.xlsx');assert rows[0]['title']==p['title'] and rows[0]['periods']==p['periods']


def test_contacts_do_not_infer_account_roles():
    data=raw({'Output 4.1':[['Full Name','Email address','Organization'],['Jane','jane@example.test','Institute']]})
    rows=P.parse_contacts(data,'contacts.xlsx')
    assert len(rows)==1 and rows[0]['outputs']==['4.1']
    assert 'user_id' not in rows[0] and 'status' not in rows[0]


def test_contacts_merge_repeated_output_sheets_without_assigning_blank_memberships():
    data=raw({'All contributors':[['Full Name','Email Address','4.1 Research','4.2 Water'],['Jane','jane@example.test','','Contribute']],
              'Output 4.1':[['Full Name','Email Address','4.1 Research'],['Jane','jane@example.test','']]})
    rows=P.parse_contacts(data,'contacts.xlsx')
    assert len(rows)==1 and rows[0]['outputs']==['4.2']
    assert len(rows[0]['origin']['sources'])==2


def test_legacy_year_and_multi_output_preserve_uncertainty():
    data=raw({'2025':[[],['Output','Name of the ongoing Activity','Description of the Implemented Activity','Biennium of Implementation'],['4.4,4.6','Ongoing training','Training program',2025]]})
    row=E.parse(data,'annual.xlsx')[0]
    assert row['biennium']=='2024-2025' and row['output']=='4.4'
    assert len(row['contributions_json'])==2
    assert not row.get('end_date') and not row.get('outcomes') and not row.get('kpi_2_active')
    assert row['origin']['row']==3
    assert E.validate(row,['4.4','4.6'])['title']=='Ongoing training'


def test_long_legacy_text_requires_correction_without_silent_truncation():
    data=raw({'4.1.':[['Name of the Implemented Activity','Description of the Implemented Activity'],['Report','x'*300]]})
    row=E.parse(data,'legacy.xlsx')[0]
    assert row['description']=='x'*300
    with pytest.raises(P.Invalid):E.validate(row,['4.1'])


def test_zero_commitment_is_preserved_as_text():
    p=plan();p['periods']={'2026-2027':0}
    assert P.validate(p,['4.1'])['periods']['2026-2027']=='0'
