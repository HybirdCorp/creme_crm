from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import BrickTestCaseMixin

from ..bricks import MailingListsBrick, SendingsBrick
from .base import EmailCampaign, _EmailsTestCase, skipIfCustomEmailCampaign


@skipIfCustomEmailCampaign
class CampaignTestCase(BrickTestCaseMixin, _EmailsTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def test_create(self):
        url = reverse('emails__create_campaign')
        self.assertGET200(url)

        # ---
        name = 'my_campaign'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': self.user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response2)
        campaign = self.get_object_or_fail(EmailCampaign, name=name)

        # ---
        response3 = self.assertGET200(campaign.get_absolute_url())
        self.assertTemplateUsed(response3, 'emails/view_campaign.html')

        sending_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=SendingsBrick,
        )
        self.assertEqual(_('Sendings'), self.get_brick_title(sending_brick_node))

        ml_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=MailingListsBrick,
        )
        self.assertEqual(_('Mailing lists'), self.get_brick_title(ml_brick_node))

    def test_edit(self):
        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=self.user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': self.user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(camp).name)

    def test_listview(self):
        response = self.assertGET200(EmailCampaign.get_lv_absolute_url())

        with self.assertNoException():
            response.context['page_obj']
