# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellCustomField, EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import RelationType, CustomField
    from creme.creme_core.models.block import *
    from creme.creme_core.gui.block import block_registry, Block, SpecificRelationsBlock
    from creme.creme_core.blocks import history_block
    from creme.creme_core.tests.base import CremeTestCase

    from creme.creme_config.blocks import(BlockDetailviewLocationsBlock, BlockPortalLocationsBlock,
        BlockDefaultMypageLocationsBlock, RelationBlocksConfigBlock,
        InstanceBlocksConfigBlock, CustomBlocksConfigBlock)

    from creme.documents.models import Folder, Document

    from creme.persons.models import Contact, Organisation  #need CremeEntity

    from creme.emails.models import EmailCampaign
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('BlocksConfigTestCase',)


class BlocksConfigTestCase(CremeTestCase):
    ADD_DT_URL     = '/creme_config/blocks/detailview/add/'
    DEL_DETAIL_URL = '/creme_config/blocks/detailview/delete'

    @classmethod
    def setUpClass(cls):
        BlockDetailviewLocation.objects.all().delete()
        BlockPortalLocation.objects.all().delete()
        BlockMypageLocation.objects.all().delete()
        RelationBlockItem.objects.all().delete()

        cls.populate('creme_core', 'creme_config')
        cls.autodiscover()

    def setUp(self):
        self.login()

    def _build_editdetail_url(self, ct=None):
        return '/creme_config/blocks/detailview/edit/%s' % (ct.id if ct else 0)

    def _build_rblock_addctypes_url(self, rbi):
        return '/creme_config/blocks/relation_block/add_ctypes/%s' % rbi.id

    def _build_rblock_editctype_url(self, rbi, model):
        return '/creme_config/blocks/relation_block/%s/edit_ctype/%s' % (
                    rbi.id, ContentType.objects.get_for_model(model).id,
                )

    def test_portal(self):
        response = self.assertGET200('/creme_config/blocks/portal/')

        fmt = 'id="%s"'
        self.assertContains(response, fmt % BlockDetailviewLocationsBlock.id_)
        self.assertContains(response, fmt % BlockPortalLocationsBlock.id_)
        self.assertContains(response, fmt % BlockDefaultMypageLocationsBlock.id_)
        self.assertContains(response, fmt % RelationBlocksConfigBlock.id_)
        self.assertContains(response, fmt % InstanceBlocksConfigBlock.id_)
        self.assertContains(response, fmt % CustomBlocksConfigBlock.id_)

    def test_add_detailview(self):
        url = self.ADD_DT_URL
        self.assertGET200(url)

        ct = ContentType.objects.get_for_model(Contact)
        self.assertFalse(BlockDetailviewLocation.objects.filter(content_type=ct))

        self.assertNoFormError(self.client.post(url, data={'ctype': ct.id}))

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual({BlockDetailviewLocation.TOP,   BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         {bl.zone for bl in b_locs}
                        )

        response = self.client.get(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertNotIn(ct, ctypes)

    def _find_field_index(self, formfield, name):
        for i, (fname, fvname) in enumerate(formfield.choices):
            if fname == name:
                return i

        self.fail('No "%s" field' % name)

    def _assertNotInChoices(self, formfield, id_, error_msg):
        for fid, fvname in formfield.choices:
            if fid == id_:
                self.fail(error_msg + ' -> should not be in choices.')

    def _find_location(self, block_id, locations):
        for location in locations:
            if location.block_id == block_id:
                return location

        self.fail('No "%s" in locations' % block_id)

    def test_edit_detailview01(self):
        self.assertGET404(self._build_editdetail_url(ContentType.objects.get_for_model(Contact)))

    def test_edit_detailview02(self):
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post(self.ADD_DT_URL, data={'ctype': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_detailview02_1')
            verbose_name  = u'Testing purpose'

            def detailview_display(self, context):     return self._render(self.get_block_template_context(context))
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_detailview02_2')
            verbose_name  = u'Testing purpose'

            #def detailview_display(self, context):    NO
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2()
        block_registry.register(foobar_block1, foobar_block2)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']

        blocks = list(block_registry.get_compatible_blocks(model))
        self.assertGreaterEqual(len(blocks), 5)
        self._find_field_index(top_field, foobar_block1.id_)
        self._assertNotInChoices(top_field, foobar_block2.id_, 'Block has no detailview_display() method')

        block_top_id1   = blocks[0].id_
        block_top_id2   = blocks[1].id_
        block_left_id1  = 'modelblock'
        block_left_id2  = blocks[2].id_
        block_right_id  = blocks[3].id_
        block_bottom_id = blocks[4].id_

        block_top_index1   = self._find_field_index(top_field, block_top_id1)
        block_top_index2   = self._find_field_index(top_field, block_top_id2)
        block_left_index1  = self._find_field_index(left_field, block_left_id1)
        block_left_index2  = self._find_field_index(left_field, block_left_id2)
        block_right_index  = self._find_field_index(right_field, block_right_id)
        block_bottom_index = self._find_field_index(bottom_field, block_bottom_id)

        response = self.client.post(url,
                                    data={'top_check_%s' % block_top_index1: 'on',
                                          'top_value_%s' % block_top_index1: block_top_id1,
                                          'top_order_%s' % block_top_index1: 1,

                                          'top_check_%s' % block_top_index2: 'on',
                                          'top_value_%s' % block_top_index2: block_top_id2,
                                          'top_order_%s' % block_top_index2: 2,

                                          'left_check_%s' % block_left_index1: 'on',
                                          'left_value_%s' % block_left_index1: block_left_id1,
                                          'left_order_%s' % block_left_index1: 1,

                                          'left_check_%s' % block_left_index2: 'on',
                                          'left_value_%s' % block_left_index2: block_left_id2,
                                          'left_order_%s' % block_left_index2: 2,

                                          'right_check_%s' % block_right_index: 'on',
                                          'right_value_%s' % block_right_index: block_right_id,
                                          'right_order_%s' % block_right_index: 1,

                                          'bottom_check_%s' % block_bottom_index: 'on',
                                          'bottom_value_%s' % block_bottom_index: block_bottom_id,
                                          'bottom_order_%s' % block_bottom_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)

        locations = [b_loc for b_loc in b_locs if b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        locations = [b_loc for b_loc in b_locs if b_loc.zone == BlockDetailviewLocation.LEFT]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_left_id1, locations).order)
        self.assertEqual(2, self._find_location(block_left_id2, locations).order)

        locations = [b_loc for b_loc in b_locs if b_loc.zone == BlockDetailviewLocation.RIGHT]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_right_id, locations).order)

        locations = [b_loc for b_loc in b_locs if b_loc.zone == BlockDetailviewLocation.BOTTOM]
        self.assertEqual(1, len(locations))
        self.assertEqual(1, self._find_location(block_bottom_id, locations).order)

    def test_edit_detailview03(self):
        "When no block -> fake block"
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        blocks = list(block_registry.get_compatible_blocks(model))
        self.assertGreaterEqual(len(blocks), 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(content_type=ct, block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(content_type=ct, block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(content_type=ct, block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(content_type=ct, block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            top_field    = fields['top']
            left_field   = fields['left']
            right_field  = fields['right']
            bottom_field = fields['bottom']

        block_top_id1 = blocks[0].id_
        block_top_id2 = blocks[1].id_

        self.assertEqual([block_top_id1], top_field.initial)
        self.assertEqual([block_top_id2], left_field.initial)
        self.assertEqual([blocks[2].id_], right_field.initial)
        self.assertEqual([blocks[3].id_], bottom_field.initial)

        block_top_index1 = self._find_field_index(top_field, block_top_id1)
        block_top_index2 = self._find_field_index(top_field, block_top_id2)

        response = self.client.post(url,
                                    data={'top_check_%s' % block_top_index1: 'on',
                                          'top_value_%s' % block_top_index1: block_top_id1,
                                          'top_order_%s' % block_top_index1: 1,

                                          'top_check_%s' % block_top_index2: 'on',
                                          'top_value_%s' % block_top_index2: block_top_id2,
                                          'top_order_%s' % block_top_index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = BlockDetailviewLocation.objects.filter(content_type=ct)
        locations = [b_loc for b_loc in b_locs if  b_loc.zone == BlockDetailviewLocation.TOP]
        self.assertEqual(2, len(locations))
        self.assertEqual(1, self._find_location(block_top_id1, locations).order)
        self.assertEqual(2, self._find_location(block_top_id2, locations).order)

        def blocks_info(zone):
            return [(bl.block_id, bl.order) for bl in b_locs if bl.zone == zone]

        self.assertEqual([('', 1)], blocks_info(BlockDetailviewLocation.LEFT))
        self.assertEqual([('', 1)], blocks_info(BlockDetailviewLocation.RIGHT))
        self.assertEqual([('', 1)], blocks_info(BlockDetailviewLocation.BOTTOM))

    def test_edit_detailview04(self):
        "Default conf"
        BlockDetailviewLocation.objects.filter(content_type=None).delete()
        url = self._build_editdetail_url()
        self.assertGET404(url)

        blocks = list(block_registry.get_compatible_blocks(model=None))
        self.assertGreaterEqual(len(blocks), 5, blocks)

        create_loc = BlockDetailviewLocation.objects.create
        create_loc(block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.TOP)
        create_loc(block_id=blocks[1].id_, order=1, zone=BlockDetailviewLocation.LEFT)
        create_loc(block_id=blocks[2].id_, order=1, zone=BlockDetailviewLocation.RIGHT)
        create_loc(block_id=blocks[3].id_, order=1, zone=BlockDetailviewLocation.BOTTOM)

        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={}))

        b_locs = BlockDetailviewLocation.objects.filter(content_type=None)
        self.assertEqual([('', 1)] * 4, [(bl.block_id, bl.order) for bl in b_locs])
        self.assertEqual({BlockDetailviewLocation.TOP,   BlockDetailviewLocation.LEFT,
                          BlockDetailviewLocation.RIGHT, BlockDetailviewLocation.BOTTOM,
                         },
                         {bl.zone for bl in b_locs}
                        )

    def test_edit_detailview05(self):
        "Post one block several times -> validation error"
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post(self.ADD_DT_URL, data={'ctype': ct.id})
        self.assertEqual(4, BlockDetailviewLocation.objects.filter(content_type=ct).count())

        url = self._build_editdetail_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            left_field  = fields['left']
            right_field = fields['right']

        blocks = list(block_registry.get_compatible_blocks(model))
        self.assertTrue(blocks)

        evil_block = blocks[0]

        block_left_id = block_right_id = evil_block.id_ # <= same block !!
        block_left_index  = self._find_field_index(left_field,  block_left_id)
        block_right_index = self._find_field_index(right_field, block_right_id)

        response = self.client.post(url,
                                    data={'right_check_%s' % block_right_index: 'on',
                                          'right_value_%s' % block_right_index: block_right_id,
                                          'right_order_%s' % block_right_index: 1,

                                          'left_check_%s' % block_left_index: 'on',
                                          'left_value_%s' % block_left_index: block_left_id,
                                          'left_order_%s' % block_left_index: 1,
                                         }
                                   )
        self.assertFormError(response, 'form', field=None,
                             errors=[_(u'The following block should be displayed only once: <%s>') %
                                        evil_block.verbose_name
                                    ]
                            )

    def test_edit_detailview06(self):
        "Instance block, relationtype block"
        model = Contact
        ct = ContentType.objects.get_for_model(model)

        self.client.post(self.ADD_DT_URL, data={'ctype': ct.id})

        rtype = RelationType.objects.all()[0]
        rtype_block_id = SpecificRelationsBlock.generate_id('test', 'foobar')
        RelationBlockItem.objects.create(block_id=rtype_block_id, relation_type=rtype)

        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')

        class FoobarInstanceBlock(Block):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_config', 'test_edit_detailview06')

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                                self.id_, self.ibci.entity
                            ) #useless :)

        instance_block_id = InstanceBlockConfigItem.generate_id(FoobarInstanceBlock, naru, '')
        InstanceBlockConfigItem.objects.create(block_id=instance_block_id,
                                               entity=naru, verbose='All stuffes',
                                              )

        block_registry.register_4_instance(FoobarInstanceBlock)

        response = self.assertGET200(self._build_editdetail_url(ct))

        with self.assertNoException():
            top_field = response.context['form'].fields['top']

        choices = [block_id for block_id, block_name in top_field.choices]
        self.assertIn(rtype_block_id,    choices)
        self.assertIn(instance_block_id, choices)

    def test_delete_detailview01(self):
        "Can not delete default conf"
        self.assertPOST404(self.DEL_DETAIL_URL, data={'id': 0})

    def test_delete_detailview02(self):
        ct = ContentType.objects.get_for_model(Contact)
        self.client.post(self.ADD_DT_URL, data={'ctype': ct.id})

        self.assertPOST200(self.DEL_DETAIL_URL, data={'id': ct.id})
        self.assertFalse(BlockDetailviewLocation.objects.filter(content_type=ct))

    def test_add_portal(self):
        url = '/creme_config/blocks/portal/add/'
        self.assertGET200(url)

        app_name = 'persons'
        self.assertFalse(BlockPortalLocation.objects.filter(app_name=app_name))

        self.assertNoFormError(self.client.post(url, data={'app_name': app_name}))

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[-1]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

        response = self.client.get(url)

        with self.assertNoException():
            choices = response.context['form'].fields['app_name'].choices

        names = {name for name, vname in choices}
        self.assertNotIn(app_name,       names)
        self.assertNotIn('creme_core',   names)
        self.assertNotIn('creme_config', names)

    def test_edit_portal01(self):
        self.assertGET404('/creme_config/blocks/portal/edit/persons')

    def test_edit_portal02(self):
        app_name = 'persons'

        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_1')
            verbose_name  = u'Testing purpose'

            ##NB: only portal_display() method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def home_display(self, context): return '<table id="%s"></table>' % self.id_

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_2')
            verbose_name  = u'Testing purpose'
            configurable  = False # <----

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock3(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_3')
            verbose_name  = u'Testing purpose'
            target_apps   = (app_name, 'billing') # <-- OK

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        class FoobarBlock4(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal02_4')
            verbose_name  = u'Testing purpose'
            target_apps   = ('billing', 'documents') # <-- KO

            def portal_display(self, context, ct_ids):
                return '<table id="%s"></table>' % self.id_

        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')

        class FoobarInstanceBlock(Block):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_config', 'test_edit_portal02')
            verbose_name  = u'Testing purpose'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def portal_display(self, context, ct_ids):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                                self.id_, self.ibci.entity
                            ) #useless :)

        instance_block_id = InstanceBlockConfigItem.generate_id(FoobarInstanceBlock, naru, '')
        InstanceBlockConfigItem.objects.create(block_id=instance_block_id, entity=naru, verbose='All stuffes')

        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2()
        foobar_block3 = FoobarBlock3()
        foobar_block4 = FoobarBlock4()
        block_registry.register(foobar_block1, foobar_block2, foobar_block3, foobar_block4)
        block_registry.register_4_instance(FoobarInstanceBlock)

        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})
        self.assertEqual(1, BlockPortalLocation.objects.filter(app_name=app_name).count())

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.assertGET200(url)

        with self.assertNoException():
            blocks_field = response.context['form'].fields['blocks']

        choices = blocks_field.choices
        self.assertGreaterEqual(len(choices), 2)
        self._find_field_index(blocks_field, foobar_block1.id_)
        self._assertNotInChoices(blocks_field, foobar_block2.id_, 'Block is not configurable')
        self._find_field_index(blocks_field, foobar_block3.id_)
        self._assertNotInChoices(blocks_field, foobar_block4.id_, 'Block is not compatible with this app')
        self._find_field_index(blocks_field, instance_block_id)

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url, data={'blocks_check_%s' % index1: 'on',
                                               'blocks_value_%s' % index1: block_id1,
                                               'blocks_order_%s' % index1: 1,

                                               'blocks_check_%s' % index2: 'on',
                                               'blocks_value_%s' % index2: block_id2,
                                               'blocks_order_%s' % index2: 2,
                                              }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def _get_blocks_4_portal(self):
        blocks = [block for block_id, block in block_registry
                            if hasattr(block, 'portal_display')
                 ]
        self.assertGreaterEqual(len(blocks), 2, blocks)

        return blocks

    def test_edit_portal03(self):
        "Set no block -> fake blocks"
        app_name = 'persons'
        blocks = self._get_blocks_4_portal()

        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name=app_name, block_id=blocks[0].id_, order=1)
        create_loc(app_name=app_name, block_id=blocks[1].id_, order=2)

        url = '/creme_config/blocks/portal/edit/%s' % app_name
        response = self.assertGET200(url)

        with self.assertNoException():
            blocks_field = response.context['form'].fields['blocks']

        self.assertEqual([blocks[0].id_, blocks[1].id_], blocks_field.initial)

        self.assertNoFormError(self.client.post(url, data={}))

        b_locs = list(BlockPortalLocation.objects.filter(app_name=app_name))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_edit_portal04(self):
        "Default conf"
        BlockPortalLocation.objects.filter(app_name='').delete()
        url = '/creme_config/blocks/portal/edit/default'
        self.assertGET404(url)

        blocks = self._get_blocks_4_portal()
        create_loc = BlockPortalLocation.objects.create
        create_loc(app_name='', block_id=blocks[0].id_, order=1)
        create_loc(app_name='', block_id=blocks[1].id_, order=2)

        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={}))

        b_locs = list(BlockPortalLocation.objects.filter(app_name=''))
        self.assertEqual(1, len(b_locs))

        bpl = b_locs[0]
        self.assertEqual(1,  bpl.order)
        self.assertEqual('', bpl.block_id)

    def test_edit_portal05(self):
        "Home -> use 'home_display' method"
        app_name = 'creme_core'

        self.assertTrue(BlockPortalLocation.objects.filter(app_name=app_name).exists())

        class FoobarBlock(Block):
            id_           = Block.generate_id('creme_config', 'test_edit_portal05')
            verbose_name  = u'Testing purpose'

            ##NB: only 'home_display' method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

            def home_display(self, context):
                return '<table id="%s"></table>' % self.id_

        foobar_block = FoobarBlock()
        block_registry.register(foobar_block)

        response = self.assertGET200('/creme_config/blocks/portal/edit/%s' % app_name)

        with self.assertNoException():
            blocks_field = response.context['form'].fields['blocks']

        self._find_field_index(blocks_field, foobar_block.id_)

    def test_edit_portal06(self):
        "Edit portal of unknown app"
        app_name = 'unknown'
        self.assertFalse(BlockPortalLocation.objects.filter(app_name=app_name).exists())
        self.assertGET404('/creme_config/blocks/portal/edit/%s' % app_name)

    def test_delete_portal(self):
        app_name = 'persons'
        self.client.post('/creme_config/blocks/portal/add/', data={'app_name': app_name})

        self.assertPOST200('/creme_config/blocks/portal/delete', data={'id': app_name})
        self.assertFalse(BlockPortalLocation.objects.filter(app_name=app_name))

    def test_delete_home(self):
        "Can not delete home conf"
        #TODO: use a helper method ??
        app_name = 'creme_core'
        blocks = [block for block_id, block in  block_registry
                            if hasattr(block, 'home_display')
                 ]
        self.assertGreaterEqual(len(blocks), 1)

        BlockPortalLocation.objects.create(app_name=app_name, block_id=blocks[0].id_, order=1)
        self.assertPOST404('/creme_config/blocks/portal/delete', data={'id': app_name})

    def test_edit_default_mypage(self):
        url = '/creme_config/blocks/mypage/edit/default'
        response = self.assertGET200(url)

        with self.assertNoException():
            blocks_field = response.context['form'].fields['blocks']

        choices = blocks_field.choices
        self.assertGreaterEqual(len(choices), 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                         blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={'blocks_check_%s' % index1: 'on',
                                          'blocks_value_%s' % index1: block_id1,
                                          'blocks_order_%s' % index1: 1,

                                          'blocks_check_%s' % index2: 'on',
                                          'blocks_value_%s' % index2: block_id2,
                                          'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=None))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_edit_mypage(self):
        user = self.user
        url = '/creme_config/blocks/mypage/edit'
        response = self.assertGET200(url)

        with self.assertNoException():
            blocks_field = response.context['form'].fields['blocks']

        choices = blocks_field.choices
        self.assertGreaterEqual(len(choices), 2)
        self.assertEqual(list(BlockMypageLocation.objects.filter(user=None).values_list('block_id', flat=True)),
                         blocks_field.initial
                        )

        block_id1 = choices[0][0]
        block_id2 = choices[1][0]

        index1 = self._find_field_index(blocks_field, block_id1)
        index2 = self._find_field_index(blocks_field, block_id2)

        response = self.client.post(url,
                                    data={'blocks_check_%s' % index1: 'on',
                                          'blocks_value_%s' % index1: block_id1,
                                          'blocks_order_%s' % index1: 1,

                                          'blocks_check_%s' % index2: 'on',
                                          'blocks_value_%s' % index2: block_id2,
                                          'blocks_order_%s' % index2: 2,
                                         }
                                   )
        self.assertNoFormError(response)

        b_locs = list(BlockMypageLocation.objects.filter(user=user))
        self.assertEqual(2, len(b_locs))
        self.assertEqual(1, self._find_location(block_id1, b_locs).order)
        self.assertEqual(2, self._find_location(block_id2, b_locs).order)

    def test_delete_default_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=None, block_id=history_block.id_, order=1)
        self.assertPOST200('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertDoesNotExist(loc)

    def test_delete_default_mypage02(self):
        "'user' must be 'None'"
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        self.assertPOST404('/creme_config/blocks/mypage/default/delete', data={'id': loc.id})
        self.assertStillExists(loc)

    def test_delete_mypage01(self):
        loc = BlockMypageLocation.objects.create(user=self.user, block_id=history_block.id_, order=1)
        self.assertPOST200('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertDoesNotExist(loc)

    def test_delete_mypage02(self):
        "BlockMypageLocation must belong to the user"
        loc = BlockMypageLocation.objects.create(user=self.other_user, block_id=history_block.id_, order=1)
        self.assertPOST404('/creme_config/blocks/mypage/delete', data={'id': loc.id})
        self.assertStillExists(loc)

    def test_add_relationblock(self):
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'),
                                )[0]
        self.assertFalse(RelationBlockItem.objects.count())

        url = '/creme_config/blocks/relation_block/add/'
        self.assertGET200(url)

        self.assertNoFormError(self.client.post(url, data={'relation_type': rt.id}))

        rb_items = RelationBlockItem.objects.all()
        self.assertEqual(1, len(rb_items))

        rb_item = rb_items[0]
        self.assertEqual(rt.id, rb_item.relation_type.id)
        self.assertEqual('specificblock_creme_config-test-subfoo', rb_item.block_id)
        self.assertIsNone(rb_item.get_cells(ContentType.objects.get_for_model(Contact)))

    def test_add_relationblock_ctypes01(self):
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate', [Contact, Organisation, Document]),
                                )[0]

        rb_item = RelationBlockItem.objects.create(
                        block_id='specificblock_creme_config-test-subfoo',
                        relation_type=rt,
                    )

        url = self._build_rblock_addctypes_url(rb_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctypes'].ctypes

        get_ct = ContentType.objects.get_for_model
        self.assertIn(get_ct(Contact),      choices)
        self.assertIn(get_ct(Organisation), choices)
        self.assertIn(get_ct(Document),     choices)
        self.assertNotIn(get_ct(Folder),    choices)

        self.assertNoFormError(self.client.post(
            url,
            data={'ctypes': [get_ct(m).id for m in (Contact, Organisation)]},
        ))

        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(get_ct(Document)))
        self.assertEqual([], rb_item.get_cells(get_ct(Contact)))
        self.assertEqual([], rb_item.get_cells(get_ct(Organisation)))

        #used CTypes should not be proposed
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctypes'].ctypes

        self.assertIn(get_ct(Document),        choices) #compatible & not used
        self.assertNotIn(get_ct(Folder),       choices) #still not compatible
        self.assertNotIn(get_ct(Contact),      choices) #used
        self.assertNotIn(get_ct(Organisation), choices) #used

    def test_add_relationblock_ctypes02(self):
        "All ContentTypes allowed"
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'),
                                )[0]

        rb_item = RelationBlockItem.objects.create(
                        block_id='specificblock_creme_config-test-subfoo',
                        relation_type=rt,
                    )

        url = self._build_rblock_addctypes_url(rb_item)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctypes'].ctypes

        get_ct = ContentType.objects.get_for_model
        self.assertIn(get_ct(Contact),      choices)
        self.assertIn(get_ct(Organisation), choices)
        self.assertIn(get_ct(Document),     choices)

        self.assertNoFormError(self.client.post( url, data={'ctypes': [get_ct(Contact).id]}))

        rb_item = self.refresh(rb_item)
        self.assertIsNone(rb_item.get_cells(get_ct(Organisation)))
        self.assertEqual([], rb_item.get_cells(get_ct(Contact)))

        #used CTypes should not be proposed
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['ctypes'].ctypes

        self.assertNotIn(get_ct(Contact),   choices) #used
        self.assertIn(get_ct(Organisation), choices) #not used

    def test_edit_relationblock_ctypes01(self):
        ct = ContentType.objects.get_for_model(Contact)
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'),
                                )[0]

        rb_item = RelationBlockItem(
                        block_id='specificblock_creme_config-test-subfoo',
                        relation_type=rt,
                    )
        rb_item.set_cells(ct, ())
        rb_item.save()

        self.assertGET404(self._build_rblock_editctype_url(rb_item, Organisation))

        url = self._build_rblock_editctype_url(rb_item, Contact)
        self.assertGET200(url)

        funcfield = Contact.function_fields.get('get_pretty_properties')
        field_fname = 'first_name'
        field_lname = 'last_name'
        self.assertNoFormError(self.client.post(
            url,
            data={'cells': 'regular_field-%(rfield1)s,regular_field-%(rfield2)s,function_field-%(ffield)s' % {
                                'rfield1': field_fname,
                                'rfield2': field_lname,
                                'ffield':  funcfield.name,
                            },
                 }
           )
        )

        rb_item = self.refresh(rb_item)
        cells = rb_item.get_cells(ct)
        self.assertIsInstance(cells, list)
        self.assertEqual(3, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

    def test_edit_relationblock_ctypes02(self):
        "Validation errors with URLField & ForeignKey"
        rb_item = RelationBlockItem(
                block_id='specificblock_creme_config-test-subfoo',
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ContentType.objects.get_for_model(Contact), ())
        rb_item.save()

        url = self._build_rblock_editctype_url(rb_item, Contact)

        def post(field_name, error=True):
            response = self.assertPOST200(
                url,
                data={'cells': 'regular_field-%(rfield1)s,regular_field-%(rfield2)s' % {
                                    'rfield1': field_name,
                                    'rfield2': 'last_name',
                                },
                     }
            )
            if error:
                self.assertFormError(response, 'form', 'cells',
                                    _('This type of field can not be the first column.')
                                    )
            else:
                self.assertNoFormError(response)

        post('url_site')
        post('email')
        post('image')
        post('image__name')
        post('civility', error=False)
        post('civility__shortcut', error=False)

    def test_edit_relationblock_ctypes03(self):
        "Validation errors with M2M"
        rb_item = RelationBlockItem(
                block_id='specificblock_creme_config-test-subfoo',
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ContentType.objects.get_for_model(EmailCampaign), ())
        rb_item.save()

        url = self._build_rblock_editctype_url(rb_item, EmailCampaign)

        def post(field_name):
            response = self.assertPOST200(
                url,
                data={'cells': 'regular_field-%(rfield1)s,regular_field-%(rfield2)s' % {
                                    'rfield1': field_name,
                                    'rfield2': 'name',
                                },
                    }
            )
            self.assertFormError(response, 'form', 'cells',
                                 _('This type of field can not be the first column.')
                                )

        post('mailing_lists')
        post('mailing_lists__name')

    def test_edit_relationblock_ctypes04(self):
        "Validation errors with Relation"
        create_rtype = RelationType.create
        rt1 = create_rtype(('test-subfoo', 'subject_predicate1'), ('test-objfoo', 'object_predicate2'))[0]
        rt2 = create_rtype(('test-subbar', 'subject_predicate2'), ('test-objbar', 'object_predicate2'))[0]

        rb_item = RelationBlockItem(
                block_id='specificblock_creme_config-test-subfoo',
                relation_type=rt1,
            )
        rb_item.set_cells(ContentType.objects.get_for_model(Organisation), ())
        rb_item.save()

        response = self.assertPOST200(
            self._build_rblock_editctype_url(rb_item, Organisation),
            data={'cells': 'relation-%(rtype)s,regular_field-%(rfield)s' % {
                                'rtype':  rt2.id,
                                'rfield': 'name',
                            },
                 }
        )
        self.assertFormError(response, 'form', 'cells',
                             _('This type of field can not be the first column.')
                            )

    def test_delete_relationblock_ctypes(self):
        get_ct = ContentType.objects.get_for_model
        ct = get_ct(Contact)

        rb_item = RelationBlockItem(
                block_id='specificblock_creme_config-test-subfoo',
                relation_type=RelationType.create(('test-subfoo', 'subject_predicate'),
                                                  ('test-objfoo', 'object_predicate'),
                                                 )[0],
            )
        rb_item.set_cells(ct, [EntityCellRegularField.build(Contact, 'first_name')])
        rb_item.save()

        url_fmt = '/creme_config/blocks/relation_block/%s/delete_ctype'
        self.assertPOST404(url_fmt % rb_item.id, data={'id': get_ct(Organisation).id})

        url = url_fmt % rb_item.id
        data = {'id': ct.id}
        self.assertGET404(url, data=data) #only POST

        self.assertPOST200(url, data=data)
        self.assertIsNone(self.refresh(rb_item).get_cells(ct))

    def test_delete_relationblock(self):
        rt = RelationType.create(('test-subfoo', 'subject_predicate'),
                                 ('test-objfoo', 'object_predicate'), is_custom=False
                                )[0]
        rbi = RelationBlockItem.objects.create(block_id='foobarid', relation_type=rt)
        loc = BlockDetailviewLocation.create(block_id=rbi.block_id, order=5,
                                             zone=BlockDetailviewLocation.RIGHT,
                                             model=Contact,
                                            )

        self.assertPOST200('/creme_config/blocks/relation_block/delete', data={'id': rbi.id})
        self.assertDoesNotExist(rbi)
        self.assertDoesNotExist(loc)

    def test_delete_instanceblock(self):
        naru = Contact.objects.create(user=self.user, first_name='Naru', last_name='Narusegawa')

        class FoobarInstanceBlock(Block):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_config', 'test_delete_instanceblock')

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity) #useless :)


        ibi = InstanceBlockConfigItem.objects.create(block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock, naru, ''),
                                                     entity=naru, verbose='All stuffes'
                                                    )
        loc = BlockDetailviewLocation.create(block_id=ibi.block_id, order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)
        self.assertPOST200('/creme_config/blocks/instance_block/delete', data={'id': ibi.id})
        self.assertDoesNotExist(ibi)
        self.assertDoesNotExist(loc)

    def test_add_customblock(self):
        url = '/creme_config/blocks/custom/add/'
        self.assertGET200(url)

        ct = ContentType.objects.get_for_model(Contact)
        self.assertFalse(CustomBlockConfigItem.objects.filter(content_type=ct))

        name = 'Regular info'
        self.assertNoFormError(self.client.post(url,
                                                data={'ctype': ct.id,
                                                      'name':  name,
                                                     }
                                               )
                              )

        cbc_items = CustomBlockConfigItem.objects.filter(content_type=ct)
        self.assertEqual(1, len(cbc_items))

        cbc_item = cbc_items[0]
        self.assertEqual(name, cbc_item.name)
        self.assertEqual([], cbc_item.cells)

        self.assertNoFormError(self.client.post(url,
                                                data={'ctype': ct.id,
                                                      'name':  'Other info',
                                                     }
                                               )
                              )
        self.assertEqual(2, CustomBlockConfigItem.objects.filter(content_type=ct).count())

    def test_edit_customblock(self):
        ct = ContentType.objects.get_for_model(Contact)

        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(name=u'Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=ct,
                                                )
        funcfield = Contact.function_fields.get('get_pretty_properties')

        name = 'info'
        cbc_item = CustomBlockConfigItem.objects.create(id='tests-contacts1',
                                                        content_type=ct, name=name,
                                                       )

        url = '/creme_config/blocks/custom/edit/%s' % cbc_item.id
        self.assertGET200(url)

        name = name.title()
        field_fname = 'first_name'
        field_lname = 'last_name'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={'name':  name,
                  'cells': 'regular_field-%(rfield1)s,regular_field-%(rfield2)s,relation-%(rtype)s,function_field-%(ffield)s,custom_field-%(cfield)s' % {
                                'rfield1': field_fname,
                                'rfield2': field_lname,
                                'cfield':  customfield.id,
                                'rtype':   loves.id,
                                'ffield':  funcfield.name,
                            },
                 }
           )
        )

        cbc_item = self.refresh(cbc_item)
        self.assertEqual(name, cbc_item.name)

        cells = cbc_item.cells
        self.assertIsInstance(cells, list)
        self.assertEqual(5, len(cells))

        cell = cells[0]
        self.assertIsInstance(cell, EntityCellRegularField)
        self.assertEqual(field_fname, cell.value)

        self.assertEqual(field_lname, cells[1].value)

        cell = cells[2]
        self.assertIsInstance(cell, EntityCellRelation)
        self.assertEqual(loves.id, cell.value)

        cell = cells[3]
        self.assertIsInstance(cell, EntityCellFunctionField)
        self.assertEqual(funcfield.name, cell.value)

        cell = cells[4]
        self.assertIsInstance(cell, EntityCellCustomField)
        self.assertEqual(str(customfield.id), cell.value)

    def test_delete_customblock(self):
        ct = ContentType.objects.get_for_model(Contact)
        cbci = CustomBlockConfigItem.objects.create(content_type=ct, name='Info')
        loc = BlockDetailviewLocation.create(block_id=cbci.generate_id(), order=5, zone=BlockDetailviewLocation.RIGHT, model=Contact)

        self.assertPOST200('/creme_config/blocks/custom/delete', data={'id': cbci.id})
        self.assertDoesNotExist(cbci)
        self.assertDoesNotExist(loc)
