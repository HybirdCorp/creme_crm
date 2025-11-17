from .. import auth
from ..auth.special import SpecialPermission, SpecialPermissionRegistry
from .base import CremeTestCase
from .fake_models import FakeContact


class AuthTestCase(CremeTestCase):
    def test_build_perms(self):
        self.assertEqual(
            'creme_core.add_fakecontact', auth.build_creation_perm(FakeContact)
        )
        self.assertEqual(
            'creme_core.link_fakecontact', auth.build_link_perm(FakeContact)
        )
        self.assertEqual(
            'creme_core.list_fakecontact', auth.build_list_perm(FakeContact)
        )
        self.assertEqual(
            'creme_core.export_fakecontact', auth.build_export_perm(FakeContact)
        )

    def test_special_permission(self):
        id = 'creme_core-cooking'
        verbose_name = 'Cooking'
        description = 'Permission to cook'
        sp = SpecialPermission(
            id=id, verbose_name=verbose_name, description=description,
            # TODO: app_label='creme_core' ??
        )
        self.assertEqual(id,           sp.id)
        self.assertEqual(verbose_name, sp.verbose_name)
        self.assertEqual(description,  sp.description)

        self.assertEqual(verbose_name, str(sp))
        self.assertEqual('special#creme_core-cooking', sp.as_perm)

    def test_special_permission_registry(self):
        registry = SpecialPermissionRegistry()
        self.assertListEqual([], [*registry.permissions])

        sp1 = SpecialPermission(
            id='creme_core-cooking', verbose_name='Cooking', description='Can cook',
        )
        sp2 = SpecialPermission(
            id='creme_core-gardening', verbose_name='Can garden', description='Gardening',
        )
        sp3 = SpecialPermission(
            id='creme_core-painting', verbose_name='Can paint', description='Painting',
        )

        registry.register(sp1, sp2).register(sp3)
        self.assertCountEqual([sp1, sp2, sp3], [*registry.permissions])

        with self.assertNoLogs():
            self.assertEqual(sp1, registry.get_permission(sp1.id))

        # ---
        with self.assertLogs(level='WARNING') as logs_manager:
            self.assertIsNone(registry.get_permission('unknown'))
        self.assertIn(
            'Invalid special permission ID: unknown',
            logs_manager.output[0],
        )

        # ---
        registry.unregister(sp1.id, sp3.id)
        self.assertListEqual([sp2], [*registry.permissions])

    def test_special_permission_registry__register__empty_id(self):
        sp = SpecialPermission(
            id='', verbose_name='Cooking', description='Can cook',
        )

        with self.assertRaises(SpecialPermissionRegistry.RegistrationError):
            SpecialPermissionRegistry().register(sp)

    def test_special_permission_registry__register__duplicated(self):
        sp1 = SpecialPermission(
            id='creme_core-cooking', verbose_name='Cooking', description='Can cook',
        )
        sp2 = SpecialPermission(
            id=sp1.id, verbose_name='Can garden', description='Gardening',
        )

        with self.assertRaises(SpecialPermissionRegistry.RegistrationError):
            SpecialPermissionRegistry().register(sp1, sp2)

    def test_special_permission_registry__unregister__unknown(self):
        with self.assertRaises(SpecialPermissionRegistry.UnRegistrationError):
            SpecialPermissionRegistry().unregister('unknown')
