# -*- coding: utf-8 -*-

from collections import defaultdict
from datetime import date
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
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
    EF_USER,
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
from creme.creme_core.gui.bricks import (
    InstanceBrick,
    SpecificRelationsBrick,
    brick_registry,
)
from creme.creme_core.gui.button_menu import Button
from creme.creme_core.gui.custom_form import EntityCellCustomFormSpecial
from creme.creme_core.gui.menu import ContainerEntry, Separator1Entry
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
    RelationBrickItem,
    RelationType,
    SearchConfigItem,
    SetCredentials,
)
from creme.creme_core.tests import fake_custom_forms
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.fake_forms import FakeAddressGroup
from creme.creme_core.tests.fake_menu import FakeContactsEntry


class ExportingInstanceBrick(InstanceBrick):
    id_ = InstanceBrickConfigItem.generate_base_id('creme_config', 'test_exporting')

    # NB: would be in __init__() in classical cases...
    verbose_name = 'Instance brick for exporter'

    def detailview_display(self, context):
        return (
            f'<table id="{self.id_}">'
            f'<thead><tr>{self.config_item.entity}</tr></thead>'
            f'</table>'
        )

    def home_display(self, context):
        return self.detailview_display(context)


class ExportingTestCase(CremeTestCase):
    URL = reverse('creme_config__transfer_export')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        BrickDetailviewLocation.objects.filter(brick_id__startswith='instanceblock').delete()
        BrickHomeLocation.objects.filter(brick_id__startswith='instanceblock').delete()
        BrickMypageLocation.objects.filter(brick_id__startswith='instanceblock').delete()

        brick_registry.register_4_instance(ExportingInstanceBrick)

    def test_creds(self):
        "Not staff."
        self.login()
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

        exporters = [*registry]
        self.assertEqual(1, len(exporters))

        item = exporters[0]
        self.assertEqual(data_id, item[0])
        self.assertIsInstance(item[1], TestExporter02)

    def test_register04(self):
        "Priority (stronger before)."
        registry = ExportersRegistry()
        data_id = 'my_exporter'

        @registry.register(data_id=data_id, priority=3)
        # def exporter1():
        #     return [{'value': 1}]
        class TestExporter01(Exporter):
            def dump_instance(self, instance):
                return [{'value': 1}]

        with self.assertNoException():
            @registry.register(data_id=data_id, priority=2)
            class TestExporter02(Exporter):
                def dump_instance(self, instance):
                    return [{'value': 2}]

        exporters = [*registry]
        self.assertEqual(1, len(exporters))

        item = exporters[0]
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
        exporters = [*registry]
        self.assertEqual(1, len(exporters))
        self.assertEqual(data_id2, exporters[0][0])

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

        exporters = [*registry]
        self.assertEqual(1, len(exporters))
        self.assertEqual(data_id2, exporters[0][0])

    def test_roles(self):
        "Roles."
        self.login(
            is_staff=True,
            allowed_apps=('creme_core', 'persons'),
            admin_4_apps=('persons',),
            creatable_models=(FakeContact, FakeOrganisation),
        )
        role = self.role
        role.exportable_ctypes.set([ContentType.objects.get_for_model(FakeContact)])

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
        # self.assertStartsWith(cd, 'attachment; filename=config-')
        self.assertStartsWith(cd, 'attachment; filename="config-')
        # self.assertEndsWith(cd, '.json')
        self.assertEndsWith(cd, '.json"')

        with self.assertNoException():
            content = response.json()

        self.assertIsInstance(content, dict)
        # self.assertEqual('1.0', content.get('version'))
        self.assertEqual('1.2', content.get('version'))

        roles_info = content.get('roles')
        self.assertIsList(roles_info, length=1)

        role_info = roles_info[0]
        self.assertIsInstance(role_info, dict)
        self.assertEqual(role.name, role_info.get('name'))
        self.assertSetEqual(
            {'creme_core', 'persons'},
            {*role_info.get('allowed_apps')},
        )
        self.assertListEqual(['persons'], role_info.get('admin_4_apps'))
        self.assertSetEqual(
            {'creme_core.fakecontact', 'creme_core.fakeorganisation'},
            {*role_info.get('creatable_ctypes', ())},
        )
        self.assertListEqual(
            ['creme_core.fakecontact'],
            role_info.get('exportable_ctypes'),
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
            role_info.get('credentials'),
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
        self.login(is_staff=True)
        get_ct = ContentType.objects.get_for_model

        create_rtype = RelationType.objects.smart_update_or_create
        rtype01 = create_rtype(
            ('test-subfoo', 'subject_predicate01'),
            ('test-objfoo', 'object_predicate01'),
        )[0]
        rtype02 = create_rtype(
            ('test-subbar', 'subject_predicate02'),
            ('test-objbar', 'object_predicate02'),
        )[0]

        rtype_brick_id01 = SpecificRelationsBrick.generate_id('test', 'foo')
        RelationBrickItem.objects.create(brick_id=rtype_brick_id01, relation_type=rtype01)

        rtype_brick_id02 = SpecificRelationsBrick.generate_id('test', 'bar')
        RelationBrickItem(
            brick_id=rtype_brick_id02,
            relation_type=rtype02,
        ).set_cells(
            get_ct(FakeContact),
            [
                EntityCellRegularField.build(FakeContact, 'first_name'),
                EntityCellRegularField.build(FakeContact, 'last_name'),
            ],
        ).set_cells(
            get_ct(FakeOrganisation),
            [EntityCellRegularField.build(FakeOrganisation, 'name')],
        ).save()

        response = self.assertGET200(self.URL)
        content = response.json()

        rtype_bricks_info = content.get('rtype_bricks')
        self.assertIsList(rtype_bricks_info, min_length=2)

        # ----
        with self.assertNoException():
            all_rbi_info01 = [
                dumped_rbi
                for dumped_rbi in rtype_bricks_info
                if dumped_rbi['relation_type'] == rtype01.id
            ]

        self.assertEqual(1, len(all_rbi_info01))

        rbi_info01 = all_rbi_info01[0]
        self.assertEqual(rtype_brick_id01, rbi_info01.get('brick_id'))
        self.assertNotIn('cells', rbi_info01)

        # ----
        with self.assertNoException():
            all_rbi_info02 = [
                dumped_rbi
                for dumped_rbi in rtype_bricks_info
                if dumped_rbi['relation_type'] == rtype02.id
            ]

        self.assertEqual(1, len(all_rbi_info02))

        rbi_info02 = all_rbi_info02[0]
        self.assertEqual(rtype_brick_id02, rbi_info02.get('brick_id'))

        cells_info = rbi_info02.get('cells')
        self.assertIsList(cells_info, length=2)

        def find_cells_for_naturalkey(key):
            for ctype_info in cells_info:
                self.assertIsList(ctype_info, length=2)

                if ctype_info[0] == key:
                    return ctype_info[1]

            self.fail(f'Cells for key="{key} not found.')

        self.assertListEqual(
            [
                {'type': 'regular_field', 'value': 'first_name'},
                {'type': 'regular_field', 'value': 'last_name'},
            ],
            find_cells_for_naturalkey('creme_core.fakecontact'),
        )
        self.assertListEqual(
            [{'type': 'regular_field', 'value': 'name'}],
            find_cells_for_naturalkey('creme_core.fakeorganisation'),
        )

    def test_custom_bricks(self):
        self.login(is_staff=True)

        cfield = CustomField.objects.create(
            content_type=ContentType.objects.get_for_model(FakeContact),
            name='Rating', field_type=CustomField.INT,
        )

        cbci = CustomBrickConfigItem.objects.create(
            id='creme_core-fake_contact_info',
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

        with self.assertNoException():
            all_cbci_info01 = [
                dumped_cbci
                for dumped_cbci in custom_bricks_info
                if dumped_cbci['id'] == cbci.id
            ]

        self.assertEqual(1, len(all_cbci_info01))

        cbci_info = all_cbci_info01[0]
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
        self.login(is_staff=True)

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
        self.login(is_staff=True)

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
                    'id': bricks.HistoryBrick.id_, 'order': 10, 'zone': RIGHT,
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
                    'id': bricks.PropertiesBrick.id_, 'order': 10, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'id': bricks.RelationsBrick.id_,  'order': 20, 'zone': LEFT,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == LEFT],
        )

    def test_detail_bricks03(self):
        "CT config per role."
        self.login(is_staff=True)
        role = self.role

        LEFT  = BrickDetailviewLocation.LEFT
        RIGHT = BrickDetailviewLocation.RIGHT

        BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, order=5,  zone=LEFT,  role=role,
        )
        BrickDetailviewLocation.objects.create_if_needed(
            model=FakeContact, brick=bricks.HistoryBrick, order=10, zone=RIGHT, role=role,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        contact_bricks_info = [
            dumped_bdl
            for dumped_bdl in content.get('detail_bricks')
            if (
                dumped_bdl.get('ctype') == 'creme_core.fakecontact'
                and dumped_bdl.get('role') == role.name
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
                    'ctype': 'creme_core.fakecontact', 'role': role.name
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == LEFT],
        )
        self.assertListEqual(
            [
                {
                    'id': bricks.HistoryBrick.id_, 'order': 10, 'zone': RIGHT,
                    'ctype': 'creme_core.fakecontact', 'role': role.name,
                },
            ],
            [binfo for binfo in contact_bricks_info if binfo['zone'] == RIGHT],
        )

    def test_detail_bricks04(self):
        "CT config for super user."
        self.login(is_staff=True)

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
        self.login(is_staff=True)

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
        self.login(is_staff=True)
        norole_brick_ids = {*BrickHomeLocation.objects.values_list('brick_id', flat=True)}

        role = self.role
        create_bhl = partial(BrickHomeLocation.objects.create, role=role)
        create_bhl(brick_id=bricks.HistoryBrick.id_,    order=1)
        create_bhl(brick_id=bricks.StatisticsBrick.id_, order=2)

        response = self.assertGET200(self.URL)
        content = response.json()

        role_brick_ids = []
        for data in content.get('home_bricks'):
            self.assertNotIn('superuser', data)

            brick_id = data.get('id')

            try:
                role_name = data['role']
            except KeyError:
                norole_brick_ids.discard(brick_id)
            else:
                self.assertEqual(role.name, role_name)
                role_brick_ids.append(brick_id)

        self.assertFalse(norole_brick_ids)
        self.assertListEqual(
            [bricks.HistoryBrick.id_, bricks.StatisticsBrick.id_],
            role_brick_ids,
        )

    def test_home_bricks03(self):
        "Config for super_user."
        self.login(is_staff=True)
        nosuper_brick_ids = {*BrickHomeLocation.objects.values_list('brick_id', flat=True)}

        create_bhl = partial(BrickHomeLocation.objects.create, superuser=True)
        create_bhl(brick_id=bricks.HistoryBrick.id_,    order=1)
        create_bhl(brick_id=bricks.StatisticsBrick.id_, order=2)

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
            [bricks.HistoryBrick.id_, bricks.StatisticsBrick.id_],
            super_brick_ids,
        )

    def test_mypage_bricks(self):
        self.login(is_staff=True)

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
        self.login(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.other_user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=ExportingInstanceBrick.id_,
            entity=naru,
        )

        # ---
        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            zone=BrickDetailviewLocation.RIGHT,
            brick=ibi.brick_id, order=5,
        )
        create_bdl(model=FakeContact)

        msg_fmt = _(
            'The configuration of blocks for detailed-views cannot be '
            'exported because it contains references to some instance-blocks '
            '({blocks}), which are not managed, for the following cases: {models}.'
        )
        self.assertContains(
            self.client.get(self.URL),
            msg_fmt.format(
                blocks=ExportingInstanceBrick.verbose_name,
                models=FakeContact._meta.verbose_name,
            ),
            status_code=409,
            html=True,
        )

        # ---
        create_bdl(model=None)
        self.assertContains(
            self.client.get(self.URL),
            msg_fmt.format(
                blocks=ExportingInstanceBrick.verbose_name,
                models='{}, {}'.format(
                    _('Default configuration'),
                    FakeContact._meta.verbose_name,
                ),
            ),
            status_code=409,
            html=True,
        )

    def test_instance_bricks02(self):
        "Home view."
        self.login(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.other_user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=ExportingInstanceBrick.id_,
            entity=naru,
        )

        BrickHomeLocation.objects.create(brick_id=ibi.brick_id, order=1, superuser=True)
        self.assertContains(
            self.client.get(self.URL),
            _(
                'The configuration of blocks for Home cannot be exported '
                'because it contains references to some instance-blocks '
                '({blocks}), which are not managed.'
            ).format(
                blocks=ExportingInstanceBrick.verbose_name,
            ),
            status_code=409,
            html=True,
        )

    def test_instance_bricks03(self):
        "<My page> view."
        self.login(is_staff=True)

        naru = FakeContact.objects.create(
            user=self.other_user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=ExportingInstanceBrick.id_,
            entity=naru,
        )

        BrickMypageLocation.objects.create(brick_id=ibi.brick_id, order=1)
        self.assertContains(
            self.client.get(self.URL),
            _(
                'The configuration of blocks for «My page» cannot be exported '
                'because it contains references to some instance-blocks '
                '({blocks}), which are not managed.'
            ).format(
                blocks=ExportingInstanceBrick.verbose_name,
            ),
            status_code=409,
            html=True,
        )

    def test_menu(self):
        self.login(is_staff=True)

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

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_items = content.get('menu')
        self.assertListEqual(
            [{'id': CremeEntry.id, 'order': creme_item.order}],
            [i for i in loaded_items if CremeEntry.id == i.get('id')],
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

    def test_buttons(self):
        self.login(is_staff=True)

        default_buttons = [*ButtonMenuItem.objects.filter(content_type=None)]
        self.assertTrue(default_buttons)

        contact_ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(ButtonMenuItem.objects.filter(content_type=contact_ct))

        def create_button(i):
            return ButtonMenuItem.objects.create(
                content_type=contact_ct,
                # id=f'creme_config_export-test_export_buttons-{i}',
                order=i,
                button_id=Button.generate_id(
                    'creme_config_export', f'test_export_buttons{i}',
                ),
            )

        bmi1 = create_button(1)
        bmi2 = create_button(2)

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_buttons = content.get('buttons')
        self.assertListEqual(
            [
                {'order': bconf.order, 'button_id': bconf.button_id}
                for bconf in default_buttons
            ],
            [d for d in loaded_buttons if 'ctype' not in d],
        )
        self.assertListEqual(
            [
                {
                    'order': bmi1.order, 'button_id': bmi1.button_id,
                    'ctype': 'creme_core.fakecontact',
                }, {
                    'order': bmi2.order, 'button_id': bmi2.button_id,
                    'ctype': 'creme_core.fakecontact',
                },
            ],
            [d for d in loaded_buttons if d.get('ctype') == 'creme_core.fakecontact']
        )

    def test_search(self):
        self.login(is_staff=True)
        role = self.role

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

        create_sci = SearchConfigItem.objects.create_if_needed
        # create_sci(model=FakeContact, fields=['first_name', 'last_name'])
        create_sci(model=FakeContact, fields=['last_name'], role=role)
        create_sci(model=FakeOrganisation, fields=['name'], role='superuser')
        create_sci(model=FakeDocument, fields=['title'], disabled=True)

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_search = content.get('search')
        self.assertListEqual(
            [
                {
                    'ctype': 'creme_core.fakecontact',
                    # 'fields': 'first_name,last_name',
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
                    'role': role.name,
                    # 'fields': 'last_name',
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
                    # 'fields': 'name',
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
                    # 'fields': 'title',
                    'cells': [{'type': 'regular_field', 'value': 'title'}],
                },
            ],
            [d for d in loaded_search if d.get('ctype') == 'creme_core.fakedocument'],
        )

    def test_property_types(self):
        self.login(is_staff=True)

        CremePropertyType.objects.create(
            pk='creme_config_export-test_export_entityfilters', text='Sugoi !',
        )

        self.assertTrue(CremePropertyType.objects.filter(is_custom=False))

        pk_fmt = 'creme_config_export-test_export_property_types{}'.format
        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk=pk_fmt(1), text='Is important', is_custom=True)
        ptype2 = create_ptype(
            str_pk=pk_fmt(2), text='Is funny', is_custom=True, is_copiable=False,
        )
        ptype3 = create_ptype(
            str_pk=pk_fmt(3), text='Is cool', is_custom=True,
            subject_ctypes=[FakeContact, FakeOrganisation],
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_ptypes = {d['id']: d for d in content.get('property_types')}

        self.assertEqual(3, len(loaded_ptypes))
        self.assertDictEqual(
            {'id': ptype1.id, 'text': ptype1.text, 'is_copiable': True},
            loaded_ptypes.get(ptype1.id),
        )
        self.assertDictEqual(
            {'id': ptype2.id, 'text': ptype2.text, 'is_copiable': False},
            loaded_ptypes.get(ptype2.id),
        )

        with self.assertNoException():
            subject_ctypes = {*loaded_ptypes.get(ptype3.id)['subject_ctypes']}

        self.assertSetEqual(
            {'creme_core.fakecontact', 'creme_core.fakeorganisation'},
            subject_ctypes,
        )

    def test_relations_types(self):
        self.login(is_staff=True)

        self.assertTrue(RelationType.objects.filter(is_custom=False))

        ptype1 = CremePropertyType.objects.create(
            pk='creme_config_export-test_export_relation_types', text='Sugoi !',
        )
        ptype2 = CremePropertyType.objects.smart_update_or_create(
            str_pk='creme_config_export-test_export_relation_types_1',
            text='Is important',
            is_custom=True,
        )

        s_pk_fmt = 'creme_config_export-subject_test_export_relations_types_{}'.format
        o_pk_fmt = 'creme_config_export-object_test_export_relations_types_{}'.format
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1a, rtype1b = create_rtype(
            (s_pk_fmt(1),  'loves',       (), [ptype1]),
            (o_pk_fmt(1),  'is loved by', (), [ptype2]),
            is_custom=True,
            is_copiable=(True, False),
            minimal_display=(False, True),
        )
        rtype2a, rtype2b = create_rtype(
            (s_pk_fmt(2),  'like',        [FakeContact, FakeOrganisation]),
            (o_pk_fmt(2),  'is liked by', [FakeDocument]),
            is_custom=True,
            is_copiable=(False, True),
            minimal_display=(True, False),
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            loaded_rtypes = {d['id']: d for d in content.get('relation_types')}

        self.assertEqual(2, len(loaded_rtypes))

        # --
        rtype1_data = loaded_rtypes.get(rtype1a.id)

        with self.assertNoException():
            subject_ptypes1a = rtype1_data.pop('subject_properties')
            object_ptypes1a  = rtype1_data.pop('object_properties')

        self.assertDictEqual(
            {
                'id':          rtype1a.id, 'predicate':       rtype1a.predicate,
                'is_copiable': True,       'minimal_display': False,
                'symmetric': {
                    'id':          rtype1b.id, 'predicate':       rtype1b.predicate,
                    'is_copiable': False,      'minimal_display': True,
                },
            },
            rtype1_data,
        )
        self.assertEqual([ptype1.id], subject_ptypes1a)
        self.assertEqual([ptype2.id], object_ptypes1a)

        # --
        rtype2_data = loaded_rtypes.get(rtype2a.id)

        with self.assertNoException():
            subject_ctypes2a = {*rtype2_data.pop('subject_ctypes')}
            object_ctypes2a  = rtype2_data.pop('object_ctypes')

        self.assertEqual(
            {
                'id': rtype2a.id,     'predicate':       rtype2a.predicate,
                'is_copiable': False, 'minimal_display': True,
                'symmetric': {
                    'id':          rtype2b.id, 'predicate':       rtype2b.predicate,
                    'is_copiable': True,       'minimal_display': False,
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
        self.login(is_staff=True)

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
        self.login(is_staff=True)

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
                    'choices': [eval1.value, eval2.value],
                }, {
                    'uuid': str(cfield4.uuid), 'ctype': ct_str1,
                    'name': cfield4.name, 'type': cfield4.field_type,
                    'choices': [eval3.value, eval4.value],
                },
            ],
            loaded_cfields,
        )

    def test_headerfilters(self):
        # self.maxDiff = None
        self.login(is_staff=True)
        other_user = self.other_user

        self.assertTrue(HeaderFilter.objects.filter(is_custom=False))
        self.assertFalse(HeaderFilter.objects.filter(is_custom=True))

        cfield = CustomField.objects.create(
            name='Rating', field_type=CustomField.INT, content_type=FakeContact,
        )

        create_hf = HeaderFilter.objects.create_if_needed
        hf1 = create_hf(
            pk='creme_config_export-test_export_headerfilters01',
            model=FakeContact, name='Contact view',
            is_custom=True,
            cells_desc=[
                (EntityCellRegularField, {'name': 'last_name'}),
                (EntityCellRegularField, {'name': 'first_name'}),
                EntityCellCustomField(cfield),
            ],
        )
        hf2 = create_hf(
            pk='creme_config_export-test_export_headerfilters02',
            model=FakeOrganisation, name='Organisation view',
            is_custom=True,
            user=other_user,
            cells_desc=[
                (EntityCellRegularField, {'name': 'name'}),
                (EntityCellRegularField, {'name': 'description'}),
            ],
        )
        hf3 = create_hf(
            pk='creme_config_export-test_export_headerfilters03',
            model=FakeOrganisation, name='Private organisation view',
            is_custom=True,
            user=other_user, is_private=True,
            cells_desc=[(EntityCellRegularField, {'name': 'name'})],
        )

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
            loaded_hfilters.get(hf1.id)
        )
        self.assertDictEqual(
            {
                'id': hf2.id,
                'name': hf2.name,
                'ctype': 'creme_core.fakeorganisation',
                'user': other_user.username,
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
                'user': other_user.username,
                'is_private': True,
                'cells': [
                    {'type': EntityCellRegularField.type_id, 'value': 'name'},
                ],
            },
            loaded_hfilters.get(hf3.id),
        )

    def test_entityfilters(self):
        user = self.login(is_staff=True)
        other_user = self.other_user

        self.assertTrue(EntityFilter.objects.filter(is_custom=False))
        self.assertFalse(EntityFilter.objects.filter(is_custom=True))

        ct_contact = ContentType.objects.get_for_model(FakeContact)
        contact = user.linked_contact

        create_cfield = partial(CustomField.objects.create, content_type=FakeContact)
        cfield1 = create_cfield(name='Rating', field_type=CustomField.INT)
        cfield2 = create_cfield(name='Party',  field_type=CustomField.DATETIME)

        ptype = CremePropertyType.objects.create(
            pk='creme_config_export-test_export_entityfilters', text='Sugoi !',
        )
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
                'filter_type': EF_USER,
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
                'filter_type': EF_USER,
                'user':  other_user.username,
                'use_or': True,
                'conditions': [
                    {
                        'type':  PropertyConditionHandler.type_id,
                        'name':  ptype.id,
                        'value': True,
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
                        'value': {'has': True, 'entity_uuid': str(contact.uuid)},
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
                'filter_type': EF_USER,
                'user':  other_user.username,
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
            },
            loaded_efilters.get(ef3.id),
        )

    def test_customforms01(self):
        self.login(is_staff=True)

        response = self.assertGET200(self.URL)
        content = response.json()

        with self.assertNoException():
            # loaded_cforms = {d['id']: d for d in content.get('custom_forms')}
            loaded_cforms = {d['descriptor']: d for d in content.get('custom_forms')}

        # self.maxDiff = None
        descriptor_id = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM.id
        self.assertDictEqual(
            {
                # 'id': cform_id,
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
                ],
            },
            loaded_cforms.get(descriptor_id),
        )

    def test_customforms02(self):
        self.login(is_staff=True)

        desc = fake_custom_forms.FAKEORGANISATION_CREATION_CFORM
        # cform_id = desc.id
        descriptor_id = desc.id
        # CustomFormConfigItem.objects.filter(cform_id=cform_id).delete()
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
            role=self.role,
        )

        response = self.assertGET200(self.URL)
        content = response.json()

        loaded_cforms = defaultdict(list)

        with self.assertNoException():
            # loaded_cforms = {d['id']: d for d in content.get('custom_forms')}
            for d in content.get('custom_forms'):
                loaded_cforms[d['descriptor']].append(d)

        # self.maxDiff = None
        # self.assertDictEqual(
        #     {
        #         'id': cform_id,
        #         'groups': [
        #             {
        #                 'name':  gname1,
        #                 'layout':  LAYOUT_DUAL_FIRST,
        #                 'cells': [
        #                     {'type': EntityCellRegularField.type_id, 'value': 'user'},
        #                     {'type': EntityCellRegularField.type_id, 'value': 'name'},
        #                     {'type': EntityCellCustomField.type_id,  'value': str(cfield.uuid)},
        #                     {
        #                         'type': EntityCellCustomFormSpecial.type_id,
        #                         'value': EntityCellCustomFormSpecial.REMAINING_REGULARFIELDS,
        #                     },
        #                 ],
        #             },
        #             {
        #                 'group_id': FakeAddressGroup.extra_group_id,
        #                 'layout': LAYOUT_DUAL_SECOND,
        #             },
        #         ],
        #     },
        #     loaded_cforms.get(cform_id),
        # )
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
                    'role': self.role.name,
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
