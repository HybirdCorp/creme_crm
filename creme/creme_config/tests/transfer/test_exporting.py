from collections import defaultdict
from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_config.core.exporters import Exporter, ExportersRegistry
from creme.creme_core import bricks, constants
from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import (
    EntityCellCustomField,
    EntityCellRegularField,
)
from creme.creme_core.core.entity_filter import (
    EF_CREDENTIALS,
    EF_REGULAR,
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
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.custom_form import (
    EntityCellCustomFormExtra,
    EntityCellCustomFormSpecial,
)
from creme.creme_core.gui.menu import (
    ContainerEntry,
    Separator0Entry,
    Separator1Entry,
)
from creme.creme_core.menu import CremeEntry
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    ButtonMenuItem,
    CremePropertyType,
    CustomBrickConfigItem,
    CustomField,
    CustomFieldEnumValue,
    CustomFormConfigItem,
    EntityFilter,
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
)
from creme.creme_core.populate import UUID_ROLE_REGULAR
from creme.creme_core.tests import fake_custom_forms, fake_forms
from creme.creme_core.tests.fake_forms import FakeAddressGroup
from creme.creme_core.tests.fake_menu import FakeContactsEntry

from .base import TransferBaseTestCase, TransferInstanceBrick


class ExportingTestCase(TransferBaseTestCase):
    URL = reverse('creme_config__transfer_export')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        prefix = InstanceBrickConfigItem._brick_id_prefix
        BrickDetailviewLocation.objects.filter(brick_id__startswith=prefix).delete()
        BrickHomeLocation.objects.filter(brick_id__startswith=prefix).delete()
        BrickMypageLocation.objects.filter(brick_id__startswith=prefix).delete()

    def test_creds(self):
        "Not staff."
        self.login_as_root()
        self.assertGET403(self.URL)

    def test_register01(self):
        registry = ExportersRegistry()
        data_id1 = 'exp1'
        data_id2 = 'exp2'

        @registry.register(data_id=data_id1)
        class TestExporter01(Exporter):
            def dump_instance(self, instance):
                return [{'value': 1}]

        @registry.register(data_id=data_id2)
        class TestExporter02(Exporter):
            def dump_instance(self, instance):
                return [{'value': 2}]

        exporters = [*registry]
        self.assertEqual(2, len(exporters))

        data_id, exporter = exporters[0]
        self.assertEqual(data_id1, data_id)
        self.assertIsInstance(exporter, TestExporter01)

        data_id, exporter = exporters[1]
        self.assertEqual(data_id2, data_id)
        self.assertIsInstance(exporter, TestExporter02)

    def test_register02(self):
        "Collision."
        registry = ExportersRegistry()
        data_id = 'my_exporter'

        @registry.register(data_id=data_id)
        class TestExporter01(Exporter):
            def dump_instance(self, instance):
                return [{'value': 1}]

        with self.assertRaises(ExportersRegistry.Collision):
            @registry.register(data_id=data_id)
            class TestExporter02(Exporter):
                def dump_instance(self, instance):
                    return [{'value': 2}]

    def test_register03(self):
        "Priority (stronger after)."
        registry = ExportersRegistry()
        data_id = 'my_exporter'

        @registry.register(data_id=data_id)
        class TestExporter01(Exporter):
            def dump_instance(self, instance):
                return [{'value': 1}]

        with self.assertNoException():
            @registry.register(data_id=data_id, priority=2)
            class TestExporter02(Exporter):
                def dump_instance(self, instance):
                    return [{'value': 2}]

        item = self.get_alone_element(registry)
        self.assertEqual(data_id, item[0])
        self.assertIsInstance(item[1], TestExporter02)

    def test_register04(self):
        "Priority (stronger before)."
        registry = ExportersRegistry()
        data_id = 'my_exporter'

        @registry.register(data_id=data_id, priority=3)
        class TestExporter01(Exporter):
            def dump_instance(self, instance):
                return [{'value': 1}]

        with self.assertNoException():
            @registry.register(data_id=data_id, priority=2)
            class TestExporter02(Exporter):
                def dump_instance(self, instance):
                    return [{'value': 2}]

        item = self.get_alone_element(registry)
        self.assertEqual(data_id, item[0])
        self.assertIsInstance(item[1], TestExporter01)

    def test_unregister01(self):
        registry = ExportersRegistry()
        data_id1 = 'exp1'
        data_id2 = 'exp2'

        @registry.register(data_id=data_id1)
        def exporter1():
            return [{'value': 1}]

        @registry.register(data_id=data_id2)
        def exporter2():
            return [{'value': 2}]

        registry.unregister(data_id1)
        item = self.get_alone_element(registry)
        self.assertEqual(data_id2, item[0])

    def test_unregister02(self):
        "Un-register before."
        registry = ExportersRegistry()
        data_id1 = 'exp1'
        data_id2 = 'exp2'

        registry.unregister(data_id1)

        @registry.register(data_id=data_id1)
        def exporter1():
            return [{'value': 1}]

        @registry.register(data_id=data_id2)
        def exporter2():
            return [{'value': 2}]

        item = self.get_alone_element(registry)
        self.assertEqual(data_id2, item[0])

    def test_roles(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(
            name='Test',
            allowed_apps=('creme_core', 'persons'),
            admin_4_apps=('persons',),
            creatable_models=[FakeContact, FakeOrganisation],
            exportable_models=[FakeContact],
        )

        efilter = EntityFilter.objects.create(
            id='creme_core-test_transfer_exporting_roles',
            name='Agencies',
            entity_type=FakeOrganisation,
            filter_type=EF_CREDENTIALS,
            use_or=True,
        )

        create_sc = partial(SetCredentials.objects.create, role=role)
        sc1 = create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.LINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )
        sc2 = create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
            ),
            set_type=SetCredentials.ESET_ALL,
            ctype=FakeContact,
        )
        sc3 = create_sc(
            value=EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_OWN,
            ctype=FakeOrganisation,
            forbidden=True,
        )
        sc4 = create_sc(
            value=EntityCredentials.CHANGE,
            set_type=SetCredentials.ESET_FILTER,
            ctype=FakeOrganisation,
            efilter=efilter,
        )

        response = self.assertGET200(self.URL)
        self.assertEqual('application/json', response['Content-Type'])

        with self.assertNoException():
            cd = response['Content-Disposition']

        # TODO: better test for name (regex ?)
        self.assertStartsWith(cd, 'attachment; filename="config-')
        self.assertEndsWith(cd, '.json"')

        with self.assertNoException():
            content = response.json()

        self.assertIsInstance(content, dict)
        self.assertEqual(self.VERSION, content.get('version'))

        roles_info = content.get('roles')
        self.assertIsList(roles_info, length=2)
        self.assertIsInstance(roles_info[0], dict)

        roles_info_per_uuid = {role_info.get('uuid'): role_info for role_info in roles_info}
        role_info1 = roles_info_per_uuid.get(UUID_ROLE_REGULAR)
        self.assertEqual(_('Regular user'), role_info1.get('name'))
        self.assertIn('creme_core', role_info1.get('allowed_apps'))
        self.assertListEqual([], role_info1.get('admin_4_apps'))

        role_info2 = roles_info_per_uuid.get(str(role.uuid))
        self.assertIsNotNone(role_info2)
        self.assertIsInstance(role_info2, dict)
        self.assertCountEqual(
            ['creme_core', 'persons'],
            role_info2.get('allowed_apps'),
        )
        self.assertListEqual(['persons'], role_info2.get('admin_4_apps'))
        self.assertCountEqual(
            ['creme_core.fakecontact', 'creme_core.fakeorganisation'],
            role_info2.get('creatable_ctypes', ()),
        )
        self.assertListEqual(
            ['creme_core.fakecontact'],
            role_info2.get('exportable_ctypes'),
        )
        self.assertListEqual(
            [
                {
                    'value': sc1.value,
                    'type':  sc1.set_type,
                }, {
                    'value': sc2.value,
                    'type':  sc2.set_type,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'value': sc3.value,
                    'type':  sc3.set_type,
                    'ctype': 'creme_core.fakeorganisation',
                    'forbidden': True,
                }, {
                    'value': sc4.value,
                    'type':  sc4.set_type,
                    'ctype': 'creme_core.fakeorganisation',
                    'efilter': efilter.id,
                },
            ],
            role_info2.get('credentials'),
        )

        efilters_info = content.get('entity_filters')
        self.assertIsList(efilters_info)
        for efilter_info in efilters_info:
            self.assertIsInstance(efilter_info, dict)
            if efilter_info.get('id') == efilter.id:
                self.assertEqual(efilter_info.get('filter_type'), EF_CREDENTIALS)
                break
        else:
            self.fail(f'EntityFilter with id="{efilter.id}" not found.')

    def test_relation_bricks(self):
        self.login_as_super(is_staff=True)
        get_ct = ContentType.objects.get_for_model

        cfield = CustomField.objects.create(
            content_type=ContentType.objects.get_for_model(FakeContact),
            name='Rating', field_type=CustomField.INT,
        )

        rtype1 = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate01',
        ).symmetric(
            id='test-objfoo', predicate='object predicate01',
        ).get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subbar', predicate='subject predicate02',
        ).symmetric(
            id='test-objbar', predicate='object predicate02',
        ).get_or_create()[0]

        rbi1 = RelationBrickItem.objects.create(relation_type=rtype1)

        rbi2 = RelationBrickItem(
            relation_type=rtype2,
        ).set_cells(
            get_ct(FakeContact),
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellCustomField(customfield=cfield),
            ],
        ).set_cells(
            get_ct(FakeOrganisation),
            [EntityCellRegularField.build(FakeOrganisation, 'name')],
        )
        rbi2.save()

        response = self.assertGET200(self.URL)
        content = response.json()

        rtype_bricks_info = content.get('rtype_bricks')
        self.assertIsList(rtype_bricks_info, min_length=2)

        # ----
        with self.assertNoException():
            all_rbi_info01 = [
                dumped_rbi
                for dumped_rbi in rtype_bricks_info
                if dumped_rbi['relation_type'] == rtype1.id
            ]

        rbi_info01 = self.get_alone_element(all_rbi_info01)
        self.assertEqual(str(rbi1.uuid), rbi_info01.get('uuid'))
        self.assertNotIn('cells', rbi_info01)

        # ----
        with self.assertNoException():
            all_rbi_info02 = [
                dumped_rbi
                for dumped_rbi in rtype_bricks_info
                if dumped_rbi['relation_type'] == rtype2.id
            ]

        rbi_info02 = self.get_alone_element(all_rbi_info02)
        self.assertEqual(str(rbi2.uuid), rbi_info02.get('uuid'))

        cells_info = rbi_info02.get('cells')
        self.assertIsDict(cells_info, length=2)
        self.assertListEqual(
            [
                {'type': 'regular_field', 'value': 'first_name'},
                {'type': 'regular_field', 'value': 'last_name'},
                {'type': 'custom_field', 'value': str(cfield.uuid)},
            ],
            cells_info.get('creme_core.fakecontact'),
        )
        self.assertListEqual(
            [{'type': 'regular_field', 'value': 'name'}],
            cells_info.get('creme_core.fakeorganisation'),
        )

    def test_custom_bricks(self):
        self.login_as_super(is_staff=True)

        cfield = CustomField.objects.create(
            content_type=ContentType.objects.get_for_model(FakeContact),
            name='Rating', field_type=CustomField.INT,
        )

        cbci = CustomBrickConfigItem.objects.create(
            name='FakeContact information',
            content_type=FakeContact,
            cells=[
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellCustomField(cfield),
            ],
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        custom_bricks_info = content.get('custom_bricks')
        self.assertIsList(custom_bricks_info)

        b_uuid = str(cbci.uuid)
        with self.assertNoException():
            all_cbci_info01 = [
                dumped_cbci
                for dumped_cbci in custom_bricks_info
                if dumped_cbci['uuid'] == b_uuid
            ]

        cbci_info = self.get_alone_element(all_cbci_info01)
        self.assertEqual('creme_core.fakecontact', cbci_info.get('content_type'))
        self.assertEqual(cbci.name, cbci_info.get('name'))
        self.assertListEqual(
            [
                {'type': 'regular_field', 'value': 'first_name'},
                {'type': 'regular_field', 'value': 'last_name'},
                {'type': 'custom_field',  'value': str(cfield.uuid)},
            ],
            cbci_info.get('cells'),
        )

    def test_detail_bricks01(self):
        "Default detail-views config."
        self.login_as_super(is_staff=True)

        existing_default_bricks_data = defaultdict(list)

        for bdl in BrickDetailviewLocation.objects.filter(
            content_type=None, role=None, superuser=False,
        ):
            existing_default_bricks_data[bdl.zone].append({'id': bdl.brick_id, 'order': bdl.order})

        self.assertFalse(existing_default_bricks_data.get(BrickDetailviewLocation.HAT))
        self.assertFalse(existing_default_bricks_data.get(BrickDetailviewLocation.TOP))
        self.assertFalse(existing_default_bricks_data.get(BrickDetailviewLocation.BOTTOM))
        self.assertTrue(existing_default_bricks_data.get(BrickDetailviewLocation.LEFT))
        self.assertTrue(existing_default_bricks_data.get(BrickDetailviewLocation.RIGHT))

        response = self.assertGET200(self.URL)
        content = response.json()

        bricks_info = content.get('detail_bricks')
        self.assertIsList(bricks_info)

        with self.assertNoException():
            default_bricks_info = [
                dumped_bdl
                for dumped_bdl in bricks_info
                if 'ctype' not in dumped_bdl and 'role' not in dumped_bdl
            ]

        self.assertFalse([
            binfo
            for binfo in default_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.HAT
        ])
        self.assertFalse([
            binfo
            for binfo in default_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.TOP
        ])
        self.assertFalse([
            binfo
            for binfo in default_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.BOTTOM
        ])

        self.assertListEqual(
            existing_default_bricks_data.get(BrickDetailviewLocation.LEFT),
            [
                {'id': binfo['id'], 'order': binfo['order']}
                for binfo in default_bricks_info
                if binfo['zone'] == BrickDetailviewLocation.LEFT
            ],
        )
        self.assertListEqual(
            existing_default_bricks_data.get(BrickDetailviewLocation.RIGHT),
            [
                {'id': binfo['id'], 'order': binfo['order']}
                for binfo in default_bricks_info
                if binfo['zone'] == BrickDetailviewLocation.RIGHT
            ],
        )

    def test_detail_bricks02(self):
        "CT config."
        self.login_as_super(is_staff=True)

        self.assertFalse(
            BrickDetailviewLocation.objects.filter(
                content_type=ContentType.objects.get_for_model(FakeContact),
                role=None, superuser=False,
            )
        )

        LEFT  = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            model=FakeContact, zone=LEFT,
        )
        BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, order=5, zone=LEFT,
        )
        create_bdl(brick=bricks.PropertiesBrick, order=10)
        create_bdl(brick=bricks.RelationsBrick,  order=20)
        create_bdl(brick=bricks.HistoryBrick,    order=10, zone=RIGHT)

        response = self.assertGET200(self.URL)
        content = response.json()

        contact_bricks_info = [
            dumped_bdl
            for dumped_bdl in content.get('detail_bricks')
            if dumped_bdl.get('ctype') == 'creme_core.fakecontact'
        ]

        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.HAT
        ])
        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.TOP
        ])
        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.BOTTOM
        ])

        self.assertListEqual(
            [
                {
                    'id': bricks.HistoryBrick.id, 'order': 10, 'zone': RIGHT,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == RIGHT],
        )
        self.assertListEqual(
            [
                {
                    'id': constants.MODELBRICK_ID,    'order': 5,  'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'id': bricks.PropertiesBrick.id, 'order': 10, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'id': bricks.RelationsBrick.id,  'order': 20, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == LEFT],
        )

    def test_detail_bricks03(self):
        "CT config per role."
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')

        LEFT  = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, order=5, zone=LEFT, role=role,
        )
        BrickDetailviewLocation.objects.create_if_needed(
            model=FakeContact, brick=bricks.HistoryBrick, order=10, zone=RIGHT, role=role,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        role_uuid = str(role.uuid)
        contact_bricks_info = [
            dumped_bdl
            for dumped_bdl in content.get('detail_bricks')
            if (
                dumped_bdl.get('ctype') == 'creme_core.fakecontact'
                and dumped_bdl.get('role') == role_uuid
            )
        ]

        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.HAT
        ])
        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.TOP
        ])
        self.assertFalse([
            binfo
            for binfo in contact_bricks_info
            if binfo['zone'] == BrickDetailviewLocation.BOTTOM
        ])

        self.assertListEqual(
            [
                {
                    'id': constants.MODELBRICK_ID, 'order': 5, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                    'role': role_uuid,
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == LEFT],
        )
        self.assertListEqual(
            [
                {
                    'id': bricks.HistoryBrick.id, 'order': 10, 'zone': RIGHT,
                    'ctype': 'creme_core.fakecontact',
                    'role': role_uuid,
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == RIGHT],
        )

    def test_detail_bricks04(self):
        "CT config for superusers."
        self.login_as_super(is_staff=True)

        LEFT = BrickDetailviewLocation.LEFT
        BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, order=5, zone=LEFT, role='superuser',
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        contact_bricks_info = [
            dumped_bdl
            for dumped_bdl in content.get('detail_bricks')
            if (
                dumped_bdl.get('ctype') == 'creme_core.fakecontact'
                and dumped_bdl.get('superuser')
            )
        ]

        self.assertFalse([binfo for binfo in contact_bricks_info if binfo['zone'] != LEFT])
        self.assertListEqual(
            [
                {
                    'id': constants.MODELBRICK_ID, 'order': 5, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact', 'superuser': True,
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == LEFT],
        )

    def test_home_bricks01(self):
        self.login_as_super(is_staff=True)

        existing_locs = [*BrickHomeLocation.objects.all()]
        self.assertTrue(existing_locs)

        response = self.assertGET200(self.URL)
        content = response.json()

        self.assertListEqual(
            [{'id': loc.brick_id, 'order': loc.order} for loc in existing_locs],
            content.get('home_bricks'),
        )

    def test_home_bricks02(self):
        "Config per role."
        self.login_as_super(is_staff=True)
        norole_brick_ids = {*BrickHomeLocation.objects.values_list('brick_id', flat=True)}

        role = self.create_role(name='Test')
        create_bhl = partial(BrickHomeLocation.objects.create, role=role)
        create_bhl(brick_id=bricks.HistoryBrick.id,    order=1)
        create_bhl(brick_id=bricks.StatisticsBrick.id, order=2)

        response = self.assertGET200(self.URL)
        content = response.json()

        role_brick_ids = []
        for data in content.get('home_bricks'):
            self.assertNotIn('superuser', data)

            brick_id = data.get('id')

            try:
                role_uuid = data['role']
            except KeyError:
                norole_brick_ids.discard(brick_id)
            else:
                self.assertEqual(str(role.uuid), role_uuid)
                role_brick_ids.append(brick_id)

        self.assertFalse(norole_brick_ids)
        self.assertListEqual(
            [bricks.HistoryBrick.id, bricks.StatisticsBrick.id],
            role_brick_ids,
        )

    def test_home_bricks03(self):
        "Config for super_user."
        self.login_as_super(is_staff=True)
        nosuper_brick_ids = {*BrickHomeLocation.objects.values_list('brick_id', flat=True)}

        create_bhl = partial(BrickHomeLocation.objects.create, superuser=True)
        create_bhl(brick_id=bricks.HistoryBrick.id,    order=1)
        create_bhl(brick_id=bricks.StatisticsBrick.id, order=2)

        response = self.assertGET200(self.URL)
        content = response.json()

        super_brick_ids = []
        for data in content.get('home_bricks'):
            self.assertNotIn('role', data)

            brick_id = data.get('id')

            try:
                superuser_flag = data['superuser']
            except KeyError:
                nosuper_brick_ids.discard(brick_id)
            else:
                self.assertIs(superuser_flag, True)
                super_brick_ids.append(brick_id)

        self.assertFalse(nosuper_brick_ids)
        self.assertListEqual(
            [bricks.HistoryBrick.id, bricks.StatisticsBrick.id],
            super_brick_ids,
        )

    def test_mypage_bricks(self):
        self.login_as_super(is_staff=True)

        existing_locs = [*BrickMypageLocation.objects.filter(user=None)]
        self.assertTrue(existing_locs)

        response = self.assertGET200(self.URL)
        content = response.json()

        self.assertListEqual(
            [{'id': loc.brick_id, 'order': loc.order} for loc in existing_locs],
            content.get('mypage_bricks'),
        )

    def test_instance_bricks01(self):
        "Detail view."
        self.login_as_super(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=TransferInstanceBrick.id,
            entity=naru,
            json_extra_data={'foo': 123},
        )
        BrickDetailviewLocation.objects.create_if_needed(
            zone=BrickDetailviewLocation.RIGHT,
            brick=ibi.brick_id, order=5,
            model=FakeContact,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        # ----
        instance_bricks_info = content.get('instance_bricks')
        self.assertIsList(instance_bricks_info, min_length=1)

        with self.assertNoException():
            my_ibci_info01 = [
                dumped_ibci
                for dumped_ibci in instance_bricks_info
                if dumped_ibci['brick_class'] == ibi.brick_class_id
            ]

        ibci_info01 = self.get_alone_element(my_ibci_info01)
        self.assertEqual(str(ibi.uuid),  ibci_info01.get('uuid'))
        self.assertEqual(str(naru.uuid), ibci_info01.get('entity'))
        self.assertDictEqual(ibi.json_extra_data, ibci_info01.get('extra_data'))

        # ---
        contact_bricks_info = [
            dumped_bdl
            for dumped_bdl in content.get('detail_bricks')
            if dumped_bdl.get('ctype') == 'creme_core.fakecontact'
        ]
        RIGHT = BrickDetailviewLocation.RIGHT
        self.assertListEqual(
            [
                {
                    'id': ibi.brick_id,
                    'order': 5, 'zone': RIGHT,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == RIGHT],
        )

    def test_instance_bricks02(self):
        "Home view."
        self.login_as_super(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=TransferInstanceBrick.id,
            entity=naru,
        )

        BrickHomeLocation.objects.create(brick_id=ibi.brick_id, order=1, superuser=True)
        response = self.assertGET200(self.URL)
        content = response.json()

        # ----
        instance_bricks_info = content.get('instance_bricks')
        self.assertIsList(instance_bricks_info, min_length=1)

        with self.assertNoException():
            my_ibci_info01 = [
                dumped_ibci
                for dumped_ibci in instance_bricks_info
                if dumped_ibci['brick_class'] == ibi.brick_class_id
            ]

        ibci_info01 = self.get_alone_element(my_ibci_info01)
        self.assertEqual(str(ibi.uuid),  ibci_info01.get('uuid'))
        self.assertEqual(str(naru.uuid), ibci_info01.get('entity'))
        self.assertDictEqual({}, ibci_info01.get('extra_data'))

        # ---
        self.assertListEqual(
            [{
                'id': ibi.brick_id,
                'superuser': True,
                'order': 1,
            }],
            [
                dumped_bdl
                for dumped_bdl in content.get('home_bricks')
                if 'superuser' in dumped_bdl
            ],
        )

    def test_instance_bricks03(self):
        "<My page> view."
        self.login_as_super(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=TransferInstanceBrick.id,
            entity=naru,
        )
        BrickMypageLocation.objects.create(brick_id=ibi.brick_id, order=1)
        response = self.assertGET200(self.URL)
        content = response.json()

        # ----
        instance_bricks_info = content.get('instance_bricks')
        self.assertIsList(instance_bricks_info, min_length=1)
        self.assertIn(
            {
                'id': ibi.brick_id,
                'order': 1,
            },
            [dumped_bdl for dumped_bdl in content.get('mypage_bricks')],
        )

    def test_menu(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')

        creme_item = MenuConfigItem.objects.get(entry_id=CremeEntry.id)

        create_item = MenuConfigItem.objects.create
        container_label = 'Fake Directory'
        directory = create_item(
            entry_id=ContainerEntry.id,
            entry_data={'label': container_label},
            order=8000,
        )
        create_item(entry_id=FakeContactsEntry.id, order=1, parent=directory)
        sep_label = 'Other'
        create_item(
            entry_id=Separator1Entry.id, order=2, parent=directory,
            entry_data={'label': sep_label},
        )

        def _build_simple_menu(role=None, superuser=False):
            create_mitem = partial(
                MenuConfigItem.objects.create, role=role, superuser=superuser,
            )
            create_mitem(entry_id=CremeEntry.id, order=1)
            create_mitem(entry_id=Separator0Entry.id, order=2)

            container = create_mitem(
                entry_id=ContainerEntry.id, entry_data={'label': 'Directory'}, order=3,
            )
            create_mitem(
                entry_id=FakeContactsEntry.id, order=1, parent=container,
            )

        _build_simple_menu(superuser=True)
        _build_simple_menu(role=role)

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_items = content.get('menu')
        self.assertListEqual(
            [{'id': CremeEntry.id, 'order': creme_item.order}],
            [
                i
                for i in loaded_items
                if CremeEntry.id == i.get('id') and 'role' not in i and 'superuser' not in i
            ],
        )
        self.assertFalse([i for i in loaded_items if FakeContactsEntry.id == i.get('id')])
        self.assertListEqual(
            [
                {
                    'id': ContainerEntry.id,
                    'order': 8000,
                    'data': {'label': container_label},
                    'children': [
                        {
                            'id': FakeContactsEntry.id,
                            'order': 1,
                        }, {
                            'id': Separator1Entry.id,
                            'order': 2,
                            'data': {'label': sep_label},
                        },
                    ],
                },
            ],
            [i for i in loaded_items if 8000 == i.get('order')],
        )
        self.assertListEqual(
            [
                {'id': 'creme_core-creme',      'order': 1, 'superuser': True},
                {'id': 'creme_core-separator0', 'order': 2, 'superuser': True},
                {
                    'id': 'creme_core-container', 'order': 3, 'superuser': True,
                    'data': {'label': 'Directory'},
                    'children': [
                        {'id': 'creme_core-list_contact', 'order': 1},  # 'superuser': True
                    ],
                },
            ],
            [i for i in loaded_items if 'superuser' in i],
        )
        role_uuid = str(role.uuid)
        self.assertListEqual(
            [
                {'id': 'creme_core-creme',      'order': 1, 'role': role_uuid},
                {'id': 'creme_core-separator0', 'order': 2, 'role': role_uuid},
                {
                    'id': 'creme_core-container', 'order': 3, 'role': role_uuid,
                    'data': {'label': 'Directory'},
                    'children': [
                        {'id': 'creme_core-list_contact', 'order': 1},
                    ],
                },
            ],
            [i for i in loaded_items if 'role' in i],
        )

    def test_buttons(self):
        self.login_as_super(is_staff=True)
        role = self.create_role()

        default_buttons = [
            *ButtonMenuItem.objects.filter(content_type=None, superuser=False, role=None),
        ]
        self.assertTrue(default_buttons)

        model = FakeContact
        self.assertFalse(
            ButtonMenuItem.objects.filter(content_type=ContentType.objects.get_for_model(model))
        )

        def gen_id(i):
            return Button.generate_id('creme_config_export', f'test_export_buttons{i}')

        create_bmi = ButtonMenuItem.objects.create_if_needed
        base_ct_bmi1 = create_bmi(order=1001, button=gen_id(1), model=model)
        base_ct_bmi2 = create_bmi(order=1002, button=gen_id(2), model=model)
        super_def_bmi1 = create_bmi(order=1, button=gen_id(3), role='superuser')
        super_def_bmi2 = create_bmi(order=2, button=gen_id(4), role='superuser')
        super_ct_bmi1 = create_bmi(order=1001, button=gen_id(5), role='superuser', model=model)
        super_ct_bmi2 = create_bmi(order=1002, button=gen_id(6), role='superuser', model=model)
        role_def_bmi1 = create_bmi(order=1, button=gen_id(7), role=role)
        role_def_bmi2 = create_bmi(order=2, button=gen_id(8), role=role)
        role_ct_bmi1 = create_bmi(order=1, button=gen_id(9), role=role, model=model)
        role_ct_bmi2 = create_bmi(order=2, button=gen_id(10), role=role, model=model)

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_buttons = content.get('buttons')
        self.maxDiff = None
        self.assertListEqual(
            [
                {'order': bconf.order, 'button_id': bconf.button_id}
                for bconf in default_buttons
            ],
            [
                d
                for d in loaded_buttons
                if 'ctype' not in d and 'superuser' not in d and 'role' not in d
            ],
        )
        self.assertListEqual(
            [
                {
                    'order': base_ct_bmi1.order, 'button_id': base_ct_bmi1.button_id,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'order': base_ct_bmi2.order, 'button_id': base_ct_bmi2.button_id,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [
                d
                for d in loaded_buttons
                if (
                    d.get('ctype') == 'creme_core.fakecontact'
                    and 'role' not in d
                    and 'superuser' not in d
                )
            ],
        )
        self.assertListEqual(
            [
                {
                    'order': super_def_bmi1.order, 'button_id': super_def_bmi1.button_id,
                    'superuser': True,
                }, {
                    'order': super_def_bmi2.order, 'button_id': super_def_bmi2.button_id,
                    'superuser': True,
                },
            ],
            [
                d
                for d in loaded_buttons
                if d.get('superuser') and 'ctype' not in d
            ],
        )
        self.assertListEqual(
            [
                {
                    'order': super_ct_bmi1.order, 'button_id': super_ct_bmi1.button_id,
                    'ctype': 'creme_core.fakecontact',
                    'superuser': True,
                }, {
                    'order': super_ct_bmi2.order, 'button_id': super_ct_bmi2.button_id,
                    'ctype': 'creme_core.fakecontact',
                    'superuser': True,
                },
            ],
            [
                d
                for d in loaded_buttons
                if d.get('superuser') and d.get('ctype') == 'creme_core.fakecontact'
            ],
        )
        role_uuid = str(role.uuid)
        self.assertListEqual(
            [
                {
                    'order': role_def_bmi1.order, 'button_id': role_def_bmi1.button_id,
                    'role': role_uuid,
                }, {
                    'order': role_def_bmi2.order, 'button_id': role_def_bmi2.button_id,
                    'role': role_uuid,
                },
            ],
            [
                d
                for d in loaded_buttons
                if d.get('role') == role_uuid and 'ctype' not in d
            ],
        )
        self.assertListEqual(
            [
                {
                    'order': role_ct_bmi1.order, 'button_id': role_ct_bmi1.button_id,
                    'ctype': 'creme_core.fakecontact',
                    'role': role_uuid,
                }, {
                    'order': role_ct_bmi2.order, 'button_id': role_ct_bmi2.button_id,
                    'ctype': 'creme_core.fakecontact',
                    'role': role_uuid,
                },
            ],
            [
                d
                for d in loaded_buttons
                if d.get('role') == role_uuid and d.get('ctype') == 'creme_core.fakecontact'
            ],
        )

    def test_search(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')

        ct = ContentType.objects.get_for_model(FakeContact)
        cfield = CustomField.objects.create(
            name='Nickname', content_type=ct, field_type=CustomField.STR,
        )

        SearchConfigItem.objects.create(
            content_type=ct,
            cells=[
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellCustomField(cfield),
            ],
        )

        sci_builder = SearchConfigItem.objects.builder
        sci_builder(model=FakeContact, fields=['last_name'], role=role).get_or_create()
        sci_builder(model=FakeOrganisation, fields=['name'], role='superuser').get_or_create()
        sci_builder(model=FakeDocument, fields=['title'], disabled=True).get_or_create()

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_search = content.get('search')
        self.assertListEqual(
            [
                {
                    'ctype': 'creme_core.fakecontact',
                    'cells': [
                        {'type': 'regular_field', 'value': 'first_name'},
                        {'type': 'regular_field', 'value': 'last_name'},
                        {'type': 'custom_field', 'value':  str(cfield.uuid)},
                    ],
                },
            ],
            [
                d for d in loaded_search
                if d.get('ctype') == 'creme_core.fakecontact' and 'role' not in d
            ],
        )
        self.assertListEqual(
            [
                {
                    'ctype': 'creme_core.fakecontact',
                    'role': str(role.uuid),
                    'cells': [{'type': 'regular_field', 'value': 'last_name'}],
                },
            ],
            [
                d for d in loaded_search
                if d.get('ctype') == 'creme_core.fakecontact' and 'role' in d
            ],
        )
        self.assertListEqual(
            [
                {
                    'ctype': 'creme_core.fakeorganisation',
                    'superuser': True,
                    'cells': [{'type': 'regular_field', 'value': 'name'}],
                },
            ],
            [d for d in loaded_search if d.get('ctype') == 'creme_core.fakeorganisation']
        )
        self.assertListEqual(
            [
                {
                    'ctype': 'creme_core.fakedocument',
                    'disabled': True,
                    'cells': [{'type': 'regular_field', 'value': 'title'}],
                },
            ],
            [d for d in loaded_search if d.get('ctype') == 'creme_core.fakedocument'],
        )

    def test_property_types(self):
        self.login_as_super(is_staff=True)

        create_ptype = CremePropertyType.objects.create
        create_ptype(text='Sugoi!')
        self.assertTrue(CremePropertyType.objects.filter(is_custom=False))

        ptype1 = create_ptype(text='Is important', is_custom=True)
        ptype2 = create_ptype(text='Is funny', is_custom=True, is_copiable=False)
        ptype3 = create_ptype(text='Is cool', is_custom=True).set_subject_ctypes(
            FakeContact, FakeOrganisation,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_ptypes = {d['uuid']: d for d in content.get('property_types')}

        self.assertEqual(3, len(loaded_ptypes))
        self.assertDictEqual(
            {'uuid': str(ptype1.uuid), 'text': ptype1.text, 'is_copiable': True},
            loaded_ptypes.get(str(ptype1.uuid)),
        )
        self.assertDictEqual(
            {'uuid': str(ptype2.uuid), 'text': ptype2.text, 'is_copiable': False},
            loaded_ptypes.get(str(ptype2.uuid)),
        )

        with self.assertNoException():
            subject_ctypes = {*loaded_ptypes[str(ptype3.uuid)]['subject_ctypes']}

        self.assertSetEqual(
            {'creme_core.fakecontact', 'creme_core.fakeorganisation'},
            subject_ctypes,
        )

    def test_relations_types(self):
        self.login_as_super(is_staff=True)

        self.assertTrue(RelationType.objects.filter(is_custom=False))

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Sugoi!')
        ptype2 = create_ptype(text='Is important', is_custom=True)
        ptype3 = create_ptype(text='Nope')
        ptype4 = create_ptype(text='Never')

        s_pk_fmt = 'creme_config_export-subject_test_export_relations_types_{}'.format
        o_pk_fmt = 'creme_config_export-object_test_export_relations_types_{}'.format
        rtype1 = RelationType.objects.builder(
            id=s_pk_fmt(1), predicate='loves',
            properties=[ptype1], forbidden_properties=[ptype3],
            is_custom=True,
        ).symmetric(
            id=o_pk_fmt(1), predicate='is loved by',
            properties=[ptype2], forbidden_properties=[ptype4],
            is_copiable=False, minimal_display=True,
        ).get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id=s_pk_fmt(2), predicate='like', models=[FakeContact, FakeOrganisation],
            is_custom=True,
            is_copiable=False,
            minimal_display=True,
        ).symmetric(
            id=o_pk_fmt(2), predicate='is liked by', models=[FakeDocument],
        ).get_or_create()[0]

        RelationType.objects.builder(
            id=s_pk_fmt(3), predicate='dislike',
            models=[FakeContact, FakeOrganisation],
            is_custom=True,
            enabled=False,  # <==
        ).symmetric(
            id=o_pk_fmt(3), predicate='is disliked by', models=[FakeDocument],
        ).get_or_create()

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_rtypes = {d['id']: d for d in content.get('relation_types')}

        self.assertEqual(2, len(loaded_rtypes))

        # --
        rtype1_data = loaded_rtypes.get(rtype1.id)

        with self.assertNoException():
            subject_ptypes1a = rtype1_data.pop('subject_properties')
            object_ptypes1a  = rtype1_data.pop('object_properties')

            subject_forbidden_ptypes1a = rtype1_data.pop('subject_forbidden_properties')
            object_forbidden_ptypes1a  = rtype1_data.pop('object_forbidden_properties')

        self.assertDictEqual(
            {
                'id':          rtype1.id, 'predicate':       rtype1.predicate,
                'is_copiable': True,       'minimal_display': False,
                'symmetric': {
                    'id': rtype1.symmetric_type_id,
                    'predicate': rtype1.symmetric_type.predicate,
                    'is_copiable': False,
                    'minimal_display': True,
                },
            },
            rtype1_data,
        )
        self.assertEqual([str(ptype1.uuid)], subject_ptypes1a)
        self.assertEqual([str(ptype2.uuid)], object_ptypes1a)
        self.assertEqual([str(ptype3.uuid)], subject_forbidden_ptypes1a)
        self.assertEqual([str(ptype4.uuid)], object_forbidden_ptypes1a)

        # --
        rtype2_data = loaded_rtypes.get(rtype2.id)

        with self.assertNoException():
            subject_ctypes2a = {*rtype2_data.pop('subject_ctypes')}
            object_ctypes2a  = rtype2_data.pop('object_ctypes')

        self.assertEqual(
            {
                'id': rtype2.id,     'predicate':       rtype2.predicate,
                'is_copiable': False, 'minimal_display': True,
                'symmetric': {
                    'id': rtype2.symmetric_type_id,
                    'predicate': rtype2.symmetric_type.predicate,
                    'is_copiable': True,
                    'minimal_display': False,
                },
            },
            rtype2_data,
        )
        self.assertSetEqual(
            {'creme_core.fakecontact', 'creme_core.fakeorganisation'},
            subject_ctypes2a,
        )
        self.assertEqual(['creme_core.fakedocument'], object_ctypes2a)

    def test_fields_config(self):
        self.login_as_super(is_staff=True)

        fname1 = 'description'
        fname2 = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (fname1, {FieldsConfig.HIDDEN: True}),
                (fname2, {FieldsConfig.REQUIRED: True}),
            ],
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_fconfigs = {
                d['ctype']: d
                for d in content['fields_config']
            }

        ctype_str = 'creme_core.fakecontact'
        self.assertDictEqual(
            {
                'ctype': ctype_str,
                'descriptions': [
                    [fname1, {'hidden': True}],
                    [fname2, {'required': True}],
                ],
            },
            loaded_fconfigs.get(ctype_str),
        )

    def test_customfields(self):
        self.login_as_super(is_staff=True)

        self.assertFalse(CustomField.objects.all())

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga    = get_ct(FakeOrganisation)

        create_cf = partial(CustomField.objects.create, content_type=ct_contact)
        cfield1 = create_cf(name='Rating',    field_type=CustomField.INT)
        cfield2 = create_cf(name='Use OS ?',  field_type=CustomField.BOOL, content_type=ct_orga)
        cfield3 = create_cf(name='Languages', field_type=CustomField.ENUM)
        cfield4 = create_cf(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield3, value='C')
        eval2 = create_evalue(custom_field=cfield3, value='Python')
        eval3 = create_evalue(custom_field=cfield4, value='Programming')
        eval4 = create_evalue(custom_field=cfield4, value='Reading')

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_cfields = content.get('custom_fields')
        ct_str1 = 'creme_core.fakecontact'
        ct_str2 = 'creme_core.fakeorganisation'
        self.assertListEqual(
            [
                {
                    'uuid': str(cfield1.uuid), 'ctype': ct_str1,
                    'name': cfield1.name, 'type': cfield1.field_type,
                }, {
                    'uuid': str(cfield2.uuid), 'ctype': ct_str2,
                    'name': cfield2.name, 'type': cfield2.field_type,
                }, {
                    'uuid': str(cfield3.uuid), 'ctype': ct_str1,
                    'name': cfield3.name, 'type': cfield3.field_type,
                    'choices': [
                        {
                            'uuid': str(eval1.uuid),
                            'value': eval1.value,
                        }, {
                            'uuid': str(eval2.uuid),
                            'value': eval2.value,
                        },
                    ],
                }, {
                    'uuid': str(cfield4.uuid), 'ctype': ct_str1,
                    'name': cfield4.name, 'type': cfield4.field_type,
                    'choices': [
                        {
                            'uuid': str(eval3.uuid),
                            'value': eval3.value,
                        }, {
                            'uuid': str(eval4.uuid),
                            'value': eval4.value,
                        },
                    ],
                },
            ],
            loaded_cfields,
        )

    def test_headerfilters(self):
        self.login_as_super(is_staff=True)
        other_user = self.get_root_user()

        self.assertTrue(HeaderFilter.objects.filter(is_custom=False))
        self.assertFalse(HeaderFilter.objects.filter(is_custom=True))

        cfield = CustomField.objects.create(
            name='Rating', field_type=CustomField.INT, content_type=FakeContact,
        )

        hf1 = HeaderFilter.objects.proxy(
            id='creme_config_export-test_export_headerfilters01',
            model=FakeContact, name='Contact view',
            is_custom=True,
            cells=[
                (EntityCellRegularField, 'last_name'),
                (EntityCellRegularField, 'first_name'),
                EntityCellCustomField(cfield),
            ],
        ).get_or_create()[0]
        hf2 = HeaderFilter.objects.proxy(
            id='creme_config_export-test_export_headerfilters02',
            model=FakeOrganisation, name='Organisation view',
            is_custom=True,
            user=other_user,
            cells=[
                (EntityCellRegularField, 'name'),
                (EntityCellRegularField, 'description'),
            ],
        ).get_or_create()[0]
        hf3 = HeaderFilter.objects.proxy(
            id='creme_config_export-test_export_headerfilters03',
            model=FakeOrganisation, name='Private organisation view',
            is_custom=True,
            user=other_user, is_private=True,
            cells=[(EntityCellRegularField, 'name')],
            extra_data={'my_key': 'my_value'},
        ).get_or_create()[0]

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_hfilters = {d['id']: d for d in content.get('header_filters')}

        self.assertEqual(3, len(loaded_hfilters))
        self.assertDictEqual(
            {
                'id': hf1.id,
                'name': hf1.name,
                'ctype': 'creme_core.fakecontact',
                'cells': [
                    {'type': EntityCellRegularField.type_id, 'value': 'last_name'},
                    {'type': EntityCellRegularField.type_id, 'value': 'first_name'},
                    # {'type': EntityCellCustomField.type_id,  'value': str(cfield.id)}, # nope
                    {'type': EntityCellCustomField.type_id,  'value': str(cfield.uuid)},
                ],
            },
            loaded_hfilters.get(hf1.id),
        )
        self.assertDictEqual(
            {
                'id': hf2.id,
                'name': hf2.name,
                'ctype': 'creme_core.fakeorganisation',
                'user': str(other_user.uuid),
                'cells': [
                    {'type': EntityCellRegularField.type_id, 'value': 'name'},
                    {'type': EntityCellRegularField.type_id, 'value': 'description'},
                ],
            },
            loaded_hfilters.get(hf2.id),
        )
        self.assertDictEqual(
            {
                'id': hf3.id,
                'name': hf3.name,
                'ctype': 'creme_core.fakeorganisation',
                'user': str(other_user.uuid),
                'is_private': True,
                'cells': [
                    {'type': EntityCellRegularField.type_id, 'value': 'name'},
                ],
                'extra_data': {'my_key': 'my_value'},
            },
            loaded_hfilters.get(hf3.id),
        )

    def test_entityfilters(self):
        self.login_as_super(is_staff=True)
        other_user = self.get_root_user()

        self.assertTrue(EntityFilter.objects.filter(is_custom=False))
        self.assertFalse(EntityFilter.objects.filter(is_custom=True))

        ct_contact = ContentType.objects.get_for_model(FakeContact)
        contact = FakeContact.objects.create(
            user=other_user, first_name='Naru', last_name='Narusegawa',
        )

        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(name='Rating', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Party',  field_type=CustomField.DATETIME)

        ptype = CremePropertyType.objects.create(text='Sugoi!')
        rtype = RelationType.objects.filter(is_internal=False).first()

        create_efilter = EntityFilter.objects.smart_update_or_create
        ef1 = create_efilter(
            'creme_config_export-test_export_entityfilters01',
            name='Spikes',
            model=FakeContact,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    operator=operators.EQUALS,
                    field_name='first_name', values=['Spike'],
                ),
                CustomFieldConditionHandler.build_condition(
                    custom_field=cfield1,
                    operator=operators.GTE,
                    values=[100],
                ),
                DateCustomFieldConditionHandler.build_condition(
                    custom_field=cfield2,
                    start=date(year=2015, month=4, day=1),
                ),
            ],
        )
        ef2 = create_efilter(
            'creme_config_export-test_export_entityfilters02',
            name='Capital > 10000',
            model=FakeOrganisation,
            user=other_user,
            is_custom=True,
            use_or=True,
            conditions=[
                PropertyConditionHandler.build_condition(
                    model=FakeOrganisation, ptype=ptype, has=True,
                ),
                RelationConditionHandler.build_condition(
                    model=FakeOrganisation, rtype=rtype, has=True,
                ),
                RelationConditionHandler.build_condition(
                    model=FakeOrganisation, rtype=rtype, has=False, ct=ct_contact,
                ),
                RelationConditionHandler.build_condition(
                    model=FakeOrganisation, rtype=rtype, has=True, entity=contact,
                ),
            ],
        )
        ef3 = create_efilter(
            'creme_config_export-test_export_entityfilters03',
            name='Capital > 50000',
            model=FakeOrganisation,
            user=other_user, is_private=True,
            is_custom=True,
            conditions=[
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    field_name='creation_date',
                    start=date(year=2017, month=11, day=7),
                ),
                DateRegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    field_name='modified',
                    date_range='current_quarter',
                ),
                SubFilterConditionHandler.build_condition(ef2),
                RelationSubFilterConditionHandler.build_condition(
                    model=FakeOrganisation, rtype=rtype, subfilter=ef1,
                ),
            ],
        )
        ef3.extra_data = {'my_attr': 'my_value'}
        ef3.save()

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_efilters = {d['id']: d for d in content.get('entity_filters')}

        self.maxDiff = None
        self.assertEqual(3, len(loaded_efilters))

        ct_str_c = 'creme_core.fakecontact'
        ct_str_o = 'creme_core.fakeorganisation'
        self.assertDictEqual(
            {
                'id':    ef1.id,
                'name':  ef1.name,
                'ctype': ct_str_c,
                'filter_type': EF_REGULAR,
                'use_or': False,
                'conditions': [
                    {
                        'type':  RegularFieldConditionHandler.type_id,
                        'name':  'first_name',
                        'value': {'operator': 1, 'values': ['Spike']},
                    }, {
                        'type':  CustomFieldConditionHandler.type_id,
                        'name':  str(cfield1.uuid),
                        'value': {'operator': 10, 'values': ['100']},
                    }, {
                        'type':  DateCustomFieldConditionHandler.type_id,
                        'name':  str(cfield2.uuid),
                        'value': {'start': {'month': 4, 'day': 1, 'year': 2015}},
                    },
                ],
            },
            loaded_efilters.get(ef1.id),
        )
        self.assertDictEqual(
            {
                'id':    ef2.id,
                'name':  ef2.name,
                'ctype': ct_str_o,
                'filter_type': EF_REGULAR,
                'user': str(other_user.uuid),
                'use_or': True,
                'conditions': [
                    {
                        'type':  PropertyConditionHandler.type_id,
                        'name': str(ptype.uuid),
                        'value': {'has': True},
                    }, {
                        'type':  RelationConditionHandler.type_id,
                        'name':  rtype.id,
                        'value': {'has': True},
                    }, {
                        'type':  RelationConditionHandler.type_id,
                        'name':  rtype.id,
                        'value': {'has': False, 'ct': ct_str_c},
                    }, {
                        'type':  RelationConditionHandler.type_id,
                        'name':  rtype.id,
                        'value': {'has': True, 'entity': str(contact.uuid)},
                    },
                ],
            },
            loaded_efilters.get(ef2.id),
        )
        self.assertDictEqual(
            {
                'id':    ef3.id,
                'name':  ef3.name,
                'ctype': ct_str_o,
                'filter_type': EF_REGULAR,
                'user': str(other_user.uuid),
                'is_private': True,
                'use_or': False,
                'conditions': [
                    {
                        'type':  DateRegularFieldConditionHandler.type_id,
                        'name':  'creation_date',
                        'value': {'start': {'year': 2017, 'month': 11, 'day': 7}},
                    }, {
                        'type': DateRegularFieldConditionHandler.type_id,
                        'name':  'modified',
                        'value': {'name': 'current_quarter'},
                    }, {
                        'type':  SubFilterConditionHandler.type_id,
                        'name':  ef2.id,
                    }, {
                        'type': RelationSubFilterConditionHandler.type_id,
                        'name': rtype.id,
                        'value': {'has': True, 'filter_id': ef1.id},
                    },
                ],
                'extra_data': {'my_attr': 'my_value'},
            },
            loaded_efilters.get(ef3.id),
        )

    def test_customforms01(self):
        self.login_as_super(is_staff=True)

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_cforms = {d['descriptor']: d for d in content.get('custom_forms')}

        # self.maxDiff = None
        descriptor_id = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM.id
        self.assertDictEqual(
            {
                'descriptor': descriptor_id,
                'groups': [
                    {
                        'name':  'General',
                        'layout':  LAYOUT_REGULAR,
                        'cells': [
                            {'type': EntityCellRegularField.type_id, 'value': 'user'},
                            {'type': EntityCellRegularField.type_id, 'value': 'name'},
                            {'type': EntityCellRegularField.type_id, 'value': 'sector'},
                        ],
                    },
                    {'group_id': 'test-address'},
                ],
            },
            loaded_cforms.get(descriptor_id),
        )

    def test_customforms02(self):
        self.login_as_super(is_staff=True)
        role = self.create_role(name='Test')

        desc = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM
        descriptor_id = desc.id
        CustomFormConfigItem.objects.filter(descriptor_id=descriptor_id).delete()

        cfield = CustomField.objects.create(
            content_type=FakeOrganisation, field_type=CustomField.STR, name='Headline',
        )

        gname1 = 'Main'
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': gname1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        EntityCellCustomField(cfield),
                        (
                            EntityCellCustomFormSpecial,
                            {'name': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS},
                        ),
                    ],
                },
                FakeAddressGroup(model=FakeOrganisation, layout=LAYOUT_DUAL_SECOND),
            ],
        )

        gname2 = 'Fields'
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': gname2,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'description'}),
                    ],
                },
            ],
            role='superuser',
        )

        gname3 = 'Regular fields'
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': gname3,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'phone'}),
                    ],
                },
            ],
            role=role,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_cforms = defaultdict(list)

        with self.assertNoException():
            for d in content.get('custom_forms'):
                loaded_cforms[d['descriptor']].append(d)

        self.assertCountEqual(
            [
                {
                    'descriptor': descriptor_id,
                    'groups': [
                        {
                            'name':  gname1,
                            'layout':  LAYOUT_DUAL_FIRST,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                                {'type': EntityCellCustomField.type_id, 'value': str(cfield.uuid)},
                                {
                                    'type': EntityCellCustomFormSpecial.type_id,
                                    'value': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
                                },
                            ],
                        },
                        {
                            'group_id': FakeAddressGroup.extra_group_id,
                            'layout': LAYOUT_DUAL_SECOND,
                        },
                    ],
                }, {
                    'descriptor': descriptor_id,
                    'superuser': True,
                    'groups': [
                        {
                            'name':  gname2,
                            'layout':  LAYOUT_REGULAR,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                                {'type': EntityCellRegularField.type_id, 'value': 'description'},
                            ],
                        },
                    ],
                }, {
                    'descriptor': descriptor_id,
                    'role': str(role.uuid),
                    'groups': [
                        {
                            'name':  gname3,
                            'layout':  LAYOUT_REGULAR,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'name'},
                                {'type': EntityCellRegularField.type_id, 'value': 'phone'},
                            ],
                        },
                    ],
                }
            ],
            loaded_cforms.get(descriptor_id),
        )

    def test_customforms03(self):
        "Extra cells."
        self.login_as_super(is_staff=True)

        desc = fake_custom_forms.FAKEACTIVITY_CREATION_CFORM
        descriptor_id = desc.id
        CustomFormConfigItem.objects.filter(descriptor_id=descriptor_id).delete()

        gname1 = 'Main'
        gname2 = 'When & where'
        CustomFormConfigItem.objects.create_if_needed(
            descriptor=desc,
            groups_desc=[
                {
                    'name': gname1,
                    'layout': LAYOUT_DUAL_FIRST,
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'type'}),
                        (EntityCellRegularField, {'name': 'title'}),
                    ],
                }, {
                    'name': gname2,
                    'cells': [
                        fake_forms.FakeActivityStartSubCell().into_cell(),
                        fake_forms.FakeActivityEndSubCell().into_cell(),
                        (EntityCellRegularField, {'name': 'place'}),
                    ],
                    'layout': LAYOUT_DUAL_SECOND,
                },
            ],
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_cforms = defaultdict(list)

        with self.assertNoException():
            for d in content.get('custom_forms'):
                loaded_cforms[d['descriptor']].append(d)

        # self.maxDiff = None
        self.assertListEqual(
            [
                {
                    'descriptor': descriptor_id,
                    'groups': [
                        {
                            'name':  gname1,
                            'layout':  LAYOUT_DUAL_FIRST,
                            'cells': [
                                {'type': EntityCellRegularField.type_id, 'value': 'user'},
                                {'type': EntityCellRegularField.type_id, 'value': 'type'},
                                {'type': EntityCellRegularField.type_id, 'value': 'title'},
                            ],
                        }, {
                            'name':  gname2,
                            'layout':  LAYOUT_DUAL_SECOND,
                            'cells': [
                                {
                                    'type': EntityCellCustomFormExtra.type_id,
                                    'value': 'fakeactivity_start',
                                },
                                {
                                    'type': EntityCellCustomFormExtra.type_id,
                                    'value': 'fakeactivity_end',
                                },
                                {'type': 'regular_field', 'value': 'place'},
                            ],
                        },
                    ],
                },
            ],
            loaded_cforms.get(descriptor_id),
        )

    def test_notification_channels(self):
        from creme.creme_core.core import notification

        self.login_as_super(is_staff=True)

        channel1 = NotificationChannel.objects.create(
            name='My channel', description='Very useful',
            default_outputs=[notification.OUTPUT_WEB, notification.OUTPUT_EMAIL],
        )
        channel2 = NotificationChannel.objects.create(
            name='Deleted channel', description='Blablabla',
            default_outputs=[notification.OUTPUT_WEB],
            deleted=now(),
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_channels = {d['uuid']: d for d in content['channels']}

        self.assertDictEqual(
            {
                'uuid': constants.UUID_CHANNEL_SYSTEM,
                'type': 'creme_core-system',
                'required': True,
                'default_outputs': ['web'],
            },
            loaded_channels.get(constants.UUID_CHANNEL_SYSTEM),
        )
        self.assertDictEqual(
            {
                'uuid': constants.UUID_CHANNEL_JOBS,
                'type': 'creme_core-jobs',
                'required': False,
                'default_outputs': ['web'],
            },
            loaded_channels.get(constants.UUID_CHANNEL_JOBS),
        )
        self.assertDictEqual(
            {
                'uuid': constants.UUID_CHANNEL_REMINDERS,
                'type': 'creme_core-reminders',
                'required': True,
                'default_outputs': ['email'],
            },
            loaded_channels.get(constants.UUID_CHANNEL_REMINDERS),
        )
        self.assertDictEqual(
            {
                'uuid': str(channel1.uuid),
                # 'type': '',
                'name': channel1.name,
                'description': channel1.description,
                'required': True,
                'default_outputs': ['web', 'email'],
            },
            loaded_channels.get(str(channel1.uuid)),
        )
        self.assertNotIn(str(channel2.uuid), loaded_channels)
