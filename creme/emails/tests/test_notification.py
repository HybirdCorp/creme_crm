from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.emails.notification import CampaignSentContent

from .base import EmailCampaign, _EmailsTestCase


class EmailsNotificationTestCase(_EmailsTestCase):
    @override_settings(SITE_DOMAIN='https://creme.domain')
    def test_campaign_sent_content(self):
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='Camp #01')

        content1 = CampaignSentContent(instance=camp)
        content2 = CampaignSentContent.from_dict(content1.as_dict())

        self.assertEqual(
            _('An emailing campaign has been sent'),
            content2.get_subject(user=user),
        )
        self.assertEqual(
            _('The campaign «%(campaign)s» has been sent') % {'campaign': camp},
            content2.get_body(user=user),
        )
        self.assertHTMLEqual(
            _('The campaign %(campaign)s has been sent') % {
                'campaign': (
                    f'<a href="https://creme.domain{camp.get_absolute_url()}" target="_self">'
                    f'{camp}'
                    f'</a>'
                ),
            },
            content2.get_html_body(user=user),
        )

    def test_campaign_sent_content__error(self):
        "Campaign does not exist anymore."
        user = self.get_root_user()
        content = CampaignSentContent.from_dict({'instance': self.UNUSED_PK})
        body = _('The campaign has been deleted')
        self.assertEqual(body, content.get_body(user=user))
        self.assertEqual(body, content.get_html_body(user=user))
