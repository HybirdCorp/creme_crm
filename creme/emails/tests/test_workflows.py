from datetime import timedelta
from functools import partial
from uuid import uuid4

from django.core import mail as django_mail
from django.test.utils import override_settings
from django.utils.timezone import now
from django.utils.translation import gettext as _

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.workflow import workflow_registry
from creme.creme_core.models import (
    FakeContact,
    FakeImage,
    FakeOrganisation,
    Job,
    Workflow,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    FixedEntitySource,
)

from ..creme_jobs import workflow_emails_send_type
from ..forms.workflows import (
    ActionRecipientField,
    EmailSendingActionForm,
    FixedUserRecipientField,
    LiteralRecipientField,
    RegularEmailFieldRecipientField,
    UserFKRecipientField,
)
from ..models import WorkflowEmail
from ..workflows import (
    ActionRecipientsRegistry,
    EmailSendingAction,
    FixedUserRecipient,
    LiteralRecipient,
    RegularEmailFieldRecipient,
    UserFKRecipient,
    recipients_registry,
)
from .base import EntityEmail, _EmailsTestCase

test_sender = 'creme@mydomain.org'


class ActionRecipientsTestCase(_EmailsTestCase):
    def test_literal(self):
        user = self.get_root_user()

        type_id = 'literal'
        email1 = 'spike.spiegel@bebop.mrs'
        recipient1 = LiteralRecipient(email_address=email1)
        self.assertEqual(type_id, recipient1.type_id)
        self.assertEqual(email1,  recipient1.email_address)
        self.assertDictEqual(
            {'type': type_id, 'email': email1}, recipient1.to_dict(),
        )
        self.assertEqual(
            _('To: {recipient}').format(recipient=email1),
            recipient1.render(user=user),
        )
        # self.assertEqual(email1, recipient1.extract({}))
        self.assertTupleEqual((email1, None), recipient1.extract({}))

        # Other values ---
        email2 = 'jet.black@bebop.mrs'
        recipient2 = LiteralRecipient(email_address=email2)
        self.assertEqual(type_id, recipient2.type_id)
        self.assertEqual(email2,  recipient2.email_address)
        self.assertEqual(
            _('To: {recipient}').format(recipient=email2),
            recipient2.render(user=user),
        )
        # self.assertEqual(email2, recipient2.extract({}))
        self.assertTupleEqual((email2, None), recipient2.extract({}))

        serialized = {'type': type_id, 'email': email2}
        self.assertDictEqual(serialized, recipient2.to_dict())

        # __eq__ ---
        self.assertEqual(recipient1, LiteralRecipient(email_address=email1))
        self.assertNotEqual(recipient1, recipient2)
        self.assertNotEqual(None, recipient1)

        # Deserialization ---
        self.assertEqual(
            recipient2,
            LiteralRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

        # Configuration ---
        formfield = LiteralRecipient.config_formfield(user=user)
        self.assertIsInstance(formfield, LiteralRecipientField)
        self.assertEqual(_('Fixed email address'), formfield.label)

        self.assertIsNone(LiteralRecipient.config_formfield(
            user=user, entity_source=CreatedEntitySource(model=FakeContact),
        ))

    def test_fixed_user(self):
        user1 = self.get_root_user()

        type_id = 'fixed_user'
        recipient1 = FixedUserRecipient(user=user1)
        self.assertEqual(type_id, recipient1.type_id)
        self.assertEqual(user1,   recipient1.user)
        self.assertDictEqual(
            # {'type': type_id, 'user': user1.username}, recipient1.to_dict(),
            {'type': type_id, 'user': str(user1.uuid)}, recipient1.to_dict(),
        )
        self.assertEqual(
            _('To: {user} <{email}>').format(user=user1, email=user1.email),
            recipient1.render(user=user1),
        )
        # self.assertEqual(user1.email, recipient1.extract({}))
        self.assertTupleEqual((user1.email, None), recipient1.extract({}))

        # Other values + username ---
        user2 = self.create_user()
        # recipient2 = FixedUserRecipient(user=user2.username)
        recipient2 = FixedUserRecipient(user=str(user2.uuid))
        self.assertEqual(type_id, recipient2.type_id)
        self.assertEqual(user2,   recipient2.user)
        self.assertEqual(
            _('To: {user} <{email}>').format(user=user2, email=user2.email),
            recipient2.render(user=user1),
        )
        # self.assertEqual(user2.email, recipient2.extract({}))
        self.assertTupleEqual((user2.email, None), recipient2.extract({}))

        # serialized = {'type': type_id, 'user': user2.username}
        serialized = {'type': type_id, 'user': str(user2.uuid)}
        self.assertDictEqual(serialized, recipient2.to_dict())

        # __eq__
        # self.assertEqual(recipient1, FixedUserRecipient(user=user1.username))
        self.assertEqual(recipient1, FixedUserRecipient(user=user1))
        self.assertNotEqual(recipient1, recipient2)
        self.assertNotEqual(None, recipient1)

        # Deserialization ---
        self.assertEqual(
            recipient2,
            FixedUserRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

        # Configuration ---
        formfield = FixedUserRecipient.config_formfield(user=user1)
        self.assertIsInstance(formfield, FixedUserRecipientField)
        self.assertEqual(_('Fixed user'), formfield.label)

        self.assertIsNone(FixedUserRecipient.config_formfield(
            user=user1, entity_source=CreatedEntitySource(model=FakeContact),
        ))

    def test_user_fk(self):
        user1 = self.get_root_user()

        type_id = 'user_fk'
        source1 = CreatedEntitySource(model=FakeOrganisation)
        field_name1 = 'user'
        recipient1 = UserFKRecipient(entity_source=source1, field_name=field_name1)
        self.assertEqual(type_id,    recipient1.type_id)
        self.assertEqual(source1,     recipient1.entity_source)
        self.assertEqual(field_name1, recipient1.field_name)
        self.assertEqual(
            _('To: user «{field}» of: {source}').format(
                field=_('Owner user'),
                source=source1.render(user=user1, mode=source1.HTML),
            ),
            recipient1.render(user=user1),
        )

        serialized = {
            'type': type_id,
            'entity': source1.to_dict(),
            'field': field_name1,
        }
        self.assertDictEqual(serialized, recipient1.to_dict())

        user2 = self.create_user(index=0)
        contact = FakeOrganisation.objects.create(user=user2, name='Bebop')
        self.assertTupleEqual(
            (user2.email, None),  # Not an email field, we ignore 'contact'
            recipient1.extract({CreatedEntitySource.type_id: contact}),
        )

        # Other values ---
        source2 = EditedEntitySource(model=FakeContact)
        field_name2 = 'is_user'
        recipient2 = UserFKRecipient(entity_source=source2, field_name=field_name2)
        self.assertEqual(source2,     recipient2.entity_source)
        self.assertEqual(field_name2, recipient2.field_name)
        self.assertEqual(
            _('To: user «{field}» of: {source}').format(
                field=_('Related user'),
                source=source2.render(user=user1, mode=source2.HTML),
            ),
            recipient2.render(user=user1),
        )
        user3 = self.create_user(index=1)
        self.assertTupleEqual(
            (user3.email, None),
            recipient2.extract({
                EditedEntitySource.type_id: FakeContact.objects.create(
                    user=user2, first_name='Spike', last_name='Spiegel',
                    is_user=user3,  # <==
                ),
            })
        )
        self.assertTupleEqual(
            ('', None),
            recipient2.extract({
                EditedEntitySource.type_id: FakeContact.objects.create(
                    user=user2, first_name='Faye', last_name='Valentine',
                    # is_user=user3,  NOPE
                ),
            }),
        )

        # __eq__
        self.assertEqual(
            recipient1,
            UserFKRecipient(entity_source=source1, field_name=field_name1),
        )
        self.assertNotEqual(
            recipient1,
            UserFKRecipient(entity_source=source1, field_name='other_user'),
        )
        self.assertNotEqual(
            recipient1,
            UserFKRecipient(
                entity_source=CreatedEntitySource(model=FakeContact),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(None, recipient1)

        # Deserialization ---
        self.assertEqual(
            recipient1,
            UserFKRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

        # Configuration ---
        self.assertIsNone(UserFKRecipient.config_formfield(user=user1))

        formfield = UserFKRecipient.config_formfield(user=user1, entity_source=source1)
        self.assertIsInstance(formfield, UserFKRecipientField)
        self.assertEqual(
            _('Field to a user of: {source}').format(
                source=source1.render(user=user1, mode=source1.HTML),
            ),
            formfield.label,
        )

    def test_regular_emailfield(self):
        user = self.get_root_user()
        orga = FakeOrganisation.objects.create(
            user=user, name='Bebop', email='contact@bebop.mrs',
        )

        type_id = 'regular_field'
        source1 = FixedEntitySource(entity=orga)
        field_name1 = 'email'
        recipient1 = RegularEmailFieldRecipient(
            entity_source=source1, field_name=field_name1,
        )
        self.assertEqual(type_id,     recipient1.type_id)
        self.assertEqual(source1,     recipient1.entity_source)
        self.assertEqual(field_name1, recipient1.field_name)
        self.assertEqual(
            _('To: field «{field}» of: {source}').format(
                field=_('Email address'),
                source=source1.render(user=user, mode=source1.HTML),
            ),
            recipient1.render(user=user),
        )

        serialized = {
            'type': type_id,
            'entity': source1.to_dict(),
            'field': field_name1,
        }
        self.assertDictEqual(serialized, recipient1.to_dict())

        # self.assertEqual(orga.email, recipient1.extract({}))
        self.assertTupleEqual((orga.email, orga), recipient1.extract({}))

        # TODO: test with other field name (sadly in fake models, EmailFields have
        #       the same name/verbose_name...)
        # Empty source
        source2 = FixedEntitySource(model=FakeContact, entity=str(uuid4()))
        recipient2 = RegularEmailFieldRecipient(
            entity_source=source2,
            field_name='email',
        )
        self.assertEqual(source2, recipient2.entity_source)
        # self.assertIsNone(recipient2.extract({}))
        self.assertTupleEqual(('', None), recipient2.extract({}))

        # __eq__
        self.assertEqual(
            recipient1,
            RegularEmailFieldRecipient(entity_source=source1, field_name=field_name1),
        )
        self.assertNotEqual(
            recipient1,
            RegularEmailFieldRecipient(entity_source=source1, field_name='other_email'),
        )
        self.assertNotEqual(
            recipient1,
            RegularEmailFieldRecipient(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(None, recipient1)

        # Deserialization ---
        self.assertEqual(
            recipient1,
            RegularEmailFieldRecipient.from_dict(
                data=serialized, registry=workflow_registry,
            ),
        )

        # Configuration ---
        self.assertIsNone(RegularEmailFieldRecipient.config_formfield(user=user))

        formfield = RegularEmailFieldRecipient.config_formfield(
            user=user, entity_source=source1,
        )
        self.assertIsInstance(formfield, RegularEmailFieldRecipientField)
        self.assertEqual(
            _('Email field of: {source}').format(
                source=source1.render(user=user, mode=source1.HTML),
            ),
            formfield.label,
        )

        # No email field
        self.assertIsNone(RegularEmailFieldRecipient.config_formfield(
            user=user,
            entity_source=CreatedEntitySource(model=FakeImage),
        ))

    # TODO: when there is a type CustomField.EMAIL
    # def test_custom_emailfield(self):
    #     user = self.get_root_user()
    #     orga = FakeOrganisation.objects.create( user=user, name='Bebop')
    #
    #     cfield = CustomField.objects.create(
    #         field_type=CustomField.EMAIL, content_type=FakeOrganisation,
    #         name='Second email',
    #     )
    #
    #     type_id = 'custom_field'
    #     source1 = FixedEntitySource(entity=orga)
    #     recipient1 = CustomEmailFieldRecipient(
    #         entity_source=source1, cfield=cfield,
    #     )
    #     ...

    def test_registry(self):
        registry = ActionRecipientsRegistry()
        self.assertFalse([*registry.recipient_classes])

        registry.register(LiteralRecipient, FixedUserRecipient)
        self.assertCountEqual(
            [LiteralRecipient, FixedUserRecipient],
            [*registry.recipient_classes],
        )

        recipient1 = LiteralRecipient(email_address='spike.spiegel@bebop.mrs')
        self.assertEqual(recipient1, registry.build_recipient(recipient1.to_dict()))

        recipient2 = FixedUserRecipient(user=self.get_root_user())
        self.assertEqual(recipient2, registry.build_recipient(recipient2.to_dict()))

    def test_global_registry(self):
        self.assertCountEqual(
            [
                LiteralRecipient,
                FixedUserRecipient,
                UserFKRecipient,
                RegularEmailFieldRecipient,
            ],
            [*recipients_registry.recipient_classes],
        )


class LiteralRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        email = 'contact@bebop.vns'
        self.assertEqual(
            LiteralRecipient(email_address=email),
            LiteralRecipientField().clean(email),
        )

    def test_empty__required(self):
        field = LiteralRecipientField()
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty__not_required(self):
        field = LiteralRecipientField(required=False)
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))

    def test_invalid(self):
        self.assertFormfieldError(
            field=LiteralRecipientField(),
            value='not_an_email',
            messages=_('Enter a valid email address.'),
            codes='invalid',
        )


class FixedUserRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        user = self.get_root_user()
        self.assertEqual(
            FixedUserRecipient(user=user),
            FixedUserRecipientField().clean(user.id),
        )

    def test_choices(self):
        user1 = self.get_root_user()
        disabled = self.create_user(index=0, is_active=False)
        team = self.create_team('Crew')
        staff = self.create_user(index=1, is_staff=True)

        choices = FixedUserRecipientField().choices
        self.assertInChoices(
            value=user1.id, label=str(user1), choices=choices,
        )
        self.assertNotInChoices(value=disabled.id, choices=choices)
        self.assertNotInChoices(value=team.id,     choices=choices)
        self.assertNotInChoices(value=staff.id,    choices=choices)

    def test_empty__required(self):
        field = FixedUserRecipientField()
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty__not_required(self):
        field = FixedUserRecipientField(required=False)
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class UserFKRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        field_name = 'user'
        source = CreatedEntitySource(model=FakeOrganisation)
        self.assertEqual(
            UserFKRecipient(entity_source=source, field_name=field_name),
            UserFKRecipientField(entity_source=source).clean(field_name),
        )

    def test_choices(self):
        self.assertListEqual(
            [('user', _('Owner user'))],
            [*UserFKRecipientField(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
            ).choices],
        )
        self.assertListEqual(
            [
                ('user',    _('Owner user')),
                ('is_user', _('Related user')),
            ],
            [*UserFKRecipientField(
                entity_source=EditedEntitySource(model=FakeContact),
            ).choices],
        )

    def test_empty__required(self):
        field = UserFKRecipientField(
            entity_source=EditedEntitySource(model=FakeContact),
        )
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty__not_required(self):
        field = UserFKRecipientField(
            entity_source=EditedEntitySource(model=FakeContact), required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class RegularEmailFieldRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        field_name = 'email'
        source = CreatedEntitySource(model=FakeOrganisation)
        self.assertEqual(
            RegularEmailFieldRecipient(entity_source=source, field_name=field_name),
            RegularEmailFieldRecipientField(entity_source=source).clean(field_name),
        )

    def test_choices(self):
        self.assertListEqual(
            [('email', _('Email address'))],
            [*RegularEmailFieldRecipientField(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
            ).choices],
        )

    def test_empty__required(self):
        field = RegularEmailFieldRecipientField(
            entity_source=EditedEntitySource(model=FakeContact),
        )
        self.assertTrue(field.required)
        self.assertFormfieldError(
            field=field,
            value='',
            messages=_('This field is required.'),
            codes='required',
        )

    def test_empty__not_required(self):
        field = RegularEmailFieldRecipientField(
            entity_source=EditedEntitySource(model=FakeContact), required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class ActionRecipientFieldTestCase(_EmailsTestCase):
    def test_fields_choices__empty(self):
        field = ActionRecipientField()
        self.assertIsNone(field.trigger)
        self.assertListEqual([], field.fields_choices)

    def test_fields_choices(self):
        model = FakeContact
        field = ActionRecipientField()
        field.user = self.get_root_user()
        field.trigger = EntityCreationTrigger(model=model)

        choices = field.fields_choices
        self.assertIsList(choices, length=4)

        kind_id1, field1 = choices[0]
        self.assertEqual('literal', kind_id1)
        self.assertIsInstance(field1, LiteralRecipientField)

        kind_id2, field2 = choices[1]
        self.assertEqual('fixed_user', kind_id2)
        self.assertIsInstance(field2, FixedUserRecipientField)

        kind_id3, field3 = choices[2]
        self.assertEqual('created_entity|user_fk', kind_id3)
        self.assertIsInstance(field3, UserFKRecipientField)
        self.assertEqual(CreatedEntitySource(model=model), field3.entity_source)

        kind_id4, field4 = choices[3]
        self.assertEqual('created_entity|regular_field', kind_id4)
        self.assertIsInstance(field4, RegularEmailFieldRecipientField)

    def test_ok(self):
        user = self.get_root_user()
        model = FakeContact
        field = ActionRecipientField(
            trigger=EntityCreationTrigger(model=model), user=user,
        )
        self.assertTrue(field.required)

        literal_kind = 'literal'
        literal_email = 'spike@bebop.strn'
        fixed_kind = 'fixed_user'
        fixed_user = self.create_user()
        fk_kind = 'created_entity|user_fk'
        fk_fname = 'user'
        rfield_kind = 'created_entity|regular_field'
        rfield_name = 'email'
        sub_values = {
            literal_kind: literal_email,
            fixed_kind:   fixed_user.id,
            fk_kind:      fk_fname,
            rfield_kind:  rfield_name,
        }

        self.assertTupleEqual(
            (literal_kind, LiteralRecipient(email_address=literal_email)),
            field.clean((literal_kind, sub_values)),
        )
        self.assertTupleEqual(
            (fixed_kind, FixedUserRecipient(user=fixed_user)),
            field.clean((fixed_kind, sub_values)),
        )
        self.assertTupleEqual(
            (fixed_kind, FixedUserRecipient(user=fixed_user)),
            field.clean((fixed_kind, sub_values)),
        )
        source = CreatedEntitySource(model=model)
        self.assertTupleEqual(
            (fk_kind, UserFKRecipient(entity_source=source, field_name=fk_fname)),
            field.clean((fk_kind, sub_values)),
        )
        self.assertTupleEqual(
            (
                rfield_kind,
                RegularEmailFieldRecipient(entity_source=source, field_name=rfield_name),
            ),
            field.clean((rfield_kind, sub_values)),
        )


class EmailSendingActionFormTestCase(_EmailsTestCase):
    def test_fields(self):
        form = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF',
                trigger=EntityCreationTrigger(model=FakeOrganisation),
            ),
        )
        self.assertCountEqual(
            ['recipient', 'subject', 'body'],
            form.fields.keys(),
        )

    def test_recipient_field(self):
        trigger = EntityCreationTrigger(model=FakeOrganisation)
        form = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=Workflow(title='My WF', trigger=trigger),
        )
        recipient_f = form.fields.get('recipient')
        self.assertIsInstance(recipient_f, ActionRecipientField)
        self.assertTrue(recipient_f.required)
        self.assertEqual(trigger, recipient_f.trigger)

    # TODO: test other fields

    def test_clean(self):
        email_address = 'spike@bebop.jpt'
        subject = 'Hi'
        body = 'The content is very important'
        wf = Workflow(
            title='My WF',
            trigger=EntityCreationTrigger(model=FakeOrganisation),
        )
        form = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=wf,
            data={
                'recipient': 'literal',
                'recipient_literal': email_address,

                'subject': subject,
                'body': body,
            },
        )
        self.assertTrue(form.is_valid())
        self.assertListEqual(
            [
                EmailSendingAction(
                    recipient=LiteralRecipient(email_address=email_address),
                    subject=subject,
                    body=body,
                ).to_dict(),
            ],
            wf.json_actions,
        )


class WorkflowEmailTestCase(_EmailsTestCase):
    def _get_job(self):
        return self.get_object_or_fail(Job, type_id=workflow_emails_send_type.id)

    def test_create_n_send(self):
        sender = 'jet.black@bebop.ura'
        recipient = 'spike.spiegel@bebop.ura'
        subject = 'This is subject'
        body = 'My body is ready'
        wf_email = WorkflowEmail.objects.create(
            sender=sender,
            recipient=recipient, subject=subject, body=body,
        )
        self.assertEqual(sender,    wf_email.sender)
        self.assertEqual(recipient, wf_email.recipient)
        self.assertEqual(subject,   wf_email.subject)
        self.assertEqual(body,      wf_email.body)
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
        self.assertBodiesEqual(message, body=body, body_html=body)  # TODO: html

    def test_job__send(self):
        self.assertFalse(WorkflowEmail.objects.all())

        queue = get_queue()
        queue.clear()

        job = self._get_job()
        self.assertIsNone(workflow_emails_send_type.next_wakeup(job=job, now_value=now()))

        sender = 'ed.wong@bebop.ura'
        recipient = 'faye.valentine@bebop.ura'
        subject = 'Hi'
        body = 'This is important'
        wf_email = WorkflowEmail.objects.create(
            sender=sender,
            recipient=recipient, subject=subject, body=body,
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
        self.assertBodiesEqual(message, body=body, body_html=body)  # TODO: html

        self.assertIsNone(workflow_emails_send_type.next_wakeup(job=job, now_value=now()))

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


@override_settings(EMAIL_SENDER=test_sender)
class EmailSendingActionTestCase(_EmailsTestCase):
    def test_simple(self):
        "Literal sender, no template for subject/body."
        user = self.get_root_user()
        type_id = 'emails-email_sending'
        self.assertEqual(type_id, EmailSendingAction.type_id)
        self.assertEqual(_('Sending an email'), EmailSendingAction.verbose_name)

        # Instance ---
        address = 'spike.spiegel@bebop.mrs'
        recipient = LiteralRecipient(email_address=address)
        subject = 'This is important'
        body = 'A Contact has been created.'
        action = EmailSendingAction(recipient=recipient, subject=subject, body=body)
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        serialized = {
            'type': type_id,
            'recipient': recipient.to_dict(),
            'subject': subject,
            'body': body,
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{subject}</li>'
            '  <li>{body_label}<br><p>{body}</p></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=recipient.render(user=user),
                subject=_('Subject: {subject}').format(subject=subject),
                body_label=_('Body:'),
                body=body,
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = EmailSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EmailSendingAction)
        self.assertEqual(recipient, deserialized.recipient)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        deserialized.execute(context={})
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(address,     wf_email.recipient)
        self.assertEqual(subject,     wf_email.subject)
        self.assertEqual(body,        wf_email.body)

    def test_fixed_user(self):
        user = self.get_root_user()

        # Instance ---
        recipient = FixedUserRecipient(user=user)
        subject = 'This is very important'
        body = 'An Organisation has been created.'
        action = EmailSendingAction(recipient=recipient, subject=subject, body=body)
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        serialized = {
            'type': EmailSendingAction.type_id,
            'recipient': recipient.to_dict(),
            'subject': subject,
            'body': body,
        }
        self.assertDictEqual(serialized, action.to_dict())

        # De-serialisation ---
        deserialized = EmailSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, EmailSendingAction)
        self.assertEqual(recipient, deserialized.recipient)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        deserialized.execute(context={})
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(user.email,  wf_email.recipient)

        self.assertFalse(EntityEmail.objects.all())

    def test_user_fk(self):
        user1 = self.get_root_user()
        user2 = self.create_user()
        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=FakeContact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            subject='Modification!!',
            body='A Contact has been modified.',
        )
        contact = FakeContact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel', is_user=user2,
        )
        action.execute(context={EditedEntitySource.type_id: contact})

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(user2.email, wf_email.recipient)

    def test_user_fk__empty(self):
        user1 = self.get_root_user()

        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=FakeContact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            subject='Modification!!',
            body='A Contact has been modified.',
        )
        contact = FakeContact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel',
            # is_user=..., => No email sent
        )
        action.execute(context={EditedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_regular_field(self):
        user = self.get_root_user()

        recipient = RegularEmailFieldRecipient(
            entity_source=CreatedEntitySource(model=FakeContact),
            field_name='email',
        )
        subject = 'A New Contact is here!'
        body = 'Go & see it!!'
        action = EmailSendingAction(recipient=recipient, subject=subject, body=body)
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        # Execution ---
        e_email_count = EntityEmail.objects.count()
        contact = FakeContact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={CreatedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        # TODO:
        # e_email = EntityEmail.objects.order_by('-id')[0]
        # self.assertEqual(test_sender, wf_email.sender)
        # self.assertEqual(user.email,  wf_email.recipient)

    def test_registry__global(self):
        self.assertIn(EmailSendingAction, workflow_registry.action_classes)
