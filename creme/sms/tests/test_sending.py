# -*- coding: utf-8 -*-

from datetime import date
from functools import partial

from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import (
    FakeOrganisation,
    HistoryLine,
    SetCredentials,
)
from creme.creme_core.models.history import TYPE_AUX_CREATION
from creme.creme_core.tests.base import CremeTestCase
from creme.persons.tests.base import skipIfCustomContact

from ..bricks import MessagesBrick
from ..models import Recipient, Sending
from ..models.message import MESSAGE_STATUS_NOTSENT
from .base import (
    Contact,
    MessageTemplate,
    MessagingList,
    SMSCampaign,
    skipIfCustomMessageTemplate,
    skipIfCustomMessagingList,
    skipIfCustomSMSCampaign,
)


@skipIfCustomSMSCampaign
@skipIfCustomMessageTemplate
@skipIfCustomMessagingList
class SendingsTestCase(CremeTestCase):
    @staticmethod
    def _build_add_url(campaign):
        return reverse('sms__create_sending', args=(campaign.id,))

    @skipIfCustomContact
    def test_create01(self):
        user = self.login()
        # We create voluntarily duplicates (recipients that have same addresses
        # than Contact, MessagingLists that contain the same addresses)
        # Sending should not contain duplicates.
        camp = SMSCampaign.objects.create(user=user, name='camp01')

        self.assertFalse(camp.sendings.exists())

        create_ml = partial(MessagingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03', is_deleted=True)

        camp.lists.add(mlist01, mlist02, mlist03)

        mobiles = [
            '0123456',    # 0
            '1789456',    # 1
            '2321321',    # 2
            '369852147',  # 3
            '46215984',   # 4
        ]

        create_recipient = Recipient.objects.create
        create_recipient(messaging_list=mlist01, phone=mobiles[0])
        create_recipient(messaging_list=mlist01, phone=mobiles[2])
        create_recipient(messaging_list=mlist01, phone=mobiles[3])
        create_recipient(messaging_list=mlist02, phone=mobiles[4])
        create_recipient(messaging_list=mlist03, phone='jin@reddragons.mrs')

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Spike', last_name='Spiegel', mobile=mobiles[0]),
            create_contact(first_name='Jet',   last_name='Black',   mobile=mobiles[1]),
        ]
        deleted_contact = create_contact(
            first_name='Ed', last_name='Wong', mobile='147852', is_deleted=True,
        )

        mlist01.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[1])
        mlist02.contacts.add(deleted_contact)

        subject = 'SUBJECT'
        body = 'BODYYYYYYYYYYY'
        template = MessageTemplate.objects.create(
            user=user, name='My template', subject=subject, body=body,
        )

        old_hlines_count = HistoryLine.objects.count()

        url = self._build_add_url(camp)
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(
            url,
            data={'template': template.id},
        ))

        sendings = self.refresh(camp).sendings.all()
        self.assertEqual(1, len(sendings))

        sending = sendings[0]
        self.assertEqual(date.today(), sending.date)
        self.assertEqual(template, sending.template)
        self.assertEqual('SUBJECT : BODYYYYYYYYYYY', sending.content)

        messages = sending.messages.all()
        self.assertEqual(len(mobiles), len(messages), messages)

        phone_set = {message.phone for message in messages}
        self.assertTrue(all(phone in phone_set for phone in mobiles))

        # ---
        self.assertEqual(old_hlines_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(camp.id,           hline.entity.id)
        self.assertEqual(TYPE_AUX_CREATION, hline.type)
        self.assertListEqual(
            [
                _('Add <{type}>: “{value}”').format(
                    type=Sending._meta.verbose_name,
                    value=sending,
                )
            ],
            hline.get_verbose_modifications(user=user),
        )
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_creation">{}<div>',
                _('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': _('Sending'),
                    'auxiliary_value': sending,
                }
            ),
            html_history_registry.line_explainers([hline], user)[0].render(),
        )

        # ---
        message = messages[0]
        self.assertEqual(MESSAGE_STATUS_NOTSENT, message.status)
        # TODO
        # response = self.assertGET200(reverse('sms__view_message', args=(message.id,)))
        # self.assertTemplateUsed(response, 'creme_core/generics/detail-popup.html')
        # self.assertEqual(_('Details of the email'), response.context.get('title'))

        # Detail popup ---------------------------------------------------------
        detail_url = reverse('sms__view_sending', args=(sending.id,))
        self.assertPOST405(detail_url)

        response = self.assertGET200(detail_url)
        self.assertTemplateUsed(response, 'sms/bricks/messages.html')
        self.assertEqual(sending, response.context.get('object'))

        # TODO
        # Test delete campaign -------------------------------------------------
        # camp.trash()
        # self.assertPOST200(camp.get_delete_absolute_url(), follow=True)
        # self.assertFalse(SMSCampaign.objects.exists())
        # self.assertFalse(Sending.objects.exists())
        # self.assertFalse(Message.objects.exists())

    def test_create02(self):
        "No related to a campaign => error"
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertGET404(self._build_add_url(nerv))

    def test_reload_messages_brick01(self):
        "Not super-user."
        user = self.login(is_superuser=False, allowed_apps=['sms'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        camp = SMSCampaign.objects.create(user=user, name='Camp#1')
        template = MessageTemplate.objects.create(
            user=user, name='My template', subject='Subject', body='My body is ready',
        )
        sending = Sending.objects.create(
            campaign=camp,
            date=date.today(),
            template=template,
            content='My body is <b>ready</b>',
        )

        url = reverse('sms__reload_messages_brick', args=(sending.id,))
        # self.assertGET404(url)  # No brick ID  TODO: see

        response = self.assertGET200(url)  # TODO: data={'brick_id': MessagesBrick.id_}
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=1)

        brick_data = content[0]
        self.assertEqual(2, len(brick_data))
        self.assertEqual(MessagesBrick.id_, brick_data[0])
        self.assertIn(f' id="{MessagesBrick.id_}"', brick_data[1])

    def test_reload_sending_bricks02(self):
        "Can not see the campaign"
        user = self.login(is_superuser=False, allowed_apps=['sms'])
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        camp = SMSCampaign.objects.create(user=self.other_user, name='Camp#1')
        template = MessageTemplate.objects.create(
            user=user, name='My template', subject='Subject', body='My body is ready',
        )
        sending = Sending.objects.create(
            campaign=camp,
            date=date.today(),
            template=template,
            content='My body is <b>ready</b>',
        )

        self.assertGET403(
            reverse('sms__reload_messages_brick', args=(sending.id,)),
            # data={'brick_id': MailsBrick.id_}
        )

    def test_inneredit(self):
        user = self.login()

        camp = SMSCampaign.objects.create(user=user, name='Camp#1')
        template = MessageTemplate.objects.create(
            user=user, name='My template', subject='Subject', body='My body is ready',
        )
        sending = Sending.objects.create(
            campaign=camp,
            date=date.today(),
            template=template,
            content='My body is <b>ready</b>',
        )

        build_url = self.build_inneredit_url
        self.assertGET(400, build_url(sending, 'campaign'))
        self.assertGET(400, build_url(sending, 'date'))
        self.assertGET(400, build_url(sending, 'template'))
        self.assertGET(400, build_url(sending, 'content'))

    # TODO: test sync_messages()
    # TODO: test send_messages()
