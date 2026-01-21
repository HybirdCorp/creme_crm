from datetime import timedelta
from functools import partial

from django.core import mail as django_mail
from django.urls import reverse
from django.utils.timezone import now

from creme.creme_core.constants import UUID_CHANNEL_JOBS
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.models import Job, Notification
from creme.emails.creme_jobs import campaign_emails_send_type
from creme.emails.models import (
    EmailSending,
    EmailSendingConfigItem,
    LightWeightEmail,
)
from creme.emails.notification import CampaignSentContent
from creme.persons.tests.base import skipIfCustomContact

from ..base import (
    Contact,
    EmailCampaign,
    EmailTemplate,
    MailingList,
    _EmailsTestCase,
)


class CampaignEmailsSendTestCase(_EmailsTestCase):
    def setUp(self):
        super().setUp()
        self.job = self.get_object_or_fail(Job, type_id=campaign_emails_send_type.id)

    @staticmethod
    def _build_sending_creation_url(campaign):
        return reverse('emails__create_sending', args=(campaign.id,))

    def _run(self):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        campaign_emails_send_type.execute(self.job)

    @skipIfCustomContact
    def test_deferred(self):
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

        self._run()
        self.assertEqual(1, len(django_mail.outbox))

        notif = self.get_object_or_fail(
            Notification, user=user, channel__uuid=UUID_CHANNEL_JOBS,
        )
        self.assertEqual(CampaignSentContent.id, notif.content_id)
        self.assertDictEqual({'instance': camp.id}, notif.content_data)

    @skipIfCustomContact
    def test_deleted_campaign(self):
        user = self.login_as_root_and_get()
        job = self.job
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
            self._build_sending_creation_url(camp),
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

        self._run()
        self.assertFalse(django_mail.outbox)

    @skipIfCustomContact
    def test_deleted_config(self):
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
        mlist = MailingList.objects.create(user=user, name='ml01')
        contact = Contact.objects.create(
            user=user, email='spike.spiegel@bebop.com',
            first_name='Spike', last_name='Spiegel',
        )

        camp.mailing_lists.add(mlist)
        mlist.contacts.add(contact)

        self.assertNoFormError(self.client.post(
            self._build_sending_creation_url(camp),
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

        self._run()
        self.assertFalse(django_mail.outbox)
        self.assertEqual(EmailSending.State.ERROR, self.refresh(sending).state)
        # TODO: error in job results

    def test_next_wakeup__several_deferred(self):
        "Several deferred sendings."
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='camp01')

        now_value = now()
        create_sending = partial(
            EmailSending.objects.create, campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
        )
        create_sending(sending_date=now_value + timedelta(weeks=2))
        sending1 = create_sending(sending_date=now_value + timedelta(weeks=1))
        create_sending(sending_date=now_value + timedelta(weeks=3))

        job = self.job
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(sending1.sending_date, wakeup)

    def test_next_wakeup__deferred_past(self):
        "A deferred sending with passed sending_date."
        user = self.login_as_root_and_get()
        camp = EmailCampaign.objects.create(user=user, name='camp01')
        now_value = now()

        EmailSending.objects.create(
            campaign=camp,
            type=EmailSending.Type.DEFERRED, state=EmailSending.State.PLANNED,
            sending_date=now_value - timedelta(hours=1),
        )

        job = self.job
        self.assertLess(job.type.next_wakeup(job, now_value), now_value)
