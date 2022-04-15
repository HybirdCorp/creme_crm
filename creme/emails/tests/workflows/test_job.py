from datetime import timedelta
from functools import partial
from os.path import basename

from django.core import mail as django_mail
from django.utils.timezone import now

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.models import Job
from creme.documents.tests.base import DocumentsTestCaseMixin
from creme.emails.creme_jobs import workflow_emails_send_type
from creme.emails.models import EmailSignature, WorkflowEmail

from ..base import _EmailsTestCase


class WorkflowEmailTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=workflow_emails_send_type.id)

    def test_create_n_send(self):
        user = self.login_as_root_and_get()

        doc = self._create_doc(title='Attachment #1', user=user)
        sender = 'jet.black@bebop.ura'
        recipient = 'spike.spiegel@bebop.ura'
        subject = 'This is subject'
        body = 'My body is ready'
        body_html = 'My body is <b>ready</b>'
        wf_email = WorkflowEmail.objects.create(
            sender=sender, recipient=recipient, subject=subject,
            body=body, body_html=body_html,
        )
        wf_email.attachments.set([doc])
        self.assertEqual(sender,    wf_email.sender)
        self.assertEqual(recipient, wf_email.recipient)
        self.assertEqual(subject,   wf_email.subject)
        self.assertEqual(body,      wf_email.body)
        self.assertEqual(body_html, wf_email.body_html)
        self.assertIsNone(wf_email.sending_date)
        self.assertEqual(wf_email.Status.NOT_SENT, wf_email.status)

        wf_email.send()

        wf_email = self.refresh(wf_email)
        self.assertEqual(wf_email.Status.SENT, wf_email.status)
        self.assertDatetimesAlmostEqual(now(), wf_email.sending_date)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(sender,      message.from_email)
        self.assertEqual([recipient], message.recipients())
        self.assertEqual(subject,     message.subject)
        self.assertBodiesEqual(message, body=body, body_html=body_html)
        self.assertListEqual(
            [(basename(doc.filedata.name), f'{doc.title}: Content', 'text/plain')],
            message.attachments[1:],  # 0 is for bodies
        )

    def test_job__send(self):
        self.assertFalse(WorkflowEmail.objects.all())

        queue = get_queue()
        queue.clear()

        job = self._get_job()
        self.assertIsNone(
            workflow_emails_send_type.next_wakeup(job=job, now_value=now())
        )

        signature = EmailSignature.objects.create(
            user=self.get_root_user(),
            name='Main signature',
            body='Client relation team',
        )

        sender = 'ed.wong@bebop.ura'
        recipient = 'faye.valentine@bebop.ura'
        subject = 'Hi'
        body = 'This is important'
        body_html = 'This is <b>important</b>'
        wf_email = WorkflowEmail.objects.create(
            sender=sender, recipient=recipient, subject=subject,
            body=body, body_html=body_html,
            signature=signature,
        )
        self.assertEqual(sender,    wf_email.sender)
        self.assertEqual(recipient, wf_email.recipient)
        self.assertEqual(subject,   wf_email.subject)
        self.assertEqual(body,      wf_email.body)
        self.assertIsNone(wf_email.sending_date)
        self.assertEqual(wf_email.Status.NOT_SENT, wf_email.status)

        self.get_alone_element(queue.refreshed_jobs)

        now_value = now()
        next_wakeup = workflow_emails_send_type.next_wakeup(job=job, now_value=now_value)
        self.assertDatetimesAlmostEqual(now_value, next_wakeup)

        # ---
        workflow_emails_send_type.execute(job)
        wf_email = self.refresh(wf_email)
        self.assertEqual(wf_email.Status.SENT, wf_email.status)
        self.assertDatetimesAlmostEqual(now(), wf_email.sending_date)

        messages = django_mail.outbox
        self.assertEqual(len(messages), 1)

        message = messages[0]
        self.assertEqual(sender,      message.from_email)
        self.assertEqual([recipient], message.recipients())
        self.assertEqual(subject,     message.subject)
        self.assertBodiesEqual(
            message,
            body=f'{body}\n\n--\n{signature.body}',
            body_html=(
                f'{body_html}'
                f'<div class="creme-emails-signature" id="signature-{signature.id}">'
                f'<p><br>--<br>{signature.body}</p>'
                f'</div>'
            ),
        )

        self.assertIsNone(
            workflow_emails_send_type.next_wakeup(job=job, now_value=now())
        )

    def test_job__retry(self):
        self.assertFalse(WorkflowEmail.objects.all())

        job = self._get_job()
        wf_email = WorkflowEmail.objects.create(
            sender='ed.wong@bebop.ura',
            recipient='faye.valentine@bebop.ura',
            subject='Hi', body='This is important',
            status=WorkflowEmail.Status.SENDING_ERROR,
            sending_date=now() - timedelta(minutes=5),
        )

        now_value = now()
        next_wakeup = workflow_emails_send_type.next_wakeup(job=job, now_value=now_value)
        self.assertDatetimesAlmostEqual(now_value + timedelta(minutes=15), next_wakeup)

        # ---
        workflow_emails_send_type.execute(job)
        self.assertEqual(len(django_mail.outbox), 1)

        wf_email = self.refresh(wf_email)
        self.assertEqual(wf_email.Status.SENT, wf_email.status)
        self.assertDatetimesAlmostEqual(now(), wf_email.sending_date)

    def test_job__remove_old_emails(self):
        self.assertFalse(WorkflowEmail.objects.all())

        now_value = now()
        create_mail = partial(
            WorkflowEmail.objects.create,
            sender='ed.wong@bebop.ura',
            recipient='faye.valentine@bebop.ura',
            subject='Hi', body='This is important',
            status=WorkflowEmail.Status.SENT,
        )
        wf_email1 = create_mail(
            status=WorkflowEmail.Status.SENDING_ERROR,
            sending_date=now_value - timedelta(days=100),
        )
        wf_email2 = create_mail(sending_date=now_value - timedelta(days=1))
        wf_email3 = create_mail(sending_date=now_value - timedelta(days=40))

        workflow_emails_send_type.execute(self._get_job())
        self.assertStillExists(wf_email1)
        self.assertStillExists(wf_email2)
        self.assertDoesNotExist(wf_email3)
