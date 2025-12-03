from collections import defaultdict
from functools import partial
from io import StringIO
from json import dumps as json_dump
from uuid import uuid4

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_config.core.importers import Importer, ImportersRegistry
from creme.creme_core import bricks, constants
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellFunctionField,
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
    operands,
    operators,
)
from creme.creme_core.core.entity_filter.condition_handler import (
    CustomFieldConditionHandler,
    DateCustomFieldConditionHandler,
    DateRegularFieldConditionHandler,
    PropertyConditionHandler,
    RegularFieldConditionHandler,
    RelationConditionHandler,
    RelationSubFilterConditionHandler,
    SubFilterConditionHandler,
)
from creme.creme_core.forms import (
    LAYOUT_DUAL_FIRST,
    LAYOUT_DUAL_SECOND,
    LAYOUT_REGULAR,
)
from creme.creme_core.function_fields import PropertiesField
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.custom_form import (
    EntityCellCustomFormExtra,
    EntityCellCustomFormSpecial,
)
from creme.creme_core.gui.menu import ContainerEntry, Separator1Entry
# RecentEntitiesEntry
from creme.creme_core.menu import CremeEntry, QuickAccessEntry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    ButtonMenuItem,
    CremeEntity,
    CremePropertyType,
    CustomBrickConfigItem,
    CustomField,
    CustomFormConfigItem,
    EntityFilter,
    EntityFilterCondition,
    FakeActivity,
    FakeContact,
    FakeDocument,
    FakeOrganisation,
    FieldsConfig,
    HeaderFilter,
    InstanceBrickConfigItem,
    MenuConfigItem,
    NotificationChannel,
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
    SetCredentials,
    UserRole,
)
from creme.creme_core.tests import fake_custom_forms
from creme.creme_core.tests.fake_constants import DEFAULT_HFILTER_FAKE_CONTACT
from creme.creme_core.tests.fake_forms import FakeAddressGroup
from creme.creme_core.tests.fake_menu import (
    FakeContactsEntry,
    FakeOrganisationsEntry,
)

from .base import TransferBaseTestCase, TransferInstanceBrick


