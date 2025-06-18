from uuid import uuid4

from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.core.workflow import (
    BrokenSource,
    WorkflowBrokenData,
    workflow_registry,
)
from creme.creme_core.workflows import (
    CreatedEntitySource,
    EditedEntitySource,
    FixedEntitySource,
)
from creme.emails.forms.workflows import (
    FixedUserRecipientField,
    LiteralRecipientField,
    RegularEmailFieldRecipientField,
    UserFKRecipientField,
)
from creme.emails.workflows import (
    ActionRecipientsRegistry,
    BrokenActionRecipient,
    FixedUserRecipient,
    LiteralRecipient,
    RegularEmailFieldRecipient,
    UserFKRecipient,
    recipients_registry,
)

from ..base import Contact, EmailCampaign, Organisation, _EmailsTestCase


class LiteralRecipientTestCase(_EmailsTestCase):
    def test_main(self):
        user = self.get_root_user()

        type_id = 'literal'
        email1 = 'spike.spiegel@bebop.mrs'
        recipient1 = LiteralRecipient(email_address=email1)
        self.assertEqual(type_id, recipient1.type_id)
        self.assertEqual(email1,  recipient1.email_address)
        self.assertIsNone(recipient1.sub_source)
        self.assertDictEqual(
            {'type': type_id, 'email': email1}, recipient1.to_dict(),
        )
        self.assertEqual(
            _('To: {recipient}').format(recipient=email1),
            recipient1.render(user=user),
        )
        self.assertTupleEqual((email1, None), recipient1.extract({}))

    def test_other_values(self):
        user = self.get_root_user()

        type_id = 'literal'
        email = 'jet.black@bebop.mrs'
        recipient = LiteralRecipient(email_address=email)
        self.assertEqual(type_id, recipient.type_id)
        self.assertEqual(email,   recipient.email_address)
        self.assertEqual(
            _('To: {recipient}').format(recipient=email),
            recipient.render(user=user),
        )
        self.assertTupleEqual((email, None), recipient.extract({}))

    def test_serialization(self):
        email = 'jet.black@bebop.mrs'
        recipient = LiteralRecipient(email_address=email)

        serialized = {'type': 'literal', 'email': email}
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            LiteralRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_eq(self):
        email1 = 'spike.spiegel@bebop.mrs'
        recipient1 = LiteralRecipient(email_address=email1)

        self.assertEqual(recipient1, LiteralRecipient(email_address=email1))
        self.assertNotEqual(
            recipient1,
            LiteralRecipient(email_address='jet.black@bebop.mrs'),
        )
        self.assertNotEqual(None, recipient1)

    def test_config_formfield(self):
        user = self.get_root_user()

        formfield = LiteralRecipient.config_formfield(user=user)
        self.assertIsInstance(formfield, LiteralRecipientField)
        self.assertEqual(_('Fixed email address'), formfield.label)

        self.assertIsNone(LiteralRecipient.config_formfield(
            user=user, entity_source=CreatedEntitySource(model=Contact),
        ))

        self.assertEqual('literal', LiteralRecipient.config_formfield_kind_id())


