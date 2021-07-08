# -*- coding: utf-8 -*-

from django.contrib.contenttypes.models import ContentType
from django.urls.base import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core import actions
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui.actions import (
    ActionRegistrationError,
    ActionsChain,
    ActionsRegistry,
    BulkAction,
    UIAction,
)
from creme.creme_core.gui.merge import merge_form_registry
from creme.creme_core.models import CremeEntity, CremeUser
from creme.creme_core.models.auth import SetCredentials, UserRole

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeOrganisation


class MockAction(UIAction):
    id = UIAction.generate_id('creme_core', 'mock_action')

    type = 'test'
    model = CremeEntity
    label = 'Test action'
    icon = 'test'

    def _get_options(self):
        return {
            'user_name': self.user.username,
            'instance_id': self.instance.id,
        }

    def _get_data(self):
        return {
            'id': self.instance.id,
        }


class MockBulkAction(BulkAction):
    id = UIAction.generate_id('creme_core', 'mock_action_bulk')

    type = 'test-bulk'
    model = CremeEntity
    label = 'Test bulk action'
    icon = 'test-bulk'

    def _get_options(self):
        return {
            'user_name': self.user.username,
        }


class MockContactAction(MockAction):
    model = FakeContact


class MockContactBulkAction(MockBulkAction):
    model = FakeContact


class MockOrganisationAction(MockAction):
    model = FakeOrganisation


class MockOrganisationBulkAction(MockBulkAction):
    model = FakeOrganisation


class ActionsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(ActionsTestCase, cls).setUpClass()

        cls.user = CremeUser(
            username='yui', email='kawa.yui@kimengumi.jp',
            first_name='Yui', last_name='Kawa',
        )

    def setUp(self):
        super().setUp()
        self.registry = ActionsRegistry()

    def assertSortedActions(self, expected_classes, actions):
        def key(a):
            return a.id or ''

        self.assertListEqual(
            sorted(expected_classes, key=key),
            sorted((a.__class__ for a in actions), key=key),
        )

    def test_action_data(self):
        user = self.user
        self.assertIsNone(UIAction(user, model=CremeEntity).action_data)

        self.assertDictEqual(
            {
                'options': {
                    'user_name': user.username,
                },
                'data': {},
            },
            MockBulkAction(user, model=CremeEntity).action_data,
        )
        self.assertDictEqual(
            {
                'options': {
                    'user_name': user.username,
                    'instance_id': user.id,
                },
                'data': {
                    'id': user.id
                },
            },
            MockAction(user, model=CremeEntity, instance=user).action_data,
        )

    def test_action_model(self):
        user = self.user
        self.assertEqual(FakeContact, UIAction(user, model=FakeContact).model)
        self.assertEqual(FakeOrganisation, UIAction(user, instance=FakeOrganisation()).model)

        with self.assertRaises(AssertionError):
            UIAction(user)

    def test_action_is_visible(self):
        other_user = CremeUser(username='other', first_name='other', last_name='other')

        class OnlyForYuiAction(MockAction):
            @property
            def is_visible(self):
                return self.user.username == 'yui'

        self.assertTrue(MockAction(self.user).is_visible)
        self.assertTrue(MockAction(other_user).is_visible)

        self.assertTrue(OnlyForYuiAction(self.user).is_visible)
        self.assertFalse(OnlyForYuiAction(other_user).is_visible)

    def test_actions_chain(self):
        achain = ActionsChain()
        self.assertListEqual([], achain.actions(model=FakeContact))

        class OrgaAction(MockOrganisationAction):
            id = 'test-contact_action'

        class ContactAction(MockContactAction):
            id = 'test-orga_action'

        achain.register_actions(MockAction, ContactAction, OrgaAction)
        self.assertEqual([MockAction], achain.actions(CremeEntity))
        self.assertCountEqual(
            [MockAction, ContactAction], achain.actions(FakeContact)
        )
        self.assertCountEqual(
            [MockAction, OrgaAction], achain.actions(FakeOrganisation)
        )

    def test_actions_chain_error(self):
        achain = ActionsChain(base_class=MockBulkAction)

        with self.assertRaises(ActionRegistrationError) as ctxt:
            achain.register_actions(MockAction)

        self.assertEqual(
            f'{MockAction} is not a <MockBulkAction>', str(ctxt.exception),
        )

    def test_actions_chain_void(self):
        achain = ActionsChain()
        self.assertListEqual([], achain.actions(model=FakeContact))

        class MockA(MockAction):
            id = 'test-a'

        class MockB(MockContactAction):
            id = 'test-b'

        class MockC(MockAction):
            id = 'test-c'

        achain.register_actions(MockA, MockB, MockC)
        achain.void_actions(FakeOrganisation, MockC)

        self.assertCountEqual([MockA, MockC],        achain.actions(CremeEntity))
        self.assertCountEqual([MockA, MockB, MockC], achain.actions(FakeContact))
        self.assertCountEqual([MockA],               achain.actions(FakeOrganisation))

    def test_action_is_registered_for_bulk01(self):
        "Empty."
        registry = self.registry

        self.assertFalse([*registry.bulk_actions(user=self.user, model=FakeContact)])

        # TODO ?
        # self.assertIsNone(registry.bulk_action(FakeContact, MockBulkAction.id))
        # self.assertFalse(MockBulkAction.is_registered_for_bulk(CremeEntity, registry=registry))
        # self.assertFalse(MockBulkAction.is_registered_for_bulk(FakeContact, registry=registry))

    def test_action_is_registered_for_bulk02(self):
        "One action registered."
        user = self.user
        registry = self.registry

        registry.register_bulk_actions(MockBulkAction)

        # Entity ---
        entity_actions = [*registry.bulk_actions(user, CremeEntity)]
        self.assertEqual(1, len(entity_actions))

        entity_action = entity_actions[0]
        self.assertIsInstance(entity_action, MockBulkAction)
        self.assertEqual(user,        entity_action.user)
        self.assertEqual(CremeEntity, entity_action.model)

        # Contact ---
        contact_actions = [*registry.bulk_actions(user, FakeContact)]
        self.assertEqual(1, len(contact_actions))

        contact_action = contact_actions[0]
        self.assertIsInstance(contact_action, MockBulkAction)
        self.assertEqual(user,        contact_action.user)
        self.assertEqual(FakeContact, contact_action.model)

        # TODO ?
        # self.assertTrue(MockBulkAction.is_registered_for_bulk(CremeEntity, registry=registry))
        # self.assertTrue(MockBulkAction.is_registered_for_bulk(FakeContact, registry=registry))

    def test_action_is_registered_for_instance01(self):
        "Empty."
        user = self.user
        registry = self.registry
        instance = FakeContact(user=user, first_name='Yui', last_name='Kawa')

        self.assertFalse([*registry.instance_actions(user=user, instance=instance)])

        self.assertEqual([], registry.instance_action_classes(model=CremeEntity))
        self.assertEqual([], registry.instance_action_classes(model=FakeContact))

        # TODO ?
        # self.assertEqual(None, registry.instance_action(FakeContact, MockAction.id))
        # self.assertFalse(MockAction.is_registered_for_instance(CremeEntity, registry=registry))
        # self.assertFalse(MockAction.is_registered_for_instance(FakeContact, registry=registry))

    def test_action_is_registered_for_instance02(self):
        "One action registered."
        user = self.user
        registry = self.registry
        entity = CremeEntity(user=user)
        contact = FakeContact(user=user, first_name='Yui', last_name='Kawa')

        registry.register_instance_actions(MockAction)

        # Entity ---
        entity_actions = [*registry.instance_actions(user=user, instance=entity)]
        self.assertEqual(1, len(entity_actions))

        entity_action = entity_actions[0]
        self.assertIsInstance(entity_action, MockAction)
        self.assertEqual(user,        entity_action.user)
        self.assertEqual(CremeEntity, entity_action.model)
        self.assertEqual(entity,      entity_action.instance)

        self.assertListEqual(
            [MockAction], registry.instance_action_classes(model=CremeEntity),
        )

        # Contact ---
        contact_actions = [*registry.instance_actions(user=user, instance=contact)]
        self.assertEqual(1, len(contact_actions))

        contact_action = contact_actions[0]
        self.assertIsInstance(contact_action, MockAction)
        self.assertEqual(user,        contact_action.user)
        self.assertEqual(FakeContact, contact_action.model)
        self.assertEqual(contact,     contact_action.instance)

        self.assertListEqual(
            [MockAction], registry.instance_action_classes(model=FakeContact),
        )

    def test_register_invalid_type(self):
        invalid_action = FakeContact

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_instance_actions(invalid_action)

        self.assertEqual(
            f'{invalid_action} is not a <UIAction>', str(ctxt.exception),
        )

        # --
        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_bulk_actions(MockAction)  # not bulk !

        self.assertEqual(
            f'{MockAction} is not a <BulkAction>', str(ctxt.exception),
        )

    def test_register_missing_model01(self):
        "Instance action"
        class MissingModelAction(UIAction):
            id = 'tests_missingmodel'

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_instance_actions(MissingModelAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {MissingModelAction}: 'model' attribute must be defined",
        )

    def test_register_missing_model02(self):
        "Bulk action."
        class MissingModelAction(BulkAction):
            id = 'tests_missingmodel'

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_bulk_actions(MissingModelAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {MissingModelAction}: 'model' attribute must be defined"
        )

    def test_register_missing_id01(self):
        "Instance action."
        class MissingIdAction(UIAction):
            model = CremeEntity

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_instance_actions(MissingIdAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {MissingIdAction}: 'id' attribute must be defined",
        )

    def test_register_missing_id02(self):
        "Bulk action."
        class MissingIdAction(BulkAction):
            model = CremeEntity

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_bulk_actions(MissingIdAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {MissingIdAction}: 'id' attribute must be defined",
        )

    def test_register_invalid_model01(self):
        "Instance action."
        class InvalidModelAction(UIAction):
            id = 'tests_invalidmodel'
            model = UIAction

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_instance_actions(InvalidModelAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {InvalidModelAction}: {UIAction} is not a Django Model",
        )

    def test_register_invalid_model02(self):
        "Bulk action."
        class InvalidModelAction(BulkAction):
            id = 'tests_invalidmodel'
            model = UIAction

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.register_bulk_actions(InvalidModelAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Invalid action {InvalidModelAction}: {UIAction} is not a Django Model",
        )

    def test_override_duplicate(self):
        user = self.user
        registry = self.registry

        registry.register_instance_actions(MockAction) \
                .register_instance_actions(MockContactAction)

        entity = CremeEntity(user=user)
        contact = FakeContact(user=user)

        self.assertSortedActions(
            [MockAction],  registry.instance_actions(user=user, instance=entity)
        )
        self.assertSortedActions(
            [MockContactAction], registry.instance_actions(user=user, instance=contact)
        )

        # Same action, no problem
        registry.register_instance_actions(MockContactAction)

        self.assertSortedActions(
            [MockAction], registry.instance_actions(user=user, instance=entity),
        )
        self.assertSortedActions(
            [MockContactAction], registry.instance_actions(user=user, instance=contact),
        )

        # Other action, raise error ---
        class MockA(MockContactAction):
            pass

        with self.assertRaises(ActionRegistrationError) as ctxt:
            registry.register_instance_actions(MockA)

        self.assertEqual(
            str(ctxt.exception),
            f"Duplicated action '{MockA.id}' for model {MockContactAction.model}",
        )

    def test_register(self):
        user = self.user
        registry = self.registry

        contact = FakeContact(user=user)
        orga = FakeOrganisation(user=user)

        self.assertFalse([*registry.instance_actions(user=user, instance=contact)])
        self.assertFalse([*registry.instance_actions(user=user, instance=orga)])

        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

        # ---
        registry.register_instance_actions(MockContactAction)

        self.assertSortedActions(
            [MockContactAction],
            [*registry.instance_actions(user=user, instance=contact)],
        )
        self.assertFalse([*registry.instance_actions(user=user, instance=orga)])

        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

        # ---
        registry.register_bulk_actions(MockContactBulkAction)

        self.assertSortedActions(
            [MockContactAction],
            registry.instance_actions(user=user, instance=contact),
        )
        self.assertFalse([*registry.instance_actions(user=user, instance=orga)])

        self.assertSortedActions(
            [MockContactBulkAction],
            registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

    def test_register_entity(self):
        user = self.user
        registry = self.registry

        contact = FakeContact(user=user)
        orga = FakeOrganisation(user=user)

        self.assertFalse([*registry.instance_actions(user=user, instance=contact)])
        self.assertFalse([*registry.instance_actions(user=user, instance=orga)])

        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

        # ---
        registry.register_instance_actions(MockAction)

        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=contact),
        )
        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=orga),
        )

        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

        # ---
        registry.register_bulk_actions(MockBulkAction)

        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=contact),
        )
        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=orga),
        )

        self.assertSortedActions(
            [MockBulkAction],
            registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertSortedActions(
            [MockBulkAction],
            registry.bulk_actions(user=user, model=FakeOrganisation),
        )

    def test_override01(self):
        "Empty."
        user = self.user
        registry = self.registry

        self.assertFalse(
            [*registry.instance_actions(user=user, instance=CremeEntity(user=user))],
        )
        self.assertFalse(
            [*registry.instance_actions(user=user, instance=FakeContact(user=user))],
        )
        self.assertFalse(
            [*registry.instance_actions(user=user, instance=FakeOrganisation(user=user))],
        )

        self.assertFalse([*registry.bulk_actions(user=user, model=CremeEntity)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

    def test_override02(self):
        "Instance action."
        user = self.user
        registry = self.registry

        registry.register_instance_actions(MockAction)
        registry.register_instance_actions(MockContactAction)

        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=CremeEntity(user=user)),
        )
        self.assertSortedActions(
            [MockContactAction],
            registry.instance_actions(user=user, instance=FakeContact(user=user)),
        )
        self.assertSortedActions(
            [MockAction],
            registry.instance_actions(user=user, instance=FakeOrganisation(user=user)),
        )

        self.assertFalse([*registry.bulk_actions(user=user, model=CremeEntity)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeContact)])
        self.assertFalse([*registry.bulk_actions(user=user, model=FakeOrganisation)])

    def test_override03(self):
        "Bulk action."
        user = self.user
        registry = self.registry

        registry.register_bulk_actions(MockBulkAction) \
                .register_bulk_actions(MockContactBulkAction)

        self.assertFalse(
            [*registry.instance_actions(user=user, instance=CremeEntity(user=user))],
        )
        self.assertFalse(
            [*registry.instance_actions(user=user, instance=FakeContact(user=user))],
        )
        self.assertFalse(
            [*registry.instance_actions(user=user, instance=FakeOrganisation(user=user))],
        )

        self.assertSortedActions(
            [MockBulkAction],
            registry.bulk_actions(user=user, model=CremeEntity),
        )
        self.assertSortedActions(
            [MockContactBulkAction],
            registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertSortedActions(
            [MockBulkAction],
            registry.bulk_actions(user=user, model=FakeOrganisation),
        )

    def test_actions01(self):
        "Instance actions."
        user = self.user
        registry = self.registry

        class MockA(MockOrganisationAction):
            id = 'test-a'

        class MockB(MockContactAction):
            id = 'test-b'

        class MockC(MockOrganisationAction):
            id = 'test-c'

        registry.register_instance_actions(MockA, MockB, MockC)

        self.assertSortedActions(
            [MockB],
            registry.instance_actions(
                user=user, instance=FakeContact(user=user, last_name='Kawa'),
            )
        )
        self.assertSortedActions(
            [MockA, MockC],
            registry.instance_actions(
                user=user, instance=FakeOrganisation(user=user, name='Kimengumi'),
            )
        )
        self.assertCountEqual(
            [MockA, MockC],
            registry.instance_action_classes(model=FakeOrganisation),
        )

    def test_actions02(self):
        "Bulk actions"
        user = self.user
        registry = self.registry

        class MockA(MockContactBulkAction):
            id = 'test-aaa'

        class MockB(MockOrganisationBulkAction):
            id = 'test-bbb'

        class MockC(MockContactBulkAction):
            id = 'test-ccc'

        registry.register_bulk_actions(MockA, MockB, MockC)

        self.assertCountEqual([],             registry.bulk_action_classes(CremeEntity))
        self.assertCountEqual([MockA, MockC], registry.bulk_action_classes(FakeContact))
        self.assertCountEqual([MockB],        registry.bulk_action_classes(FakeOrganisation))

        self.assertSortedActions(
            [], registry.bulk_actions(user=user, model=CremeEntity),
        )
        self.assertSortedActions(
            [MockA, MockC], registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertSortedActions(
            [MockB], registry.bulk_actions(user=user, model=FakeOrganisation),
        )

    def test_actions_override01(self):
        "Instance actions."
        user = self.user
        registry = self.registry

        class MockA(MockAction):
            id = 'test-a'

        class MockB(MockContactAction):
            id = 'test-b'

        class MockC(MockOrganisationAction):
            id = 'test-c'

        class MockAOverride(MockOrganisationAction):
            id = 'test-a'

        registry.register_instance_actions(MockA, MockB, MockC)
        registry.register_instance_actions(MockAOverride)

        entity  = CremeEntity(user=user)
        contact = FakeContact(user=user, last_name='Kawa')
        orga    = FakeOrganisation(user=user, name='Kimengumi')

        self.assertSortedActions(
            [MockA], registry.instance_actions(user=user, instance=entity),
        )
        self.assertSortedActions(
            [MockA, MockB], registry.instance_actions(user=user, instance=contact),
        )
        self.assertSortedActions(
            [MockAOverride, MockC], registry.instance_actions(user=user, instance=orga),
        )

        # TODO ?
        # self.assertEqual(MockA,         registry.instance_action(CremeEntity, 'test-a'))
        # self.assertEqual(MockA,         registry.instance_action(FakeContact, 'test-a'))
        # self.assertEqual(MockAOverride, registry.instance_action(FakeOrganisation, 'test-a'))

    def test_actions_override02(self):
        "Bulk actions"
        user = self.user
        registry = self.registry

        class MockA(MockBulkAction):
            id = 'test-a'

        class MockAOverride(MockOrganisationBulkAction):
            id = 'test-a'

        class MockB(MockContactBulkAction):
            id = 'test-b'

        registry.register_instance_actions(MockAOverride)

        registry.register_bulk_actions(MockA, MockB)
        registry.register_bulk_actions(MockAOverride)

        self.assertSortedActions(
            [MockA], registry.bulk_actions(user=user, model=CremeEntity),
        )
        self.assertSortedActions(
            [MockA, MockB], registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertSortedActions(
            [MockAOverride], registry.bulk_actions(user=user, model=FakeOrganisation),
        )

        # TODO ?
        # self.assertEqual(MockA,         registry.bulk_action(CremeEntity, 'test-a'))
        # self.assertEqual(MockA,         registry.bulk_action(FakeContact, 'test-a'))
        # self.assertEqual(MockAOverride, registry.bulk_action(FakeOrganisation, 'test-a'))

    def test_actions_void01(self):
        "Instance actions"
        user = self.user
        registry = self.registry

        class MockA(MockAction):
            id = 'test-a'

        class MockB(MockContactAction):
            id = 'test-b'

        class MockC(MockAction):
            id = 'test-c'

        registry.register_instance_actions(
            MockA, MockB, MockC,
        ).void_instance_actions(FakeOrganisation, MockC)

        entity = CremeEntity(user=user)
        contact = FakeContact(user=user, last_name='Kawa')
        orga = FakeOrganisation(user=user, name='Kimengumi')

        self.assertSortedActions(
            [MockA, MockC], registry.instance_actions(user=user, instance=entity)
        )
        self.assertSortedActions(
            [MockA, MockB, MockC],
            registry.instance_actions(user=user, instance=contact),
        )
        self.assertSortedActions(
            [MockA], registry.instance_actions(user=user, instance=orga),
        )

        # TODO ?
        # self.assertEqual(MockC, registry.instance_action(CremeEntity, 'test-c'))
        # self.assertEqual(MockC, registry.instance_action(FakeContact, 'test-c'))
        # self.assertEqual(None,  registry.instance_action(FakeOrganisation, 'test-c'))

    def test_actions_void02(self):
        "Bulk actions."
        user = self.user
        registry = self.registry

        class MockA(MockBulkAction):
            id = 'test-a'

        class MockB(MockContactBulkAction):
            id = 'test-b'

        class MockC(MockBulkAction):
            id = 'test-c'

        res = registry.void_instance_actions(
            FakeOrganisation, MockC,
        ).register_bulk_actions(
            MockA, MockB, MockC,
        ).void_bulk_actions(
            FakeOrganisation, MockA,
        )
        self.assertIs(res, registry)

        self.assertSortedActions(
            [MockA, MockC],
            registry.bulk_actions(user=user, model=CremeEntity),
        )
        self.assertSortedActions(
            [MockA, MockB, MockC],
            registry.bulk_actions(user=user, model=FakeContact),
        )
        self.assertSortedActions(
            [MockC],
            registry.bulk_actions(user=user, model=FakeOrganisation),
        )

        # TODO ?
        # self.assertEqual(MockA, registry.bulk_action(CremeEntity, 'test-a'))
        # self.assertEqual(MockA, registry.bulk_action(FakeContact, 'test-a'))
        # self.assertEqual(None,  registry.bulk_action(FakeOrganisation, 'test-a'))

    def test_actions_duplicate_void01(self):
        "Instance action."
        self.registry.register_instance_actions(MockContactAction)

        with self.assertRaises(ActionRegistrationError) as ctxt:
            self.registry.void_instance_actions(FakeContact, MockContactAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Unable to void action 'creme_core-mock_action'. "
            f"An action is already defined for model {FakeContact}"
        )

    def test_actions_duplicate_void02(self):
        "Bulk action."
        registry = self.registry
        registry.register_bulk_actions(MockContactBulkAction)

        with self.assertRaises(ActionRegistrationError) as ctxt:
            registry.void_bulk_actions(FakeContact, MockContactBulkAction)

        self.assertEqual(
            str(ctxt.exception),
            f"Unable to void action 'creme_core-mock_action_bulk'. "
            f"An action is already defined for model {FakeContact}"
        )


class BuiltinActionsTestCase(CremeTestCase):
    @classmethod
    def _create_role(
            cls, name,
            allowed_apps=(),
            admin_4_apps=(),
            set_creds=(),
            creates=(),
            users=()):
        get_ct = ContentType.objects.get_for_model

        role = UserRole(name=name)
        role.allowed_apps = allowed_apps
        role.admin_4_apps = admin_4_apps
        role.save()

        role.creatable_ctypes.set([get_ct(model) for model in creates])
        role.save()

        for sc in set_creds:
            if len(sc) == 2:
                value, set_type = sc
                ctype = None
            else:
                value, set_type, model = sc
                ctype = ContentType.objects.get_for_model(model)

            SetCredentials.objects.create(role=role, value=value, set_type=set_type, ctype=ctype)

        for user in users:
            user.role = role
            user.save()

        return role

    @classmethod
    def setUpClass(cls):
        super(BuiltinActionsTestCase, cls).setUpClass()

        cls.user = user = CremeUser(
            username='yui', email='kawa.yui@kimengumi.jp',
            first_name='Yui', last_name='Kawa',
        )
        cls.other_user = other_user = CremeUser(
            username='johndoe', email='john.doe@unknown.org',
            first_name='John', last_name='Doe',
        )

        cls.role = cls._create_role(
            'Action view only', ['creme_core'],
            users=[user, other_user],  # 'persons'
            set_creds=[
                (EntityCredentials._ALL_CREDS, SetCredentials.ESET_OWN),
            ],
            creates=[FakeContact],
        )

        create_contact = FakeContact.objects.create
        cls.contact = create_contact(last_name='A', user=user)
        cls.contact_other = create_contact(last_name='B', user=other_user)

    def assertAction(self, action, model, action_id, action_type, url, **kwargs):
        self.assertEqual(action.model, model)
        self.assertEqual(action.id, action_id)
        self.assertEqual(action.type, action_type)
        self.assertEqual(action.url, url)

        for key, expected in kwargs.items():
            value = getattr(action, key)
            self.assertEqual(value, expected, f'action.{key}')

    def test_edit_action(self):
        self.assertAction(
            actions.EditAction(self.user, FakeContact, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-edit',
            action_type='redirect',
            url=self.contact.get_edit_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Edit'),
            icon='edit',
        )
        self.assertAction(
            actions.EditAction(self.user, FakeContact, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-edit',
            action_type='redirect',
            url=self.contact_other.get_edit_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Edit'),
            icon='edit',
        )

    def test_delete_action(self):
        self.assertAction(
            actions.DeleteAction(self.user, FakeContact, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-delete',
            action_type='delete',
            url=self.contact.get_delete_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Delete'),
            icon='delete',
        )
        self.assertAction(
            actions.DeleteAction(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-delete',
            action_type='delete',
            url=self.contact_other.get_delete_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Delete'),
            icon='delete',
        )

    def test_view_action(self):
        self.assertAction(
            actions.ViewAction(self.user, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-view',
            action_type='redirect',
            url=self.contact.get_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=True,
            label=_('See'),
            icon='view',
            help_text=gettext('Go to the entity {entity}').format(entity=self.contact),
        )
        self.assertAction(
            actions.ViewAction(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-view',
            action_type='redirect',
            url=self.contact_other.get_absolute_url(),
            is_enabled=False,  # other users can view entity
            is_visible=True,
            is_default=True,
            label=_('See'),
            icon='view',
            help_text=gettext('Go to the entity {entity}').format(entity=self.contact_other),
        )

    def test_clone_action(self):
        self.assertTrue(self.user.has_perm_to_create(self.contact))
        self.assertTrue(self.user.has_perm_to_view(self.contact))

        self.assertAction(
            actions.CloneAction(self.user, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-clone',
            action_type='clone',
            url=self.contact.get_clone_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Clone'),
            icon='clone',
            action_data={
                'options': {},
                'data': {'id': self.contact.id},
            },
        )

        self.assertTrue(self.user.has_perm_to_create(self.contact_other))
        self.assertFalse(self.user.has_perm_to_view(self.contact_other))

        self.assertAction(
            actions.CloneAction(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-clone',
            action_type='clone',
            url=self.contact_other.get_clone_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Clone'),
            icon='clone',
            action_data={
                'options': {},
                'data': {'id': self.contact_other.id},
            },
        )

    def test_bulk_edit_action(self):
        get_ct = ContentType.objects.get_for_model

        self.assertAction(
            actions.BulkEditAction(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_edit',
            action_type='edit-selection',
            url=reverse('creme_core__bulk_update', args=(get_ct(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple update'),
            icon='edit',
        )
        self.assertAction(
            actions.BulkEditAction(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_edit',
            action_type='edit-selection',
            url=reverse('creme_core__bulk_update', args=(get_ct(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple update'),
            icon='edit',
        )

    def test_bulk_delete_action(self):
        self.assertAction(
            actions.BulkDeleteAction(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_delete',
            action_type='delete-selection',
            url=reverse('creme_core__delete_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple deletion'),
            icon='delete',
        )
        self.assertAction(
            actions.BulkDeleteAction(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_delete',
            action_type='delete-selection',
            url=reverse('creme_core__delete_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple deletion'),
            icon='delete',
        )

    def test_bulk_add_property_action(self):
        get_ct = ContentType.objects.get_for_model
        self.assertAction(
            actions.BulkAddPropertyAction(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_add_property',
            action_type='addto-selection',
            url=reverse('creme_core__add_properties_bulk', args=(get_ct(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple property adding'),
            icon='property',
        )
        self.assertAction(
            actions.BulkAddPropertyAction(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_add_property',
            action_type='addto-selection',
            url=reverse('creme_core__add_properties_bulk', args=(get_ct(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple property adding'),
            icon='property',
        )

    def test_bulk_add_relation_action(self):
        get_ct = ContentType.objects.get_for_model
        self.assertAction(
            actions.BulkAddRelationAction(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_add_relation',
            action_type='addto-selection',
            url=reverse('creme_core__create_relations_bulk', args=(get_ct(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple relationship adding'),
            icon='relations',
        )
        self.assertAction(
            actions.BulkAddRelationAction(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_add_relation',
            action_type='addto-selection',
            url=reverse('creme_core__create_relations_bulk', args=(get_ct(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple relationship adding'),
            icon='relations',
        )

    def test_merge_action(self):
        get_ct = ContentType.objects.get_for_model

        self.assertIsNone(merge_form_registry.get(CremeEntity))
        self.assertIsNotNone(merge_form_registry.get(FakeContact))

        self.assertAction(
            actions.MergeAction(self.user),
            model=CremeEntity,
            ctype=get_ct(CremeEntity),
            action_id='creme_core-merge',
            action_type='merge-selection',
            url=reverse('creme_core__merge_entities'),
            is_enabled=False,
            is_visible=False,
            is_default=False,
            label=_('Merge 2 entities'),
            icon='merge',
        )
        self.assertAction(
            actions.MergeAction(self.user, model=FakeContact),
            model=FakeContact,
            ctype=get_ct(FakeContact),
            action_id='creme_core-merge',
            action_type='merge-selection',
            url=reverse('creme_core__merge_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Merge 2 entities'),
            icon='merge',
        )
