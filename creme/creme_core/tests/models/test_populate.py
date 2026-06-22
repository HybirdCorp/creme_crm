from django.utils.timezone import now

from creme.creme_core.models import PopulatedApp

from ..base import CremeTestCase


class PopulatedAppTestCase(CremeTestCase):
    def test_command(self):
        pop_app = self.get_object_or_fail(
            PopulatedApp, app='creme_core', version__startswith='3.0',
        )
        self.assertLess(pop_app.performed, now())

        self.get_object_or_fail(
            PopulatedApp, app='creme_config', version__startswith='3.0',
        )
