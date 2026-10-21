# -*- coding: utf-8 -*-
"""Páginas 16:9 con tablas provenientes del mismo cálculo del dashboard."""


def slides(stats):
    s = stats
    pages = [{'title': 'Implementation overview', 'rows': [
        ['Published activities', s['overview']['activities']],
        ['Institutions', s['overview']['institutions']],
        ['Countries across reporting, supporter and beneficiary roles', s['overview']['member_states_impacted']],
    ]}]
    for title, rows in [
        ('Knowledge and scientific products', [
            ['Knowledge products', s['kpi_1']['knowledge_products']],
            ['Scientific products', s['kpi_1']['scientific_products']]]),
        ('Knowledge exchange', [
            ['Stakeholders', s['kpi_2']['individuals']],
            ['Youth (18–35)', s['kpi_2']['youth']],
            ['Female participants', s['kpi_2']['female']],
            ['Youth / female (%)', '{} / {}'.format(
                s['kpi_2']['pct_youth'] if s['kpi_2']['pct_youth'] is not None else 'No data',
                s['kpi_2']['pct_female'] if s['kpi_2']['pct_female'] is not None else 'No data')]]),
        ('Training and education', [['Training materials and courses', s['kpi_3']['materials']],
                                    ['Curricula', s['kpi_4']['curricula']]]),
        ('Awareness raising', [['Stakeholders', s['kpi_5']['individuals']],
            ['Youth (18–35)', s['kpi_5']['youth']], ['Female participants', s['kpi_5']['female']]]),
    ]:
        pages.append({'title': title, 'rows': rows})
    pages.append({'title': 'Transboundary water systems', 'rows': [
        ['Activities reported', s['kpi_6']['active_activities']],
        ['Member States supported in transboundary water management, as reported', s['kpi_6']['member_states_reported']],
        ['Distinct countries', s['kpi_6']['member_states_distinct']]]})
    pages.append({'title': 'Stakeholder groups with strengthened capacity', 'rows': [
        ['Activities reported', s['kpi_8']['active_activities']],
        ['Stakeholder groups', s['kpi_8']['stakeholder_groups']],
        ['Distinct countries', s['kpi_8']['member_states_distinct']]]})
    for dimension, title in [('by_dimension', 'Activities by scope'), ('by_output', 'Activities by Output')]:
        rows = [[item.get('label') or item['key'], item['count']] for item in s['overview'][dimension]]
        for offset in range(0, len(rows), 2):
            pages.append({'title': title, 'rows': rows[offset:offset + 2]})
    return pages
