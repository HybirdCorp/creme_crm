# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as load_json

    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase
    from ..fake_models import (FakeContact as Contact,
            FakeOrganisation as Organisation, FakeAddress as Address)
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.blocks import RelationsBlock
    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.gui.block import (block_registry, Block,
            InstanceBlockConfigItem, _BlockRegistry)
    from creme.creme_core.models import (SetCredentials, RelationType, Relation,
            BlockState, BlockDetailviewLocation, CustomBlockConfigItem, FieldsConfig)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BlockViewTestCase(CremeTestCase):
    SET_STATE_URL = '/creme_core/blocks/reload/set_state/%s/'
    # TODO: other urls...

    # @classmethod
    # def setUpClass(cls):
    #     CremeTestCase.setUpClass()
    #     cls.populate('creme_core')

    def test_set_state01(self):
        user = self.login()
        self.assertEqual(0, BlockState.objects.count())

        block_id = RelationsBlock.id_
        self.assertPOST200(self.SET_STATE_URL % block_id, data={'is_open': 1})

        bstates = BlockState.objects.all()
        self.assertEqual(1, len(bstates))

        bstate = bstates[0]
        self.assertEqual(block_id, bstate.block_id)
        self.assertEqual(user,     bstate.user)
        self.assertTrue(bstate.is_open)

        self.assertPOST200(self.SET_STATE_URL % block_id, data={'is_open': 0})
        self.assertEqual(1, BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=user, block_id=block_id)
        self.assertFalse(bstate.is_open)

        self.assertPOST200(self.SET_STATE_URL % block_id, data={})  # No data
        self.assertEqual(1, BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=user, block_id=block_id)
        self.assertFalse(bstate.is_open)

    def test_set_state02(self):
        user = self.login()
        block_id = RelationsBlock.id_
        self.assertPOST200(self.SET_STATE_URL % block_id, data={'is_open': 1, 'show_empty_fields': 1})

        bstate = self.get_object_or_fail(BlockState, user=user, block_id=block_id)
        self.assertTrue(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

    def test_set_state03(self):
        user = self.login()
        block_id = RelationsBlock.id_
        self.client.post(self.SET_STATE_URL % block_id,
                         data={'is_open': 1, 'show_empty_fields': 1}
                        )

        self.client.logout()
        self.client.login(username=self.other_user.username, password="test")

        block_id = RelationsBlock.id_
        self.client.post(self.SET_STATE_URL % block_id,
                         data={'is_open': 0, 'show_empty_fields': 0}
                        )

        blocks_states = BlockState.objects.filter(block_id=block_id)

        block_state_user = blocks_states.get(user=user)
        block_state_other_user = blocks_states.get(user=self.other_user)

        self.assertTrue(block_state_user.is_open)
        self.assertTrue(block_state_user.show_empty_fields)

        self.assertFalse(block_state_other_user.is_open)
        self.assertFalse(block_state_other_user.show_empty_fields)

    def test_set_state04(self):
        "Block ids with |"
        user = self.login()
        casca = Contact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class ContactBlock(Block):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (Organisation,)
            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                            self.id_, self.ibci.entity
                        )  # Useless :)

        self.assertTrue(InstanceBlockConfigItem.id_is_specific(ContactBlock.id_))

        ibci = InstanceBlockConfigItem.objects \
                                      .create(entity=casca,
                                              block_id=InstanceBlockConfigItem.generate_id(ContactBlock, casca, ''),
                                              verbose=u"I am an awesome block",
                                              data='',
                                             )

        block_registry = _BlockRegistry()
        block_registry.register_4_instance(ContactBlock)

        blocks = block_registry.get_blocks([ibci.block_id], entity=casca)
        block_id = blocks[0].id_

        self.assertPOST200(self.SET_STATE_URL % block_id, data={'is_open': 1, 'show_empty_fields': 1})

    class TestBlock(Block):
        verbose_name = u'Testing purpose'

        string_format_detail = '<div id=%s>DETAIL</div>'
        string_format_home   = '<div id=%s>HOME</div>'
        string_format_portal = '<div id=%s>PORTAL</div>'

        contact = None
        ct_ids  = None

        def detailview_display(self, context):
            self.contact = context.get('object')
            return self.string_format_detail % self.id_

        def home_display(self, context):
            return self.string_format_home % self.id_

        def portal_display(self, context, ct_ids):
            self.ct_ids = ct_ids
            return self.string_format_portal % self.id_

    def test_reload_detailview01(self):
        user = self.login()
        atom = Contact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview01')

        block1 = FoobarBlock()
        block_registry.register(block1)

        response = self.assertGET200('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         load_json(response.content)
                        )
        self.assertEqual(atom, block1.contact)

    def test_reload_detailview02(self):
        "With dependencies"
        user = self.login()
        atom = Contact.objects.create(user=user, first_name='Atom', last_name='Tenma')

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

        response = self.assertGET200('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id),
                                     data={block1.id_ + '_deps': ','.join([block2.id_, block3.id_])}
                                    )
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_],
                          [block2.id_, self.TestBlock.string_format_detail % block2.id_],
                          [block3.id_, self.TestBlock.string_format_detail % block3.id_],
                         ],
                         load_json(response.content)
                        )
        self.assertEqual(atom, block1.contact)
        self.assertEqual(atom, block2.contact)
        self.assertEqual(atom, block3.contact)

    def test_reload_detailview03(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview03')

        block1 = FoobarBlock()
        block_registry.register(block1)
        self.assertGET403('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))

    def test_reload_detailview04(self):
        "Not superuser"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertTrue(self.user.has_perm_to_view(atom))

        class FoobarBlock(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_detailview04')

        block1 = FoobarBlock()
        block_registry.register(block1)

        response = self.assertGET200('/creme_core/blocks/reload/%s/%s/' % (block1.id_, atom.id))
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         load_json(response.content)
                        )

    def test_reload_detailview05(self):
        "Invalid block_id"
        user = self.login()
        atom = Contact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        response = self.assertGET200('/creme_core/blocks/reload/%s/%s/' % ('test_reload_detailview05', atom.id))
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([], load_json(response.content))

    def test_reload_home(self):
        self.login()

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_home_1')

        class FoobarBlock2(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_home_2')

        block1 = FoobarBlock1()
        block2 = FoobarBlock2()
        block_registry.register(block1, block2)

        response = self.assertGET200('/creme_core/blocks/reload/home/%s/' % block1.id_,
                                     data={block1.id_ + '_deps': ','.join([block2.id_, 'silly_id'])}
                                    )
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_home % block1.id_],
                          [block2.id_, self.TestBlock.string_format_home % block2.id_],
                         ],
                         load_json(response.content)
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
        response = self.assertGET200('/creme_core/blocks/reload/portal/%s/%s,%s/' % (
                                            block1.id_, ct_id1, ct_id2
                                        ),
                                     data={block1.id_ + '_deps': ','.join([block2.id_, 'silly_id'])}
                                    )
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_portal % block1.id_],
                          [block2.id_, self.TestBlock.string_format_portal % block2.id_],
                         ],
                         load_json(response.content)
                        )

        ct_ids = [ct_id1, ct_id2]
        self.assertEqual(ct_ids, block1.ct_ids)
        self.assertEqual(ct_ids, block2.ct_ids)

    def test_reload_portal02(self):
        "Do not have the credentials"
        self.login(is_superuser=False, allowed_apps=['documents'])

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal02_1')

        block1 = FoobarBlock1()
        block_registry.register(block1)
        self.assertGET403('/creme_core/blocks/reload/portal/%s/%s/' % (
                                block1.id_,
                                ContentType.objects.get_for_model(Contact).id
                            )
                         )

    def test_reload_portal03(self):
        "Not superuser"
        model = Contact
        self.login(is_superuser=False, allowed_apps=[model._meta.app_label])

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_portal03')

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.assertGET200('/creme_core/blocks/reload/portal/%s/%s/' % (
                                            block1.id_, ContentType.objects.get_for_model(model).id
                                        ),
                                    )
        self.assertEqual([[block1.id_, self.TestBlock.string_format_portal % block1.id_]],
                         load_json(response.content)
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

        response = self.assertGET200('/creme_core/blocks/reload/basic/%s/' % block1.id_,
                                     data={block1.id_ + '_deps': '%s,silly_id' % block2.id_}
                                    )
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_],
                          [block2.id_, self.TestBlock.string_format_detail % block2.id_],
                         ],
                         load_json(response.content)
                        )

    def test_reload_basic02(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic02')
            permission = 'persons'

        block1 = FoobarBlock1()
        block_registry.register(block1)
        self.assertGET403('/creme_core/blocks/reload/basic/%s/' % block1.id_)

    def test_reload_basic03(self):
        "Not superuser"
        app_name = 'persons'
        self.login(is_superuser=False, allowed_apps=[app_name])

        class FoobarBlock1(self.TestBlock):
            id_ = Block.generate_id('creme_core', 'test_reload_basic03')
            permission = app_name

        block1 = FoobarBlock1()
        block_registry.register(block1)

        response = self.assertGET200('/creme_core/blocks/reload/basic/%s/' % block1.id_)
        self.assertEqual([[block1.id_, self.TestBlock.string_format_detail % block1.id_]],
                         load_json(response.content)
                        )

    def test_reload_relations01(self):
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of')
                                    )[0]
        rel1 = Relation.objects.create(subject_entity=atom, type=rtype1, object_entity=tenma, user=user)

        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rel2 = Relation.objects.create(subject_entity=atom, type=rtype2, object_entity=uran, user=user)

        response = self.assertGET200('/creme_core/blocks/reload/relations_block/%s/' % atom.id)
        self.assertEqual('text/javascript', response['Content-Type'])

        content = load_json(response.content)
        self.assertTrue(isinstance(content, list))
        self.assertEqual(1, len(content))

        content = content[0]
        self.assertTrue(isinstance(content, list))
        self.assertEqual(2, len(content))
        self.assertEqual(RelationsBlock.id_, content[0])

        self.assertEqual(atom, response.context['object'])
        self.assertEqual({rel1, rel2}, set(response.context['page'].object_list))

    def test_reload_relations02(self):
        "With relationtype to exclude"
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of')
                                    )[0]
        Relation.objects.create(subject_entity=atom, type=rtype1, object_entity=tenma, user=user)

        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rel2 = Relation.objects.create(subject_entity=atom, type=rtype2, object_entity=uran, user=user)

        response = self.assertGET200('/creme_core/blocks/reload/relations_block/%s/%s/' % (atom.id, rtype1.id))
        self.assertEqual([rel2], list(response.context['page'].object_list))

    def test_reload_relations03(self):
        "Do not have the credentials"
        self.login(is_superuser=False)
        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertFalse(self.user.has_perm_to_view(atom))
        self.assertGET403('/creme_core/blocks/reload/relations_block/%s/' % atom.id)

    def test_reload_relations04(self):
        "Not superuser"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        atom = Contact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertTrue(self.user.has_perm_to_view(atom))
        self.assertGET200('/creme_core/blocks/reload/relations_block/%s/' % atom.id)

    def _get_contact_block_content(self, contact):
        content = self.assertGET200(contact.get_absolute_url()).content
        block_id = 'modelblock_creme_core-fakecontact'
        block_start_idx = content.find('id="%s"' % block_id)
        self.assertNotEqual(-1, block_start_idx)

        content_start_idx = block_start_idx + content[block_start_idx:].find('<tbody class="collapsable">')
        self.assertNotEqual(-1, content_start_idx)

        content_end_idx = content_start_idx + content[content_start_idx:].find('</tbody>')
        self.assertNotEqual(-1, content_end_idx)

        return content[content_start_idx:content_end_idx]

    def test_display_objectblock01(self):
        user = self.login()
        naru = Contact.objects.create(user=user, last_name='Narusegawa',
                                      first_name='Naru', phone='1122334455',
                                     )
        block_content = self._get_contact_block_content(naru)
        self.assertIn(naru.last_name, block_content)
        self.assertIn(naru.phone,     block_content)

    def test_display_objectblock02(self):
        "With FieldsConfig"
        user = self.login()

        FieldsConfig.create(Contact,
                            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
                           )
        naru = Contact.objects.create(user=user, last_name='Narusegawa',
                                      first_name='Naru', phone='1122334455',
                                     )
        block_content = self._get_contact_block_content(naru)
        self.assertIn(naru.last_name, block_content)
        self.assertNotIn(naru.phone,  block_content)

    def test_display_customblock01(self):
        user = self.login()

        fname1 = 'last_name'
        fname2 = 'phone'
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(Contact),
                        cells=[build_cell(Contact, fname1),
                               build_cell(Contact, fname2),
                              ],
                    )
        bdl = BlockDetailviewLocation.create(block_id=cbc_item.generate_id(),
                                             order=1000,  # Should be the last block
                                             model=Contact,
                                             zone=BlockDetailviewLocation.BOTTOM,
                                            )
        naru = Contact.objects.create(user=user, last_name='Narusegawa',
                                      first_name='Naru', phone='1122334455',
                                     )
        content = self.assertGET200(naru.get_absolute_url()).content
        idx = content.find('id="%s"' % bdl.block_id)
        self.assertNotEqual(-1, idx)

        content_end = content[idx:]
        self.assertIn(naru.last_name, content_end)
        self.assertIn(naru.phone,  content_end)

    def test_display_customblock02(self):
        "With FieldsConfig"
        user = self.login()

        hidden_fname = 'phone'
        FieldsConfig.create(Contact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(Contact),
                        cells=[build_cell(Contact, 'last_name'),
                               build_cell(Contact, hidden_fname),
                              ],
                    )
        bdl = BlockDetailviewLocation.create(block_id=cbc_item.generate_id(),
                                             order=1000,  # Should be the last block
                                             model=Contact,
                                             zone=BlockDetailviewLocation.BOTTOM,
                                            )
        naru = Contact.objects.create(user=user, last_name='Narusegawa',
                                      first_name='Naru', phone='1122334455',
                                     )
        content = self.assertGET200(naru.get_absolute_url()).content
        idx = content.find('id="%s"' % bdl.block_id)
        self.assertNotEqual(-1, idx)

        content_end = content[idx:]
        self.assertIn(naru.last_name, content_end)
        self.assertNotIn(naru.phone,  content_end)

    def test_display_customblock03(self):
        "With FieldsConfig on sub-fields"
        user = self.login()

        hidden_fname = 'zipcode'
        FieldsConfig.create(Address,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(Contact),
                        cells=[build_cell(Contact, 'last_name'),
                               build_cell(Contact, 'address__' + hidden_fname),
                               build_cell(Contact, 'address__city'),
                              ],
                    )
        bdl = BlockDetailviewLocation.create(block_id=cbc_item.generate_id(),
                                             order=1000,  # Should be the last block
                                             model=Contact,
                                             zone=BlockDetailviewLocation.BOTTOM,
                                            )
        naru = Contact.objects.create(user=user, last_name='Narusegawa',
                                      first_name='Naru', phone='1122334455',
                                     )
        naru.address = Address.objects.create(value='Hinata Inn', city='Tokyo',
                                              zipcode='112233', entity=naru,
                                             )
        naru.save()

        content = self.assertGET200(naru.get_absolute_url()).content
        idx = content.find('id="%s"' % bdl.block_id)
        self.assertNotEqual(-1, idx)

        content_end = content[idx:]
        self.assertIn(naru.last_name,    content_end)
        self.assertIn(naru.address.city, content_end)
        self.assertNotIn(naru.address.zipcode, content_end)
