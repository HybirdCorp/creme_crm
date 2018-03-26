# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import dumps as json_dump # loads as load_json

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.bricks import RelationsBrick
    from creme.creme_core.core.entity_cell import EntityCellRegularField
    from creme.creme_core.gui.bricks import (brick_registry, Brick,
            InstanceBlockConfigItem, _BrickRegistry, BricksManager)
    from creme.creme_core.models import (SetCredentials, RelationType, Relation, FieldsConfig,
            BlockState, BlockDetailviewLocation, CustomBlockConfigItem, RelationBlockItem)

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation, FakeAddress

    from .base import BrickTestCaseMixin
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BrickViewTestCase(CremeTestCase, BrickTestCaseMixin):
    SET_STATE_URL = reverse('creme_core__set_brick_state')

    class TestBrick(Brick):
        verbose_name = u'Testing purpose'

        string_format_detail = '<div id=%s>DETAIL</div>'
        string_format_home   = '<div id=%s>HOME</div>'
        string_format_portal = '<div id=%s>PORTAL</div>'

        def detailview_display(self, context):
            return self.string_format_detail % self.id_

        def home_display(self, context):
            return self.string_format_home % self.id_

        def portal_display(self, context, ct_ids):
            return self.string_format_portal % self.id_

    def test_set_state01(self):
        user = self.login()
        self.assertEqual(0, BlockState.objects.count())

        brick_id = RelationsBrick.id_
        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 1})

        bstates = BlockState.objects.all()
        self.assertEqual(1, len(bstates))

        bstate = bstates[0]
        self.assertEqual(brick_id, bstate.brick_id)
        self.assertEqual(user,     bstate.user)
        self.assertTrue(bstate.is_open)

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 0})
        self.assertEqual(1, BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, })  # No data
        self.assertEqual(1, BlockState.objects.count())

        bstate = self.get_object_or_fail(BlockState, user=user, brick_id=brick_id)
        self.assertFalse(bstate.is_open)

    def test_set_state02(self):
        user = self.login()
        brick_id = RelationsBrick.id_
        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 1})

        bstate = self.get_object_or_fail(BlockState, user=user, brick_id=brick_id)
        self.assertTrue(bstate.is_open)
        self.assertTrue(bstate.show_empty_fields)

    def test_set_state03(self):
        user = self.login()
        brick_id = RelationsBrick.id_
        self.client.post(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 1})

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        self.client.post(self.SET_STATE_URL,
                         data={'id': brick_id, 'is_open': 0, 'show_empty_fields': 0}
                        )

        blocks_states = BlockState.objects.filter(brick_id=brick_id)

        block_state_user = blocks_states.get(user=user)
        block_state_other_user = blocks_states.get(user=self.other_user)

        self.assertTrue(block_state_user.is_open)
        self.assertTrue(block_state_user.show_empty_fields)

        self.assertFalse(block_state_other_user.is_open)
        self.assertFalse(block_state_other_user.show_empty_fields)

    def test_set_state04(self):
        "Brick ids with |"
        user = self.login()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(Brick):
            id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                super(ContactBrick, self).__init__()
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (
                            self.id_, self.ibci.entity
                        )  # Useless :)

        self.assertTrue(InstanceBlockConfigItem.id_is_specific(ContactBrick.id_))

        ibci = InstanceBlockConfigItem.objects \
                                      .create(entity=casca,
                                              brick_id=InstanceBlockConfigItem.generate_id(ContactBrick, casca, ''),
                                              verbose=u'I am an awesome brick',
                                              data='',
                                             )

        brick_registry = _BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        bricks = list(brick_registry.get_bricks([ibci.brick_id], entity=casca))
        brick_id = bricks[0].id_

        self.assertPOST200(self.SET_STATE_URL, data={'id': brick_id, 'is_open': 1, 'show_empty_fields': 1})

    def test_reload_basic01(self):
        self.login()

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_1')
            permission = 'persons'

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic01_2')
            permission = 'persons'

        brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(reverse('creme_core__reload_bricks'),
                                     data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, 'silly_id']},
                                    )
        # self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([[FoobarBrick1.id_, self.TestBrick.string_format_detail % FoobarBrick1.id_],
                          [FoobarBrick2.id_, self.TestBrick.string_format_detail % FoobarBrick2.id_],
                         ],
                         # load_json(response.content)
                         response.json()
                        )

    def test_reload_basic02(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic02')
            permission = 'persons'

        brick_registry.register(FoobarBrick1)

        self.assertGET403(reverse('creme_core__reload_bricks'), data={'brick_id': FoobarBrick1.id_})

    def test_reload_basic03(self):
        "Not superuser"
        app_name = 'persons'
        self.login(is_superuser=False, allowed_apps=[app_name])

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic03')
            permission = app_name

        brick_registry.register(FoobarBrick1)

        response = self.assertGET200(reverse('creme_core__reload_bricks'), data={'brick_id': FoobarBrick1.id_})
        self.assertEqual([[FoobarBrick1.id_, self.TestBrick.string_format_detail % FoobarBrick1.id_]],
                         # load_json(response.content)
                         response.json()
                        )

    def test_reload_basic04(self):
        "Extra data"
        self.login()
        extra_data = [1, 2]

        errors = []  # TODO: nonlocal in Py3K
        received_extra_data = []  # TODO: nonlocal in Py3K

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic04')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                received_extra_data.append(info)

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(reverse('creme_core__reload_bricks'),
                                     data={'brick_id': FoobarBrick.id_,
                                           'extra_data': json_dump({FoobarBrick.id_: extra_data}),
                                          },
                                    )
        self.assertEqual([[FoobarBrick.id_, self.TestBrick.string_format_detail % FoobarBrick.id_]],
                         # load_json(response.content)
                         response.json()
                        )

        self.assertTrue(received_extra_data)
        self.assertEqual(extra_data, received_extra_data[0])
        self.assertFalse(errors)

    def test_reload_basic05(self):
        "Invalid extra data"
        self.login()

        errors = []  # TODO: nonlocal in Py3K
        received_extra_data = []  # TODO: nonlocal in Py3K

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_basic05')

            def detailview_display(self, context):
                try:
                    received_extra_data.append(BricksManager.get(context).get_reloading_info(self))
                except Exception as e:
                    errors.append(e)

                return super(FoobarBrick, self).detailview_display(context)

        brick_registry.register(FoobarBrick)

        self.assertGET200(reverse('creme_core__reload_bricks'),
                          data={'brick_id': FoobarBrick.id_,
                                'extra_data': '{%s: ' % FoobarBrick.id_,
                               },
                         )
        self.assertFalse(received_extra_data)
        self.assertTrue(errors)

    def test_reload_detailview01(self):
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview01')

            contact = None

            def detailview_display(self, context):
                FoobarBrick.contact = context.get('object')
                return super(FoobarBrick, self).detailview_display(context)

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': FoobarBrick.id_},
                                    )
        # self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([[FoobarBrick.id_, self.TestBrick.string_format_detail % FoobarBrick.id_]],
                         # load_json(response.content)
                         response.json()
                        )
        self.assertEqual(atom, FoobarBrick.contact)

    def test_reload_detailview02(self):
        "With dependencies"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_1')
            contact = None

            def detailview_display(self, context):
                FoobarBrick1.contact = context.get('object')
                return super(FoobarBrick1, self).detailview_display(context)

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_2')
            contact = None

            def detailview_display(self, context):
                FoobarBrick2.contact = context.get('object')
                return super(FoobarBrick2, self).detailview_display(context)

        class FoobarBrick3(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview02_3')
            contact = None

            def detailview_display(self, context):
                FoobarBrick3.contact = context.get('object')
                return super(FoobarBrick3, self).detailview_display(context)

        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, FoobarBrick3.id_]},
                                    )

        fmt = self.TestBrick.string_format_detail
        self.assertEqual([[FoobarBrick1.id_, fmt % FoobarBrick1.id_],
                          [FoobarBrick2.id_, fmt % FoobarBrick2.id_],
                          [FoobarBrick3.id_, fmt % FoobarBrick3.id_],
                         ],
                         # load_json(response.content)
                         response.json()
                        )
        self.assertEqual(atom, FoobarBrick1.contact)
        self.assertEqual(atom, FoobarBrick2.contact)
        self.assertEqual(atom, FoobarBrick3.contact)

    def test_reload_detailview03(self):
        "Do not have the credentials"
        self.login(is_superuser=False)

        atom = FakeContact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview03')

        brick_registry.register(FoobarBrick)

        self.assertGET403(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                          data={'brick_id': FoobarBrick.id_},
                         )

    def test_reload_detailview04(self):
        "Not superuser"
        self.login(is_superuser=False)
        SetCredentials.objects.create(role=self.role, value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        atom = FakeContact.objects.create(user=self.other_user, first_name='Atom', last_name='Tenma')
        self.assertTrue(self.user.has_perm_to_view(atom))

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview04')

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': FoobarBrick.id_},
                                    )
        self.assertEqual([[FoobarBrick.id_, self.TestBrick.string_format_detail % FoobarBrick.id_]],
                         # load_json(response.content)
                         response.json()
                        )

    def test_reload_detailview05(self):
        "Invalid block_id"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks',
                                             args=(atom.id,),
                                            ),
                                     data={'brick_id': 'test_bricks_reload_detailview05'},
                                    )
        # self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('application/json', response['Content-Type'])
        # self.assertEqual([], load_json(response.content))
        self.assertEqual([], response.json())

    def test_reload_detailview06(self):
        "Extra data"
        user = self.login()
        atom = FakeContact.objects.create(user=user, first_name='Atom', last_name='Tenma')
        extra_data = [1, 2]
        received_extra_data = []  # TODO: nonlocal in Py3K

        class FoobarBrick(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_detailview06')

            @self.TestBrick.reloading_info.setter
            def reloading_info(self, info):
                received_extra_data.append(info)

        brick_registry.register(FoobarBrick)

        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': FoobarBrick.id_,
                                           'extra_data': json_dump({FoobarBrick.id_: extra_data}),
                                          },
                                    )
        self.assertEqual([[FoobarBrick.id_, self.TestBrick.string_format_detail % FoobarBrick.id_]],
                         # load_json(response.content)
                         response.json()
                        )

        self.assertTrue(received_extra_data)
        self.assertEqual(extra_data, received_extra_data[0])

    def test_reload_home(self):
        self.login()

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_home_1')

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_home_2')

        brick_registry.register(FoobarBrick1, FoobarBrick2)

        response = self.assertGET200(reverse('creme_core__reload_home_bricks'),
                                     # data={'brick_id': FoobarBrick1.id_,
                                     #       'brick_deps': ','.join([FoobarBrick2.id_, 'silly_id'])
                                     #      }
                                     data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, 'silly_id']},
                                    )
        # self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([[FoobarBrick1.id_, self.TestBrick.string_format_home % FoobarBrick1.id_],
                          [FoobarBrick2.id_, self.TestBrick.string_format_home % FoobarBrick2.id_],
                         ],
                         # load_json(response.content)
                         response.json()
                        )

    def test_reload_portal01(self):
        self.login()

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_portal01_1')
            ct_ids = None

            def portal_display(self, context, ct_ids):
                FoobarBrick1.ct_ids = ct_ids
                return super(FoobarBrick1, self).portal_display(context, ct_ids)

        class FoobarBrick2(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_portal01_2')
            ct_ids = None

            def portal_display(self, context, ct_ids):
                FoobarBrick2.ct_ids = ct_ids
                return super(FoobarBrick2, self).portal_display(context, ct_ids)

        brick_registry.register(FoobarBrick1, FoobarBrick2)

        get_ct = ContentType.objects.get_for_model
        ct_id1 = get_ct(FakeContact).id
        ct_id2 = get_ct(FakeOrganisation).id

        response = self.assertGET200(reverse('creme_core__reload_portal_bricks'),
                                     data={'brick_id': [FoobarBrick1.id_, FoobarBrick2.id_, 'silly_id'],
                                           'ct_id':    [ct_id1, ct_id2],
                                           },
                                    )
        # self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual('application/json', response['Content-Type'])
        self.assertEqual([[FoobarBrick1.id_, self.TestBrick.string_format_portal % FoobarBrick1.id_],
                          [FoobarBrick2.id_, self.TestBrick.string_format_portal % FoobarBrick2.id_],
                         ],
                         # load_json(response.content)
                         response.json()
                        )

        ct_ids = [str(ct_id1), str(ct_id2)]
        self.assertEqual(ct_ids, FoobarBrick1.ct_ids)
        self.assertEqual(ct_ids, FoobarBrick2.ct_ids)

    def test_reload_portal02(self):
        "Do not have the credentials"
        self.login(is_superuser=False, allowed_apps=['documents'])

        class FoobarBrick1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_portal02_1')

        brick_registry.register(FoobarBrick1)

        self.assertGET403(reverse('creme_core__reload_portal_bricks'),
                          data={'brick_id': FoobarBrick1.id_,
                                'ct_id': ContentType.objects.get_for_model(FakeContact).id,
                               },
                         )

    def test_reload_portal03(self):
        "Not superuser"
        model = FakeContact
        self.login(is_superuser=False, allowed_apps=[model._meta.app_label])

        class FoobarBlock1(self.TestBrick):
            id_ = Brick.generate_id('creme_core', 'test_bricks_reload_portal03')

        brick_registry.register(FoobarBlock1)

        response = self.assertGET200(reverse('creme_core__reload_portal_bricks'),
                                     data={'brick_id': FoobarBlock1.id_,
                                           'ct_id': ContentType.objects.get_for_model(model).id,
                                          },
                                    )
        self.assertEqual([[FoobarBlock1.id_, self.TestBrick.string_format_portal % FoobarBlock1.id_]],
                         # load_json(response.content)
                         response.json()
                        )

    def test_relations_brick01(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
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
        Relation.objects.create(subject_entity=atom, type=rtype2, object_entity=uran, user=user)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')

        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, RelationsBrick.id_)
        self.assertInstanceLink(brick_node, tenma)
        self.assertInstanceLink(brick_node, uran)
        self.assertEqual('{}', brick_node.attrib.get('data-brick-reloading-info'))

    def test_relations_brick02(self):
        """With A SpecificRelationBrick ; but the concerned relationship is minimal_display=False
        (so there is no RelationType to exclude)
        """
        user = self.login()
        rbrick_id = RelationsBrick.id_

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of')
                                    )[0]
        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rbi = RelationBlockItem.create(rtype1.id)

        BlockDetailviewLocation.create_4_model_brick(order=1, zone=BlockDetailviewLocation.LEFT, model=FakeContact)

        create_bdl = partial(BlockDetailviewLocation.create_if_needed, zone=BlockDetailviewLocation.RIGHT, model=FakeContact)
        create_bdl(brick_id=rbi.brick_id, order=2)
        create_bdl(brick_id=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)
        rel_brick_node = self.get_brick_node(document, rbrick_id)

        reloading_info = {'include': [rtype1.id]}
        self.assertEqual(json_dump(reloading_info),
                         rel_brick_node.attrib.get('data-brick-reloading-info')
                        )
        self.assertInstanceLink(rel_brick_node, tenma)
        self.assertInstanceLink(rel_brick_node, uran)

        rbi_brick_node = self.get_brick_node(document, rbi.brick_id)
        self.assertIsNone(rbi_brick_node.attrib.get('data-brick-reloading-info'))
        self.assertInstanceLink(rbi_brick_node, tenma)
        self.assertNoInstanceLink(rbi_brick_node, uran)

        # Reloading
        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': rbrick_id,
                                           'extra_data': json_dump({rbrick_id: reloading_info}),
                                          },
                                    )

        # load_data = load_json(response.content)
        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

    def test_relations_brick03(self):
        """With A SpecificRelationBrick ; the concerned relationship is minimal_display=True,
        so the RelationType is excluded.
        """
        user = self.login()
        rbrick_id = RelationsBrick.id_

        rtype1 = RelationType.create(('test-subject_son',   'is the son of'),
                                     ('test-object_father', 'is the father of'),
                                     minimal_display=(True, True),
                                    )[0]
        rtype2 = RelationType.create(('test-subject_brother', 'is the brother of'),
                                     ('test-object_sister',   'is the sister of')
                                    )[0]
        rbi = RelationBlockItem.create(rtype1.id)

        BlockDetailviewLocation.create_4_model_brick(order=1, zone=BlockDetailviewLocation.LEFT, model=FakeContact)

        create_bdl = partial(BlockDetailviewLocation.create_if_needed, zone=BlockDetailviewLocation.RIGHT, model=FakeContact)
        create_bdl(brick_id=rbi.brick_id, order=2)
        create_bdl(brick_id=rbrick_id,    order=3)

        create_contact = partial(FakeContact.objects.create, user=user)
        atom  = create_contact(first_name='Atom', last_name='Tenma')
        tenma = create_contact(first_name='Dr',   last_name='Tenma')
        uran  = create_contact(first_name='Uran', last_name='Ochanomizu')

        create_rel = partial(Relation.objects.create, subject_entity=atom, user=user)
        create_rel(type=rtype1, object_entity=tenma)
        create_rel(type=rtype2, object_entity=uran)

        response = self.assertGET200(atom.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/bricks/relations.html')
        self.assertTemplateUsed(response, 'creme_core/bricks/specific-relations.html')

        document = self.get_html_tree(response.content)

        rel_brick_node = self.get_brick_node(document, rbrick_id)
        self.assertInstanceLink(rel_brick_node, uran)
        self.assertNoInstanceLink(rel_brick_node, tenma)

        reloading_info = {'exclude': [rtype1.id]}
        self.assertEqual(json_dump(reloading_info),
                         rel_brick_node.attrib.get('data-brick-reloading-info')
                        )

        # Reloading
        response = self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                                     data={'brick_id': rbrick_id,
                                           'extra_data': json_dump({rbrick_id: reloading_info}),
                                          },
                                    )

        # load_data = load_json(response.content)
        load_data = response.json()
        self.assertEqual(load_data[0][0], rbrick_id)

        l_document = self.get_html_tree(load_data[0][1])
        l_rel_brick_node = self.get_brick_node(l_document, rbrick_id)
        self.assertNoInstanceLink(l_rel_brick_node, tenma)
        self.assertInstanceLink(l_rel_brick_node, uran)

        # Reloading + bad data
        def assertBadData(data):
            self.assertGET200(reverse('creme_core__reload_detailview_bricks', args=(atom.id,)),
                              data={'brick_id': rbrick_id,
                                    'extra_data': json_dump({rbrick_id: data}),
                                   },
                             )

        assertBadData(1)
        assertBadData({'include': 1})
        assertBadData({'exclude': 1})
        assertBadData({'include': [[]]})
        assertBadData({'exclude': [[]]})

    def _get_contact_brick_content(self, contact, brick_id):
        response = self.assertGET200(contact.get_absolute_url())
        document = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(document, brick_id)

        content_node = brick_node.find('.//div[@class="brick-content "]')
        self.assertIsNotNone(content_node)

        return content_node

    def _assertNoBrickTile(self, content_node, key):
        self.assertIsNone(content_node.find('.//div[@data-key="%s"]' % key))

    def test_display_objectbrick01(self):
        user = self.login()
        naru = FakeContact.objects.create(user=user, last_name='Narusegawa',
                                          first_name='Naru', phone='1122334455',
                                         )

        content_node = self._get_contact_brick_content(naru, brick_id='modelblock_creme_core-fakecontact')
        self.assertEqual(naru.last_name, self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self.assertIn(naru.phone, self.get_brick_tile(content_node, 'regular_field-phone').text)

    def test_display_objectbrick02(self):
        "With FieldsConfig"
        user = self.login()

        FieldsConfig.create(FakeContact,
                            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
                           )
        naru = FakeContact.objects.create(user=user, last_name='Narusegawa',
                                          first_name='Naru', phone='1122334455',
                                         )

        content_node = self._get_contact_brick_content(naru, brick_id='modelblock_creme_core-fakecontact')
        self.assertEqual(naru.last_name, self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick01(self):
        user = self.login()

        fname1 = 'last_name'
        fname2 = 'phone'
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(FakeContact),
                        cells=[build_cell(FakeContact, fname1),
                               build_cell(FakeContact, fname2),
                              ],
                    )
        bdl = BlockDetailviewLocation.create_if_needed(brick_id=cbc_item.generate_id(),
                                                       order=1000,
                                                       model=FakeContact,
                                                       zone=BlockDetailviewLocation.BOTTOM,
                                                      )
        naru = FakeContact.objects.create(user=user, last_name='Narusegawa',
                                          first_name='Naru', phone='1122334455',
                                         )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(naru.last_name, self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self.assertIn(naru.phone, self.get_brick_tile(content_node, 'regular_field-phone').text)

    def test_display_custombrick02(self):
        "With FieldsConfig"
        user = self.login()

        hidden_fname = 'phone'
        FieldsConfig.create(FakeContact,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                            )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(FakeContact),
                        cells=[build_cell(FakeContact, 'last_name'),
                               build_cell(FakeContact, hidden_fname),
                              ],
                    )
        bdl = BlockDetailviewLocation.create_if_needed(brick_id=cbc_item.generate_id(),
                                                       order=1000,
                                                       model=FakeContact,
                                                       zone=BlockDetailviewLocation.BOTTOM,
                                                      )
        naru = FakeContact.objects.create(user=user, last_name='Narusegawa',
                                          first_name='Naru', phone='1122334455',
                                         )

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(naru.last_name, self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self._assertNoBrickTile(content_node, 'regular_field-phone')

    def test_display_custombrick03(self):
        "With FieldsConfig on sub-fields"
        user = self.login()

        hidden_fname = 'zipcode'
        FieldsConfig.create(FakeAddress,
                            descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})],
                           )
        build_cell = EntityCellRegularField.build
        cbc_item = CustomBlockConfigItem.objects.create(
                        id='tests-contacts1', name='Contact info',
                        content_type=ContentType.objects.get_for_model(FakeContact),
                        cells=[build_cell(FakeContact, 'last_name'),
                               build_cell(FakeContact, 'address__' + hidden_fname),
                               build_cell(FakeContact, 'address__city'),
                              ],
                    )
        bdl = BlockDetailviewLocation.create_if_needed(brick_id=cbc_item.generate_id(),
                                                       order=1000,  # Should be the last block
                                                       model=FakeContact,
                                                       zone=BlockDetailviewLocation.BOTTOM,
                                                      )
        naru = FakeContact.objects.create(user=user, last_name='Narusegawa',
                                          first_name='Naru', phone='1122334455',
                                         )
        naru.address = FakeAddress.objects.create(value='Hinata Inn', city='Tokyo',
                                                  zipcode='112233', entity=naru,
                                                 )
        naru.save()

        content_node = self._get_contact_brick_content(naru, brick_id=bdl.brick_id)
        self.assertEqual(naru.last_name,    self.get_brick_tile(content_node, 'regular_field-last_name').text)
        self.assertEqual(naru.address.city, self.get_brick_tile(content_node, 'regular_field-address__city').text)
        self._assertNoBrickTile(content_node, 'regular_field-address__zipcode')
