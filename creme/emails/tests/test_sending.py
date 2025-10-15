from copy import deepcopy
from datetime import timedelta
from functools import partial

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core import mail as django_mail
from django.core.validators import EmailValidator
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.html import format_html
from django.utils.timezone import (
    get_current_timezone,
    localtime,
    make_naive,
    now,
)
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.constants import UUID_CHANNEL_JOBS
# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    FakeOrganisation,
    HistoryLine,
    Job,
    Notification,
)
from creme.creme_core.models.history import TYPE_AUX_CREATION
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.models import Civility
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import (
    LwMailPopupBrick,
    LwMailsHistoryBrick,
    MailsBrick,
    SendingBrick,
    SendingConfigItemsBrick,
    SendingHTMLBodyBrick,
    SendingsBrick,
)
from ..creme_jobs import campaign_emails_send_type
from ..forms.sending import SendingConfigField
from ..models import (
    EmailRecipient,
    EmailSending,
    EmailSendingConfigItem,
    LightWeightEmail,
)
from ..notification import CampaignSentContent
from .base import (
    Contact,
    EmailCampaign,
    EmailTemplate,
    MailingList,
    Organisation,
    _EmailsTestCase,
    skipIfCustomEmailCampaign,
    skipIfCustomEmailTemplate,
    skipIfCustomMailingList,
)


class SendingConfigTestCase(BrickTestCaseMixin, _EmailsTestCase):
    DEL_CONF_URL = reverse('emails__delete_sending_config_item')

    def _build_password_edition_url(self, item):
        return reverse('emails__set_sending_config_item_password', args=(item.id,))

    def test_model(self):
        name = 'Config #1'
        password = 'c0w|3OY B3b0P'
        item = EmailSendingConfigItem.objects.create(
            name=name,
            host='pop.mydomain.org',
            username='spike',
            password=password,
            port=25,
            use_tls=False,
        )
        self.assertEqual(name, item.name)
        self.assertEqual(name, str(item))

        with self.assertNoException():
            _ = EmailSendingConfigItem._meta.get_field('encoded_password')

        self.assertNotIn(
            'password',
            {f.name for f in EmailSendingConfigItem._meta.concrete_fields},
        )

        item = self.refresh(item)
        self.assertNotEqual(password, item.encoded_password)
        self.assertEqual(password, item.password)

        # Bad signature ---
        item.encoded_password = 'invalid'

        with self.assertLogs(level='CRITICAL') as logs_manager:
            password = item.password

        self.assertEqual('', password)
        self.assertListEqual(
            logs_manager.output,
            [
                f'CRITICAL:'
                f'creme.emails.models.sending:'
                f'issue with password of EmailSendingConfigItem with id={item.id}: '
                f'SymmetricEncrypter.decrypt: invalid token'
            ],
        )

    def test_creme_config_portal(self):
        self.login_as_root()

        EmailSendingConfigItem.objects.create(
            name='My config',
            host='smtp.mydomain.org',
            username='spike@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        response = self.assertGET200(reverse('creme_config__app_portal', args=('emails',)))

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=SendingConfigItemsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Configured server for campaigns',
            plural_title='{count} Configured servers for campaigns',
        )

    def test_creation01(self):
        self.login_as_emails_admin()

        url = reverse('emails__create_sending_config_item')
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            password_f = context1['form'].fields['password']

        self.assertFalse(password_f.required)
        self.assertFalse(password_f.help_text)
        self.assertEqual(
            pgettext('emails', 'Create a server configuration'),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the configuration'),
            context1.get('submit_label'),
        )

        # ---
        name = 'Config #1'
        host = 'smtp.mydomain.org'
        username = 'spike@mydomain.org'
        password = 'c0w|3OY B3b0P'
        port = 1024
        response2 = self.client.post(
            url,
            data={
                'name': name,
                'host': host,
                'username': username,
                'password': password,
                'port': port,
                'use_tls': 'on',
            },
        )
        self.assertNoFormError(response2)

        item = self.get_object_or_fail(EmailSendingConfigItem, name=name)
        self.assertEqual(host, item.host)
        self.assertEqual(username, item.username)
        self.assertEqual(password, item.password)
        self.assertEqual(port,     item.port)
        self.assertEqual('',       item.default_sender)
        self.assertIs(item.use_tls, True)

        # Name uniqueness ---
        response3 = self.assertPOST200(
            url,
            data={
                'name': name,
                'host': 'other.mydomain.org',
                'username': 'spike@otherdomain.org',
                'password': password,
                'port': port,
                'use_tls': 'on',
            },
        )
        self.assertFormError(
            response3.context['form'],
            field='name',
            errors=_("%(model_name)s with this %(field_label)s already exists.") % {
                'model_name': _('SMTP configuration'),
                'field_label': _('Name'),
            },
        )

    def test_creation02(self):
        "No TLS, empty username, sender."
        self.login_as_emails_admin()

        name = 'Config #1'
        host = 'localhost'
        username = ''
        password = ''
        port = 25
        sender = 'jet@mydomain.org'
        response2 = self.client.post(
            reverse('emails__create_sending_config_item'),
            data={
                'name': name,
                'host': host,
                'username': username,
                'password': password,
                'port': port,
                'use_tls': '',
                'default_sender': sender,
            },
        )
        self.assertNoFormError(response2)

        item = self.get_object_or_fail(EmailSendingConfigItem, name=name)
        self.assertEqual(host, item.host)
        self.assertEqual(username, item.username)
        self.assertEqual(password, item.password)
        self.assertEqual(port,     item.port)
        self.assertEqual(sender,   item.default_sender)
        self.assertIs(item.use_tls, False)

    def test_creation03(self):
        "No admin credentials."
        self.login_as_emails_user()
        self.assertGET403(reverse('emails__create_sending_config_item'))

    def test_edition01(self):
        "No TLS, default port."
        self.login_as_emails_admin()

        password = 'c0w|3OY B3b0P'
        item = EmailSendingConfigItem.objects.create(
            name='My config',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password=password,
            port=25,
            use_tls=False,
        )

        url = item.get_edit_absolute_url()
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            fields1 = context1['form'].fields

        self.assertNotIn('password', fields1)

        self.assertEqual(
            pgettext('emails', 'Edit the server configuration'),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the configuration'),
            context1.get('submit_label'),
        )

        # ---
        name = 'My config #1'
        host = 'smtp.mydomain.org'
        username = 'campaigns'
        # port = 1024
        response2 = self.client.post(
            url,
            data={
                'name': name,
                'host': host,
                'username': username,
                # 'port': port,
                'use_tls': '',
            },
        )
        self.assertNoFormError(response2)

        item = self.refresh(item)
        self.assertEqual(name,      item.name)
        self.assertEqual(host,      item.host)
        self.assertEqual(username,  item.username)
        self.assertEqual(password,  item.password)  # No change
        self.assertIsNone(item.port)
        self.assertFalse(item.use_tls)

    def test_edition02(self):
        "Port is set."
        self.login_as_emails_admin()

        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smtp.bebop.mrs',
            username='spiegel@bebop.mrs',
            password='c0w|3OY B3b0P',
            # port=...,
            use_tls=False,
        )

        host = 'smail.bebop.mrs'
        username = 'spike.spiegel@bebop.mrs'
        port = 1024
        response = self.client.post(
            item.get_edit_absolute_url(),
            data={
                'name': item.name,
                'host': host,
                'username': username,
                'port': port,
                'use_tls': 'on',
            },
        )
        self.assertNoFormError(response)

        item = self.refresh(item)
        self.assertEqual(port, item.port)
        self.assertTrue(item.use_tls)

    def test_edition03(self):
        "No admin credentials."
        self.login_as_emails_user()

        item = EmailSendingConfigItem.objects.create(
            host='smtp.host.mrs',
            username='spike@host.mrs',
            password='c0w|3OY B3b0P',
        )
        self.assertGET403(item.get_edit_absolute_url())

    def test_password_edition01(self):
        self.login_as_emails_admin()

        item = EmailSendingConfigItem.objects.create(
            name='My config',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            # password='',
            port=25,
            use_tls=False,
        )

        url = self._build_password_edition_url(item)
        context1 = self.assertGET200(url).context

        with self.assertNoException():
            fields1 = context1['form'].fields

        self.assertIn('password', fields1)
        self.assertEqual(1, len(fields1))

        self.assertEqual(
            pgettext('emails', 'Edit the server password'),
            context1.get('title'),
        )
        self.assertEqual(
            _('Save the password'),
            context1.get('submit_label'),
        )

        # ---
        password = 'c0w|3OY B3b0P'
        response2 = self.client.post(url, data={'password': password})
        self.assertNoFormError(response2)
        self.assertEqual(password, self.refresh(item).password)

    def test_password_edition02(self):
        "Set empty password."
        self.login_as_emails_admin()

        item = EmailSendingConfigItem.objects.create(
            name='My config',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='123456',
            port=25,
            use_tls=True,
        )
        response = self.client.post(
            self._build_password_edition_url(item),
            data={'password': ''},
        )
        self.assertNoFormError(response)
        self.assertEqual('', self.refresh(item).password)

    def test_password_edition03(self):
        "No admin credentials."
        self.login_as_emails_user()

        item = EmailSendingConfigItem.objects.create(
            host='smtp.host.mrs',
            username='spike@host.mrs',
            password='c0w|3OY B3b0P',
        )
        self.assertGET403(self._build_password_edition_url(item))

    def test_deletion01(self):
        self.login_as_emails_admin()

        item = EmailSendingConfigItem.objects.create(
            host='smtp.host.mrs',
            username='spike@host.mrs',
            password='c0w|3OY B3b0P',
        )

        url = self.DEL_CONF_URL
        data = {'id': item.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data)
        self.assertDoesNotExist(item)

    def test_deletion02(self):
        "No admin credentials."
        self.login_as_emails_user()

        item = EmailSendingConfigItem.objects.create(
            host='smtp.host.mrs',
            username='spike@host.mrs',
            password='c0w|3OY B3b0P',
        )
        self.assertPOST403(self.DEL_CONF_URL, data={'id': item.id})
        self.assertStillExists(item)


