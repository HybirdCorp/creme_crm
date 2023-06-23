from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.tests.views.base import BrickTestCaseMixin

from .. import bricks
from .base import EmailCampaign, _EmailsTestCase, skipIfCustomEmailCampaign


@skipIfCustomEmailCampaign
class CampaignTestCase(BrickTestCaseMixin, _EmailsTestCase):
    def test_create(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        url = reverse('emails__create_campaign')
        self.assertGET200(url)

        # ---
        name = 'my_campaign'
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response2)
        campaign = self.get_object_or_fail(EmailCampaign, name=name)

        # ---
        response3 = self.assertGET200(campaign.get_absolute_url())
        self.assertTemplateUsed(response3, 'emails/view_campaign.html')

        sending_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.SendingsBrick,
        )
        self.assertEqual(_('Emails sending'), self.get_brick_title(sending_brick_node))

        ml_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=bricks.MailingListsBrick,
        )
        self.assertEqual(_('Mailing lists'), self.get_brick_title(ml_brick_node))

    def test_edit(self):
        # user = self.login()
        user = self.login_as_root_and_get()

        name = 'my_campaign'
        camp = EmailCampaign.objects.create(user=user, name=name)

        url = camp.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user': user.pk,
                'name': name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(camp).name)

    def test_list(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='my_campaign')

        response = self.assertGET200(EmailCampaign.get_lv_absolute_url())

        with self.assertNoException():
            camp_page = response.context['page_obj']

        self.assertEqual(1, camp_page.number)
        self.assertCountEqual([camp], camp_page.object_list)
