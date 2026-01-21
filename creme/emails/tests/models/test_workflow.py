from os.path import basename

from django.core import mail as django_mail
from django.utils.timezone import now

from creme.documents.tests.base import DocumentsTestCaseMixin
from creme.emails.models import WorkflowEmail

from ..base import _EmailsTestCase


class WorkflowEmailTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
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
