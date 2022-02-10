# -*- coding: utf-8 -*-

from functools import partial

from django.contrib.sessions.backends.base import SessionBase
from django.template.context import make_context
from django.template.engine import Engine
from django.test import RequestFactory
from django.utils.translation import gettext as _

from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.gui.bricks import (
    Brick,
    BricksManager,
    CustomBrick,
    EntityBrick,
    InstanceBrick,
    QuerysetBrick,
    SimpleBrick,
    SpecificRelationsBrick,
    _BrickRegistry,
)
from creme.creme_core.models import (
    CustomBrickConfigItem,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    InstanceBrickConfigItem,
    Relation,
    RelationBrickItem,
    RelationType,
)

from ..base import CremeTestCase


class BrickRegistryTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        RelationBrickItem.objects.all().delete()
        InstanceBrickConfigItem.objects.all().delete()

    def test_register01(self):
        class FoobarBrick(Brick):
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick1(FoobarBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(FoobarBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_2')

        brick_registry = _BrickRegistry()
        self.assertListEqual([], [*brick_registry])

        with self.assertRaises(KeyError):
            brick_registry[FoobarBrick1.id_]  # NOQA

        # 1 brick
        brick_registry.register(FoobarBrick1)
        self.assertListEqual([(FoobarBrick1.id_, FoobarBrick1)], [*brick_registry])
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id_])

        # 2 bricks
        brick_registry.register(FoobarBrick2)
        self.assertCountEqual(
            [
                (FoobarBrick1.id_, FoobarBrick1),
                (FoobarBrick2.id_, FoobarBrick2),
            ],
            [*brick_registry],
        )
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id_])
        self.assertEqual(FoobarBrick2, brick_registry[FoobarBrick2.id_])

    def test_register02(self):
        "2 classes at once."
        class FoobarBrick(Brick):
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick1(FoobarBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(FoobarBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_2')

        brick_registry = _BrickRegistry()
        brick_registry.register(FoobarBrick1, FoobarBrick2)
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id_])
        self.assertEqual(FoobarBrick2, brick_registry[FoobarBrick2.id_])

    def test_register03(self):
        "Duplicates."
        class FoobarBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick2(FoobarBrick1):
            pass

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register(FoobarBrick1, FoobarBrick2)

        self.assertEqual(
            f"Duplicated brick's id: {FoobarBrick2.id_}", str(cm.exception),
        )

    def test_register04(self):
        "Empty ID."
        class FoobarBrick(Brick):
            # id_ = Brick.generate_id('creme_core', 'foobar_brick')  # NOPE
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register(FoobarBrick)

        self.assertEqual(
            f"Brick class with empty id_: {FoobarBrick}", str(cm.exception),
        )

    def test_register05(self):
        "Old <permission> attribute."
        class FoobarBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = 'Testing purpose'
            permission = 'creme_core'  # <== Old attribute

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register(FoobarBrick1)

        self.assertEqual(
            f'Brick class with old attribute "permission" '
            f'(use "permissions" instead): {FoobarBrick1}',
            str(cm.exception),
        )

    def test_register_4_instance01(self):
        user = self.create_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        class _FoobarInstanceBrick(InstanceBrick):
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        class FoobarInstanceBrick1(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')

        class FoobarInstanceBrick2(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_2')

        class FoobarInstanceBrick3(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_3')

        create_ibci = partial(InstanceBrickConfigItem.objects.create, entity=casca)
        ibci1 = create_ibci(brick_class_id=FoobarInstanceBrick1.id_)
        ibci2 = create_ibci(brick_class_id=FoobarInstanceBrick2.id_)
        brick_registry = _BrickRegistry()

        ibrick1 = brick_registry.get_brick_4_instance(ibci1)
        self.assertIs(ibrick1.__class__, InstanceBrick)
        self.assertEqual('??', ibrick1.verbose_name)
        self.assertListEqual(
            [_('Unknown type of block (bad uninstall ?)')],
            ibrick1.errors,
        )

        # 1 brick
        brick_registry.register_4_instance(FoobarInstanceBrick1)

        ibrick2 = brick_registry.get_brick_4_instance(ibci1)
        self.assertIsInstance(ibrick2, FoobarInstanceBrick1)
        self.assertEqual(ibci1.brick_id, ibrick2.id_)
        self.assertFalse(ibrick2.dependencies)
        self.assertIsNone(ibrick2.errors)

        self.assertIs(
            brick_registry.get_brick_4_instance(ibci2).__class__, InstanceBrick,
        )

        # 3 bricks
        brick_registry.register_4_instance(FoobarInstanceBrick2, FoobarInstanceBrick3)
        self.assertIsInstance(
            brick_registry.get_brick_4_instance(ibci1), FoobarInstanceBrick1,
        )
        self.assertIsInstance(
            brick_registry.get_brick_4_instance(ibci2), FoobarInstanceBrick2,
        )

    def test_register_4_instance02(self):
        "Duplicates."
        class FoobarInstanceBrick1(InstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        class FoobarInstanceBrick2(FoobarInstanceBrick1):
            verbose_name = 'Testing purpose #2'

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(
                FoobarInstanceBrick1, FoobarInstanceBrick2,
            )

        self.assertEqual(
            f"Duplicated brick's id: {FoobarInstanceBrick2.id_}",
            str(cm.exception),
        )

    def test_register_4_instance03(self):
        "Empty ID."
        class FoobarInstanceBrick(InstanceBrick):
            # id_ = InstanceBrickConfigItem.generate_base_id(...)
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(FoobarInstanceBrick)

        self.assertEqual(
            f"Brick class with empty id_: {FoobarInstanceBrick}",
            str(cm.exception),
        )

    def test_register_4_instance04(self):
        "Invalid base class."
        class FoobarInstanceBrick(Brick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr></tr></thead></table>'

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(FoobarInstanceBrick)

        self.assertEqual(
            f"Brick class does not inherit InstanceBrick: {FoobarInstanceBrick}",
            str(cm.exception),
        )

    def test_get_brick_4_instance(self):
        "With 'entity' argument."
        user = self.create_user()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FoobarInstanceBrick(InstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')
            verbose_name = 'Testing purpose'
            dependencies = (FakeOrganisation, )

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=FoobarInstanceBrick.id_,
        )
        brick_registry = _BrickRegistry()

        brick_registry.register_4_instance(FoobarInstanceBrick)

        ibrick = brick_registry.get_brick_4_instance(ibci, entity=casca)
        self.assertIsInstance(ibrick, FoobarInstanceBrick)
        self.assertEqual((FakeOrganisation, FakeContact), ibrick.dependencies)

    def test_get_compatible_bricks01(self):
        user = self.create_user()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FoobarBrick1(Brick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick2(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_2')
            verbose_name = 'Testing purpose'
            target_ctypes = (FakeContact, FakeOrganisation)

        class FoobarBrick3(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_3')
            verbose_name = 'Testing purpose'
            target_ctypes = (FakeOrganisation,)  # Not 'Contact'

        class FoobarBrick4(SimpleBrick):
            id_ = Brick.generate_id('creme_core', 'foobar_brick_4')
            verbose_name = 'Testing purpose'
            configurable = False  # <------

        class FoobarBrick5(Brick):  # No detailview_display() method
            id_ = Brick.generate_id('creme_core', 'foobar_brick_5')
            verbose_name = 'Testing purpose'

            def home_display(self, context):
                return f'<table id="{self.id_}"></table>'

        class FakeContactBrick(EntityBrick):
            verbose_name = 'Fake Contact block'

        class FakeOrganisationBrick(EntityBrick):
            verbose_name = 'Fake Organisation block'

        class _FoobarInstanceBrick(InstanceBrick):
            verbose_name = 'Testing purpose'

        class FoobarInstanceBrick1(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        class FoobarInstanceBrick2(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_2')
            target_ctypes = (FakeContact, FakeOrganisation)  # <-- OK !!

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        class FoobarInstanceBrick3(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_3')
            target_ctypes = (FakeOrganisation, FakeImage)  # <-- KO !!

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        class FoobarInstanceBrick4(_FoobarInstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_4')

            def home_display(self, context):  # <====== not detailview_display()
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'

        create_ibci = partial(InstanceBrickConfigItem.objects.create, entity=casca)
        ibci1 = create_ibci(brick_class_id=FoobarInstanceBrick1.id_)
        ibci2 = create_ibci(brick_class_id=FoobarInstanceBrick2.id_)
        create_ibci(brick_class_id=FoobarInstanceBrick3.id_)
        create_ibci(brick_class_id=FoobarInstanceBrick4.id_)

        brick_registry = _BrickRegistry()

        rtype1 = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves'),
            ('test-object_loved', 'is loved by'),
        )[0]
        RelationBrickItem.objects.create_if_needed(rtype1)

        create_cbci = CustomBrickConfigItem.objects.create
        cbci = create_cbci(
            id='test-contacts01', name='General (contact)',
            content_type=FakeContact,
            cells=[EntityCellRegularField.build(FakeContact, 'last_name')],
        )
        create_cbci(
            id='test-organisations01', name='General (orga)',
            content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )  # Not compatible with Contact

        brick_registry.register(
            FoobarBrick1,
            FoobarBrick2,
            FoobarBrick3,
            FoobarBrick4,
            FoobarBrick5,
        ).register_4_model(
            FakeContact, FakeContactBrick,
        ).register_4_model(
            FakeOrganisation, FakeOrganisationBrick
        ).register_4_instance(
            FoobarInstanceBrick1,
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
        self.assertEqual(cbci.brick_id, brick.id_)

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

    def test_get_compatible_bricks02(self):
        "SpecificRelationsBrick."
        create_rtype = RelationType.objects.smart_update_or_create
        rtype1 = create_rtype(
            ('test-subject_loves', 'loves'),
            ('test-object_loved', 'is loved by'),
        )[0]
        rtype2 = create_rtype(
            ('test-subject_hires', 'hires', [FakeOrganisation]),
            ('test-object_hires', 'is hired by'),
        )[0]

        create_rbi = RelationBrickItem.objects.create_if_needed
        create_rbi(rtype1)
        create_rbi(rtype2)

        brick_registry = _BrickRegistry()

        def extract_rtypes(**kwargs):
            return [
                brick.config_item.relation_type
                for brick in brick_registry.get_compatible_bricks(**kwargs)
                if isinstance(brick, SpecificRelationsBrick)
            ]

        # No model ----
        rtypes = extract_rtypes()
        self.assertGreaterEqual(2, len(rtypes))
        self.assertIn(rtype1, rtypes)
        self.assertNotIn(rtype2, rtypes)  # Not compatible with all kind of entity

        # Compatible model ----
        rtypes = extract_rtypes(model=FakeOrganisation)
        self.assertIn(rtype1, rtypes)
        self.assertIn(rtype2, rtypes)

        # Incompatible model ----
        rtypes = extract_rtypes(model=FakeContact)
        self.assertIn(rtype1, rtypes)
        self.assertNotIn(rtype2, rtypes)

    def test_get_compatible_bricks03(self):
        "No custom model brick."
        brick_registry = _BrickRegistry()

        def extract_model_brick(**kwargs):
            return [
                brick
                for brick in brick_registry.get_compatible_bricks(**kwargs)
                if isinstance(brick, EntityBrick)
            ]

        # No model ----
        bricks1 = extract_model_brick()
        self.assertEqual(1, len(bricks1), bricks1)

        # Model ----
        bricks2 = extract_model_brick(model=FakeOrganisation)
        self.assertEqual(1, len(bricks2), bricks2)

    def test_get_compatible_hat_bricks01(self):
        brick_registry = _BrickRegistry()
        bricks = [*brick_registry.get_compatible_hat_bricks(FakeContact)]
        self.assertEqual(1, len(bricks))

        brick = bricks[0]
        self.assertIsInstance(brick, SimpleBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual('creme_core/bricks/generic/hat-bar.html', brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id_)

    def test_get_compatible_hat_bricks02(self):
        "Register main class."
        template = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick(SimpleBrick):
            template_name = template

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(FakeContact, main_brick_cls=FakeContactHatBrick)
        bricks = [*brick_registry.get_compatible_hat_bricks(FakeContact)]
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
        "Secondary classes."
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick01(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_1')

        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_2')

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(
            FakeContact,
            secondary_brick_classes=(FakeContactHatBrick01, FakeContactHatBrick02),
        )

        bricks = [*brick_registry.get_compatible_hat_bricks(FakeContact)]
        self.assertEqual(3, len(bricks))

        self.assertIsInstance(bricks[0], SimpleBrick)
        self.assertSetEqual(
            {FakeContactHatBrick01, FakeContactHatBrick02},
            {brick.__class__ for brick in bricks[1:]},
        )

    def test_get_compatible_hat_bricks03_error(self):
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        # id_ is None -----------
        class FakeContactHatBrick01(BaseFakeContactHatBrick):
            pass

        brick_registry = _BrickRegistry()

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick01],
            )

        # Bad id_ type ------------
        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'test_get_compatible_hat_bricks03_error')

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick02],
            )

        # Duplicated id_ -------------
        class FakeContactHatBrick03(BaseFakeContactHatBrick):
            id_ = SimpleBrick._generate_hat_id(
                'creme_core', 'test_get_compatible_hat_bricks03_error',
            )

        class FakeContactHatBrick04(BaseFakeContactHatBrick):
            id_ = FakeContactHatBrick03.id_  # <===

        with self.assertNoException():
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick03],
            )

        with self.assertRaises(_BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick04],
            )

    def test_get_compatible_home_bricks(self):
        class FoobarBrick1(Brick):
            id_ = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_1',
            )
            verbose_name = 'Testing purpose'

            # NB: only home_display() method
            # def detailview_display(self, context): [...]
            def home_display(self, context):
                return f'<table id="{self.id_}"></table>'

        class FoobarBrick2(Brick):
            id_ = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_2',
            )
            verbose_name = 'Testing purpose'
            configurable = False  # <----

            def home_display(self, context):
                return f'<table id="{self.id_}"></table>'

        class FoobarBrick3(Brick):
            id_ = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_3',
            )
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"></table>'
            # def home_display(self, context): [...]

        brick_registry = _BrickRegistry()
        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        blocks = [*brick_registry.get_compatible_home_bricks()]
        self.assertEqual(1, len(blocks))
        self.assertIsInstance(blocks[0], FoobarBrick1)

    def test_get_bricks01(self):
        class QuuxBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_1')
            verbose_name = 'Testing purpose #1'

        class QuuxBrick2(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_2')
            verbose_name = 'Testing purpose #2'

        class QuuxBrick3(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_3')
            verbose_name = 'Testing purpose #3'

        # self.assertFalse(InstanceBrickConfigItem.id_is_specific(QuuxBrick1.id_))

        brick_registry = _BrickRegistry()
        brick_registry.register(QuuxBrick1, QuuxBrick2, QuuxBrick3)

        def assertBricks(brick_classes, bricks):
            self.assertIsList(bricks, length=len(brick_classes))

            for brick_cls, brick in zip(brick_classes, bricks):
                self.assertIsInstance(brick, brick_cls)

        assertBricks(
            [QuuxBrick1, QuuxBrick2],
            [*brick_registry.get_bricks([QuuxBrick1.id_, QuuxBrick2.id_])],
        )

        # Not registered -------------
        bricks = [
            *brick_registry.get_bricks([
                SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_4'),
            ])
        ]
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], Brick)

    def test_get_bricks02(self):
        "Model brick."
        user = self.create_user()

        class ContactBrick(EntityBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = _BrickRegistry()
        brick_registry.register_4_model(FakeContact, ContactBrick)

        # No entity
        self.assertFalse([*brick_registry.get_bricks([MODELBRICK_ID])])

        # No registered model brick
        orga = FakeOrganisation.objects.create(user=user, name='Hawk')
        orga_brick = next(brick_registry.get_bricks([MODELBRICK_ID], entity=orga))
        self.assertIsInstance(orga_brick, EntityBrick)

        # No registered model brick
        contact = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')
        contact_brick = next(brick_registry.get_bricks([MODELBRICK_ID], entity=contact))
        self.assertIsInstance(contact_brick, EntityBrick)

    def test_get_bricks03(self):
        "Specific relation bricks, custom bricks."
        class QuuxBrick1(SimpleBrick):
            id_ = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_2')
            verbose_name = 'Testing purpose #1'

        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves'),
            ('test-object_loved', 'is loved by'),
        )[0]
        rbi = RelationBrickItem.objects.create_if_needed(rtype)

        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        brick_registry = _BrickRegistry()
        brick_registry.register(QuuxBrick1)

        bricks = [
            *brick_registry.get_bricks([QuuxBrick1.id_, rbi.brick_id, cbci.brick_id]),
        ]
        self.assertEqual(3, len(bricks))

        self.assertIsInstance(bricks[0], QuuxBrick1)

        rel_brick = bricks[1]
        self.assertIsInstance(rel_brick, SpecificRelationsBrick)
        self.assertEqual((rtype.id,), rel_brick.relation_type_deps)

        custom_brick = bricks[2]
        self.assertIsInstance(custom_brick, CustomBrick)
        self.assertEqual(cbci.brick_id,      custom_brick.id_)
        self.assertEqual([FakeOrganisation], custom_brick.dependencies)
        self.assertEqual(cbci.name,          custom_brick.verbose_name)

    def test_get_bricks04(self):
        "Hat brick."
        user = self.create_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        class FakeContactBasicHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactCardHatBrick(SimpleBrick):
            id_ = SimpleBrick._generate_hat_id('creme_core', 'fake_contact_card')
            template_name = 'creme_core/bricks/fake_contact_hat_card.html'  # (does not exists)

        brick_registry = _BrickRegistry()
        brick_registry.register_hat(
            FakeContact,
            main_brick_cls=FakeContactBasicHatBrick,
            secondary_brick_classes=[FakeContactCardHatBrick],
        )

        brick_id = SimpleBrick.GENERIC_HAT_BRICK_ID
        self.assertFalse([*brick_registry.get_bricks([brick_id])])

        # ----
        bricks = [*brick_registry.get_bricks([brick_id], entity=casca)]
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactBasicHatBrick)

        # ----
        bricks = [*brick_registry.get_bricks([FakeContactCardHatBrick.id_], entity=casca)]
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactCardHatBrick)

        # ----
        bricks = [
            *brick_registry.get_bricks(
                [SimpleBrick._generate_hat_id('creme_core', 'invalid')],
                entity=casca,
            ),
        ]
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], FakeContactBasicHatBrick)

    def test_brick_4_model01(self):
        brick_registry = _BrickRegistry()

        brick = brick_registry.get_brick_4_object(FakeOrganisation)
        self.assertEqual(MODELBRICK_ID, brick.id_)
        self.assertEqual((FakeOrganisation,), brick.dependencies)

    def test_brick_4_model02(self):
        brick_registry = _BrickRegistry()

        user = self.create_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        brick = brick_registry.get_brick_4_object(casca)
        self.assertEqual(brick.__class__, EntityBrick)
        self.assertEqual(MODELBRICK_ID, brick.id_)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_model03(self):
        class ContactBrick(EntityBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = _BrickRegistry()
        brick_registry.register_4_model(FakeContact, ContactBrick)

        brick = brick_registry.get_brick_4_object(FakeContact)
        self.assertIsInstance(brick, ContactBrick)
        self.assertEqual(MODELBRICK_ID, brick.id_)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_model04(self):
        "Custom brick does not inherit EntityBrick."
        class ContactBrick(SimpleBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = _BrickRegistry()
        with self.assertRaises(AssertionError):
            brick_registry.register_4_model(FakeContact, ContactBrick)

    def test_brick_4_instance01(self):
        user = self.create_user()

        create_contact = FakeContact.objects.create
        casca = create_contact(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(InstanceBrick):
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'  # useless :)

        # self.assertTrue(InstanceBrickConfigItem.id_is_specific(ContactBrick.id_))

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=ContactBrick.id_,
        )

        brick_registry = _BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        brick_id = ibci.brick_id
        bricks = [*brick_registry.get_bricks([brick_id])]
        self.assertEqual(1, len(bricks))

        brick = bricks[0]
        self.assertIsInstance(brick, ContactBrick)
        self.assertEqual(ibci, brick.config_item)
        self.assertEqual(brick_id, brick.id_)
        self.assertEqual((FakeOrganisation,), brick.dependencies)

        # ----------------------------------------------------------------------
        # In detail-views of an entity we give it in order to compute dependencies correctly.
        judo = create_contact(user=user, first_name='Judo',  last_name='Doe')
        brick = next(brick_registry.get_bricks([brick_id], entity=judo))
        self.assertEqual((FakeOrganisation, FakeContact), brick.dependencies)

        hawk = FakeOrganisation.objects.create(user=user, name='Hawk')
        brick = next(brick_registry.get_bricks([brick_id], entity=hawk))
        self.assertEqual((FakeOrganisation,), brick.dependencies)

        # ----------------------------------------------------------------------
        bad_ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=InstanceBrickConfigItem.generate_base_id(
                'creme_core',
                'does_not_exist',  # <==
            ),
        )
        bricks = [*brick_registry.get_bricks([bad_ibci.brick_id])]
        self.assertEqual(1, len(bricks))
        self.assertIsInstance(bricks[0], Brick)

    def test_brick_4_instance02(self):
        self.login()

        class BaseBrick(InstanceBrick):
            # Used twice !!
            id_ = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_brick')

            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def detailview_display(self, context):
                return f'<table id="{self.id_}"><thead><tr>' \
                       f'{self.config_item.entity}</tr></thead></table>'  # Useless :)

        class ContactBrick(BaseBrick):
            pass

        class OrgaBrick(BaseBrick):
            pass

        brick_registry = _BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)
        self.assertRaises(
            _BrickRegistry.RegistrationError,
            brick_registry.register_4_instance,
            OrgaBrick,
        )

    # TODO different keys


