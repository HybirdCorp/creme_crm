from uuid import uuid4

from django.utils.html import escape
from django.utils.translation import gettext as _

from creme.creme_core.core.workflow import (
    BrokenSource,
    WorkflowBrokenData,
    workflow_registry,
)
from creme.creme_core.forms.workflows import (
    FixedUserSourceField,
    UserFKSourceField,
)
from creme.creme_core.workflows import (
    BrokenUserSource,
    CreatedEntitySource,
    EditedEntitySource,
    FixedUserSource,
    UserFKSource,
    UserSourceRegistry,
    user_source_registry,
)

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeOrganisation


class FixedUserSourceTestCase(CremeTestCase):
    def test_user_instance(self):
        user = self.get_root_user()

        type_id = 'fixed_user'
        user_src = FixedUserSource(user=user)
        self.assertEqual(type_id, user_src.type_id)
        self.assertEqual(_('Fixed user'), user_src.verbose_name)
        self.assertIsNone(user_src.wf_source)

        with self.assertNumQueries(0):
            self.assertEqual(user, user_src.user)

        self.assertEqual(
            _('Notify: {user}').format(user=user),
            user_src.render(user=user),
        )
        self.assertEqual(user, user_src.extract({}))
        self.assertEqual(
            'FixedUserSource(user=CremeUser(username="root"))', repr(user_src),
        )

    def test_user_instance__serialization(self):
        user = self.get_root_user()
        user_src = FixedUserSource(user=user)

        serialized = {'type': 'fixed_user', 'user': str(user.uuid)}
        self.assertDictEqual(serialized, user_src.to_dict())
        self.assertEqual(
            user_src,
            FixedUserSource.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_user_uuid(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        with self.assertNumQueries(0):
            user_src = FixedUserSource(user=str(user2.uuid))

        self.assertEqual('fixed_user', user_src.type_id)

        with self.assertNumQueries(1):
            self.assertEqual(user2, user_src.user)

        with self.assertNumQueries(0):
            user_src.user  # NOQA

        self.assertEqual(
            _('Notify: {user}').format(user=user2),
            user_src.render(user=user1),
        )
        self.assertEqual(user2, user_src.extract({}))

    def test_user_uuid__serialization(self):
        user = self.get_root_user()
        user_src = FixedUserSource(user=str(user.uuid))

        serialized = {'type': 'fixed_user', 'user': str(user.uuid)}
        self.assertDictEqual(serialized, user_src.to_dict())
        self.assertEqual(
            user_src,
            FixedUserSource.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_eq(self):
        user1 = self.get_root_user()
        user2 = self.create_user()
        recipient1 = FixedUserSource(user=user1)
        self.assertEqual(recipient1, FixedUserSource(user=user1))
        self.assertNotEqual(recipient1, FixedUserSource(user=str(user2.uuid)))
        self.assertNotEqual(None, recipient1)

    def test_inactive_user(self):
        user1 = self.get_root_user()
        user2 = self.create_user(is_active=False)
        user_src = FixedUserSource(user=user2)
        self.assertIsNone(user_src.extract({}))

        self.assertEqual(
            '{}<span class="warninglist">{}</span>'.format(
                escape(_('Notify:')),
                escape(
                    _(
                        'The user «{username}» is disabled (no action will be performed)'
                    ).format(username=user2.username)
                ),
            ),
            user_src.render(user=user1),
        )

    def test_broken_user(self):
        user_src = FixedUserSource(user=str(uuid4()))

        with self.assertNumQueries(1):
            with self.assertRaises(WorkflowBrokenData) as cm:
                user_src.user # NOQA

        self.assertEqual(
            _('The user does not exist anymore'), str(cm.exception),
        )

        with self.assertNumQueries(0):
            with self.assertRaises(WorkflowBrokenData):
                user_src.user # NOQA

        self.assertIsNone(user_src.extract({}))

        self.assertEqual(
            '{}<p class="errorlist">{}</p>'.format(
                escape(_('Notify a fixed user')),
                escape(_('The user does not exist anymore')),
            ),
            user_src.render(user=self.get_root_user()),
        )

    def test_config_formfield(self):
        user = self.get_root_user()
        formfield = FixedUserSource.config_formfield(user=user)
        self.assertIsInstance(formfield, FixedUserSourceField)
        self.assertEqual(_('Fixed user'), formfield.label)

        self.assertIsNone(FixedUserSource.config_formfield(
            user=user, entity_source=CreatedEntitySource(model=FakeContact),
        ))

        self.assertEqual('fixed_user', FixedUserSource.config_formfield_kind_id())


class UserFKSourceTestCase(CremeTestCase):
    def test_field_user(self):
        user1 = self.get_root_user()

        type_id = 'user_fk'
        source = CreatedEntitySource(model=FakeOrganisation)
        field_name = 'user'
        user_src = UserFKSource(entity_source=source, field_name=field_name)
        self.assertEqual(type_id,         user_src.type_id)
        self.assertEqual(_('User field'), user_src.verbose_name)
        self.assertEqual(field_name,      user_src.field_name)
        self.assertEqual(source,          user_src.wf_source)
        self.assertEqual(
            _('Notify the user «{field}» of: {source}').format(
                field=_('Owner user'),
                source=source.render(user=user1, mode=source.RenderMode.HTML),
            ),
            user_src.render(user=user1),
        )
        self.assertEqual(
            'UserFKSource('
            'entity_source=CreatedEntitySource(model=FakeOrganisation)), '
            'field_name="user"'
            ')',
            repr(user_src),
        )

    def test_eq(self):
        source1 = CreatedEntitySource(model=FakeContact)
        field_name1 = 'user'
        recipient1 = UserFKSource(entity_source=source1, field_name=field_name1)
        self.assertEqual(
            recipient1,
            UserFKSource(entity_source=source1, field_name=field_name1),
        )
        self.assertNotEqual(
            recipient1,
            UserFKSource(entity_source=source1, field_name='is_user'),
        )
        self.assertNotEqual(
            recipient1,
            UserFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name=field_name1,
            ),
        )
        self.assertNotEqual(None, recipient1)

    def test_field_user__extraction(self):
        user_src = UserFKSource(
            entity_source=CreatedEntitySource(model=FakeOrganisation),
            field_name='user',
        )

        user = self.create_user(index=0)
        orga = FakeOrganisation.objects.create(user=user, name='Bebop')
        self.assertEqual(
            user, user_src.extract({CreatedEntitySource.type_id: orga}),
        )

    def test_field_user__serialization(self):
        source = CreatedEntitySource(model=FakeOrganisation)
        field_name = 'user'
        user_src = UserFKSource(entity_source=source, field_name=field_name)

        serialized = {
            'type': 'user_fk',
            'entity': source.to_dict(),
            'field': field_name,
        }
        self.assertDictEqual(serialized, user_src.to_dict())
        self.assertEqual(
            user_src,
            UserFKSource.from_dict(data=serialized, registry=workflow_registry),
        )

    def test_field_is_user(self):
        user = self.get_root_user()

        source = EditedEntitySource(model=FakeContact)
        field_name = 'is_user'
        recipient = UserFKSource(entity_source=source, field_name=field_name)
        self.assertEqual(source,     recipient.wf_source)
        self.assertEqual(field_name, recipient.field_name)
        self.assertEqual(
            _('Notify the user «{field}» of: {source}').format(
                field=_('Related user'),
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            recipient.render(user=user),
        )

    def test_field_is_user__extraction(self):
        user1 = self.get_root_user()
        user2 = self.create_user()

        recipient = UserFKSource(
            entity_source=EditedEntitySource(model=FakeContact),
            field_name='is_user',
        )
        self.assertEqual(
            user1, recipient.extract({EditedEntitySource.type_id: user1.linked_contact}),
        )
        self.assertIsNone(
            recipient.extract({
                EditedEntitySource.type_id: FakeContact.objects.create(
                    user=user2, first_name='Faye', last_name='Valentine',
                ),
            }),
        )

    def test_inactive_user(self):
        user = self.create_user(is_active=False)
        recipient = UserFKSource(
            entity_source=CreatedEntitySource(model=FakeOrganisation),
            field_name='user',
        )
        orga = FakeOrganisation.objects.create(user=user, name='Bebop')
        self.assertIsNone(
            recipient.extract({CreatedEntitySource.type_id: orga}),
        )

    def test_broken_source(self):
        message = 'Invalid model'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKSource(
                entity_source=BrokenSource(message=message),
                field_name='user',
            )

        self.assertEqual(message, str(cm.exception))

    def test_broken_field__unknown(self):
        field_name = 'invalid'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name=field_name,
            )

        self.assertEqual(
            _('The field «{field}» is invalid in model «{model}»').format(
                field=field_name, model='Test Organisation',
            ),
            str(cm.exception),
        )

    def test_broken_field__not_fk(self):
        field_name = 'name'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name=field_name,
            )

        self.assertEqual(
            f'The field "{field_name}" is not a ForeignKey',
            str(cm.exception),
        )

    def test_broken_field__not_fk_to_user(self):
        field_name = 'sector'

        with self.assertRaises(WorkflowBrokenData) as cm:
            UserFKSource(
                entity_source=CreatedEntitySource(model=FakeOrganisation),
                field_name=field_name,
            )

        self.assertEqual(
            f'The field "{field_name}" is not a ForeignKey to User',
            str(cm.exception),
        )

    def test_config_formfield(self):
        user = self.get_root_user()
        self.assertIsNone(UserFKSource.config_formfield(user=user))

        source = CreatedEntitySource(model=FakeOrganisation)
        formfield = UserFKSource.config_formfield(user=user, entity_source=source)
        self.assertIsInstance(formfield, UserFKSourceField)
        self.assertEqual(
            _('Field to a user of: {source}').format(
                source=source.render(user=user, mode=source.RenderMode.HTML),
            ),
            formfield.label,
        )
        self.assertEqual(
            'created_entity|user_fk',
            UserFKSource.config_formfield_kind_id(wf_source=source),
        )


class UserSourceRegistryTestCase(CremeTestCase):
    def test_BrokenUserSource(self):
        message = 'Invalid field'
        user_source = BrokenUserSource(message=message)
        self.assertEqual('',      user_source.type_id)
        self.assertEqual(message, user_source.message)
        self.assertIsNone(user_source.extract({}))
        self.assertEqual(
            f'<p class="errorlist">{message}</p>',
            user_source.render(user=self.get_root_user()),
        )

    def test_main(self):
        registry = UserSourceRegistry()
        self.assertFalse([*registry.user_source_classes])

        registry.register(FixedUserSource, UserFKSource)
        self.assertCountEqual(
            [FixedUserSource, UserFKSource],
            [*registry.user_source_classes],
        )

        user_src1 = FixedUserSource(user=self.get_root_user())
        self.assertEqual(user_src1, registry.build_user_source(user_src1.to_dict()))

        user_src2 = UserFKSource(
            entity_source=CreatedEntitySource(model=FakeOrganisation), field_name='user',
        )
        self.assertEqual(user_src2, registry.build_user_source(user_src2.to_dict()))

        # ---
        registry.unregister(FixedUserSource)
        self.assertListEqual([UserFKSource], [*registry.user_source_classes])

    def test_error__duplicated(self):
        registry = UserSourceRegistry()

        class TestUserSource1(FixedUserSource):
            pass

        class TestUserSource2(FixedUserSource):
            pass

        registry.register(TestUserSource1)

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestUserSource2)

    def test_error__empty_id(self):
        registry = UserSourceRegistry()

        class TestUserSource(FixedUserSource):
            type_id = ''

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestUserSource)

    def test_error__unknown_id(self):
        registry = UserSourceRegistry()

        with self.assertRaises(registry.UnRegistrationError):
            registry.unregister(FixedUserSource)

    def test_error__forbidden_char_in_id(self):
        registry = UserSourceRegistry()

        class TestUSource1(FixedUserSource):
            type_id = 'type_w|th_p|pe'

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestUSource1)

        # ---
        class TestUSource2(FixedUserSource):
            type_id = 'type_with_#ash'

        with self.assertRaises(registry.RegistrationError):
            registry.register(TestUSource2)

    def test_broken_data__invalid_type_id(self):
        type_id = 'uninstalled_app-my_user_source'
        registry = UserSourceRegistry()
        recipient = registry.build_user_source({
            'type': type_id,
            # ...
        })
        self.assertIsInstance(recipient, BrokenUserSource)
        self.assertEqual(
            _(
                'The type of user-source «{type}» is invalid (uninstalled app?)'
            ).format(type=type_id),
            recipient.message,
        )

    def test_broken_data__subdata(self):
        registry = UserSourceRegistry().register(UserFKSource)
        field_name = 'invalid'
        user_src = registry.build_user_source({
            'type': UserFKSource.type_id,
            'entity': CreatedEntitySource(model=FakeContact).to_dict(),
            'field': field_name,
        })
        self.assertIsInstance(user_src, BrokenUserSource)
        self.assertEqual(
            _(
                'The user-source «{name}» is broken (original error: {error})'
            ).format(
                name=_('User field'),
                error=_('The field «{field}» is invalid in model «{model}»').format(
                    field=field_name, model='Test Contact',
                ),
            ),
            user_src.message,
        )

    def test_global_registry(self):
        self.assertCountEqual(
            [
                FixedUserSource,
                UserFKSource,
            ],
            [*user_source_registry.user_source_classes],
        )
