from .. import auth
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
