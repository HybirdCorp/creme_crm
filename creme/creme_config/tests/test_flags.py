from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.models import FlagsConfigItem
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils.translation import plural

from ..bricks import FlagsConfigBrick


class FlagsConfigTestCase(BrickTestCaseMixin, CremeTestCase):
    PORTAL_URL = reverse('creme_config__flags')

    def setUp(self):
        super().setUp()
        self.login()

    # @staticmethod
    # def _build_add_url(ctype):
    #     return reverse('creme_config__create_search_config', args=(ctype.id,))
    #
    # @staticmethod
    # def _build_edit_url(sci):
    #     return reverse('creme_config__edit_search_config', args=(sci.id,))

    def test_portal01(self):
        response = self.assertGET200(self.PORTAL_URL)
        self.assertTemplateUsed(response, 'creme_config/portals/flags.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            FlagsConfigBrick.id_,
        )
        self.assertEqual(
            _('Configured types of resource'),
            self.get_brick_title(brick_node),
        )

    def test_portal02(self):
        create_fitem = partial(FlagsConfigItem.objects.create, value=1)
        create_fitem(entity_type=FakeContact,      name='Leader')
        create_fitem(entity_type=FakeOrganisation, name='HQ')

        response = self.assertGET200(self.PORTAL_URL)
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            FlagsConfigBrick.id_,
        )

        msg = _(
            '{count} Configured types of resource'
        ) if plural(2) else _(
            '{count} Configured type of resource'
        )

        self.assertEqual(
            msg.format(count=2),
            self.get_brick_title(brick_node),
        )
        # TODO: complete
