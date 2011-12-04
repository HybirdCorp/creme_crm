# -*- coding: utf-8 -*-

try:
    from django.template import Template, RequestContext
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import BlockDetailviewLocation, BlockPortalLocation, BlockMypageLocation
    from creme_core.gui.block import block_registry, SimpleBlock, BlocksManager
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error:', e


class CremeBlockTagsTestCase(CremeTestCase):
    def test_import_n_display_block(self):
        blockstr = '<div>FOOBAR</div>'

        class FooBlock(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'test_import_n_display_block')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return blockstr

        block_registry.register(FooBlock())

        try:
            template = Template("{% load creme_block %}"
                                "{% import_block from_app 'creme_core' named 'test_import_n_display_block' as 'my_block' %}"
                                "{% display_block_detailview 'my_block' %}"
                               )
            render = template.render(RequestContext({}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(blockstr, render.strip())

    def test_import_n_display_block_on_portal(self):
        blockstr = '<div>FOOBAR</div>'

        class FooBlock(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'test_import_n_display_block_on_portal')
            verbose_name = u'Testing purpose'

            def portal_display(self, context, ct_ids):
                self.ct_ids = ct_ids
                return blockstr

        block1 = FooBlock()
        block_registry.register(block1)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        try:
            template = Template("{% load creme_block %}"
                                "{% import_block from_app 'creme_core' named 'test_import_n_display_block_on_portal' as 'my_block' %}"
                                "{% display_block_portal 'my_block' ct_ids %}"
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual(blockstr, render.strip())
        self.assertEqual(ct_ids, block1.ct_ids)

    def test_import_n_display_on_detail_from_conf01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def detailview_display(self, context):
                return self.blockstr

        block_zones = [BlockDetailviewLocation.TOP]   * 2 + \
                      [BlockDetailviewLocation.LEFT]      + \
                      [BlockDetailviewLocation.RIGHT] * 3 + \
                      [BlockDetailviewLocation.BOTTOM]
        blocks = []

        for i, zone in enumerate(block_zones, start=1):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_':      TestBlock.generate_id('creme_core', 'test_import_n_display_on_detail_from_conf01_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockDetailviewLocation.create(block_id=block.id_, order=i, zone=zone)

        block_registry.register(*blocks)

        try:
            template = Template("{% load creme_block %}"
                                "{% import_detailview_blocks %}"
                                "<div>{% display_detailview_blocks top %}</div>"
                                "<div>{% display_detailview_blocks left %}</div>"
                                "<div>{% display_detailview_blocks right %}</div>"
                                "<div>{% display_detailview_blocks bottom %}</div>"
                               )
            render = template.render(RequestContext({}, {'object': orga}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p></div>'
                         '<div><p>BLOCK#3</p></div>'
                         '<div><p>BLOCK#4</p><p>BLOCK#5</p><p>BLOCK#6</p></div>'
                         '<div><p>BLOCK#7</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_detail_from_conf02(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def detailview_display(self, context):
                return self.blockstr

        block_zones = [BlockDetailviewLocation.TOP]   * 2 + \
                      [BlockDetailviewLocation.LEFT]      + \
                      [BlockDetailviewLocation.RIGHT] * 3 + \
                      [BlockDetailviewLocation.BOTTOM]
        blocks = []

        for i, zone in enumerate(block_zones, start=1):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_':      TestBlock.generate_id('creme_core', 'test_import_n_display_on_detail_from_conf02_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockDetailviewLocation.create(block_id=block.id_, order=i, zone=zone, model=Organisation)

        BlockDetailviewLocation.create(block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.BOTTOM) #default conf should be ignored
        block_registry.register(*blocks)

        try:
            template = Template("{% load creme_block %}"
                                "{% import_detailview_blocks %}"
                                "<div>{% display_detailview_blocks top %}</div>"
                                "<div>{% display_detailview_blocks left %}</div>"
                                "<div>{% display_detailview_blocks right %}</div>"
                                "<div>{% display_detailview_blocks bottom %}</div>"
                               )
            render = template.render(RequestContext({}, {'object': orga}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p></div>'
                         '<div><p>BLOCK#3</p></div>'
                         '<div><p>BLOCK#4</p><p>BLOCK#5</p><p>BLOCK#6</p></div>'
                         '<div><p>BLOCK#7</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_portal_from_conf01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def portal_display(self, context, ct_ids):
                return self.blockstr

        blocks = []

        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_':      TestBlock.generate_id('creme_core', 'test_import_n_display_on_portal_from_conf01_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i)

        block_registry.register(*blocks)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        try:
            template = Template("{% load creme_block %}"
                                "{% import_portal_blocks 'persons' %}"
                                "<div>{% display_portal_blocks ct_ids %}</div>"
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_portal_from_conf02(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def portal_display(self, context, ct_ids):
                return self.blockstr

        blocks = []

        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_':      TestBlock.generate_id('creme_core', 'test_import_n_display_on_portal_from_conf02_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i, app_name='persons')

        BlockPortalLocation.create(block_id=blocks[0].id_, order=1)  #default conf should be ignored
        block_registry.register(*blocks)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        try:
            template = Template("{% load creme_block %}"
                                "{% import_portal_blocks app_name %}"
                                "<div>{% display_portal_blocks ct_ids %}</div>"
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids, 'app_name': 'persons'}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_home_from_conf(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def home_display(self, context):
                return self.blockstr

        blocks = []

        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': TestBlock.generate_id('creme_core', 'test_import_n_display_on_home_from_conf01_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i, app_name='creme_core')

        block_registry.register(*blocks)

        try:
            template = Template("{% load creme_block %}"
                                "{% import_home_blocks %}"
                                "<div>{% display_home_blocks %}</div>"
                               )
            render = template.render(RequestContext({}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_mypage_from_conf(self):
        self.login()
        user = self.user
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def home_display(self, context):
                return self.blockstr

        blocks = []

        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': TestBlock.generate_id('creme_core', 'test_import_n_display_on_mypage_from_conf01_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockMypageLocation.create(block_id=block.id_, order=i, user=user)

        block_registry.register(*blocks)

        context = RequestContext({})
        context['user'] = user

        try:
            template = Template("{% load creme_block %}"
                                "{% import_mypage_blocks %}"
                                "<div>{% display_mypage_blocks %}</div>"
                               )
            render = template.render(context)
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_blocks(self):
        blockstr1 = '<div>FOO</div>'
        blockstr2 = '<div>BAR</div>'

        class FooBlock1(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'test_import_n_display_blocks_1')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return blockstr1

        class FooBlock2(SimpleBlock):
            id_          = SimpleBlock.generate_id('creme_core', 'test_import_n_display_blocks_2')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return blockstr2

        block1 = FooBlock1()
        block2 = FooBlock2()
        #block_registry.register(block1, block2) #useless

        try:
            template = Template("{% load creme_block %}"
                                "{% import_blocks blocks as 'my_blocks' %}"
                                "{% display_blocks 'my_blocks' %}"
                               )
            render = template.render(RequestContext({}, {'blocks': [block1, block2]}))
        except Exception as e:
            self.fail(str(e))

        self.assertEqual('<div>FOO</div><div>BAR</div>', render.strip())

    def test_get_blocks_dependencies(self):
        class TestBlock(SimpleBlock):
            verbose_name  = u'Testing purpose'

            def detailview_display(self, context): return ''

        class FoobarBlock1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__test_get_blocks_dependencies_1')

        class FoobarBlock2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__test_get_blocks_dependencies_2')
            dependencies = (Contact,)

        class FoobarBlock3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__test_get_blocks_dependencies_3')
            dependencies = (Organisation,)

        class FoobarBlock4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__test_get_blocks_dependencies_4')
            dependencies = (Contact, Organisation)

        block1 = FoobarBlock1(); block2 = FoobarBlock2(); block3 = FoobarBlock3(); block4 = FoobarBlock4()

        mngr = BlocksManager()
        mngr.add_group('gname1', block1, block2, block3, block4)

        try:
            template = Template("{% load creme_block %}"
                                "{% import_blocks blocks as 'my_blocks' %}"
                                "{% display_blocks 'my_blocks' %}"
                                "{% get_blocks_dependencies %}"
                               )
            render = template.render(RequestContext({}, {'blocks': [block1, block2, block3, block4]}))
        except Exception as e:
            self.fail(str(e))

        self.assertTrue(render.strip()) #TODO: improve...
