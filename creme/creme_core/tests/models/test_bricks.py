# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as jsonloads

    from django.contrib.auth import get_user_model
    from django.contrib.contenttypes.models import ContentType
    from django.utils.translation import ugettext as _

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation, FakeImage
    from creme.creme_core.blocks import (relations_block, properties_block,
             customfields_block, history_block)
    from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellFunctionField
    from creme.creme_core.gui.bricks import Brick
    from creme.creme_core.models import (BlockDetailviewLocation, UserRole,
            BlockPortalLocation, BlockMypageLocation,
            CremeEntity, InstanceBlockConfigItem,
            RelationBlockItem, RelationType, CustomBlockConfigItem)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BlockTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super(BlockTestCase, cls).setUpClass()

        cls._bdl_backup = list(BlockDetailviewLocation.objects.all())
        cls._bpl_backup = list(BlockPortalLocation.objects.all())
        cls._bml_backup = list(BlockMypageLocation.objects.all())

        BlockDetailviewLocation.objects.all().delete()
        BlockPortalLocation.objects.all().delete()
        BlockMypageLocation.objects.all().delete()

    @classmethod
    def tearDownClass(cls):
        super(BlockTestCase, cls).tearDownClass()

        BlockDetailviewLocation.objects.all().delete()
        BlockPortalLocation.objects.all().delete()
        BlockMypageLocation.objects.all().delete()

        for model, backup in [(BlockDetailviewLocation, cls._bdl_backup),
                              (BlockPortalLocation,     cls._bpl_backup),
                              (BlockMypageLocation,     cls._bml_backup),
                             ]:
            try:
                model.objects.bulk_create(backup)
            except Exception as e:
                print('CremeBlockTagsTestCase: test-data backup problem with model=%s (%s)' % (model, e))

    def test_populate(self):
        self.assertLessEqual({'modelblock', customfields_block.id_, relations_block.id_,
                              properties_block.id_, history_block.id_,
                              },
                             {loc.block_id for loc in self._bdl_backup}
                            )
        block_id = history_block.id_
        self.assertIn(block_id, {bpl.block_id for bpl in self._bpl_backup if bpl.app_name == ''})
        self.assertIn(block_id, {bpl.block_id for bpl in self._bpl_backup if bpl.app_name == 'creme_core'})
        self.assertIn(block_id, {bml.block_id for bml in self._bml_backup if bml.user is None})

    def test_create_detailview01(self):
        "Default configuration"
        order = 25
        zone = BlockDetailviewLocation.TOP
        block_id = relations_block.id_
        loc = BlockDetailviewLocation.create(block_id=block_id, order=order, zone=zone)
        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.pk)
        self.assertIsNone(loc.content_type)
        self.assertEqual(block_id, loc.block_id)
        self.assertEqual(order,    loc.order)
        self.assertEqual(zone,     loc.zone)

    def test_create_detailview02(self):
        "For a ContentType"
        self.assertFalse(BlockDetailviewLocation.config_exists(FakeContact))

        order = 4
        zone = BlockDetailviewLocation.LEFT
        block_id = properties_block.id_
        loc = BlockDetailviewLocation.create(block_id=block_id, order=order, zone=zone, model=FakeContact)
        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.pk)
        self.assertEqual(FakeContact, loc.content_type.model_class())
        self.assertEqual(block_id, loc.block_id)
        self.assertEqual(order,    loc.order)
        self.assertEqual(zone,     loc.zone)

        self.assertTrue(BlockDetailviewLocation.config_exists(FakeContact))

    def test_create_detailview03(self):
        "Do not create if already exists (in any zone/order)"
        block_id = properties_block.id_
        order = 5
        zone = BlockDetailviewLocation.RIGHT

        create_bdl = partial(BlockDetailviewLocation.create, block_id=block_id, model=FakeContact)
        create_bdl(order=order, zone=zone)
        create_bdl(order=4,     zone=BlockDetailviewLocation.LEFT)

        locs = BlockDetailviewLocation.objects.filter(
                block_id=block_id,
                content_type=ContentType.objects.get_for_model(FakeContact),
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

    def test_create_detailview04(self):
        "For a Role"
        role = UserRole.objects.create(name='Viewer')

        block_id = properties_block.id_
        order = 5
        zone = BlockDetailviewLocation.RIGHT

        create_bdl = partial(BlockDetailviewLocation.create, block_id=block_id,
                             model=FakeContact, role=role,
                            )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4,     zone=BlockDetailviewLocation.LEFT)

        locs = BlockDetailviewLocation.objects.filter(
                block_id=block_id,
                content_type=ContentType.objects.get_for_model(FakeContact),
                role=role, superuser=False,
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

        # Do not avoid default configuration creation
        count = BlockDetailviewLocation.objects.count()
        zone = BlockDetailviewLocation.BOTTOM
        loc = create_bdl(order=order, zone=zone, role=None)
        self.assertEqual(count + 1, BlockDetailviewLocation.objects.count())
        self.assertEqual(zone,  loc.zone)
        self.assertIsNone(loc.role)
        self.assertFalse(loc.superuser)

    def test_create_detailview05(self):
        "For super-users"
        block_id = properties_block.id_
        order = 5
        zone = BlockDetailviewLocation.RIGHT

        create_bdl = partial(BlockDetailviewLocation.create, block_id=block_id,
                             model=FakeContact, role='superuser',
                            )
        create_bdl(order=order, zone=zone)
        create_bdl(order=4,     zone=BlockDetailviewLocation.LEFT)

        locs = BlockDetailviewLocation.objects.filter(
                block_id=block_id,
                content_type=ContentType.objects.get_for_model(FakeContact),
                role=None, superuser=True,
        )
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

        # Do not avoid default configuration creation
        count = BlockDetailviewLocation.objects.count()
        zone = BlockDetailviewLocation.BOTTOM
        loc = create_bdl(order=order, zone=zone, role=None)
        self.assertEqual(count + 1, BlockDetailviewLocation.objects.count())
        self.assertEqual(zone,  loc.zone)
        self.assertIsNone(loc.role)
        self.assertFalse(loc.superuser)

    def test_create_detailview06(self):
        "Default configuration cannot have a related role"
        with self.assertRaises(ValueError):
            BlockDetailviewLocation.create(block_id=properties_block.id_,
                                           order=5, zone=BlockDetailviewLocation.RIGHT,
                                           model=None, role='superuser', # <==
                                          )

    def test_create_4_model_block(self):
        order = 5
        zone = BlockDetailviewLocation.RIGHT
        model = FakeContact
        loc = BlockDetailviewLocation.create_4_model_block(order=order, zone=zone, model=model)

        self.assertEqual(1, BlockDetailviewLocation.objects.count())

        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.id)
        self.assertEqual('modelblock', loc.block_id)
        self.assertEqual(model,        loc.content_type.model_class())
        self.assertEqual(order,        loc.order)
        self.assertEqual(zone,         loc.zone)

    def test_create_4_model_brick01(self):
        order = 5
        zone = BlockDetailviewLocation.RIGHT
        model = FakeContact
        loc = BlockDetailviewLocation.create_4_model_brick(order=order, zone=zone, model=model)

        self.assertEqual(1, BlockDetailviewLocation.objects.count())

        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.id)
        self.assertEqual('modelblock', loc.block_id)
        self.assertEqual(model,        loc.content_type.model_class())
        self.assertEqual(order,        loc.order)
        self.assertEqual(zone,         loc.zone)

    def test_create_4_model_brick02(self):
        "model = None"
        loc = BlockDetailviewLocation.create_4_model_brick(
                order=8, zone=BlockDetailviewLocation.BOTTOM, model=None,
        )
        self.assertEqual(1, BlockDetailviewLocation.objects.count())
        self.assertEqual('modelblock', loc.block_id)
        self.assertIsNone(loc.content_type)

    def test_create_4_model_brick03(self):
        "With a Role"
        role = UserRole.objects.create(name='Viewer')
        loc = BlockDetailviewLocation.create_4_model_brick(
                model=FakeContact, role=role,
                order=8, zone=BlockDetailviewLocation.BOTTOM,
        )
        self.assertEqual(1, BlockDetailviewLocation.objects.count())
        self.assertEqual('modelblock', loc.block_id)
        self.assertEqual(role, loc.role)

    def test_create_empty_detailview_config01(self):
        self.assertEqual(0, BlockDetailviewLocation.objects.count())

        BlockDetailviewLocation.create_empty_config()
        locs = BlockDetailviewLocation.objects.all()
        self.assertEqual([('', 1, None)] * 5,
                         [(bl.block_id, bl.order, bl.content_type) for bl in locs]
                         )
        self.assertEqual({BlockDetailviewLocation.HAT,
                          BlockDetailviewLocation.TOP,   BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         {bl.zone for bl in locs}
                        )

    def test_create_empty_detailview_config02(self):
        block_id = relations_block.id_
        BlockDetailviewLocation.create(block_id=block_id, order=1, zone=BlockDetailviewLocation.RIGHT)

        BlockDetailviewLocation.create_empty_config()
        self.assertEqual([block_id], [bl.block_id for bl in BlockDetailviewLocation.objects.all()])

    def test_create_empty_detailview_config03(self):
        zone = BlockDetailviewLocation.BOTTOM
        model = FakeOrganisation

        BlockDetailviewLocation.create_empty_config()
        BlockDetailviewLocation.create_empty_config(model=model)

        locs = BlockDetailviewLocation.objects.filter(content_type=ContentType.objects.get_for_model(model))
        self.assertEqual({BlockDetailviewLocation.HAT,
                          BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         {bl.zone for bl in locs}
                        )
        self.assertEqual(5, len(locs))

        loc = [loc for loc in locs if loc.zone == zone][0]
        self.assertEqual(model,  loc.content_type.model_class())

    def test_create_portal01(self):
        app_name = 'persons'
        order = 25
        block_id = history_block.id_
        loc = BlockPortalLocation.create(app_name=app_name, block_id=block_id, order=order)
        self.get_object_or_fail(BlockPortalLocation, pk=loc.pk, app_name=app_name,
                                block_id=block_id, order=order,
                               )

        self.assertEqual(_('History'), unicode(loc.block_verbose_name))
        self.assertEqual(_('History'), unicode(loc.brick_verbose_name))

    def test_create_portal02(self):
        order = 10
        block_id = history_block.id_
        loc = BlockPortalLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockPortalLocation, pk=loc.pk, app_name='',
                                block_id=block_id, order=order,
                               )

    def test_create_portal03(self):
        app_name = 'billing'
        block_id = history_block.id_
        BlockPortalLocation.create(block_id=block_id, order=3, app_name=app_name)

        order = 10
        BlockPortalLocation.create(block_id=block_id, order=order, app_name=app_name)

        locs = BlockPortalLocation.objects.filter(app_name=app_name, block_id=block_id)
        self.assertEqual(1, len(locs))
        self.assertEqual(order, locs[0].order)

    def test_create_empty_portal_config01(self):
        app_name = 'creme_core'
        self.assertEqual(0, BlockPortalLocation.objects.count())

        BlockPortalLocation.create_empty_config(app_name)
        locs = BlockPortalLocation.objects.all()
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(app_name, loc.app_name)
        self.assertEqual('',       loc.block_id)
        self.assertEqual(1,        loc.order)

    def test_create_empty_portal_config02(self):
        for i in (1, 2):
            BlockPortalLocation.create_empty_config('creme_core')

        self.assertEqual(1, BlockPortalLocation.objects.count())

    def test_create_empty_portal_config03(self):
        BlockPortalLocation.create_empty_config()
        locs = BlockPortalLocation.objects.all()
        self.assertEqual(1,  len(locs))
        self.assertEqual('', locs[0].app_name)

    def test_create_mypage01(self):
        self.login()

        user = self.user
        order = 25
        block_id = history_block.id_
        loc = BlockMypageLocation.create(user=user, block_id=block_id, order=order)
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=user,
                                block_id=block_id, order=order,
                               )

        self.assertEqual(_('History'), unicode(loc.block_verbose_name))
        self.assertEqual(_('History'), unicode(loc.brick_verbose_name))

    def test_create_mypage02(self):
        order = 10
        block_id = history_block.id_
        loc = BlockMypageLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=None,
                                block_id=block_id, order=order,
                               )

    def test_create_mypage03(self):
        block_id = history_block.id_
        BlockMypageLocation.create(block_id=block_id, order=3)

        order = 10
        loc = BlockMypageLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=None,
                                block_id=block_id, order=order,
                               )

    def test_mypage_new_user(self):
        block_id = history_block.id_
        order = 3
        BlockMypageLocation.create(block_id=block_id, order=order)

        user = get_user_model().objects.create(username='Kirika')
        user.set_password('password')
        user.save()
        self.get_object_or_fail(BlockMypageLocation, user=user, block_id=block_id, order=order)

    def test_relation_block01(self):
        rtype = RelationType.create(('test-subject_loves', 'loves'),
                                    ('test-object_loved',  'is loved by')
                                   )[0]

        rbi = RelationBlockItem.create(rtype.id)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga = get_ct(FakeOrganisation)
        ct_img = get_ct(FakeImage)

        rbi = self.refresh(rbi)  # Test persistence
        self.assertIsNone(rbi.get_cells(ct_contact))
        self.assertIsNone(rbi.get_cells(ct_orga))
        self.assertIsNone(rbi.get_cells(ct_img))
        self.assertIs(rbi.all_ctypes_configured, False)

        rbi.set_cells(ct_contact,
                      [EntityCellRegularField.build(FakeContact, 'last_name'),
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

    def test_relation_block02(self):
        "All ctypes configured"
        rtype = RelationType.create(('test-subject_rented', 'is rented by'),
                                    ('test-object_rented',  'rents', [FakeContact, FakeOrganisation]),
                                   )[0]

        rbi = RelationBlockItem.create(rtype.id)
        get_ct = ContentType.objects.get_for_model

        rbi.set_cells(get_ct(FakeContact), [EntityCellRegularField.build(FakeContact, 'last_name')])
        rbi.save()
        self.assertFalse(self.refresh(rbi).all_ctypes_configured)

        rbi.set_cells(get_ct(FakeOrganisation), [EntityCellRegularField.build(FakeOrganisation, 'name')])
        rbi.save()
        self.assertTrue(self.refresh(rbi).all_ctypes_configured)

    def test_relation_block_errors(self):
        rtype = RelationType.create(('test-subject_rented', 'is rented by'),
                                    ('test-object_rented',  'rents'),
                                   )[0]
        ct_contact = ContentType.objects.get_for_model(FakeContact)
        rbi = RelationBlockItem.create(rtype.id)

        build = partial(EntityCellRegularField.build, model=FakeContact)
        rbi.set_cells(ct_contact,
                      [build(name='last_name'), build(name='description')]
                     )
        rbi.save()

        # Inject error by bypassing checkings
        RelationBlockItem.objects.filter(id=rbi.id) \
            .update(json_cells_map=rbi.json_cells_map.replace('description', 'invalid'))

        rbi = self.refresh(rbi)
        cells_contact = rbi.get_cells(ct_contact)
        self.assertEqual(1, len(cells_contact))
        self.assertEqual('last_name', cells_contact[0].value)

        with self.assertNoException():
            deserialized = jsonloads(rbi.json_cells_map)

        self.assertEqual({str(ct_contact.id): [{'type': 'regular_field', 'value': 'last_name'}]},
                         deserialized
                        )

    def test_custom_block(self):
        cbci = CustomBlockConfigItem.objects.create(
                id='tests-organisations01', name='General',
                content_type=ContentType.objects.get_for_model(FakeOrganisation),
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        cells = self.refresh(cbci).cells
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('name', cell.value)

    def test_custom_block_errors01(self):
        cbci = CustomBlockConfigItem.objects.create(
                id='tests-organisations01', name='General',
                content_type=ContentType.objects.get_for_model(FakeOrganisation),
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name'),
                       EntityCellRegularField.build(FakeOrganisation, 'description'),
                      ],
        )

        # Inject error by bypassing checkings
        CustomBlockConfigItem.objects.filter(id=cbci.id) \
            .update(json_cells=cbci.json_cells.replace('description', 'invalid'))

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

        with self.assertNoException():
            deserialized = jsonloads(cbci.json_cells)

        self.assertEqual([{'type': 'regular_field', 'value': 'name'}],
                         deserialized
                        )

    def test_custom_block_errors02(self):
        cbci = CustomBlockConfigItem.objects.create(
                id='tests-organisations01', name='General',
                content_type=ContentType.objects.get_for_model(FakeOrganisation),
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name'),
                       EntityCellRegularField.build(FakeOrganisation, 'invalid'),
                      ],
        )

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

    # See reports for InstanceBlockConfigItem with a working classes; here are the error cases
    def test_instance_block(self):
        self.login()

        class TestInstanceBlock(Brick):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'invalid_id')

        brick_entity = CremeEntity.objects.create(user=self.user)

        generate_id = InstanceBlockConfigItem.generate_id
        self.assertRaises(ValueError, generate_id, TestInstanceBlock, brick_entity, 'foo#bar')

        ibi = InstanceBlockConfigItem(
                block_id=generate_id(TestInstanceBlock, brick_entity, ''),
                entity=brick_entity,
        )

        id_is_specific = InstanceBlockConfigItem.id_is_specific
        self.assertFalse(id_is_specific(Brick.generate_id('creme_core', 'foobar')))
        self.assertTrue(id_is_specific(ibi.block_id))

        brick = ibi.brick
        self.assertIsInstance(brick, Brick)
        self.assertFalse(isinstance(brick, TestInstanceBlock))  # Because the class is not registered
        self.assertEqual('??', brick.verbose_name)
        self.assertEqual(brick, ibi.block)

        errors = [_(u'Unknown type of block (bad uninstall ?)')]
        self.assertEqual(errors, getattr(brick, 'errors', None))
        self.assertEqual(errors, ibi.errors)

# TODO: test BlockState
