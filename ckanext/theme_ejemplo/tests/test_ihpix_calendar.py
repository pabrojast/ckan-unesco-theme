"""Fechas explícitas, límites del mes y planificación sin fechas inventadas."""
from datetime import date
import pytest
from ckanext.theme_ejemplo import ihpix_calendar as C, ihpix_planning as P


def plan(id='p',start='',end=''):
    return dict(id=id,group_id='oetwg-4',review_status='draft',execution_status='planned',
                payload=dict(title='Activity',output='4.1',planned_start=start,planned_end=end,periods={'2026-2027':'Milestone'}))


def test_biennium_is_not_a_date():
    view=C.month_view([plan()],[],'2026-11')
    assert len(view['unscheduled'])==1 and not view['events'] and view['scheduled']==0


def test_interval_crosses_month_and_leap_day():
    view=C.month_view([plan(start='2024-02-28',end='2024-03-02')],[],'2024-02',date(2024,2,29))
    days={d['date']:d for w in view['weeks'] for d in w}
    assert len(view['events'])==1 and days['2024-02-29']['today']
    assert days['2024-02-29']['events'] and not days['2024-03-01']['events']
    assert view['previous']=='2024-01' and view['following']=='2024-03'


def test_end_only_milestone_and_task():
    tasks=[dict(id='t',kind='task',title='Follow up',body='',due_date=date(2026,12,5),status='pending')]
    view=C.month_view([plan(end='2026-12-05')],tasks,'2026-12')
    assert len(view['events'])==2 and view['events'][0]['start']==view['events'][0]['end']
    assert view['following']=='2027-01'


@pytest.mark.parametrize('value',['bad','2024-02-30','20241101','0000-01-01'])
def test_invalid_date_rejected(value):
    with pytest.raises(P.Invalid):C.schedule({'planned_start':value})


def test_reversed_interval_rejected():
    with pytest.raises(P.Invalid):C.schedule({'planned_start':'2026-12-01','planned_end':'2026-11-01'})


@pytest.mark.parametrize('month',['wrong','9999-12','0000-01','2024-13'])
def test_invalid_month_falls_back(month):
    assert C.month_view([],[],month,date(2026,11,7))['month']=='2026-11'


def test_export_keeps_dates_and_full_source():
    payload=P.validate(dict(title='Activity',description='Original',output='4.1',planned_start='2026-11-03',planned_end='2026-11-10'),['4.1'])
    original=dict(plan(),payload=payload,approved={})
    parsed=P.parse_plans(P.export_plans([original],['4.1']),'export.xlsx')[0]
    assert parsed['planned_start']=='2026-11-03' and parsed['planned_end']=='2026-11-10'
