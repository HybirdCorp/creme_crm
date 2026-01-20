from django.urls import reverse

from creme.activities import get_activity_model
from creme.activities.tests.base import skipIfCustomActivity
from creme.creme_core.models import ButtonMenuItem
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views import base as view_base
from creme.opportunities import buttons

from .base import OpportunitiesBaseTestCase, Opportunity

Activity = get_activity_model()


class ButtonsTestCase(view_base.ButtonTestCaseMixin, OpportunitiesBaseTestCase):
    @skipIfNotInstalled('creme.activities')
    @skipIfCustomActivity
    def test_unsuccessful_phone_call(self):
        user = self.login_as_root_and_get()
        ButtonMenuItem.objects.create(
            content_type=Opportunity, order=1,
            button=buttons.AddUnsuccessfulPhoneCallButton,
        )
        opp = self._create_opportunity_n_organisations(user=user)[0]
        add_url = reverse('opportunities__create_unsuccessful_phone_call', args=(opp.id,))
        response = self.assertGET200(opp.get_absolute_url())
        self.assertTrue(
            [*self.iter_button_nodes(
                self.get_instance_buttons_node(self.get_html_tree(response.content)),
                tags=['a'], href=add_url,
            )],
            msg='<Add call> button not found!',
        )

# TODO: test LinkedOpportunityButton
