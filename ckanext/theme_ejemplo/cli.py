# -*- coding: utf-8 -*-
"""CLI commands for IHP-IX data management.

Uso:
    ckan ihpix seed-data -f path/to/ihpix_seed_data.json
    ckan ihpix seed-data --from-excel path/to/file.xlsx
"""
import json
import os
import logging
import datetime

import click

log = logging.getLogger(__name__)


@click.group()
def ihpix():
    """Comandos de gestión de datos IHP-IX."""
    pass


@ihpix.command(name='seed-data')
@click.option('-f', '--file', 'json_file', default=None,
              help='Ruta al archivo JSON seed (ihpix_seed_data.json)')
@click.option('--from-excel', 'excel_file', default=None,
              help='Ruta al archivo Excel para generar seed y cargar')
@click.option('--append', is_flag=True, default=False,
              help='Agregar datos sin borrar los existentes')
def seed_data(json_file, excel_file, append):
    """Cargar datos IHP-IX desde JSON seed o Excel."""
    from ckan import model as ckan_model
    from ckanext.theme_ejemplo.model import (
        IhpixActivity, init_ihpix_activities_db,
        IhpixCountrySummary, init_ihpix_country_summary_db,
    )
    import ckan.model.meta as meta

    init_ihpix_activities_db()
    init_ihpix_country_summary_db()

    if excel_file:
        click.echo('Generando seed desde Excel: {}'.format(excel_file))
        from ckanext.theme_ejemplo.scripts.generate_seed import generate_seed
        data = generate_seed(excel_file)
    elif json_file:
        click.echo('Cargando seed desde JSON: {}'.format(json_file))
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # Buscar archivo por defecto
        default_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'data', 'ihpix_seed_data.json'
        )
        if os.path.exists(default_path):
            click.echo('Usando archivo seed por defecto: {}'.format(default_path))
            with open(default_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            click.echo('Error: Proporcione -f <json> o --from-excel <xlsx>')
            raise SystemExit(1)

    activities = data.get('activities', [])
    country_summaries = data.get('country_summaries', [])

    try:
        if not append:
            click.echo('Eliminando datos existentes...')
            meta.Session.query(IhpixActivity).filter(
                IhpixActivity.original_id != u'',
                IhpixActivity.original_id != None  # noqa: E711
            ).delete(synchronize_session='fetch')
            IhpixCountrySummary.delete_all()

        # Cargar actividades
        click.echo('Cargando {} actividades...'.format(len(activities)))
        loaded = 0
        for act_data in activities:
            try:
                end_date = None
                ed = act_data.get('end_date', '')
                if ed:
                    try:
                        if 'T' in ed:
                            end_date = datetime.datetime.fromisoformat(
                                ed.replace('Z', '+00:00')).date()
                        elif '-' in ed and len(ed) >= 10:
                            end_date = datetime.datetime.strptime(
                                ed[:10], '%Y-%m-%d').date()
                    except (ValueError, TypeError):
                        end_date = None

                activity = IhpixActivity(
                    title=act_data.get('title', u''),
                    priority_area=act_data.get('priority_area', u''),
                    description=act_data.get('description', u''),
                    output=act_data.get('output', u''),
                    country=act_data.get('country', u''),
                    institution=act_data.get('institution', u''),
                    status=act_data.get('status', 'published'),
                    contact_name=act_data.get('contact_name', u''),
                    contact_email=act_data.get('contact_email', u''),
                    end_date=end_date,
                    key_activity=act_data.get('key_activity', u''),
                    outcomes=act_data.get('outcomes', u''),
                    biennium=act_data.get('biennium', u''),
                    institution_type=act_data.get('institution_type', u''),
                    partners=act_data.get('partners', u''),
                    unesco_participation=act_data.get('unesco_participation', u''),
                    flagships=act_data.get('flagships', u''),
                    regions=act_data.get('regions', u''),
                    member_states=act_data.get('member_states', u''),
                    knowledge_product_type=act_data.get('knowledge_product_type', u''),
                    knowledge_product_type_other=act_data.get('knowledge_product_type_other', u''),
                    num_knowledge_products=act_data.get('num_knowledge_products', 0),
                    scientific_product_type=act_data.get('scientific_product_type', u''),
                    num_scientific_products=act_data.get('num_scientific_products', 0),
                    training_type=act_data.get('training_type', u''),
                    num_training_materials=act_data.get('num_training_materials', 0),
                    num_curricula=act_data.get('num_curricula', 0),
                    num_transboundary_ms=act_data.get('num_transboundary_ms', 0),
                    knowledge_activity_type=act_data.get('knowledge_activity_type', u''),
                    knowledge_activity_type_other=act_data.get('knowledge_activity_type_other', u''),
                    stakeholders_knowledge=act_data.get('stakeholders_knowledge', 0),
                    stakeholders_knowledge_female=act_data.get('stakeholders_knowledge_female', 0),
                    stakeholders_knowledge_youth=act_data.get('stakeholders_knowledge_youth', 0),
                    stakeholders_awareness=act_data.get('stakeholders_awareness', 0),
                    stakeholders_awareness_female=act_data.get('stakeholders_awareness_female', 0),
                    stakeholders_awareness_youth=act_data.get('stakeholders_awareness_youth', 0),
                    num_stakeholder_groups=act_data.get('num_stakeholder_groups', 0),
                    stakeholder_group_type=act_data.get('stakeholder_group_type', u''),
                    notes=act_data.get('notes', u''),
                    cross_cutting_wg=act_data.get('cross_cutting_wg', u''),
                    synergies=act_data.get('synergies', u''),
                    supporting_member_state=act_data.get('supporting_member_state', u''),
                    original_timestamp=act_data.get('original_timestamp', u''),
                    original_id=str(act_data.get('original_id', u'')),
                )
                meta.Session.add(activity)
                loaded += 1
                if loaded % 100 == 0:
                    meta.Session.flush()
                    click.echo('  ... {} actividades cargadas'.format(loaded))
            except Exception as e:
                log.warning('Error cargando actividad %s: %s',
                            act_data.get('title', '?')[:50], e)

        meta.Session.flush()
        click.echo('Actividades cargadas: {}'.format(loaded))

        # Cargar country summaries
        click.echo('Cargando {} country summaries...'.format(len(country_summaries)))
        cs_loaded = 0
        for cs_data in country_summaries:
            try:
                country = cs_data.get('country')
                if not country:
                    log.warning('Saltando country summary sin campo "country"')
                    continue
                cs = IhpixCountrySummary(
                    country=country,
                    latitude=cs_data.get('latitude', 0.0),
                    longitude=cs_data.get('longitude', 0.0),
                    region=cs_data.get('region', u''),
                    total_activities=cs_data.get('total_activities', 0),
                    pa1_count=cs_data.get('pa1_count', 0),
                    pa2_count=cs_data.get('pa2_count', 0),
                    pa3_count=cs_data.get('pa3_count', 0),
                    pa4_count=cs_data.get('pa4_count', 0),
                    pa5_count=cs_data.get('pa5_count', 0),
                    transboundary_all=cs_data.get('transboundary_all', 0),
                    transboundary_pa1=cs_data.get('transboundary_pa1', 0),
                    transboundary_pa2=cs_data.get('transboundary_pa2', 0),
                    transboundary_pa3=cs_data.get('transboundary_pa3', 0),
                    transboundary_pa4=cs_data.get('transboundary_pa4', 0),
                    transboundary_pa5=cs_data.get('transboundary_pa5', 0),
                    supporting_all=cs_data.get('supporting_all', 0),
                    supporting_pa1=cs_data.get('supporting_pa1', 0),
                    supporting_pa2=cs_data.get('supporting_pa2', 0),
                    supporting_pa3=cs_data.get('supporting_pa3', 0),
                    supporting_pa4=cs_data.get('supporting_pa4', 0),
                    supporting_pa5=cs_data.get('supporting_pa5', 0),
                    flagship_data=cs_data.get('flagship_data', u''),
                    pa_output_data=cs_data.get('pa_output_data', u''),
                )
                meta.Session.add(cs)
                cs_loaded += 1
            except Exception as e:
                log.warning('Error cargando country %s: %s',
                            cs_data.get('country', '?'), e)

        meta.Session.commit()
        click.echo('Country summaries cargados: {}'.format(cs_loaded))
        click.echo('Ingesta completada exitosamente.')

    except Exception as e:
        meta.Session.rollback()
        click.echo('Error durante la ingesta, rollback realizado: {}'.format(e))
        raise SystemExit(1)
