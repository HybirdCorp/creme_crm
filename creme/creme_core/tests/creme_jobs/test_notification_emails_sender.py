from datetime import timedelta
from functools import partial

from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.test.utils import override_settings
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.notification import (
    OUTPUT_EMAIL,
    OUTPUT_WEB,
    SimpleNotifContent,
)
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.creme_jobs import (
    notification_emails_sender_type as sender_type,
)
from creme.creme_core.models import (
    Job,
    JobResult,
    Notification,
    NotificationChannel,
)
from creme.creme_core.utils.dates import dt_from_ISO8601, dt_to_ISO8601

from ..base import CremeTestCase

SOFTWARE_LABEL = 'My CRM'
EMAIL_SENDER = 'sender@domain.org'


class NotificationEmailsSenderTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def tearDown(self):
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=sender_type.id)

    def _send_mails(self, job):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        sender_type.execute(job)

    @override_settings(
        SOFTWARE_LABEL=SOFTWARE_LABEL,
        EMAIL_SENDER=EMAIL_SENDER,
    )
    def test_ok(self):
        user = self.login_as_standard()

        job = self._get_job()
        self.assertIsNone(sender_type.next_wakeup(job=job, now_value=now()))

        chan = NotificationChannel.objects.first()

        subject1 = 'Hello...'
        body1 = '...world'
        html_body1 = '<b>world</b>!'
        subject2 = 'Hi!'
        body2 = 'How are you?'
        create_notif = partial(
            Notification.objects.create, channel=chan, user=user, output=OUTPUT_EMAIL,
        )
        notif1 = create_notif(
            content=SimpleNotifContent(subject=subject1, body=body1, html_body=html_body1),
        )
        create_notif(content=SimpleNotifContent(subject=subject2, body=body2))
        create_notif(
            content=SimpleNotifContent(subject='Not email', body='Ignored'),
            output=OUTPUT_WEB,
        )
        create_notif(
            content=SimpleNotifContent(subject='Already sent', body='Ignored'),
            extra_data={'sent': dt_to_ISO8601(now() - timedelta(hours=1))},
        )

        now_value = now()
        self.assertEqual(now_value, sender_type.next_wakeup(job=job, now_value=now_value))

        self._send_mails(job)
        self.assertFalse(self.refresh(notif1).discarded)

        messages = mail.outbox
        self.assertEqual(len(messages), 2)

        message1 = messages[0]
        self.assertEqual([user.email], message1.to)
        self.assertEqual(EMAIL_SENDER, message1.from_email)
        self.assertFalse(message1.attachments)
        self.assertEqual(
            _('[Notification from {software}] {subject}').format(
                software=SOFTWARE_LABEL, subject=subject2,
            ),
            message1.subject,
        )
        self.assertEqual(body2, message1.body)
        self.assertListEqual([], message1.alternatives)

        message2 = messages[1]
        self.assertEqual(body1, message2.body)
        self.assertListEqual([(html_body1, 'text/html')], message2.alternatives)

        sent_str = self.refresh(notif1).extra_data.get('sent')
        self.assertIsInstance(sent_str, str)
        with self.assertNoException():
            sent_date = dt_from_ISO8601(sent_str)
        self.assertDatetimesAlmostEqual(now(), sent_date)

        self.assertIsNone(sender_type.next_wakeup(job=job, now_value=now()))

    def test_emails_error(self):
        user = self.login_as_standard()

        job = self._get_job()
        self.assertIsNone(sender_type.next_wakeup(job=job, now_value=now()))

        chan = NotificationChannel.objects.first()
        Notification.objects.create(
            channel=chan, user=user, output=OUTPUT_EMAIL,
            content=SimpleNotifContent(subject='*subject*', body='*body*'),
        )

        send_messages_called = False
        err_msg = 'Sent error'

        def send_messages(this, messages):
            nonlocal send_messages_called
            send_messages_called = True
            raise Exception(err_msg)

        EmailBackend.send_messages = send_messages
        self._send_mails(job)

        self.assertTrue(send_messages_called)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _("An error occurred while sending notification's emails"),
                _('Original error: {}').format(err_msg),
            ],
            jresult.messages,
        )
