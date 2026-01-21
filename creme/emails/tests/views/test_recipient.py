from io import StringIO

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import FakeOrganisation
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.emails import bricks
from creme.emails.models import EmailRecipient

from ..base import MailingList, _EmailsTestCase, skipIfCustomMailingList


@skipIfCustomMailingList
class RecipientViewsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    def test_add_recipients__basic(self):
        user = self.login_as_root_and_get()

        mlist = MailingList.objects.create(user=user, name='ml01')
        self.assertFalse(mlist.emailrecipient_set.exists())

        url = reverse('emails__add_recipients', args=(mlist.id,))

        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('New recipients for «{entity}»').format(entity=mlist),
            context1.get('title')
        )
        self.assertEqual(EmailRecipient.multi_save_label, context1.get('submit_label'))

        # --------------------
        recipients = ['spike.spiegel@bebop.com', 'jet.black@bebop.com']
        self.assertPOST200(url, follow=True, data={'recipients': '\n'.join(recipients)})
        self.assertCountEqual(
            recipients, [r.address for r in mlist.emailrecipient_set.all()],
        )

        response2 = self.assertGET200(mlist.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=bricks.EmailRecipientsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Not linked recipient',
            plural_title='{count} Not linked recipients',
        )

        # --------------------
        # Invalid address
        response3 = self.assertPOST200(url, data={'recipients': 'faye.valentine#bebop.com'})
        self.assertFormError(
            response3.context['form'],
            field='recipients', errors=_('Enter a valid email address.'),
        )

        # --------------------
        recipient = mlist.emailrecipient_set.all()[0]
        ct = ContentType.objects.get_for_model(EmailRecipient)
        self.assertPOST200(
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            follow=True, data={'id': recipient.id},
        )

        addresses = {r.address for r in mlist.emailrecipient_set.all()}
        self.assertEqual(len(recipients) - 1, len(addresses))
        self.assertNotIn(recipient.address, addresses)

    @parameterized.expand([
        '\n',    # Unix EOF
        '\r\n',  # Windows EOF
        '\r',    # Old Mac EOF
    ])
    def test_add_recipients__from_csv(self, end):
        user = self.login_as_root_and_get()

        mlist = MailingList.objects.create(user=user, name='ml01')
        url = reverse('emails__add_recipients_from_csv', args=(mlist.id,))
        self.assertGET200(url)

        # TODO: it seems django validator does not manages address with unicode chars:
        #       is it a problem
        # recipients = ['spike.spiegel@bebop.com', 'jet.bläck@bebop.com']
        recipient1 = 'spike.spiegel@bebop.com'
        recipient2 = 'jet.black@bebop.com'

        csvfile = StringIO(end.join([' ' + recipient1, recipient2 + ' ']) + ' ')
        csvfile.name = 'recipients.csv'  # Django uses this

        self.assertNoFormError(self.client.post(url, data={'recipients': csvfile}))
        self.assertSetEqual(
            {recipient1, recipient2},
            {r.address for r in mlist.emailrecipient_set.all()},
        )

        csvfile.close()

    def test_add_recipients__error(self):
        "Not a MailingList."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Dojo')
        self.assertGET404(reverse('emails__add_recipients', args=(orga.id,)))