class SendingConfigFieldTestCase(CremeTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        create_config = EmailSendingConfigItem.objects.create
        cls.item1 = create_config(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet',
            password='c0w|3OY B3b0P',
            default_sender='jet@mydomain.org',
        )
        cls.item2 = create_config(
            name='Config #2',
            host='smtp.mydomain.org',
            username='spike',
            password='sp4c3 c0w|3OY',
        )

    def test_configuration_class(self):
        email1 = 'jet@mydomain.org'
        conf1 = SendingConfigField.Configuration(item=self.item1, sender=email1)
        self.assertEqual(self.item1, conf1.item)
        self.assertEqual(email1,     conf1.sender)

        email2 = 'spike@mydomain.org'
        conf2 = SendingConfigField.Configuration(item=self.item2, sender=email2)
        self.assertEqual(self.item2, conf2.item)
        self.assertEqual(email2,     conf2.sender)

        self.assertTrue(bool(conf1))
        self.assertNotEqual(conf1, None)
        self.assertNotEqual(conf1, conf2)
        self.assertEqual(
            SendingConfigField.Configuration(item=self.item1, sender=email1),
            conf1,
        )
        self.assertNotEqual(
            SendingConfigField.Configuration(item=self.item2, sender=email1),
            conf1,
        )
        self.assertNotEqual(
            SendingConfigField.Configuration(item=self.item1, sender=email2),
            conf1,
        )

    def test_ok01(self):
        item1 = self.item1
        item2 = self.item2
        field = SendingConfigField()

        self.assertListEqual(
            [
                (str(item1.id), item1.name, {'default_sender': item1.default_sender}),
                (str(item2.id), item2.name, {'default_sender': ''}),
            ],
            [*field.widget.choices],
        )

        sender = 'jet@mydomain.org'
        self.assertEqual(
            SendingConfigField.Configuration(item=item1, sender=sender),
            field.clean([item1.id, sender]),
        )

    def test_ok02(self):
        sender = 'spike@mydomain.org'
        item = self.item2
        self.assertEqual(
            SendingConfigField.Configuration(item=item, sender=sender),
            SendingConfigField().clean([item.id, sender]),
        )

    def test_required(self):
        field = SendingConfigField()
        msg = _('This field is required.')
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=['', ''],
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=None,
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=[self.item1.id, ''],
        )
        self.assertFormfieldError(
            field=field, messages=msg, codes='required', value=['', 'spike@mydomain.org'],
        )

    def test_not_required(self):
        clean = SendingConfigField(required=False).clean
        self.assertIsNone(clean(['', '']))
        self.assertIsNone(clean(['']))
        self.assertIsNone(clean([]))
        self.assertIsNone(clean(None))
        self.assertIsNone(clean([self.item1.id, '']))
        self.assertIsNone(clean(['', 'spike@mydomain.org']))

    def test_invalid_pk(self):
        self.assertFormfieldError(
            field=SendingConfigField(),
            value=[self.UNUSED_PK, 'spike@mydomain.org'],
            messages=forms.ModelChoiceField.default_error_messages['invalid_choice'],
            codes='invalid_choice',
        )

    def test_invalid_email(self):
        self.assertFormfieldError(
            field=SendingConfigField(),
            value=[self.item1.id, 'not an email'],
            messages=EmailValidator.message,
            codes='invalid',
        )

    def test_widget(self):
        field1 = SendingConfigField()
        item1 = self.item1
        item2 = self.item2
        expected = [
            (str(item1.id), item1.name, {'default_sender': item1.default_sender}),
            (str(item2.id), item2.name, {'default_sender': item2.default_sender}),
        ]
        self.assertListEqual(expected, [*field1.widget.choices])
        self.assertEqual(2, len(field1.queryset))  # We force the evaluation of the queryset

        field2 = deepcopy(field1)
        item3 = EmailSendingConfigItem.objects.create(
            name='Config #3',
            host='smtp2.mydomain.org',
            username='faye',
            password='c0w|3OY B3b0P',
            default_sender='faye@mydomain.org',
        )
        self.assertEqual(3, len(field2.queryset))
        self.assertListEqual(
            [
                *expected,
                (str(item3.id), item3.name, {'default_sender': item3.default_sender}),
            ],
            [*field2.widget.choices],
        )


