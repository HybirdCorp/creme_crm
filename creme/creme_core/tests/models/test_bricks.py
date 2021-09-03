# -*- coding: utf-8 -*-

from functools import partial
from json import loads as jsonloads

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import ProtectedError
from django.utils.translation import gettext as _

from creme.creme_core import setting_keys
from creme.creme_core.bricks import (
    CustomFieldsBrick,
    HistoryBrick,
    PropertiesBrick,
    RelationsBrick,
)
from creme.creme_core.core.entity_cell import (
    EntityCellFunctionField,
    EntityCellRegularField,
)
from creme.creme_core.gui.bricks import Brick
from creme.creme_core.models import (
    BrickDetailviewLocation,
    BrickHomeLocation,
    BrickMypageLocation,
    BrickState,
    CremeEntity,
    CustomBrickConfigItem,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    InstanceBrickConfigItem,
    RelationBrickItem,
    RelationType,
    SettingValue,
    UserRole,
)

from ..base import CremeTestCase


class BrickTestCase(CremeTestCase):
    class TestBrick01(Brick):
        id_ = Brick.generate_id('creme_core', 'test_models_bricks01')
        verbose_name = 'First test block'

    class TestBrick02(Brick):
        id_ = Brick.generate_id('creme_core', 'test_models_bricks02')
        verbose_name = 'Second test block'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._bdl_backup = [*BrickDetailviewLocation.objects.all()]
        cls._bpl_backup = [*BrickHomeLocation.objects.all()]
        cls._bml_backup = [*BrickMypageLocation.objects.all()]

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        BrickDetailviewLocation.objects.all().delete()
        BrickHomeLocation.objects.all().delete()
        BrickMypageLocation.objects.all().delete()

        for model, backup in [
            (BrickDetailviewLocation, cls._bdl_backup),
            (BrickHomeLocation, cls._bpl_backup),
            (BrickMypageLocation, cls._bml_backup),
        ]:
            try:
                model.objects.bulk_create(backup)
            except Exception as e:
                print(f'BrickTestCase: test-data backup problem with model={model} ({e})')

    def test_populate(self):
        self.assertLessEqual(
            {
                'modelblock', CustomFieldsBrick.id_, RelationsBrick.id_,
                PropertiesBrick.id_, HistoryBrick.id_,
            },
            {loc.brick_id for loc in self._bdl_backup},
        )
        brick_id = HistoryBrick.id_
        self.assertIn(brick_id, {bpl.brick_id for bpl in self._bpl_backup})
        self.assertIn(brick_id, {bml.brick_id for bml in self._bml_backup if bml.user is None})

    def test_detail_manager_create_if_needed01(self):
        "Default configuration + brick ID."
        order = 25
        zone = BrickDetailviewLocation.TOP
        brick_id = self.TestBrick01.id_

        loc = BrickDetailviewLocation.objects.create_if_needed(
            brick=brick_id, order=order, zone=zone,
        )
        self.assertIsInstance(loc, BrickDetailviewLocation)

        loc = self.get_object_or_fail(BrickDetailviewLocation, pk=loc.pk)
        self.assertIsNone(loc.content_type)
        self.assertEqual(brick_id, loc.brick_id)
        self.assertEqual(order,    loc.order)
        self.assertEqual(zone,     loc.zone)

    def test_detail_manager_create_if_needed02(self):
        "For a model + brick class."
        self.assertFalse(BrickDetailviewLocation.objects.filter_for_model(FakeContact))

        order = 4
        zone = BrickDetailviewLocation.LEFT
        TestBrick = self.TestBrick02
        loc = BrickDetailviewLocation.objects.create_if_needed(
            brick=TestBrick, order=order, zone=zone, model=FakeContact,
        )

        loc = self.refresh(loc)
        self.assertEqual(FakeContact, loc.content_type.model_class())
        self.assertEqual(TestBrick.id_, loc.brick_id)
        self.assertEqual(order,         loc.order)
        self.assertEqual(zone,          loc.zone)

        self.assertListEqual(
            [loc],
            [*BrickDetailviewLocation.objects.filter_for_model(FakeContact)],
        )

    def test_detail_manager_create_if_needed03(self):
        "Do not create if already exists (in any zone/order)."
        brick_id = self.TestBrick01.id_
        order = 5
        zone = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=brick_id, model=FakeContact,
        )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4, zone=BrickDetailviewLocation.LEFT)

        locs = BrickDetailviewLocation.objects.filter(
            brick_id=brick_id,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

    def test_detail_manager_create_if_needed04(self):
        "For a Role + ContentType instance."
        role = UserRole.objects.create(name='Viewer')
        ctype = ContentType.objects.get_for_model(FakeContact)

        brick_id = PropertiesBrick.id_
        order = 5
        zone = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=brick_id, model=ctype, role=role,
        )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4,     zone=BrickDetailviewLocation.LEFT)

        locs = BrickDetailviewLocation.objects.filter(
            brick_id=brick_id,
            content_type=ctype,
            role=role, superuser=False,
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

        # Do not avoid default configuration creation
        count = BrickDetailviewLocation.objects.count()
        zone = BrickDetailviewLocation.BOTTOM
        loc = create_bdl(order=order, zone=zone, role=None)
        self.assertEqual(count + 1, BrickDetailviewLocation.objects.count())
        self.assertEqual(zone,  loc.zone)
        self.assertIsNone(loc.role)
        self.assertFalse(loc.superuser)

    def test_detail_manager_create_if_needed05(self):
        "For super-users."
        MyBrick = self.TestBrick01
        order = 5
        zone = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=MyBrick, model=FakeContact, role='superuser',
        )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4, zone=BrickDetailviewLocation.LEFT)

        locs = BrickDetailviewLocation.objects.filter(
            brick_id=MyBrick.id_,
            content_type=ContentType.objects.get_for_model(FakeContact),
            role=None, superuser=True,
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

        # Do not avoid default configuration creation
        count = BrickDetailviewLocation.objects.count()
        zone = BrickDetailviewLocation.BOTTOM
        loc = create_bdl(order=order, zone=zone, role=None)
        self.assertEqual(count + 1, BrickDetailviewLocation.objects.count())
        self.assertEqual(zone,  loc.zone)
        self.assertIsNone(loc.role)
        self.assertFalse(loc.superuser)

    def test_detail_manager_create_if_needed06(self):
        "Default configuration cannot have a related role."
        with self.assertRaises(ValueError):
            BrickDetailviewLocation.objects.create_if_needed(
                brick=self.TestBrick01,
                order=5, zone=BrickDetailviewLocation.RIGHT,
                model=None, role='superuser',  # <==
            )

    def test_detail_manager_create_for_model_brick01(self):
        order = 5
        zone = BrickDetailviewLocation.RIGHT
        model = FakeContact
        loc = BrickDetailviewLocation.objects.create_for_model_brick(
            order=order, zone=zone, model=model,
        )

        self.assertEqual(1, BrickDetailviewLocation.objects.count())

        loc = self.get_object_or_fail(BrickDetailviewLocation, pk=loc.id)
        self.assertEqual('modelblock', loc.brick_id)
        self.assertEqual(model,        loc.content_type.model_class())
        self.assertEqual(order,        loc.order)
        self.assertEqual(zone,         loc.zone)

    def test_detail_manager_create_for_model_brick02(self):
        "model = None."
        loc = BrickDetailviewLocation.objects.create_for_model_brick(
            order=8, zone=BrickDetailviewLocation.BOTTOM, model=None,
        )
        self.assertEqual(1, BrickDetailviewLocation.objects.count())
        self.assertEqual('modelblock', loc.brick_id)
        self.assertIsNone(loc.content_type)

    def test_detail_manager_create_for_model_brick03(self):
        "With a Role."
        role = UserRole.objects.create(name='Viewer')
        loc = BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, role=role,
            order=8, zone=BrickDetailviewLocation.BOTTOM,
        )
        self.assertEqual(1, BrickDetailviewLocation.objects.count())
        self.assertEqual('modelblock', loc.brick_id)
        self.assertEqual(role,         loc.role)

    def test_detail_manager_multi_create01(self):
        order1 = 25
        order2 = 50
        order3 = 75
        zone1 = BrickDetailviewLocation.LEFT
        zone2 = BrickDetailviewLocation.RIGHT
        zone3 = BrickDetailviewLocation.BOTTOM
        locs = BrickDetailviewLocation.objects.multi_create(
            data=[
                {'brick': self.TestBrick01.id_, 'order': order1, 'zone': zone1},
                {'brick': self.TestBrick02,     'order': order2, 'zone': zone2},
                {'order': order3, 'zone': zone3},
            ],
        )
        self.assertIsList(locs, length=3)

        loc1 = locs[0]
        self.assertIsInstance(loc1, BrickDetailviewLocation)
        self.assertIsNotNone(loc1.pk)

        loc1 = self.refresh(loc1)
        self.assertIsNone(loc1.content_type)
        self.assertIsNone(loc1.role)
        self.assertFalse(loc1.superuser)
        self.assertEqual(self.TestBrick01.id_, loc1.brick_id)
        self.assertEqual(order1,               loc1.order)
        self.assertEqual(zone1,                loc1.zone)

        loc2 = locs[1]
        self.assertIsNone(loc2.content_type)
        self.assertEqual(self.TestBrick02.id_, loc2.brick_id)
        self.assertEqual(order2,               loc2.order)
        self.assertEqual(zone2,                loc2.zone)

        loc3 = locs[2]
        self.assertIsNone(loc3.content_type)
        self.assertIsNone(loc3.role)
        self.assertFalse(loc3.superuser)
        self.assertEqual('modelblock', loc3.brick_id)
        self.assertEqual(order3,       loc3.order)
        self.assertEqual(zone3,        loc3.zone)

    def test_detail_manager_multi_create02(self):
        "<defaults> argument."
        order1 = 25
        order2 = 50
        zone1 = BrickDetailviewLocation.LEFT
        zone2 = BrickDetailviewLocation.RIGHT
        locs = BrickDetailviewLocation.objects.multi_create(
            defaults={'model': FakeContact, 'role': 'superuser', 'zone': zone1},
            data=[
                {'brick': self.TestBrick01.id_, 'order': order1},
                {'order': order2, 'zone': zone2},
            ],
        )
        self.assertIsList(locs, length=2)

        loc1 = locs[0]
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertEqual(ct, loc1.content_type)
        self.assertIsNone(loc1.role)
        self.assertTrue(loc1.superuser)
        self.assertEqual(self.TestBrick01.id_, loc1.brick_id)
        self.assertEqual(order1,               loc1.order)
        self.assertEqual(zone1,                loc1.zone)

        loc2 = locs[1]
        self.assertEqual(ct, loc1.content_type)
        self.assertIsNone(loc2.role)
        self.assertTrue(loc2.superuser)
        self.assertEqual('modelblock', loc2.brick_id)
        self.assertEqual(order2,       loc2.order)
        self.assertEqual(zone2,        loc2.zone)

    def test_detail_manager_multi_create03(self):
        "'brick' in <defaults> argument."
        order1 = 25
        order2 = 50
        zone = BrickDetailviewLocation.LEFT
        locs = BrickDetailviewLocation.objects.multi_create(
            defaults={'brick': self.TestBrick01.id_, 'zone': zone},
            data=[
                {'model': FakeContact,      'order': order1},
                {'model': FakeOrganisation, 'order': order2},
            ],
        )
        self.assertIsList(locs, length=2)

    def test_detail_str(self):
        TOP = BrickDetailviewLocation.TOP

        # Default
        loc1 = BrickDetailviewLocation.objects.create_if_needed(
            brick=RelationsBrick, order=25, zone=TOP,
        )
        self.assertEqual(
            _('Default block configuration for detail-views uses «{block}»').format(
                block=RelationsBrick.verbose_name,
            ),
            str(loc1),
        )

        # For a model
        loc2 = BrickDetailviewLocation.objects.create_if_needed(
            brick=RelationsBrick, order=25, zone=TOP, model=FakeContact,
        )
        self.assertEqual(
            _('Block configuration for detail-views of «{model}» uses «{block}»').format(
                model='Test Contact',
                block=RelationsBrick.verbose_name,
            ),
            str(loc2),
        )

        # For a role
        role = UserRole.objects.create(name='Viewer')
        loc3 = BrickDetailviewLocation.objects.create_if_needed(
            brick=RelationsBrick, order=25, zone=TOP,
            model=FakeContact, role=role,
        )
        self.assertEqual(
            _(
                'Block configuration for detail-views of «{model}» '
                'for role «{role}» uses «{block}»'
            ).format(
                model='Test Contact',
                role=role,
                block=RelationsBrick.verbose_name,
            ),
            str(loc3),
        )

        # For superusers
        loc4 = BrickDetailviewLocation.objects.create_if_needed(
            brick=PropertiesBrick, order=25, zone=TOP,
            model=FakeOrganisation, role='superuser',
        )
        self.assertEqual(
            _(
                'Block configuration for detail-views of «{model}» '
                'for superusers uses «{block}»'
            ).format(
                model='Test Organisation',
                block=PropertiesBrick.verbose_name,
            ),
            str(loc4),
        )

        # Unknown brick
        loc5 = BrickDetailviewLocation.objects.create_if_needed(
            brick='invalid', order=25, zone=TOP,
        )
        self.assertEqual(
            _('Default block configuration for detail-views uses «{block}»').format(
                block='BLOCK',
            ),
            str(loc5),
        )

    def test_home_str(self):
        loc1 = BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id_, order=1,
        )
        self.assertEqual(
            _('Block configuration of Home uses «{block}»').format(
                block=HistoryBrick.verbose_name,
            ),
            str(loc1),
        )

        # For role
        role = UserRole.objects.create(name='Viewer')
        loc2 = BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id_, order=1, role=role,
        )
        self.assertEqual(
            _('Block configuration of Home for role «{role}» uses «{block}»').format(
                role=role,
                block=HistoryBrick.verbose_name,
            ),
            str(loc2),
        )

        # For superusers
        loc3 = BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id_, order=1, superuser=True,
        )
        self.assertEqual(
            _('Block configuration of Home for superusers uses «{block}»').format(
                role=role,
                block=HistoryBrick.verbose_name,
            ),
            str(loc3),
        )

    def test_mypage_str(self):
        loc1 = BrickMypageLocation.objects.create(
            brick_id=HistoryBrick.id_, order=1,
        )
        self.assertEqual(
            _('Default block configuration of "My page" uses «{block}»').format(
                block=HistoryBrick.verbose_name,
            ),
            str(loc1),
        )

        # For user
        user = self.create_user()
        loc2 = BrickMypageLocation.objects.create(
            brick_id=HistoryBrick.id_, order=1, user=user,
        )
        self.assertEqual(
            _('Block configuration of "My page" for «{user}» uses «{block}»').format(
                user=user,
                block=HistoryBrick.verbose_name,
            ),
            str(loc2),
        )

    def test_mypage_new_user(self):
        brick_id = HistoryBrick.id_
        order = 3
        BrickMypageLocation.objects.create(brick_id=brick_id, order=order)

        user = get_user_model().objects.create(username='Kirika')
        user.set_password('password')
        user.save()
        self.get_object_or_fail(
            BrickMypageLocation,
            user=user, brick_id=brick_id, order=order,
        )

    def test_relation_brick01(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves'),
            ('test-object_loved',  'is loved by'),
        )[0]

        rbi = RelationBrickItem.objects.create_if_needed(rtype.id)
        self.assertIsInstance(rbi, RelationBrickItem)
        self.assertIsNotNone(rbi.pk)
        self.assertEqual(rtype.id, rbi.relation_type_id)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga = get_ct(FakeOrganisation)
        ct_img = get_ct(FakeImage)

        rbi = self.refresh(rbi)  # Test persistence
        self.assertIsNone(rbi.get_cells(ct_contact))
        self.assertIsNone(rbi.get_cells(ct_orga))
        self.assertIsNone(rbi.get_cells(ct_img))
        self.assertIs(rbi.all_ctypes_configured, False)

        rbi.set_cells(
            ct_contact,
            [
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellFunctionField.build(FakeContact, 'get_pretty_properties'),
            ],
        )
        rbi.set_cells(ct_orga, [EntityCellRegularField.build(FakeOrganisation, 'name')])
        rbi.save()

        rbi = self.refresh(rbi)  # Test persistence
        self.assertIsNone(rbi.get_cells(ct_img))
        self.assertIs(rbi.all_ctypes_configured, False)

        cells_contact = rbi.get_cells(ct_contact)
        self.assertEqual(2, len(cells_contact))

        cell_contact = cells_contact[0]
        self.assertIsInstance(cell_contact, EntityCellRegularField)
        self.assertEqual('last_name', cell_contact.value)

        cell_contact = cells_contact[1]
        self.assertIsInstance(cell_contact, EntityCellFunctionField)
        self.assertEqual('get_pretty_properties', cell_contact.value)

        self.assertEqual(1, len(rbi.get_cells(ct_orga)))

        # ---
        self.assertEqual(rbi, RelationBrickItem.objects.create_if_needed(rtype.id))

    def test_relation_brick02(self):
        "All ctypes configured + Relation instance."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_rented', 'is rented by'),
            ('test-object_rented',  'rents', [FakeContact, FakeOrganisation]),
        )[0]

        rbi = RelationBrickItem.objects.create_if_needed(rtype)
        self.assertIsInstance(rbi, RelationBrickItem)
        self.assertIsNotNone(rbi.pk)
        self.assertEqual(rtype.id, rbi.relation_type_id)

        get_ct = ContentType.objects.get_for_model

        rbi.set_cells(
            get_ct(FakeContact),
            [EntityCellRegularField.build(FakeContact, 'last_name')],
        )
        rbi.save()
        self.assertFalse(self.refresh(rbi).all_ctypes_configured)

        rbi.set_cells(
            get_ct(FakeOrganisation),
            [EntityCellRegularField.build(FakeOrganisation, 'name')]
        )
        rbi.save()
        self.assertTrue(self.refresh(rbi).all_ctypes_configured)

        # ---
        self.assertEqual(rbi, RelationBrickItem.objects.create_if_needed(rtype))

    def test_relation_brick_errors(self):
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_rented', 'is rented by'),
            ('test-object_rented',  'rents'),
        )[0]
        ct_contact = ContentType.objects.get_for_model(FakeContact)
        rbi = RelationBrickItem.objects.create_if_needed(rtype.id)

        build = partial(EntityCellRegularField.build, model=FakeContact)
        rbi.set_cells(
            ct_contact,
            [build(name='last_name'), build(name='description')],
        )
        rbi.save()

        # Inject error by bypassing checks
        RelationBrickItem.objects.filter(id=rbi.id).update(
            json_cells_map=rbi.json_cells_map.replace('description', 'invalid'),
        )

        rbi = self.refresh(rbi)
        cells_contact = rbi.get_cells(ct_contact)
        self.assertEqual(1, len(cells_contact))
        self.assertEqual('last_name', cells_contact[0].value)

        with self.assertNoException():
            deserialized = jsonloads(rbi.json_cells_map)

        self.assertDictEqual(
            {str(ct_contact.id): [{'type': 'regular_field', 'value': 'last_name'}]},
            deserialized,
        )

    def test_relationbrick_delete01(self):
        user = self.login()
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        rbi = RelationBrickItem.objects.create(brick_id='foobarid', relation_type=rt)

        create_state = partial(BrickState.objects.create, user=user)
        state1 = create_state(brick_id=rbi.brick_id)
        state2 = create_state(brick_id=self.TestBrick01.id_)

        rbi.delete()
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_relationbrick_delete02(self):
        "Cannot delete because it is used."
        self.login()
        rt = RelationType.objects.smart_update_or_create(
            ('test-subfoo', 'subject_predicate'),
            ('test-objfoo', 'object_predicate'),
            is_custom=False,
        )[0]
        rbi = RelationBrickItem.objects.create(brick_id='foobarid', relation_type=rt)

        def try_delete(msg, locs):
            with self.assertRaises(ProtectedError) as cm:
                rbi.delete()

            exc = cm.exception
            self.assertEqual(msg, exc.args[0])
            self.assertCountEqual(locs, exc.args[1])

            self.assertStillExists(rbi)

        create_dbl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=rbi.brick_id, order=5,
            zone=BrickDetailviewLocation.RIGHT,
        )
        loc1 = create_dbl(model=FakeContact, role=self.role)
        try_delete(
            _(
                'This block is used in the detail-view configuration of '
                '«{model}» for role «{role}»'
            ).format(model='Test Contact', role=self.role),
            [loc1],
        )
        self.assertStillExists(loc1)

        # ---
        loc2 = create_dbl(model=FakeContact, role='superuser')
        try_delete(
            _(
                'This block is used in the detail-view configuration of '
                '«{model}» for superusers'
            ).format(model='Test Contact'),
            [loc1, loc2],
        )
        self.assertStillExists(loc2)

        # ---
        loc3 = create_dbl(model=FakeContact)
        try_delete(
            _(
                'This block is used in the detail-view configuration of «{model}»'
            ).format(model='Test Contact'),
            [loc1, loc2, loc3],
        )
        self.assertStillExists(loc3)

        # ---
        loc4 = create_dbl()
        try_delete(
            _('This block is used in the default detail-view configuration'),
            [loc1, loc2, loc3, loc4],
        )
        self.assertStillExists(loc4)

    def test_custom_brick(self):
        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )
        # self.assertEqual(f'customblock-{cbci.id}', cbci.generate_id())
        self.assertEqual(f'customblock-{cbci.id}', cbci.brick_id)

        cells = self.refresh(cbci).cells
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('name', cell.value)

    def test_custom_brick_errors01(self):
        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRegularField.build(FakeOrganisation, 'description'),
            ],
        )

        # Inject error by bypassing checks
        CustomBrickConfigItem.objects.filter(id=cbci.id).update(
            json_cells=cbci.json_cells.replace('description', 'invalid'),
        )

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

        with self.assertNoException():
            deserialized = jsonloads(cbci.json_cells)

        self.assertListEqual(
            [{'type': 'regular_field', 'value': 'name'}],
            deserialized,
        )

    def test_custom_brick_errors02(self):
        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRegularField.build(FakeOrganisation, 'invalid'),
            ],
        )

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

    def test_custom_brick_delete01(self):
        self.login()
        cbci = CustomBrickConfigItem.objects.create(
            content_type=FakeContact, name='Info',
        )

        cbci.delete()
        self.assertDoesNotExist(cbci)

    def test_custom_brick_delete02(self):
        "Cannot delete because it is used."
        self.login()
        cbci = CustomBrickConfigItem.objects.create(
            content_type=FakeContact, name='Info',
        )
        loc = BrickDetailviewLocation.objects.create_if_needed(
            brick=cbci.brick_id, order=5,
            model=FakeContact,
            zone=BrickDetailviewLocation.RIGHT,
        )

        with self.assertRaises(ProtectedError) as cm:
            cbci.delete()

        exc = cm.exception
        self.assertEqual(
            _(
                'This block is used in the detail-view '
                'configuration of «{model}»'
            ).format(model='Test Contact'),
            exc.args[0]
        )
        self.assertCountEqual([loc], exc.args[1])

        self.assertStillExists(cbci)
        self.assertStillExists(loc)

    # NB: see reports for InstanceBrickConfigItem with a working Brick class
    def test_instance_brick01(self):
        user = self.create_user()

        class TestInstanceBrick(Brick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'invalid_id')

        brick_entity = CremeEntity.objects.create(user=user)
        ibi = InstanceBrickConfigItem(
            brick_class_id=TestInstanceBrick.id_,
            entity=brick_entity,
        )

        with self.assertRaises(ValueError):
            ibi.brick_id  # NOQA

        ibi.save()
        brick_id = f'instanceblock-{ibi.id}'
        self.assertEqual(brick_id, ibi.brick_id)

        id_from_brick_id = InstanceBrickConfigItem.id_from_brick_id
        self.assertEqual(ibi.id, id_from_brick_id(brick_id))
        self.assertIsNone(id_from_brick_id('invalid'))
        self.assertIsNone(id_from_brick_id(f'invalid-{ibi.id}'))
        self.assertIsNone(id_from_brick_id('instanceblock-notanint'))

        brick = ibi.brick
        self.assertIsInstance(brick, Brick)

        # Because the class is not registered
        self.assertFalse(isinstance(brick, TestInstanceBrick))

        self.assertEqual(brick_id, brick.id_)
        self.assertEqual('??', brick.verbose_name)

        errors = [_('Unknown type of block (bad uninstall ?)')]
        self.assertEqual(errors, getattr(brick, 'errors', None))
        # self.assertEqual(errors, ibi.errors)

    def test_instance_brick02(self):
        "Extra data."
        user = self.create_user()

        class TestInstanceBrick(Brick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'invalid_id')

        brick_entity = CremeEntity.objects.create(user=user)

        ibi = InstanceBrickConfigItem(
            brick_class_id=TestInstanceBrick.id_,
            entity=brick_entity,
        )
        self.assertIsNone(ibi.get_extra_data('key1'))

        ibi.set_extra_data(key='key1', value='value1')
        ibi.set_extra_data(key='key2', value='value2')
        ibi.save()

        ibi = self.refresh(ibi)
        self.assertEqual('value1', ibi.get_extra_data('key1'))
        self.assertEqual('value2', ibi.get_extra_data('key2'))
        self.assertIsNone(ibi.get_extra_data('key3'))

        self.assertDictEqual(
            {
                'key1': 'value1',
                'key2': 'value2',
            },
            dict(ibi.extra_data_items),
        )

    def test_instance_brick_delete01(self):
        user = self.login()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id_,
            entity=naru,
        )

        brick_id = ibi.brick_id

        create_state = BrickState.objects.create
        state1 = create_state(brick_id=brick_id,             user=user)
        state2 = create_state(brick_id=self.TestBrick02.id_, user=user)

        ibi.delete()
        self.assertDoesNotExist(ibi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_instance_brick_delete02(self):
        "Cannot delete because it is used by detail-view configuration."
        user = self.login()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id_,
            entity=naru,
        )
        loc = BrickDetailviewLocation.objects.create_if_needed(
            zone=BrickDetailviewLocation.RIGHT, model=FakeContact,
            brick=ibi.brick_id, order=5,
        )

        with self.assertRaises(ProtectedError) as cm:
            ibi.delete()

        exc = cm.exception
        self.assertEqual(
            _(
                'This block is used in the detail-view configuration '
                'of «{model}»'
            ).format(model='Test Contact'),
            exc.args[0]
        )
        self.assertEqual([loc], exc.args[1])

        self.assertStillExists(ibi)
        self.assertStillExists(loc)

    def test_instance_brick_delete03(self):
        "Cannot delete because it is used by home configuration."
        user = self.login()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id_,
            entity=naru,
        )

        def try_delete(msg, locs):
            with self.assertRaises(ProtectedError) as cm:
                ibi.delete()

            args = cm.exception.args
            self.assertEqual(msg, args[0])
            self.assertCountEqual(locs, args[1])

            self.assertStillExists(ibi)

        create_bhl = partial(
            BrickHomeLocation.objects.create,
            brick_id=ibi.brick_id, order=5,
        )
        loc1 = create_bhl(role=self.role)
        try_delete(
            _(
                'This block is used in the Home configuration of role «{}»'
            ).format(self.role),
            [loc1],
        )
        self.assertStillExists(loc1)

        # ------------------------
        loc2 = create_bhl(superuser=True)
        try_delete(
            _('This block is used in the Home configuration for superusers'),
            [loc1, loc2],
        )
        self.assertStillExists(loc2)

        # ------------------------
        loc3 = create_bhl()
        try_delete(
            _('This block is used in the default Home configuration'),
            [loc1, loc2, loc3],
        )
        self.assertStillExists(loc3)

    def test_instance_brick_delete04(self):
        """Cannot delete because it is used by "My Page" configuration."""
        user = self.login()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id_,
            entity=naru,
        )

        def try_delete(msg, locs):
            with self.assertRaises(ProtectedError) as cm:
                ibi.delete()

            args = cm.exception.args
            self.assertEqual(msg, args[0])
            self.assertCountEqual(locs, args[1])

            self.assertStillExists(ibi)

        create_bml = partial(
            BrickMypageLocation.objects.create,
            brick_id=ibi.brick_id, order=5,
        )
        loc1 = create_bml(user=user)
        try_delete(
            _(
                'This block is used in the configuration of «{}» for "My page"'
            ).format(user),
            [loc1],
        )
        self.assertStillExists(loc1)

        # ------------------------
        loc2 = create_bml()
        try_delete(
            _('This block is used in the default configuration for "My page"'),
            [loc1, loc2],
        )
        self.assertStillExists(loc2)

    def test_brick_state_manager_get_for_brick_id01(self):
        "State does not exist in DB."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_state01')

        # Not used (other user)
        BrickState.objects.create(
            user=user2,
            brick_id=TestBrick.id_,
            is_open=True,
            show_empty_fields=False,
        )

        with self.assertNumQueries(2):  # try to retrieve state + SettingValues
            state = BrickState.objects.get_for_brick_id(user=user1, brick_id=TestBrick.id_)

        self.assertIsInstance(state, BrickState)
        self.assertEqual(user1, state.user)
        self.assertIs(state.is_open,           True)
        self.assertIs(state.show_empty_fields, True)
        self.assertIsNone(state.pk)

    def test_brick_state_manager_get_for_brick_id02(self):
        "State stored in DB."
        user = self.create_user()

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_state02')

        state = BrickState.objects.create(
            user=user,
            brick_id=TestBrick.id_,
            is_open=True,
            show_empty_fields=False,
        )

        with self.assertNumQueries(1):
            stored_state = BrickState.objects.get_for_brick_id(
                user=user,
                brick_id=TestBrick.id_,
            )

        self.assertEqual(state, stored_state)

    def test_brick_state_manager_get_for_brick_id03(self):
        "Other value for SettingValues."
        user = self.create_user()

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_state03')

        sv_open = SettingValue.objects.get_4_key(setting_keys.block_opening_key)
        sv_open.value = False
        sv_open.save()

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TestBrick.id_)
        self.assertFalse(state.is_open)
        self.assertTrue(state.show_empty_fields)

        # ---
        sv_show = SettingValue.objects.get_4_key(setting_keys.block_showempty_key)
        sv_show.value = False
        sv_show.save()

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TestBrick.id_)
        self.assertFalse(state.is_open)
        self.assertFalse(state.show_empty_fields)

    def test_brick_state_extra_data(self):
        user = self.create_user()

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_state_extra')

        state = BrickState.objects.create(user=user, brick_id=TestBrick.id_)
        key1 = 'creme_core-foo'
        self.assertIsNone(state.get_extra_data(key1))
        self.assertIs(True, state.get_extra_data(key1, default=True))

        foo_value = 'bar'
        changed1 = state.set_extra_data(key1, foo_value)
        self.assertIs(changed1, True)

        state.save()
        state = self.refresh(state)
        self.assertEqual(foo_value, state.get_extra_data(key1))

        # ---
        key2 = 'creme_core-baz'
        self.assertIsNone(state.get_extra_data(key2))

        baz_value = 1
        changed2 = state.set_extra_data(key2, baz_value)
        self.assertIs(changed2, True)

        state.save()

        get_extra_data2 = self.refresh(state).get_extra_data
        self.assertEqual(foo_value, get_extra_data2(key1))
        self.assertEqual(baz_value, get_extra_data2(key2))

        # ---
        changed3 = state.set_extra_data(key2, baz_value)
        self.assertIs(changed3, False)

        # del_extra_data ---
        state.del_extra_data(key2)
        state.save()

        get_extra_data3 = self.refresh(state).get_extra_data
        self.assertEqual(foo_value, get_extra_data3(key1))
        self.assertIsNone(get_extra_data3(key2))

    def test_brick_state_manager_get_for_brick_ids01(self):
        "States do not exist in DB."
        user = self.create_user()

        class TestBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_states01_01')

        class TestBrick2(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_states01_02')

        with self.assertNumQueries(2):
            states = BrickState.objects.get_for_brick_ids(
                user=user,
                brick_ids=[TestBrick1.id_, TestBrick2.id_],
            )

        self.assertIsInstance(states, dict)
        self.assertEqual(2, len(states))

        state1 = states.get(TestBrick1.id_)
        self.assertIsInstance(state1, BrickState)
        self.assertEqual(user, state1.user)
        self.assertIs(state1.is_open,           True)
        self.assertIs(state1.show_empty_fields, True)
        self.assertIsNone(state1.pk)

        state2 = states.get(TestBrick2.id_)
        self.assertIsInstance(state2, BrickState)
        self.assertEqual(user, state2.user)
        self.assertIs(state2.is_open,           True)
        self.assertIs(state2.show_empty_fields, True)
        self.assertIsNone(state2.pk)

    def test_brick_state_manager_get_for_brick_ids02(self):
        "A state is stored in DB."
        user1 = self.create_user(index=0)
        user2 = self.create_user(index=1)

        class TestBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_states02_01')

        class TestBrick2(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_states02_02')

        stored_state1 = BrickState.objects.create(
            user=user1,
            brick_id=TestBrick1.id_,
            is_open=False,
            show_empty_fields=True,
        )
        BrickState.objects.create(
            user=user2,  # <== not used
            brick_id=TestBrick2.id_,
            is_open=True,
            show_empty_fields=False,
        )

        states = BrickState.objects.get_for_brick_ids(
            user=user1,
            brick_ids=[TestBrick1.id_, TestBrick2.id_],
        )
        self.assertIsInstance(states, dict)
        self.assertEqual(2, len(states))
        self.assertEqual(stored_state1, states.get(TestBrick1.id_))

        state2 = states.get(TestBrick2.id_)
        self.assertIsNone(state2.pk)

        # ---
        with self.assertNumQueries(1):
            BrickState.objects.get_for_brick_ids(
                user=user1, brick_ids=[TestBrick1.id_],
            )

    def test_brick_state_manager_get_for_brick_ids03(self):
        "Other value for SettingValues."
        user = self.create_user()

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_models_states03')

        sv_open = SettingValue.objects.get_4_key(setting_keys.block_opening_key)
        sv_open.value = False
        sv_open.save()

        states = BrickState.objects.get_for_brick_ids(
            user=user,
            brick_ids=[TestBrick.id_],
        )
        self.assertEqual(1, len(states))

        state = states.get(TestBrick.id_)
        self.assertFalse(state.is_open)
        self.assertTrue(state.show_empty_fields)

        # ---
        sv_show = SettingValue.objects.get_4_key(setting_keys.block_showempty_key)
        sv_show.value = False
        sv_show.save()

        states = BrickState.objects.get_for_brick_ids(user=user, brick_ids=[TestBrick.id_])
        self.assertEqual(1, len(states))

        state = states.get(TestBrick.id_)
        self.assertFalse(state.is_open)
        self.assertFalse(state.show_empty_fields)
