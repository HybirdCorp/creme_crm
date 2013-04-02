# -*- coding: utf-8 -*-

try:
    from django.template import Template, RequestContext
    from django.core.serializers.json import simplejson
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import (BlockDetailviewLocation, BlockPortalLocation,
                                   BlockMypageLocation, InstanceBlockConfigItem,
                                   Relation)
    from creme.creme_core.gui.block import block_registry, Block, SimpleBlock, BlocksManager
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class CremeBlockTagsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        BlockDetailviewLocation.objects.all().delete()
        BlockPortalLocation.objects.all().delete()
        BlockMypageLocation.objects.all().delete()

    def test_import_n_display_block(self):
        blockstr = '<div>FOOBAR</div>'
        name = 'CremeBlockTagsTestCase__import_n_display_block'

        class FooBlock(Block):
            id_          = Block.generate_id('creme_core', name)
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return blockstr

        block_registry.register(FooBlock())

        with self.assertNoException():
            template = Template("{%% load creme_block %%}"
                                "{%% import_block from_app 'creme_core' named '%(name)s' as 'my_block' %%}"
                                "{%% display_block_detailview 'my_block' %%}" % {'name': name}
                               )
            render = template.render(RequestContext({}))

        self.assertEqual(blockstr, render.strip())

    def test_import_n_display_block_on_portal(self):
        blockstr = '<div>FOOBAR</div>'
        name = 'CremeBlockTagsTestCase__import_n_display_block_on_portal'

        class FooBlock(SimpleBlock):
            id_ = SimpleBlock.generate_id('creme_core', name)
            verbose_name = u'Testing purpose'

            def portal_display(self, context, ct_ids):
                self.ct_ids = ct_ids
                return blockstr

        block1 = FooBlock()
        block_registry.register(block1)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        with self.assertNoException():
            template = Template("{%% load creme_block %%}"
                                "{%% import_block from_app 'creme_core' named '%(name)s' as 'my_block' %%}"
                                "{%% display_block_portal 'my_block' ct_ids %%}" % {'name': name}
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids}))

        self.assertEqual(blockstr, render.strip())
        self.assertEqual(ct_ids, block1.ct_ids)

    def test_import_n_display_on_detail_from_conf01(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(Block):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def detailview_display(self, context):
                return self.blockstr

        block_zones = [BlockDetailviewLocation.TOP]   * 2 + \
                      [BlockDetailviewLocation.LEFT]      + \
                      [BlockDetailviewLocation.RIGHT] * 3 + \
                      [BlockDetailviewLocation.BOTTOM]
        blocks = []

        gen_id = TestBlock.generate_id
        for i, zone in enumerate(block_zones, start=1):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': gen_id('creme_core',
                                              'CremeBlockTagsTestCase__import_n_display_on_detail_from_conf01_%s' % i,
                                             ),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockDetailviewLocation.create(block_id=block.id_, order=i, zone=zone)

        block_registry.register(*blocks)

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_detailview_blocks %}"
                                "<div>{% display_detailview_blocks top %}</div>"
                                "<div>{% display_detailview_blocks left %}</div>"
                                "<div>{% display_detailview_blocks right %}</div>"
                                "<div>{% display_detailview_blocks bottom %}</div>"
                               )
            render = template.render(RequestContext({}, {'object': orga}))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p></div>'
                         '<div><p>BLOCK#3</p></div>'
                         '<div><p>BLOCK#4</p><p>BLOCK#5</p><p>BLOCK#6</p></div>'
                         '<div><p>BLOCK#7</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_detail_from_conf02(self):
        self.login()
        orga = Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(Block):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def detailview_display(self, context):
                return self.blockstr

        block_zones = [BlockDetailviewLocation.TOP]   * 2 + \
                      [BlockDetailviewLocation.LEFT]      + \
                      [BlockDetailviewLocation.RIGHT] * 3 + \
                      [BlockDetailviewLocation.BOTTOM]
        blocks = []

        gen_id = TestBlock.generate_id
        for i, zone in enumerate(block_zones, start=1):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_':      gen_id('creme_core', 'CremeBlockTagsTestCase__import_n_display_on_detail_from_conf02_%s' % i),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockDetailviewLocation.create(block_id=block.id_, order=i, zone=zone, model=Organisation)

        BlockDetailviewLocation.create(block_id=blocks[0].id_, order=1, zone=BlockDetailviewLocation.BOTTOM) #default conf should be ignored
        block_registry.register(*blocks)

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_detailview_blocks %}"
                                "<div>{% display_detailview_blocks top %}</div>"
                                "<div>{% display_detailview_blocks left %}</div>"
                                "<div>{% display_detailview_blocks right %}</div>"
                                "<div>{% display_detailview_blocks bottom %}</div>"
                               )
            render = template.render(RequestContext({}, {'object': orga}))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p></div>'
                         '<div><p>BLOCK#3</p></div>'
                         '<div><p>BLOCK#4</p><p>BLOCK#5</p><p>BLOCK#6</p></div>'
                         '<div><p>BLOCK#7</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_detail_from_conf03(self): # InstanceBlock dependencies
        self.login()

        orga = Organisation.objects.create(user=self.user, name='Xing')

        class OrgaInfoBlock(Block):
            id_          = Block.generate_id('creme_core', 'CremeBlockTagsTestCase__import_n_display_on_detail_from_conf03')
            verbose_name = u'Testing purpose'
            dependencies = (Organisation,)

            def detailview_display(self, context):
                return ('<table id="%s">'
                            '<thead><th>Information on the organisation</th></thead>'
                            '<tbody>'
                                '<tr>'
                                    '<th>Name</th>'
                                    '<td>%s</td>'
                                '</tr>'
                            '</tbody>'
                        '</table>' % (self.id_, context['object'].name)
                       )

        class OrgaInstanceBlock(Block):
            id_  = InstanceBlockConfigItem.generate_base_id('creme_core', 'base_block')
            #dependencies = ()
            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                            self.id_, self.ibci.entity
                        )

        infoblock = OrgaInfoBlock()
        ibci = InstanceBlockConfigItem.objects \
                                      .create(entity=orga,
                                              block_id=InstanceBlockConfigItem.generate_id(OrgaInstanceBlock, orga, ''),
                                              verbose=u"I am an awesome block",
                                              data='',
                                             )

        BlockDetailviewLocation.create(block_id=ibci.block_id, order=1, zone=BlockDetailviewLocation.RIGHT)
        BlockDetailviewLocation.create(block_id=infoblock.id_, order=2, zone=BlockDetailviewLocation.RIGHT)

        block_registry.register(infoblock)
        block_registry.register_4_instance(OrgaInstanceBlock)

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_detailview_blocks %}"
                                "<div>{% display_detailview_blocks right %}</div>"
                                "{% get_blocks_dependencies %}"
                               )
            render = template.render(RequestContext({}, {'object': orga}))

        render = render.strip()

        self.assertIn('BEWARE ! There are some unused imported blocks', render)

        js_varname = 'creme.utils.blocks_deps ='
        idx = render.find(js_varname)
        self.assertNotEqual(-1, idx)

        idx += len(js_varname)

        with self.assertNoException():
            deps_map = simplejson.loads(render[idx:render.find('}', idx) + 1])

        self.assertEqual({infoblock.id_: ibci.block_id,
                          ibci.block_id: infoblock.id_,
                         },
                         deps_map
                        )

    def test_import_n_display_on_portal_from_conf01(self):
        self.login()
        Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def portal_display(self, context, ct_ids):
                return self.blockstr

        blocks = []

        gen_id = TestBlock.generate_id
        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': gen_id('creme_core',
                                              'CremeBlockTagsTestCase__import_n_display_on_portal_from_conf01_%s' % i,
                                             ),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i)

        block_registry.register(*blocks)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_portal_blocks 'persons' %}"
                                "<div>{% display_portal_blocks ct_ids %}</div>"
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids}))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_portal_from_conf02(self):
        self.login()
        Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def portal_display(self, context, ct_ids):
                return self.blockstr

        blocks = []

        gen_id = TestBlock.generate_id
        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': gen_id('creme_core',
                                              'CremeBlockTagsTestCase___import_n_display_on_portal_from_conf02_%s' % i,
                                             ),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i, app_name='persons')

        BlockPortalLocation.create(block_id=blocks[0].id_, order=1)  #default conf should be ignored
        block_registry.register(*blocks)

        ct_ids = [ContentType.objects.get_for_model(Organisation).id]

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_portal_blocks app_name %}"
                                "<div>{% display_portal_blocks ct_ids %}</div>"
                               )
            render = template.render(RequestContext({}, {'ct_ids': ct_ids, 'app_name': 'persons'}))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_home_from_conf(self):
        self.login()
        Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def home_display(self, context):
                return self.blockstr

        blocks = []

        gen_id = TestBlock.generate_id
        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': gen_id('creme_core',
                                              'CremeBlockTagsTestCase__import_n_display_on_home_from_conf01_%s' % i,
                                             ),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockPortalLocation.create(block_id=block.id_, order=i, app_name='creme_core')

        block_registry.register(*blocks)

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_home_blocks %}"
                                "<div>{% display_home_blocks %}</div>"
                               )
            render = template.render(RequestContext({}))

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_on_mypage_from_conf(self):
        self.login()
        user = self.user
        Organisation.objects.create(user=self.user, name='Xing')

        class TestBlock(SimpleBlock):
            verbose_name = u'Testing purpose'
            self.blockstr = None

            def home_display(self, context):
                return self.blockstr

        blocks = []

        gen_id = TestBlock.generate_id
        for i in xrange(1, 4):
            block_class = type('TestBlock_%s' % i, (TestBlock,),
                               {'id_': gen_id('creme_core',
                                              'CremeBlockTagsTestCase___import_n_display_on_mypage_from_conf01_%s' % i,
                                             ),
                                'blockstr': '<p>BLOCK#%s</p>' % i,
                               }
                              )
            block = block_class()
            blocks.append(block)

            BlockMypageLocation.create(block_id=block.id_, order=i, user=user)

        block_registry.register(*blocks)

        context = RequestContext({})
        context['user'] = user

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_mypage_blocks %}"
                                "<div>{% display_mypage_blocks %}</div>"
                               )
            render = template.render(context)

        self.assertEqual('<div><p>BLOCK#1</p><p>BLOCK#2</p><p>BLOCK#3</p></div>',
                         render.strip()
                        )

    def test_import_n_display_blocks(self):
        class FooBlock1(Block):
            id_          = Block.generate_id('creme_core', 'CremeBlockTagsTestCase__import_n_display_blocks_1')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return '<div>FOO</div>'

        class FooBlock2(Block):
            id_          = Block.generate_id('creme_core', 'CremeBlockTagsTestCase__import_n_display_blocks_2')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context):
                return '<div>BAR</div>'

        block1 = FooBlock1()
        block2 = FooBlock2()
        #block_registry.register(block1, block2) #useless

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_blocks blocks as 'my_blocks' %}"
                                "{% display_blocks 'my_blocks' %}"
                               )
            render = template.render(RequestContext({}, {'blocks': [block1, block2]}))

        self.assertEqual('<div>FOO</div><div>BAR</div>', render.strip())

    def test_get_blocks_dependencies(self):
        class TestBlock(Block):
            verbose_name = u'Testing purpose'

            def detailview_display(self, context): return ''

        class FoobarBlock1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_blocks_dependencies_1')

        class FoobarBlock2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_blocks_dependencies_2')
            dependencies = (Contact,)

        class FoobarBlock3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_blocks_dependencies_3')
            dependencies = (Organisation,)

        class FoobarBlock4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_blocks_dependencies_4')
            dependencies = (Contact, Organisation)

        block1 = FoobarBlock1(); block2 = FoobarBlock2(); block3 = FoobarBlock3(); block4 = FoobarBlock4()

        mngr = BlocksManager()
        mngr.add_group('gname1', block1, block2, block3, block4)

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_blocks blocks as 'my_blocks' %}"
                                "{% display_blocks 'my_blocks' %}"
                                "{% get_blocks_dependencies %}"
                               )
            render = template.render(RequestContext({}, {'blocks': [block1, block2, block3, block4]}))

        #TODO: improve...
        render = render.strip()
        self.assertIn('creme.utils.blocks_deps', render)
        self.assertIn('creme.utils.getBlocksDeps', render)

    def test_get_block_reload_uri(self):
        with self.assertNoException():
            template = Template('{% load creme_block %}{% get_block_reload_uri %}')
            render = template.render(RequestContext({}, {'block_name': 'test-testblock',
                                                         'base_url':   '/base/url/',
                                                         'update_url': '/update/url/',
                                                        }
                                                   )
                                    )

        self.assertEqual("'/update/url/?base_url=/base/url/&test-testblock_deps=' + creme.utils.getBlocksDeps('test-testblock')",
                         render
                        )

    def test_get_block_relation_reload_uri(self):
        class FooBlock1(SimpleBlock):
            id_ = SimpleBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_block_relation_reload_uri_1')
            dependencies = (Contact,)

        class FooBlock2(SimpleBlock):
            id_ = SimpleBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_block_relation_reload_uri_2')
            dependencies = (Relation,)

        class FooBlock3(SimpleBlock):
            id_ = SimpleBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_block_relation_reload_uri_3')
            dependencies = (Relation,)

        class FooBlock4(SimpleBlock):
            id_ = SimpleBlock.generate_id('creme_core', 'CremeBlockTagsTestCase__get_block_relation_reload_uri_4')
            dependencies = '*'

        block1 = FooBlock1(); block2 = FooBlock2()
        block3 = FooBlock3(); block4 = FooBlock4()

        with self.assertNoException():
            template = Template("{% load creme_block %}"
                                "{% import_blocks blocks as 'my_blocks' %}"
                                "{% get_block_relation_reload_uri %}"
                               )
            render = template.render(RequestContext({}, {'base_url':   '/base/url/',
                                                         'update_url': '/update/url/',
                                                         'blocks':     [block1, block2, block3, block4],
                                                         'block_name': block2.id_, #we simulate the displaying of 'block2'
                                                        }
                                                   )
                                    )

        self.assertEqual(u"'/update/url/?base_url=/base/url/&%s_deps=%s,%s'" % (
                                block2.id_, block3.id_, block4.id_
                            ),
                         render
                        )
