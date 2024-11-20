from ..auth import build_creation_perm, build_export_perm, build_link_perm
from .base import CremeTestCase
from .fake_models import FakeContact


class AuthTestCase(CremeTestCase):
    def test_build_perms(self):
        self.assertEqual(
            'creme_core.add_fakecontact', build_creation_perm(FakeContact)
        )
        self.assertEqual(
            'creme_core.link_fakecontact', build_link_perm(FakeContact)
        )
        self.assertEqual(
            'creme_core.export_fakecontact', build_export_perm(FakeContact)
        )
