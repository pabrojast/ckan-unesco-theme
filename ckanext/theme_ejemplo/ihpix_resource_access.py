# -*- coding: utf-8 -*-
"""Autorización de referencias internas, independiente de la visibilidad del reporte."""
import ckan.model as model
import ckan.plugins.toolkit as tk


def visible(link, actor=None):
    kind, target = link.get('target_kind'), link.get('target_id')
    if kind == 'url':
        return True
    if kind == 'package' or (kind == 'course' and (target or '').startswith('learning:')):
        package = model.Package.get(target[9:] if kind == 'course' else target)
        if not package or package.state != 'active':
            return False
        try:
            tk.check_access('package_show', {'user': actor.name if actor else '',
                'auth_user_obj': actor}, {'id': package.id})
            return True
        except (tk.NotAuthorized, tk.ObjectNotFound):
            return False
    if kind == 'page':
        from ckanext.pages.db import Page
        page = model.Session.query(Page).filter_by(name=target).first()
        if not page:
            return False
        if actor and (actor.sysadmin or page.user_id == actor.id):
            return True
        return not getattr(page, 'private', False) and getattr(page, 'submission_status', None) in (None, '', 'approved')
    if kind == 'course':
        # El catálogo nativo es la fuente actual; no depende del caché legado.
        native = model.Session.query(model.Package).join(model.PackageExtra).filter(
            model.Package.type == 'learning', model.PackageExtra.key == 'learning_external_id',
            model.PackageExtra.value == target, model.PackageExtra.state == 'active').first()
        if native:
            return visible({'target_kind': 'package', 'target_id': native.id}, actor)
        from ckanext.theme_ejemplo.model import OpenLearningCourse
        course = OpenLearningCourse.get_by_course_id(target)
        return bool(course and course.status == 'approved')
    return False


def filtered(links, actor=None):
    return [link for link in links if visible(link, actor)]
