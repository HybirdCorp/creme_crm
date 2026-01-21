from django.utils.translation import gettext as _

from creme.creme_core.forms import CreatorEntityField
from creme.creme_core.forms.workflows import SourceField
from creme.creme_core.models import Workflow
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    EntityCreationTrigger,
)
from creme.emails.forms.workflows import (
    ActionRecipientField,
    EmailSendingActionForm,
    FixedUserRecipientField,
    LiteralRecipientField,
    RegularEmailFieldRecipientField,
    TemplateSendingActionForm,
    UserFKRecipientField,
)
from creme.emails.workflows import (
    EmailSendingAction,
    FixedUserRecipient,
    LiteralRecipient,
    RegularEmailFieldRecipient,
    TemplateSendingAction,
    UserFKRecipient,
)

from ..base import (
    Contact,
    EmailCampaign,
    EmailTemplate,
    Organisation,
    _EmailsTestCase,
)


class LiteralRecipientFieldTestCase(_EmailsTestCase):
    def test_ok(self):
        email = 'contact@bebop.vns'
        field = LiteralRecipientField()
        recipient = LiteralRecipient(email_address=email)
        self.assertEqual(recipient, field.clean(email))
        self.assertEqual(email, field.prepare_value(recipient))

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
        field = FixedUserRecipientField()
        recipient = FixedUserRecipient(user=user)
        self.assertEqual(recipient, field.clean(user.id))
        self.assertEqual(user.id, field.prepare_value(recipient))

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
        recipient = UserFKRecipient(entity_source=source, field_name=field_name)
        field = UserFKRecipientField(entity_source=source)
        self.assertEqual(recipient, field.clean(field_name))
        self.assertEqual(field_name, field.prepare_value(recipient))

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
        recipient = RegularEmailFieldRecipient(entity_source=source, field_name=field_name)
        field = RegularEmailFieldRecipientField(entity_source=source)
        self.assertEqual(recipient, field.clean(field_name))
        self.assertEqual(field_name, field.prepare_value(recipient))

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

        # Prepare value ---
        self.assertIsNone(field.prepare_value(None))
        self.assertTupleEqual(
            (literal_kind, {literal_kind: literal_email}),
            field.prepare_value(LiteralRecipient(email_address=literal_email)),
        )
        self.assertTupleEqual(
            (fixed_kind, {fixed_kind: fixed_user.id}),
            field.prepare_value(FixedUserRecipient(user=fixed_user)),
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

    def test_initial__empty(self):
        fields = EmailSendingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF', trigger=EntityCreationTrigger(model=Organisation),
            ),
        ).fields
        self.assertIsNone(fields['recipient'].initial)
        self.assertIsNone(fields['source'].initial)
        self.assertIsNone(fields['body'].initial)
        self.assertIsNone(fields['subject'].initial)

    def test_initial__edition(self):
        recipient = LiteralRecipient(email_address='spike@bebop.jpt')
        model = Organisation
        subject = 'Hi'
        body = 'An Organisation has been created: {{entity}}'
        source = CreatedEntitySource(model=model)
        wf = Workflow.objects.create(
            title='My WF',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                EmailSendingAction(
                    recipient=recipient, entity_source=source,
                    subject=subject, body=body,
                ),
            ],
        )
        fields = EmailSendingActionForm(
            user=self.get_root_user(), instance=wf, action_index=0,
        ).fields
        self.assertEqual(body,      fields['body'].initial)
        self.assertEqual(subject,   fields['subject'].initial)
        self.assertEqual(source,    fields['source'].initial)
        self.assertEqual(recipient, fields['recipient'].initial)

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

    def test_initial__empty(self):
        fields = TemplateSendingActionForm(
            user=self.get_root_user(),
            instance=Workflow(
                title='My WF', trigger=EntityCreationTrigger(model=Organisation),
            ),
        ).fields
        self.assertIsNone(fields['recipient'].initial)
        self.assertIsNone(fields['source'].initial)
        self.assertIsNone(fields['template'].initial)

    def test_initial__edition(self):
        user = self.get_root_user()

        recipient = LiteralRecipient(email_address='spike@bebop.jpt')
        model = Organisation
        source = CreatedEntitySource(model=model)
        template = EmailTemplate.objects.create(
            user=user, subject='Hi', body='The content is very important',
        )
        wf = Workflow.objects.create(
            title='My WF',
            content_type=model,
            trigger=EntityCreationTrigger(model=model),
            actions=[
                TemplateSendingAction(
                    recipient=recipient, entity_source=source, template=template,
                ),
            ],
        )
        fields = TemplateSendingActionForm(
            user=self.get_root_user(), instance=wf, action_index=0,
        ).fields

        self.assertEqual(recipient,   fields['recipient'].initial)
        self.assertEqual(source,      fields['source'].initial)
        self.assertEqual(template.id, fields['template'].initial)

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
