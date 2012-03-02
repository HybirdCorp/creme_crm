# -*- coding: utf-8 -*-

try:
    from time import sleep

    from functools import partial

    from django.contrib.auth.models import User
    from django.contrib.sessions.models import Session

    from creme_core.models import *
    from creme_core.gui.listview import get_field_name_from_pattern
    from creme_core.gui.last_viewed import LastViewedItem
    from creme_core.gui.bulk_update import _BulkUpdateRegistry
    from creme_core.gui.block import Block, SimpleBlock, SpecificRelationsBlock, _BlockRegistry, BlocksManager
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation

    from activities.models import Meeting, Activity
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('GuiTestCase', 'BulkUpdateRegistryTestCase', 'ListViewStateTestCase',
           'BlockRegistryTestCase', 'BlocksManagerTestCase',
          )


class GuiTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def test_last_viewed_items(self):
        self.login()

        class FakeRequest(object):
            def __init__(self):
                sessions = Session.objects.all()
                assert 1 == len(sessions)
                self.session = sessions[0].get_decoded()

        def get_items():
            #try:
            with self.assertNoException():
                return FakeRequest().session['last_viewed_items']
            #except Exception as e:
                #self.fail(str(e))

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


class BulkUpdateRegistryTestCase(CremeTestCase):
    def setUp(self):
        self.bulk_update_registry = _BulkUpdateRegistry()

    def test_bulk_update_registry01(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Organisation)

        self.assertTrue(is_bulk_updatable(field_name='siren', exclude_unique=False)) # Inner editable
        self.assertTrue(is_bulk_updatable(field_name='name'))
        self.assertTrue(is_bulk_updatable(field_name='phone'))

        self.assertFalse(is_bulk_updatable(field_name='created')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='billing_address')) # Editable = False
        self.assertFalse(is_bulk_updatable(field_name='siren')) # Unique

    def test_bulk_update_registry02(self):
        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Contact)

        self.assertTrue(is_bulk_updatable(field_name='first_name'))
        self.assertTrue(is_bulk_updatable(field_name='last_name'))

        # Automatically inherited from CremeEntity excluded fields (editable = false)
        self.assertFalse(is_bulk_updatable(field_name='modified'))
        self.assertFalse(is_bulk_updatable(field_name='shipping_address'))
        self.assertFalse(is_bulk_updatable(field_name='is_deleted'))

    def test_bulk_update_registry03(self):
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable = partial(self.bulk_update_registry.is_bulk_updatable, model=Activity)

        activity_excluded_fields = ['type', 'start_date', 'end_date', 'busy', 'is_all_day']

        bulk_update_registry.register((Activity, activity_excluded_fields))

        self.assertTrue(is_bulk_updatable(field_name='title'))
        self.assertTrue(is_bulk_updatable(field_name='description'))

        self.assertFalse(is_bulk_updatable(field_name='type'))
        self.assertFalse(is_bulk_updatable(field_name='end_date'))
        self.assertFalse(is_bulk_updatable(field_name='busy'))

    def test_bulk_update_registry04(self): # Inheritance test case Parent / Child
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable_for_activity = partial(bulk_update_registry.is_bulk_updatable, model=Activity)
        is_bulk_updatable_for_meeting = partial(bulk_update_registry.is_bulk_updatable, model=Meeting)

        activity_excluded_fields = ['type', 'start', 'end', 'busy', 'is_all_day']

        bulk_update_registry.register((Activity, activity_excluded_fields))

        self.assertFalse(is_bulk_updatable_for_activity(field_name='type'))
        self.assertFalse(is_bulk_updatable_for_activity(field_name='end'))
        self.assertFalse(is_bulk_updatable_for_activity(field_name='busy'))

        bulk_update_registry.register((Meeting, []))

        # inherited automatically from CremeEntity
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='created'))

        # inherited from Activity excluded fields
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='type'))
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='end'))
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='busy'))

    def test_bulk_update_registry05(self): # Inheritance test case Child / Parent
        bulk_update_registry = self.bulk_update_registry

        is_bulk_updatable_for_meeting = partial(bulk_update_registry.is_bulk_updatable, model=Meeting)

        bulk_update_registry.register((Meeting, []))

        self.assertTrue(is_bulk_updatable_for_meeting(field_name='type'))
        self.assertTrue(is_bulk_updatable_for_meeting(field_name='end'))
        self.assertTrue(is_bulk_updatable_for_meeting(field_name='busy'))

        activity_excluded_fields = ['type', 'start', 'end', 'busy', 'is_all_day']
        bulk_update_registry.register((Activity, activity_excluded_fields))

        self.assertFalse(is_bulk_updatable_for_meeting(field_name='type'))
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='end'))
        self.assertFalse(is_bulk_updatable_for_meeting(field_name='busy'))


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
        self.login()
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Mylove')


        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_1')
            verbose_name  = u'Testing purpose'

            def detailview_display(self, context): return self._render(self.get_block_template_context(context))


        class FoobarBlock2(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'foobar_block_2')
            verbose_name  = u'Testing purpose'
            target_ctypes = (Contact, Organisation)


        class FoobarBlock3(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'foobar_block_3')
            verbose_name  = u'Testing purpose'

            target_ctypes = (Organisation,) #No contact


        class FoobarBlock4(SimpleBlock):
            id_           = Block.generate_id('creme_core', 'foobar_block_4')
            verbose_name  = u'Testing purpose'
            configurable  = False # <------


        class FoobarBlock5(Block): #No detailview_display()
            id_           = Block.generate_id('creme_core', 'foobar_block_5')
            verbose_name  = u'Testing purpose'

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
            def home_display(self, context):           return '<table id="%s"></table>' % self.id_


        class _FoobarInstanceBlock(Block):
            verbose_name  = u'Testing purpose'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item


        class FoobarInstanceBlock1(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_1')

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock2(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_2')
            target_ctypes = (Contact, Organisation) # <-- OK !!

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock3(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_3')
            target_ctypes = (Organisation, Meeting) # <-- KO !!

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock4(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_4')

            def home_display(self, context): #<====== not detailview_display()
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        create_ibci = InstanceBlockConfigItem.objects.create
        ibci1 = create_ibci(entity=casca, verbose=u"I am an awesome block", data='',
                            block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock1, casca, ''),
                           )
        ibci2 = create_ibci(entity=casca, verbose=u"I am an awesome block too", data='',
                            block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock2, casca, ''),
                           )
        create_ibci(entity=casca, verbose=u"I am a poor block", data='',
                    block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock3, casca, ''),
                   )
        create_ibci(entity=casca, verbose=u"I am a poor block too", data='',
                    block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock4, casca, ''),
                   )

        block_registry = _BlockRegistry()
        foobar_block1 = FoobarBlock1()
        foobar_block2 = FoobarBlock2(); self.assertTrue(hasattr(foobar_block2, 'detailview_display'))
        foobar_block5 = FoobarBlock5(); self.assertFalse(hasattr(foobar_block5, 'detailview_display'))

        rtype1 = RelationType.create(('test-subject_loves', 'loves'), ('test-object_loved', 'is loved by'))[0]
        RelationBlockItem.create(rtype1.id)

        block_registry.register(foobar_block1, foobar_block2, FoobarBlock3(), FoobarBlock4(), foobar_block5)
        block_registry.register_4_instance(FoobarInstanceBlock1, FoobarInstanceBlock2, FoobarInstanceBlock3, FoobarInstanceBlock4)

        blocks = sorted(block_registry.get_compatible_blocks(Contact), key=lambda b: b.id_)
        self.assertEqual(5, len(blocks))
        self.assertEqual([foobar_block1, foobar_block2], blocks[:2])

        block = blocks[2]
        self.assertIsInstance(block, FoobarInstanceBlock1)
        self.assertEqual(ibci1.block_id, block.id_)

        block = blocks[3]
        self.assertIsInstance(block, FoobarInstanceBlock2)
        self.assertEqual(ibci2.block_id, block.id_)

        block = blocks[4]
        self.assertIsInstance(block, SpecificRelationsBlock)
        self.assertEqual((rtype1.id,), block.relation_type_deps)

    def test_get_compatible_portal_blocks01(self):
        self.login()
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Mylove')

        class FoobarBlock1(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_1')
            verbose_name  = u'Testing purpose'

            ##NB: only portal_display() method
            #def detailview_display(self, context): return self._render(self.get_block_template_context(context))
            #def home_display(self, context): return '<table id="%s"></table>' % self.id_
            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock2(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_2')
            verbose_name  = u'Testing purpose'
            configurable  = False # <----

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock3(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_3')
            verbose_name  = u'Testing purpose'

            #def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
            def home_display(self, context): return '<table id="%s"></table>' % self.id_


        class FoobarBlock4(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_4')
            verbose_name  = u'Testing purpose'
            target_apps   = ('documents', 'persons', 'activities') # <-- OK

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class FoobarBlock5(Block):
            id_           = Block.generate_id('creme_core', 'foobar_block_5')
            verbose_name  = u'Testing purpose'
            target_apps   = ('documents', 'activities') # <-- KO !!

            def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_


        class _FoobarInstanceBlock(Block):
            verbose_name  = u'Testing purpose'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item


        class FoobarInstanceBlock1(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_1')

            def portal_display(self, context, ct_ids):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock2(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_2')
            target_apps   = ('documents', 'persons') # <-- OK !!

            def portal_display(self, context, ct_ids):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock3(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_3')
            target_apps   = ('documents', 'tickets') # <-- KO !!

            def portal_display(self, context, ct_ids):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)


        class FoobarInstanceBlock4(_FoobarInstanceBlock):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_4')

            def home_display(self, context): #<====== not portal_display()
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)



        create_ibci = InstanceBlockConfigItem.objects.create
        ibci1 = create_ibci(entity=casca, verbose=u"I am an awesome block", data='',
                            block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock1, casca, ''),
                           )
        ibci2 = create_ibci(entity=casca, verbose=u"I am an awesome block too", data='',
                            block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock2, casca, ''),
                           )
        create_ibci(entity=casca, verbose=u"I am a poor block", data='',
                    block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock3, casca, ''),
                   )
        create_ibci(entity=casca, verbose=u"I am a poor block too", data='',
                    block_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock4, casca, ''),
                   )

        block_registry = _BlockRegistry()

        foobar_block1 = FoobarBlock1()
        foobar_block4 = FoobarBlock4()
        block_registry.register(foobar_block1, FoobarBlock2(), FoobarBlock3(), foobar_block4, FoobarBlock5())
        block_registry.register_4_instance(FoobarInstanceBlock1, FoobarInstanceBlock2, FoobarInstanceBlock3, FoobarInstanceBlock4)

        blocks = sorted(block_registry.get_compatible_portal_blocks('persons'), key=lambda b: b.id_)
        self.assertEqual(4, len(blocks))
        self.assertEqual([foobar_block1, foobar_block4], blocks[:2])
        self.assertEqual([ibci1.block_id, ibci2.block_id], [block.id_ for block in blocks[2:]])

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

    def test_get_blocks01(self):
        class QuuxBlock1(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'BlockRegistryTestCase__test_get_blocks_1')
            verbose_name = u'Testing purpose #1'

        class QuuxBlock2(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'BlockRegistryTestCase__test_get_blocks_2')
            verbose_name = u'Testing purpose #2'

        class QuuxBlock3(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'BlockRegistryTestCase__test_get_blocks_3')
            verbose_name = u'Testing purpose #3'

        self.assertFalse(InstanceBlockConfigItem.id_is_specific(QuuxBlock1.id_))

        block1 = QuuxBlock1()
        block2 = QuuxBlock2()

        block_registry = _BlockRegistry()
        block_registry.register(block1, block2, QuuxBlock3())

        self.assertEqual([block1, block2], block_registry.get_blocks([block1.id_, block2.id_]))

        #-------------
        blocks = block_registry.get_blocks([SimpleBlock.generate_id('creme_core', 'BlockRegistryTestCase__test_get_blocks_4')]) #not registered
        self.assertEqual(1, len(blocks))
        self.assertIsInstance(blocks[0], Block)

    #def test_get_blocks02(self): TODO: with specific relation blocks

    def test_block_4_model01(self):
        block_registry = _BlockRegistry()

        block = block_registry.get_block_4_object(Organisation)
        self.assertEqual(u'modelblock_persons-organisation', block.id_)
        self.assertEqual((Organisation,), block.dependencies)

    def test_block_4_model02(self):
        block_registry = _BlockRegistry()

        self.login()
        casca = Contact.objects.create(user=self.user, first_name='Casca', last_name='Mylove')

        block = block_registry.get_block_4_object(casca)
        self.assertEqual(u'modelblock_persons-contact', block.id_)
        self.assertEqual((Contact,), block.dependencies)

    def test_block_4_model03(self):
        class ContactBlock(SimpleBlock):
            template_name = 'persons/templatetags/block_contact.html'

        block = ContactBlock()

        block_registry = _BlockRegistry()
        block_registry.register_4_model(Contact, block)

        self.assertIs(block_registry.get_block_4_object(Contact), block)
        self.assertEqual(u'modelblock_persons-contact', block.id_)
        self.assertEqual((Contact,), block.dependencies)

    def test_block_4_instance01(self):
        self.login()

        create_contact = Contact.objects.create
        casca = create_contact(user=self.user, first_name='Casca', last_name='Mylove')

        class ContactBlock(Block):
            id_  = InstanceBlockConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (Organisation,)
            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                            self.id_, self.ibci.entity
                        ) #useless :)

        self.assertTrue(InstanceBlockConfigItem.id_is_specific(ContactBlock.id_))

        ibci = InstanceBlockConfigItem.objects \
                                      .create(entity=casca,
                                              block_id=InstanceBlockConfigItem.generate_id(ContactBlock, casca, ''),
                                              verbose=u"I am an awesome block",
                                              data='',
                                             )

        block_registry = _BlockRegistry()
        block_registry.register_4_instance(ContactBlock)

        blocks = block_registry.get_blocks([ibci.block_id])
        self.assertEqual(1, len(blocks))

        block = blocks[0]
        self.assertIsInstance(block, ContactBlock)
        self.assertEqual(ibci, block.ibci)
        self.assertEqual(ibci.block_id, block.id_)
        self.assertEqual((Organisation,), block.dependencies)

        #-----------------------------------------------------------------------
        #In detailviews of an entity we give it in order to compute dependencies correctly
        judo = create_contact(user=self.user, first_name='Judo',  last_name='Doe')
        blocks = block_registry.get_blocks([ibci.block_id], entity=judo)
        self.assertEqual((Organisation, Contact), blocks[0].dependencies)

        hawk = Organisation.objects.create(user=self.user, name='Hawk')
        blocks = block_registry.get_blocks([ibci.block_id], entity=hawk)
        self.assertEqual((Organisation,), blocks[0].dependencies)

        #-----------------------------------------------------------------------
        bad_block_id = InstanceBlockConfigItem.generate_base_id('creme_core', 'does_not_exist') + '#%s_' % casca.id
        InstanceBlockConfigItem.objects.create(entity=casca,
                                               block_id=bad_block_id,
                                               verbose=u"I am bad",
                                               data=''
                                              )
        blocks = block_registry.get_blocks([bad_block_id])
        self.assertEqual(1, len(blocks))
        self.assertIsInstance(blocks[0], Block)

    def test_block_4_instance02(self):
        self.login()

        class BaseBlock(Block):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'base_block') # <====== Used twice !!
            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity) #useless :)

        class ContactBlock(BaseBlock): pass
        class OrgaBlock(BaseBlock): pass

        block_registry = _BlockRegistry()
        block_registry.register_4_instance(ContactBlock)
        self.assertRaises(_BlockRegistry.RegistrationError, block_registry.register_4_instance, OrgaBlock)

    #TODO different keys


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

        self.assertDictEqual({block1.id_: set([]),
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

        with self.assertNoException():
            fake_context = {mngr.var_name: mngr}

        self.assertIs(mngr, BlocksManager.get(fake_context))

    #TODO: test def get_state(self, block_id, user)
