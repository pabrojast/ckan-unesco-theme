"""Calendario de planes y tareas; los bienios nunca se convierten en fechas."""
import calendar
import re
from datetime import date, timedelta


def schedule(data):
    from .ihpix_planning import Invalid
    result = {}
    for key in ('planned_start', 'planned_end'):
        value = str(data.get(key) or '').strip()
        if value:
            try:
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                    raise ValueError()
                date.fromisoformat(value)
            except ValueError:
                raise Invalid({key: 'Enter a valid date'})
        result[key] = value
    if result['planned_start'] and result['planned_end'] and result['planned_end'] < result['planned_start']:
        raise Invalid({'planned_end': 'The end date must be on or after the start date'})
    return result


def month_view(plans, tasks, month='', today=None):
    today = today or date.today()
    try:
        if not re.fullmatch(r'\d{4}-\d{2}', month):
            raise ValueError()
        first = date.fromisoformat(month + '-01')
        if first.year < 1901 or first.year > 2099:
            raise ValueError()
    except (ValueError, TypeError):
        first = today.replace(day=1)
    following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = following - timedelta(days=1)
    weeks = [[{'date': d.isoformat(), 'day': d.day, 'in_month': d.month == first.month,
               'today': d == today, 'events': []} for d in week]
             for week in calendar.Calendar().monthdatescalendar(first.year, first.month)]
    events = []
    unscheduled = []
    for plan in plans:
        p = plan['payload']
        start = p.get('planned_start') or p.get('planned_end')
        end = p.get('planned_end') or start
        if not start:
            unscheduled.append(plan)
            continue
        events.append(dict(kind='plan', id=plan['id'], group_id=plan['group_id'], title=p['title'],
                           start=start, end=end, status=plan['execution_status'], output=p.get('output', ''),
                           review_status=plan['review_status']))
    for task in tasks:
        if task['kind'] == 'task' and task.get('due_date'):
            day = str(task['due_date'])[:10]
            events.append(dict(kind='task', id=task['id'], title=task['title'] or task['body'],
                               start=day, end=day, status=task['status']))
    events.sort(key=lambda e: (e['start'], e['title'].casefold(), e['id']))
    visible = [e for e in events if e['start'] <= last.isoformat() and e['end'] >= first.isoformat()]
    for week in weeks:
        for day in week:
            if day['in_month']:
                day['events'] = [e for e in visible if e['start'] <= day['date'] <= e['end']]
    return dict(month=first.strftime('%Y-%m'), previous=(first-timedelta(days=1)).strftime('%Y-%m'),
                following=following.strftime('%Y-%m'), today=today.strftime('%Y-%m'), weeks=weeks,
                events=visible, unscheduled=unscheduled, scheduled=len(events))
