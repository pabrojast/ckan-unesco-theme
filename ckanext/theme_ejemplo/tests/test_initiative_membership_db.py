"""Integración con PostgreSQL y authz real; requiere una DB aislada de CKAN."""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

if not os.environ.get('INITIATIVE_TEST_DATABASE_URL'):
    raise unittest.SkipTest('Requires isolated PostgreSQL and CKAN runtime')

import sqlalchemy as sa
import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan import authz
from ckanext.theme_ejemplo import initiative_membership as service


@unittest.skipUnless(os.environ.get('INITIATIVE_TEST_DATABASE_URL'), 'Requires isolated PostgreSQL')
class InitiativeMembershipTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        model.init_model(sa.create_engine(os.environ['INITIATIVE_TEST_DATABASE_URL']))
        tk.config[service.CONFIG] = True
        tk.config['ckan.auth.roles_that_cascade_to_sub_groups'] = ['admin']
        assert authz.INITIATIVE_ADMIN_SCOPE_GUARD
        service.init_db()

    def setUp(self):
        model.Session.rollback()
        self.prefix = 'initiative-test-' + uuid.uuid4().hex[:12]
        self.users = []
        self.groups = []
        self.applicant = self.user('applicant')
        self.reviewer = self.user('reviewer')
        self.stranger = self.user('stranger')
        self.global_admin = self.user('global', sysadmin=True)
        self.a = self.group('a')
        self.b = self.group('b')
        self.child = self.group('child')
        self.org = self.group('org', organization=True)
        self.add_member(self.reviewer, self.a, 'admin')
        self.add_member(self.stranger, self.b, 'admin')
        model.Session.add(model.Member(group=self.child, table_id=self.a.id,
                          table_name='group', capacity='public', state='active'))
        model.Session.commit()
        self.notify = patch.object(service, '_after_commit').start()
        patch.object(tk, '_', side_effect=lambda value: value).start()
        patch.object(tk, 'get_action', side_effect=self.action).start()

    def tearDown(self):
        patch.stopall()
        model.Session.rollback()
        gids = [g.id for g in self.groups]
        uids = [u.id for u in self.users]
        model.Session.execute(service.scopes.delete().where(service.scopes.c.group_id.in_(gids)))
        model.Session.execute(service.requests.delete().where(service.requests.c.group_id.in_(gids)))
        model.Session.query(model.Member).filter(model.Member.group_id.in_(gids)).delete(synchronize_session=False)
        for obj in self.groups + self.users:
            model.Session.delete(obj)
        model.Session.commit()
        model.Session.remove()

    def user(self, suffix, **kw):
        obj = model.User(name=self.prefix+'-'+suffix, email=self.prefix+'-'+suffix+'@example.invalid', state='active', **kw)
        model.Session.add(obj); model.Session.flush(); self.users.append(obj)
        return obj

    def group(self, suffix, organization=False):
        obj = model.Group(name=self.prefix+'-'+suffix, title=suffix, type='organization' if organization else 'group',
                          is_organization=organization)
        obj.state = 'active'
        model.Session.add(obj); model.Session.flush(); self.groups.append(obj)
        return obj

    def add_member(self, user, group, capacity):
        obj = model.Member(group=group, table_id=user.id, table_name='user', capacity=capacity, state='active')
        model.Session.add(obj); model.Session.flush()
        return obj

    def ctx(self, user):
        return {'user': user.name, 'auth_user_obj': user}

    def action(self, name):
        self.assertEqual(name, 'member_create')
        def create(context, data):
            self.assertTrue(context['defer_commit'])
            self.assertEqual(data['capacity'], 'admin')
            group = service._group(data['id'])
            self.assertTrue(authz.has_user_permission_for_group_or_org(group.id, context['user'], 'membership'))
            user = model.User.get(data['object'])
            existing = service._membership(user.id, group.id)
            if existing:
                existing.capacity = data['capacity']
            else:
                self.add_member(user, group, data['capacity'])
        return create

    def request(self, user=None, group=None):
        return service.initiative_membership_request_create(self.ctx(user or self.applicant),
                {'group_id': (group or self.a).id, 'message': '<script>untrusted</script>'})

    def process(self, row, reviewer=None, decision='approve', **extra):
        return service.initiative_membership_request_process(self.ctx(reviewer or self.reviewer),
                dict(id=row['id'], action=decision, **extra))

    def test_approved_admin_is_direct_only(self):
        self.process(self.request(), role='sysadmin', user_id=self.stranger.id)
        self.assertEqual(service._membership(self.applicant.id, self.a.id).capacity, 'admin')
        for permission in ('update', 'membership', 'delete', 'manage_group'):
            self.assertTrue(authz.has_user_permission_for_group_or_org(self.a.id, self.applicant.name, permission))
            for target in (self.b, self.child, self.org):
                self.assertFalse(authz.has_user_permission_for_group_or_org(target.id, self.applicant.name, permission))
        self.assertFalse(self.applicant.sysadmin)

    def test_existing_admin_still_inherits(self):
        self.assertTrue(authz.has_user_permission_for_group_or_org(self.child.id, self.reviewer.name, 'update'))
        self.process(self.request())
        self.assertTrue(authz.has_user_permission_for_group_or_org(self.child.id, self.reviewer.name, 'update'))

    def test_existing_unrelated_rights_preserved(self):
        self.add_member(self.applicant, self.b, 'admin'); model.Session.commit()
        self.process(self.request())
        self.assertTrue(authz.has_user_permission_for_group_or_org(self.b.id, self.applicant.name, 'update'))

    def test_editor_can_request_upgrade(self):
        self.add_member(self.applicant, self.a, 'editor'); model.Session.commit()
        result = self.process(self.request())
        self.assertEqual(result['prior_capacity'], 'editor')
        self.assertFalse(authz.has_user_permission_for_group_or_org(self.child.id, self.applicant.name, 'update'))

    def test_other_initiative_admin_cannot_review(self):
        row = self.request()
        with self.assertRaises(tk.NotAuthorized): self.process(row, self.stranger)
        with self.assertRaises(tk.NotAuthorized):
            service.initiative_membership_request_list(self.ctx(self.stranger), {'group_id': self.a.id})
        self.assertEqual(service._row(row['id'])['status'], 'pending')

    def test_form_group_cannot_redirect_approval(self):
        row = self.request()
        with self.assertRaises(tk.NotAuthorized): self.process(row, group_id=self.b.id)
        self.assertIsNone(service._membership(self.applicant.id, self.a.id))

    def test_global_admin_can_review_without_local_admin(self):
        row = self.request(group=self.child)
        self.assertEqual(self.process(row, self.global_admin)['status'], 'approved')

    def test_reject_then_reapply(self):
        row = self.request(); self.process(row, decision='reject')
        self.assertIsNone(service._membership(self.applicant.id, self.a.id))
        self.assertNotEqual(row['id'], self.request()['id'])

    def test_duplicate_pending_rejected(self):
        self.request()
        with self.assertRaises(tk.ValidationError): self.request()

    def test_retry_does_not_repeat_notification(self):
        row = self.request(); self.process(row); self.notify.reset_mock(); self.process(row)
        self.notify.assert_not_called()
        self.assertEqual(model.Session.execute(sa.select(sa.func.count()).select_from(service.scopes).where(
            service.scopes.c.group_id == self.a.id)).scalar(), 1)

    def test_conflicting_second_decision_rejected(self):
        row = self.request(); self.process(row)
        with self.assertRaises(tk.ValidationError): self.process(row, decision='reject')

    def test_revocation_removes_access(self):
        self.process(self.request())
        service._membership(self.applicant.id, self.a.id).state = 'deleted'; model.Session.commit()
        self.assertFalse(authz.has_user_permission_for_group_or_org(self.a.id, self.applicant.name, 'update'))

    def test_organizations_are_not_initiatives(self):
        with self.assertRaises(tk.ObjectNotFound): self.request(group=self.org)

    def test_member_states_are_not_initiatives(self):
        country = model.Group.get('gambia')
        self.assertIsNotNone(country)
        with self.assertRaises(tk.ObjectNotFound): self.request(group=country)

    def test_disabled_and_missing_guard_reject_even_sysadmin(self):
        for flag, guard in [(False, True), (True, False)]:
            tk.config[service.CONFIG] = flag
            with patch.object(authz, 'INITIATIVE_ADMIN_SCOPE_GUARD', guard):
                with self.assertRaises(tk.NotAuthorized): self.request(self.global_admin)
        tk.config[service.CONFIG] = True

    def test_anonymous_and_revoked_tokens_are_denied_without_server_error(self):
        from flask_login import AnonymousUserMixin
        anonymous = AnonymousUserMixin()
        context = {'auth_user_obj': anonymous, 'user': None}
        with self.assertRaises(tk.NotAuthorized):
            service.initiative_membership_request_count(context, {})
        with self.assertRaises(tk.NotAuthorized):
            service.initiative_membership_request_create(context, {'group_id': self.a.id})
        self.assertFalse(service.can_review(anonymous, self.a))
        self.assertIsNone(service._limited_actor_scope(context, self.a.id))
        self.assertFalse(service.access_auth(context, {})['success'])

    def test_existing_admin_is_not_restricted_by_pending_request(self):
        row = self.request(); self.add_member(self.applicant, self.a, 'admin'); model.Session.commit()
        self.process(row)
        self.assertTrue(authz.has_user_permission_for_group_or_org(self.child.id, self.applicant.name, 'update'))

    def test_failed_scope_insert_rolls_back_membership(self):
        row = self.request()
        with patch.object(service.scopes, 'insert', side_effect=RuntimeError('scope write failed')):
            with self.assertRaises(RuntimeError): self.process(row)
        self.assertIsNone(service._membership(self.applicant.id, self.a.id))
        self.assertEqual(service._row(row['id'])['status'], 'pending')

    def test_native_member_and_group_updates_preserve_delegation_scope(self):
        self.process(self.request())
        for wrapper in (service.scoped_member_create, service.scoped_group_update):
            user = self.user('delegate-'+uuid.uuid4().hex[:5]); model.Session.commit()
            def original(context, data):
                self.assertTrue(context['defer_commit'])
                if wrapper == service.scoped_group_update:
                    self.assertTrue(context['allow_partial_update'])
                self.add_member(user, self.a, 'admin')
                return {'success': True}
            wrapper(original, self.ctx(self.applicant), {'id': self.a.id})
            self.assertTrue(authz.has_user_permission_for_group_or_org(self.a.id, user.name, 'update'))
            self.assertFalse(authz.has_user_permission_for_group_or_org(self.child.id, user.name, 'update'))

    def test_limited_admin_cannot_gain_inheritance_by_changing_hierarchy(self):
        self.add_member(self.applicant, self.b, 'admin'); model.Session.commit()
        self.process(self.request())
        context = self.ctx(self.applicant)
        with self.assertRaises(tk.NotAuthorized):
            service.scoped_member_create(lambda *args: self.fail('Must reject before mutation'),
                context, {'id': self.a.id, 'object': self.b.id,
                          'object_type': 'group', 'capacity': 'public'})
        def change_parents(ctx, data):
            self.assertTrue(ctx['defer_commit'])
            model.Session.add(model.Member(group=self.a, table_id=self.b.id,
                table_name='group', capacity='public', state='active'))
            return {}
        with self.assertRaises(tk.NotAuthorized):
            service.scoped_group_update(change_parents, context, {'id': self.a.id})
        self.assertFalse(authz.has_user_permission_for_group_or_org(self.child.id, self.applicant.name, 'update'))
        self.assertFalse(model.Session.query(model.Member).filter_by(
            group_id=self.a.id, table_id=self.b.id, table_name='group', state='active').first())

    def test_organization_update_alias_cannot_bypass_initiative_scope(self):
        self.process(self.request())
        with self.assertRaises(tk.NotAuthorized):
            service.scoped_organization_update(lambda *args: self.fail('Must not delegate alias'),
                self.ctx(self.applicant), {'id': self.a.id})
        self.assertEqual(service.scoped_organization_update(lambda *args: 'normal organization action',
                self.ctx(self.applicant), {'id': self.org.id}), 'normal organization action')
        self.assertEqual(service.scoped_organization_update(lambda *args: 'existing admin action',
                self.ctx(self.reviewer), {'id': self.a.id}), 'existing admin action')

    def test_scope_lookup_serializes_with_a_concurrent_new_grant(self):
        group_id = self.a.id
        # Incluso quien todavía no tiene Admin conserva el cerrojo hasta que
        # termine la autorización/mutación nativa; una aprobación no se intercala.
        self.assertIsNone(service._limited_actor_scope(self.ctx(self.applicant), group_id))
        statement = sa.text('SELECT pg_try_advisory_xact_lock(hashtextextended(:key, 0))')
        with model.meta.engine.begin() as conn:
            key = {'key': 'initiative-admin-group:' + group_id}
            self.assertFalse(conn.execute(statement, key).scalar())
            model.Session.rollback()
            self.assertTrue(conn.execute(statement, key).scalar())

    def test_disabling_requests_keeps_existing_scope_and_delegation_guard(self):
        self.process(self.request())
        tk.config[service.CONFIG] = False
        try:
            self.assertFalse(authz.has_user_permission_for_group_or_org(self.child.id, self.applicant.name, 'update'))
            self.assertIsNotNone(service._limited_actor_scope(self.ctx(self.applicant), self.a.id))
        finally:
            tk.config[service.CONFIG] = True

    def test_concurrent_requests_and_approvals(self):
        applicant, reviewer, group_id = self.applicant.name, self.reviewer.name, self.a.id
        def create(_):
            try:
                return service.initiative_membership_request_create({'user': applicant}, {'group_id': group_id})
            except tk.ValidationError:
                return None
            finally:
                model.Session.remove()
        with ThreadPoolExecutor(2) as pool:
            rows = [r for r in pool.map(create, range(2)) if r]
        self.assertEqual(len(rows), 1)
        def approve(_):
            try:
                return service.initiative_membership_request_process({'user': reviewer},
                    {'id': rows[0]['id'], 'action': 'approve'})['status']
            finally:
                model.Session.remove()
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual(list(pool.map(approve, range(2))), ['approved', 'approved'])
        self.assertEqual(model.Session.execute(sa.select(sa.func.count()).select_from(service.scopes).where(
            service.scopes.c.group_id == group_id)).scalar(), 1)


if __name__ == '__main__':
    unittest.main()
