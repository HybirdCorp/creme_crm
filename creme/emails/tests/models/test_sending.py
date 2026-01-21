from datetime import timedelta

from django.utils.timezone import now

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.models import Job
from creme.emails.creme_jobs import campaign_emails_send_type
from creme.emails.models import EmailSending, EmailSendingConfigItem
from creme.emails.tests.base import EmailCampaign, _EmailsTestCase


class EmailSendingConfigItemTestCase(_EmailsTestCase):
    def test_fields(self):
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


class EmailSendingTestCase(_EmailsTestCase):
    def test_refresh_job__work(self):
        "Restore campaign with sending which has to be sent."
        user = self.login_as_root_and_get()
        job = self.get_object_or_fail(Job, type_id=campaign_emails_send_type.id)
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

    def test_refresh_job__no_work(self):
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
