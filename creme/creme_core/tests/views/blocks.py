# -*- coding: utf-8 -*-

try:
    from django.core.serializers.json import simplejson
    from django.contrib.contenttypes.models import ContentType

    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.blocks import RelationsBlock
    from creme_core.models import BlockState, SetCredentials, RelationType, Relation
    from creme_core.gui.block import block_registry, Block
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('BlockViewTestCase', )


class BlockViewTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def test_set_state01(self):
        self.login()
        self.assertEqual(0, BlockState.objects.count())

        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id, data={'is_open': 1})
        self.assertEqual(200, response.status_code)

        bstates = BlockState.objects.all()
        self.assertEqual(1, len(bstates))

        bstate = bstates[0]
        self.assertEqual(block_id,  bstate.block_id)
        self.assertEqual(self.user, bstate.user)
        self.assertTrue(bstate.is_open)

        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id, data={'is_open': 0})
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=self.user, block_id=block_id)
        self.assertFalse(bstate.is_open)

        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id, data={})#No data
        self.assertEqual(200, response.status_code)
        self.assertEqual(1,   BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=self.user, block_id=block_id)
        self.assertFalse(bstate.is_open)

    def test_set_state02(self):
        self.login()
        block_id = RelationsBlock.id_
        response = self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                                    data={'is_open': 1, 'show_empty_fields': 1}
                                   )
        self.assertEqual(200, response.status_code)

        bstate = self.get_object_or_fail(BlockState, user=self.user, block_id=block_id)
        self.assertTrue(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

    def test_set_state03(self):
        self.login()
        block_id = RelationsBlock.id_
        self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                         data={'is_open': 1, 'show_empty_fields': 1}
                        )

        self.client.logout()
        self.client.login(username=self.other_user.username, password="test")

        block_id = RelationsBlock.id_
        self.client.post('/creme_core/blocks/reload/set_state/%s/' % block_id,
                         data={'is_open': 0, 'show_empty_fields': 0}
                        )

        blocks_states = BlockState.objects.filter(block_id=block_id)

        block_state_user = blocks_states.get(user=self.user)
        block_state_other_user = blocks_states.get(user=self.other_user)

        self.assertTrue(block_state_user.is_open)
        self.assertTrue(block_state_user.show_empty_fields)

        self.assertFalse(block_state_other_user.is_open)
        self.assertFalse(block_state_other_user.show_empty_fields)

    class TestBlock(Block):
        verbose_name = u'Testing purpose'

        string_format_detail = '<div id=%s>DETAIL</div>'
        string_format_home   = '<div id=%s>HOME</div>'
        string_format_portal = '<div id=%s>PORTAL</div>'

        contact = None
        ct_ids  = None

        def detailview_display(self, context):
            self.contact = context.get('object')
            return  self.string_format_detail % self.id_

        def home_display(self, context):
            return  self.string_format_home % self.id_

        def portal_display(self, context, ct_ids):
            self.ct_ids = ct_ids
            return  self.string_format_portal % self.id_

    def test_reload_detailview01(self):
        self.login()
        atom = Contact.objects.create(user=self.user, first_name='Atom', last_name='Tenma')

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview01')

        block1 = FoobarBlock()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         simplejson.loads(response.content)
                        )
        self.assertEqual(atom, block1.contact)

    def test_reload_detailview02(self): #with dependencies
        self.login()
        atom = Contact.objects.create(user=self.user, first_name='Atom', last_name='Tenma')

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview02_1')

        class FoobarBlock2(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview02_2')

        class FoobarBlock3(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview02_3')

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block3 = FoobarBlock3()
        block_registry.register(block1, block2, block3)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id),
                                   data={block1.id_ + '_deps': ','.join([block2.id_, block3.id_])}
                                  )
        self.assertEqual(200, response.status_code)
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_],
                          [block2.id_, self.TestBlock.string_format_detail % block2.id_],
                          [block3.id_, self.TestBlock.string_format_detail % block3.id_],
                         ],
                         simplejson.loads(response.content)
                        )
        self.assertEqual(atom, block1.contact)
        self.assertEqual(atom, block2.contact)
        self.assertEqual(atom, block3.contact)

    def test_reload_detailview03(self): #do not have the credentials
        self.login(is_superuser=False)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview03')

        block1 = FoobarBlock()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))
        self.assertEqual(403, response.status_code)

    def test_reload_detailview04(self): #not superuser
        self.login(is_superuser=False, allowed_apps=['persons'])
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertTrue(atom.can_view(self.user))

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview04')

        block1 = FoobarBlock()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         simplejson.loads(response.content)
                        )

    def test_reload_detailview05(self): #invalid block_id
        self.login()
        atom = Contact.objects.create(user=self.user, first_name='Atom', last_name='Tenma')

        response = self.client.get('/creme_core/blocks/reload/%s/%s/' % ('test_reload_detailview05', atom.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([], simplejson.loads(response.content))

    def test_reload_home(self):
        self.login()

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_home_1')

        class FoobarBlock2(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_home_2')

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block_registry.register(block1, block2)

        response = self.client.get('/creme_core/blocks/reload/home/%s/' % block1.id_,
                                   data={block1.id_ + '_deps': ','.join([block2.id_, 'silly_id'])}
                                  )
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_home % block1.id_],
                          [block2.id_, self.TestBlock.string_format_home % block2.id_],
                         ],
                         simplejson.loads(response.content)
                        )

    def test_reload_portal01(self):
        self.login()

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal01_1')

        class FoobarBlock2(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal01_2')

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block_registry.register(block1, block2)

        get_ct = ContentType.objects.get_for_model
        ct_id1 = get_ct(Contact).id
        ct_id2 = get_ct(Organisation).id
        response = self.client.get('/creme_core/blocks/reload/portal/%s/%s,%s/' % (
                                            block1.id_, ct_id1, ct_id2
                                        ),
                                   data={block1.id_ + '_deps': ','.join([block2.id_, 'silly_id'])}
                                  )
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_portal % block1.id_],
                          [block2.id_, self.TestBlock.string_format_portal % block2.id_],
                         ],
                         simplejson.loads(response.content)
                        )

        ct_ids = [ct_id1, ct_id2]
        self.assertEqual(ct_ids, block1.ct_ids)
        self.assertEqual(ct_ids, block2.ct_ids)

    def test_reload_portal02(self): #do not have the credentials
        self.login(is_superuser=False)

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal02_1')

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/portal/%s/%s/' % (
                                            block1.id_, ContentType.objects.get_for_model(Contact).id
                                        ),
                                  )
        self.assertEqual(403, response.status_code)

    def test_reload_portal03(self): #not superuser
        model = Contact
        self.login(is_superuser=False, allowed_apps=[model._meta.app_label])

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal03')

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/portal/%s/%s/' % (
                                            block1.id_, ContentType.objects.get_for_model(model).id
                                        ),
                                  )
        self.assertEqual(200, response.status_code)
        self.assertEqual([[block1.id_, self.TestBlock.string_format_portal % block1.id_]],
                         simplejson.loads(response.content)
                        )

    def test_reload_basic01(self):
        self.login()

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic01_1')
            permission = 'persons'

        class FoobarBlock2(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic01_2')
            permission = 'persons'

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block_registry.register(block1, block2)

        response = self.client.get('/creme_core/blocks/reload/basic/%s/' % block1.id_,
                                   data={block1.id_ + '_deps': '%s,silly_id' % block2.id_}
                                  )
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_],
                          [block2.id_, self.TestBlock.string_format_detail % block2.id_],
                         ],
                         simplejson.loads(response.content)
                        )

    def test_reload_basic02(self): #do not have the credentials
        self.login(is_superuser=False)

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic02')
            permission = 'persons'

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/basic/%s/' % block1.id_)
        self.assertEqual(403, response.status_code)

    def test_reload_basic03(self): #not superuser
        self.login(is_superuser=False, allowed_apps=['persons'])

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic03')
            permission = 'persons'

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.client.get('/creme_core/blocks/reload/basic/%s/' % block1.id_)
        self.assertEqual(200, response.status_code)
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         simplejson.loads(response.content)
                        )

    def test_reload_relations01(self):
        self.login()
        user = self.user

        create_contact = Contact.objects.create
        atom  = create_contact(user=user, first_name='Atom', last_name='Tenma')
        tenma = create_contact(user=user, first_name='Dr',   last_name='Tenma')
        uran  = create_contact(user=user, first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of')
                                    )[0]
        rel1 = Relation.objects.create(subject_entity=atom, type=rtype1, object_entity=tenma, user=user)

        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rel2 = Relation.objects.create(subject_entity=atom, type=rtype2, object_entity=uran, user=user)

        response = self.client.get('/creme_core/blocks/reload/relations_block/%s/' % atom.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = simplejson.loads(response.content)
        self.assertTrue(isinstance(content, list))
        self.assertEqual(1, len(content))

        content = content[0]
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(RelationsBlock.id_, content[0])

        self.assertEqual(atom, response.context['object'])
        self.assertEqual(set([rel1, rel2]), set(response.context['page'].object_list))

    def test_reload_relations02(self): #with relationtype to exclude
        self.login()
        user = self.user

        create_contact = Contact.objects.create
        atom  = create_contact(user=user, first_name='Atom', last_name='Tenma')
        tenma = create_contact(user=user, first_name='Dr',   last_name='Tenma')
        uran  = create_contact(user=user, first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of')
                                    )[0]
        Relation.objects.create(subject_entity=atom, type=rtype1, object_entity=tenma, user=user)

        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rel2 = Relation.objects.create(subject_entity=atom, type=rtype2, object_entity=uran, user=user)

        response = self.client.get('/creme_core/blocks/reload/relations_block/%s/%s/' % (atom.id, rtype1.id))
        self.assertEqual(200, response.status_code)
        self.assertEqual([rel2], list(response.context['page'].object_list))

    def test_reload_relations03(self): #do not have the credentials
        self.login(is_superuser=False, allowed_apps=['persons'])
        atom  = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')

        response = self.client.get('/creme_core/blocks/reload/relations_block/%s/' % atom.id)
        self.assertEqual(403, response.status_code)

    def test_reload_relations04(self): #not superuser
        self.login(is_superuser=False, allowed_apps=['persons'])
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertTrue(atom.can_view(self.user))

        response = self.client.get('/creme_core/blocks/reload/relations_block/%s/' % atom.id)
        self.assertEqual(200, response.status_code)