class ImportingTestCase(TransferBaseTestCase):
    URL = reverse('creme_config__transfer_import')

    def test_creds(self):
        "Not staff."
        self.login_as_root()
        self.assertGET403(self.URL)

    def test_register01(self):
        registry = ImportersRegistry()
        data_id1 = 'imp1'
        data_id2 = 'imp2'

        @registry.register(data_id=data_id1)
        class TestImporter01(Importer):
            pass

        @registry.register(data_id=data_id2)
        class TestImporter02(Importer):
            pass

        importers = registry.build_importers()
        self.assertEqual(2, len(importers))

        importer1 = importers[0]
        self.assertIsInstance(importer1, TestImporter01)
        self.assertEqual(data_id1, importer1.data_id)

        importer2 = importers[1]
        self.assertIsInstance(importer2, TestImporter02)
        self.assertEqual(data_id2, importer2.data_id)

    def test_register02(self):
        "Collision."
        registry = ImportersRegistry()
        data_id = 'my_importer'

        @registry.register(data_id=data_id)
        class TestImporter01(Importer):
            pass

        with self.assertRaises(ImportersRegistry.Collision):
            @registry.register(data_id=data_id)
            class TestImporter02(Importer):
                pass

    def test_register03(self):
        "Priority (stronger after)."
        registry = ImportersRegistry()
        data_id = 'my_importer'

        @registry.register(data_id=data_id)
        class TestImporter01(Importer):
            pass

        with self.assertNoException():
            @registry.register(data_id=data_id, priority=2)
            class TestImporter02(Importer):
                pass

        importer = self.get_alone_element(registry.build_importers())
        self.assertIsInstance(importer, TestImporter02)

    def test_register04(self):
        "Priority (stronger before)."
        registry = ImportersRegistry()
        data_id = 'my_importer'

        @registry.register(data_id=data_id, priority=3)
        class TestImporter01(Importer):
            pass

        with self.assertNoException():
            @registry.register(data_id=data_id, priority=2)
            class TestImporter02(Importer):
                pass

        importer = self.get_alone_element(registry.build_importers())
        self.assertIsInstance(importer, TestImporter01)

    def test_unregister01(self):
        registry = ImportersRegistry()
        data_id1 = 'imp1'
        data_id2 = 'imp2'

        @registry.register(data_id=data_id1)
        class TestImporter01(Importer):
            pass

        @registry.register(data_id=data_id2)
        class TestImporter02(Importer):
            pass

        registry.unregister(data_id1)

        importer = self.get_alone_element(registry.build_importers())
        self.assertIsInstance(importer, TestImporter02)

    def test_unregister02(self):
        "Un-register before."
        registry = ImportersRegistry()
        data_id1 = 'imp1'
        data_id2 = 'imp2'

        registry.unregister(data_id1)

        @registry.register(data_id=data_id1)
        class TestImporter01(Importer):
            pass

        @registry.register(data_id=data_id2)
        class TestImporter02(Importer):
            pass

        importer = self.get_alone_element(registry.build_importers())
        self.assertIsInstance(importer, TestImporter02)

    def test_dependencies(self):
        registry = ImportersRegistry()
        data_id1 = 'imp1'
        data_id2 = 'imp2'
        data_id3 = 'imp3'

        @registry.register(data_id=data_id1)
        class TestImporter01(Importer):
            dependencies = [data_id3]

        @registry.register(data_id=data_id2)
        class TestImporter02(Importer):
            pass

        @registry.register(data_id=data_id3)
        class TestImporter03(Importer):
            pass

        importers = registry.build_importers()
        self.assertIsInstance(importers[0], TestImporter02)
        self.assertIsInstance(importers[1], TestImporter03)
        self.assertIsInstance(importers[2], TestImporter01)

    def test_error01(self):
        "Invalid JSON."
        self.login_as_super(is_staff=True)

        json_file = StringIO("{'roles': [")
        json_file.name = 'config-23-10-2017.csv'  # Django uses this

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config', errors=_('File content is not valid JSON.'),
        )

    def test_error02(self):
        "Invalid data."
        self.login_as_super(is_staff=True)

        json_file = StringIO(json_dump([]))
        json_file.name = 'config-23-10-2017.csv'  # Django uses this

        response1 = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            response1.context['form'],
            field='config',
            errors=_('File content is not valid (%(error)s).') % {
                'error': _('main content must be a dictionary'),
            },
        )

        # ---
        json_file = StringIO(json_dump({'roles': 1}))  # 'roles' is not a list
        json_file.name = 'config-23-10-2017.csv'  # Django uses this

        response2 = self.assertPOST200(self.URL, data={'config': json_file})

        with self.assertNoException():
            errors = response2.context['form'].errors

        self.assertIn('config', errors)

    def test_error03(self):
        "Bad version."
        self.login_as_super(is_staff=True)

        json_file = StringIO(json_dump({'version': '2.0', 'roles': []}))
        json_file.name = 'config-23-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config', errors=_('The file has an unsupported version.'),
        )

    def test_roles01(self):
        self.login_as_super(is_staff=True)

        self.assertGET200(self.URL)

        uid = str(uuid4())
        name = 'Role#1'
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': uid,
                'name': name,

                'allowed_apps': ['persons', 'documents'],
                'admin_4_apps': ['persons'],

                'creatable_ctypes':  ['creme_core.fakecontact', 'creme_core.fakeorganisation'],
                'exportable_ctypes': ['creme_core.fakecontact'],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.LINK
                        ),
                        'type':  SetCredentials.ESET_OWN,
                    }, {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                        'ctype': 'creme_core.fakecontact',
                        'forbidden': False,
                    }, {
                        'value': EntityCredentials.CHANGE,
                        'type': SetCredentials.ESET_OWN,
                        'ctype': 'creme_core.fakeorganisation',
                        'forbidden': True,
                    },
                ],
            }],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-03-03-2020.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, uuid=uid)
        self.assertEqual(name, role.name)
        self.assertSetEqual({'persons', 'documents'}, role.allowed_apps)
        self.assertSetEqual({'persons'},              role.admin_4_apps)

        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct    = get_ct(FakeOrganisation)
        self.assertCountEqual([contact_ct, orga_ct], role.creatable_ctypes.all())
        self.assertCountEqual([contact_ct],          role.exportable_ctypes.all())

        credentials = [*role.credentials.all()]
        self.assertEqual(3, len(credentials))

        # --
        own_creds = self.get_alone_element(
            sc
            for sc in credentials
            if sc.set_type == SetCredentials.ESET_OWN and not sc.forbidden
        )
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.LINK,
            own_creds.value,
        )
        self.assertFalse(own_creds.ctype)

        # --
        all_creds = self.get_alone_element(
            sc for sc in credentials if sc.set_type == SetCredentials.ESET_ALL
        )
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            all_creds.value
        )
        self.assertEqual(contact_ct, all_creds.ctype)
        self.assertFalse(all_creds.forbidden)

        # --
        forbidden_creds = self.get_alone_element(sc for sc in credentials if sc.forbidden)
        self.assertEqual(SetCredentials.ESET_OWN,  forbidden_creds.set_type)
        self.assertEqual(EntityCredentials.CHANGE, forbidden_creds.value)
        self.assertEqual(orga_ct,                  forbidden_creds.ctype)

    def test_roles02(self):
        "Role with same name already exists => override it."
        self.login_as_super(is_staff=True)

        role = self.create_role(
            name='Superhero',
            allowed_apps=['creme_core', 'persons'],
            admin_4_apps=['persons'],
            creatable_models=[FakeContact],
            exportable_models=[FakeContact],
        )
        self.add_credentials(role, own=['VIEW', 'CHANGE', 'LINK'], model=FakeContact)

        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': str(role.uuid),
                'name': role.name,

                'allowed_apps': ['persons', 'documents'],
                'admin_4_apps': ['documents'],

                'creatable_ctypes':  ['creme_core.fakecontact', 'creme_core.fakeorganisation'],
                'exportable_ctypes': ['creme_core.fakeorganisation'],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                    },
                ]
            }],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-24-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        role = self.get_object_or_fail(UserRole, uuid=role.uuid)
        self.assertSetEqual({'persons', 'documents'}, role.allowed_apps)
        self.assertSetEqual({'documents'},            role.admin_4_apps)

        get_ct = ContentType.objects.get_for_model
        orga_ct = get_ct(FakeOrganisation)
        self.assertCountEqual([get_ct(FakeContact), orga_ct], role.creatable_ctypes.all())
        self.assertCountEqual([orga_ct],                      role.exportable_ctypes.all())

        credentials = self.get_alone_element(role.credentials.all())
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE,
            credentials.value,
        )
        self.assertEqual(SetCredentials.ESET_ALL, credentials.set_type)
        self.assertFalse(credentials.ctype)

    def test_roles03(self):
        "Credentials with filter."
        self.login_as_super(is_staff=True)
        ct_str_c = 'creme_core.fakecontact'

        rtype_id = 'creme_config-subject_test_import_roles03'

        efilter_id = 'creme_config-test_import_roles03'
        efilter_name = 'Lovers'

        role_uuid = str(uuid4())
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': role_uuid,
                'name': 'Lover users',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes': ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [{
                    'value': EntityCredentials.VIEW | EntityCredentials.CHANGE,
                    'type': SetCredentials.ESET_FILTER,
                    'ctype': ct_str_c,
                    'efilter': efilter_id,
                }],
            }],
            'entity_filters': [{
                'id':   efilter_id,
                'name': efilter_name,

                'ctype': ct_str_c,

                'filter_type': EF_CREDENTIALS,

                'conditions': [{
                    'type':  RelationConditionHandler.type_id,
                    'name':  rtype_id,
                    'value': {'has': True},
                }],
            }],
            'relation_types': [{
                'id': rtype_id,
                'predicate': 'loves',
                'is_copiable': True, 'minimal_display': False,

                'symmetric': {
                    'predicate': 'is loved by',
                    'is_copiable': True, 'minimal_display': False,
                },
            }],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-03-03-2020.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)

        # ---
        efilter = self.get_object_or_fail(EntityFilter, id=efilter_id)
        self.assertEqual(EF_CREDENTIALS, efilter.filter_type)
        self.assertEqual(efilter_name, efilter.name)
        self.assertTrue(efilter.is_custom)
        self.assertEqual(ct_contact, efilter.entity_type)
        self.assertIsNone(efilter.user)
        self.assertFalse(efilter.is_private)

        condition = self.get_alone_element(efilter.conditions.all())
        self.assertEqual(RelationConditionHandler.type_id, condition.type)
        self.assertEqual(rtype_id, condition.name)

        # ---
        role = self.get_object_or_fail(UserRole, uuid=role_uuid)

        credentials = self.get_alone_element(role.credentials.all())
        self.assertEqual(
            EntityCredentials.VIEW | EntityCredentials.CHANGE,
            credentials.value,
        )
        self.assertEqual(SetCredentials.ESET_FILTER, credentials.set_type)
        self.assertEqual(ct_contact, credentials.ctype)
        self.assertEqual(efilter, credentials.efilter)

    def test_roles_error(self):
        "Invalid filter."
        self.login_as_super(is_staff=True)
        efilter_id = 'creme_config-test_import_role_error'
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': str(uuid4()),
                'name': 'Lover users',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes': ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [{
                    'value': EntityCredentials.VIEW,
                    'type': SetCredentials.ESET_FILTER,
                    'ctype': 'creme_core.fakecontact',
                    'efilter': efilter_id,
                }],
            }],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-03-03-2020.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This filter PK is invalid: «{}».').format(efilter_id),
        )

    def test_menu(self):
        self.login_as_super(is_staff=True)
        role1 = self.create_role(name='Test')

        role_uid2 = str(uuid4())

        container_label1 = 'My entries'
        container_label2 = 'My super entries'
        container_label3 = 'My role entries #1'
        container_label4 = 'My role entries #2'

        sep_label = 'Misc'
        menu_data = [
            # Default
            {
                'order': 1,
                'id': ContainerEntry.id,
                'data': {'label': container_label1},
                'children': [
                    {
                        'order': 1,
                        'id': FakeContactsEntry.id,
                    },
                    {
                        'order': 20,
                        'id': Separator1Entry.id,
                        'data': {'label': sep_label},
                    },
                ],
            }, {
                'order': 3,
                'id': CremeEntry.id,
            },

            # Superuser
            {
                'order': 1,
                'id': CremeEntry.id,
                'superuser': True,
            }, {
                'order': 2,
                'id': ContainerEntry.id,
                'superuser': True,
                'data': {'label': container_label2},
                'children': [
                    {'order': 1, 'id': FakeContactsEntry.id},
                ],
            },

            # Existing Role
            {
                'order': 1,
                # 'id': RecentEntitiesEntry.id,
                'id': QuickAccessEntry.id,
                'role': str(role1.uuid),
            }, {
                'order': 2,
                'id': ContainerEntry.id,
                'role': str(role1.uuid),
                'data': {'label': container_label3},
                'children': [
                    {'order': 1, 'id': FakeContactsEntry.id},
                ],
            },

            # New Role
            {
                'order': 2,
                # 'id': RecentEntitiesEntry.id,
                'id': QuickAccessEntry.id,
                'role': role_uid2,
            }, {
                'order': 3,
                'id': ContainerEntry.id,
                'role': role_uid2,
                'data': {'label': container_label4},
                'children': [
                    {'order': 1, 'id': FakeOrganisationsEntry.id},
                ],
            },
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'menu': menu_data,
            'roles': [{
                'uuid': role_uid2,
                'name': 'Super-hero',
                'allowed_apps': ['persons'],
                'creatable_ctypes': ['creme_core.fakecontact'],

                'credentials': [
                    {'value': EntityCredentials.VIEW, 'type': SetCredentials.ESET_ALL},
                ],
            }],
        }))
        json_file.name = 'config-26-04-2021.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        # ---
        default_items = MenuConfigItem.objects.filter(parent=None, superuser=False, role=None)
        self.assertEqual(2, len(default_items))

        default_item1 = default_items[0]
        self.assertEqual(ContainerEntry.id, default_item1.entry_id)
        self.assertEqual(1,                 default_item1.order)
        self.assertDictEqual({'label': container_label1}, default_item1.entry_data)

        default_children = default_item1.children.all()
        self.assertEqual(2, len(default_children))

        default_child1 = default_children[0]
        self.assertEqual(FakeContactsEntry.id, default_child1.entry_id)
        self.assertEqual(1, default_child1.order)
        self.assertFalse(default_child1.superuser)
        self.assertIsNone(default_child1.role)
        self.assertDictEqual({}, default_child1.entry_data)

        default_child2 = default_children[1]
        self.assertEqual(Separator1Entry.id, default_child2.entry_id)
        self.assertEqual(20,                 default_child2.order)
        self.assertDictEqual({'label': sep_label}, default_child2.entry_data)

        default_item2 = default_items[1]
        self.assertEqual(CremeEntry.id, default_item2.entry_id)
        self.assertEqual(3,             default_item2.order)
        self.assertDictEqual({}, default_item2.entry_data)

        # ---
        super_items = MenuConfigItem.objects.filter(parent=None, superuser=True)
        self.assertEqual(2, len(super_items))

        super_item1 = super_items[0]
        self.assertEqual(CremeEntry.id, super_item1.entry_id)
        self.assertEqual(1,             super_item1.order)
        self.assertDictEqual({}, super_item1.entry_data)

        super_item2 = super_items[1]
        self.assertEqual(ContainerEntry.id, super_item2.entry_id)
        self.assertEqual(2,                 super_item2.order)
        self.assertDictEqual({'label': container_label2}, super_item2.entry_data)

        super_child1 = self.get_alone_element(super_item2.children.all())
        self.assertEqual(FakeContactsEntry.id, super_child1.entry_id)
        self.assertEqual(1,                    super_child1.order)
        self.assertTrue(super_child1.superuser)
        self.assertIsNone(super_child1.role)
        self.assertDictEqual({}, super_child1.entry_data)

        # ---
        role1_items = MenuConfigItem.objects.filter(parent=None, role=role1)
        self.assertEqual(2, len(role1_items))

        # self.assertEqual(RecentEntitiesEntry.id, role1_items[0].entry_id)
        self.assertEqual(QuickAccessEntry.id, role1_items[0].entry_id)

        role1_item2 = role1_items[1]
        self.assertEqual(ContainerEntry.id, role1_item2.entry_id)

        role1_child1 = self.get_alone_element(role1_item2.children.all())
        self.assertEqual(FakeContactsEntry.id, role1_child1.entry_id)
        self.assertFalse(role1_child1.superuser)
        self.assertEqual(role1, role1_child1.role)

        # ---
        role2 = UserRole.objects.get(uuid=role_uid2)

        role2_items = MenuConfigItem.objects.filter(parent=None, role=role2)
        self.assertEqual(2, len(role2_items))

        # self.assertEqual(RecentEntitiesEntry.id, role2_items[0].entry_id)
        self.assertEqual(QuickAccessEntry.id, role2_items[0].entry_id)

        role2_item2 = role2_items[1]
        self.assertEqual(ContainerEntry.id, role2_item2.entry_id)

        role2_child1 = self.get_alone_element(role2_item2.children.all())
        self.assertEqual(FakeOrganisationsEntry.id, role2_child1.entry_id)
        self.assertFalse(role2_child1.superuser)
        self.assertEqual(role2, role2_child1.role)

    def test_buttons01(self):
        self.login_as_super(is_staff=True)

        role = self.create_role(name='Test')
        role_uuid = str(role.uuid)

        contact_ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=contact_ct))

        def gen_bid(i):
            return Button.generate_id('creme_config_export', f'test_import_buttons{i}')

        create_bmi = partial(ButtonMenuItem.objects.create, content_type=contact_ct)
        create_bmi(order=1, button_id=gen_bid(1))
        create_bmi(order=2, button_id=gen_bid(2))

        orga_bmi = create_bmi(
            order=1, button_id=gen_bid(3), content_type=FakeOrganisation,
        )

        ct_str = 'creme_core.fakecontact'
        buttons_data = [
            {'order': 1, 'button_id': gen_bid(3)},
            {'order': 2, 'button_id': gen_bid(4)},

            {'order': 1, 'button_id': gen_bid(5), 'ctype': ct_str},
            {'order': 2, 'button_id': gen_bid(6), 'ctype': ct_str},

            {'order': 1, 'button_id': gen_bid(7), 'superuser': True},
            {'order': 2, 'button_id': gen_bid(8), 'superuser': True},

            {'order': 1, 'button_id': gen_bid(9),  'superuser': True, 'ctype': ct_str},
            {'order': 2, 'button_id': gen_bid(10), 'superuser': True, 'ctype': ct_str},

            {'order': 1, 'button_id': gen_bid(11), 'role': role_uuid},
            {'order': 2, 'button_id': gen_bid(12), 'role': role_uuid},

            {'order': 1, 'button_id': gen_bid(13), 'role': role_uuid, 'ctype': ct_str},
            {'order': 2, 'button_id': gen_bid(14), 'role': role_uuid, 'ctype': ct_str},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'buttons': buttons_data}))
        json_file.name = 'config-25-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            [buttons_data[0], buttons_data[1]],
            [
                {'order': bmi.order, 'button_id': bmi.button_id}
                for bmi in ButtonMenuItem.objects.filter(
                    content_type=None, superuser=False, role=None,
                )
            ],
        )
        self.assertListEqual(
            [buttons_data[2], buttons_data[3]],
            [
                {'order': bmi.order, 'button_id': bmi.button_id, 'ctype': ct_str}
                for bmi in ButtonMenuItem.objects.filter(
                    content_type=contact_ct, superuser=False, role=None,
                )
            ],
        )
        self.assertListEqual(
            [buttons_data[4], buttons_data[5]],
            [
                {'order': bmi.order, 'button_id': bmi.button_id, 'superuser': True}
                for bmi in ButtonMenuItem.objects.filter(
                    content_type=None, superuser=True, role=None,
                )
            ],
        )
        self.assertListEqual(
            [buttons_data[6], buttons_data[7]],
            [
                {
                    'order': bmi.order, 'button_id': bmi.button_id,
                    'superuser': True, 'ctype': ct_str,
                } for bmi in ButtonMenuItem.objects.filter(
                    content_type=contact_ct, superuser=True, role=None,
                )
            ],
        )
        self.assertListEqual(
            [buttons_data[8], buttons_data[9]],
            [
                {'order': bmi.order, 'button_id': bmi.button_id, 'role': role_uuid}
                for bmi in ButtonMenuItem.objects.filter(
                    content_type=None, superuser=False, role=role,
                )
            ],
        )
        self.assertListEqual(
            [buttons_data[10], buttons_data[11]],
            [
                {
                    'order': bmi.order, 'button_id': bmi.button_id,
                    'role': role_uuid, 'ctype': ct_str,
                } for bmi in ButtonMenuItem.objects.filter(
                    content_type=contact_ct, superuser=False, role=role,
                )
            ],
        )
        self.assertDoesNotExist(orga_bmi)

    def test_buttons02(self):
        self.login_as_super(is_staff=True)

        def gen_bid(i):
            return Button.generate_id('creme_config_export', f'test_import_buttons{i}')

        role_uuid = str(uuid4())
        buttons_data = [
            {'order': 1, 'button_id': gen_bid(1)},
            {'order': 2, 'button_id': gen_bid(2)},

            {'order': 1, 'button_id': gen_bid(3), 'role': role_uuid},
            {'order': 2, 'button_id': gen_bid(4), 'role': role_uuid},
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'buttons': buttons_data,
            'roles': [{
                'uuid': role_uuid,
                'name': 'Super-hero',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes': ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type': SetCredentials.ESET_ALL,
                    },
                ],
            }],
        }))
        json_file.name = 'config-12-09-2024.csv'

        self.assertNoFormError(self.client.post(self.URL, data={'config': json_file}))
        self.assertListEqual(
            [buttons_data[2], buttons_data[3]],
            [
                {'order': bmi.order, 'button_id': bmi.button_id, 'role': role_uuid}
                for bmi in ButtonMenuItem.objects.filter(
                    content_type=None, superuser=False, role__uuid=role_uuid,
                )
            ],
        )

    def test_search01(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')  # TODO: in setupClass?

        cf_uuid = '6a52b4db-f838-489f-b6df-d1558b3938e5'
        search_data = [
            {
                'ctype': 'creme_core.fakecontact',
                'cells': [
                    {'type': 'regular_field', 'value': 'first_name'},
                    {'type': 'regular_field', 'value': 'last_name'},
                    {'type': 'custom_field',  'value': cf_uuid},
                ],
            }, {
                'ctype': 'creme_core.fakeorganisation',
                'role': str(role.uuid),
                'cells': [{'type': 'regular_field', 'value': 'name'}],
            }, {
                'ctype': 'creme_core.fakedocument',
                'superuser': True,
                'cells': [{'type': 'regular_field', 'value': 'title'}],
            }, {
                'ctype': 'creme_core.fakeactivity',
                'disabled': True,
                'cells': [],
            },
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'search': search_data,
            'custom_fields': [
                {
                    'uuid': cf_uuid, 'ctype': 'creme_core.fakecontact',
                    'name': 'Rating', 'type': CustomField.INT,
                },
            ],
        }))
        json_file.name = 'config-25-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        cfield = self.get_object_or_fail(CustomField, uuid=cf_uuid)

        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        sci1 = self.get_object_or_fail(
            SearchConfigItem, content_type=contact_ct, role=None, superuser=False,
        )
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellCustomField(cfield),
            ],
            [*sci1.cells],
        )

        self.get_object_or_fail(
            SearchConfigItem, content_type=get_ct(FakeOrganisation), role=role,
        )
        self.get_object_or_fail(
            SearchConfigItem, content_type=get_ct(FakeDocument), superuser=True,
        )
        self.get_object_or_fail(
            SearchConfigItem, content_type=get_ct(FakeActivity), disabled=True,
        )

    def test_search02(self):
        "Related role is imported."
        self.login_as_super(is_staff=True)

        role_uuid = str(uuid4())
        role_name = 'Super-hero'
        search_data = [
            {
                'ctype': 'creme_core.fakecontact',
                'role': role_uuid,
                'cells': [
                    {'type': 'regular_field', 'value': 'last_name'},
                    {'type': 'regular_field', 'value': 'description'},
                ],
            },
        ]
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': role_uuid,
                'name': role_name,

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes':  ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                    },
                ],
            }],
            'search': search_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-30-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        sci = self.get_object_or_fail(
            SearchConfigItem,
            content_type=ContentType.objects.get_for_model(FakeContact),
            role__uuid=role_uuid, superuser=False,
        )
        self.assertListEqual(
            ['last_name', 'description'],
            [cell.value for cell in sci.cells],
        )

    def test_property_types01(self):
        self.login_as_super(is_staff=True)

        def uid():
            return str(uuid4())

        ptype3_data = {'uuid': uid(), 'text': 'Is cool', 'is_copiable': True}
        ptypes_data = [
            {'uuid': uid(), 'text': 'Is important', 'is_copiable': True},
            {'uuid': uid(), 'text': 'Is funny',     'is_copiable': False},
            {
                **ptype3_data,
                'subject_ctypes': ['creme_core.fakecontact', 'creme_core.fakeorganisation'],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'property_types': ptypes_data}))
        json_file.name = 'config-25-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        ptype1 = self.get_object_or_fail(CremePropertyType, **ptypes_data[0])
        self.assertFalse(ptype1.subject_ctypes.all())

        self.get_object_or_fail(CremePropertyType, **ptypes_data[1])

        ptype3 = self.get_object_or_fail(CremePropertyType, **ptype3_data)
        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*ptype3.subject_models],
        )

    def test_property_types02(self):
        "Uniqueness of text."
        self.login_as_super(is_staff=True)

        uid = str(uuid4())

        ptypes_data = [
            {'uuid': uid, 'text': 'Is important', 'is_copiable': True},
            {'uuid': uid, 'text': 'Is funny', 'is_copiable': False},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'property_types': ptypes_data}))
        json_file.name = 'config-25-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.get_object_or_fail(CremePropertyType, **ptypes_data[1])

    def test_property_types03(self):
        "Do no override a not custom ptype."
        self.login_as_super(is_staff=True)

        ptype = CremePropertyType.objects.create(text='Sugoi!')

        ptypes_data = [{'uuid': str(ptype.uuid), 'text': 'Is important', 'is_copiable': True}]
        json_file = StringIO(json_dump({'version': self.VERSION, 'property_types': ptypes_data}))
        json_file.name = 'config-25-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This property type cannot be overridden: «{}».').format(ptype),
        )

    def test_relations_types01(self):
        self.login_as_super(is_staff=True)

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Is very important')
        ptype2 = create_ptype(text='Is important', is_custom=True)
        ptype3 = create_ptype(text='Is hot',       is_custom=True)
        ptype4 = create_ptype(text='Is bad',       is_custom=True)
        ptype5 = create_ptype(text='Is nasty',     is_custom=True)

        pk_fmt = 'creme_config-subject_test_import_relations_types01_{}'.format
        pk1a = pk_fmt(1)
        pk2a = pk_fmt(2)

        rtypes_data = [
            {
                'id':          pk1a, 'predicate':       'loves',
                'is_copiable': True, 'minimal_display': False,

                'subject_properties': [str(ptype1.uuid), str(ptype2.uuid)],
                'object_properties': [str(ptype3.uuid)],

                'subject_forbidden_properties': [str(ptype4.uuid)],
                'object_forbidden_properties': [str(ptype5.uuid)],

                'symmetric': {
                    'predicate': 'is loved by', 'is_copiable': False,
                    'minimal_display': True,
                },
            }, {
                'id':          pk2a, 'predicate':        'likes',
                'is_copiable': False, 'minimal_display': True,

                'subject_ctypes': ['creme_core.fakecontact', 'creme_core.fakeorganisation'],
                'object_ctypes':  ['creme_core.fakedocument'],

                'symmetric': {
                    'predicate': 'is liked by', 'is_copiable': True,
                    'minimal_display': False,
                },
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'relation_types': rtypes_data}))
        json_file.name = 'config-26-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        # ---
        rtype_data = rtypes_data[0]
        rtype1 = self.get_object_or_fail(
            RelationType,
            is_custom=True, id=rtype_data['id'], predicate=rtype_data['predicate'],
        )
        self.assertTrue(rtype1.is_copiable)
        self.assertFalse(rtype1.minimal_display)
        self.assertFalse(rtype1.subject_ctypes.all())
        self.assertFalse(rtype1.object_ctypes.all())
        self.assertCountEqual([ptype1, ptype2], [*rtype1.subject_properties.all()])
        self.assertListEqual([ptype3],          [*rtype1.object_properties.all()])
        self.assertListEqual([ptype4],          [*rtype1.subject_forbidden_properties.all()])
        self.assertListEqual([ptype5],          [*rtype1.object_forbidden_properties.all()])

        sym_rtype_data = rtype_data['symmetric']
        sym_rtype1 = rtype1.symmetric_type
        self.assertEqual('creme_config-object_test_import_relations_types01_1', sym_rtype1.id)
        self.assertEqual(sym_rtype_data['predicate'], sym_rtype1.predicate)
        self.assertFalse(sym_rtype1.is_copiable)
        self.assertTrue(sym_rtype1.minimal_display)

        # ---
        rtype_data = rtypes_data[1]
        rtype2 = self.get_object_or_fail(
            RelationType,
            is_custom=True, id=rtype_data['id'], predicate=rtype_data['predicate'],
        )
        self.assertFalse(rtype2.is_copiable)
        self.assertTrue(rtype2.minimal_display)
        self.assertFalse(rtype2.subject_properties.all())
        self.assertFalse(rtype2.object_properties.all())
        self.assertFalse(rtype2.subject_forbidden_properties.all())
        self.assertFalse(rtype2.object_forbidden_properties.all())
        self.assertCountEqual(
            [FakeContact, FakeOrganisation], [*rtype2.subject_models],
        )
        self.assertListEqual([FakeDocument], [*rtype2.object_models])

        sym_rtype2 = rtype2.symmetric_type
        self.assertTrue(sym_rtype2.is_copiable)
        self.assertFalse(sym_rtype2.minimal_display)

    def test_relations_types02(self):
        "Invalid subject PK."
        self.login_as_super(is_staff=True)

        pka = 'creme_config-test_import_relations_types02'  # not '-subject_'

        rtypes_data = [{
            'id':          pka,  'predicate':       'loves',
            'is_copiable': True, 'minimal_display': False,

            'symmetric': {
                'id': 'creme_config-object_test_import_relations_types02',
                'predicate': 'is loved by',
                'is_copiable': False, 'minimal_display': True,
            },
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'relation_types': rtypes_data}))
        json_file.name = 'config-26-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This relation type PK is invalid: «{}».').format(pka),
        )

    def test_relations_types03(self):
        "Do no override a not custom relation-type."
        self.login_as_super(is_staff=True)

        rtype = RelationType.objects.filter(is_custom=False, id__contains='-subject_').first()
        self.assertIsNotNone(rtype)

        rtypes_data = [{
            'id':          rtype.id, 'predicate': 'loves',
            'is_copiable': True, 'minimal_display': False,
            'symmetric':   {
                'predicate': 'is loved by', 'is_copiable': False, 'minimal_display': True,
            },
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'relation_types': rtypes_data}))
        json_file.name = 'config-26-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This relation type cannot be overridden: «{}».').format(rtype),
        )

    def test_relations_types04(self):
        "Invalid property types."
        self.login_as_super(is_staff=True)

        ptype_uuid = uuid4()
        rtypes_data = [{
            'id':         'creme_config-subject_test_import_relations_types04',
            'predicate':  'loves',
            'is_copiable': True,
            'minimal_display': False,

            'subject_properties': [str(ptype_uuid)],

            'symmetric':   {
                'predicate': 'is loved by', 'is_copiable': False, 'minimal_display': True,
            },
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'relation_types': rtypes_data}))
        json_file.name = 'config-30-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This property type UUIDs are invalid: {}.').format(ptype_uuid),
        )

    def test_relations_types05(self):
        "A related property types is imported"
        self.login_as_super(is_staff=True)

        ptype1 = CremePropertyType.objects.create(text='Is very important')
        ptype2_uuid = str(uuid4())

        rtypes_data = [{
            'id':         'creme_config-subject_test_import_relations_types05',
            'predicate':  'loves',
            'is_copiable': True,
            'minimal_display': False,

            'subject_properties': [str(ptype1.uuid), ptype2_uuid],

            'symmetric': {
                'predicate': 'is loved by', 'is_copiable': False, 'minimal_display': True,
            },
        }]
        data = {
            'version': self.VERSION,
            'property_types': [
                {'uuid': ptype2_uuid, 'text': 'Is important', 'is_copiable': True},
            ],
            'relation_types': rtypes_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-30-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        rtype_data = rtypes_data[0]
        rtype = self.get_object_or_fail(
            RelationType,
            is_custom=True, id=rtype_data['id'], predicate=rtype_data['predicate'],
        )
        ptype2 = self.get_object_or_fail(CremePropertyType, uuid=ptype2_uuid)
        self.assertCountEqual([ptype1, ptype2], rtype.subject_properties.all())

    def test_fields_config01(self):
        self.login_as_super(is_staff=True)

        fname1 = 'description'
        fname2 = 'phone'
        fconfs_data = [
            {
                'ctype': 'creme_core.fakecontact',
                'descriptions': [
                    [fname1, {'hidden': True}],
                    [fname2, {'required': True}],
                ],
            },
        ]
        data = {
            'version': self.VERSION,
            'fields_config': fconfs_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-02-07-2021.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        fconf = self.get_object_or_fail(
            FieldsConfig,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertEqual(2, len(fconf.descriptions))

        self.assertTrue(fconf.is_fieldname_hidden(fname1))
        self.assertTrue(fconf.is_fieldname_required(fname2))

    def test_fields_config02(self):
        "A configuration already exists for this ContentType."
        self.login_as_super(is_staff=True)

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('mobile', {FieldsConfig.HIDDEN: True})],
        )

        fname = 'phone'
        data = {
            'version': self.VERSION,
            'fields_config': [
                {
                    'ctype': 'creme_core.fakecontact',
                    'descriptions': [[fname, {'hidden': True}]],
                },
            ],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-02-07-2021.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        fconf = self.get_object_or_fail(
            FieldsConfig,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertEqual(1, len(fconf.descriptions))
        self.assertTrue(fconf.is_fieldname_hidden(fname))

    def test_customfields01(self):
        self.login_as_super(is_staff=True)

        get_ct = ContentType.objects.get_for_model

        uuid_01 = uuid4()
        uuid_02 = uuid4()

        uuid_enum11 = uuid4()
        uuid_enum12 = uuid4()
        uuid_enum21 = uuid4()
        uuid_enum22 = uuid4()

        ct_str_c = 'creme_core.fakecontact'
        ct_str_o = 'creme_core.fakeorganisation'

        cfields_data = [
            {
                'uuid': str(uuid_01), 'ctype': ct_str_c, 'name': 'Rating',
                'type': CustomField.INT,
            }, {
                'uuid': str(uuid_02), 'ctype': ct_str_o, 'name': 'Use OS ?',
                'type': CustomField.BOOL
            }, {
                'uuid': str(uuid4()), 'ctype': ct_str_c, 'name': 'Languages',
                'type': CustomField.ENUM,
                'choices': [
                    {
                        'uuid': str(uuid_enum11),
                        'value': 'C',
                    }, {
                        'uuid': str(uuid_enum12),
                        'value': 'Python',
                    },
                ],
            }, {
                'uuid': str(uuid4()), 'ctype': ct_str_c, 'name': 'Hobbies',
                'type': CustomField.MULTI_ENUM,
                'choices': [
                    {
                        'uuid': str(uuid_enum21),
                        'value': 'Programming',
                    }, {
                        'uuid': str(uuid_enum22),
                        'value': 'Reading',
                    },
                ],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_fields': cfields_data}))
        json_file.name = 'config-27-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        cfield_data = cfields_data[0]
        self.get_object_or_fail(
            CustomField,
            content_type=get_ct(FakeContact),
            uuid=cfield_data['uuid'],
            name=cfield_data['name'], field_type=cfield_data['type'],
        )

        cfield_data = cfields_data[1]
        self.get_object_or_fail(
            CustomField,
            content_type=get_ct(FakeOrganisation),
            uuid=cfield_data['uuid'],
            name=cfield_data['name'], field_type=cfield_data['type'],
        )

        cfield_data = cfields_data[2]
        cfield3 = self.get_object_or_fail(CustomField, name=cfield_data['name'])
        self.assertCountEqual(
            cfield_data['choices'],
            [
                {
                    'uuid': str(uid),
                    'value': value,
                } for uid, value in cfield3.customfieldenumvalue_set.values_list('uuid', 'value')
            ]
        )

        cfield_data = cfields_data[3]
        cfield4 = self.get_object_or_fail(CustomField, name=cfield_data['name'])
        self.assertCountEqual(
            cfield_data['choices'],
            [
                {
                    'uuid': str(uid),
                    'value': value,
                } for uid, value in cfield4.customfieldenumvalue_set.values_list('uuid', 'value')
            ]
        )

    def test_customfields02(self):
        "Invalid type."
        self.login_as_super(is_staff=True)

        unknown_cfield_type = 1024
        cfields_data = [{
            'uuid': str(uuid4()), 'ctype': 'creme_core.fakecontact',
            'name': 'Rating', 'type': unknown_cfield_type,
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_fields': cfields_data}))
        json_file.name = 'config-27-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This custom-field type is invalid: {}.').format(unknown_cfield_type),
        )

    def test_customfields03(self):
        "Name + ContentType uniqueness"
        self.login_as_super(is_staff=True)

        name = 'Rating'
        CustomField.objects.create(
            content_type=FakeContact, name=name, field_type=CustomField.FLOAT,
        )

        cfields_data = [{
            'uuid': str(uuid4()), 'ctype': 'creme_core.fakecontact',
            'name': name, 'type': CustomField.INT,
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_fields': cfields_data}))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('There is already a custom-field with the same name: {}.').format(name),
        )

    def test_customfields04(self):
        "UUID uniqueness."
        self.login_as_super(is_staff=True)

        cfield = CustomField.objects.create(
            content_type=FakeContact, name='Rating', field_type=CustomField.FLOAT,
        )

        cfields_data = [{
            'uuid': str(cfield.uuid), 'ctype': 'creme_core.fakecontact',
            'name': 'Rank', 'type': CustomField.INT,
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_fields': cfields_data}))
        json_file.name = 'config-06-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'There is already a custom-field with the same UUID: {}.'
            ).format(cfield.uuid),
        )

    def test_headerfilters01(self):
        self.login_as_super(is_staff=True)
        other_user = self.get_root_user()

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)

        rtype = RelationType.objects.first()
        self.assertIsNotNone(rtype)

        ff_name = PropertiesField.name

        cells = [
            EntityCellRegularField.build(FakeContact,  'last_name'),
            EntityCellRegularField.build(FakeContact,  'first_name'),
            EntityCellRelation.build(FakeContact,      rtype.id),
            EntityCellFunctionField.build(FakeContact, ff_name),
        ]

        hfilters_data = [
            {
                'id':         'creme_config-test_import_headerfilters01',
                'name':       'Contact view',
                'ctype':      'creme_core.fakecontact',
                'is_private': True,  # <== not used
                'cells':      [cell.to_dict() for cell in cells],
            }, {
                'id':    'creme_config-test_import_headerfilters02',
                'name':  'Organisation view with spécial character in name',
                'ctype': 'creme_core.fakeorganisation',
                'user':  str(other_user.uuid),
                'cells': [],
                'extra_data': {'my_value': 'my_value'},
            }, {
                'id':         'creme_config-test_import_headerfilters03',
                'name':       'Private contact view',
                'ctype':      'creme_core.fakecontact',
                'user': str(other_user.uuid),
                'is_private': True,
                'cells':      [],
            }, {
                'id':    'creme_config-test_import_headerfilters04',
                'name':  "Invalid user's Organisation view",
                'ctype': 'creme_core.fakeorganisation',
                'user':  str(uuid4()),  # Unknown user
                'cells': [],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-27-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        hfilter_data1 = hfilters_data[0]
        hf1 = self.get_object_or_fail(
            HeaderFilter,
            is_custom=True,
            entity_type=ct_contact,
            id=hfilter_data1['id'],
            name=hfilter_data1['name'],
            user=None, is_private=False,
        )
        self.assertDictEqual({}, hf1.extra_data)

        cells1 = hf1.cells
        self.assertEqual(4, len(cells1))

        cell1_1 = cells1[0]
        self.assertIsInstance(cell1_1, EntityCellRegularField)
        self.assertEqual('last_name',  cell1_1.value)
        self.assertEqual('first_name', cells1[1].value)

        cell1_3 = cells1[2]
        self.assertIsInstance(cell1_3, EntityCellRelation)
        self.assertEqual(rtype, cell1_3.relation_type)

        cell1_4 = cells1[3]
        self.assertIsInstance(cell1_4, EntityCellFunctionField)
        self.assertEqual(ff_name, cell1_4.function_field.name)

        # --
        hfilter_data2 = hfilters_data[1]
        hf2 = self.get_object_or_fail(
            HeaderFilter,
            is_custom=True,
            entity_type=get_ct(FakeOrganisation),
            id=hfilter_data2['id'],
            name=hfilter_data2['name'],
            user=other_user,
            is_private=False,
        )
        self.assertDictEqual({'my_value': 'my_value'}, hf2.extra_data)

        # --
        hfilter_data3 = hfilters_data[2]
        self.get_object_or_fail(
            HeaderFilter,
            is_custom=True,
            entity_type=ct_contact,
            id=hfilter_data3['id'],
            name=hfilter_data3['name'],
            user=other_user,
            is_private=True,
        )

        self.assertFalse(HeaderFilter.objects.filter(id=hfilters_data[3]['id']))

    def test_headerfilters02(self):
        "Do not override not custom header-filters."
        self.login_as_super(is_staff=True)

        hf = self.get_object_or_fail(HeaderFilter, id=DEFAULT_HFILTER_FAKE_CONTACT)

        hfilters_data = [{
            'id':    hf.id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-27-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This view of list cannot be overridden: «{}».').format(hf.name),
        )

    def test_headerfilters03(self):
        "A used RelationType is imported"
        self.login_as_super(is_staff=True)

        rtype_id1 = 'creme_config-subject_test_import_headerfilter03_1'

        rtype_id2a = 'creme_config-subject_test_import_headerfilter03_2'
        rtype_id2b = 'creme_config-object_test_import_headerfilter03_2'

        hf_id = 'creme_config-test_import_headerfilters05'
        hfilter_data = {
            'id':    hf_id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [
                {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                {'type': EntityCellRelation.type_id, 'value': rtype_id1},
                {'type': EntityCellRelation.type_id, 'value': rtype_id2b},
            ],
        }
        data = {
            'version': self.VERSION,
            'relation_types': [
                {
                    'id':              rtype_id1,
                    'predicate':       'loves',
                    'is_copiable':     True,
                    'minimal_display': False,

                    'symmetric': {
                        'predicate': 'is loved by', 'is_copiable': False, 'minimal_display': True,
                    },
                }, {
                    'id':              rtype_id2a,
                    'predicate':       'likes',
                    'is_copiable':     True,
                    'minimal_display': False,

                    'symmetric':       {
                        'predicate': 'is liked by', 'is_copiable': False, 'minimal_display': True,
                    },
                },
            ],
            'header_filters': [hfilter_data],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        hf1 = self.get_object_or_fail(
            HeaderFilter,
            is_custom=True,
            entity_type=ContentType.objects.get_for_model(FakeContact),
            id=hfilter_data['id'],
            name=hfilter_data['name'],
            user=None, is_private=False,
        )
        cells = hf1.cells
        self.assertEqual(3, len(cells))

        cell1_1 = cells[0]
        self.assertIsInstance(cell1_1, EntityCellRegularField)
        self.assertEqual('last_name',  cell1_1.value)

        cell1_2 = cells[1]
        self.assertIsInstance(cell1_2, EntityCellRelation)
        self.assertEqual(rtype_id1, cell1_2.relation_type.id)

        cell1_3 = cells[2]
        self.assertIsInstance(cell1_3, EntityCellRelation)
        self.assertEqual(rtype_id2b, cell1_3.relation_type.id)

    def test_headerfilters04(self):
        "A used CustomField is imported."
        self.login_as_super(is_staff=True)

        cf_uuid = '6a52b4db-f832-489f-b6de-d1558b3938e3'
        ct_str = 'creme_core.fakecontact'
        hf_id = 'creme_config-test_import_headerfilters05'
        hfilter_data = {
            'id':     hf_id,
            'name':  'Contact view',
            'ctype': ct_str,
            'cells': [
                {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                {'type': EntityCellCustomField.type_id,  'value': cf_uuid},
            ],
        }
        data = {
            'version': self.VERSION,
            'custom_fields': [
                {
                    'uuid': cf_uuid, 'ctype': ct_str,
                    'name': 'Rating', 'type': CustomField.INT,
                },
            ],
            'header_filters': [hfilter_data],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        hf1 = self.get_object_or_fail(
            HeaderFilter,
            is_custom=True,
            entity_type=ContentType.objects.get_for_model(FakeContact),
            id=hfilter_data['id'],
            name=hfilter_data['name'],
            user=None, is_private=False,
        )
        cells = hf1.cells
        self.assertEqual(2, len(cells))

        cell1_1 = cells[0]
        self.assertIsInstance(cell1_1, EntityCellRegularField)
        self.assertEqual('last_name',  cell1_1.value)

        cfield = self.get_object_or_fail(CustomField, uuid=cf_uuid)
        cell1_2 = cells[1]
        self.assertIsInstance(cell1_2, EntityCellCustomField)
        self.assertEqual(cfield, cell1_2.custom_field)

    def test_headerfilters_error01(self):
        "Invalid type of cell."
        self.login_as_super(is_staff=True)

        cell_type = 'invalid'
        hf_id = 'creme_config-test_import_headerfilters_error01'
        data = {
            'version': self.VERSION,
            'header_filters': [{
                'id':    hf_id,
                'name':  'Contact view',
                'ctype': 'creme_core.fakecontact',
                'cells': [{'type': cell_type, 'value': 'last_name'}],
            }],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with type="{type}" is invalid in «{container}».').format(
                type=cell_type,
                container=_('view of list id="{id}"').format(id=hf_id),
            ),
        )

    def test_headerfilters_error02(self):
        "Invalid cell: regular field."
        self.login_as_super(is_staff=True)

        fname = 'name'
        hf_id = 'creme_config-test_import_headerfilters_error02'
        hfilters_data = [{
            'id':    hf_id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [EntityCellRegularField.build(FakeOrganisation, fname).to_dict()],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-27-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with field="{field}" is invalid in «{container}».'
            ).format(
                field=fname,
                container=_('view of list id="{id}"').format(id=hf_id),
            ),
        )

    def test_headerfilters_error03(self):
        "Invalid cell: custom-field."
        self.login_as_super(is_staff=True)

        cf_uuid = '6a52b4db-f832-489f-b6de-d1558b3938f4'
        hf_id = 'creme_config-test_import_headerfilters_error03'
        hfilters_data = [{
            'id':    hf_id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [{'type': EntityCellCustomField.type_id,  'value': cf_uuid}],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-06-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with custom-field="{uuid}" is invalid in «{container}».'
            ).format(
                uuid=cf_uuid,
                container=_('view of list id="{id}"').format(id=hf_id),
            ),
        )

    def test_headerfilters_error04(self):
        "Invalid cell: function field."
        self.login_as_super(is_staff=True)

        ff_name = 'invalid'
        hf_id = 'creme_config-test_import_headerfilters-error04'
        hfilters_data = [{
            'id':    hf_id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [
                {'type': EntityCellRegularField.type_id,  'value': 'last_name'},
                {'type': EntityCellFunctionField.type_id, 'value': ff_name},
            ],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with function-field="{ffield}" is invalid in «{container}».'
            ).format(
                ffield=ff_name,
                container=_('view of list id="{id}"').format(id=hf_id),
            ),
        )

    def test_headerfilters_error05(self):
        "Invalid cell: relation."
        self.login_as_super(is_staff=True)

        rtype_id = 'creme_config-subject_test_import_headerfilters_error05'  # <= does not exist
        hf_id = 'creme_config-test_import_headerfilters-error04'
        hfilters_data = [{
            'id':    hf_id,
            'name':  'Contact view',
            'ctype': 'creme_core.fakecontact',
            'cells': [
                {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                {'type': EntityCellRelation.type_id, 'value': rtype_id},
            ],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'header_filters': hfilters_data}))
        json_file.name = 'config-01-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with relation-type="{rtype}" is invalid in «{container}».'
            ).format(
                rtype=rtype_id,
                container=_('view of list id="{id}"').format(id=hf_id),
            ),
        )

    def test_entityfilters01(self):
        self.login_as_super(is_staff=True)
        other_user = self.get_root_user()

        ct_str_c = 'creme_core.fakecontact'
        ct_str_o = 'creme_core.fakeorganisation'

        cf_uuid1 = str(uuid4())
        cf_uuid2 = str(uuid4())

        rtype_id1 = 'creme_config-subject_test_import_entityfilter01'
        ptype_uuid1 = str(uuid4())

        ptype2 = CremePropertyType.objects.create(text='Is very important')

        rtype2 = RelationType.objects.filter(is_internal=False).first()
        self.assertIsNotNone(rtype2)

        contact = other_user.linked_contact

        efilters_data = [
            {
                'id':         'creme_config-test_import_entityfilters01_1',
                'name':       'Spikes',
                'ctype':      ct_str_c,
                'is_private': True,  # <== not used
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': operators.EQUALS, 'values': ['Spike']},
                    }, {
                        'type': RegularFieldConditionHandler.type_id,
                        'name':  'last_name',
                        'value': {'operator': operators.STARTSWITH, 'values': ['Spi']},
                    }, {
                        'type':  RelationConditionHandler.type_id,
                        'name':  rtype_id1,
                        'value': {'has': True},
                    }, {
                        'type':  PropertyConditionHandler.type_id,
                        'name':  ptype_uuid1,
                        'value': True,
                    }, {
                        'type': PropertyConditionHandler.type_id,
                        'name':  str(ptype2.uuid),
                        'value': False,
                    },
                ],
            }, {
                'id':     'creme_config-test_import_entityfilters01_2',
                'name':   'Organisation view with spécial characters in name',
                'ctype':  ct_str_o,
                'user':   str(other_user.uuid),
                'use_or': False,
                'conditions': [
                    {
                        'type':  DateRegularFieldConditionHandler.type_id,
                        'name':  'creation_date',
                        'value': {'start': {'month': 4, 'day': 1, 'year': 2015}},
                    }, {
                        'type':  DateRegularFieldConditionHandler.type_id,
                        'name':  'creation_date',
                        'value': {'end': {'month': 5, 'day': 1, 'year': 2015}},
                    }, {
                        'type': DateRegularFieldConditionHandler.type_id,
                        'name':  'modified',
                        'value': {'name': 'current_quarter'},
                    }, {
                        'type': RelationConditionHandler.type_id,
                        'name':  rtype2.id,
                        'value': {'has': False, 'ct': ct_str_c},
                    }, {
                        'type': RelationConditionHandler.type_id,
                        'name':  rtype2.id,
                        'value': {'has': True, 'entity': str(contact.uuid)},
                    },
                ],
                'extra_data': {'my_key': 'my_value'},
            }, {
                'id':         'creme_config-test_import_entityfilters01_3',
                'name':       'Private contact view',
                'ctype':      ct_str_c,
                'user':       str(other_user.uuid),
                'is_private': True,
                'use_or':     True,
                'conditions': [
                    {
                        'type':  CustomFieldConditionHandler.type_id,
                        'name':  cf_uuid1,
                        'value': {'operator': 10, 'values': ['100']},
                    }, {
                        'type':  DateCustomFieldConditionHandler.type_id,
                        'name':  cf_uuid2,
                        'value': {'start': {'month': 11, 'day': 7, 'year': 2017}},
                    },
                ],
            }, {
                'id':         'creme_config-test_import_entityfilters01_4',
                'name':       "Invalid user's Organisation view",
                'ctype':      ct_str_o,
                'user':       str(uuid4()),  # <==
                'conditions': [],
            }, {
                'id':         'creme_config-test_import_entityfilters01_5',
                'name':       'Organisation view with sub-filter',
                'ctype':      ct_str_o,
                'conditions': [
                    {
                        'type':  SubFilterConditionHandler.type_id,
                        'name':  'creme_config-test_import_entityfilters01_2',  # defined before
                    }, {
                        'type': RelationSubFilterConditionHandler.type_id,
                        'name':  rtype_id1,
                        'value': {
                            'has': True,
                            'filter_id': 'creme_config-test_import_entityfilters01_1',
                        },
                    },
                ],
            },
        ]

        data = {
            'version': self.VERSION,
            'entity_filters': efilters_data,
            'custom_fields':  [
                {
                    'uuid': cf_uuid1, 'ctype': ct_str_c, 'name': 'Rating',
                    'type': CustomField.INT,
                },
                {
                    'uuid': cf_uuid2, 'ctype': ct_str_c, 'name': 'Party',
                    'type': CustomField.DATETIME,
                },
            ],
            'relation_types': [
                {
                    'id':          rtype_id1, 'predicate':   'loves',
                    'is_copiable': True, 'minimal_display': False,

                    'symmetric': {
                        'predicate': 'is loved by',
                        'is_copiable': False, 'minimal_display': True,
                    },
                },
            ],
            'property_types': [
                {'uuid': ptype_uuid1, 'text': 'Is important', 'is_copiable': True},
            ],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-28-10-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)

        efilter_data1 = efilters_data[0]
        ef1 = self.get_object_or_fail(EntityFilter, id=efilter_data1['id'])
        self.assertEqual(efilter_data1['name'], ef1.name)
        self.assertEqual(EF_REGULAR, ef1.filter_type)
        self.assertEqual(ct_contact, ef1.entity_type)
        self.assertTrue(ef1.is_custom)
        self.assertIsNone(ef1.user)
        self.assertFalse(ef1.is_private)
        self.assertFalse(ef1.use_or)
        self.assertDictEqual({}, ef1.extra_data)

        conditions1 = ef1.conditions.all()
        self.assertEqual(5, len(conditions1))

        condition1_1 = conditions1[0]
        self.assertIsInstance(condition1_1, EntityFilterCondition)
        self.assertEqual(RegularFieldConditionHandler.type_id, condition1_1.type)
        self.assertEqual('first_name', condition1_1.name)
        self.assertDictEqual(
            {'operator': operators.EQUALS, 'values': ['Spike']},
            condition1_1.value,
        )

        condition1_2 = conditions1[1]
        self.assertEqual('last_name', condition1_2.name)
        self.assertDictEqual(
            {'operator': operators.STARTSWITH, 'values': ['Spi']},
            condition1_2.value,
        )

        condition1_3 = conditions1[2]
        self.assertEqual(RelationConditionHandler.type_id, condition1_3.type)
        self.assertEqual(rtype_id1, condition1_3.name)
        self.assertEqual({'has': True}, condition1_3.value)

        condition1_4 = conditions1[3]
        self.assertEqual(PropertyConditionHandler.type_id, condition1_4.type)
        self.assertEqual(ptype_uuid1, condition1_4.name)
        self.assertEqual({'has': True}, condition1_4.value)

        condition1_5 = conditions1[4]
        self.assertEqual(str(ptype2.uuid), condition1_5.name)
        self.assertEqual({'has': False}, condition1_5.value)

        # --
        efilter_data2 = efilters_data[1]
        ef2 = self.get_object_or_fail(EntityFilter, id=efilter_data2['id'])
        self.assertEqual(efilter_data2['name'], ef2.name)
        self.assertEqual(EF_REGULAR, ef2.filter_type)
        self.assertEqual(get_ct(FakeOrganisation), ef2.entity_type)
        self.assertTrue(ef2.is_custom)
        self.assertEqual(other_user, ef2.user)
        self.assertFalse(ef2.is_private)
        self.assertFalse(ef2.use_or)
        self.assertDictEqual({'my_key': 'my_value'}, ef2.extra_data)

        conditions2 = ef2.conditions.all()
        self.assertEqual(5, len(conditions2))

        condition2_1 = conditions2[0]
        self.assertEqual(DateRegularFieldConditionHandler.type_id, condition2_1.type)
        self.assertDictEqual(
            {'start': {'day': 1, 'month': 4, 'year': 2015}},
            condition2_1.value,
        )

        self.assertDictEqual(
            {'end': {'day': 1, 'month': 5, 'year': 2015}},
            conditions2[1].value,
        )
        self.assertEqual({'name': 'current_quarter'}, conditions2[2].value)

        condition2_4 = conditions2[3]
        self.assertEqual(rtype2.id, condition2_4.name)
        self.assertDictEqual(
            {'has': False, 'ct': 'creme_core.fakecontact'},
            condition2_4.value,
        )

        condition2_5 = conditions2[4]
        self.assertEqual(rtype2.id, condition2_5.name)
        self.assertDictEqual(
            {'has': True, 'entity': str(contact.uuid)},
            condition2_5.value,
        )

        # --
        efilter_data3 = efilters_data[2]
        ef3 = self.get_object_or_fail(EntityFilter, id=efilter_data3['id'])
        self.assertEqual(efilter_data3['name'], ef3.name)
        self.assertEqual(ct_contact, ef3.entity_type)
        self.assertTrue(ef3.is_custom)
        self.assertEqual(other_user, ef3.user)
        self.assertTrue(ef3.is_private)
        self.assertTrue(ef3.use_or)

        conditions3 = ef3.conditions.all()
        self.assertEqual(2, len(conditions3))

        cfield1 = self.get_object_or_fail(CustomField, uuid=cf_uuid1)
        condition3_1 = conditions3[0]
        self.assertEqual(str(cfield1.uuid), condition3_1.name)
        self.assertDictEqual(
            {
                'operator': 10,
                'rname': 'customfieldinteger',
                'values': ['100'],
            },
            condition3_1.value,
        )

        cfield2 = self.get_object_or_fail(CustomField, uuid=cf_uuid2)
        condition3_2 = conditions3[1]
        self.assertEqual(
            DateCustomFieldConditionHandler.type_id,
            condition3_2.type,
        )
        self.assertEqual(str(cfield2.uuid), condition3_2.name)
        self.assertDictEqual(
            {
                'rname': 'customfielddatetime',
                'start': {'day': 7, 'month': 11, 'year': 2017}
            },
            condition3_2.value,
        )

        # --
        self.assertFalse(EntityFilter.objects.filter(id=efilters_data[3]['id']))
        # --

        efilter_data = efilters_data[4]
        ef5 = self.get_object_or_fail(
            EntityFilter, id=efilter_data['id'], name=efilter_data['name'],
        )

        conditions5 = ef5.conditions.all()
        self.assertEqual(2, len(conditions5))

        condition5_1 = conditions5[0]
        self.assertEqual(ef2.id, condition5_1.name)
        self.assertFalse(condition5_1.value)

        condition5_2 = conditions5[1]
        self.assertEqual(
            RelationSubFilterConditionHandler.type_id,
            condition5_2.type,
        )
        self.assertEqual(rtype_id1, condition5_2.name)
        self.assertDictEqual(
            {'has': True, 'filter_id': ef1.id},
            condition5_2.value,
        )

    def test_entityfilters02(self):
        "Do not override not custom filters."
        self.login_as_super(is_staff=True)

        efilter = EntityFilter.objects.smart_update_or_create(
            'creme_config-contact_me', name='Me',
            model=FakeContact,
            user='admin',
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='is_user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        efilters_data = [
            {
                'id':         efilter.id,
                'name':       'Spikes',
                'ctype':      'creme_core.fakecontact',
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': '{"operator": 1, "values": ["Spike"]}',
                    },
                ],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-28-10-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_('This filter cannot be overridden: «{}».').format(efilter.name),
        )

    def test_entityfilters03(self):
        "Sub-filters ordering."
        self.login_as_super(is_staff=True)
        ct_str_c = 'creme_core.fakecontact'

        ef1 = EntityFilter.objects.smart_update_or_create(
            'creme_config-test_import_entityfilters03_1',
            name='Me',
            model=FakeContact,
            user='admin',
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='is_user',
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        ef_id2 = 'creme_config-test_import_entityfilters03_2'
        ef_id3 = 'creme_config-test_import_entityfilters03_3'
        ef_id4 = 'creme_config-test_import_entityfilters03_4'

        efilters_data = [
            {
                'id':         ef_id2,
                'name':       'Organisation view #1',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type': SubFilterConditionHandler.type_id,
                        'name': ef_id3,  # defined after
                    },
                ],
            }, {
                'id':         ef_id3,
                'name':       'Spikes',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': operators.EQUALS, 'values': ['Spike']},
                    },
                ],
            }, {
                'id':         ef_id4,
                'name':       'Spikes & me',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type': RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': operators.EQUALS, 'values': ['Spike']},
                    }, {
                        'type': SubFilterConditionHandler.type_id,
                        'name': ef1.id,
                    },
                ],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-08-11-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        ef2 = self.get_object_or_fail(EntityFilter, id=efilters_data[0]['id'])
        ef3 = self.get_object_or_fail(EntityFilter, id=efilters_data[1]['id'])

        condition2_1 = self.get_alone_element(ef2.conditions.all())
        self.assertEqual(SubFilterConditionHandler.type_id, condition2_1.type)
        self.assertEqual(ef3.id, condition2_1.name)

        ef4 = self.get_object_or_fail(EntityFilter, id=efilters_data[2]['id'])
        condition4_2 = ef4.conditions.all()[1]
        self.assertEqual(SubFilterConditionHandler.type_id, condition4_2.type)
        self.assertEqual(ef1.id, condition4_2.name)

    def test_entityfilters04(self):
        "(relation) Sub-filters ordering."
        self.login_as_super(is_staff=True)
        ct_str_c = 'creme_core.fakecontact'

        rtype = RelationType.objects.filter(is_internal=False).first()
        self.assertIsNotNone(rtype)

        ef1 = EntityFilter.objects.smart_update_or_create(
            'creme_config-test_import_entityfilters04_1',
            name='Me',
            model=FakeContact,
            user='admin',
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    field_name='is_user',
                    operator=operators.EQUALS,
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        ef_id2 = 'creme_config-test_import_entityfilters04_2'
        ef_id3 = 'creme_config-test_import_entityfilters04_3'
        ef_id4 = 'creme_config-test_import_entityfilters04_4'

        efilters_data = [
            {
                'id':         ef_id2,
                'name':       'Organisation view #1',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type':  RelationSubFilterConditionHandler.type_id,
                        'name':  rtype.id,
                        'value': {
                            'has':       False,
                            'filter_id': ef_id3,  # defined after
                        },
                    },
                ],
            }, {
                'id':         ef_id3,
                'name':       'Spikes',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': operators.EQUALS, 'values': ['Spike']},
                    },
                ],
            }, {
                'id':         ef_id4,
                'name':       'Related to orga',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type':  RelationSubFilterConditionHandler.type_id,
                        'name':  rtype.id,
                        'value': {'has': True, 'filter_id': ef1.id},
                    },
                ],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-08-11-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        ef2 = self.get_object_or_fail(EntityFilter, id=efilters_data[0]['id'])
        ef3 = self.get_object_or_fail(EntityFilter, id=efilters_data[1]['id'])

        condition2_1 = self.get_alone_element(ef2.conditions.all())
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition2_1.type)
        self.assertEqual(rtype.id, condition2_1.name)
        self.assertDictEqual({'has': False, 'filter_id': ef3.id}, condition2_1.value)

        # --
        ef4 = self.get_object_or_fail(EntityFilter, id=efilters_data[2]['id'])

        condition4_1 = self.get_alone_element(ef4.conditions.all())
        self.assertEqual(RelationSubFilterConditionHandler.type_id, condition4_1.type)
        self.assertEqual(rtype.id, condition4_1.name)
        self.assertDictEqual({'has': True, 'filter_id': ef1.id}, condition4_1.value)

    def test_entityfilters_error01(self):
        "Invalid condition type."
        self.login_as_super(is_staff=True)

        unknown_cond_type = 1024
        efilter_id = 'creme_config-test_import_entityfilters_error01'
        efilters_data = [
            {
                'id':         efilter_id,
                'name':       'Spikes',
                'ctype':      'creme_core.fakecontact',
                'conditions': [
                    {
                        'type':  unknown_cond_type,  # <=
                        'name':  'dontcare',
                        'value': {"operator": 1, "values": ["Spike"]},
                    },
                ],
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-06-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition with type="{type}" is invalid in the filter id="{id}".'
            ).format(type=unknown_cond_type, id=efilter_id),
        )

    def test_entityfilters_error02(self):
        "Invalid condition: regular field."
        self.login_as_super(is_staff=True)

        efilters_data = [{
            'id':         'creme_config-test_import_entityfilters_error02',
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  RegularFieldConditionHandler.type_id,
                'name':  'invalid',  # <=
                'value': {'operator': 1, 'values': ['Spike']},
            }],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        errors = self.get_form_or_fail(response).errors
        self.assertTrue(errors)

    def test_entityfilters_error03(self):
        "Invalid condition: property."
        self.login_as_super(is_staff=True)

        ptype_uuid = str(uuid4())  # does not exist/not imported
        ef_id = 'creme_config-test_import_entityfilters_error03'
        efilters_data = [{
            'id':         ef_id,
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  PropertyConditionHandler.type_id,
                'name':  ptype_uuid,
                'value': True,
            }],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on property-type="{ptype}" is invalid '
                'in the filter id="{id}".'
            ).format(ptype=ptype_uuid, id=ef_id),
        )

    def test_entityfilters_error04_a(self):
        "Invalid condition: relation (invalid rtype)."
        self.login_as_super(is_staff=True)

        # Does not exist/not imported
        rtype_id = 'creme_config-subject_test_import_entityfilter_error04_a'

        ef_id = 'creme_config-test_import_entityfilters_error04'
        efilters_data = [{
            'id':         ef_id,
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  RelationConditionHandler.type_id,
                'name':  rtype_id,
                'value': {'has': True},
            }],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on relation-type is invalid in the filter id="{id}" '
                '(unknown relation-type={rtype}).'
            ).format(rtype=rtype_id, id=ef_id),
        )

    def test_entityfilters_error04_b(self):
        "Invalid condition: relation (invalid entity's UUID)."
        self.login_as_super(is_staff=True)

        rtype = RelationType.objects.filter(is_internal=False).first()

        uuid_str = '4be3ab50-6f5a-4688-ab67-3f6874e71b30'
        self.assertFalse(CremeEntity.objects.filter(uuid=uuid_str))

        ef_id = 'creme_config-test_import_entityfilters_error04_b'
        efilters_data = [{
            'id':         ef_id,
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  RelationConditionHandler.type_id,
                'name':  rtype.id,
                'value': {'has': True, 'entity': uuid_str},
            }],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on relation-type is invalid '
                'in the filter id="{id}" (unknown uuid={uuid}).'
            ).format(rtype=rtype.id, id=ef_id, uuid=uuid_str),
        )

    def test_entityfilters_error05(self):
        "Invalid condition: custom-field."
        self.login_as_super(is_staff=True)

        cf_uuid = str(uuid4())  # does not exist/not imported

        ef_id = 'creme_config-test_import_entityfilters_error05'
        efilters_data = [{
            'id':         ef_id,
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  CustomFieldConditionHandler.type_id,
                'name':  cf_uuid,
                'value': {'operator': 10, 'values': ['100']},
            }],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'entity_filters': efilters_data}))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on custom-field="{cfield}" is invalid in the '
                'filter id="{id}".'
            ).format(cfield=cf_uuid, id=ef_id),
        )

    def test_entityfilters_error06(self):
        "Invalid condition: (date) custom-field."
        self.login_as_super(is_staff=True)

        cf_uuid = str(uuid4())  # does not exist/not imported

        ef_id = 'creme_config-test_import_entityfilters_error06'
        efilters_data = [{
            'id':         ef_id,
            'name':       'Spikes',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  DateCustomFieldConditionHandler.type_id,
                'name':  cf_uuid,
                'value': {'start': {'month': 11, 'day': 7, 'year': 2017}},
            }],
        }]

        json_file = StringIO(json_dump({
            'version': self.VERSION, 'entity_filters': efilters_data,
        }))
        json_file.name = 'config-07-11-2017.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on custom-field="{cfield}" is invalid in the '
                'filter id="{id}".'
            ).format(cfield=cf_uuid, id=ef_id),
        )

    def test_entityfilters_error07(self):
        "Invalid condition: sub-filter."
        self.login_as_super(is_staff=True)

        ef_id1 = 'creme_config-test_import_entityfilters_error07_1'
        ef_id2 = 'creme_config-test_import_entityfilters_error07_2'
        efilters_data = [{
            'id':         ef_id1,
            'name':       'Contact view',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type': SubFilterConditionHandler.type_id,
                'name': ef_id2,  # does not exist/not imported
            }],
        }]

        json_file = StringIO(json_dump({
            'version': self.VERSION, 'entity_filters': efilters_data,
        }))
        json_file.name = 'config-08-11-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on sub-filter="{subfilter}" is invalid in the '
                'filter id="{id}".'
            ).format(subfilter=ef_id2, id=ef_id1),
        )

    def test_entityfilters_error08(self):
        "Invalid condition: relation sub-filters (unknown filter)."
        self.login_as_super(is_staff=True)

        rtype = RelationType.objects.filter(is_internal=False).first()
        self.assertIsNotNone(rtype)

        ef_id1 = 'creme_config-test_import_entityfilters_error08_1'
        ef_id2 = 'creme_config-test_import_entityfilters_error08_2'
        efilters_data = [{
            'id':         ef_id1,
            'name':       'Contact view',
            'ctype':      'creme_core.fakecontact',
            'conditions': [{
                'type':  RelationSubFilterConditionHandler.type_id,
                'name':  rtype.id,
                'value': {
                    'has':       False,
                    'filter_id': ef_id2,  # does not exist/not imported
                },
            }],
        }]

        json_file = StringIO(json_dump({
            'version': self.VERSION, 'entity_filters': efilters_data,
        }))
        json_file.name = 'config-08-11-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on related sub-filter="{subfilter}" is invalid '
                'in the filter id="{id}" (unknown filter ID).'
            ).format(subfilter=ef_id2, id=ef_id1),
        )

    def test_entityfilters_error09(self):
        "Invalid condition: relation sub-filters (unknown relation-type)."
        self.login_as_super(is_staff=True)
        ct_str_c = 'creme_core.fakecontact'

        ef_id1 = 'creme_config-test_import_entityfilters_error08_1'
        ef_id2 = 'creme_config-test_import_entityfilters_error08_2'

        rtype_id = 'creme_config-subject_test_import_entityfilter_error09'

        efilters_data = [
            {
                'id':         ef_id1,
                'name':       'Spikes',
                'ctype':      ct_str_c,
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': 1, 'values': ['Spike']},
                    },
                ],
            }, {
                'id':         ef_id2,
                'name':       'Contact view with related subfilter',
                'ctype':      ct_str_c,
                'conditions': [{
                    'type':  RelationSubFilterConditionHandler.type_id,
                    'name':  rtype_id,  # does not exist/not imported
                    'value': {
                        'has':       False,
                        'filter_id': ef_id1,
                    },
                }],
            },
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION, 'entity_filters': efilters_data,
        }))
        json_file.name = 'config-08-11-2017.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The condition on related sub-filter="{subfilter}" is invalid '
                'in the filter id="{id}" (unknown relation-type ID).'
            ).format(subfilter=ef_id1, id=ef_id2),
        )

    def test_customforms01(self):
        self.login_as_super(is_staff=True)

        desc = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM
        cf_uuid = '6a52b4db-f838-489f-b6df-d1558b3938d6'

        role_uuid = str(uuid4())
        gname1 = 'Main'
        gname2 = 'General'
        gname3 = 'Info'
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': role_uuid,
                'name': 'Super-hero',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes':  ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                    },
                ],
            }],
            'custom_forms': [
                {
                    'descriptor': desc.id,
                    'groups': [
                        {
                            'name': gname1,
                            'layout': LAYOUT_DUAL_FIRST,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                                {'type': EntityCellCustomField.type_id, 'value': cf_uuid},
                                {
                                    'type': EntityCellCustomFormSpecial.type_id,
                                    'value': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
                                },
                            ],
                        }, {
                            'group_id': FakeAddressGroup.extra_group_id,
                            'layout': LAYOUT_DUAL_SECOND,
                        },
                    ],
                }, {
                    'descriptor': desc.id,
                    'superuser': True,
                    'groups': [
                        {
                            'name': gname2,
                            'layout': LAYOUT_REGULAR,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                            ],
                        },
                    ],
                }, {
                    'descriptor': desc.id,
                    'role': role_uuid,
                    'groups': [
                        {
                            'name': gname3,
                            'layout': LAYOUT_DUAL_FIRST,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                                {'type': EntityCellRegularField.type_id, 'value': 'phone'},
                            ],
                        },
                    ],
                }
            ],
            'custom_fields': [
                {
                    'uuid': cf_uuid, 'ctype': 'creme_core.fakeorganisation',
                    'name': 'Rating', 'type': CustomField.INT,
                },
            ],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-14-12-2020.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        cfield = self.get_object_or_fail(CustomField, uuid=cf_uuid)

        cfci01 = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )

        groups1 = desc.groups(cfci01)
        self.assertEqual(2, len(groups1), groups1)

        group11 = groups1[0]
        self.assertEqual(gname1,            group11.name)
        self.assertEqual(LAYOUT_DUAL_FIRST, group11.layout)

        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeOrganisation, name='user'),
                EntityCellRegularField.build(model=FakeOrganisation, name='name'),
                EntityCellCustomField(cfield),
                EntityCellCustomFormSpecial(
                    model=FakeOrganisation,
                    name=EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
                ),
            ],
            [*group11.cells],
        )

        group21 = groups1[1]
        self.assertIsInstance(group21, FakeAddressGroup)
        self.assertEqual(LAYOUT_DUAL_SECOND, group21.layout)

        # ---
        cfci02 = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=True,
        )

        group21 = self.get_alone_element(desc.groups(cfci02))
        self.assertEqual(gname2,         group21.name)
        self.assertEqual(LAYOUT_REGULAR, group21.layout)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeOrganisation, name='user'),
                EntityCellRegularField.build(model=FakeOrganisation, name='name'),
            ],
            [*group21.cells],
        )

        # ---
        role = self.get_object_or_fail(UserRole, uuid=role_uuid)
        self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=role, superuser=False,
        )

    def test_customforms02(self):
        "Cells extra."
        self.login_as_super(is_staff=True)

        desc = fake_custom_forms.FAKEACTIVITY_CREATION_CFORM
        gname1 = 'Main'
        gname2 = 'When'
        data = {
            'version': self.VERSION,
            'custom_forms': [
                {
                    'descriptor': desc.id,
                    'groups': [
                        {
                            'name': gname1,
                            'layout': LAYOUT_DUAL_FIRST,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'type'},
                                {'type': EntityCellRegularField.type_id, 'value': 'title'},
                            ],
                        }, {
                            'name': gname2,
                            'cells': [
                                {
                                    'type': EntityCellCustomFormExtra.type_id,
                                    'value': 'fakeactivity_start',
                                },
                                {
                                    'type': EntityCellCustomFormExtra.type_id,
                                    'value': 'fakeactivity_end',
                                },
                            ],
                            'layout': LAYOUT_DUAL_SECOND,
                        },
                    ],
                },
            ],
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-2023-05-25.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        cfci = self.get_object_or_fail(
            CustomFormConfigItem,
            descriptor_id=desc.id, role=None, superuser=False,
        )

        groups = desc.groups(cfci)
        self.assertEqual(2, len(groups), groups)

        group1 = groups[0]
        self.assertEqual(gname1,            group1.name)
        self.assertEqual(LAYOUT_DUAL_FIRST, group1.layout)
        self.assertListEqual(
            [
                EntityCellRegularField.build(model=FakeActivity, name='user'),
                EntityCellRegularField.build(model=FakeActivity, name='type'),
                EntityCellRegularField.build(model=FakeActivity, name='title'),
            ],
            [*group1.cells],
        )

        group2 = groups[1]
        self.assertEqual(gname2,             group2.name)
        self.assertEqual(LAYOUT_DUAL_SECOND, group2.layout)
        self.assertListEqual(
            [
                {'type': EntityCellCustomFormExtra.type_id, 'value': 'fakeactivity_start'},
                {'type': EntityCellCustomFormExtra.type_id, 'value': 'fakeactivity_end'},
            ],
            [cell.to_dict() for cell in group2.cells],
        )

    def test_customforms_error01(self):
        self.login_as_super(is_staff=True)

        descriptor_id = 'INVALID'
        cforms_data = [{
            'descriptor': descriptor_id,
            'groups': [],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_forms': cforms_data}))
        json_file.name = 'config-14-12-2020.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=f"The custom-form descriptor ID is invalid: {descriptor_id}",
        )

    def test_customforms_error02(self):
        self.login_as_super(is_staff=True)

        descriptor_id = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM.id
        cell_type = 'INVALID'
        cforms_data = [{
            'descriptor': descriptor_id,
            'groups': [
                {
                    'name': 'Main',
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        {'type': EntityCellRegularField.type_id, 'value': 'user'},
                        {'type': EntityCellRegularField.type_id, 'value': 'name'},
                        {'type': cell_type, 'value': 'foobar'},
                    ],
                },
            ],
        }]

        json_file = StringIO(json_dump({'version': self.VERSION, 'custom_forms': cforms_data}))
        json_file.name = 'config-2023-05-25.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertFormError(
            self.get_form_or_fail(response),
            field='config',
            errors=_(
                'The column with type="{type}" is invalid in «{container}».'
            ).format(
                type=cell_type,
                container=_('custom-form with id="{id}"').format(id=descriptor_id),
            ),
        )

    def test_relation_bricks(self):
        self.login_as_super(is_staff=True)
        get_ct = ContentType.objects.get_for_model
        ct_str1 = 'creme_core.fakecontact'
        ct_str2 = 'creme_core.fakeorganisation'

        rtype01, rtype02 = RelationType.objects.filter(
            is_custom=False, id__contains='-subject_',
        )[:2]
        rtype03_id = 'creme_config-subject_test_import_relation_bricks01'

        cf_uuid = uuid4()
        cfields_data = [
            {
                'uuid': str(cf_uuid), 'ctype': ct_str1, 'name': 'Rating',
                'type': CustomField.INT,
            },
        ]

        rbi1 = RelationBrickItem(
            relation_type=rtype01,
        ).set_cells(
            get_ct(FakeContact),
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
            ],
        )
        rbi1.save()

        # Will be removed
        rbi2 = RelationBrickItem.objects.create(relation_type=rtype02)

        rbi_uuid3 = uuid4()

        rtypes_data = [
            {
                'id': rtype03_id, 'predicate': 'loves',
                'is_copiable': True, 'minimal_display': False,

                'symmetric': {
                    'predicate': 'is loved by',
                    'is_copiable': True, 'minimal_display': False,
                },
            },
        ]

        rbi_data = [
            {
                'uuid': str(rbi1.uuid),
                'relation_type': rtype01.id,
            }, {
                'uuid': str(rbi_uuid3),
                'relation_type': rtype03_id,
                'cells': {
                    ct_str1: [
                        {'type': EntityCellRegularField.type_id, 'value': 'first_name'},
                        {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                        {'type': EntityCellCustomField.type_id, 'value': str(cf_uuid)},
                    ],
                    ct_str2: [{'type': 'regular_field', 'value': 'name'}],
                },
            },
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'rtype_bricks': rbi_data,
            'relation_types': rtypes_data,
            'custom_fields': cfields_data,
        }))
        json_file.name = 'config-12-02-2021.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        self.assertDoesNotExist(rbi2)

        # rbi1 = self.assertStillExists(rbi1) TODO: recycle instance?
        rbi1 = self.get_object_or_fail(RelationBrickItem, uuid=rbi1.uuid)
        self.assertEqual(rtype01, rbi1.relation_type)
        self.assertFalse([*rbi1.iter_cells()])

        cfield = self.get_object_or_fail(CustomField, uuid=cf_uuid)

        rbi3 = self.get_object_or_fail(RelationBrickItem, relation_type_id=rtype03_id)
        self.assertEqual(rbi_uuid3, rbi3.uuid)

        def assert_cells(model, keys):
            cells = rbi3.get_cells(get_ct(model))
            self.assertIsNotNone(cells)
            self.assertListEqual(keys, [cell.key for cell in cells])

        assert_cells(
            FakeContact,
            [
                'regular_field-first_name',
                'regular_field-last_name',
                f'custom_field-{cfield.id}',
            ],
        )
        assert_cells(FakeOrganisation, ['regular_field-name'])

    def test_instance_bricks(self):
        self.login_as_super(is_staff=True)

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
        contact1 = create_contact(first_name='Naru',    last_name='Narusegawa')
        contact2 = create_contact(first_name='Mutsumi', last_name='Otohime')

        create_ibi = partial(
            InstanceBrickConfigItem.objects.create,
            brick_class_id=TransferInstanceBrick.id,
        )
        create_ibi(entity=contact1)
        create_ibi(entity=contact2)

        ibi_uuid1 = uuid4()
        extra_data1 = {'foo': 128}

        ibi_uuid2 = uuid4()
        e_uuid2 = uuid4()
        self.assertFalse(CremeEntity.objects.filter(uuid=e_uuid2).exists())

        ibi_data = [
            {
                'uuid': str(ibi_uuid1),
                'brick_class': TransferInstanceBrick.id,
                'entity': str(contact1.uuid),
                'extra_data': extra_data1,
            }, {
                'uuid': str(ibi_uuid2),
                'brick_class': TransferInstanceBrick.id,
                'entity': str(e_uuid2),
                'extra_data': {},
            },
        ]
        LEFT = BrickDetailviewLocation.LEFT
        instance_prefix = InstanceBrickConfigItem._brick_id_prefix
        detail_bricks_data = [
            {'id': constants.MODELBRICK_ID,    'order': 1, 'zone': LEFT},
            {'id': f'{instance_prefix}-{ibi_uuid1}', 'order': 2, 'zone': LEFT},
            # Should be dropped
            {'id': f'{instance_prefix}-{ibi_uuid2}', 'order': 3, 'zone': LEFT},
        ]
        home_bricks_data = [
            {'id': bricks.StatisticsBrick.id,  'order': 1},
            {'id': f'{instance_prefix}-{ibi_uuid1}', 'order': 2},
            # Should be dropped
            {'id': f'{instance_prefix}-{ibi_uuid2}', 'order': 3},
        ]
        mypage_bricks_data = [
            {'id': bricks.HistoryBrick.id,     'order': 1},
            {'id': f'{instance_prefix}-{ibi_uuid1}', 'order': 2},
            # Should be dropped
            {'id': f'{instance_prefix}-{ibi_uuid2}', 'order': 3},
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'instance_bricks': ibi_data,
            'detail_bricks': detail_bricks_data,
            'home_bricks': home_bricks_data,
            'mypage_bricks': mypage_bricks_data,
        }))
        json_file.name = 'config-24-05-2023.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        ibi = self.get_alone_element(InstanceBrickConfigItem.objects.all())
        self.assertEqual(ibi_uuid1,                ibi.uuid)
        self.assertEqual(contact1.id,              ibi.entity_id)
        self.assertEqual(TransferInstanceBrick.id, ibi.brick_class_id)
        self.assertDictEqual(extra_data1, ibi.json_extra_data)

        self.assertFalse(InstanceBrickConfigItem.objects.filter(uuid=ibi_uuid2))

        self.assertListEqual(
            [data['id'] for data in detail_bricks_data],
            [
                *BrickDetailviewLocation.objects.filter(
                    content_type=None, role=None, superuser=False, zone=LEFT,
                ).values_list('brick_id', flat=True),
            ],
        )
        self.assertListEqual(
            [data['id'] for data in home_bricks_data],
            [*BrickHomeLocation.objects.values_list('brick_id', flat=True)],
        )
        self.assertListEqual(
            [data['id'] for data in mypage_bricks_data],  # Not ..._data[2]
            [
                *BrickMypageLocation.objects.filter(user=None).values_list('brick_id', flat=True)
            ],
        )

    def test_custom_bricks(self):
        self.login_as_super(is_staff=True)

        old_cbci = CustomBrickConfigItem.objects.create(
            name='FakeOrganisation information',
            content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        ct_str = 'creme_core.fakecontact'

        cf_uuid = uuid4()
        cfields_data = [
            {
                'uuid': str(cf_uuid), 'ctype': ct_str, 'name': 'Rating',
                'type': CustomField.INT,
            },
        ]

        cbci_uuid = uuid4()
        name = 'FakeContact information'
        cbci_data = [
            {
                'uuid': str(cbci_uuid),
                'content_type': ct_str,
                'name': name,
                'cells': [
                    {'type': EntityCellRegularField.type_id, 'value': 'first_name'},
                    {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                    {'type': EntityCellCustomField.type_id,  'value': str(cf_uuid)},
                ],
            },
        ]

        json_file = StringIO(json_dump({
            'version': self.VERSION,
            'custom_bricks': cbci_data,
            'custom_fields': cfields_data,
        }))
        json_file.name = 'config-13-02-2021.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        self.assertDoesNotExist(old_cbci)

        cfield = self.get_object_or_fail(CustomField, uuid=cf_uuid)

        cbci = self.get_object_or_fail(CustomBrickConfigItem, uuid=cbci_uuid)
        self.assertEqual(name,        cbci.name)
        self.assertEqual(FakeContact, cbci.content_type.model_class())
        self.assertListEqual(
            [
                'regular_field-first_name',
                'regular_field-last_name',
                f'custom_field-{cfield.id}',
            ],
            [cell.key for cell in cbci.cells],
        )

    def test_detailview_bricks01(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')
        role_uuid = str(role.uuid)

        TOP    = BrickDetailviewLocation.TOP
        LEFT   = BrickDetailviewLocation.LEFT
        RIGHT  = BrickDetailviewLocation.RIGHT
        BOTTOM = BrickDetailviewLocation.BOTTOM

        BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeOrganisation, order=5, zone=LEFT,
        )

        ct_str = 'creme_core.fakecontact'

        bricks_data = [
            # Default
            {'id': bricks.HistoryBrick.id,      'order': 1,  'zone': TOP},
            {'id': constants.MODELBRICK_ID,     'order': 1,  'zone': LEFT},
            {'id': bricks.CustomFieldsBrick.id, 'order': 10, 'zone': LEFT},
            {'id': bricks.RelationsBrick.id,    'order': 5,  'zone': RIGHT},
            {'id': bricks.PropertiesBrick.id,   'order': 15, 'zone': BOTTOM},

            # FakeContact
            {'id': constants.MODELBRICK_ID,   'order': 1, 'zone': TOP,    'ctype': ct_str},
            {'id': bricks.HistoryBrick.id,    'order': 1, 'zone': LEFT,   'ctype': ct_str},
            {'id': bricks.RelationsBrick.id,  'order': 5, 'zone': RIGHT,  'ctype': ct_str},
            {'id': bricks.PropertiesBrick.id, 'order': 5, 'zone': BOTTOM, 'ctype': ct_str},

            # FakeContact for existing role
            {
                'id': bricks.RelationsBrick.id,    'order': 2, 'zone': TOP,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': bricks.CustomFieldsBrick.id, 'order': 2, 'zone': LEFT,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': constants.MODELBRICK_ID,     'order': 2, 'zone': RIGHT,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': bricks.HistoryBrick.id,      'order': 2, 'zone': BOTTOM,
                'ctype': ct_str, 'role': role_uuid,
            },

            # FakeContact for superuser
            {
                'id': bricks.RelationsBrick.id,    'order': 2, 'zone': TOP,
                'ctype': ct_str, 'superuser': True,
            }, {
                'id': bricks.CustomFieldsBrick.id, 'order': 2, 'zone': LEFT,
                'ctype': ct_str, 'superuser': True,
            }, {
                'id': constants.MODELBRICK_ID,     'order': 2, 'zone': RIGHT,
                'ctype': ct_str, 'superuser': True,
            }, {
                'id': bricks.HistoryBrick.id,      'order': 2, 'zone': BOTTOM,
                'ctype': ct_str, 'superuser': True,
            },
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'detail_bricks': bricks_data}))
        json_file.name = 'config-24-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        # --
        default_bricks_data = defaultdict(list)
        for bdl in BrickDetailviewLocation.objects.filter(
            content_type=None, role=None, superuser=False,
        ):
            default_bricks_data[bdl.zone].append(
                {'id': bdl.brick_id, 'order': bdl.order, 'zone': bdl.zone}
            )

        self.assertFalse(default_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertEqual([bricks_data[0]],                 default_bricks_data.get(TOP))
        self.assertEqual([bricks_data[1], bricks_data[2]], default_bricks_data.get(LEFT))
        self.assertEqual([bricks_data[3]],                 default_bricks_data.get(RIGHT))
        self.assertEqual([bricks_data[4]],                 default_bricks_data.get(BOTTOM))

        # --
        contact_bricks_data = defaultdict(list)
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        for bdl in BrickDetailviewLocation.objects.filter(
                content_type=contact_ct,
                role=None,
                superuser=False,
        ):
            contact_bricks_data[bdl.zone].append({
                'id': bdl.brick_id, 'order': bdl.order, 'zone': bdl.zone, 'ctype': ct_str,
            })

        self.assertFalse(contact_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertEqual([bricks_data[5]], contact_bricks_data.get(TOP))
        self.assertEqual([bricks_data[6]], contact_bricks_data.get(LEFT))
        self.assertEqual([bricks_data[7]], contact_bricks_data.get(RIGHT))
        self.assertEqual([bricks_data[8]], contact_bricks_data.get(BOTTOM))

        # --
        role_contact_bricks_data = defaultdict(list)
        for bdl in BrickDetailviewLocation.objects.filter(
                content_type=contact_ct,
                role=role,
                superuser=False,
        ):
            role_contact_bricks_data[bdl.zone].append({
                'id': bdl.brick_id, 'order': bdl.order, 'zone': bdl.zone,
                'ctype': ct_str, 'role': str(role.uuid),
            })

        self.assertFalse(role_contact_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertEqual([bricks_data[9]],  role_contact_bricks_data.get(TOP))
        self.assertEqual([bricks_data[10]], role_contact_bricks_data.get(LEFT))
        self.assertEqual([bricks_data[11]], role_contact_bricks_data.get(RIGHT))
        self.assertEqual([bricks_data[12]], role_contact_bricks_data.get(BOTTOM))

        # --
        superuser_contact_bricks_data = defaultdict(list)
        for bdl in BrickDetailviewLocation.objects.filter(
                content_type=contact_ct, role=None, superuser=True,
        ):
            superuser_contact_bricks_data[bdl.zone].append({
                'id': bdl.brick_id, 'order': bdl.order, 'zone': bdl.zone,
                'ctype': ct_str, 'superuser': True,
            })

        self.assertFalse(superuser_contact_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertEqual([bricks_data[13]], superuser_contact_bricks_data.get(TOP))
        self.assertEqual([bricks_data[14]], superuser_contact_bricks_data.get(LEFT))
        self.assertEqual([bricks_data[15]], superuser_contact_bricks_data.get(RIGHT))
        self.assertEqual([bricks_data[16]], superuser_contact_bricks_data.get(BOTTOM))

        self.assertFalse(BrickDetailviewLocation.objects.filter(
            content_type=ContentType.objects.get_for_model(FakeOrganisation)
        ))

    def test_detailview_bricks02(self):
        "Related role is imported."
        self.login_as_super(is_staff=True)

        TOP    = BrickDetailviewLocation.TOP
        LEFT   = BrickDetailviewLocation.LEFT
        RIGHT  = BrickDetailviewLocation.RIGHT
        BOTTOM = BrickDetailviewLocation.BOTTOM

        ct_str = 'creme_core.fakecontact'
        role_uuid = str(uuid4())
        bricks_data = [
            # Default
            {'id': bricks.HistoryBrick.id,      'order': 1,  'zone': TOP},
            {'id': constants.MODELBRICK_ID,     'order': 1,  'zone': LEFT},
            {'id': bricks.CustomFieldsBrick.id, 'order': 10, 'zone': LEFT},
            {'id': bricks.RelationsBrick.id,    'order': 5,  'zone': RIGHT},
            {'id': bricks.PropertiesBrick.id,   'order': 15, 'zone': BOTTOM},

            # FakeContact for our role
            {
                'id': bricks.RelationsBrick.id,    'order': 2, 'zone': TOP,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': bricks.CustomFieldsBrick.id, 'order': 2, 'zone': LEFT,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': constants.MODELBRICK_ID,     'order': 2, 'zone': RIGHT,
                'ctype': ct_str, 'role': role_uuid,
            }, {
                'id': bricks.HistoryBrick.id,      'order': 2, 'zone': BOTTOM,
                'ctype': ct_str, 'role': role_uuid,
            },
        ]
        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': role_uuid,
                'name': 'Super-hero',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes':  ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                    },
                ],
            }],
            'detail_bricks': bricks_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-30-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        # --
        role_contact_bricks_data = defaultdict(list)
        for bdl in BrickDetailviewLocation.objects.filter(
            content_type=ContentType.objects.get_for_model(FakeContact),
            role__uuid=role_uuid,
            superuser=False,
        ):
            role_contact_bricks_data[bdl.zone].append({
                'id': bdl.brick_id, 'order': bdl.order, 'zone': bdl.zone,
                'ctype': ct_str, 'role': role_uuid,
            })

        self.assertFalse(role_contact_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertEqual([bricks_data[5]], role_contact_bricks_data.get(TOP))
        self.assertEqual([bricks_data[6]], role_contact_bricks_data.get(LEFT))
        self.assertEqual([bricks_data[7]], role_contact_bricks_data.get(RIGHT))
        self.assertEqual([bricks_data[8]], role_contact_bricks_data.get(BOTTOM))

    def test_home_bricks01(self):
        self.login_as_super(is_staff=True)

        bricks_data = [
            {'id': bricks.HistoryBrick.id,    'order': 5},
            {'id': bricks.StatisticsBrick.id, 'order': 15},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'home_bricks': bricks_data}))
        json_file.name = 'config-24-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            bricks_data,
            [
                {'id': loc.brick_id, 'order': loc.order}
                for loc in BrickHomeLocation.objects.all()
            ],
        )

    def test_home_bricks02(self):
        "Config per role."
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')
        role_uid = str(role.uuid)

        bricks_data = [
            {'id': bricks.HistoryBrick.id,    'order': 5,  'role': role_uid},
            {'id': bricks.StatisticsBrick.id, 'order': 15, 'role': role_uid},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'home_bricks': bricks_data}))
        json_file.name = 'config-02-03-2020.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            bricks_data,
            [
                {'id': loc.brick_id, 'order': loc.order, 'role': str(loc.role.uuid)}
                for loc in BrickHomeLocation.objects.filter(role=role, superuser=False)
            ],
        )

    def test_home_bricks03(self):
        "Config per role (role is imported)."
        self.login_as_super(is_staff=True)

        role_uuid = str(uuid4())
        bricks_data = [
            {'id': bricks.HistoryBrick.id,    'order': 5,  'role': role_uuid},
            {'id': bricks.StatisticsBrick.id, 'order': 15, 'role': role_uuid},
        ]

        data = {
            'version': self.VERSION,
            'roles': [{
                'uuid': role_uuid,
                'name': 'Super-hero',

                'allowed_apps': ['persons'],
                'admin_4_apps': [],

                'creatable_ctypes':  ['creme_core.fakecontact'],
                'exportable_ctypes': [],

                'credentials': [
                    {
                        'value': (
                            EntityCredentials.VIEW
                            | EntityCredentials.CHANGE
                            | EntityCredentials.DELETE
                        ),
                        'type':  SetCredentials.ESET_ALL,
                    },
                ],
            }],
            'home_bricks': bricks_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-02-03-2020.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            bricks_data,
            [
                {'id': loc.brick_id, 'order': loc.order, 'role': str(loc.role.uuid)}
                for loc in BrickHomeLocation.objects.filter(role__isnull=False, superuser=False)
            ],
        )

    def test_home_bricks04(self):
        "Config for superuser."
        self.login_as_super(is_staff=True)

        bricks_data = [
            {'id': bricks.HistoryBrick.id,    'order': 5,  'superuser': True},
            {'id': bricks.StatisticsBrick.id, 'order': 15, 'superuser': True},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'home_bricks': bricks_data}))
        json_file.name = 'config-02-03-2020.csv'

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            bricks_data,
            [
                {'id': loc.brick_id, 'order': loc.order, 'superuser': True}
                for loc in BrickHomeLocation.objects.filter(role=None, superuser=True)
            ],
        )

    def test_mypage_bricks(self):
        user = self.login_as_super(is_staff=True)
        user_loc = BrickMypageLocation.objects.create(
            brick_id=bricks.HistoryBrick.id, order=1, user=user,
        )

        bricks_data = [
            {'id': bricks.HistoryBrick.id,    'order': 5},
            {'id': bricks.StatisticsBrick.id, 'order': 15},
        ]

        json_file = StringIO(json_dump({'version': self.VERSION, 'mypage_bricks': bricks_data}))
        json_file.name = 'config-24-10-2017.csv'  # Django uses this

        response = self.client.post(self.URL, data={'config': json_file})
        self.assertNoFormError(response)
        self.assertListEqual(
            bricks_data,
            [
                {'id': loc.brick_id, 'order': loc.order}
                for loc in BrickMypageLocation.objects.filter(user=None)
            ],
        )

        self.assertStillExists(user_loc)

    def test_notification_channels(self):
        from creme.creme_core.core.notification import OUTPUT_EMAIL

        self.login_as_super(is_staff=True)

        uid1 = uuid4()
        name1 = 'My channel'
        description1 = 'Very useful'

        channel2 = NotificationChannel.objects.create(
            name='My channel #2', description='Description #2',
            default_outputs=[OUTPUT_EMAIL],
        )
        uid2 = channel2.uuid
        name2 = 'My other channel'
        description2 = 'Other description'

        channels_data = [
            {
                'uuid': constants.UUID_CHANNEL_SYSTEM,
                'type': 'creme_core-system',
                'required': False,
                'default_outputs': ['email'],
            }, {
                'uuid': str(uid1),
                # 'type': '',
                'name': name1,
                'description': description1,
                'required': True,
                'default_outputs': ['web', 'email'],
            }, {
                'uuid': str(uid2),
                # 'type': '',
                'name': name2,
                'description': description2,
                'required': False,
                'default_outputs': ['web'],
            },
        ]
        data = {
            'version': self.VERSION,
            'channels': channels_data,
        }

        json_file = StringIO(json_dump(data))
        json_file.name = 'config-16-01-2024.csv'

        response = self.assertPOST200(self.URL, data={'config': json_file})
        self.assertNoFormError(response)

        sys_channel = self.get_object_or_fail(
            NotificationChannel,
            uuid=constants.UUID_CHANNEL_SYSTEM,
        )
        self.assertFalse(sys_channel.required)
        self.assertListEqual(['email'], sys_channel.default_outputs)

        channel1 = self.get_object_or_fail(NotificationChannel, uuid=uid1)
        self.assertEqual('',           channel1.type_id)
        self.assertEqual(name1,        channel1.name)
        self.assertEqual(description1, channel1.description)
        self.assertTrue(channel1.required)
        self.assertListEqual(['web', 'email'], channel1.default_outputs)

        channel2 = self.refresh(channel2)
        self.assertEqual(uid2,         channel2.uuid)
        self.assertEqual('',           channel2.type_id)
        self.assertEqual(name2,        channel2.name)
        self.assertEqual(description2, channel2.description)
        self.assertFalse(channel2.required)
        self.assertListEqual(['web'], channel2.default_outputs)