@skipIfCustomEmailCampaign
@skipIfCustomEmailTemplate
@skipIfCustomMailingList
class SendingsTestCase(BrickTestCaseMixin, _EmailsTestCase):
    @staticmethod
    def _build_add_url(campaign):
        return reverse('emails__create_sending', args=(campaign.id,))

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=campaign_emails_send_type.id)

    def _send_mails(self, job=None):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        campaign_emails_send_type.execute(job or self._get_job())

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @override_settings(ENTITIES_DELETION_ALLOWED=True)
    def test_create01(self):
        """We create voluntarily duplicates (recipients that have same addresses
        than Contact/Organisation, MailingList that contain the same addresses)
        EmailSending should not contain duplicates.
        """
        user = self.login_as_root_and_get()

        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet',
            password='c0w|3OY B3b0P',
            default_sender='jet@mydomain.org',
        )

        camp = EmailCampaign.objects.create(user=user, name='camp01')
        self.assertFalse(camp.sendings_set.exists())

        create_ml = partial(MailingList.objects.create, user=user)
        mlist01 = create_ml(name='ml01')
        mlist02 = create_ml(name='ml02')
        mlist03 = create_ml(name='ml03')
        mlist04 = create_ml(name='ml04', is_deleted=True)
        mlist05 = create_ml(name='ml05')
        mlist06 = create_ml(name='ml06', is_deleted=True)

        mlist01.children.add(mlist02, mlist03, mlist04)
        camp.mailing_lists.add(mlist01, mlist05, mlist06)

        addresses = [
            'spike.spiegel@bebop.com',   # 0
            'jet.black@bebop.com',       # 1
            'faye.valentine@bebop.com',  # 2
            'ed.wong@bebop.com',         # 3
            'ein@bebop.com',             # 4
            'contact@nerv.jp',           # 5
            'contact@seele.jp',          # 6
            'shin@reddragons.mrs',       # 7
        ]

        create_recipient = EmailRecipient.objects.create
        create_recipient(ml=mlist01, address=addresses[0])
        create_recipient(ml=mlist02, address=addresses[2])
        create_recipient(ml=mlist02, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[3])
        create_recipient(ml=mlist03, address=addresses[4])
        create_recipient(ml=mlist03, address=addresses[6])
        create_recipient(ml=mlist04, address='vicious@reddragons.mrs')
        create_recipient(ml=mlist05, address=addresses[7])
        create_recipient(ml=mlist06, address='jin@reddragons.mrs')

        create_contact = partial(Contact.objects.create, user=user)
        contacts = [
            create_contact(first_name='Spike', last_name='Spiegel', email=addresses[0]),
            create_contact(first_name='Jet',   last_name='Black',   email=addresses[1]),
        ]
        deleted_contact = create_contact(
            first_name='Ed', last_name='Wong', email='ew@bebop.com', is_deleted=True,
        )

        mlist01.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[0])
        mlist02.contacts.add(contacts[1])
        mlist02.contacts.add(deleted_contact)

        create_orga = partial(Organisation.objects.create, user=user)
        orgas = [
            create_orga(name='NERV',  email=addresses[5]),
            create_orga(name='Seele', email=addresses[6]),
        ]

        mlist02.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[0])
        mlist03.organisations.add(orgas[1])

        subject = 'SUBJECT'
        body = 'BODYYYYYYYYYYY'
        template = EmailTemplate.objects.create(
            user=user, name='My template', subject=subject, body=body,
        )

        old_hlines_count = HistoryLine.objects.count()

        url = self._build_add_url(camp)
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('New sending for «{entity}»').format(entity=camp),
            context1.get('title'),
        )
        self.assertEqual(
            pgettext('emails', 'Save the sending'), context1.get('submit_label'),
        )

        with self.assertNoException():
            config_f = context1['form'].fields['config']
        self.assertListEqual([item.id, item.default_sender], config_f.initial)

        # ---
        sender = 'vicious@reddragons.mrs'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'config_0': item.id,
                'config_1': sender,

                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        sending = self.get_alone_element(
            self.refresh(camp).sendings_set.all()  # refresh is probably be useless...
        )

        self.assertEqual(item,                        sending.config_item)
        self.assertEqual(sender,                      sending.sender)
        self.assertEqual(EmailSending.Type.IMMEDIATE, sending.type)
        self.assertEqual(EmailSending.State.PLANNED,  sending.state)
        self.assertEqual(subject,                     sending.subject)
        self.assertEqual(body,                        sending.body)
        self.assertEqual('',                          sending.body_html)

        now_value = now()
        self.assertDatetimesAlmostEqual(sending.created, now_value)
        self.assertDatetimesAlmostEqual(sending.modified, now_value)

        mails = sending.mails_set.all()
        self.assertEqual(len(addresses), len(mails))

        addr_set = {mail.recipient for mail in mails}
        self.assertTrue(all(address in addr_set for address in addresses))

        related_set = {
            (mail.recipient_ctype_id, mail.recipient_entity_id)
            for mail in mails
        }
        for c in contacts:
            self.assertIn((c.entity_type_id, c.id), related_set)
        for o in orgas:
            self.assertIn((o.entity_type_id, o.id), related_set)

        self.assertEqual('', sending.mails_set.filter(recipient_entity=None)[0].body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=contacts[0].id).body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=orgas[0].id).body)

        # ---
        self.assertEqual(old_hlines_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(camp.id,           hline.entity.id)
        self.assertEqual(TYPE_AUX_CREATION, hline.type)
        self.assertHTMLEqual(
            format_html(
                '<div class="history-line history-line-auxiliary_creation">{}<div>',
                _('“%(auxiliary_ctype)s“ added: %(auxiliary_value)s') % {
                    'auxiliary_ctype': _('Email campaign sending'),
                    'auxiliary_value': sending,
                }
            ),
            html_history_registry.line_explainers([hline], user)[0].render(),
        )

        # ---
        mail = mails[0]
        self.assertEqual(0, mail.reads)
        self.assertEqual(LightWeightEmail.Status.NOT_SENT, mail.status)

        response1 = self.assertGET200(reverse('emails__view_lw_mail', args=(mail.id,)))
        self.assertTemplateUsed(response1, 'creme_core/generics/detail-popup.html')
        self.assertEqual(_('Details of the email'), response1.context.get('title'))
        self.assertEqual('DENY', response1.get('X-Frame-Options'))
        popup_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content), brick=LwMailPopupBrick,
        )
        self.assertIsNone(popup_brick_node.find('.//iframe'))

        # ---
        response2 = self.assertGET200(reverse('emails__lw_mail_body', args=(mail.id,)))
        self.assertEqual('', response2.text)
        self.assertEqual('SAMEORIGIN', response2.get('X-Frame-Options'))

        # Detail view ----------------------------------------------------------
        detail_url = sending.get_absolute_url()
        self.assertPOST405(detail_url)

        response3 = self.assertGET200(detail_url)
        self.assertTemplateUsed(response3, 'emails/view_sending.html')
        self.assertEqual(sending, response3.context.get('object'))

        self.assertContains(response3, contacts[0].email)
        self.assertContains(response3, orgas[0].email)

        tree3 = self.get_html_tree(response3.content)
        self.get_brick_node(tree3, brick=SendingBrick)

        body_brick_node = self.get_brick_node(tree3, brick=SendingHTMLBodyBrick)
        self.assertIsNone(body_brick_node.find('.//iframe'))

        # HTML body ----------------------------------------------------------
        body_url = reverse('emails__sending_body', args=(sending.id,))
        self.assertPOST405(body_url)

        response4 = self.assertGET200(body_url)
        self.assertEqual('', response4.text)
        self.assertEqual('SAMEORIGIN', response4.get('X-Frame-Options'))

        # History brick --------------------------------------------------------
        BrickDetailviewLocation.objects.create_if_needed(
            brick=LwMailsHistoryBrick, order=1, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )

        contact1 = contacts[0]
        contact1_mail = next(mail for mail in mails if mail.recipient_entity_id == contact1.id)
        response5 = self.assertGET200(contact1.get_absolute_url())
        history_brick_node = self.get_brick_node(
            self.get_html_tree(response5.content), brick=LwMailsHistoryBrick,
        )
        self.assertBrickTitleEqual(
            history_brick_node,
            count=1,
            title='{count} Campaign email in the history',
            plural_title='{count} Campaigns emails in the history',
        )
        self.assertBrickHasAction(
            history_brick_node,
            url=reverse('emails__view_lw_mail', args=(contact1_mail.pk,)),
            action_type='view',
        )

        # Test delete campaign -------------------------------------------------
        camp.trash()
        self.assertPOST(302, camp.get_delete_absolute_url())
        self.assertDoesNotExist(camp)
        self.assertDoesNotExist(sending)
        self.assertFalse(LightWeightEmail.objects.exists())

    @skipIfCustomContact
    def test_create02(self):
        "Test template."
        user = self.login_as_root_and_get()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )

        first_name1 = 'Spike'
        last_name1 = 'Spiegel'

        first_name2 = 'Faye'
        last_name2 = 'Valentine'

        civ = Civility.objects.first()

        create_contact = partial(Contact.objects.create, user=user)
        contact1 = create_contact(
            civility=civ, first_name=first_name1, last_name=last_name1,
            email='spike.spiegel@bebop.com',
        )
        contact2 = create_contact(
            # civility=civ,  Nope
            first_name=first_name2, last_name=last_name2,
            email='faye.valentine@bebop.com',
        )

        camp = EmailCampaign.objects.create(user=user, name='camp01')
        mlist = MailingList.objects.create(user=user, name='ml01')

        camp.mailing_lists.add(mlist)
        mlist.contacts.set([contact1, contact2])

        subject = 'Hello'
        body = 'Your first name is: {{first_name}} !'
        body_html = (
            '<div>'
            '<p>Your last name is: {{last_name}} !</p>'
            '<p>Your civility is: {{civility}} !</p>'
            '</div>'
        )
        template = EmailTemplate.objects.create(
            user=user, name='name', subject=subject, body=body, body_html=body_html,
        )
        response1 = self.client.post(
            self._build_add_url(camp),
            data={
                'config_0': item.id,
                'config_1': 'vicious@reddragons.mrs',

                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        )
        self.assertNoFormError(response1)

        with self.assertNoException():
            sending = self.refresh(camp).sendings_set.all()[0]

        self.assertEqual(sending.subject, subject)

        with self.assertNoException():
            mail1 = sending.mails_set.get(recipient_entity=contact1)
            mail2 = sending.mails_set.get(recipient_entity=contact2)

        self.assertEqual(f'Your first name is: {first_name1} !', mail1.rendered_body)

        html1 = (
            f'<div>'
            f'<p>Your last name is: {last_name1} !</p>'
            f'<p>Your civility is: {civ.title} !</p>'
            f'</div>'
        )
        self.assertHTMLEqual(html1, mail1.rendered_body_html)
        self.assertHTMLEqual(
            f'<div>'
            f'<p>Your last name is: {last_name2} !</p>'
            f'<p>Your civility is:  !</p>'
            f'</div>',
            mail2.rendered_body_html,
        )

        self.assertEqual(
            html1.encode(),
            self.client.get(reverse('emails__lw_mail_body', args=(mail1.id,))).content,
        )

        # Detail view ----------------------------------------------------------
        response2 = self.assertGET200(sending.get_absolute_url())
        body_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content), brick=SendingHTMLBodyBrick,
        )
        iframe_node1 = body_brick_node.find('.//iframe')
        self.assertIsNotNone(iframe_node1)
        self.assertEqual(
            reverse('emails__sending_body', args=(sending.id,)),
            iframe_node1.attrib.get('src'),
        )

        # Email Detail view ----------------------------------------------------
        response3 = self.assertGET200(reverse('emails__view_lw_mail', args=(mail1.id,)))
        email_brick_node = self.get_brick_node(
            self.get_html_tree(response3.content), brick=LwMailPopupBrick,
        )
        iframe_node2 = email_brick_node.find('.//iframe')
        self.assertIsNotNone(iframe_node2)
        self.assertEqual(
            reverse('emails__lw_mail_body', args=(mail1.id,)),
            iframe_node2.attrib.get('src'),
        )

        # View template --------------------------------------------------------
        response4 = self.assertGET200(reverse('emails__sending_body', args=(sending.id,)))
        self.assertEqual(template.body_html.encode(), response4.content)

        # Delete sending -------------------------------------------------------
        ct = ContentType.objects.get_for_model(EmailSending)
        self.assertPOST(
            302,
            reverse('creme_core__delete_related_to_entity', args=(ct.id,)),
            data={'id': sending.pk},
        )
        self.assertDoesNotExist(sending)
        self.assertDoesNotExist(mail1)

    @skipIfCustomContact
    @skipIfCustomOrganisation
    @override_settings(EMAILCAMPAIGN_SLEEP_TIME=0.1)
    def test_create03(self):
        "Job + outbox."
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )

        queue = get_queue()
        queue.clear()

        job = self._get_job()
        now_value = now()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )
        mlist = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(
            user=user, email='spike.spiegel@bebop.com',
            first_name='Spike', last_name='Spiegel',
        )

        create_orga = partial(Organisation.objects.create, user=user)
        orga1 = create_orga(name='NERV',  email='contact@nerv.jp')
        orga2 = create_orga(name='Seele', email='contact@seele.jp')

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)
        mlist.organisations.add(orga1, orga2)

        sender = 'vicious@reddragons.mrs'
        self.assertNoFormError(self.client.post(
            self._build_add_url(camp),
            data={
                'config_0': item.id,
                'config_1': sender,

                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))
        self.assertFalse(django_mail.outbox)
        self.assertIs(job.type.next_wakeup(job, now_value), now_value)

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(job, jobs[0][0])

        queue.clear()
        self._send_mails(job)

        with self.assertNoException():
            sending = camp.sendings_set.all()[0]

        self.assertEqual(EmailSending.State.DONE, sending.state)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 3)

        message = messages[0]
        self.assertEqual(template.subject, message.subject)
        self.assertEqual(sender,           message.from_email)
        self.assertBodiesEqual(message, body=template.body, body_html='')
        self.assertEqual(1, len(message.attachments))

        # See 'creme.creme_core.utils.test.EmailBackend'
        connection = message.connection
        self.assertHasAttr(connection, 'kwargs')
        self.assertFalse(connection.args)
        self.assertDictEqual(
            {
                'host':     item.host,
                'port':     item.port,
                'username': item.username,
                'password': item.password,
                'use_tls':  item.use_tls,

                'fail_silently': False,
            },
            connection.kwargs,
        )

        self.assertSetEqual(
            {contact.email, orga1.email, orga2.email},
            {
                recipient
                for message in messages
                for recipient in message.recipients()
            },
        )

        self.assertIsNone(job.type.next_wakeup(job, now_value))
        # Other save() in job should not send REFRESH signals
        self.assertFalse(queue.refreshed_jobs)

        self.assertFalse(
            Notification.objects.filter(user=user, channel__uuid=UUID_CHANNEL_JOBS)
        )

    def test_create04(self):
        "Test deferred."
        user = self.login_as_root_and_get()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )

        now_value = now()
        sending_date = now_value + timedelta(weeks=1)
        naive_sending_date = make_naive(sending_date, get_current_timezone())
        data = {
            'config_0': item.id,
            'config_1': 'vicious@reddragons.mrs',
            'type':     EmailSending.Type.DEFERRED,
            'template': template.id,
        }

        post = partial(self.client.post, self._build_add_url(camp))
        self.assertNoFormError(post(
            data={
                **data,
                'sending_date': naive_sending_date.strftime('%Y-%m-%d'),  # Future: OK
                'hour':         naive_sending_date.hour,
                'minute':       naive_sending_date.minute,
            },
        ))

        with self.assertNoException():
            sending = self.refresh(camp).sendings_set.all()[0]

        self.assertDatetimesAlmostEqual(sending_date, sending.sending_date, seconds=60)

        job = self._get_job()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(sending.sending_date, wakeup)

        # ---
        self.assertFormError(
            post(data=data).context['form'],
            field='sending_date',
            errors=_('Sending date required for a deferred sending'),
        )

        # ---
        msg = _('Sending date must be is the future')
        self.assertFormError(
            post(data={
                **data,
                'sending_date': (now_value - timedelta(days=1)).strftime('%Y-%m-%d'),
            }).context['form'],
            field='sending_date', errors=msg,
        )
        self.assertFormError(
            post(data={
                **data,
                'sending_date': now_value.strftime('%Y-%m-%d'),
            }).context['form'],
            field='sending_date', errors=msg,
        )

    def test_create05(self):
        "Test deferred (today)."
        user = self.login_as_root_and_get()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )

        now_dt = now()
        sending_date = now_dt + timedelta(hours=1)  # Today if we run the test before 23h...

        naive_sending_date = make_naive(sending_date, get_current_timezone())
        data = {
            'config_0': item.id,
            'config_1': 'vicious@reddragons.mrs',
            'type':     EmailSending.Type.DEFERRED,
            'template': template.id,
        }

        post = partial(self.client.post, self._build_add_url(camp))
        self.assertNoFormError(post(
            data={
                **data,
                'sending_date': naive_sending_date.strftime('%Y-%m-%d'),  # Future: OK
                'hour':         naive_sending_date.hour,
                'minute':       naive_sending_date.minute,
            },
        ))

        with self.assertNoException():
            sending = self.refresh(camp).sendings_set.all()[0]

        self.assertDatetimesAlmostEqual(sending_date, sending.sending_date, seconds=60)

    def test_create06(self):
        "Body with variables."
        user = self.login_as_root_and_get()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject',
            body='Hello {{first_name}} {{last_name}} !',
            body_html='<b>Hello</b> {{first_name}} {{last_name}} !',
        )

        mlist = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(
            user=user, email='spike.spiegel@bebop.com',
            first_name='Spike', last_name='Spiegel',
        )
        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        self.assertNoFormError(self.client.post(
            self._build_add_url(camp),
            data={
                'config_0': item.id,
                'config_1': 'vicious@reddragons.mrs',
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        self._send_mails(self._get_job())
        message = self.get_alone_element(django_mail.outbox)
        self.assertBodiesEqual(
            message,
            body='Hello Spike Spiegel !',
            body_html='<b>Hello</b> Spike Spiegel !',
        )
        self.assertEqual(1, len(message.attachments))

    def test_create07(self):
        "No related to a campaign => error."
        user = self.login_as_root_and_get()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertGET404(self._build_add_url(nerv))

    def test_edit01(self):
        user = self.login_as_root_and_get()

        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        sending = EmailSending.objects.create(
            # config_item=None,
            sender='invalid@domain.org',
            campaign=camp,
            sending_date=now() + timedelta(days=2),
        )

        url = sending.get_edit_absolute_url()
        context1 = self.assertGET200(url).context
        self.assertEqual(
            _('Edit the sending on {date}').format(
                date=date_format(localtime(sending.sending_date), 'DATETIME_FORMAT'),
            ),
            context1.get('title'),
        )

        with self.assertNoException():
            fields1 = context1['form'].fields
            config_f1 = fields1['config']

        self.assertEqual(1, len(fields1), fields1)
        self.assertIsNone(config_f1.initial)

        # ---
        sender = 'vicious@reddragons.mrs'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'config_0': item.id,
                'config_1': sender,
            },
        ))

        sending.refresh_from_db()
        self.assertEqual(item,   sending.config_item)
        self.assertEqual(sender, sending.sender)

        # ---
        context3 = self.assertGET200(url).context

        with self.assertNoException():
            config_f3 = context3['form'].fields['config']
        self.assertListEqual([item.id, sender], config_f3.initial)

    def test_edit02(self):
        "State is DONE => error."
        user = self.login_as_root_and_get()

        camp = EmailCampaign.objects.create(user=user, name='camp01')
        sending = EmailSending.objects.create(
            # config_item=None,
            sender='invalid@domain.org',
            campaign=camp,
            sending_date=now() - timedelta(days=2),
            state=EmailSending.State.DONE,
        )
        self.assertGET409(sending.get_edit_absolute_url())

    def test_view_lw_email01(self):
        "Not super-user"
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW'])

        camp = EmailCampaign.objects.create(user=user, name='Camp#1')
        sending = EmailSending.objects.create(
            sender='vicious@reddragons.mrs',
            campaign=camp,
            sending_date=now(),
            body='My body is ready',
            body_html='My body is <b>ready</b>',
        )

        lw_mail = LightWeightEmail(sending=sending)
        lw_mail.genid_n_save()

        # List of emails ---
        response = self.assertGET200(reverse('emails__view_sending', args=(sending.id,)))
        self.assertTemplateUsed(response, 'emails/view_sending.html')
        self.assertEqual(sending, response.context.get('object'))

        # Template ---
        self.assertGET200(reverse('emails__sending_body', args=(sending.id,)))

        # Email detail ---
        response = self.assertGET200(reverse('emails__view_lw_mail', args=(lw_mail.id,)))
        self.assertEqual(_('Details of the email'), response.context.get('title'))

    def test_view_lw_email02(self):
        "Cannot view the campaign => error."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW'])

        camp = EmailCampaign.objects.create(user=self.get_root_user(), name='Camp#1')
        self.assertFalse(user.has_perm_to_view(camp))

        sending = EmailSending.objects.create(
            sender='vicious@reddragons.mrs',
            campaign=camp,
            sending_date=now(),
        )

        lw_mail = LightWeightEmail(sending=sending)
        lw_mail.genid_n_save()

        self.assertGET403(reverse('emails__view_sending', args=(sending.id,)))
        self.assertGET403(reverse('emails__sending_body', args=(sending.id,)))
        self.assertGET403(reverse('emails__view_lw_mail', args=(lw_mail.id,)))

    def test_sending_bricks(self):
        user = self.login_as_root_and_get()

        camp = EmailCampaign.objects.create(user=user, name='Camp#1')
        create_sending = partial(
            EmailSending.objects.create,
            sender='vicious@reddragons.mrs',
            campaign=camp,
        )
        sending1 = create_sending(
            sending_date=now(),
            body='My body is ready #1',
            body_html='My body is <b>ready</b> #1',
        )
        sending2 = create_sending(
            sending_date=now() + timedelta(days=2),
            body='My body is ready #2',
            body_html='My body is <b>ready</b> #2',
        )

        response = self.assertGET200(camp.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=SendingsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2, title='{count} Sent bundle', plural_title='{count} Sent bundles',
        )
        self.assertBrickHasAction(
            brick_node, url=sending1.get_absolute_url(), action_type='redirect',
        )
        self.assertBrickHasAction(
            brick_node, url=sending2.get_absolute_url(), action_type='redirect',
        )

    def test_reload_sending_bricks01(self):
        "Not super-user."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW'])

        camp = EmailCampaign.objects.create(user=user, name='Camp#1')
        sending = EmailSending.objects.create(
            sender='vicious@reddragons.mrs',
            campaign=camp,
            sending_date=now(),
            body='My body is ready',
            body_html='My body is <b>ready</b>',
        )

        url = reverse('emails__reload_sending_bricks', args=(sending.id,))
        self.assertGET404(url)  # No brick ID

        response = self.assertGET200(url, data={'brick_id': MailsBrick.id})
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=1)

        brick_data = content[0]
        self.assertEqual(2, len(brick_data))
        self.assertEqual(MailsBrick.id, brick_data[0])
        self.assertIn(f' id="brick-{MailsBrick.id}"', brick_data[1])
        self.assertIn(f' data-brick-id="{MailsBrick.id}"', brick_data[1])

        # TODO: test other bricks

    def test_reload_sending_bricks02(self):
        "Can not see the campaign."
        user = self.login_as_emails_user()
        self.add_credentials(user.role, own=['VIEW'])

        camp = EmailCampaign.objects.create(user=self.get_root_user(), name='Camp#1')
        sending = EmailSending.objects.create(
            sender='vicious@reddragons.mrs',
            campaign=camp,
            sending_date=now(),
            body='My body is ready',
            body_html='My body is <b>ready</b>',
        )

        self.assertGET403(
            reverse('emails__reload_sending_bricks', args=(sending.id,)),
            data={'brick_id': MailsBrick.id},
        )

    def test_reload_sending_bricks03(self):
        "No app perm."
        self.login_as_standard()  # No 'emails'
        self.assertGET403(
            reverse('emails__reload_sending_bricks', args=(self.UNUSED_PK,)),
            data={'brick_id': 'whatever'},
        )

    # TODO?
    # def test_inneredit(self):
    #     user = self.login()
    #     camp = EmailCampaign.objects.create(user=user, name='camp01')
    #     sending = EmailSending.objects.create(
    #         campaign=camp, type=EmailSending.Type.IMMEDIATE,
    #         sending_date=now(), state=EmailSending.State.PLANNED,
    #     )
    #
    #     build_uri = self.build_inneredit_uri
    #     self.assertGET404(build_uri(sending, 'campaign'))
    #     self.assertGET404(build_uri(sending, 'state'))
    #     self.assertGET404(build_uri(sending, 'subject'))
    #     self.assertGET404(build_uri(sending, 'body'))
    #     self.assertGET404(build_uri(sending, 'body_html'))
    #     self.assertGET404(build_uri(sending, 'signature'))
    #     self.assertGET404(build_uri(sending, 'attachments'))
    #     self.assertGET404(build_uri(sending, 'sender'))
    #     self.assertGET404(build_uri(sending, 'type'))
    #     self.assertGET404(build_uri(sending, 'sending_date'))

    def test_next_wakeup01(self):
        "Several deferred sendings."
        user = self.login_as_root_and_get()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=user, name='camp01')

        now_value = now()
        create_sending = partial(
            EmailSending.objects.create, campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
        )
        create_sending(sending_date=now_value + timedelta(weeks=2))
        sending1 = create_sending(sending_date=now_value + timedelta(weeks=1))
        create_sending(sending_date=now_value + timedelta(weeks=3))

        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(sending1.sending_date, wakeup)

    def test_next_wakeup02(self):
        "A deferred sending with passed sending_date."
        user = self.login_as_root_and_get()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        now_value = now()

        EmailSending.objects.create(
            campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
            sending_date=now_value - timedelta(hours=1),
        )

        self.assertLess(job.type.next_wakeup(job, now_value), now_value)

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

    def test_campaign_sent_content_error(self):
        "Campaign does not exist anymore."
        user = self.get_root_user()
        content = CampaignSentContent.from_dict({'instance': self.UNUSED_PK})
        body = _('The campaign has been deleted')
        self.assertEqual(body, content.get_body(user=user))
        self.assertEqual(body, content.get_html_body(user=user))

    @skipIfCustomContact
    def test_job01(self):
        "Deferred => notification."
        user = self.login_as_root_and_get()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='Camp #001')
        sending = EmailSending.objects.create(
            config_item=item,
            sender='vicious@reddragons.mrs',
            campaign=camp,
            type=EmailSending.Type.DEFERRED,
            sending_date=now() - timedelta(hours=1),
            subject='Subject',
            body='My body is ready!',
        )
        LightWeightEmail(
            sending=sending,
            sender=sending.sender,
            recipient='spike.spiegel@bebop.com',
            sending_date=sending.sending_date,
        ).genid_n_save()

        self._send_mails(self._get_job())
        self.assertEqual(1, len(django_mail.outbox))

        notif = self.get_object_or_fail(
            Notification, user=user, channel__uuid=UUID_CHANNEL_JOBS,
        )
        self.assertEqual(CampaignSentContent.id, notif.content_id)
        self.assertDictEqual({'instance': camp.id}, notif.content_data)

    @skipIfCustomContact
    def test_job02(self):
        "Deleted campaign."
        user = self.login_as_root_and_get()
        job = self._get_job()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )
        mlist = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(
            user=user, email='spike.spiegel@bebop.com',
            first_name='Spike', last_name='Spiegel',
        )

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        response = self.client.post(
            self._build_add_url(camp),
            data={
                'config_0': item.id,
                'config_1': 'vicious@reddragons.mrs',

                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        )
        self.assertNoFormError(response)
        self.assertFalse(django_mail.outbox)

        camp.trash()
        self.assertIsNone(job.type.next_wakeup(job, now()))

        self._send_mails(job)
        self.assertFalse(django_mail.outbox)

    @skipIfCustomContact
    def test_job03(self):
        "Deleted config."
        user = self.login_as_root_and_get()
        job = self._get_job()
        item = EmailSendingConfigItem.objects.create(
            name='Config #1',
            host='smail.mydomain.org',
            username='jet@mydomain.org',
            password='c0w|3OY B3b0P',
        )
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )
        mlist = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(
            user=user, email='spike.spiegel@bebop.com',
            first_name='Spike', last_name='Spiegel',
        )

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        self.assertNoFormError(self.client.post(
            self._build_add_url(camp),
            data={
                'config_0': item.id,
                'config_1': 'vicious@reddragons.mrs',

                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        item.delete()
        self.assertStillExists(camp)

        sending = self.get_alone_element(camp.sendings_set.all())
        self.assertEqual(EmailSending.State.PLANNED, sending.state)
        self.assertIsNone(sending.config_item)

        self._send_mails(job)
        self.assertFalse(django_mail.outbox)
        self.assertEqual(EmailSending.State.ERROR, self.refresh(sending).state)
        # TODO: error in job results

    def test_refresh_job01(self):
        "Restore campaign with sending which has to be sent."
        user = self.login_as_root_and_get()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=user, name='camp01', is_deleted=True)

        EmailSending.objects.create(
            campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
            sending_date=now() - timedelta(hours=1),
        )

        queue = get_queue()
        queue.clear()

        camp.restore()
        self.assertFalse(self.refresh(camp).is_deleted)
        self.assertTrue(getattr(camp.restore, 'alters_data', False))

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(job, jobs[0][0])

    def test_refresh_job02(self):
        "Restore campaign with sending which does not have to be sent."
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='camp01', is_deleted=True)

        EmailSending.objects.create(
            campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.DONE,
            sending_date=now() - timedelta(hours=1),
        )

        queue = get_queue()
        queue.clear()

        camp.restore()
        self.assertFalse(queue.refreshed_jobs)

    def test_lw_mails_history(self):
        user = self.login_as_emails_user(allowed_apps=['persons'])
        self.add_credentials(user.role, own=['VIEW'])

        BrickDetailviewLocation.objects.create_if_needed(
            brick=LwMailsHistoryBrick, order=1, zone=BrickDetailviewLocation.RIGHT, model=Contact,
        )
        LwMailsHistoryBrick.page_size = max(settings.BLOCK_SIZE, 2)

        create_camp = EmailCampaign.objects.create
        camp1 = create_camp(user=user,                 name='camp #1')
        camp2 = create_camp(user=self.get_root_user(), name='camp #2')

        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel', email='spike.spiegel@bebop.com',
        )

        create_sending = partial(
            EmailSending.objects.create,
            sender='contact@domain.org', sending_date=now() + timedelta(days=2),
        )
        sending1 = create_sending(campaign=camp1, subject='Allowed subject')
        sending2 = create_sending(campaign=camp2, subject='Forbidden subject')

        create_mail = partial(LightWeightEmail.objects.create, real_recipient=contact)
        lw_mail1 = create_mail(id='73571da6a8a046578b11c4a78e68ea67', sending=sending1)
        lw_mail2 = create_mail(id='737673eead0e43d198c9be8486f373c0', sending=sending2)

        response = self.assertGET200(contact.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=LwMailsHistoryBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Campaign email in the history',
            plural_title='{count} Campaigns emails in the history',
        )
        self.assertBrickHasAction(
            brick_node,
            url=reverse('emails__view_lw_mail', args=(lw_mail1.pk,)),
            action_type='view',
        )
        self.assertBrickHasNoAction(
            brick_node,
            url=reverse('emails__view_lw_mail', args=(lw_mail2.pk,)),
        )
