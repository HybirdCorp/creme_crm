try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.contrib.sessions.backends.base import SessionBase
    from django.test import RequestFactory

    from ..base import CremeTestCase
    from ..fake_models import FakeContact, FakeOrganisation, FakeImage
    from creme.creme_core.core.entity_cell import EntityCellRegularField, EntityCellRelation
    from creme.creme_core.gui.bricks import (Brick, SimpleBrick, QuerysetBrick,
            SpecificRelationsBrick, CustomBrick, _BrickRegistry, BricksManager)
    from creme.creme_core.models import (Relation, RelationType,
            InstanceBrickConfigItem, RelationBrickItem, CustomBrickConfigItem)
    from creme.creme_core.views.bricks import build_context
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class BrickRegistryTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        # super(BrickRegistryTestCase, cls).setUpClass()
        super().setUpClass()
        RelationBrickItem.objects.all().delete()
        InstanceBrickConfigItem.objects.all().delete()

    def test_get_compatible_bricks(self):
        user = self.login()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FoobarBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context): return self._render(self.get_template_context(context))

        class FoobarBrick2(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_2')
            verbose_name  = u'Testing purpose'
            target_ctypes = (FakeContact, FakeOrganisation)

        class FoobarBrick3(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_3')
            verbose_name = u'Testing purpose'
            target_ctypes = (FakeOrganisation,)  # Not 'Contact'

        class FoobarBrick4(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_4')
            verbose_name = u'Testing purpose'
            configurable = False  # <------

        class FoobarBrick5(Brick):  # No detailview_display() method
            id_ = Brick.generate_id('creme_core', 'foobar_brick_5')
            verbose_name = u'Testing purpose'

            # def portal_display(self, context, ct_ids): return '<table id="{}"></table>'.format(self.id_)
            def home_display(self, context): return '<table id="{}"></table>'.format(self.id_)

        class FakeContactBrick(SimpleBrick):
            verbose_name = u'Fake Contact block'

        class FakeOrganisationBrick(SimpleBrick):
            verbose_name = u'Fake Organisation block'

        class _FoobarInstanceBrick(Brick):
            verbose_name = u'Testing purpose'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

        class FoobarInstanceBrick1(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')

            def detailview_display(self, context):
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(self.id_, self.ibci.entity)

        class FoobarInstanceBrick2(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_2')
            target_ctypes = (FakeContact, FakeOrganisation)  # <-- OK !!

            def detailview_display(self, context):
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(self.id_, self.ibci.entity)

        class FoobarInstanceBrick3(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_3')
            target_ctypes = (FakeOrganisation, FakeImage)  # <-- KO !!

            def detailview_display(self, context):
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(self.id_, self.ibci.entity)

        class FoobarInstanceBrick4(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_4')

            def home_display(self, context):  # <====== not detailview_display()
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(self.id_, self.ibci.entity)

        create_ibci = partial(InstanceBrickConfigItem.objects.create, entity=casca, data='')
        ibci1 = create_ibci(verbose=u'I am an awesome brick',
                            brick_id=InstanceBrickConfigItem.generate_id(FoobarInstanceBrick1, casca, ''),
                           )
        ibci2 = create_ibci(verbose=u'I am an awesome brick too',
                            brick_id=InstanceBrickConfigItem.generate_id(FoobarInstanceBrick2, casca, ''),
                           )
        create_ibci(verbose=u'I am a poor brick',
                    brick_id=InstanceBrickConfigItem.generate_id(FoobarInstanceBrick3, casca, ''),
                   )
        create_ibci(verbose=u'I am a poor brick too',
                    brick_id=InstanceBrickConfigItem.generate_id(FoobarInstanceBrick4, casca, ''),
                   )

        brick_registry = _BrickRegistry()

        rtype1 = RelationType.create(('test-subject_loves', 'loves'), ('test-object_loved', 'is loved by'))[0]
        RelationBrickItem.create(rtype1.id)

        create_cbci = CustomBrickConfigItem.objects.create
        get_ct = ContentType.objects.get_for_model
        cbci = create_cbci(id='test-contacts01', name='General (contact)', content_type=get_ct(FakeContact),
                           cells=[EntityCellRegularField.build(FakeContact, 'last_name')],
                           )
        create_cbci(id='test-organisations01', name='General (orga)', content_type=get_ct(FakeOrganisation),
                    cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
                   )  # Not compatible with Contact

        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3, FoobarBrick4, FoobarBrick5)
        brick_registry.register_4_model(FakeContact,      FakeContactBrick)
        brick_registry.register_4_model(FakeOrganisation, FakeOrganisationBrick)
        brick_registry.register_4_instance(FoobarInstanceBrick1,
                                           FoobarInstanceBrick2,
                                           FoobarInstanceBrick3,
                                           FoobarInstanceBrick4,
                                          )

        bricks = sorted(brick_registry.get_compatible_bricks(FakeContact), key=lambda b: b.id_)
        self.assertEqual(7, len(bricks))
        self.assertIsInstance(bricks[0], FoobarBrick1)
        self.assertIsInstance(bricks[1], FoobarBrick2)

        brick = bricks[2]
        self.assertIsInstance(brick, CustomBrick)
        self.assertEqual(cbci.generate_id(), brick.id_)

        brick = bricks[3]
        self.assertIsInstance(brick, FoobarInstanceBrick1)
        self.assertEqual(ibci1.brick_id, brick.id_)

        brick = bricks[4]
        self.assertIsInstance(brick, FoobarInstanceBrick2)
        self.assertEqual(ibci2.brick_id, brick.id_)

        brick = bricks[5]
        self.assertIsInstance(brick, FakeContactBrick)
        self.assertEqual((FakeContact,), brick.dependencies)

        brick = bricks[6]
        self.assertIsInstance(brick, SpecificRelationsBrick)
        self.assertEqual((rtype1.id,), brick.relation_type_deps)

    def test_get_compatible_hat_bricks01(self):
        brick_registry = _BrickRegistry()
        bricks = list(brick_registry.get_compatible_hat_bricks(FakeContact))
        self.assertEqual(1, len(bricks))

        brick = bricks[0]
        self.assertIsInstance(brick, SimpleBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual('creme_core/bricks/generic/hat-bar.html', brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id_)

    def test_get_compatible_hat_bricks02(self):
        "Register main class"
        template = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick(SimpleBrick):
            template_name = template

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(FakeContact, main_brick_cls=FakeContactHatBrick)
        bricks = list(brick_registry.get_compatible_hat_bricks(FakeContact))
        self.assertEqual(1, len(bricks))

        brick = bricks[0]
        self.assertIsInstance(brick, FakeContactHatBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual(template, brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id_)

    def test_get_compatible_hat_bricks02_error(self):
        brick_registry = _BrickRegistry()

        class FakeContactHatBrick(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'contact_hat')
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(FakeContact, main_brick_cls=FakeContactHatBrick)

    def test_get_compatible_hat_bricks03(self):
        "Secondary classes"
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick01(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_1')

        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_2')

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(FakeContact,
                                    secondary_brick_classes=(FakeContactHatBrick01, FakeContactHatBrick02),
                                   )

        bricks = list(brick_registry.get_compatible_hat_bricks(FakeContact))
        self.assertEqual(3, len(bricks))

        self.assertIsInstance(bricks[0], SimpleBrick)
        self.assertEqual({FakeContactHatBrick01, FakeContactHatBrick02},
                         {brick.__class__ for brick in bricks[1:]}
                        )

    def test_get_compatible_hat_bricks03_error(self):
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        # id_ is None -----------
        class FakeContactHatBrick01(BaseFakeContactHatBrick): pass

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(FakeContact, secondary_brick_classes=[FakeContactHatBrick01])

        # Bad id_ type ------------
        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'test_get_compatible_hat_bricks03_error')

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(FakeContact, secondary_brick_classes=[FakeContactHatBrick02])

        # Duplicated id_ -------------
        class FakeContactHatBrick03(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_error')

        class FakeContactHatBrick04(BaseFakeContactHatBrick):
            id_ = FakeContactHatBrick03.id_  # <===

        with self.assertNoException():
            brick_registry.register_hat(FakeContact, secondary_brick_classes=[FakeContactHatBrick03])

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(FakeContact, secondary_brick_classes=[FakeContactHatBrick04])

    # def test_get_compatible_portal_blocks01(self):
    #     user = self.login()
    #     casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')
    #
    #     class FoobarBlock1(Brick):
    #         id_          = Brick.generate_id('creme_core', 'foobar_block_1')
    #         verbose_name = u'Testing purpose'
    #
    #         # NB: only portal_display() method
    #         # def detailview_display(self, context): [...]
    #         # def home_display(self, context): [...]
    #         def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock2(Brick):
    #         id_           = Brick.generate_id('creme_core', 'foobar_block_2')
    #         verbose_name  = u'Testing purpose'
    #         configurable  = False  # <----
    #
    #         def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock3(Brick):
    #         id_           = Brick.generate_id('creme_core', 'foobar_block_3')
    #         verbose_name  = u'Testing purpose'
    #
    #         # def portal_display(self, context, ct_ids): [...]
    #         def home_display(self, context): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock4(Brick):
    #         id_           = Brick.generate_id('creme_core', 'foobar_block_4')
    #         verbose_name  = u'Testing purpose'
    #         target_apps   = ('documents', 'persons', 'activities')  # <-- OK
    #
    #         def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock5(Brick):
    #         id_           = Brick.generate_id('creme_core', 'foobar_block_5')
    #         verbose_name  = u'Testing purpose'
    #         target_apps   = ('documents', 'activities')  # <-- KO !!
    #
    #         def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
    #
    #     class _FoobarInstanceBlock(Brick):
    #         verbose_name  = u'Testing purpose'
    #
    #         def __init__(self, instance_block_config_item):
    #             self.ibci = instance_block_config_item
    #
    #     class FoobarInstanceBlock1(_FoobarInstanceBlock):
    #         id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_1')
    #
    #         def portal_display(self, context, ct_ids):
    #             return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)
    #
    #     class FoobarInstanceBlock2(_FoobarInstanceBlock):
    #         id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_2')
    #         target_apps   = ('documents', 'persons')  # <-- OK !!
    #
    #         def portal_display(self, context, ct_ids):
    #             return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)
    #
    #     class FoobarInstanceBlock3(_FoobarInstanceBlock):
    #         id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_3')
    #         target_apps   = ('documents', 'tickets')  # <-- KO !!
    #
    #         def portal_display(self, context, ct_ids):
    #             return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)
    #
    #     class FoobarInstanceBlock4(_FoobarInstanceBlock):
    #         id_ = InstanceBlockConfigItem.generate_base_id('creme_core', 'foobar_instance_block_4')
    #
    #         def home_display(self, context):  # <====== not portal_display()
    #             return '<table id="%s"><thead><tr>%s</tr></thead></table>' % (self.id_, self.ibci.entity)
    #
    #     create_ibci = InstanceBlockConfigItem.objects.create
    #     ibci1 = create_ibci(entity=casca, verbose=u"I am an awesome block", data='',
    #                         brick_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock1, casca, ''),
    #                        )
    #     ibci2 = create_ibci(entity=casca, verbose=u"I am an awesome block too", data='',
    #                         brick_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock2, casca, ''),
    #                        )
    #     create_ibci(entity=casca, verbose=u"I am a poor block", data='',
    #                 brick_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock3, casca, ''),
    #                )
    #     create_ibci(entity=casca, verbose=u"I am a poor block too", data='',
    #                 brick_id=InstanceBlockConfigItem.generate_id(FoobarInstanceBlock4, casca, ''),
    #                )
    #
    #     brick_registry = _BrickRegistry()
    #
    #     brick_registry.register(FoobarBlock1,
    #                             FoobarBlock2,
    #                             FoobarBlock3,
    #                             FoobarBlock4,
    #                             FoobarBlock5,
    #                            )
    #     brick_registry.register_4_instance(FoobarInstanceBlock1,
    #                                        FoobarInstanceBlock2,
    #                                        FoobarInstanceBlock3,
    #                                        FoobarInstanceBlock4,
    #                                       )
    #
    #     blocks = sorted(brick_registry.get_compatible_portal_blocks('persons'), key=lambda b: b.id_)
    #     self.assertEqual(4, len(blocks))
    #     self.assertIsInstance(blocks[0], FoobarBlock1)
    #     self.assertIsInstance(blocks[1], FoobarBlock4)
    #     self.assertEqual([ibci1.brick_id, ibci2.brick_id], [block.id_ for block in blocks[2:]])
    #
    # def test_get_compatible_portal_blocks02(self):
    #     "Home"
    #     class FoobarBlock1(Brick):
    #         id_ = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_portal_blocks02_1')
    #         verbose_name  = u'Testing purpose'
    #
    #         # NB: only home_display() method
    #         # def detailview_display(self, context): [...]
    #         # def portal_display(self, context, ct_ids): [...]
    #         def home_display(self, context): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock2(Brick):
    #         id_  = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_portal_blocks02_2')
    #         verbose_name  = u'Testing purpose'
    #         configurable  = False  # <----
    #
    #         def home_display(self, context): return '<table id="%s"></table>' % self.id_
    #
    #     class FoobarBlock3(Brick):
    #         id_ = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_portal_blocks02_3')
    #         verbose_name  = u'Testing purpose'
    #
    #         # def home_display(self, context): [...]
    #         def portal_display(self, context, ct_ids): return '<table id="%s"></table>' % self.id_
    #
    #     brick_registry = _BrickRegistry()
    #     brick_registry.register(FoobarBlock1, FoobarBlock2, FoobarBlock3)
    #
    #     blocks = list(brick_registry.get_compatible_portal_blocks('creme_core'))
    #     self.assertEqual(1, len(blocks))
    #     self.assertIsInstance(blocks[0], FoobarBlock1)

    def test_get_compatible_home_bricks(self):
        class FoobarBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_1')
            verbose_name = u'Testing purpose'

            # NB: only home_display() method
            # def detailview_display(self, context): [...]
            # def portal_display(self, context, ct_ids): [...]
            def home_display(self, context): return '<table id="{}"></table>'.format(self.id_)

        class FoobarBrick2(Brick):
            id_  = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_2')
            verbose_name = u'Testing purpose'
            configurable = False  # <----

            def home_display(self, context): return '<table id="{}"></table>'.format(self.id_)

        class FoobarBrick3(Brick):
            id_ = Brick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_3')
            verbose_name = u'Testing purpose'

            def detailview_display(self, context): return '<table id="{}"></table>'.format(self.id_)
            # def home_display(self, context): [...]
            # def portal_display(self, context, ct_ids): return '<table id="{}"></table>'.format(self.id_)

        brick_registry = _BrickRegistry()
        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        blocks = list(brick_registry.get_compatible_home_bricks())
        self.assertEqual(1, len(blocks))
        self.assertIsInstance(blocks[0], FoobarBrick1)

    def test_get_bricks01(self):
        class QuuxBrick1(SimpleBrick):
            id_          = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_1')
            verbose_name = u'Testing purpose #1'

        class QuuxBrick2(SimpleBrick):
            id_          = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_2')
            verbose_name = u'Testing purpose #2'

        class QuuxBrick3(SimpleBrick):
            id_          = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_3')
            verbose_name = u'Testing purpose #3'

        self.assertFalse(InstanceBrickConfigItem.id_is_specific(QuuxBrick1.id_))

        brick_registry = _BrickRegistry()
        brick_registry.register(QuuxBrick1, QuuxBrick2, QuuxBrick3)

        def assertBricks(brick_classes, bricks):
            self.assertIsInstance(bricks, list)
            self.assertEqual(len(brick_classes), len(bricks))

            for brick_cls, brick in zip(brick_classes, bricks):
                self.assertIsInstance(brick, brick_cls)

        assertBricks([QuuxBrick1, QuuxBrick2], list(brick_registry.get_bricks([QuuxBrick1.id_, QuuxBrick2.id_])))

        # Not registered -------------
        bricks = list(brick_registry.get_bricks([SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_4')]))
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], Brick)

    def test_get_bricks02(self):
        "Specific relation blocks, custom blocks"
        class QuuxBrick1(SimpleBrick):
            id_          = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_2')
            verbose_name = u'Testing purpose #1'

        rtype = RelationType.create(('test-subject_loves', 'loves'), ('test-object_loved', 'is loved by'))[0]
        rbi = RelationBrickItem.create(rtype.id)

        cbci = CustomBrickConfigItem.objects.create(
                    id='tests-organisations01', name='General',
                    content_type=ContentType.objects.get_for_model(FakeOrganisation),
                    cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
                )

        brick_registry = _BrickRegistry()
        brick_registry.register(QuuxBrick1)

        bricks = list(brick_registry.get_bricks([QuuxBrick1.id_, rbi.brick_id, cbci.generate_id()]))
        self.assertEqual(3, len(bricks))

        self.assertIsInstance(bricks[0], QuuxBrick1)

        rel_brick = bricks[1]
        self.assertIsInstance(rel_brick, SpecificRelationsBrick)
        self.assertEqual((rtype.id,), rel_brick.relation_type_deps)

        custom_brick = bricks[2]
        self.assertIsInstance(custom_brick, CustomBrick)
        self.assertEqual(cbci.generate_id(), custom_brick.id_)
        self.assertEqual([FakeOrganisation], custom_brick.dependencies)
        self.assertEqual(cbci.name,          custom_brick.verbose_name)

    def test_get_bricks03(self):
        "Hat brick"
        user = self.login()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FakeContactBasicHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactCardHatBrick(SimpleBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'fake_contact_card')
            template_name = 'creme_core/bricks/fake_contact_hat_card.html'  # (does not exists)

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(FakeContact,
                                    main_brick_cls=FakeContactBasicHatBrick,
                                    secondary_brick_classes=[FakeContactCardHatBrick]
                                   )

        brick_id = SimpleBrick.GENERIC_HAT_BRICK_ID
        self.assertFalse(list(brick_registry.get_bricks([brick_id])))

        # ----
        bricks = list(brick_registry.get_bricks([brick_id], entity=casca))
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactBasicHatBrick)

        # ----
        bricks = list(brick_registry.get_bricks([FakeContactCardHatBrick.id_], entity=casca))
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactCardHatBrick)

        # ----
        bricks = list(brick_registry.get_bricks([SimpleBrick._generate_hat_id('creme_core', 'invalid')],
                                                entity=casca,
                                               )
                     )
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactBasicHatBrick)

    def test_brick_4_model01(self):
        block_registry = _BrickRegistry()

        brick = block_registry.get_brick_4_object(FakeOrganisation)
        self.assertEqual(u'modelblock_creme_core-fakeorganisation', brick.id_)
        self.assertEqual((FakeOrganisation,), brick.dependencies)

    def test_brick_4_model02(self):
        block_registry = _BrickRegistry()

        user = self.login()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        brick = block_registry.get_brick_4_object(casca)
        self.assertEqual(u'modelblock_creme_core-fakecontact', brick.id_)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_model03(self):
        class ContactBrick(SimpleBrick):
            template_name = 'persons/templatetags/block_contact.html'

        block_registry = _BrickRegistry()
        block_registry.register_4_model(FakeContact, ContactBrick)

        brick = block_registry.get_brick_4_object(FakeContact)
        self.assertIsInstance(brick, ContactBrick)
        self.assertEqual(u'modelblock_creme_core-fakecontact', brick.id_)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_instance01(self):
        user = self.login()

        create_contact = FakeContact.objects.create
        casca = create_contact(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(Brick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(
                            self.id_, self.ibci.entity
                        )  # useless :)

        self.assertTrue(InstanceBrickConfigItem.id_is_specific(ContactBrick.id_))

        ibci = InstanceBrickConfigItem.objects \
                                      .create(entity=casca,
                                              brick_id=InstanceBrickConfigItem.generate_id(ContactBrick, casca, ''),
                                              verbose=u'I am an awesome block',
                                              data='',
                                             )

        brick_registry = _BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        bricks = list(brick_registry.get_bricks([ibci.brick_id]))
        self.assertEqual(1, len(bricks))

        brick = bricks[0]
        self.assertIsInstance(brick, ContactBrick)
        self.assertEqual(ibci, brick.ibci)
        self.assertEqual(ibci.brick_id, brick.id_)
        self.assertEqual((FakeOrganisation,), brick.dependencies)

        # ----------------------------------------------------------------------
        # In detail-views of an entity we give it in order to compute dependencies correctly.
        judo = create_contact(user=user, first_name='Judo',  last_name='Doe')
        brick = next(brick_registry.get_bricks([ibci.brick_id], entity=judo))
        self.assertEqual((FakeOrganisation, FakeContact), brick.dependencies)

        hawk = FakeOrganisation.objects.create(user=user, name='Hawk')
        brick = next(brick_registry.get_bricks([ibci.brick_id], entity=hawk))
        self.assertEqual((FakeOrganisation,), brick.dependencies)

        # ----------------------------------------------------------------------
        bad_brick_id = InstanceBrickConfigItem.generate_base_id('creme_core', 'does_not_exist') + '#{}_'.format(casca.id)
        InstanceBrickConfigItem.objects.create(entity=casca,
                                               brick_id=bad_brick_id,
                                               verbose=u'I am bad',
                                               data='',
                                              )
        bricks = list(brick_registry.get_bricks([bad_brick_id]))
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], Brick)

    def test_brick_4_instance02(self):
        self.login()

        class BaseBrick(Brick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_brick')  # <====== Used twice !!
            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def __init__(self, instance_block_config_item):
                self.ibci = instance_block_config_item

            def detailview_display(self, context):
                return '<table id="{}"><thead><tr>{}</tr></thead></table>'.format(self.id_, self.ibci.entity)  # Useless :)

        class ContactBrick(BaseBrick): pass
        class OrgaBrick(BaseBrick): pass

        block_registry = _BrickRegistry()
        block_registry.register_4_instance(ContactBrick)
        self.assertRaises(_BrickRegistry.RegistrationError, block_registry.register_4_instance, OrgaBrick)

    # TODO different keys


class BricksManagerTestCase(CremeTestCase):
    def test_manage01(self):
        class TestBlock(SimpleBrick):
            verbose_name  = u'Testing purpose'

        class FoobarBrick1(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_1')

        class FoobarBrick2(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_2')
            dependencies = (FakeContact,)

        class FoobarBrick3(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_3')
            dependencies = (FakeOrganisation,)

        class FoobarBrick4(TestBlock):
            id_ = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_4')
            dependencies = (FakeContact, FakeOrganisation)

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()

        mngr = BricksManager()
        self.assertFalse(mngr.brick_is_registered(brick1))
        self.assertTrue(hasattr(BricksManager, 'Error'))

        name1 = 'gname1'
        mngr.add_group(name1, brick1, brick2, brick3)
        self.assertTrue(mngr.brick_is_registered(brick1))
        self.assertFalse(mngr.brick_is_registered(brick4))
        self.assertRaises(BricksManager.Error, mngr.add_group, name1, brick4)  # Same name
        # self.assertDictEqual({block1.id_: set(),
        #                       block2.id_: set(),
        #                       block3.id_: set(),
        #                      },
        #                      mngr.get_dependencies_map()
        #                     )
        _ = mngr.used_relationtypes_ids
        self.assertRaises(BricksManager.Error, mngr.add_group, 'gname2', brick4)  # Deps already solved

    def test_manage02(self):
        class TestBrick(SimpleBrick):
            verbose_name  = u'Testing purpose'

        class FoobarBrick1(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_1')

        class FoobarBrick2(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_2')
            dependencies = (FakeContact,)

        class FoobarBrick3(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_3')
            dependencies = (FakeOrganisation,)

        class FoobarBrick4(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_4')
            dependencies = (FakeContact, FakeOrganisation)

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()

        mngr = BricksManager()
        mngr.add_group('gname1', brick1, brick2, brick3)
        mngr.add_group('gname2', brick4)
        remaining_groups = mngr.get_remaining_groups()
        self.assertIsInstance(remaining_groups, list)
        self.assertCountEqual(['gname1', 'gname2'], mngr.get_remaining_groups())

        # group =
        mngr.pop_group('gname1')
        # TODO: test group
        self.assertEqual(['gname2'], mngr.get_remaining_groups())
        self.assertRaises(KeyError, mngr.pop_group, 'gname1')

        # self.assertDictEqual({block1.id_: set(),
        #                       block2.id_: {block4.id_},
        #                       block3.id_: {block4.id_},
        #                       block4.id_: {block2.id_, block3.id_},
        #                      },
        #                      mngr.get_dependencies_map()
        #                     )
        dep_map = mngr._build_dependencies_map()
        self.assertEqual(2, len(dep_map))
        self.assertEqual({FoobarBrick2.id_, FoobarBrick4.id_},
                         {brick.id_ for brick in dep_map[FakeContact]}
                        )
        self.assertEqual({FoobarBrick3.id_, FoobarBrick4.id_},
                         {brick.id_ for brick in dep_map[FakeOrganisation]}
                        )

    def test_manage03(self):
        "Relation bricks"
        rtype1_pk = 'test-subject_loves'
        rtype1, srtype1 = RelationType.create((rtype1_pk, 'loves'), ('test-object_loved',  'is loved by'))

        rtype2_pk = 'test-subject_follows'
        rtype2, srtype2 = RelationType.create((rtype2_pk, 'follow'), ('test-object_followed',  'is followed by'))

        class TestBrick(SimpleBrick):
            verbose_name  = u'Testing purpose'

        class FoobarBrick1(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_1')

        class FoobarBrick2(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_2')
            dependencies = (FakeContact,)

        class FoobarBrick3(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_3')
            dependencies = (Relation,)

        self.assertEqual((), FoobarBrick3.relation_type_deps)

        class FoobarBrick4(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_4')
            dependencies = (Relation,)
            relation_type_deps = (rtype1_pk,)

        class FoobarBrick5(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_5')
            dependencies = (Relation,)
            relation_type_deps = (rtype1_pk, rtype2_pk)

        class FoobarBrick6(SpecificRelationsBrick):
            verbose_name = u'Testing purpose'

        self.assertEqual((Relation,), FoobarBrick6.dependencies)

        brick1 = FoobarBrick1(); brick2 = FoobarBrick2()
        brick3 = FoobarBrick3(); brick4 = FoobarBrick4(); brick5 = FoobarBrick5()
        brick6 = FoobarBrick6(RelationBrickItem.create(rtype2_pk))

        mngr = BricksManager()
        mngr.add_group('gname1', brick1, brick2, brick3)
        mngr.add_group('gname2', brick4, brick5, brick6)
        self.assertEqual({rtype1_pk, rtype2_pk}, mngr.used_relationtypes_ids)

        # self.assertDictEqual({block1.id_: set(),
        #                       block2.id_: set(),
        #                       block3.id_: set(),
        #                       block4.id_: {block5.id_},
        #                       block5.id_: {block4.id_, block6.id_},
        #                       block6.id_: {block5.id_},
        #                      },
        #                      mngr.get_dependencies_map()
        #                     )

        rtypes_ids = [srtype1.id, srtype2.id]
        mngr.used_relationtypes_ids = rtypes_ids
        self.assertEqual(set(rtypes_ids), mngr.used_relationtypes_ids)

    def test_wildcard01(self):
        "Wildcard dependencies, read-only"
        id_fmt = 'BricksManagerTestCase__wildcard01_{}'.format

        class FoobarBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(1))

        class FoobarBrick2(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(2))
            dependencies = (FakeContact,)

        class FoobarBrick3(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(3))
            dependencies = (FakeOrganisation,)

        class FoobarBrick4(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(4))
            dependencies = '*'

        class FoobarBrick5(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(5))
            dependencies = '*'

        class FoobarBrick6(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', id_fmt(6))
            dependencies = (Relation,)

        brick1 = FoobarBrick1(); brick2 = FoobarBrick2()
        brick3 = FoobarBrick3(); brick4 = FoobarBrick4()
        brick5 = FoobarBrick5(); brick6 = FoobarBrick6()

        mngr = BricksManager()
        # Notice that brick4 is before brick3, but the dependencies are still OK
        mngr.add_group('gname', brick1, brick2, brick4, brick3, brick5, brick6)

        # self.maxDiff = None
        # self.assertDictEqual({block1.id_: set(),
        #                       block2.id_: {block4.id_, block5.id_},
        #                       block3.id_: {block4.id_, block5.id_},
        #                       block4.id_: {block2.id_, block3.id_, block5.id_},
        #                       block5.id_: {block2.id_, block3.id_, block4.id_},
        #                       block6.id_: {block4.id_, block5.id_},
        #                      },
        #                      mngr.get_dependencies_map()
        #                     )
        dep_map = mngr._build_dependencies_map()
        self.assertEqual(3, len(dep_map))
        self.assertEqual({FoobarBrick2.id_, FoobarBrick4.id_, FoobarBrick5.id_},
                         {brick.id_ for brick in dep_map[FakeContact]}
                        )
        self.assertEqual({FoobarBrick3.id_, FoobarBrick4.id_, FoobarBrick5.id_},
                         {brick.id_ for brick in dep_map[FakeOrganisation]}
                        )
        self.assertEqual({FoobarBrick6.id_, FoobarBrick4.id_, FoobarBrick5.id_},
                         {brick.id_ for brick in dep_map[Relation]}
                        )

    # def test_read_only01(self):
    #     "Read-only dependencies"
    #     class FoobarBlock1(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_core', 'BricksManagerTestCase__read_only01_1')
    #
    #     class FoobarBlock2(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_core', 'BricksManagerTestCase__read_only01_2')
    #         dependencies = (FakeContact,)
    #
    #     block1 = FoobarBlock1(); block2 = FoobarBlock2()
    #     self.assertIs(block1.read_only, False)
    #
    #     class FoobarBlock3(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_core', 'BricksManagerTestCase__read_only01_3')
    #         dependencies = (FakeOrganisation,)
    #
    #     class FoobarBlock4(SimpleBrick):
    #         id_ = SimpleBrick.generate_id('creme_core', 'BricksManagerTestCase__read_only01_4')
    #         dependencies = (FakeOrganisation, FakeContact)
    #         read_only = True  # <=====
    #
    #     block3 = FoobarBlock3(); block4 = FoobarBlock4()
    #
    #     mngr = BricksManager()
    #     mngr.add_group('gname', block1, block2, block3, block4)
    #
    #     self.assertDictEqual({block1.id_: set(),
    #                           block2.id_: {block4.id_},
    #                           block3.id_: {block4.id_},
    #                           block4.id_: set(),  # <=====
    #                          },
    #                          mngr.get_dependencies_map()
    #                         )

    def test_get(self):
        mngr = BricksManager()

        with self.assertNoException():
            fake_context = {mngr.var_name: mngr}

        self.assertIs(mngr, BricksManager.get(fake_context))

    # TODO: test def get_state(self, brick_id, user)


class BrickTestCase(CremeTestCase):
    def setUp(self):
        # super(BrickTestCase, self).setUp()
        super().setUp()
        self.factory = RequestFactory()

    class OrderedBrick(QuerysetBrick):
        id_ = QuerysetBrick.generate_id('creme_core', 'BrickTestCase-test_queryset_brick_order')
        dependencies = (FakeContact,)
        page_size = 10
        order_by = 'last_name'

    def _assertPageOrderedLike(self, page, ordered_instances):
        ids = {c.id for c in ordered_instances}
        self.assertEqual(ordered_instances,
                         [c for c in page.object_list if c.id in ids]
                        )

    def _build_request(self, url='/'):  # TODO: factorise (see CremeBricksTagsTestCase)
        request = self.factory.get(url)
        request.session = SessionBase()
        request.user = self.user

        return request

    def test_custom_brick01(self):
        cbci = CustomBrickConfigItem.objects.create(
                id='tests-organisations01', name='General',
                content_type=ContentType.objects.get_for_model(FakeOrganisation),
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        cbrick = CustomBrick(cbci.generate_id(), cbci)
        self.assertEqual([FakeOrganisation], cbrick.dependencies)
        self.assertFalse(cbrick.relation_type_deps)

    def test_custom_brick02(self):
        "Relation + dependencies"
        rtype = RelationType.create(('test-subject_employs', 'employs'),
                                    ('test-object_employs', 'is employed by')
                                   )[0]

        cbci = CustomBrickConfigItem.objects.create(
                id='tests-organisations01', name='General',
                content_type=ContentType.objects.get_for_model(FakeOrganisation),
                cells=[EntityCellRegularField.build(FakeOrganisation, 'name'),
                       EntityCellRelation(model=FakeOrganisation, rtype=rtype),
                      ],
        )

        cbrick = CustomBrick(cbci.generate_id(), cbci)
        self.assertEqual([FakeOrganisation, Relation], cbrick.dependencies)
        self.assertEqual([rtype.id], cbrick.relation_type_deps)

    def test_paginated_brick01(self):
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz',  last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        template_context = brick.get_template_context(build_context(self._build_request()),
                                                      FakeContact.objects.filter(description=description),
                                                     )

        with self.assertNoException():
            page = template_context['page']

        self.assertEqual(2, page.paginator.per_page)
        self.assertEqual(2, page.paginator.num_pages)
        self.assertEqual(1, page.number)

    def test_paginated_brick02(self):
        "Page in request"
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz',  last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        request = self._build_request('/?{}_page=2'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request),
                                                      FakeContact.objects.filter(description=description),
                                                     )

        page = template_context['page']
        self.assertEqual(2, page.number)

    def test_paginated_brick03(self):
        "Page in request: invalid number (not int)"
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz', last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        request = self._build_request('/?{}_page=NaN'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request),
                                                      FakeContact.objects.filter(description=description),
                                                     )

        page = template_context['page']
        self.assertEqual(1, page.number)

    def test_paginated_brick04(self):
        "Page in request: number too great."
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz', last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        request = self._build_request('/?{}_page=3'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request),
                                                      FakeContact.objects.filter(description=description),
                                                     )

        page = template_context['page']
        self.assertEqual(2, page.number)

    def test_queryset_brick_order01(self):
        "No order in request"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        template_context = brick.get_template_context(build_context(self._build_request()),
                                                      FakeContact.objects.all(),
                                                     )

        with self.assertNoException():
            page = template_context['page']
            model = page.object_list.model

        self.assertEqual(FakeContact, model)
        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order02(self):
        "No order in request: invalid field in Brick class"
        user = self.login()

        class ProblematicBrick(QuerysetBrick):
            id_ = QuerysetBrick.generate_id('creme_core', 'BrickTestCase-test_queryset_brick_order02')
            dependencies = (FakeContact,)
            order_by = 'unknown'  # < ===

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = ProblematicBrick()
        template_context = brick.get_template_context(build_context(self._build_request()),
                                                      FakeContact.objects.all(),
                                                     )
        self._assertPageOrderedLike(template_context['page'], [cranel, crozzo, wallen])

    def test_queryset_brick_order03(self):
        "Order in request: valid field"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        aiz  = create_contact(first_name='Aiz',      last_name='Wallenstein')
        lili = create_contact(first_name='Liliruca', last_name='Arde')
        bell = create_contact(first_name='Bell',     last_name='Cranel')
        welf = create_contact(first_name='Welf',     last_name='Crozzo')

        brick = self.OrderedBrick()

        # ASC
        request = self._build_request('/?{}_order=first_name'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request), FakeContact.objects.all())
        self._assertPageOrderedLike(template_context['page'], [aiz, bell, lili, welf])

        # DESC
        request = self._build_request('/?{}_order=-first_name'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request), FakeContact.objects.all())
        self._assertPageOrderedLike(template_context['page'], [welf, lili, bell, aiz])

    def test_queryset_brick_order04(self):
        "Order in request: invalid field"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        request = self._build_request('/?{}_order=unknown'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request), FakeContact.objects.all())

        with self.assertNoException():
            page = template_context['page']
            list(page.object_list)

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order05(self):
        "Order in request: not sortable field"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        request = self._build_request('/?{}_order=languages'.format(brick.id_))
        template_context = brick.get_template_context(build_context(request), FakeContact.objects.all())

        with self.assertNoException():
            page = template_context['page']
            list(page.object_list)

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])
