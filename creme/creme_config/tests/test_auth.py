from django.utils.translation import gettext as _

from creme.creme_core.auth.special import (
    SpecialPermission,
    special_perm_registry,
)
from creme.creme_core.tests.base import CremeTestCase

from ..auth import role_config_perm, user_config_perm


class AuthTestCase(CremeTestCase):
    def test_user_config_perm(self):
        self.assertIsInstance(user_config_perm, SpecialPermission)
        self.assertEqual('creme_config-user',  user_config_perm.id)
        self.assertEqual(_('User management'), user_config_perm.verbose_name)

    def test_role_config_perm(self):
        self.assertIsInstance(role_config_perm, SpecialPermission)
        self.assertEqual('creme_config-role', role_config_perm.id)

    def test_global_registry(self):
        self.assertIs(
            special_perm_registry.get_permission(user_config_perm.id),
            user_config_perm,
        )
        self.assertIs(
            special_perm_registry.get_permission(role_config_perm.id),
            role_config_perm,
        )
