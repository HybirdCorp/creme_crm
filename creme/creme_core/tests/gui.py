# -*- coding: utf-8 -*-

try:
    from time import sleep

    from django.contrib.auth.models import User
    from django.contrib.sessions.models import Session

    from creme_core.models import *
    from creme_core.gui.listview import get_field_name_from_pattern
    from creme_core.gui.last_viewed import LastViewedItem
    from creme_core.gui.bulk_update import BulkUpdateRegistry
    from creme_core.gui.block import Block, SimpleBlock, SpecificRelationsBlock, _BlockRegistry, BlocksManager
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation

    from activities.models import Meeting, Activity
except Exception, e:
    print 'Error:', e


__all__ = ('GuiTestCase', 'ListViewStateTestCase', 'BlockRegistryTestCase', 'BlocksManagerTestCase')


class GuiTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.bulk_update_registry = BulkUpdateRegistry()

    def test_last_viewed_items(self):
        self.login()

        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_items():
            try:
                return FakeRequest().session['last_viewed_items']
            except Exception, e:
                self.fail(str(e))

        self.assertEqual(0, len(LastViewedItem.get_all(FakeRequest())))

        contact01 = Contact.objects.create(user=self.user, first_name='Casca', last_name='Mylove')
        contact02 = Contact.objects.create(user=self.user, first_name='Puck',  last_name='Elfman')
        contact03 = Contact.objects.create(user=self.user, first_name='Judo',  last_name='Doe')

        self.assertEqual(200, self.client.get(contact01.get_absolute_url()).status_code)
        items = get_items()
        self.assertEqual(1, len(items))
        self.assertEqual(contact01.pk, items[0].pk)

        self.assertEqual(200, self.client.get(contact02.get_absolute_url()).status_code)
        self.assertEqual(200, self.client.get(contact03.get_absolute_url()).status_code)
        items = get_items()
        self.assertEqual(3, len(items))
        self.assertEqual([contact03.pk, contact02.pk, contact01.pk], [i.pk for i in items])

        sleep(1)
        contact01.last_name = 'ILoveYou'
        contact01.save()
        self.assertEqual(200, self.client.get(Contact.get_lv_absolute_url()).status_code)
        old_item = get_items()[2]
        self.assertEqual(contact01.pk,       old_item.pk)
        self.assertEqual(unicode(contact01), old_item.name)

        self.assertEqual(200, self.client.get(contact02.get_absolute_url()).status_code)
        self.assertEqual([contact02.pk, contact03.pk, contact01.pk], [i.pk for i in get_items()])

        contact03.delete()
        self.assertEqual(0, CremeEntity.objects.filter(pk=contact03.id).count())
        self.assertEqual(200, self.client.get(Contact.get_lv_absolute_url()).status_code)
        self.assertEqual([contact02.pk, contact01.pk], [i.pk for i in get_items()])

    def test_bulk_update_registry01(self):
        bulk_update_registry = self.bulk_update_registry

        contact_excluded_fields = ['position', 'first_name']
        ce_excluded_fields = ['created']

        bulk_update_registry.register((Contact, contact_excluded_fields))
        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(contact_excluded_fields))

        bulk_update_registry.register((CremeEntity, ce_excluded_fields))
        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(contact_excluded_fields) | set(ce_excluded_fields))

    def test_bulk_update_registry02(self):
        bulk_update_registry    = self.bulk_update_registry
        contact_excluded_fields = ['position', 'first_name']
        orga_excluded_fields    = ['sector', 'name']
        ce_excluded_fields      = ['created']

        bulk_update_registry.register(
                                        (Contact,      contact_excluded_fields),
                                        (CremeEntity,  ce_excluded_fields),
                                        (Organisation, orga_excluded_fields),
                                     )
        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact),      set(contact_excluded_fields) | set(ce_excluded_fields))
        self.assertEqual(bulk_update_registry.get_excluded_fields(Organisation), set(orga_excluded_fields)    | set(ce_excluded_fields))

    def test_bulk_update_registry03(self):
        bulk_update_registry     = self.bulk_update_registry
        contact_excluded_fields  = ['position', 'first_name']
        orga_excluded_fields     = ['sector', 'name']
        ce_excluded_fields       = ['created']
        activity_excluded_fields = ['title']
        meeting_excluded_fields  = ['place']

        bulk_update_registry.register(
                                        (Contact,      contact_excluded_fields),
                                        (CremeEntity,  ce_excluded_fields),
                                        (Organisation, orga_excluded_fields),
                                        (Meeting,      meeting_excluded_fields),
                                        (Activity,     activity_excluded_fields),
                                     )

        meeting_excluded_fields_expected = set(activity_excluded_fields)   | set(ce_excluded_fields) | set(meeting_excluded_fields)
        self.assertEqual(bulk_update_registry.get_excluded_fields(Meeting), meeting_excluded_fields_expected)

        bulk_update_registry.register((Activity, ['status']))
        activity_excluded_fields_expected = set(activity_excluded_fields) | set(ce_excluded_fields) | set(['status'])
        self.assertEqual(bulk_update_registry.get_excluded_fields(Activity), activity_excluded_fields_expected)

    def test_bulk_update_registry04(self):
        bulk_update_registry = self.bulk_update_registry
        ce_excluded_fields = ['created']

        bulk_update_registry.register(
                                        (CremeEntity,  ce_excluded_fields),
                                     )
        self.assertEqual(bulk_update_registry.get_excluded_fields(Contact), set(ce_excluded_fields))


