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


def _apply_legacy_normalization(activity):
    """Aplica `ihpix_normalize.normalize_activity_row` a una actividad recién
    construida (seed) y la marca como normalizada."""
    from ckanext.theme_ejemplo import ihpix_normalize as N
    changes = N.normalize_activity_row(activity.as_dict())
    for field, value in changes.items():
        if field == 'end_date':
            try:
                value = datetime.datetime.strptime(value, '%Y-%m-%d').date()
            except (TypeError, ValueError):
                continue
        setattr(activity, field, value)
    activity.legacy_normalized_at = datetime.datetime.utcnow()


@ihpix.command(name='normalize-legacy')
@click.option('--apply', 'apply_changes', is_flag=True, default=False,
              help='Escribir los cambios (por defecto sólo los muestra)')
@click.option('--status', default=None,
              help='Limitar a un estado (published, pending, draft, rejected)')
@click.option('--all', 'all_rows', is_flag=True, default=False,
              help='Revisar también las filas ya marcadas como normalizadas')
def normalize_legacy(apply_changes, status, all_rows):
    """Normalizar valores heredados del Excel (alias, puertas Sí/No,
    países, key activity). Sin --apply es un ensayo."""
    from ckanext.theme_ejemplo.model import (
        init_ihpix_activities_db, normalize_legacy_activities,
        IhpixCountrySummary, init_ihpix_country_summary_db,
    )
    import ckan.model.meta as meta

    init_ihpix_activities_db()
    dry_run = not apply_changes
    try:
        summary = normalize_legacy_activities(
            dry_run=dry_run, status=status, only_pending=not all_rows)
    except Exception as e:
        meta.Session.rollback()
        click.echo('Error normalizando: {}'.format(e))
        raise SystemExit(1)

    click.echo('{}: {} filas revisadas, {} con cambios'.format(
        'ENSAYO' if dry_run else 'APLICADO', summary['scanned'], summary['changed']))
    for field, n in sorted(summary['fields'].items(), key=lambda kv: -kv[1]):
        old, new = summary['examples'].get(field, ('', ''))
        click.echo('  {:34s} {:5d}   ej: {!r:.45} -> {!r:.45}'.format(field, n, old, new))
    if summary['unknown_values']:
        click.echo('Valores fuera de las listas (revisar a mano):')
        for field, values in summary['unknown_values'].items():
            for value, n in sorted(values.items(), key=lambda kv: -kv[1]):
                click.echo('  {:28s} {:4d}  {}'.format(field, n, value[:80]))
    if dry_run:
        click.echo('Nada escrito. Repite con --apply para guardar.')
        return

    try:
        init_ihpix_country_summary_db()
        from ckanext.theme_ejemplo.actions import (
            ihpix_country_name, _ihpix_invalidate_stats_cache)
        updated = IhpixCountrySummary.recompute_from_activities(
            resolve_name=ihpix_country_name)
        _ihpix_invalidate_stats_cache()
        click.echo('Country summaries recalculados: {}'.format(updated))
    except Exception as e:
        meta.Session.rollback()
        click.echo('Normalización guardada, pero falló el recálculo por país: {}'.format(e))


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
                # Alias, puertas Sí/No y código de key activity al cargar,
                # para que un re-seed no reintroduzca valores heredados
                _apply_legacy_normalization(activity)
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


@ihpix.command(name='recompute-summary')
@click.option('--country', default=None,
              help='Recalcular sólo este país (nombre o slug del grupo)')
@click.option('--dry-run', is_flag=True, default=False,
              help='Mostrar los conteos sin escribir en la BD')
def recompute_summary(country, dry_run):
    """Recalcular ihpix_country_summary desde las actividades publicadas."""
    from ckanext.theme_ejemplo.model import (
        IhpixActivity, init_ihpix_activities_db,
        IhpixCountrySummary, init_ihpix_country_summary_db,
    )
    from ckanext.theme_ejemplo.actions import ihpix_country_name
    import ckan.model.meta as meta

    init_ihpix_activities_db()
    init_ihpix_country_summary_db()

    if dry_run:
        counts = IhpixActivity.get_country_counts({})
        for name in sorted(counts, key=lambda n: -counts[n]['total']):
            d = counts[name]
            click.echo('{:40s} total={:4d}  PA1={} PA2={} PA3={} PA4={} PA5={}'.format(
                name[:40], d['total'], d['pa1_count'], d['pa2_count'],
                d['pa3_count'], d['pa4_count'], d['pa5_count']))
        click.echo('{} países con actividades publicadas (sin cambios).'.format(len(counts)))
        return

    try:
        updated = IhpixCountrySummary.recompute_from_activities(
            country=country, resolve_name=ihpix_country_name)
        click.echo('Country summaries recalculados: {}'.format(updated))
    except Exception as e:
        meta.Session.rollback()
        click.echo('Error recalculando country summaries: {}'.format(e))
        raise SystemExit(1)


@ihpix.command(name='seed-workspaces')
def seed_workspaces():
    """Crear los workspaces (working groups) que falten, uno por Output."""
    from ckanext.theme_ejemplo.model import (
        IhpixWorkingGroup, init_ihpix_working_groups_db,
    )
    init_ihpix_working_groups_db()  # crea tablas y siembra los que faltan
    total = len(IhpixWorkingGroup.get_all())
    click.echo('Workspaces IHP-IX existentes: {}'.format(total))


@click.group()
def openlearning():
    """Comandos de sincronización de cursos UNESCO Open Learning."""
    pass


