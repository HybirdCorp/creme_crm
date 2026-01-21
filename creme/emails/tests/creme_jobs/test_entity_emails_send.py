from datetime import timedelta

from django.core import mail
from django.utils.timezone import now

from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.workflow import WorkflowConditions, WorkflowEngine
from creme.creme_core.models import CremePropertyType, Job, Workflow
from creme.emails.creme_jobs import entity_emails_send_type

from ..base import EntityEmail, _EmailsTestCase, skipIfCustomEntityEmail


@skipIfCustomEntityEmail
class EntityEmailsSendTypeTestCase(_EmailsTestCase):
    def setUp(self):
        super().setUp()
        self.job = self.get_object_or_fail(Job, type_id=entity_emails_send_type.id)

    def _run(self):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        entity_emails_send_type.execute(self.job)

    def test_ok(self):
        user = self.login_as_root_and_get()
        now_value = now()

        ptype = CremePropertyType.objects.create(text='Sent this year')
        source = workflows.EditedEntitySource(model=EntityEmail)
        Workflow.objects.create(
            title='WF for EntityEmail',
            content_type=EntityEmail,
            trigger=workflows.EntityEditionTrigger(model=EntityEmail),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    condition_handler.DateRegularFieldConditionHandler.build_condition(
                        model=EntityEmail,
                        field_name='sending_date',
                        date_range='current_year',
                    ),
                ],
            ),
            actions=[workflows.PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        job = self.job
        self.assertIsNone(job.user)
        self.assertIsNone(job.type.next_wakeup(job, now_value))

        email = self._create_email(user=user, status=EntityEmail.Status.NOT_SENT)
        self.clear_global_info()  # Clear the event queue to allow edition event

        self.assertIs(job.type.next_wakeup(job, now_value), now_value)
        self.assertIsNone(email.sending_date)

        self._run()

        message = self.get_alone_element(mail.outbox)
        self.assertEqual(email.subject, message.subject)
        self.assertBodiesEqual(message, body=email.body, body_html=email.body_html)

        email = self.refresh(email)
        self.assertDatetimesAlmostEqual(now(), email.sending_date)
        self.assertHasProperty(entity=email, ptype=ptype)

    def test_error_n_retry(self):
        from creme.emails.creme_jobs import entity_emails_send

        user = self.login_as_root_and_get()
        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)

        job = self.job
        now_value = now()
        wakeup = job.type.next_wakeup(job, now_value)
        self.assertIsNotNone(wakeup)
        self.assertDatetimesAlmostEqual(
            now_value + timedelta(minutes=entity_emails_send.ENTITY_EMAILS_RETRY),
            wakeup,
        )

        self._run()

        message = self.get_alone_element(mail.outbox)
        self.assertEqual(email.subject, message.subject)
        self.assertBodiesEqual(message, body=email.body, body_html=email.body_html)

    def test_email_already_sent(self):
        user = self.login_as_root_and_get()
        self._create_email(user=user, status=EntityEmail.Status.SENT)
        self._run()

        self.assertFalse(mail.outbox)

    def test_deleted_email(self):
        "Email is in the trash."
        user = self.login_as_root_and_get()
        email = self._create_email(user=user, status=EntityEmail.Status.SENDING_ERROR)
        email.trash()

        job = self.job
        self.assertIsNone(job.type.next_wakeup(job, now()))

        self._run()
        self.assertFalse(mail.outbox)
