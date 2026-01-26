from datetime import timedelta

from django.conf import settings
from django.core import mail
from django.core.mail.backends.locmem import EmailBackend
from django.test.utils import override_settings
from django.utils.translation import gettext as _

from creme.commercial.creme_jobs import com_approaches_emails_send_type
from creme.commercial.models import CommercialApproach
from creme.creme_core.core.workflow import WorkflowEngine
from creme.creme_core.models import Job, JobResult, Relation
from creme.creme_core.tests.base import CremeTestCase
from creme.opportunities.models import SalesPhase
from creme.opportunities.tests.base import skipIfCustomOpportunity
from creme.persons.constants import (
    REL_SUB_CUSTOMER_SUPPLIER,
    REL_SUB_EMPLOYED_BY,
    REL_SUB_MANAGES,
)
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .base import Contact, Opportunity, Organisation


@skipIfCustomOrganisation
class ComApproachesEmailsSendTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.original_send_messages = EmailBackend.send_messages

    def setUp(self):
        super().setUp()
        self.user = self.login_as_root_and_get()

    def tearDown(self):
        super().tearDown()
        EmailBackend.send_messages = self.original_send_messages

    def _send_mails(self):
        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        job = self.get_object_or_fail(Job, type_id=com_approaches_emails_send_type.id)
        self.assertIsNone(job.user)

        com_approaches_emails_send_type.execute(job)

        return job

    def _build_orgas(self):
        user = self.user
        mngd_orga = Organisation.objects.filter_managed_by_creme()[0]
        customer  = Organisation.objects.create(user=user, name='NERV')

        Relation.objects.create(
            user=user, subject_entity=customer,
            type_id=REL_SUB_CUSTOMER_SUPPLIER,
            object_entity=mngd_orga,
        )

        return mngd_orga, customer

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_neglected(self):
        "Customer has no CommercialApproach."
        self._send_mails()
        self.assertFalse(mail.outbox)

        mngd_orga, customer = self._build_orgas()

        self._send_mails()
        messages = mail.outbox

        message = self.get_alone_element(messages)
        self.assertEqual(
            _('[{software}] The organisation «{organisation}» seems neglected').format(
                software='My CRM', organisation=customer,
            ),
            message.subject,
        )
        self.assertEqual(
            _(
                "It seems you haven't created a commercial approach "
                "for the organisation «{orga}» since {delay} days."
            ).format(orga=customer, delay=30),
            message.body,
        )
        self.assertEqual(settings.EMAIL_SENDER, message.from_email)
        self.assertHasNoAttr(message, 'alternatives')
        self.assertFalse(message.attachments)
        self.assertListEqual(
            [self.user.email],
            [recipient for msg in messages for recipient in msg.recipients()],
        )

    def test_not_neglected(self):
        "A Commercial Approach is linked to the customer."
        mngd_orga, customer = self._build_orgas()

        CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=customer,
        )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_old_approach(self):
        "The linked Commercial Approach is too old."
        mngd_orga, customer = self._build_orgas()

        commapp = CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=customer,
        )

        CommercialApproach.objects.filter(
            id=commapp.id,
        ).update(creation_date=commapp.creation_date - timedelta(days=31))

        self._send_mails()
        self.assertEqual(1, len(mail.outbox))

    @skipIfCustomContact
    def test_linked_to_manager(self):
        "A Commercial Approach is linked to a manager."
        mngd_orga, customer = self._build_orgas()

        manager = Contact.objects.create(
            user=self.user, first_name='Ryoga', last_name='Hibiki',
        )
        Relation.objects.create(
            user=self.user, subject_entity=manager,
            type_id=REL_SUB_MANAGES,
            object_entity=customer,
        )

        CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=manager,
        )

        self._send_mails()
        self.assertFalse(mail.outbox)

    @skipIfCustomContact
    def test_linked_to_employee(self):
        "A Commercial Approach is linked to an employee."
        mngd_orga, customer = self._build_orgas()

        employee = Contact.objects.create(
            user=self.user, first_name='Ryoga', last_name='Hibiki',
        )
        Relation.objects.create(
            user=self.user, subject_entity=employee,
            type_id=REL_SUB_EMPLOYED_BY,
            object_entity=customer,
        )

        CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=employee,
        )

        self._send_mails()
        self.assertFalse(mail.outbox)

    @skipIfCustomOpportunity
    def test_linked_to_opportunity(self):
        "A Commercial Approach is linked to an Opportunity."
        mngd_orga, customer = self._build_orgas()

        opp = Opportunity.objects.create(
            user=self.user, name='Opp custo',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=mngd_orga, target=customer,
        )

        CommercialApproach.objects.create(
            title='Commapp01',
            description='A commercial approach',
            creme_entity=opp,
        )

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_ignored__organisations(self):
        "Ignore the managed organisations which are customer of another managed organisation."
        mngd_orga, customer = self._build_orgas()

        customer.is_managed = True
        customer.save()

        self._send_mails()
        self.assertFalse(mail.outbox)

    def test_error(self):
        "Sending error."
        self._build_orgas()

        self.send_messages_called = False
        err_msg = 'Sent error'

        def send_messages(this, messages):
            self.send_messages_called = True
            raise Exception(err_msg)

        EmailBackend.send_messages = send_messages

        job = self._send_mails()
        self.assertFalse(mail.outbox)

        jresult = self.get_alone_element(JobResult.objects.filter(job=job))
        self.assertListEqual(
            [
                _('An error has occurred while sending emails'),
                _('Original error: {}').format(err_msg),
            ],
            jresult.messages,
        )