@openlearning.command(name='sync')
@click.option('--force', is_flag=True, default=False,
              help='Ignorar el TTL y sincronizar siempre')
def openlearning_sync(force):
    """Sincronizar la caché curada de cursos con la API de Open Learning."""
    import ckan.plugins as p
    if p.plugin_loaded('learning'):
        import json
        from ckanext.learning.compat import sync
        click.echo(json.dumps(sync({}, {})))
        return
    from ckanext.theme_ejemplo.model import init_open_learning_courses_db
    from ckanext.theme_ejemplo import openlearning as ol

    init_open_learning_courses_db()
    summary = ol.sync_courses(force=force)
    click.echo(
        'Sync Open Learning: {created} nuevos, {updated} actualizados, '
        '{marked_unavailable} no disponibles '
        '(api={total_api}, completo={full_success})'.format(**summary)
    )
    if not summary['full_success']:
        click.echo('Aviso: el fetch fue parcial; no se marcaron cursos '
                   'como no disponibles.')


@click.group()
def pageviews():
    """Conteo liviano de vistas/descargas (volcado Redis -> Postgres)."""
    pass


@pageviews.command(name='flush')
def pageviews_flush():
    """Volcar los contadores de Redis a las tablas de tracking.

    Pensado para correr por cron cada ~5 min. Crea las tablas si faltan.
    """
    from ckanext.theme_ejemplo.model import init_pageview_tracking_db
    from ckanext.theme_ejemplo import pageview_tracking

    init_pageview_tracking_db()
    result = pageview_tracking.flush_to_db()
    status = result.get('status')
    if status == 'no-redis':
        click.echo('Redis no disponible; nada que volcar.')
        return
    if status == 'locked':
        click.echo('Otro flush está en curso; se omite esta corrida.')
        return
    if status != 'ok':
        raise click.ClickException('No se pudo consolidar: {}'.format(status))
    click.echo(
        'Flush pageviews: {datasets_updated} datasets, '
        '{resources_updated} resources, +{views_added} vistas, '
        '+{downloads_added} descargas.'.format(**result)
    )


@pageviews.command(name='status')
def pageviews_status():
    """Mostrar pendientes en Redis y totales acumulados en Postgres."""
    from ckanext.theme_ejemplo import pageview_tracking

    s = pageview_tracking.get_status()
    click.echo('pageviews_enabled: {}'.format(s['enabled']))
    click.echo('Redis disponible:  {}'.format(s['redis']))
    click.echo('Pendientes en Redis -> vistas: {pending_views}, '
               'descargas: {pending_downloads}, '
               'días: {pending_days}'.format(**s))
    click.echo('Totales en DB -> page_views: {}, downloads: {}'.format(
        s['total_page_views'], s['total_downloads']))


@pageviews.command(name='reconcile-downloads')
@click.option('--apply', 'apply_changes', is_flag=True,
              help='Guardar el total corregido; por defecto sólo simula.')
@click.option('--backup', type=click.Path(dir_okay=False),
              help='Archivo JSON nuevo obligatorio al aplicar.')
def pageviews_reconcile_downloads(apply_changes, backup):
    """Excluir SLD del agregado sin borrar el histórico de recursos."""
    from ckanext.theme_ejemplo.pageview_tracking import reconcile_downloads
    try:
        result = reconcile_downloads(apply=apply_changes, backup=backup)
    except Exception as error:
        raise click.ClickException(str(error))
    click.echo(json.dumps(result, indent=2))


@click.group()
def ranking():
    """Ranking de contribución de Member States, Initiatives y Organizations."""
    pass


@ranking.command(name='recompute')
def ranking_recompute():
    """Recalcular y persistir los scores de contribución.

    Pensado para correr por cron (diario). Crea la tabla si falta.
    """
    from ckanext.theme_ejemplo import ranking as ranking_mod

    summary = ranking_mod.compute_all_scores()
    click.echo(
        'Ranking recomputado: {computed} entidades '
        '({member_states} member states, {initiatives} initiatives, '
        '{organizations} organizations, '
        '{with_completeness} con completitud media).'.format(**summary)
    )


@ranking.command(name='show')
@click.option('-n', '--limit', default=15, help='Número de filas a mostrar')
@click.option('--entity', default=None,
              type=click.Choice(['member_state', 'initiative',
                                 'organization']),
              help='Filtrar por tipo de entidad')
def ranking_show(limit, entity):
    """Mostrar el ranking persistido (solo lectura)."""
    from ckanext.theme_ejemplo.model import (
        ContributionScore, init_contribution_scores_db)

    init_contribution_scores_db()
    rows = ContributionScore.get_ranked(entity)
    if not rows:
        click.echo('Sin scores persistidos. Ejecuta: ckan ranking recompute')
        return
    click.echo(
        '{:<4} {:<28} {:<13} {:>6} {:>5} {:>5} {:>5} {:>6} {:>8} {:>8}'.format(
            '#', 'group', 'entity', 'score', 'ds', 'doc', 'news', 'rec90',
            'views', 'avg_c'))
    for i, r in enumerate(rows[:limit], start=1):
        click.echo(
            '{:<4} {:<28} {:<13} {:>6.2f} {:>5} {:>5} {:>5} {:>6} {:>8} {:>8}'
            .format(
                i, (r.group_name or '')[:28], r.entity_type, r.score or 0,
                r.datasets_count or 0, r.documents_count or 0,
                r.news_events_count or 0, r.recent_90d or 0,
                getattr(r, 'views_total', 0) or 0,
                '{:.1f}'.format(r.avg_completeness)
                if r.avg_completeness is not None else '-'))
