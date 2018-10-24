# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType
    from django.urls.base import reverse
    from django.utils.translation import gettext_lazy as _, gettext
    
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.gui import actions
    from creme.creme_core.models import CremeUser, CremeEntity
    from creme.creme_core.models.auth import SetCredentials, UserRole
    from creme.creme_core.templatetags.creme_ctype import ctype_can_be_merged
    
    from ..base import CremeTestCase
    from ..fake_models import (FakeContact, FakeOrganisation)
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class MockBulkAction(actions.ActionEntry):
    action_id = 'mock_action-bulk'

    action = 'test-bulk'
    model = CremeEntity
    label = 'Test bulk action'
    icon = 'test-bulk'

    def _get_options(self):
        return {
            'user_name': self.user.username
        }


class MockAction(actions.ActionEntry):
    action_id = 'mock_action'

    action = 'test'
    model = CremeEntity
    label = 'Test action'
    icon = 'test'

    def _get_options(self):
        return {
            'user_name': self.user.username,
            'instance_id': self.instance.id
        }

    def _get_data(self):
        return {
            'id': self.instance.id
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

        cls.user = CremeUser(username='yui', email='kawa.yui@kimengumi.jp',
                             first_name='Yui', last_name='Kawa',
                            )

    def setUp(self):
        self.registry = actions._ActionsRegistry()

    def assertSortedActions(self, expected, actions):
        _key = lambda a: a.action_id or ''

        self.assertEqual(sorted(expected, key=_key),
                         sorted(actions, key=_key))

    def test_action_data(self):
        self.assertEqual(None, actions.ActionEntry(self.user, model=CremeEntity).action_data)

        self.assertEqual({
                'options': {
                    'user_name': self.user.username
                },
                'data': {}
            }, MockBulkAction(self.user, model=CremeEntity).action_data)

        self.assertEqual({
                'options': {
                    'user_name': self.user.username,
                    'instance_id': self.user.id
                },
                'data': {
                    'id': self.user.id
                }
            }, MockAction(self.user, model=CremeEntity, instance=self.user).action_data)

    def test_action_context(self):
        self.assertEqual({}, actions.ActionEntry(self.user, model=CremeEntity).context)
        self.assertEqual({
            'custom': 12
        }, actions.ActionEntry(self.user, model=CremeEntity, instance=self.user, custom=12).context)

    def test_action_model(self):
        self.assertEqual(FakeContact, actions.ActionEntry(self.user, model=FakeContact).model)
        self.assertEqual(FakeOrganisation, actions.ActionEntry(self.user, instance=FakeOrganisation()).model)

        with self.assertRaises(AssertionError) as e:
            actions.ActionEntry(self.user)

    def test_action_is_visible(self):
        other_user = CremeUser(username='other',
                               first_name='other', last_name='other')

        class OnlyForYuiAction(MockAction):
            @property
            def is_visible(self):
                return self.user.username == 'yui'

        self.assertTrue(MockAction(self.user).is_visible)
        self.assertTrue(MockAction(other_user).is_visible)

        self.assertTrue(OnlyForYuiAction(self.user).is_visible)
        self.assertFalse(OnlyForYuiAction(other_user).is_visible)

    def test_action_is_registered_for_bulk(self):
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual(None, self.registry.bulk_action(FakeContact, MockBulkAction.action_id))

        self.assertFalse(MockBulkAction.is_registered_for_bulk(CremeEntity, registry=self.registry))
        self.assertFalse(MockBulkAction.is_registered_for_bulk(FakeContact, registry=self.registry))

        self.registry.register_bulk_actions(MockBulkAction)

        self.assertEqual([MockBulkAction], self.registry.bulk_actions(CremeEntity))
        self.assertEqual([MockBulkAction], self.registry.bulk_actions(FakeContact))

        self.assertTrue(MockBulkAction.is_registered_for_bulk(CremeEntity, registry=self.registry))
        self.assertTrue(MockBulkAction.is_registered_for_bulk(FakeContact, registry=self.registry))

    def test_action_is_registered_for_instance(self):
        self.assertEqual([], self.registry.instance_actions(FakeContact))
        self.assertEqual(None, self.registry.instance_action(FakeContact, MockAction.action_id))

        self.assertFalse(MockAction.is_registered_for_instance(CremeEntity, registry=self.registry))
        self.assertFalse(MockAction.is_registered_for_instance(FakeContact, registry=self.registry))

        self.registry.register_instance_actions(MockAction)

        self.assertEqual([MockAction], self.registry.instance_actions(CremeEntity))
        self.assertEqual([MockAction], self.registry.instance_actions(FakeContact))

        self.assertTrue(MockAction.is_registered_for_instance(CremeEntity, registry=self.registry))
        self.assertTrue(MockAction.is_registered_for_instance(FakeContact, registry=self.registry))

    def test_register_invalid_type(self):
        invalid_action = FakeContact

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_instance_actions(invalid_action)

        self.assertEqual(str(e.exception), "{} is not an ActionEntry".format(invalid_action))

    def test_register_missing_model(self):
        class MissingModelAction(actions.ActionEntry):
            action_id = 'tests_missingmodel'

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_instance_actions(MissingModelAction)

        self.assertEqual(str(e.exception), "Invalid action {}. 'model' attribute must be defined".format(MissingModelAction))

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_bulk_actions(MissingModelAction)

        self.assertEqual(str(e.exception), "Invalid action {}. 'model' attribute must be defined".format(MissingModelAction))

    def test_register_missing_id(self):
        class MissingIdAction(actions.ActionEntry):
            model = CremeEntity

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_instance_actions(MissingIdAction)

        self.assertEqual(str(e.exception), "Invalid action {}. 'action_id' attribute must be defined".format(MissingIdAction))

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_bulk_actions(MissingIdAction)

        self.assertEqual(str(e.exception), "Invalid action {}. 'action_id' attribute must be defined".format(MissingIdAction))

    def test_register_invalid_model(self):
        class InvalidModelAction(actions.ActionEntry):
            action_id = 'tests_invalidmodel'
            model = actions.ActionEntry

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_instance_actions(InvalidModelAction)

        self.assertEqual(str(e.exception), "Invalid action {}. {} is not a Django Model".format(InvalidModelAction, actions.ActionEntry))

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_bulk_actions(InvalidModelAction)

        self.assertEqual(str(e.exception), "Invalid action {}. {} is not a Django Model".format(InvalidModelAction, actions.ActionEntry))

    def test_override_duplicate(self):
        self.registry.register_instance_actions(MockAction)
        self.registry.register_instance_actions(MockContactAction)

        self.assertEqual([MockAction], self.registry.instance_actions(CremeEntity))
        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))

        # same action, no pb
        self.registry.register_instance_actions(MockContactAction)

        self.assertEqual([MockAction], self.registry.instance_actions(CremeEntity))
        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))

        class MockA(MockContactAction):
            pass

        # other action, raise
        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.register_instance_actions(MockA)

        self.assertEqual(str(e.exception),
                         "Duplicate action '{}' for model {}".format(MockA.action_id, MockContactAction.model))

    def test_register(self):
        self.assertEqual([], self.registry.instance_actions(FakeContact))
        self.assertEqual([], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_instance_actions(MockContactAction)

        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_bulk_actions(MockContactBulkAction)

        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([MockContactBulkAction], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

    def test_register_entity(self):
        self.assertEqual([], self.registry.instance_actions(FakeContact))
        self.assertEqual([], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_instance_actions(MockAction)

        self.assertEqual([MockAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([MockAction], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_bulk_actions(MockBulkAction)

        self.assertEqual([MockAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([MockAction], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([MockBulkAction], self.registry.bulk_actions(FakeContact))
        self.assertEqual([MockBulkAction], self.registry.bulk_actions(FakeOrganisation))

    def test_override(self):
        self.assertEqual([], self.registry.instance_actions(CremeEntity))
        self.assertEqual([], self.registry.instance_actions(FakeContact))
        self.assertEqual([], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(CremeEntity))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_instance_actions(MockAction)
        self.registry.register_instance_actions(MockContactAction)

        self.assertEqual([MockAction], self.registry.instance_actions(CremeEntity))
        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([MockAction], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([], self.registry.bulk_actions(CremeEntity))
        self.assertEqual([], self.registry.bulk_actions(FakeContact))
        self.assertEqual([], self.registry.bulk_actions(FakeOrganisation))

        self.registry.register_bulk_actions(MockAction)
        self.registry.register_bulk_actions(MockContactAction)

        self.assertEqual([MockAction], self.registry.instance_actions(CremeEntity))
        self.assertEqual([MockContactAction], self.registry.instance_actions(FakeContact))
        self.assertEqual([MockAction], self.registry.instance_actions(FakeOrganisation))
        self.assertEqual([MockAction], self.registry.bulk_actions(CremeEntity))
        self.assertEqual([MockContactAction], self.registry.bulk_actions(FakeContact))
        self.assertEqual([MockAction], self.registry.bulk_actions(FakeOrganisation))

    def test_actions(self):
        class MockA(MockOrganisationAction):
            action_id = 'test-a'

        class MockB(MockContactAction):
            action_id = 'test-b'

        class MockC(MockOrganisationAction):
            action_id = 'test-c'

        class MockD(MockContactAction):
            action_id = 'test-d'

        self.registry.register_instance_actions(MockA, MockB, MockC)
        self.registry.register_bulk_actions(MockB, MockC, MockD)

        self.assertSortedActions([MockB], self.registry.instance_actions(FakeContact))
        self.assertSortedActions([MockA, MockC], self.registry.instance_actions(FakeOrganisation))

        self.assertSortedActions([], self.registry.bulk_actions(CremeEntity))
        self.assertSortedActions([MockB, MockD], self.registry.bulk_actions(FakeContact))
        self.assertSortedActions([MockC], self.registry.bulk_actions(FakeOrganisation))

    def test_actions_override(self):
        class MockA(MockAction):
            action_id = 'test-a'

        class MockB(MockContactAction):
            action_id = 'test-b'

        class MockC(MockOrganisationAction):
            action_id = 'test-c'

        class MockAOverride(MockOrganisationAction):
            action_id = 'test-a'

        class MockD(MockContactAction):
            action_id = 'test-d'

        self.registry.register_instance_actions(MockA, MockB, MockC)
        self.registry.register_instance_actions(MockAOverride)

        self.registry.register_bulk_actions(MockA, MockD)
        self.registry.register_bulk_actions(MockAOverride)

        self.assertSortedActions([MockA], self.registry.instance_actions(CremeEntity))
        self.assertSortedActions([MockA, MockB], self.registry.instance_actions(FakeContact))
        self.assertSortedActions([MockAOverride, MockC],  self.registry.instance_actions(FakeOrganisation))

        self.assertEqual(MockA, self.registry.instance_action(CremeEntity, 'test-a'))
        self.assertEqual(MockA, self.registry.instance_action(FakeContact, 'test-a'))
        self.assertEqual(MockAOverride, self.registry.instance_action(FakeOrganisation, 'test-a'))

        self.assertSortedActions([MockA], self.registry.bulk_actions(CremeEntity))
        self.assertSortedActions([MockA, MockD], self.registry.bulk_actions(FakeContact))
        self.assertSortedActions([MockAOverride], self.registry.bulk_actions(FakeOrganisation))

        self.assertEqual(MockA, self.registry.bulk_action(CremeEntity, 'test-a'))
        self.assertEqual(MockA, self.registry.bulk_action(FakeContact, 'test-a'))
        self.assertEqual(MockAOverride, self.registry.bulk_action(FakeOrganisation, 'test-a'))

    def test_actions_void(self):
        class MockA(MockAction):
            action_id = 'test-a'

        class MockB(MockContactAction):
            action_id = 'test-b'

        class MockC(MockAction):
            action_id = 'test-c'

        self.registry.register_instance_actions(MockA, MockB, MockC)
        self.registry.void_instance_actions(FakeOrganisation, 'test-c')

        self.registry.register_bulk_actions(MockA, MockB, MockC)
        self.registry.void_bulk_actions(FakeOrganisation, 'test-a')

        self.assertSortedActions([MockA, MockC], self.registry.instance_actions(CremeEntity))
        self.assertSortedActions([MockA, MockB, MockC], self.registry.instance_actions(FakeContact))
        self.assertSortedActions([MockA], self.registry.instance_actions(FakeOrganisation))

        self.assertEqual(MockC, self.registry.instance_action(CremeEntity, 'test-c'))
        self.assertEqual(MockC, self.registry.instance_action(FakeContact, 'test-c'))
        self.assertEqual(None, self.registry.instance_action(FakeOrganisation, 'test-c'))

        self.assertSortedActions([MockA, MockC], self.registry.bulk_actions(CremeEntity))
        self.assertSortedActions([MockA, MockB, MockC], self.registry.bulk_actions(FakeContact))
        self.assertSortedActions([MockC], self.registry.bulk_actions(FakeOrganisation))

        self.assertEqual(MockA, self.registry.bulk_action(CremeEntity, 'test-a'))
        self.assertEqual(MockA, self.registry.bulk_action(FakeContact, 'test-a'))
        self.assertEqual(None, self.registry.bulk_action(FakeOrganisation, 'test-a'))

    def test_actions_duplicate_void(self):
        self.registry.register_instance_actions(MockContactAction)
        self.registry.register_bulk_actions(MockContactAction)

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.void_instance_actions(FakeContact, 'mock_action')

        self.assertEqual(str(e.exception),
                         "Unable to void action 'mock_action'. An action is already defined for model {}".format(FakeContact)
                        )

        with self.assertRaises(actions.ActionRegistrationError) as e:
            self.registry.void_bulk_actions(FakeContact, 'mock_action')

        self.assertEqual(str(e.exception),
                         "Unable to void action 'mock_action'. An action is already defined for model {}".format(FakeContact)
                        )


class BuiltinActionsTestCase(CremeTestCase):

    @classmethod
    def _create_role(cls, name, allowed_apps=(), admin_4_apps=(), set_creds=(), creates=(), users=()):
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

        cls.user = CremeUser(username='yui', email='kawa.yui@kimengumi.jp',
                             first_name='Yui', last_name='Kawa',
                            )

        cls.other_user = CremeUser(username='johndoe', email='john.doe@unknown.org',
                             first_name='John', last_name='Doe',
                            )

        cls.role = cls._create_role(
            'Action view only', ['creme_core'],
            users=[cls.user, cls.other_user],  # 'persons'
            set_creds=[
                (EntityCredentials._ALL_CREDS, SetCredentials.ESET_OWN),
            ],
            creates=[FakeContact]
        )

        cls.contact = FakeContact.objects.create(last_name='A', user=cls.user)
        cls.contact_other = FakeContact.objects.create(last_name='B', user=cls.other_user)

    def assertAction(self, entry, model, action_id, action, url, **kwargs):
        self.assertEqual(entry.model, model)
        self.assertEqual(entry.action_id, action_id)
        self.assertEqual(entry.action, action)
        self.assertEqual(entry.url, url)

        for key, expected in kwargs.items():
            value = getattr(entry, key)
            self.assertEqual(value, expected, 'action.{}'.format(key))

    def test_edit_action(self):
        self.assertAction(actions.EditActionEntry(self.user, FakeContact, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-edit',
            action='redirect',
            url=self.contact.get_edit_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Edit'),
            icon='edit',
        )

        self.assertAction(actions.EditActionEntry(self.user, FakeContact, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-edit',
            action='redirect',
            url=self.contact_other.get_edit_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Edit'),
            icon='edit',
        )

    def test_delete_action(self):
        self.assertAction(actions.DeleteActionEntry(self.user, FakeContact, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-delete',
            action='delete',
            url=self.contact.get_delete_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Delete'),
            icon='delete',
        )

        self.assertAction(actions.DeleteActionEntry(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-delete',
            action='delete',
            url=self.contact_other.get_delete_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Delete'),
            icon='delete',
        )

    def test_view_action(self):
        self.assertAction(actions.ViewActionEntry(self.user, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-view',
            action='redirect',
            url=self.contact.get_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=True,
            label=_('See'),
            icon='view',
            help_text=gettext('Go to the entity {entity}').format(entity=self.contact)
        )

        self.assertAction(actions.ViewActionEntry(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-view',
            action='redirect',
            url=self.contact_other.get_absolute_url(),
            is_enabled=False,    # other users can view entity
            is_visible=True,
            is_default=True,
            label=_('See'),
            icon='view',
            help_text=gettext('Go to the entity {entity}').format(entity=self.contact_other)
        )

    def test_clone_action(self):
        self.assertTrue(self.user.has_perm_to_create(self.contact))
        self.assertTrue(self.user.has_perm_to_view(self.contact))

        self.assertAction(actions.CloneActionEntry(self.user, instance=self.contact),
            model=FakeContact,
            action_id='creme_core-clone',
            action='clone',
            url=self.contact.get_clone_absolute_url(),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Clone'),
            icon='clone',
            action_data={
                'options': {},
                'data': {
                    'id': self.contact.id
                }
            }
        )

        self.assertTrue(self.user.has_perm_to_create(self.contact_other))
        self.assertFalse(self.user.has_perm_to_view(self.contact_other))

        self.assertAction(actions.CloneActionEntry(self.user, instance=self.contact_other),
            model=FakeContact,
            action_id='creme_core-clone',
            action='clone',
            url=self.contact_other.get_clone_absolute_url(),
            is_enabled=False,
            is_visible=True,
            is_default=False,
            label=_('Clone'),
            icon='clone',
            action_data={
                'options': {},
                'data': {
                    'id': self.contact_other.id
                }
            }
        )

    def test_bulk_edit_action(self):
        self.assertAction(actions.BulkEditActionEntry(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_edit',
            action='edit-selection',
            url=reverse('creme_core__bulk_update', args=(ContentType.objects.get_for_model(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple update'),
            icon='edit'
        )

        self.assertAction(actions.BulkEditActionEntry(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_edit',
            action='edit-selection',
            url=reverse('creme_core__bulk_update', args=(ContentType.objects.get_for_model(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple update'),
            icon='edit'
        )

    def test_bulk_delete_action(self):
        self.assertAction(actions.BulkDeleteActionEntry(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_delete',
            action='delete-selection',
            url=reverse('creme_core__delete_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple deletion'),
            icon='delete'
        )

        self.assertAction(actions.BulkDeleteActionEntry(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_delete',
            action='delete-selection',
            url=reverse('creme_core__delete_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple deletion'),
            icon='delete'
        )

    def test_bulk_add_property_action(self):
        self.assertAction(actions.BulkAddPropertyActionEntry(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_add_property',
            action='addto-selection',
            url=reverse('creme_core__add_properties_bulk', args=(ContentType.objects.get_for_model(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple property adding'),
            icon='property'
        )

        self.assertAction(actions.BulkAddPropertyActionEntry(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_add_property',
            action='addto-selection',
            url=reverse('creme_core__add_properties_bulk', args=(ContentType.objects.get_for_model(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple property adding'),
            icon='property'
        )

    def test_bulk_add_relation_action(self):
        self.assertAction(actions.BulkAddRelationActionEntry(self.user),
            model=CremeEntity,
            action_id='creme_core-bulk_add_relation',
            action='addto-selection',
            url=reverse('creme_core__create_relations_bulk', args=(ContentType.objects.get_for_model(CremeEntity).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple relationship adding'),
            icon='relations'
        )

        self.assertAction(actions.BulkAddRelationActionEntry(self.user, model=FakeContact),
            model=FakeContact,
            action_id='creme_core-bulk_add_relation',
            action='addto-selection',
            url=reverse('creme_core__create_relations_bulk', args=(ContentType.objects.get_for_model(FakeContact).id,)),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Multiple relationship adding'),
            icon='relations'
        )

    def test_merge_action(self):
        self.assertFalse(ctype_can_be_merged(ContentType.objects.get_for_model(CremeEntity)))
        self.assertTrue(ctype_can_be_merged(ContentType.objects.get_for_model(FakeContact)))

        self.assertAction(actions.MergeActionEntry(self.user),
            model=CremeEntity,
            ctype=ContentType.objects.get_for_model(CremeEntity),
            action_id='creme_core-merge',
            action='merge-selection',
            url=reverse('creme_core__merge_entities'),
            is_enabled=False,
            is_visible=False,
            is_default=False,
            label=_('Merge 2 entities'),
            icon='merge'
        )

        self.assertAction(actions.MergeActionEntry(self.user, model=FakeContact),
            model=FakeContact,
            ctype=ContentType.objects.get_for_model(FakeContact),
            action_id='creme_core-merge',
            action='merge-selection',
            url=reverse('creme_core__merge_entities'),
            is_enabled=True,
            is_visible=True,
            is_default=False,
            label=_('Merge 2 entities'),
            icon='merge'
        )