class BricksManagerTestCase(CremeTestCase):
    def test_manage01(self):
        class TestBlock(SimpleBrick):
            verbose_name = 'Testing purpose'

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
        _ = mngr.used_relationtypes_ids

        # Dependencies already solved
        self.assertRaises(BricksManager.Error, mngr.add_group, 'gname2', brick4)

    def test_manage02(self):
        class TestBrick(SimpleBrick):
            verbose_name = 'Testing purpose'

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
        self.assertIsList(remaining_groups)
        self.assertCountEqual(['gname1', 'gname2'], mngr.get_remaining_groups())

        # group =
        mngr.pop_group('gname1')
        # TODO: test group
        self.assertEqual(['gname2'], mngr.get_remaining_groups())
        self.assertRaises(KeyError, mngr.pop_group, 'gname1')

        dep_map = mngr._build_dependencies_map()
        self.assertEqual(2, len(dep_map))
        self.assertSetEqual(
            {FoobarBrick2.id_, FoobarBrick4.id_},
            {brick.id_ for brick in dep_map[FakeContact]},
        )
        self.assertSetEqual(
            {FoobarBrick3.id_, FoobarBrick4.id_},
            {brick.id_ for brick in dep_map[FakeOrganisation]},
        )

    def test_manage03(self):
        "Relation bricks."
        rtype1_pk = 'test-subject_loves'
        rtype1, srtype1 = RelationType.objects.smart_update_or_create(
            (rtype1_pk,           'loves'),
            ('test-object_loved', 'is loved by'),
        )

        rtype2_pk = 'test-subject_follows'
        rtype2, srtype2 = RelationType.objects.smart_update_or_create(
            (rtype2_pk,              'follow'),
            ('test-object_followed', 'is followed by'),
        )

        class TestBrick(SimpleBrick):
            verbose_name = 'Testing purpose'

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
            verbose_name = 'Testing purpose'

        self.assertEqual((Relation,), FoobarBrick6.dependencies)

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()
        brick5 = FoobarBrick5()
        brick6 = FoobarBrick6(RelationBrickItem.objects.create_if_needed(rtype2))

        mngr = BricksManager()
        mngr.add_group('gname1', brick1, brick2, brick3)
        mngr.add_group('gname2', brick4, brick5, brick6)
        self.assertEqual({rtype1_pk, rtype2_pk}, mngr.used_relationtypes_ids)

        rtypes_ids = [srtype1.id, srtype2.id]
        mngr.used_relationtypes_ids = rtypes_ids
        self.assertSetEqual({*rtypes_ids}, mngr.used_relationtypes_ids)

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

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()
        brick5 = FoobarBrick5()
        brick6 = FoobarBrick6()

        mngr = BricksManager()
        # Notice that brick4 is before brick3, but the dependencies are still OK
        mngr.add_group('gname', brick1, brick2, brick4, brick3, brick5, brick6)

        dep_map = mngr._build_dependencies_map()
        self.assertEqual(3, len(dep_map))
        self.assertEqual(
            {FoobarBrick2.id_, FoobarBrick4.id_, FoobarBrick5.id_},
            {brick.id_ for brick in dep_map[FakeContact]},
        )
        self.assertSetEqual(
            {FoobarBrick3.id_, FoobarBrick4.id_, FoobarBrick5.id_},
            {brick.id_ for brick in dep_map[FakeOrganisation]},
        )
        self.assertSetEqual(
            {FoobarBrick6.id_, FoobarBrick4.id_, FoobarBrick5.id_},
            {brick.id_ for brick in dep_map[Relation]},
        )

    def test_get(self):
        mngr = BricksManager()

        with self.assertNoException():
            fake_context = {mngr.var_name: mngr}

        self.assertIs(mngr, BricksManager.get(fake_context))

    # TODO: test def get_state(self, brick_id, user)


class BrickTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    class OrderedBrick(QuerysetBrick):
        id_ = QuerysetBrick.generate_id('creme_core', 'BrickTestCase-test_queryset_brick_order')
        dependencies = (FakeContact,)
        page_size = 10
        order_by = 'last_name'

    def _assertPageOrderedLike(self, page, ordered_instances):
        ids = {c.id for c in ordered_instances}
        self.assertListEqual(
            ordered_instances,
            [c for c in page.object_list if c.id in ids],
        )

    def _build_request(self, url='/'):  # TODO: factorise (see CremeBricksTagsTestCase)
        request = self.factory.get(url)
        request.session = SessionBase()
        request.user = self.user

        return request

    @staticmethod
    def _build_context(request):
        context = make_context({}, request)

        for processor in Engine.get_default().template_context_processors:
            context.update(processor(request))

        return context.flatten()

    def test_custom_brick01(self):
        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        cbrick = CustomBrick(cbci.brick_id, cbci)
        self.assertEqual([FakeOrganisation], cbrick.dependencies)
        self.assertFalse(cbrick.relation_type_deps)

    def test_custom_brick02(self):
        "Relation + dependencies."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_employs', 'employs'),
            ('test-object_employs', 'is employed by'),
        )[0]

        cbci = CustomBrickConfigItem.objects.create(
            id='tests-organisations01', name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRelation(model=FakeOrganisation, rtype=rtype),
            ],
        )

        cbrick = CustomBrick(cbci.brick_id, cbci)
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
        template_context = brick.get_template_context(
            self._build_context(self._build_request()),
            FakeContact.objects.filter(description=description),
        )

        with self.assertNoException():
            page = template_context['page']

        self.assertEqual(2, page.paginator.per_page)
        self.assertEqual(2, page.paginator.num_pages)
        self.assertEqual(1, page.number)

    def test_paginated_brick02(self):
        "Page in request."
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz',  last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        request = self._build_request(f'/?{brick.id_}_page=2')
        template_context = brick.get_template_context(
            self._build_context(request),
            FakeContact.objects.filter(description=description),
        )

        page = template_context['page']
        self.assertEqual(2, page.number)

    def test_paginated_brick03(self):
        "Page in request: invalid number (not int)."
        user = self.login()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz', last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        request = self._build_request(f'/?{brick.id_}_page=NaN')
        template_context = brick.get_template_context(
            self._build_context(request),
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
        request = self._build_request(f'/?{brick.id_}_page=3')
        template_context = brick.get_template_context(
            self._build_context(request),
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
        template_context = brick.get_template_context(
            self._build_context(self._build_request()),
            FakeContact.objects.all(),
        )

        with self.assertNoException():
            page = template_context['page']
            model = page.object_list.model

        self.assertEqual(FakeContact, model)
        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order02(self):
        "No order in request: invalid field in Brick class."
        user = self.login()

        class ProblematicBrick(QuerysetBrick):
            id_ = QuerysetBrick.generate_id(
                'creme_core', 'BrickTestCase-test_queryset_brick_order02',
            )
            dependencies = (FakeContact,)
            order_by = 'unknown'  # < ===

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = ProblematicBrick()
        template_context = brick.get_template_context(
            self._build_context(self._build_request()),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [cranel, crozzo, wallen])

    def test_queryset_brick_order03(self):
        "Order in request: valid field."
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        aiz  = create_contact(first_name='Aiz',      last_name='Wallenstein')
        lili = create_contact(first_name='Liliruca', last_name='Arde')
        bell = create_contact(first_name='Bell',     last_name='Cranel')
        welf = create_contact(first_name='Welf',     last_name='Crozzo')

        brick = self.OrderedBrick()

        # ASC
        request = self._build_request(f'/?{brick.id_}_order=first_name')
        template_context = brick.get_template_context(
            self._build_context(request),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [aiz, bell, lili, welf])

        # DESC
        request = self._build_request(f'/?{brick.id_}_order=-first_name')
        template_context = brick.get_template_context(
            self._build_context(request),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [welf, lili, bell, aiz])

    def test_queryset_brick_order04(self):
        "Order in request: invalid field."
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        request = self._build_request(f'/?{brick.id_}_order=unknown')
        template_context = brick.get_template_context(
            self._build_context(request),
            FakeContact.objects.all()
        )

        with self.assertNoException():
            page = template_context['page']
            [*page.object_list]  # NOQA

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order05(self):
        "Order in request: not sortable field"
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        request = self._build_request(f'/?{brick.id_}_order=languages')
        template_context = brick.get_template_context(
            self._build_context(request),
            FakeContact.objects.all()
        )

        with self.assertNoException():
            page = template_context['page']
            [*page.object_list]  # NOQA

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_specific_relations_brick01(self):
        predicate = 'loves'
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', predicate),
            ('test-object_loved', 'is loved by'),
        )[0]
        rbi = RelationBrickItem.objects.create_if_needed(rtype)

        brick = SpecificRelationsBrick(relationbrick_item=rbi)
        self.assertEqual((Relation,), brick.dependencies)
        self.assertEqual((rtype.id,), brick.relation_type_deps)
        self.assertEqual(
            _('Relationship block: «{predicate}»').format(predicate=predicate),
            brick.verbose_name,
        )
        self.assertEqual((), brick.target_ctypes)

    def test_specific_relations_brick02(self):
        "ContentType constraints."
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_loves', 'loves', [FakeOrganisation, FakeContact]),
            ('test-object_loved', 'is loved by'),
        )[0]
        rbi = RelationBrickItem.objects.create_if_needed(rtype)

        brick = SpecificRelationsBrick(relationbrick_item=rbi)
        expected_models = {FakeOrganisation, FakeContact}

        with self.assertNumQueries(1):
            models = brick.target_ctypes

        self.assertIsInstance(models, tuple)
        self.assertSetEqual(expected_models, {*models})

        with self.assertNumQueries(0):
            self.assertSetEqual(expected_models, {*brick.target_ctypes})