class FixedUserRecipientTestCase(_EmailsTestCase):
    def test_user_instance(self):
        user = self.get_root_user()

        type_id = 'fixed_user'
        recipient = FixedUserRecipient(user=user)
        self.assertEqual(type_id, recipient.type_id)
        self.assertIsNone(recipient.sub_source)

        with self.assertNumQueries(0):
            self.assertEqual(user, recipient.user)

        self.assertEqual(
            _('To: {user} <{email}>').format(user=user, email=user.email),
            recipient.render(user=user),
        )
        self.assertTupleEqual((user.email, None), recipient.extract({}))

    def test_user_instance__serialization(self):
        user = self.get_root_user()
        recipient = FixedUserRecipient(user=user)

        serialized = {'type': 'fixed_user', 'user': str(user.uuid)}
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            FixedUserRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_user_uuid(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        with self.assertNumQueries(0):
            recipient = FixedUserRecipient(user=str(user2.uuid))

        self.assertEqual('fixed_user', recipient.type_id)

        with self.assertNumQueries(1):
            self.assertEqual(user2, recipient.user)

        with self.assertNumQueries(0):
            recipient.user  # NOQA

        self.assertEqual(
            _('To: {user} <{email}>').format(user=user2, email=user2.email),
            recipient.render(user=user1),
        )
        self.assertTupleEqual((user2.email, None), recipient.extract({}))

    def test_user_uuid__serialization(self):
        user = self.get_root_user()
        recipient = FixedUserRecipient(user=str(user.uuid))

        serialized = {'type': 'fixed_user', 'user': str(user.uuid)}
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            FixedUserRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_eq(self):
        user1 = self.get_root_user()
        user2 = self.create_user()
        recipient1 = FixedUserRecipient(user=user1)
        self.assertEqual(recipient1, FixedUserRecipient(user=user1))
        self.assertNotEqual(recipient1, FixedUserRecipient(user=str(user2.uuid)))
        self.assertNotEqual(None, recipient1)

    def test_config_formfield(self):
        user = self.get_root_user()
        formfield = FixedUserRecipient.config_formfield(user=user)
        self.assertIsInstance(formfield, FixedUserRecipientField)
        self.assertEqual(_('Fixed user'), formfield.label)

        self.assertIsNone(FixedUserRecipient.config_formfield(
            user=user, entity_source=CreatedEntitySource(model=Contact),
        ))

        self.assertEqual('fixed_user', FixedUserRecipient.config_formfield_kind_id())

    def test_inactive_user(self):
        user1 = self.get_root_user()
        user2 = self.create_user(is_active=False)
        recipient = FixedUserRecipient(user=user2)
        self.assertTupleEqual(('', None), recipient.extract({}))

        self.assertEqual(
            '{}<span class="warninglist">{}</span>'.format(
                escape(_('To:')),
                escape(
                    _(
                        'The user «{username}» is disabled (no email will be sent)'
                    ).format(username=user2.username)
                ),
            ),
            recipient.render(user=user1),
        )

    def test_broken_user(self):
        recipient = FixedUserRecipient(user=str(uuid4()))

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                recipient.user # NOQA

        self.assertEqual(
            _('The user does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                recipient.user # NOQA

        self.assertTupleEqual(('', None), recipient.extract({}))

        self.assertEqual(
            '{}<p class="errorlist">{}</p>'.format(
                escape(_('To: a fixed user')),
                escape(_('The user does not exist anymore')),
            ),
            recipient.render(user=self.get_root_user()),
        )


class UserFKRecipientTestCase(_EmailsTestCase):
    def test_field_user(self):
        user1 = self.get_root_user()

        type_id = 'user_fk'
        source = CreatedEntitySource(model=Organisation)
        field_name = 'user'
        recipient = UserFKRecipient(entity_source=source, field_name=field_name)
        self.assertEqual(type_id,    recipient.type_id)
        self.assertEqual(source,     recipient.sub_source)
        self.assertEqual(field_name, recipient.field_name)
        self.assertEqual(
            _('To: user «{field}» of: {source}').format(
                field=_('Owner user'),
                source=source.render(user=user1, mode=source.RenderMode.HTML),
            ),
            recipient.render(user=user1),
        )

    def test_field_user__extraction(self):
        recipient = UserFKRecipient(
            entity_source=CreatedEntitySource(model=Organisation),
            field_name='user',
        )

        user = self.create_user(index=0)
        orga = Organisation.objects.create(user=user, name='Bebop')
        self.assertTupleEqual(
            (user.email, None),  # Not an email field, we ignore 'contact'
            recipient.extract({CreatedEntitySource.type_id: orga}),
        )

    def test_field_user__serialization(self):
        source = CreatedEntitySource(model=Organisation)
        field_name = 'user'
        recipient = UserFKRecipient(entity_source=source, field_name=field_name)

        serialized = {
            'type': 'user_fk',
            'entity': source.to_dict(),
            'field': field_name,
        }
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            UserFKRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_field_is_user(self):
        user = self.get_root_user()

        source = EditedEntitySource(model=Contact)
        field_name = 'is_user'
        recipient = UserFKRecipient(entity_source=source, field_name=field_name)
        self.assertEqual(source,     recipient.sub_source)
        self.assertEqual(field_name, recipient.field_name)
        self.assertEqual(
            _('To: user «{field}» of: {source}').format(
                field=_('Related user'),
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            recipient.render(user=user),
        )

    def test_field_is_user__extraction(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        recipient = UserFKRecipient(
            entity_source=EditedEntitySource(model=Contact),
            field_name='is_user',
        )
        self.assertTupleEqual(
            (user1.email, None),
            recipient.extract({EditedEntitySource.type_id: user1.linked_contact}),
        )
        self.assertTupleEqual(
            ('', None),
            recipient.extract({
                EditedEntitySource.type_id: Contact.objects.create(
                    user=user2, first_name='Faye', last_name='Valentine',
                ),
            }),
        )

    def test_field_is_user__serialization(self):
        source = EditedEntitySource(model=Contact)
        field_name = 'is_user'
        recipient = UserFKRecipient(entity_source=source, field_name=field_name)

        serialized = {
            'type': 'user_fk',
            'entity': source.to_dict(),
            'field': field_name,
        }
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            UserFKRecipient.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_eq(self):
        source1 = CreatedEntitySource(model=Contact)
        field_name1 = 'user'
        recipient1 = UserFKRecipient(entity_source=source1, field_name=field_name1)
        self.assertEqual(
            recipient1,
            UserFKRecipient(entity_source=source1, field_name=field_name1),
        )
        self.assertNotEqual(
            recipient1,
            UserFKRecipient(entity_source=source1, field_name='is_user'),
        )
        self.assertNotEqual(
            recipient1,
            UserFKRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(None, recipient1)

    def test_config_formfield(self):
        user = self.get_root_user()
        self.assertIsNone(UserFKRecipient.config_formfield(user=user))

        source = CreatedEntitySource(model=Organisation)
        formfield = UserFKRecipient.config_formfield(user=user, entity_source=source)
        self.assertIsInstance(formfield, UserFKRecipientField)
        self.assertEqual(
            _('Field to a user of: {source}').format(
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            formfield.label,
        )

        self.assertEqual(
            'created_entity|user_fk',
            UserFKRecipient.config_formfield_kind_id(sub_source=source),
        )

    def test_inactive_user(self):
        user = self.create_user(is_active=False)
        recipient = UserFKRecipient(
            entity_source=CreatedEntitySource(model=Organisation), field_name='user',
        )
        orga = Organisation.objects.create(user=user, name='Bebop')
        self.assertTupleEqual(
            ('', None), recipient.extract({CreatedEntitySource.type_id: orga}),
        )

    def test_broken_source(self):
        message = 'Invalid model'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKRecipient(
                entity_source=BrokenSource(message=message),
                field_name='user',
            )

        self.assertEqual(message, str(cm.exception))

    def test_broken_field__unknown(self):
        field_name = 'invalid'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name,
            )

        self.assertEqual(
            _('The field «{field}» is invalid in model «{model}»').format(
                field=field_name, model=_('Organisation'),
            ),
            str(cm.exception),
        )

    def test_broken_field__not_fk(self):
        field_name = 'name'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name,
            )

        self.assertEqual(
            f'The field "{field_name}" is not a ForeignKey',
            str(cm.exception),
        )

    def test_broken_field__not_fk_to_user(self):
        field_name = 'sector'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name,
            )

        self.assertEqual(
            f'The field "{field_name}" is not a ForeignKey to User',
            str(cm.exception),
        )


class RegularEmailFieldRecipientTestCase(_EmailsTestCase):
    def test_main(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(
            user=user, name='Bebop', email='contact@bebop.mrs',
        )

        source = FixedEntitySource(entity=orga)
        field_name = 'email'
        recipient = RegularEmailFieldRecipient(
            entity_source=source, field_name=field_name,
        )
        self.assertEqual('regular_field', recipient.type_id)
        self.assertEqual(source,     recipient.sub_source)
        self.assertEqual(field_name, recipient.field_name)
        self.assertEqual(
            _('To: field «{field}» of: {source}').format(
                field=_('Email address'),
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            recipient.render(user=user),
        )
        self.assertTupleEqual((orga.email, orga), recipient.extract({}))

    def test_serialization(self):
        source = CreatedEntitySource(model=Organisation)
        field_name = 'email'
        recipient = RegularEmailFieldRecipient(
            entity_source=source, field_name=field_name,
        )

        serialized = {
            'type': 'regular_field',
            'entity': source.to_dict(),
            'field': field_name,
        }
        self.assertDictEqual(serialized, recipient.to_dict())
        self.assertEqual(
            recipient,
            RegularEmailFieldRecipient.from_dict(
                data=serialized, registry=workflow_registry,
            ),
        )

    def test_empty_source(self):
        # TODO: test with other field name (sadly in fake models, EmailFields
        #       have the same name/verbose_name...)
        source = FixedEntitySource(model=Contact, entity=str(uuid4()))
        recipient = RegularEmailFieldRecipient(
            entity_source=source, field_name='email',
        )
        self.assertEqual(source, recipient.sub_source)
        self.assertTupleEqual(('', None), recipient.extract({}))

    def test_eq(self):
        user = self.get_root_user()
        source1 = FixedEntitySource(
            entity=Organisation.objects.create(
                user=user, name='Bebop', email='contact@bebop.mrs',
            ),
        )
        field_name1 = 'email'
        recipient1 = RegularEmailFieldRecipient(
            entity_source=source1, field_name=field_name1,
        )

        self.assertEqual(
            recipient1,
            RegularEmailFieldRecipient(entity_source=source1, field_name=field_name1),
        )
        # TODO: need a fake model with 2 email fields
        # self.assertNotEqual(
        #     recipient1,
        #     RegularEmailFieldRecipient(entity_source=source1, field_name='other_email'),
        # )
        self.assertNotEqual(
            recipient1,
            RegularEmailFieldRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(None, recipient1)

    def test_config_formfield(self):
        user = self.get_root_user()
        orga = Organisation.objects.create(
            user=user, name='Bebop', email='contact@bebop.mrs',
        )

        source = FixedEntitySource(entity=orga)
        self.assertIsNone(RegularEmailFieldRecipient.config_formfield(user=user))

        formfield = RegularEmailFieldRecipient.config_formfield(
            user=user, entity_source=source,
        )
        self.assertIsInstance(formfield, RegularEmailFieldRecipientField)
        self.assertEqual(
            _('Email field of: {source}').format(
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            formfield.label,
        )

        # No email field ---
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

    def test_broken_field__not_emailfield(self):
        field_name = 'name'

        with self.assertRaises(WorkflowBrokenData) as cm:
            RegularEmailFieldRecipient(
                entity_source=CreatedEntitySource(model=Organisation),
                field_name=field_name,
            )

        self.assertEqual(
            f'The field "{field_name}" is not an EmailField',
            str(cm.exception),
        )


class ActionRecipientsRegistryTestCase(_EmailsTestCase):
    def test_BrokenActionRecipient(self):
        message = 'Invalid field'
        recipient = BrokenActionRecipient(message=message)
        self.assertEqual('',      recipient.type_id)
        self.assertEqual(message, recipient.message)
        self.assertTupleEqual(('', None), recipient.extract({}))
        self.assertEqual(
            f'<p class="errorlist">{message}</p>',
            recipient.render(user=self.get_root_user()),
        )

    def test_main(self):
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

    def test_error__duplicated(self):
        registry = ActionRecipientsRegistry()

        class TestRecipient1(LiteralRecipient):
            pass

        class TestRecipient2(LiteralRecipient):
            pass

        registry.register(TestRecipient1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient2)

    def test_error__empty_id(self):
        registry = ActionRecipientsRegistry()

        class TestRecipient(LiteralRecipient):
            type_id = ''

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestRecipient)

    def test_error__unknown_id(self):
        registry = ActionRecipientsRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister(LiteralRecipient)

    def test_error__forbidden_char_in_id(self):
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

    def test_broken_data__invalid_type_id(self):
        type_id = 'uninstalled_app-my_recipient'
        registry = ActionRecipientsRegistry()
        recipient = registry.build_recipient({
            'type': 'uninstalled_app-my_recipient',
            # ...
        })
        self.assertIsInstance(recipient, BrokenActionRecipient)
        self.assertEqual(
            _(
                'The type of recipient «{type}» is invalid (uninstalled app?)'
            ).format(type=type_id),
            recipient.message,
        )

    def test_broken_data__subdata(self):
        registry = ActionRecipientsRegistry().register(UserFKRecipient)
        field_name = 'invalid'
        recipient = registry.build_recipient({
            'type': UserFKRecipient.type_id,
            'entity': CreatedEntitySource(model=Contact).to_dict(),
            'field': field_name,
        })
        self.assertIsInstance(recipient, BrokenActionRecipient)
        self.assertEqual(
            _(
                'The recipient «{name}» is broken (original error: {error})'
            ).format(
                name=_('User field'),
                error=_('The field «{field}» is invalid in model «{model}»').format(
                    field=field_name, model=_('Contact'),
                ),
            ),
            recipient.message,
        )

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
