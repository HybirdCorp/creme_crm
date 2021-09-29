# -*- coding: utf-8 -*-

from datetime import timedelta
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core import mail as django_mail
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import format_html
from django.utils.timezone import get_current_timezone, make_naive, now
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
# Should be a test queue
# from creme.creme_core.core.job import JobSchedulerQueue
from creme.creme_core.core.job import get_queue
from creme.creme_core.gui.history import html_history_registry
from creme.creme_core.models import (
    FakeOrganisation,
    HistoryLine,
    Job,
    SetCredentials,
    SettingValue,
)
from creme.creme_core.models.history import TYPE_AUX_CREATION
from creme.persons.models import Civility
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..bricks import MailsBrick
from ..constants import SETTING_EMAILCAMPAIGN_SENDER  # MAIL_STATUS_NOTSENT
from ..creme_jobs import campaign_emails_send_type
from ..models import EmailRecipient, EmailSending, LightWeightEmail
# from ..models.sending import (
#     SENDING_STATE_DONE,
#     SENDING_STATE_PLANNED,
#     SENDING_TYPE_DEFERRED,
#     SENDING_TYPE_IMMEDIATE,
# )
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


@skipIfCustomEmailCampaign
@skipIfCustomEmailTemplate
@skipIfCustomMailingList
class SendingsTestCase(_EmailsTestCase):
    @staticmethod
    def _build_add_url(campaign):
        return reverse('emails__create_sending', args=(campaign.id,))

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=campaign_emails_send_type.id)

    def _send_mails(self, job=None):
        campaign_emails_send_type.execute(job or self._get_job())

    def test_sender_setting01(self):
        user = self.login()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='SUBJECT', body='BODY',
        )

        url = self._build_add_url(camp)
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(
            _('New sending for «{entity}»').format(entity=camp),
            context.get('title'),
        )
        self.assertEqual(EmailSending.save_label, context.get('submit_label'))

        with self.assertNoException():
            sender = context['form'].fields['sender']
        self.assertIsNone(sender.initial)

        sender_email = 'vicious@reddragons.mrs'
        self.assertNoFormError(self.client.post(
            url,
            data={
                'sender':   sender_email,
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        # --
        response = self.assertGET200(url)

        with self.assertNoException():
            sender = response.context['form'].fields['sender']

        self.assertEqual(sender_email, sender.initial)

        response = self.assertPOST200(
            url,
            data={
                'sender':   'another_email@address.com',
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        )
        self.assertFormError(
            response, 'form', 'sender',
            _(
                'You are not allowed to modify the sender address, '
                'please contact your administrator.'
            ),
        )

    def test_sender_setting02(self):
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
                | EntityCredentials.CHANGE
            ),
            set_type=SetCredentials.ESET_ALL
        )

        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='SUBJECT', body='BODY',
        )

        url = self._build_add_url(camp)
        response = self.assertGET200(url)

        with self.assertNoException():
            sender = response.context['form'].fields['sender']

        self.assertEqual(
            _(
                'No sender email address has been configured, '
                'please contact your administrator.'
            ),
            sender.initial,
        )
        sender_email = 'vicious@reddragons.mrs'

        self.assertFormError(
            self.client.post(
                url,
                data={
                    'sender': sender_email,
                    # 'type': SENDING_TYPE_IMMEDIATE,
                    'type': EmailSending.Type.IMMEDIATE,
                    'template': template.id,
                },
            ),
            'form', 'sender',
            _(
                'You are not allowed to modify the sender address, '
                'please contact your administrator.'
            ),
        )

        sender_setting = SettingValue.objects.get(key_id=SETTING_EMAILCAMPAIGN_SENDER)
        sender_setting.value = sender_email
        sender_setting.save()

        response = self.assertGET200(url)

        with self.assertNoException():
            sender = response.context['form'].fields['sender']

        self.assertEqual(sender_email, sender.initial)

        self.assertNoFormError(self.client.post(
            url,
            data={
                'sender':   sender_email,
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

    @skipIfCustomContact
    @skipIfCustomOrganisation
    def test_create01(self):
        user = self.login()
        # We create voluntarily duplicates (recipients that have same addresses
        # than Contact/Organisation, MailingList that contain the same addresses)
        # EmailSending should not contain duplicates.
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
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(
            url,
            data={
                'sender':   'vicious@reddragons.mrs',
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        sendings = EmailCampaign.objects.get(pk=camp.id).sendings_set.all()
        self.assertEqual(1, len(sendings))

        sending = sendings[0]
        # self.assertEqual(SENDING_TYPE_IMMEDIATE, sending.type)
        self.assertEqual(EmailSending.Type.IMMEDIATE, sending.type)
        # self.assertEqual(SENDING_STATE_PLANNED,  sending.state)
        self.assertEqual(EmailSending.State.PLANNED,  sending.state)
        self.assertEqual(subject,                sending.subject)
        self.assertEqual(body,                   sending.body)
        self.assertEqual('',                     sending.body_html)

        mails = sending.mails_set.all()
        self.assertEqual(len(addresses), len(mails))

        addr_set = {mail.recipient for mail in mails}
        self.assertTrue(all(address in addr_set for address in addresses))

        related_set = {mail.recipient_entity_id for mail in mails}
        self.assertTrue(all(c.id in related_set for c in contacts))
        self.assertTrue(all(o.id in related_set for o in orgas))

        self.assertEqual('', sending.mails_set.filter(recipient_entity=None)[0].body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=contacts[0].id).body)
        self.assertEqual('', sending.mails_set.get(recipient_entity=orgas[0].id).body)

        # ---
        self.assertEqual(old_hlines_count + 1, HistoryLine.objects.count())

        hline = HistoryLine.objects.order_by('-id').first()
        self.assertEqual(camp.id,          hline.entity.id)
        self.assertEqual(TYPE_AUX_CREATION,    hline.type)
        self.assertListEqual(
            [
                _('Add <{type}>: “{value}”').format(
                    type=EmailSending._meta.verbose_name,
                    value=sending,
                )
            ],
            hline.get_verbose_modifications(user=user),
        )
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
        # self.assertEqual(MAIL_STATUS_NOTSENT, mail.status)
        self.assertEqual(LightWeightEmail.Status.NOT_SENT, mail.status)

        response1 = self.assertGET200(reverse('emails__view_lw_mail', args=(mail.id,)))
        self.assertTemplateUsed(response1, 'creme_core/generics/detail-popup.html')
        self.assertEqual(_('Details of the email'), response1.context.get('title'))
        self.assertEqual('DENY', response1.get('X-Frame-Options'))

        # ---
        response2 = self.assertGET200(reverse('emails__lw_mail_body', args=(mail.id,)))
        self.assertEqual(b'', response2.content)
        self.assertEqual('SAMEORIGIN', response2.get('X-Frame-Options'))

        # Detail view ----------------------------------------------------------
        # detail_url = reverse('emails__view_sending', args=(sending.id,))
        detail_url = sending.get_absolute_url()
        self.assertPOST405(detail_url)

        response3 = self.assertGET200(detail_url)
        self.assertTemplateUsed(response3, 'emails/view_sending.html')
        self.assertEqual(sending, response3.context.get('object'))

        self.assertContains(response3, contacts[0].email)
        self.assertContains(response3, orgas[0].email)

        # HTML body ----------------------------------------------------------
        body_url = reverse('emails__sending_body', args=(sending.id,))
        self.assertPOST405(body_url)

        response4 = self.assertGET200(body_url)
        self.assertEqual(b'', response4.content)
        self.assertEqual('SAMEORIGIN', response4.get('X-Frame-Options'))

        # Test delete campaign -------------------------------------------------
        camp.trash()
        self.assertPOST(302, camp.get_delete_absolute_url())
        self.assertFalse(EmailCampaign.objects.exists())
        self.assertFalse(EmailSending.objects.exists())
        self.assertFalse(LightWeightEmail.objects.exists())

    @skipIfCustomContact
    def test_create02(self):
        "Test template."
        user = self.login()
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
        response = self.client.post(
            self._build_add_url(camp),
            data={
                'sender':   'vicious@reddragons.mrs',
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        )
        self.assertNoFormError(response)

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

        # View template --------------------------------------------------------
        response = self.assertGET200(reverse('emails__sending_body', args=(sending.id,)))
        self.assertEqual(template.body_html.encode(), response.content)

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
        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        job = self._get_job()
        now_value = now()
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        user = self.login()
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
                'sender':   sender,
                # 'type':     SENDING_TYPE_IMMEDIATE,
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

        # self.assertEqual(SENDING_STATE_DONE, sending.state)
        self.assertEqual(EmailSending.State.DONE, sending.state)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 3)

        message = messages[0]
        self.assertEqual(template.subject, message.subject)
        self.assertEqual(template.body,    message.body)
        self.assertEqual(sender,           message.from_email)
        self.assertListEqual([('', 'text/html')], message.alternatives)
        self.assertFalse(message.attachments)

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

    def test_create04(self):
        "Test deferred"
        user = self.login()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )

        now_value = now()
        sending_date = now_value + timedelta(weeks=1)
        naive_sending_date = make_naive(sending_date, get_current_timezone())
        data = {
            'sender':   'vicious@reddragons.mrs',
            # 'type':     SENDING_TYPE_DEFERRED,
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

        self.assertFormError(
            post(data=data), 'form', 'sending_date',
            _('Sending date required for a deferred sending'),
        )

        msg = _('Sending date must be is the future')
        self.assertFormError(
            post(data={
                **data,
                'sending_date': (now_value - timedelta(days=1)).strftime('%Y-%m-%d'),
            }),
            'form', 'sending_date', msg,
        )
        self.assertFormError(
            post(data={
                **data,
                'sending_date': now_value.strftime('%Y-%m-%d'),
            }),
            'form', 'sending_date', msg,
        )

    def test_create05(self):
        "Test deferred (today)."
        user = self.login()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        template = EmailTemplate.objects.create(
            user=user, name='name', subject='subject', body='body',
        )

        now_dt = now()
        sending_date = now_dt + timedelta(hours=1)  # Today if we run the test before 23h...

        naive_sending_date = make_naive(sending_date, get_current_timezone())
        data = {
            'sender':   'vicious@reddragons.mrs',
            # 'type':     SENDING_TYPE_DEFERRED,
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
        user = self.login()

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
                'sender':   'vicious@reddragons.mrs',
                # 'type':     SENDING_TYPE_IMMEDIATE,
                'type':     EmailSending.Type.IMMEDIATE,
                'template': template.id,
            },
        ))

        self._send_mails(self._get_job())
        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual('Hello Spike Spiegel !', message.body)
        self.assertListEqual(
            [('<b>Hello</b> Spike Spiegel !', 'text/html')],
            message.alternatives,
        )

    def test_create07(self):
        "No related to a campaign => error"
        user = self.login()
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        self.assertGET404(self._build_add_url(nerv))

    def test_view_lw_email01(self):
        "Not super-user"
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

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
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        camp = EmailCampaign.objects.create(user=self.other_user, name='Camp#1')
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

    def test_reload_sending_bricks01(self):
        "Not super-user."
        user = self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

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

        response = self.assertGET200(url, data={'brick_id': MailsBrick.id_})
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=1)

        brick_data = content[0]
        self.assertEqual(2, len(brick_data))
        self.assertEqual(MailsBrick.id_, brick_data[0])
        self.assertIn(f' id="{MailsBrick.id_}"', brick_data[1])

        # TODO: test other bricks

    def test_reload_sending_bricks02(self):
        "Can not see the campaign"
        self.login(is_superuser=False)
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW,
            set_type=SetCredentials.ESET_OWN,
        )

        camp = EmailCampaign.objects.create(user=self.other_user, name='Camp#1')
        sending = EmailSending.objects.create(
            sender='vicious@reddragons.mrs',
            campaign=camp,
            sending_date=now(),
            body='My body is ready',
            body_html='My body is <b>ready</b>',
        )

        self.assertGET403(
            reverse('emails__reload_sending_bricks', args=(sending.id,)),
            data={'brick_id': MailsBrick.id_}
        )

    def test_inneredit(self):
        user = self.login()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        sending = EmailSending.objects.create(
            # campaign=camp, type=SENDING_TYPE_IMMEDIATE,
            campaign=camp, type=EmailSending.Type.IMMEDIATE,
            # sending_date=now(), state=SENDING_STATE_PLANNED,
            sending_date=now(), state=EmailSending.State.PLANNED,
        )

        build_url = self.build_inneredit_url
        self.assertGET(400, build_url(sending, 'campaign'))
        self.assertGET(400, build_url(sending, 'state'))
        self.assertGET(400, build_url(sending, 'subject'))
        self.assertGET(400, build_url(sending, 'body'))
        self.assertGET(400, build_url(sending, 'body_html'))
        self.assertGET(400, build_url(sending, 'signature'))
        self.assertGET(400, build_url(sending, 'attachments'))

        self.assertGET(400, build_url(sending, 'sender'))
        self.assertGET(400, build_url(sending, 'type'))
        self.assertGET(400, build_url(sending, 'sending_date'))

    def test_next_wakeup01(self):
        "Several deferred sendings."
        user = self.login()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=user, name='camp01')

        now_value = now()
        create_sending = partial(
            EmailSending.objects.create, campaign=camp,
            # type=SENDING_TYPE_DEFERRED, state=SENDING_STATE_PLANNED,
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
        self.login()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=self.user, name='camp01')
        now_value = now()

        EmailSending.objects.create(
            campaign=camp,
            # type=SENDING_TYPE_DEFERRED, state=SENDING_STATE_PLANNED,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
            sending_date=now_value - timedelta(hours=1),
        )

        self.assertLess(job.type.next_wakeup(job, now_value), now_value)

    @skipIfCustomContact
    def test_job(self):
        "Deleted campaign."
        user = self.login()
        job = self._get_job()
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

        sender = 'vicious@reddragons.mrs'
        response = self.client.post(
            self._build_add_url(camp),
            data={
                'sender':   sender,
                # 'type':     SENDING_TYPE_IMMEDIATE,
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

    def test_refresh_job01(self):
        "Restore campaign with sending which has to be sent."
        self.login()
        job = self._get_job()
        camp = EmailCampaign.objects.create(user=self.user, name='camp01', is_deleted=True)

        EmailSending.objects.create(
            campaign=camp,
            # type=SENDING_TYPE_DEFERRED, state=SENDING_STATE_PLANNED,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
            sending_date=now() - timedelta(hours=1),
        )

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        camp.restore()
        self.assertFalse(self.refresh(camp).is_deleted)

        jobs = queue.refreshed_jobs
        self.assertEqual(1, len(jobs))
        self.assertEqual(job, jobs[0][0])

    def test_refresh_job02(self):
        "Restore campaign with sending which does not have to be sent."
        self.login()
        camp = EmailCampaign.objects.create(user=self.user, name='camp01', is_deleted=True)

        EmailSending.objects.create(
            campaign=camp,
            # type=SENDING_TYPE_DEFERRED, state=SENDING_STATE_DONE,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.DONE,
            sending_date=now() - timedelta(hours=1),
        )

        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        camp.restore()
        self.assertFalse(queue.refreshed_jobs)
