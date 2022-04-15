from datetime import timedelta
from functools import partial
from os.path import basename
from uuid import uuid4

from django.core import mail as django_mail
from django.test.utils import override_settings
from django.utils.html import escape
from django.utils.timezone import now
from django.utils.translation import gettext as _

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.core.workflow import workflow_registry
from creme.creme_core.forms import CreatorEntityField
from creme.creme_core.forms.workflows import SourceField
from creme.creme_core.models import Job, Workflow
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
    FixedEntitySource,
)
from creme.documents.tests.base import DocumentsTestCaseMixin

from ..constants import REL_SUB_MAIL_RECEIVED
from ..creme_jobs import workflow_emails_send_type
from ..forms.workflows import (
    ActionRecipientField,
    EmailSendingActionForm,
    FixedUserRecipientField,
    LiteralRecipientField,
    RegularEmailFieldRecipientField,
    TemplateSendingActionForm,
    UserFKRecipientField,
)
from ..models import EmailSignature, WorkflowEmail
from ..workflows import (
    ActionRecipientsRegistry,
    EmailSendingAction,
    FixedUserRecipient,
    LiteralRecipient,
    RegularEmailFieldRecipient,
    TemplateSendingAction,
    UserFKRecipient,
    recipients_registry,
)
from .base import (
    Contact,
    EmailCampaign,
    EmailTemplate,
    EntityEmail,
    Organisation,
    _EmailsTestCase,
)

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
            user=user, entity_source=CreatedEntitySource(model=Contact),
        ))

    def test_fixed_user(self):
        user1 = self.get_root_user()

        type_id = 'fixed_user'
        recipient1 = FixedUserRecipient(user=user1)
        self.assertEqual(type_id, recipient1.type_id)
        self.assertEqual(user1,   recipient1.user)
        self.assertDictEqual(
            {'type': type_id, 'user': str(user1.uuid)}, recipient1.to_dict(),
        )
        self.assertEqual(
            _('To: {user} <{email}>').format(user=user1, email=user1.email),
            recipient1.render(user=user1),
        )
        self.assertTupleEqual((user1.email, None), recipient1.extract({}))

        # Other values + username ---
        user2 = self.create_user()
        recipient2 = FixedUserRecipient(user=str(user2.uuid))
        self.assertEqual(type_id, recipient2.type_id)
        self.assertEqual(user2,   recipient2.user)
        self.assertEqual(
            _('To: {user} <{email}>').format(user=user2, email=user2.email),
            recipient2.render(user=user1),
        )
        self.assertTupleEqual((user2.email, None), recipient2.extract({}))

        serialized = {'type': type_id, 'user': str(user2.uuid)}
        self.assertDictEqual(serialized, recipient2.to_dict())

        # __eq__
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
            user=user1, entity_source=CreatedEntitySource(model=Contact),
        ))

    def test_fixed_user__inactive(self):
        user = self.create_user(is_active=False)
        recipient = FixedUserRecipient(user=user)
        self.assertTupleEqual(('', None), recipient.extract({}))

    def test_user_fk(self):
        user1 = self.get_root_user()

        type_id = 'user_fk'
        source1 = CreatedEntitySource(model=Organisation)
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
        orga = Organisation.objects.create(user=user2, name='Bebop')
        self.assertTupleEqual(
            (user2.email, None),  # Not an email field, we ignore 'contact'
            recipient1.extract({CreatedEntitySource.type_id: orga}),
        )

        # Other values ---
        source2 = EditedEntitySource(model=Contact)
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
                EditedEntitySource.type_id: user3.linked_contact,
            })
        )
        self.assertTupleEqual(
            ('', None),
            recipient2.extract({
                EditedEntitySource.type_id: Contact.objects.create(
                    user=user2, first_name='Faye', last_name='Valentine',
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
                entity_source=CreatedEntitySource(model=Contact),
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

    def test_user_fk__inactive(self):
        user = self.create_user(is_active=False)
        recipient = UserFKRecipient(
            entity_source=CreatedEntitySource(model=Organisation), field_name='user',
        )
        orga = Organisation.objects.create(user=user, name='Bebop')
        self.assertTupleEqual(
            ('', None), recipient.extract({CreatedEntitySource.type_id: orga}),
        )

    def test_regular_emailfield(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(
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

        self.assertTupleEqual((orga.email, orga), recipient1.extract({}))

        # TODO: test with other field name (sadly in fake models, EmailFields have
        #       the same name/verbose_name...)
        # Empty source
        source2 = FixedEntitySource(model=Contact, entity=str(uuid4()))
        recipient2 = RegularEmailFieldRecipient(
            entity_source=source2,
            field_name='email',
        )
        self.assertEqual(source2, recipient2.entity_source)
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
                entity_source=CreatedEntitySource(model=Organisation),
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
            entity_source=CreatedEntitySource(model=EmailCampaign),
        ))

    # TODO: when there is a type CustomField.EMAIL
    # def test_custom_emailfield(self):
    #     user = self.get_root_user()
    #     orga = Organisation.objects.create( user=user, name='Bebop')
    #
    #     cfield = CustomField.objects.create(
    #         field_type=CustomField.EMAIL, content_type=Organisation,
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

        # ---
        registry.unregister(LiteralRecipient)
        self.assertListEqual([FixedUserRecipient], [*registry.recipient_classes])

    def test_registry__error__duplicated(self):
        registry = ActionRecipientsRegistry()

        class TestRecipient1(LiteralRecipient):
            pass

        class TestRecipient2(LiteralRecipient):
            pass

        registry.register(TestRecipient1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient2)

    def test_registry__error__empty_id(self):
        registry = ActionRecipientsRegistry()

        class TestRecipient(LiteralRecipient):
            type_id = ''

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient)

    def test_registry__error__unknown_id(self):
        registry = ActionRecipientsRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister(LiteralRecipient)

    def test_registry__error__forbidden_char_in_id(self):
        registry = ActionRecipientsRegistry()

        class TestRecipient1(LiteralRecipient):
            type_id = 'type_w|th_p|pe'

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient1)

        # ---
        class TestRecipient2(LiteralRecipient):
            type_id = 'type_with_#ash'

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient2)

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
        source = CreatedEntitySource(model=Organisation)
        self.assertEqual(
            UserFKRecipient(entity_source=source, field_name=field_name),
            UserFKRecipientField(entity_source=source).clean(field_name),
        )

    def test_choices(self):
        self.assertListEqual(
            [('user', _('Owner user'))],
            [*UserFKRecipientField(
                entity_source=CreatedEntitySource(model=Organisation),
            ).choices],
        )
        self.assertListEqual(
            [
                ('user',    _('Owner user')),
                ('is_user', _('Related user')),
            ],
            [*UserFKRecipientField(
                entity_source=EditedEntitySource(model=Contact),
            ).choices],
        )

    def test_empty__required(self):
        field = UserFKRecipientField(
            entity_source=EditedEntitySource(model=Contact),
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
            entity_source=EditedEntitySource(model=Contact), required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class RegularEmailFieldRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        field_name = 'email'
        source = CreatedEntitySource(model=Organisation)
        self.assertEqual(
            RegularEmailFieldRecipient(entity_source=source, field_name=field_name),
            RegularEmailFieldRecipientField(entity_source=source).clean(field_name),
        )

    def test_choices(self):
        self.assertListEqual(
            [('email', _('Email address'))],
            [*RegularEmailFieldRecipientField(
                entity_source=CreatedEntitySource(model=Organisation),
            ).choices],
        )

    def test_empty__required(self):
        field = RegularEmailFieldRecipientField(
            entity_source=EditedEntitySource(model=Contact),
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
            entity_source=EditedEntitySource(model=Contact), required=False,
        )
        self.assertFalse(field.required)
        self.assertIsNone(field.clean(''))


class ActionRecipientFieldTestCase(_EmailsTestCase):
    def test_fields_choices__empty(self):
        field = ActionRecipientField()
        self.assertIsNone(field.trigger)
        self.assertListEqual([], field.fields_choices)

    def test_fields_choices(self):
        model = Contact
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
        model = Contact
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
        trigger = EntityCreationTrigger(model=Organisation)
        form = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=Workflow(title='My WF', trigger=trigger),
        )
        self.assertCountEqual(
            ['recipient', 'source', 'subject', 'body'], form.fields.keys(),
        )

        recipient_f = form.fields.get('recipient')
        self.assertIsInstance(recipient_f, ActionRecipientField)
        self.assertTrue(recipient_f.required)
        self.assertEqual(trigger, recipient_f.trigger)

        source_f = form.fields.get('source')
        self.assertIsInstance(source_f, SourceField)
        self.assertTrue(source_f.required)
        self.assertEqual(trigger, source_f.trigger)

    def test_clean(self):
        email_address = 'spike@bebop.jpt'
        model = Organisation
        subject = 'Hi'
        body = 'An Organisation has been created: {{entity}}'
        wf = Workflow(title='My WF', trigger=EntityCreationTrigger(model=model))
        form = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=wf,
            data={
                'recipient': 'literal',
                'recipient_literal': email_address,

                'source': 'created_entity',
                'source_created_entity': '',

                'subject': subject,
                'body': body,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertListEqual(
            [
                EmailSendingAction(
                    recipient=LiteralRecipient(email_address=email_address),
                    entity_source=CreatedEntitySource(model=model),
                    subject=subject,
                    body=body,
                ).to_dict(),
            ],
            wf.json_actions,
        )

    def test_body_errors(self):
        user = self.get_root_user()
        wf = Workflow(title='My WF', trigger=EntityCreationTrigger(model=Organisation))

        def build_form(body):
            return EmailSendingActionForm(
                user=user,
                instance=wf,
                data={
                    'recipient': 'literal',
                    'recipient_literal': 'spike@bebop.jpt',

                    'source': 'created_entity',
                    'source_created_entity': '',

                    'subject': 'Hi',
                    'body': body,
                },
            )

        self.assertFormInstanceErrors(
            build_form('The content is very important {{unknown}}'),
            (
                'body',
                _('The following variables are invalid: %(vars)s') % {'vars': 'unknown'},
            ),
        )
        self.assertFormInstanceErrors(
            build_form('{% load creme_core_tags %}The content is very important'),
            ('body', _('The tags like {% … %} are forbidden')),
        )
        self.assertFalse(wf.actions)


class TemplateSendingActionFormTestCase(_EmailsTestCase):
    def test_fields(self):
        user = self.get_root_user()
        trigger = EntityCreationTrigger(model=Organisation)
        form = TemplateSendingActionForm(
            user=user, instance=Workflow(title='My WF', trigger=trigger),
        )
        self.assertCountEqual(
            ['recipient', 'source', 'template'], form.fields.keys(),
        )

        recipient_f = form.fields.get('recipient')
        self.assertIsInstance(recipient_f, ActionRecipientField)
        self.assertTrue(recipient_f.required)
        self.assertEqual(trigger, recipient_f.trigger)

        source_f = form.fields.get('source')
        self.assertIsInstance(source_f, SourceField)
        self.assertTrue(source_f.required)
        self.assertEqual(trigger, source_f.trigger)

        template_f = form.fields.get('template')
        self.assertIsInstance(template_f, CreatorEntityField)
        self.assertTrue(template_f.required)
        self.assertEqual(EmailTemplate, template_f.model)
        self.assertEqual(user,          template_f.user)

    def test_clean(self):
        user = self.get_root_user()
        model = Organisation
        email_address = 'spike@bebop.jpt'
        template = EmailTemplate.objects.create(
            user=user, subject='Hi', body='The content is very important',
        )
        wf = Workflow(
            title='My WF', trigger=EntityCreationTrigger(model=model),
        )
        form = TemplateSendingActionForm(
            user=user,
            instance=wf,
            data={
                'recipient': 'literal',
                'recipient_literal': email_address,

                'source': 'created_entity',
                'source_created_entity': '',

                'template': f'{template.id}',
            },
        )
        self.assertTrue(form.is_valid())
        self.assertListEqual(
            [
                TemplateSendingAction(
                    recipient=LiteralRecipient(email_address=email_address),
                    entity_source=CreatedEntitySource(model=model),
                    template=template,
                ).to_dict(),
            ],
            wf.json_actions,
        )

    def test_error__not_a_person(self):
        user = self.get_root_user()
        model = EmailCampaign
        email_address = 'spike@bebop.jpt'
        template = EmailTemplate.objects.create(
            user=user, subject='Hi', body='The content is very important',
        )
        wf = Workflow(title='My WF', trigger=EntityCreationTrigger(model=model))
        form = TemplateSendingActionForm(
            user=user,
            instance=wf,
            data={
                'recipient': 'literal',
                'recipient_literal': email_address,

                'source': 'created_entity',
                'source_created_entity': '',

                'template': f'{template.id}',
            },
        )
        self.assertFormInstanceErrors(
            form, ('source', _('The entity must be a Contact or an Organisation.')),
        )
        self.assertFalse(wf.actions)


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
        self.assertIsNone(workflow_emails_send_type.next_wakeup(job=job, now_value=now()))

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
        source = CreatedEntitySource(model=Contact)
        action = EmailSendingAction(
            recipient=recipient, entity_source=source, subject=subject, body=body,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)
        self.assertEqual(source,    action.entity_source)

        serialized = {
            'type': type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
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
        self.assertEqual(source,    deserialized.entity_source)
        self.assertEqual(subject,   deserialized.subject)
        self.assertEqual(body,      deserialized.body)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        deserialized.execute(context={
            CreatedEntitySource.type_id: Contact.objects.create(user=user, last_name='Spiegel'),
        })
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(address,     wf_email.recipient)
        self.assertEqual(subject,     wf_email.subject)
        self.assertEqual(body,        wf_email.body)

        # Configuration ---
        self.assertEqual(
            EmailSendingAction.config_form_class(), EmailSendingActionForm,
        )

    def test_fixed_user(self):
        user = self.get_root_user()

        # Instance ---
        recipient = FixedUserRecipient(user=user)
        source = CreatedEntitySource(model=Organisation)
        subject = 'This is very important'
        body = 'An Organisation has been created.'
        action = EmailSendingAction(
            recipient=recipient, subject=subject, body=body, entity_source=source,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        serialized = {
            'type': EmailSendingAction.type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
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
        deserialized.execute(context={
            CreatedEntitySource.type_id: Organisation.objects.create(user=user, name='Bebop'),
        })
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(user.email,  wf_email.recipient)

        self.assertFalse(EntityEmail.objects.all())

    def test_user_fk(self):
        user = self.get_root_user()
        contact = user.linked_contact
        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=Contact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            entity_source=EditedEntitySource(model=Contact),
            subject='Modification!!',
            body='A Contact has been modified: {{entity}}',
        )
        action.execute(context={EditedEntitySource.type_id: contact})

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(user.email, wf_email.recipient)
        self.assertEqual(
            f'A Contact has been modified: {contact}',
            wf_email.body,
        )
        self.assertEqual(
            f'A Contact has been modified: {contact}',
            wf_email.body,
        )
        self.assertHTMLEqual(
            f'<!DOCTYPE html>'
            f'<html>'
            f' <head>'
            f'  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'  <title>Creme Workflow</title>'
            f' </head>'
            f' <body style="margin:0;padding-top:0;padding-bottom:0;padding-right:0;'
            f'padding-left:0;min-width:100%;background-color:#f0f0f0;">'
            f'  <p style="margin: 10px;background-color: #d2e3f2;padding: 10px;'
            f'color: #21323c;border-radius: 5px;width: fit-content;">'
            f'A Contact has been modified: '
            f'   <a href="{contact.get_absolute_url()}">{contact}</a>'
            f'  </p>'
            f' </body>'
            f'</html>',
            wf_email.body_html,
        )

    def test_user_fk__empty(self):
        user = self.get_root_user()

        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=Contact),
            field_name='is_user',
        )
        action = EmailSendingAction(
            recipient=recipient,
            entity_source=EditedEntitySource(model=Contact),
            subject='Modification!!',
            body='A Contact has been modified.',
        )

        # <is_user==None> => No email sent
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
        )
        action.execute(context={EditedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_regular_field(self):
        user = self.get_root_user()

        recipient = RegularEmailFieldRecipient(
            entity_source=CreatedEntitySource(model=Contact),
            field_name='email',
        )
        subject = 'A New Contact is here!'
        body = 'Go & see it!!\nHere: {{entity}}'
        action = EmailSendingAction(
            recipient=recipient, subject=subject, body=body,
            entity_source=CreatedEntitySource(model=Contact),
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(subject,   action.subject)
        self.assertEqual(body,      action.body)

        # Execution ---
        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={CreatedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        # self.assertEqual(...,   e_email.user)  # TODO
        self.assertEqual(_('Created by a workflow'), e_email.description)
        self.assertEqual(test_sender,   e_email.sender)
        self.assertEqual(contact.email, e_email.recipient)
        self.assertEqual(subject,       e_email.subject)
        self.assertEqual(f'Go & see it!!\nHere: {contact}', e_email.body)
        self.assertEqual(EntityEmail.Status.NOT_SENT, e_email.status)
        self.assertHaveRelation(
            subject=e_email, type=REL_SUB_MAIL_RECEIVED, object=contact,
        )
        self.maxDiff = None
        self.assertHTMLEqual(
            f'<!DOCTYPE html>'
            f'<html>'
            f' <head>'
            f'  <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />'
            f'  <meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'  <title>Creme Workflow</title>'
            f' </head>'
            f' <body style="margin:0;padding-top:0;padding-bottom:0;padding-right:0;'
            f'padding-left:0;min-width:100%;background-color:#f0f0f0;">'
            f'  <p style="margin: 10px;background-color: #d2e3f2;padding: 10px;'
            f'color: #21323c;border-radius: 5px;width: fit-content;">'
            f'Go & see it!!<br>Here: <a href="{contact.get_absolute_url()}">{contact}</a>'
            f'  </p>'
            f' </body>'
            f'</html>',
            e_email.body_html,
        )

    def test_registry__global(self):
        self.assertIn(EmailSendingAction, workflow_registry.action_classes)


@override_settings(EMAIL_SENDER=test_sender)
class TemplateSendingActionTestCase(DocumentsTestCaseMixin, _EmailsTestCase):
    def test_simple(self):
        "Literal sender, no template variable."
        user = self.get_root_user()
        type_id = 'emails-template_sending'
        self.assertEqual(type_id, TemplateSendingAction.type_id)
        self.assertEqual(
            _('Sending an email (from a template)'),
            TemplateSendingAction.verbose_name,
        )

        # Instance ---
        signature = EmailSignature.objects.create(
            user=user,
            name='Main signature',
            body='Client relation team',
        )
        template = EmailTemplate.objects.create(
            user=user, name='Template for WF',
            subject='This is important',
            body='A Contact has been created.',
            body_html='A <i>Contact</i> has been created.',
            signature=signature,
        )

        address = 'spike.spiegel@bebop.mrs'
        recipient = LiteralRecipient(email_address=address)
        source = CreatedEntitySource(model=Contact)
        action = TemplateSendingAction(
            recipient=recipient, entity_source=source, template=template,
        )
        self.assertEqual(recipient, action.recipient)
        self.assertEqual(source,    action.entity_source)
        self.assertEqual(template,  action.template)

        serialized = {
            'type': type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'template': str(template.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())
        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{template_label}<a href="{template_url}" target="_self">{template}</a></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=recipient.render(user=user),
                template_label=_('Use template:'),
                template_url=template.get_absolute_url(),
                template=template.name,
            ),
            action.render(user=user),
        )

        # De-serialisation ---
        deserialized = TemplateSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, TemplateSendingAction)
        self.assertEqual(recipient, deserialized.recipient)
        self.assertEqual(template,  deserialized.template)

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        contact = Contact.objects.create(user=user, first_name='Ed', last_name='Wong')
        deserialized.execute(context={CreatedEntitySource.type_id: contact})
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(address,     wf_email.recipient)
        self.assertEqual(template.subject,   wf_email.subject)
        self.assertEqual(template.body,      wf_email.body)
        self.assertEqual(template.body_html, wf_email.body_html)
        self.assertEqual(signature, wf_email.signature)

        self.assertFalse(EntityEmail.objects.all())

        # Configuration ---
        self.assertEqual(
            TemplateSendingAction.config_form_class(), TemplateSendingActionForm,
        )

    def test_fixed_user(self):
        user = self.login_as_root_and_get()
        doc = self._create_doc(title='Attachment #1', user=user)

        # Instance ---
        recipient = FixedUserRecipient(user=user)

        source = CreatedEntitySource(model=Contact)
        subject = 'This is very important'
        template = EmailTemplate.objects.create(
            user=user, name='Template for WF', subject=subject,
            body='A Contact has been created: {{last_name}}, {{first_name}}',
            body_html='A Contact has been <b>created</b>: {{last_name}}, {{first_name}}',
        )
        template.attachments.set([doc])

        action = TemplateSendingAction(
            recipient=recipient, template=str(template.uuid), entity_source=source,
        )

        serialized = {
            'type': TemplateSendingAction.type_id,
            'recipient': recipient.to_dict(),
            'entity': source.to_dict(),
            'template': str(template.uuid),
        }
        self.assertDictEqual(serialized, action.to_dict())

        # De-serialisation ---
        deserialized = TemplateSendingAction.from_dict(
            data=serialized, registry=workflow_registry,
        )
        self.assertIsInstance(deserialized, TemplateSendingAction)
        self.assertEqual(recipient, deserialized.recipient)

        self.assertHTMLEqual(
            '<div>'
            '{label}'
            ' <ul>'
            '  <li>{recipient}</li>'
            '  <li>{template_label}<a href="{template_url}" target="_self">{template}</a></li>'
            ' </ul>'
            '</div>'.format(
                label=_('Sending an email:'),
                recipient=escape(recipient.render(user=user)),
                template_label=_('Use template:'),
                template_url=template.get_absolute_url(),
                template=template.name,
            ),
            deserialized.render(user=user),
        )

        # Execution ---
        wf_email_count = WorkflowEmail.objects.count()
        contact = Contact.objects.create(user=user, first_name='Ed', last_name='Wong')
        deserialized.execute(context={
            CreatedEntitySource.type_id: contact,
        })
        self.assertEqual(wf_email_count + 1, WorkflowEmail.objects.count())

        wf_email = WorkflowEmail.objects.order_by('-id')[0]
        self.assertEqual(test_sender, wf_email.sender)
        self.assertEqual(user.email,  wf_email.recipient)
        self.assertEqual(
            f'A Contact has been created: {contact.last_name}, {contact.first_name}',
            wf_email.body,
        )
        self.assertEqual(
            f'A Contact has been <b>created</b>: {contact.last_name}, {contact.first_name}',
            wf_email.body_html,
        )
        self.assertListEqual([doc], [*wf_email.attachments.all()])

    def test_no_recipient(self):
        user1 = self.get_root_user()

        action = TemplateSendingAction(
            recipient=UserFKRecipient(
                entity_source=EditedEntitySource(model=Contact),
                field_name='is_user',
            ),
            entity_source=CreatedEntitySource(model=Contact),
            template=EmailTemplate.objects.create(
                user=user1,
                subject='Modification!!',
                body='A Contact has been modified.',
            ),
        )
        contact = Contact.objects.create(
            user=user1, first_name='Spike', last_name='Spiegel',
            # is_user=..., => No email sent
        )
        action.execute(context={EditedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())

    def test_regular_field(self):
        user = self.login_as_root_and_get()
        doc = self._create_doc(title='Attachment #1', user=user)

        recipient = RegularEmailFieldRecipient(
            entity_source=CreatedEntitySource(model=Contact),
            field_name='email',
        )
        source = CreatedEntitySource(model=Contact)
        signature = EmailSignature.objects.create(
            user=user,
            name='Main signature',
            body='Client relation team',
        )
        template = EmailTemplate.objects.create(
            user=user, subject='A New Contact is here!',
            body='This is {{first_name}} {{last_name}}',
            body_html='This is {{first_name}} <b>{{last_name}}</b>',
            signature=signature,
        )
        template.attachments.set([doc])
        action = TemplateSendingAction(
            recipient=recipient, entity_source=source, template=template,
        )

        # Execution ---
        e_email_count = EntityEmail.objects.count()
        contact = Contact.objects.create(
            user=user, first_name='Spike', last_name='Spiegel',
            email='spike.spiegel@bebop.mrs',
        )
        action.execute(context={CreatedEntitySource.type_id: contact})
        self.assertFalse(WorkflowEmail.objects.all())
        self.assertEqual(e_email_count + 1, EntityEmail.objects.count())

        e_email = EntityEmail.objects.order_by('-id')[0]
        # self.assertEqual(...,   e_email.user)  # TODO
        self.assertEqual(_('Created by a workflow'), e_email.description)
        self.assertEqual(test_sender,      e_email.sender)
        self.assertEqual(contact.email,    e_email.recipient)
        self.assertEqual(template.subject, e_email.subject)
        self.assertEqual(signature,        e_email.signature)
        self.assertEqual(
            f'This is {contact.first_name} {contact.last_name}',
            e_email.body,
        )
        self.assertEqual(
            f'This is {contact.first_name} <b>{contact.last_name}</b>',
            e_email.body_html,
        )
        self.assertEqual(EntityEmail.Status.NOT_SENT, e_email.status)
        self.assertListEqual([doc], [*e_email.attachments.all()])
        self.assertHaveRelation(
            subject=e_email, type=REL_SUB_MAIL_RECEIVED, object=contact,
        )

    def test_registry__global(self):
        self.assertIn(TemplateSendingAction, workflow_registry.action_classes)
