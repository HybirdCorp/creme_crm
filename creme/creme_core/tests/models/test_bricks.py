from functools import partial
from uuid import UUID

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
    EntityCellCustomField,
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
    CustomField,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    InstanceBrickConfigItem,
    RelationBrickItem,
    RelationType,
    SettingValue,
)

from ..base import CremeTestCase
from ..fake_bricks import FakeOrganisationCardHatBrick


class BrickTestCase(CremeTestCase):
    class TestBrick01(Brick):
        id = Brick.generate_id('creme_core', 'test_models_bricks01')
        verbose_name = 'First test block'

    class TestBrick02(Brick):
        id = Brick.generate_id('creme_core', 'test_models_bricks02')
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
                'model', CustomFieldsBrick.id, RelationsBrick.id,
                PropertiesBrick.id, HistoryBrick.id,
            },
            {loc.brick_id for loc in self._bdl_backup},
        )
        brick_id = HistoryBrick.id
        self.assertIn(brick_id, {bpl.brick_id for bpl in self._bpl_backup})
        self.assertIn(brick_id, {bml.brick_id for bml in self._bml_backup if bml.user is None})

    def test_detail_manager_create_if_needed01(self):
        "Default configuration + brick ID."
        order = 25
        zone = BrickDetailviewLocation.TOP
        brick_id = self.TestBrick01.id

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
        self.assertEqual(FakeContact,  loc.content_type.model_class())
        self.assertEqual(TestBrick.id, loc.brick_id)
        self.assertEqual(order,        loc.order)
        self.assertEqual(zone,         loc.zone)

        self.assertListEqual(
            [loc],
            [*BrickDetailviewLocation.objects.filter_for_model(FakeContact)],
        )

    def test_detail_manager_create_if_needed03(self):
        "Do not create if already exists (in any zone/order)."
        brick_id = self.TestBrick01.id
        order = 5
        zone = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=brick_id, model=FakeContact,
        )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4, zone=BrickDetailviewLocation.LEFT)

        loc = self.get_alone_element(
            BrickDetailviewLocation.objects.filter(
                brick_id=brick_id,
                content_type=ContentType.objects.get_for_model(FakeContact),
            )
        )
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

    def test_detail_manager_create_if_needed04(self):
        "For a Role + ContentType instance."
        role = self.create_role(name='Viewer')
        ctype = ContentType.objects.get_for_model(FakeContact)

        brick_id = PropertiesBrick.id
        order = 5
        zone = BrickDetailviewLocation.RIGHT

        create_bdl = partial(
            BrickDetailviewLocation.objects.create_if_needed,
            brick=brick_id, model=ctype, role=role,
        )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4,     zone=BrickDetailviewLocation.LEFT)

        loc = self.get_alone_element(
            BrickDetailviewLocation.objects.filter(
                brick_id=brick_id,
                content_type=ctype,
                role=role, superuser=False,
            )
        )
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

        loc = self.get_alone_element(
            BrickDetailviewLocation.objects.filter(
                brick_id=MyBrick.id,
                content_type=ContentType.objects.get_for_model(FakeContact),
                role=None, superuser=True,
            )
        )
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
        self.assertEqual('model', loc.brick_id)
        self.assertEqual(model,   loc.content_type.model_class())
        self.assertEqual(order,   loc.order)
        self.assertEqual(zone,    loc.zone)

    def test_detail_manager_create_for_model_brick02(self):
        "model = None."
        loc = BrickDetailviewLocation.objects.create_for_model_brick(
            order=8, zone=BrickDetailviewLocation.BOTTOM, model=None,
        )
        self.assertEqual(1, BrickDetailviewLocation.objects.count())
        self.assertEqual('model', loc.brick_id)
        self.assertIsNone(loc.content_type)

    def test_detail_manager_create_for_model_brick03(self):
        "With a Role."
        role = self.create_role(name='Viewer')
        loc = BrickDetailviewLocation.objects.create_for_model_brick(
            model=FakeContact, role=role,
            order=8, zone=BrickDetailviewLocation.BOTTOM,
        )
        self.assertEqual(1, BrickDetailviewLocation.objects.count())
        self.assertEqual('model', loc.brick_id)
        self.assertEqual(role,    loc.role)

    def test_detail_manager_multi_create01(self):
        order1 = 25
        order2 = 50
        order3 = 75
        zone1 = BrickDetailviewLocation.LEFT
        zone2 = BrickDetailviewLocation.RIGHT
        zone3 = BrickDetailviewLocation.BOTTOM
        locs = BrickDetailviewLocation.objects.multi_create(
            data=[
                {'brick': self.TestBrick01.id, 'order': order1, 'zone': zone1},
                {'brick': self.TestBrick02,    'order': order2, 'zone': zone2},
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
        self.assertEqual(self.TestBrick01.id, loc1.brick_id)
        self.assertEqual(order1,              loc1.order)
        self.assertEqual(zone1,               loc1.zone)

        loc2 = locs[1]
        self.assertIsNone(loc2.content_type)
        self.assertEqual(self.TestBrick02.id, loc2.brick_id)
        self.assertEqual(order2,              loc2.order)
        self.assertEqual(zone2,               loc2.zone)

        loc3 = locs[2]
        self.assertIsNone(loc3.content_type)
        self.assertIsNone(loc3.role)
        self.assertFalse(loc3.superuser)
        self.assertEqual('model', loc3.brick_id)
        self.assertEqual(order3,  loc3.order)
        self.assertEqual(zone3,   loc3.zone)

    def test_detail_manager_multi_create02(self):
        "<defaults> argument."
        order1 = 25
        order2 = 50
        zone1 = BrickDetailviewLocation.LEFT
        zone2 = BrickDetailviewLocation.RIGHT
        locs = BrickDetailviewLocation.objects.multi_create(
            defaults={'model': FakeContact, 'role': 'superuser', 'zone': zone1},
            data=[
                {'brick': self.TestBrick01.id, 'order': order1},
                {'order': order2, 'zone': zone2},
            ],
        )
        self.assertIsList(locs, length=2)

        loc1 = locs[0]
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertEqual(ct, loc1.content_type)
        self.assertIsNone(loc1.role)
        self.assertTrue(loc1.superuser)
        self.assertEqual(self.TestBrick01.id, loc1.brick_id)
        self.assertEqual(order1,              loc1.order)
        self.assertEqual(zone1,               loc1.zone)

        loc2 = locs[1]
        self.assertEqual(ct, loc1.content_type)
        self.assertIsNone(loc2.role)
        self.assertTrue(loc2.superuser)
        self.assertEqual('model', loc2.brick_id)
        self.assertEqual(order2,  loc2.order)
        self.assertEqual(zone2,   loc2.zone)

    def test_detail_manager_multi_create03(self):
        "'brick' in <defaults> argument."
        order1 = 25
        order2 = 50
        zone = BrickDetailviewLocation.LEFT
        locs = BrickDetailviewLocation.objects.multi_create(
            defaults={'brick': self.TestBrick01.id, 'zone': zone},
            data=[
                {'model': FakeContact,      'order': order1},
                {'model': FakeOrganisation, 'order': order2},
            ],
        )
        self.assertIsList(locs, length=2)

    def test_detail_clone_for_role01(self):
        role = self.get_regular_role()
        src = BrickDetailviewLocation.objects.create(
            order=1, brick_id=self.TestBrick01.id, zone=BrickDetailviewLocation.LEFT,
        )
        clone = src.clone_for_role(role)
        self.assertIsInstance(clone, BrickDetailviewLocation)
        self.assertIsNone(clone.pk)
        self.assertIsNone(clone.id)
        self.assertEqual(src.brick_id, clone.brick_id)
        self.assertEqual(src.order,    clone.order)
        self.assertEqual(src.zone,     clone.zone)
        self.assertIsNone(clone.content_type)
        self.assertEqual(role, clone.role)
        self.assertFalse(clone.superuser)

    def test_detail_clone_for_role02(self):
        src = BrickDetailviewLocation.objects.create(
            order=2, brick_id=self.TestBrick02.id, zone=BrickDetailviewLocation.RIGHT,
            content_type=ContentType.objects.get_for_model(FakeContact),
            role=self.get_regular_role(),
        )
        clone = src.clone_for_role(None)
        self.assertEqual(src.brick_id,     clone.brick_id)
        self.assertEqual(src.order,        clone.order)
        self.assertEqual(src.zone,         clone.zone)
        self.assertEqual(src.content_type, clone.content_type)
        self.assertIsNone(clone.role)
        self.assertTrue(clone.superuser)

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
        role = self.create_role(name='Viewer')
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

        # Hat brick (generic)
        loc6 = BrickDetailviewLocation.objects.create_if_needed(
            brick=Brick.GENERIC_HAT_BRICK_ID,
            order=1, zone=BrickDetailviewLocation.HAT, model=FakeOrganisation,
        )
        self.assertEqual(
            _('Block configuration for detail-views of «{model}» uses «{block}»').format(
                model='Test Organisation', block=_('Title bar'),
            ),
            str(loc6),
        )

        # Hat brick (specific)
        loc7 = BrickDetailviewLocation.objects.create_if_needed(
            brick=FakeOrganisationCardHatBrick,
            order=1, zone=BrickDetailviewLocation.HAT, model=FakeOrganisation,
        )
        self.assertEqual(
            _('Block configuration for detail-views of «{model}» uses «{block}»').format(
                model='Test Organisation',
                block=FakeOrganisationCardHatBrick.verbose_name,
            ),
            str(loc7),
        )

    def test_home_str(self):
        loc1 = BrickHomeLocation.objects.create(brick_id=HistoryBrick.id, order=1)
        self.assertEqual(
            _('Block configuration of Home uses «{block}»').format(
                block=HistoryBrick.verbose_name,
            ),
            str(loc1),
        )

        # For role
        role = self.create_role(name='Viewer')
        loc2 = BrickHomeLocation.objects.create(
            brick_id=HistoryBrick.id, order=1, role=role,
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
            brick_id=HistoryBrick.id, order=1, superuser=True,
        )
        self.assertEqual(
            _('Block configuration of Home for superusers uses «{block}»').format(
                role=role,
                block=HistoryBrick.verbose_name,
            ),
            str(loc3),
        )

    def test_mypage_str(self):
        loc1 = BrickMypageLocation.objects.create(brick_id=HistoryBrick.id, order=1)
        self.assertEqual(
            _('Default block configuration of "My page" uses «{block}»').format(
                block=HistoryBrick.verbose_name,
            ),
            str(loc1),
        )

        # For user
        user = self.get_root_user()
        loc2 = BrickMypageLocation.objects.create(
            brick_id=HistoryBrick.id, order=1, user=user,
        )
        self.assertEqual(
            _('Block configuration of "My page" for «{user}» uses «{block}»').format(
                user=user,
                block=HistoryBrick.verbose_name,
            ),
            str(loc2),
        )

    def test_mypage_new_user(self):
        brick_id = HistoryBrick.id
        order = 3
        BrickMypageLocation.objects.create(brick_id=brick_id, order=order)

        user = self.create_user()
        self.get_object_or_fail(
            BrickMypageLocation,
            user=user, brick_id=brick_id, order=order,
        )

    def test_relation_brick01(self):
        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(
            id='test-object_loved', predicate='is loved by',
        ).get_or_create()[0]

        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=FakeContact,
        )

        rbi = RelationBrickItem.objects.create(relation_type=rtype)
        self.assertIsInstance(rbi, RelationBrickItem)
        self.assertIsNotNone(rbi.pk)
        self.assertIsInstance(rbi.uuid, UUID)
        self.assertEqual(rtype.id, rbi.relation_type_id)
        self.assertDictEqual({}, rbi.json_cells_map)

        brick_id = f'rtype-{rbi.uuid}'
        self.assertEqual(brick_id, rbi.brick_id)

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
                EntityCellCustomField(customfield=cfield),
            ],
        )
        rbi.set_cells(ct_orga, [EntityCellRegularField.build(FakeOrganisation, 'name')])
        rbi.save()
        self.assertDictEqual(
            {
                'creme_core.fakecontact': [
                    {'type': 'regular_field', 'value': 'last_name'},
                    {'type': 'function_field', 'value': 'get_pretty_properties'},
                    {'type': 'custom_field', 'value': str(cfield.uuid)},
                ],
                'creme_core.fakeorganisation': [{'type': 'regular_field', 'value': 'name'}],
            },
            rbi.json_cells_map,
        )

        rbi = self.refresh(rbi)  # Test persistence
        self.assertIsNone(rbi.get_cells(ct_img))
        self.assertIs(rbi.all_ctypes_configured, False)
        self.assertListEqual(
            [
                EntityCellRegularField.build(FakeContact, 'last_name'),
                EntityCellFunctionField.build(FakeContact, 'get_pretty_properties'),
                EntityCellCustomField(customfield=cfield),
            ],
            rbi.get_cells(ct_contact),
        )
        self.assertListEqual(
            [EntityCellRegularField.build(FakeOrganisation, 'name')],
            rbi.get_cells(ct_orga),
        )

    def test_relation_brick02(self):
        "All ctypes configured + Relation instance."
        rtype = RelationType.objects.builder(
            id='test-subject_rented', predicate='is rented by',
        ).symmetric(
            id='test-object_rented', predicate='rents',
            models=[FakeContact, FakeOrganisation],
        ).get_or_create()[0]
        rbi = RelationBrickItem.objects.get_or_create(relation_type=rtype)[0]
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

    def test_relation_brick_errors(self):
        rtype = RelationType.objects.builder(
            id='test-subject_rented', predicate='is rented by',
        ).symmetric(
            id='test-object_rented', predicate='rents',
        ).get_or_create()[0]
        ct_contact = ContentType.objects.get_for_model(FakeContact)
        rbi = RelationBrickItem.objects.create(relation_type=rtype)

        build = partial(EntityCellRegularField.build, model=FakeContact)
        rbi.set_cells(
            ct_contact,
            [build(name='last_name'), build(name='description')],
        )
        rbi.save()

        # Inject error by bypassing checks
        invalid_info = rbi.json_cells_map
        invalid_info['creme_core.fakecontact'][1]['value'] = 'invalid'
        rbi.json_cells_map = invalid_info
        rbi.save()

        rbi = self.refresh(rbi)
        cell_contact = self.get_alone_element(rbi.get_cells(ct_contact))
        self.assertEqual('last_name', cell_contact.value)

        with self.assertNoException():
            deserialized = rbi.json_cells_map

        self.assertDictEqual(
            {'creme_core.fakecontact': [{'type': 'regular_field', 'value': 'last_name'}]},
            deserialized,
        )

    def test_relationbrick_delete01(self):
        user = self.get_root_user()
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject_predicate',
            is_custom=False,
        ).symmetric(
            id='test-objfoo', predicate='object_predicate',
        ).get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rt)

        create_state = partial(BrickState.objects.create, user=user)
        state1 = create_state(brick_id=rbi.brick_id)
        state2 = create_state(brick_id=self.TestBrick01.id)

        rbi.delete()
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_relationbrick_delete02(self):
        "Cannot delete because it is used."
        rt = RelationType.objects.builder(
            id='test-subfoo', predicate='subject predicate',
            is_custom=False,
        ).symmetric(id='test-objfoo', predicate='object predicate').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rt)

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
        role = self.create_role(name='Test')
        loc1 = create_dbl(model=FakeContact, role=role)
        try_delete(
            _(
                'This block is used in the detail-view configuration of '
                '«{model}» for role «{role}»'
            ).format(model='Test Contact', role=role),
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

    def test_relation_brick_manager(self):
        rtype1 = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loved', predicate='is loved by').get_or_create()[0]
        rtype2 = rtype1.symmetric_type
        rtype3 = RelationType.objects.builder(
            id='test-subject_likes', predicate='likes',
        ).symmetric(id='test-object_liked', predicate='is liked by').get_or_create()[0]

        create_rbi = RelationBrickItem.objects.create
        rbi1 = create_rbi(relation_type=rtype1)
        rbi2 = create_rbi(relation_type=rtype2)
        rbi3 = create_rbi(relation_type=rtype3)

        self.assertCountEqual(
            [rbi1, rbi3],
            [
                *RelationBrickItem.objects.for_brick_ids([
                    rbi1.brick_id,
                    'invalid',
                    f'invalid-{rbi2.uuid}',
                    'rtype-notauuid',
                    rbi3.brick_id,
                ]),
            ],
        )

        # ---
        with self.assertNumQueries(0):
            count = len(RelationBrickItem.objects.for_brick_ids(['invalid']))
        self.assertEqual(0, count)

    def test_custom_brick(self):
        model = FakeOrganisation
        fname = 'name'
        cfield = CustomField.objects.create(
            name='Size (cm)',
            field_type=CustomField.INT,
            content_type=model,
        )
        cbci = CustomBrickConfigItem.objects.create(
            name='General', content_type=model,
            cells=[
                EntityCellRegularField.build(model, fname),
                EntityCellCustomField(customfield=cfield),
            ],
        )
        self.assertEqual(f'custom-{cbci.uuid}', cbci.brick_id)
        self.assertEqual(
            [
                {'type': 'regular_field', 'value': fname},
                {'type': 'custom_field', 'value': str(cfield.uuid)},
            ],
            cbci.json_cells,
        )

        self.assertListEqual(
            [
                EntityCellRegularField.build(model, fname),
                EntityCellCustomField(customfield=cfield),
            ],
            self.refresh(cbci).cells,
        )

    def test_custom_brick_errors01(self):
        cbci = CustomBrickConfigItem.objects.create(
            name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRegularField.build(FakeOrganisation, 'description'),
            ],
        )

        # Inject error by bypassing checks
        invalid_info = cbci.json_cells
        invalid_info[1]['value'] = 'invalid'
        cbci.json_cells = invalid_info
        cbci.save()

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

        with self.assertNoException():
            deserialized = cbci.json_cells

        self.assertListEqual(
            [{'type': 'regular_field', 'value': 'name'}],
            deserialized,
        )

    def test_custom_brick_errors02(self):
        cbci = CustomBrickConfigItem.objects.create(
            name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRegularField.build(FakeOrganisation, 'invalid'),
            ],
        )

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

    def test_custom_brick_delete01(self):
        cbci = CustomBrickConfigItem.objects.create(
            content_type=FakeContact, name='Info',
        )

        cbci.delete()
        self.assertDoesNotExist(cbci)

    def test_custom_brick_delete02(self):
        "Cannot delete because it is used."
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
            exc.args[0],
        )
        self.assertCountEqual([loc], exc.args[1])

        self.assertStillExists(cbci)
        self.assertStillExists(loc)

    def test_custom_brick_manager(self):
        create_cdbci = partial(
            CustomBrickConfigItem.objects.create, content_type=FakeContact,
        )
        cbci1 = create_cdbci(name='Info #1')
        cbci2 = create_cdbci(name='Info #2')
        cbci3 = create_cdbci(name='Info #3')

        self.assertCountEqual(
            [cbci1, cbci3],
            [
                *CustomBrickConfigItem.objects.for_brick_ids([
                    cbci1.brick_id,
                    'invalid',
                    f'invalid-{cbci2.uuid}',
                    'custom-notauuid',
                    cbci3.brick_id,
                ]),
            ],
        )

        # ---
        with self.assertNumQueries(0):
            count = len(CustomBrickConfigItem.objects.for_brick_ids(['invalid']))
        self.assertEqual(0, count)

    # NB: see reports for InstanceBrickConfigItem with a working Brick class
    def test_instance_brick01(self):
        user = self.get_root_user()

        class TestInstanceBrick(Brick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'invalid_id')

        brick_entity = CremeEntity.objects.create(user=user)
        ibi = InstanceBrickConfigItem(
            brick_class_id=TestInstanceBrick.id,
            entity=brick_entity,
        )

        ibi.save()
        brick_id = f'instance-{ibi.uuid}'
        self.assertEqual(brick_id, ibi.brick_id)

        brick = ibi.brick
        self.assertIsInstance(brick, Brick)

        # Because the class is not registered
        self.assertFalse(isinstance(brick, TestInstanceBrick))

        self.assertEqual(brick_id, brick.id)
        self.assertEqual('??', brick.verbose_name)

        self.assertListEqual(
            [_('Unknown type of block (bad uninstall?)')],
            getattr(brick, 'errors', None),
        )

    def test_instance_brick02(self):
        "Extra data."
        user = self.get_root_user()

        class TestInstanceBrick(Brick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'invalid_id')

        brick_entity = CremeEntity.objects.create(user=user)

        ibi = InstanceBrickConfigItem(
            brick_class_id=TestInstanceBrick.id,
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
        user = self.get_root_user()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id,
            entity=naru,
        )

        brick_id = ibi.brick_id

        create_state = BrickState.objects.create
        state1 = create_state(brick_id=brick_id,             user=user)
        state2 = create_state(brick_id=self.TestBrick02.id, user=user)

        ibi.delete()
        self.assertDoesNotExist(ibi)
        self.assertDoesNotExist(state1)
        self.assertStillExists(state2)

    def test_instance_brick_delete02(self):
        "Cannot delete because it is used by detail-view configuration."
        user = self.get_root_user()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id,
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
            exc.args[0],
        )
        self.assertEqual([loc], exc.args[1])

        self.assertStillExists(ibi)
        self.assertStillExists(loc)

    def test_instance_brick_delete03(self):
        "Cannot delete because it is used by home configuration."
        user = self.get_root_user()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id,
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
        role = self.create_role(name='Test')
        loc1 = create_bhl(role=role)
        try_delete(
            _(
                'This block is used in the Home configuration of role «{}»'
            ).format(role),
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
        user = self.get_root_user()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )

        ibi = InstanceBrickConfigItem.objects.create(
            brick_class_id=self.TestBrick01.id,
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

    def test_instance_brick_manager(self):
        user = self.get_root_user()
        naru = FakeContact.objects.create(
            user=user, first_name='Naru', last_name='Narusegawa',
        )
        inn = FakeOrganisation.objects.create(user=user, name='Hinata')

        create_ibi = InstanceBrickConfigItem.objects.create
        ibi1 = create_ibi(brick_class_id=self.TestBrick01.id, entity=naru)
        ibi2 = create_ibi(brick_class_id=self.TestBrick02.id, entity=naru)
        ibi3 = create_ibi(brick_class_id=self.TestBrick02.id, entity=inn)

        self.assertCountEqual(
            [ibi1, ibi3],
            [
                *InstanceBrickConfigItem.objects.for_brick_ids([
                    ibi1.brick_id,
                    'invalid',
                    f'invalid-{ibi2.uuid}',
                    'instance-notauuid',
                    ibi3.brick_id,
                ]),
            ],
        )

        # ---
        with self.assertNumQueries(0):
            count = len(InstanceBrickConfigItem.objects.for_brick_ids(['invalid']))
        self.assertEqual(0, count)

    def test_brick_state_manager_get_for_brick_id01(self):
        "State does not exist in DB."
        user1 = self.get_root_user()
        user2 = self.create_user()

        class TestBrick(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_state01')

        # Not used (other user)
        BrickState.objects.create(
            user=user2,
            brick_id=TestBrick.id,
            is_open=True,
            show_empty_fields=False,
        )

        with self.assertNumQueries(2):  # try to retrieve state + SettingValues
            state = BrickState.objects.get_for_brick_id(user=user1, brick_id=TestBrick.id)

        self.assertIsInstance(state, BrickState)
        self.assertEqual(user1, state.user)
        self.assertIs(state.is_open,           True)
        self.assertIs(state.show_empty_fields, True)
        self.assertIsNone(state.pk)

    def test_brick_state_manager_get_for_brick_id02(self):
        "State stored in DB."
        user = self.get_root_user()

        class TestBrick(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_state02')

        state = BrickState.objects.create(
            user=user,
            brick_id=TestBrick.id,
            is_open=True,
            show_empty_fields=False,
        )

        with self.assertNumQueries(1):
            stored_state = BrickState.objects.get_for_brick_id(
                user=user, brick_id=TestBrick.id,
            )

        self.assertEqual(state, stored_state)

    def test_brick_state_manager_get_for_brick_id03(self):
        "Other value for SettingValues."
        user = self.get_root_user()

        class TestBrick(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_state03')

        sv_open = SettingValue.objects.get_4_key(setting_keys.brick_opening_key)
        sv_open.value = False
        sv_open.save()

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TestBrick.id)
        self.assertFalse(state.is_open)
        self.assertTrue(state.show_empty_fields)

        # ---
        sv_show = SettingValue.objects.get_4_key(setting_keys.brick_showempty_key)
        sv_show.value = False
        sv_show.save()

        state = BrickState.objects.get_for_brick_id(user=user, brick_id=TestBrick.id)
        self.assertFalse(state.is_open)
        self.assertFalse(state.show_empty_fields)

    def test_brick_state_extra_data(self):
        user = self.get_root_user()

        class TestBrick(Brick):
            id_ = Brick.generate_id('creme_core', 'test_brick_state_extra')

        state = BrickState.objects.create(user=user, brick_id=TestBrick.id)
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
        user = self.get_root_user()

        class TestBrick1(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_states01_01')

        class TestBrick2(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_states01_02')

        with self.assertNumQueries(2):
            states = BrickState.objects.get_for_brick_ids(
                user=user, brick_ids=[TestBrick1.id, TestBrick2.id],
            )

        self.assertIsDict(states, length=2)

        state1 = states.get(TestBrick1.id)
        self.assertIsInstance(state1, BrickState)
        self.assertEqual(user, state1.user)
        self.assertIs(state1.is_open,           True)
        self.assertIs(state1.show_empty_fields, True)
        self.assertIsNone(state1.pk)

        state2 = states.get(TestBrick2.id)
        self.assertIsInstance(state2, BrickState)
        self.assertEqual(user, state2.user)
        self.assertIs(state2.is_open,           True)
        self.assertIs(state2.show_empty_fields, True)
        self.assertIsNone(state2.pk)

    def test_brick_state_manager_get_for_brick_ids02(self):
        "A state is stored in DB."
        user1 = self.get_root_user()
        user2 = self.create_user()

        class TestBrick1(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_states02_01')

        class TestBrick2(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_states02_02')

        stored_state1 = BrickState.objects.create(
            user=user1,
            brick_id=TestBrick1.id,
            is_open=False,
            show_empty_fields=True,
        )
        BrickState.objects.create(
            user=user2,  # <== not used
            brick_id=TestBrick2.id,
            is_open=True,
            show_empty_fields=False,
        )

        states = BrickState.objects.get_for_brick_ids(
            user=user1, brick_ids=[TestBrick1.id, TestBrick2.id],
        )
        self.assertIsDict(states, length=2)
        self.assertEqual(stored_state1, states.get(TestBrick1.id))

        state2 = states.get(TestBrick2.id)
        self.assertIsNone(state2.pk)

        # ---
        with self.assertNumQueries(1):
            BrickState.objects.get_for_brick_ids(
                user=user1, brick_ids=[TestBrick1.id],
            )

    def test_brick_state_manager_get_for_brick_ids03(self):
        "Other value for SettingValues."
        user = self.get_root_user()

        class TestBrick(Brick):
            id = Brick.generate_id('creme_core', 'test_brick_models_states03')

        sv_open = SettingValue.objects.get_4_key(setting_keys.brick_opening_key)
        sv_open.value = False
        sv_open.save()

        states = BrickState.objects.get_for_brick_ids(
            user=user, brick_ids=[TestBrick.id],
        )
        self.assertEqual(1, len(states))

        state = states.get(TestBrick.id)
        self.assertFalse(state.is_open)
        self.assertTrue(state.show_empty_fields)

        # ---
        sv_show = SettingValue.objects.get_4_key(setting_keys.brick_showempty_key)
        sv_show.value = False
        sv_show.save()

        states = BrickState.objects.get_for_brick_ids(user=user, brick_ids=[TestBrick.id])
        self.assertEqual(1, len(states))

        state = states.get(TestBrick.id)
        self.assertFalse(state.is_open)
        self.assertFalse(state.show_empty_fields)
