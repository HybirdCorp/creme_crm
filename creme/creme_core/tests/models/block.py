# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as jsonloads

    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import User
    from django.utils.translation import ugettext as _

    from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellFunctionField
    from creme.creme_core.models import (BlockDetailviewLocation,
            BlockPortalLocation, BlockMypageLocation,
            RelationBlockItem, RelationType, CustomBlockConfigItem)
    from creme.creme_core.blocks import (relations_block, properties_block,
            customfields_block, history_block)
    from ..base import CremeTestCase

    from creme.documents.models import Document

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('BlockTestCase',)


class BlockTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        BlockDetailviewLocation.objects.all().delete()
        BlockPortalLocation.objects.all().delete()
        BlockMypageLocation.objects.all().delete()

        cls.autodiscover()

    def test_populate(self):
        self.populate('creme_core')

        self.assertEqual({'modelblock', customfields_block.id_, relations_block.id_,
                          properties_block.id_, history_block.id_,
                         },
                         set(loc.block_id for loc in BlockDetailviewLocation.objects.all())
                        )
        self.assertEqual([history_block.id_], [loc.block_id for loc in BlockPortalLocation.objects.filter(app_name='')])
        self.assertEqual([history_block.id_], [loc.block_id for loc in BlockPortalLocation.objects.filter(app_name='creme_core')])
        self.assertEqual([history_block.id_], [loc.block_id for loc in BlockMypageLocation.objects.filter(user=None)])

    def test_create_detailview01(self):
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
        order = 4
        zone = BlockDetailviewLocation.LEFT
        block_id = properties_block.id_
        loc = BlockDetailviewLocation.create(block_id=block_id, order=order, zone=zone, model=Contact)
        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.pk)
        self.assertEqual(Contact,  loc.content_type.model_class())
        self.assertEqual(block_id, loc.block_id)
        self.assertEqual(order,    loc.order)
        self.assertEqual(zone,     loc.zone)

    def test_create_detailview03(self):
        block_id = properties_block.id_
        order = 5
        zone = BlockDetailviewLocation.RIGHT
        BlockDetailviewLocation.create(block_id=block_id, order=order, zone=zone, model=Contact)
        BlockDetailviewLocation.create(block_id=block_id, order=4, zone=BlockDetailviewLocation.LEFT, model=Contact)

        locs = BlockDetailviewLocation.objects.filter(block_id=block_id, content_type=ContentType.objects.get_for_model(Contact))
        self.assertEqual(1, len(locs))

        loc = locs[0]
        self.assertEqual(order, loc.order)
        self.assertEqual(zone,  loc.zone)

    def test_create_4_model_block01(self):
        order = 5
        zone = BlockDetailviewLocation.RIGHT
        model = Contact
        loc = BlockDetailviewLocation.create_4_model_block(order=order, zone=zone, model=model)

        self.assertEqual(1, BlockDetailviewLocation.objects.count())

        loc = self.get_object_or_fail(BlockDetailviewLocation, pk=loc.id)
        self.assertEqual('modelblock', loc.block_id)
        self.assertEqual(order,        loc.order)
        self.assertEqual(zone,         loc.zone)

    def test_create_4_model_block02(self): #model = None
        loc = BlockDetailviewLocation.create_4_model_block(order=8, zone=BlockDetailviewLocation.BOTTOM, model=None)
        self.assertEqual(1, BlockDetailviewLocation.objects.count())
        self.assertEqual('modelblock', loc.block_id)
        self.assertIsNone(loc.content_type)

    def test_create_empty_detailview_config01(self):
        self.assertEqual(0, BlockDetailviewLocation.objects.count())

        BlockDetailviewLocation.create_empty_config()
        locs = BlockDetailviewLocation.objects.all()
        self.assertEqual([('', 1, None)] * 4, [(bl.block_id, bl.order, bl.content_type) for bl in locs])
        self.assertEqual({BlockDetailviewLocation.TOP,   BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         set(bl.zone for bl in locs)
                        )

    def test_create_empty_detailview_config02(self):
        block_id = relations_block.id_
        BlockDetailviewLocation.create(block_id=block_id, order=1, zone=BlockDetailviewLocation.RIGHT)

        BlockDetailviewLocation.create_empty_config()
        self.assertEqual([block_id], [bl.block_id for bl in BlockDetailviewLocation.objects.all()])

    def test_create_empty_detailview_config03(self):
        zone = BlockDetailviewLocation.BOTTOM
        model = Organisation

        BlockDetailviewLocation.create_empty_config()
        BlockDetailviewLocation.create_empty_config(model=model)

        locs = BlockDetailviewLocation.objects.filter(content_type=ContentType.objects.get_for_model(model))
        self.assertEqual({BlockDetailviewLocation.TOP, BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         set(bl.zone for bl in locs)
                        )
        self.assertEqual(4, len(locs))

        loc = [loc for loc in locs if loc.zone == zone][0]
        self.assertEqual(model,  loc.content_type.model_class())

    def test_create_portal01(self):
        app_name = 'persons'
        order = 25
        block_id = history_block.id_
        loc = BlockPortalLocation.create(app_name=app_name, block_id=block_id, order=order)
        self.get_object_or_fail(BlockPortalLocation, pk=loc.pk, app_name=app_name, block_id=block_id, order=order)

    def test_create_portal02(self):
        order = 10
        block_id = history_block.id_
        loc = BlockPortalLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockPortalLocation, pk=loc.pk, app_name='', block_id=block_id, order=order)

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
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=user, block_id=block_id, order=order)

        self.assertEqual(_('History'), unicode(loc.block_verbose_name))

    def test_create_mypage02(self):
        order = 10
        block_id = history_block.id_
        loc = BlockMypageLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=None, block_id=block_id, order=order)

    def test_create_mypage03(self):
        block_id = history_block.id_
        BlockMypageLocation.create(block_id=block_id, order=3)

        order = 10
        loc = BlockMypageLocation.create(block_id=block_id, order=order)
        self.get_object_or_fail(BlockMypageLocation, pk=loc.pk, user=None, block_id=block_id, order=order)

    def test_mypage_new_user(self):
        block_id = history_block.id_
        order = 3
        BlockMypageLocation.create(block_id=block_id, order=order)

        user = User.objects.create(username='Kirika')
        user.set_password('password')
        user.save()
        self.get_object_or_fail(BlockMypageLocation, user=user, block_id=block_id, order=order)

    def test_relation_block01(self):
        rtype = RelationType.create(('test-subject_loves', 'loves'),
                                    ('test-object_loved',  'is loved by')
                                   )[0]

        rbi = RelationBlockItem.create(rtype.id)

        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_orga = get_ct(Organisation)
        ct_doc = get_ct(Document)

        rbi = self.refresh(rbi) #test persistence
        self.assertIsNone(rbi.get_cells(ct_contact))
        self.assertIsNone(rbi.get_cells(ct_orga))
        self.assertIsNone(rbi.get_cells(ct_doc))
        self.assertIs(rbi.all_ctypes_configured, False)

        rbi.set_cells(ct_contact,
                      [EntityCellRegularField.build(Contact, 'last_name'),
                       EntityCellFunctionField.build(Contact, 'get_pretty_properties'),
                      ],
                     )
        rbi.set_cells(ct_orga, [EntityCellRegularField.build(Organisation, 'name')])
        rbi.save()

        rbi = self.refresh(rbi) #test persistence
        self.assertIsNone(rbi.get_cells(ct_doc))
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
                                    ('test-object_rented',  'rents', [Contact, Organisation]),
                                   )[0]

        rbi = RelationBlockItem.create(rtype.id)
        get_ct = ContentType.objects.get_for_model

        rbi.set_cells(get_ct(Contact), [EntityCellRegularField.build(Contact, 'last_name')])
        rbi.save()
        self.assertFalse(self.refresh(rbi).all_ctypes_configured)

        rbi.set_cells(get_ct(Organisation), [EntityCellRegularField.build(Organisation, 'name')])
        rbi.save()
        self.assertTrue(self.refresh(rbi).all_ctypes_configured)

    def test_relation_block_errors(self):
        rtype = RelationType.create(('test-subject_rented', 'is rented by'),
                                    ('test-object_rented',  'rents'),
                                   )[0]
        ct_contact = ContentType.objects.get_for_model(Contact)
        rbi = RelationBlockItem.create(rtype.id)

        build = partial(EntityCellRegularField.build, model=Contact)
        rbi.set_cells(ct_contact,
                      [build(name='last_name'), build(name='description')]
                     )
        rbi.save()

        #inject error by bypassing checkings
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
                    content_type=ContentType.objects.get_for_model(Organisation),
                    cells=[EntityCellRegularField.build(Organisation, 'name')],
                )

        cells = self.refresh(cbci).cells 
        self.assertEqual(1, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual('name', cell.value)

    def test_custom_block_errors01(self):
        cbci = CustomBlockConfigItem.objects.create(
                    id='tests-organisations01', name='General',
                    content_type=ContentType.objects.get_for_model(Organisation),
                    cells=[EntityCellRegularField.build(Organisation, 'name'),
                           EntityCellRegularField.build(Organisation, 'description'),
                          ],
               )

        #inject error by bypassing checkings
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
                    content_type=ContentType.objects.get_for_model(Organisation),
                    cells=[EntityCellRegularField.build(Organisation, 'name'),
                           EntityCellRegularField.build(Organisation, 'invalid'),
                          ],
               )

        cbci = self.refresh(cbci)
        self.assertEqual(1, len(cbci.cells))

#TODO: test other models