class ListViewStateTestCase(CremeTestCase):
    def test_get_field_name_from_pattern(self):
        self.assertEqual('foo__bar__plop', get_field_name_from_pattern('foo__bar__plop__icontains'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__icontains'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__exact'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__creme-boolean'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar__exact'))
        self.assertEqual('foo__bar',       get_field_name_from_pattern('foo__bar'))
        self.assertEqual('foo',            get_field_name_from_pattern('foo'))
        self.assertEqual('foo',            get_field_name_from_pattern('foo__isnull'))


class BlockRegistryTestCase(CremeTestCase):
    def test_get_compatible_blocks(self):
        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_blocks_1')
            verbose_name  = u'Testing purpose'

            def detailview_display(self, context): return self._render(self.get_block_template_context(context))


        class FoobarBlock2(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_blocks_2')
            verbose_name  = u'Testing purpose'
            target_ctypes = (Contact, Organisation)


        class FoobarBlock3(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_blocks_3')
            verbose_name  = u'Testing purpose'

            target_ctypes = (Organisation,) #No contact


        class FoobarBlock4(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_blocks_4')
            verbose_name  = u'Testing purpose'
            configurable  = False # <------


        class FoobarBlock5(Block): #No detailview_display()
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_blocks_5')
            verbose_name  = u'Testing purpose'

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_


        block_registry = _BlockRegistry()
        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2(); self.assert_(hasattr(foobar_block2, 'detailview_display'))
        foobar_block5 = FoobarBlock5(); self.assertFalse(hasattr(foobar_block5, 'detailview_display'))

        block_registry.register(foobar_block1, foobar_block2, FoobarBlock3(), FoobarBlock4(), foobar_block5)
        self.assertEqual([foobar_block1, foobar_block2],
                         sorted(block_registry.get_compatible_blocks(Contact), key=lambda b: b.id_)
                        )

    def test_get_compatible_portal_blocks01(self):
        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks01_1')
            verbose_name  = u'Testing purpose'

            ##NB: only portal_display() method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def home_display(self, context): return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks01_2')
            verbose_name  = u'Testing purpose'
            configurable  = False # <----

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock3(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks01_3')
            verbose_name  = u'Testing purpose'

            #def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
            def home_display(self, context): return '<table id="%s"></table>' % self.id_


        class FoobarBlock4(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks01_4')
            verbose_name  = u'Testing purpose'
            target_apps   = ('documents', 'persons', 'activities') # <-- OK

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock5(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks01_5')
            verbose_name  = u'Testing purpose'
            target_apps   = ('documents', 'activities') # <-- KO !!

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        block_registry = _BlockRegistry()

        foobar_block1 = FoobarBlock1()
        foobar_block4 = FoobarBlock4()
        block_registry.register(foobar_block1, FoobarBlock2(), FoobarBlock3(), foobar_block4, FoobarBlock5())

        blocks = sorted(block_registry.get_compatible_portal_blocks('persons'), key=lambda b: b.id_)
        self.assertEqual([foobar_block1, foobar_block4], blocks)

    def test_get_compatible_portal_blocks02(self): #home
        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks02_1')
            verbose_name  = u'Testing purpose'

            ##NB: only home_display() method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
            def home_display(self, context): return '<table id="%s"></table>' % self.id_

        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks02_2')
            verbose_name  = u'Testing purpose'
            configurable  = False # <----

            def home_display(self, context): return '<table id="%s"></table>' % self.id_

        class FoobarBlock3(Block):
            id_           = Block.generate_id('creme_core', 'BlockRegistryTestCase__test_get_compatible_portal_blocks02_3')
            verbose_name  = u'Testing purpose'

            #def home_display(self, context): return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_

        block_registry = _BlockRegistry()

        foobar_block1 = FoobarBlock1()
        block_registry.register(foobar_block1, FoobarBlock2(), FoobarBlock3())

        blocks = list(block_registry.get_compatible_portal_blocks('creme_core'))
        self.assertEqual([foobar_block1], blocks)


class BlocksManagerTestCase(CremeTestCase):
    def test_manage01(self):
        class TestBlock(SimpleBlock):
            verbose_name  = u'Testing purpose'

        class FoobarBlock1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage01_1')

        class FoobarBlock2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage01_2')
            dependencies = (Contact,)

        class FoobarBlock3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage01_3')
            dependencies = (Organisation,)

        class FoobarBlock4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__manage01_4')
            dependencies = (Contact, Organisation)

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block3 = FoobarBlock3()
        block4 = FoobarBlock4()

        mngr = BlocksManager()
        self.assertFalse(mngr.block_is_registered(block1))
        self.assertTrue(hasattr(BlocksManager, 'Error'))

        name1 = 'gname1'
        mngr.add_group(name1, block1, block2, block3)
        self.assertTrue(mngr.block_is_registered(block1))
        self.assertFalse(mngr.block_is_registered(block4))
        self.assertRaises(BlocksManager.Error, mngr.add_group, name1, block4) #same name
        self.assertDictEqual({block1.id_: set(),
                              block2.id_: set(),
                              block3.id_: set(),
                             },
                             mngr.get_dependencies_map()
                            )
        self.assertRaises(BlocksManager.Error, mngr.add_group, 'gname2', block4) #deps already solved

    def test_manage02(self):
        class TestBlock(SimpleBlock):
            verbose_name  = u'Testing purpose'

        class FoobarBlock1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage02_1')

        class FoobarBlock2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage02_2')
            dependencies = (Contact,)

        class FoobarBlock3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage02_3')
            dependencies = (Organisation,)

        class FoobarBlock4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage02_4')
            dependencies = (Contact, Organisation)

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block3 = FoobarBlock3()
        block4 = FoobarBlock4()

        mngr = BlocksManager()
        mngr.add_group('gname1', block1, block2, block3)
        mngr.add_group('gname2', block4)
        self.assertEqual(['gname1', 'gname2'], mngr.get_remaining_groups())

        group = mngr.pop_group('gname1')
        self.assertEqual(['gname2'], mngr.get_remaining_groups())
        self.assertRaises(KeyError, mngr.pop_group, 'gname1')

        self.assertDictEqual({block1.id_: set(),
                              block2.id_: set([block4.id_]),
                              block3.id_: set([block4.id_]),
                              block4.id_: set([block2.id_, block3.id_]),
                             },
                             mngr.get_dependencies_map()
                            )

    def test_manage03(self): #relation blocks
        rtype1_pk = 'test-subject_loves'
        rtype1, srtype1 = RelationType.create((rtype1_pk, 'loves'), ('test-object_loved',  'is loved by'))

        rtype2_pk = 'test-subject_follows'
        rtype2, srtype2 = RelationType.create((rtype2_pk, 'follow'), ('test-object_followed',  'is followed by'))

        class TestBlock(SimpleBlock):
            verbose_name  = u'Testing purpose'

        class FoobarBlock1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_1')

        class FoobarBlock2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_2')
            dependencies = (Contact,)

        class FoobarBlock3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_3')
            dependencies = (Relation,)

        self.assertEqual((), FoobarBlock3.relation_type_deps)

        class FoobarBlock4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_4')
            dependencies = (Relation,)
            relation_type_deps = (rtype1_pk,)

        class FoobarBlock5(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_5')
            dependencies = (Relation,)
            relation_type_deps = (rtype1_pk, rtype2_pk)

        class FoobarBlock6(SpecificRelationsBlock):
            verbose_name = u'Testing purpose'

        self.assertEqual((Relation,), FoobarBlock6.dependencies)

        block1 = FoobarBlock1(); block2 = FoobarBlock2()
        block3 = FoobarBlock3(); block4 = FoobarBlock4(); block5 = FoobarBlock5()
        block6 = FoobarBlock6(id_=TestBlock.generate_id('creme_core', 'BlocksManagerTestCase__test_manage03_6'),
                              relation_type_id=rtype2_pk
                             )

        mngr = BlocksManager()
        mngr.add_group('gname1', block1, block2, block3)
        mngr.add_group('gname2', block4, block5, block6)
        self.assertEqual(set([rtype1_pk, rtype2_pk]), mngr.get_used_relationtypes_ids())

        self.assertDictEqual({
                                block1.id_: set([]),
                                block2.id_: set([]),
                                block3.id_: set([]),
                                block4.id_: set([block5.id_]),
                                block5.id_: set([block4.id_, block6.id_]),
                                block6.id_: set([block5.id_]),
                             },
                             mngr.get_dependencies_map()
                            )

        rtypes_ids = [srtype1.id, srtype2.id]
        mngr.set_used_relationtypes_ids(rtypes_ids)
        self.assertEqual(set(rtypes_ids), mngr.get_used_relationtypes_ids())

    def test_get(self):
        mngr = BlocksManager()

        try:
            fake_context = {mngr.var_name: mngr}
        except Exception, e:
            self.fail(str(e))

        self.assertIs(mngr, BlocksManager.get(fake_context))

    #TODO: test def get_state(self, block_id, user)
