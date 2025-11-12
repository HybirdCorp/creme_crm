from copy import deepcopy
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory
from django.utils.translation import gettext as _

from creme.creme_core.constants import MODELBRICK_ID
from creme.creme_core.core.entity_cell import (
    EntityCellRegularField,
    EntityCellRelation,
)
from creme.creme_core.gui.bricks import (
    Brick,
    BrickManager,
    BrickRegistry,
    CustomBrick,
    EntityBrick,
    ForbiddenBrick,
    InstanceBrick,
    QuerysetBrick,
    SimpleBrick,
    SpecificRelationsBrick,
    VoidBrick,
)
from creme.creme_core.models import (
    CremeEntity,
    CustomBrickConfigItem,
    FakeContact,
    FakeImage,
    FakeOrganisation,
    InstanceBrickConfigItem,
    Relation,
    RelationBrickItem,
    RelationType,
)
from creme.creme_core.utils.content_type import entity_ctypes

from ..base import CremeTestCase
from ..fake_constants import FAKE_REL_OBJ_EMPLOYED_BY
from ..views.base import BrickTestCaseMixin


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
            id = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_2')

        brick_registry = BrickRegistry()
        self.assertListEqual([], [*brick_registry])

        with self.assertRaises(KeyError):
            brick_registry[FoobarBrick1.id]  # NOQA

        # 1 brick
        brick_registry.register(FoobarBrick1)
        self.assertListEqual([(FoobarBrick1.id, FoobarBrick1)], [*brick_registry])
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id])

        # 2 bricks
        brick_registry.register(FoobarBrick2)
        self.assertCountEqual(
            [
                (FoobarBrick1.id, FoobarBrick1),
                (FoobarBrick2.id, FoobarBrick2),
            ],
            [*brick_registry],
        )
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id])
        self.assertEqual(FoobarBrick2, brick_registry[FoobarBrick2.id])

    def test_register02(self):
        "2 classes at once."
        # class FoobarBrick(Brick):
        class FoobarBrick(SimpleBrick):
            verbose_name = 'Testing purpose'

            # def detailview_display(self, context):
            #     return self._render(self.get_template_context(context))

        class FoobarBrick1(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_2')

        brick_registry = BrickRegistry()
        brick_registry.register(FoobarBrick1, FoobarBrick2)
        self.assertEqual(FoobarBrick1, brick_registry[FoobarBrick1.id])
        self.assertEqual(FoobarBrick2, brick_registry[FoobarBrick2.id])

    def test_register03(self):
        "Duplicates."
        # class FoobarBrick1(Brick):
        class FoobarBrick1(SimpleBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = 'Testing purpose'

            # def detailview_display(self, context):
            #     return self._render(self.get_template_context(context))

        class FoobarBrick2(FoobarBrick1):
            pass

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError) as cm:
            brick_registry.register(FoobarBrick1, FoobarBrick2)

        self.assertEqual(
            f"Duplicated brick's ID: {FoobarBrick2.id}", str(cm.exception),
        )

    def test_register04(self):
        "Empty ID."
        # class FoobarBrick(Brick):
        class FoobarBrick(SimpleBrick):
            # id = Brick.generate_id('creme_core', 'foobar_brick')  # NOPE
            verbose_name = 'Testing purpose'

            # def detailview_display(self, context):
            #     return self._render(self.get_template_context(context))

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError) as cm:
            brick_registry.register(FoobarBrick)

        self.assertEqual(
            f"Brick class with empty ID: {FoobarBrick}", str(cm.exception),
        )

    def test_unregister(self):
        class FoobarBrick(Brick):
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick1(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_2')

        class FoobarBrick3(FoobarBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_3')

        brick_registry = BrickRegistry().register(FoobarBrick1, FoobarBrick2, FoobarBrick3)
        brick_registry.unregister(FoobarBrick1, FoobarBrick3)
        self.assertEqual(FoobarBrick2, brick_registry[FoobarBrick2.id])

        with self.assertRaises(KeyError):
            brick_registry[FoobarBrick1.id]  # NOQA
        with self.assertRaises(KeyError):
            brick_registry[FoobarBrick3.id]  # NOQA

        # ---
        class FoobarBrick4(FoobarBrick):
            pass

        with self.assertRaises(brick_registry.UnRegistrationError) as cm1:
            brick_registry.unregister(FoobarBrick4)

        self.assertEqual(
            f'Brick class with empty ID: {FoobarBrick4}',
            str(cm1.exception),
        )

        # ---
        with self.assertRaises(brick_registry.UnRegistrationError) as cm1:
            brick_registry.unregister(FoobarBrick2, FoobarBrick1)

        self.assertEqual(
            f'Brick class with invalid ID (already unregistered?): {FoobarBrick1}',
            str(cm1.exception)
        )

    def test_register_4_instance01(self):
        user = self.get_root_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        class _FoobarInstanceBrick(InstanceBrick):
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        class FoobarInstanceBrick1(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')

        class FoobarInstanceBrick2(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_2')

        class FoobarInstanceBrick3(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_3')

        self.assertEqual(
            'instance-creme_core-foobar_instance_brick_1',
            FoobarInstanceBrick1.id,
        )

        create_ibci = partial(InstanceBrickConfigItem.objects.create, entity=casca)
        ibci1 = create_ibci(brick_class_id=FoobarInstanceBrick1.id)
        ibci2 = create_ibci(brick_class_id=FoobarInstanceBrick2.id)
        brick_registry = BrickRegistry()

        ibrick1 = brick_registry.get_brick_4_instance(ibci1)
        self.assertIs(ibrick1.__class__, InstanceBrick)
        self.assertEqual('??', ibrick1.verbose_name)
        self.assertListEqual(
            [_('Unknown type of block (bad uninstall?)')],
            ibrick1.errors,
        )

        # 1 brick
        brick_registry.register_4_instance(FoobarInstanceBrick1)

        ibrick2 = brick_registry.get_brick_4_instance(ibci1)
        self.assertIsInstance(ibrick2, FoobarInstanceBrick1)
        self.assertEqual(ibci1.brick_id, ibrick2.id)
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
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        class FoobarInstanceBrick2(FoobarInstanceBrick1):
            verbose_name = 'Testing purpose #2'

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(
                FoobarInstanceBrick1, FoobarInstanceBrick2,
            )

        self.assertEqual(
            f"Duplicated brick's ID: {FoobarInstanceBrick2.id}",
            str(cm.exception),
        )

    def test_register_4_instance03(self):
        "Empty ID."
        class FoobarInstanceBrick(InstanceBrick):
            # id = InstanceBrickConfigItem.generate_base_id(...)
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(FoobarInstanceBrick)

        self.assertEqual(
            f"Brick class with empty ID: {FoobarInstanceBrick}",
            str(cm.exception),
        )

    def test_register_4_instance04(self):
        "Invalid base class."
        class FoobarInstanceBrick(Brick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.html_id}"><thead><tr></tr></thead></table>'

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError) as cm:
            brick_registry.register_4_instance(FoobarInstanceBrick)

        self.assertEqual(
            f"Brick class does not inherit InstanceBrick: {FoobarInstanceBrick}",
            str(cm.exception),
        )

    def test_get_brick_4_instance(self):
        "With 'entity' argument."
        user = self.get_root_user()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FoobarInstanceBrick(InstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')
            verbose_name = 'Testing purpose'
            dependencies = (FakeOrganisation, )

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=FoobarInstanceBrick.id,
        )
        brick_registry = BrickRegistry()

        brick_registry.register_4_instance(FoobarInstanceBrick)

        ibrick = brick_registry.get_brick_4_instance(ibci, entity=casca)
        self.assertIsInstance(ibrick, FoobarInstanceBrick)
        self.assertEqual((FakeOrganisation, FakeContact), ibrick.dependencies)

    def test_get_compatible_bricks01(self):
        user = self.get_root_user()
        casca = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')

        class FoobarBrick1(Brick):
            id = Brick.generate_id('creme_core', 'foobar_brick_1')
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return self._render(self.get_template_context(context))

        class FoobarBrick2(SimpleBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_2')
            verbose_name = 'Testing purpose'
            target_ctypes = (FakeContact, FakeOrganisation)

        class FoobarBrick3(SimpleBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_3')
            verbose_name = 'Testing purpose'
            target_ctypes = (FakeOrganisation,)  # Not 'Contact'

        class FoobarBrick4(SimpleBrick):
            id = Brick.generate_id('creme_core', 'foobar_brick_4')
            verbose_name = 'Testing purpose'
            configurable = False  # <------

        class FoobarBrick5(Brick):  # No detailview_display() method
            id = Brick.generate_id('creme_core', 'foobar_brick_5')
            verbose_name = 'Testing purpose'

            def home_display(self, context):
                return f'<table id="{self.html_id}"></table>'

        class FakeContactBrick(EntityBrick):
            verbose_name = 'Fake Contact block'

        class FakeOrganisationBrick(EntityBrick):
            verbose_name = 'Fake Organisation block'

        class _FoobarInstanceBrick(InstanceBrick):
            verbose_name = 'Testing purpose'

        class FoobarInstanceBrick1(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_1')

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        class FoobarInstanceBrick2(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_2')
            target_ctypes = (FakeContact, FakeOrganisation)  # <-- OK !!

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        class FoobarInstanceBrick3(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_3')
            target_ctypes = (FakeOrganisation, FakeImage)  # <-- KO !!

            def detailview_display(self, context):
                return (
                    f'<table id="{self.html_id}"><thead><tr>'
                    f'{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        class FoobarInstanceBrick4(_FoobarInstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'foobar_instance_brick_4')

            def home_display(self, context):  # <====== not detailview_display()
                return (
                    f'<table id="{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )

        create_ibci = partial(InstanceBrickConfigItem.objects.create, entity=casca)
        ibci1 = create_ibci(
            brick_class_id=FoobarInstanceBrick1.id,
            uuid='575f1df4-5bdc-4696-aa45-a2f49865580e',
        )
        ibci2 = create_ibci(
            brick_class_id=FoobarInstanceBrick2.id,
            uuid='675f1df4-5bdc-4696-aa45-a2f49865580e',  # After "ibci1.uuid" to facilitate test.
        )
        create_ibci(brick_class_id=FoobarInstanceBrick3.id)
        create_ibci(brick_class_id=FoobarInstanceBrick4.id)

        brick_registry = BrickRegistry()

        rtype1 = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loved', predicate='is loved by').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype1)

        create_cbci = CustomBrickConfigItem.objects.create
        cbci = create_cbci(
            # id='test-contacts01',
            name='General (contact)',
            content_type=FakeContact,
            cells=[EntityCellRegularField.build(FakeContact, 'last_name')],
        )
        create_cbci(
            name='General (orga)',
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
            FakeOrganisation, FakeOrganisationBrick,
        ).register_4_instance(
            FoobarInstanceBrick1,
            FoobarInstanceBrick2,
            FoobarInstanceBrick3,
            FoobarInstanceBrick4,
        )

        bricks = sorted(brick_registry.get_compatible_bricks(FakeContact), key=lambda b: b.id)
        self.assertEqual(7, len(bricks))

        bricks_by_id = {brick.id: brick for brick in bricks}
        self.assertIsInstance(bricks_by_id.get(FoobarBrick1.id), FoobarBrick1)
        self.assertIsInstance(bricks_by_id.get(FoobarBrick2.id), FoobarBrick2)

        self.assertIsInstance(bricks_by_id.get(cbci.brick_id), CustomBrick)
        self.assertIsInstance(bricks_by_id.get(ibci1.brick_id), FoobarInstanceBrick1)
        self.assertIsInstance(bricks_by_id.get(ibci2.brick_id), FoobarInstanceBrick2)

        model_brick = bricks_by_id['model']
        self.assertIsInstance(model_brick, FakeContactBrick)
        self.assertEqual((FakeContact,), model_brick.dependencies)

        rel_brick = bricks_by_id[rbi.brick_id]
        self.assertIsInstance(rel_brick, SpecificRelationsBrick)
        self.assertEqual((rtype1.id,), rel_brick.relation_type_deps)

    def test_get_compatible_bricks02(self):
        "SpecificRelationsBrick."
        rtype1 = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loved', predicate='is loved by').get_or_create()[0]
        rtype2 = RelationType.objects.builder(
            id='test-subject_hires', predicate='hires', models=[FakeOrganisation],
        ).symmetric(id='test-object_hires', predicate='is hired by').get_or_create()[0]

        create_rbi = RelationBrickItem.objects.create
        create_rbi(relation_type=rtype2)
        create_rbi(relation_type=rtype1)

        brick_registry = BrickRegistry()

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
        brick_registry = BrickRegistry()

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
        brick_registry = BrickRegistry()
        brick = self.get_alone_element(brick_registry.get_compatible_hat_bricks(FakeContact))
        self.assertIsInstance(brick, SimpleBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual('creme_core/bricks/generic/hat-bar.html', brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id)

    def test_get_compatible_hat_bricks02(self):
        "Register main class."
        template = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick(SimpleBrick):
            template_name = template

        brick_registry = BrickRegistry()
        brick_registry.register_hat(FakeContact, main_brick_cls=FakeContactHatBrick)
        brick = self.get_alone_element(
            brick_registry.get_compatible_hat_bricks(FakeContact)
        )
        self.assertIsInstance(brick, FakeContactHatBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual(template, brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id)

    def test_get_compatible_hat_bricks02_error(self):
        brick_registry = BrickRegistry()

        class FakeContactHatBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'contact_hat')
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        with self.assertRaises(BrickRegistry.RegistrationError):
            brick_registry.register_hat(FakeContact, main_brick_cls=FakeContactHatBrick)

    def test_get_compatible_hat_bricks03(self):
        "Secondary classes."
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick01(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_1')

        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_2')

        brick_registry = BrickRegistry()
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

        # id is None -----------
        class FakeContactHatBrick01(BaseFakeContactHatBrick):
            pass

        brick_registry = BrickRegistry()

        with self.assertRaises(BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick01],
            )

        # Bad id type ------------
        class FakeContactHatBrick02(BaseFakeContactHatBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_get_compatible_hat_bricks03_error')

        with self.assertRaises(BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick02],
            )

        # Duplicated id -------------
        class FakeContactHatBrick03(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id(
                'creme_core', 'test_get_compatible_hat_bricks03_error',
            )

        class FakeContactHatBrick04(BaseFakeContactHatBrick):
            id = FakeContactHatBrick03.id  # <===

        with self.assertNoException():
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick03],
            )

        with self.assertRaises(BrickRegistry.RegistrationError):
            brick_registry.register_hat(
                FakeContact, secondary_brick_classes=[FakeContactHatBrick04],
            )

    def test_unregister_hat_bricks01(self):
        "Main class."
        class FakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        brick_registry = BrickRegistry().register_hat(
            FakeContact, main_brick_cls=FakeContactHatBrick,
        )

        brick_registry.unregister_hat(FakeContact, main_brick=True)
        brick = self.get_alone_element(brick_registry.get_compatible_hat_bricks(FakeContact))
        self.assertIsInstance(brick, SimpleBrick)
        self.assertEqual((FakeContact,), brick.dependencies)
        self.assertEqual('creme_core/bricks/generic/hat-bar.html', brick.template_name)
        self.assertEqual(SimpleBrick.GENERIC_HAT_BRICK_ID, brick.id)

        # ---
        with self.assertRaises(brick_registry.UnRegistrationError) as cm:
            brick_registry.unregister_hat(FakeContact, main_brick=True)
        self.assertEqual(
            "Invalid main hat brick for model "
            "<class 'creme.creme_core.tests.fake_models.FakeContact'> "
            "(already unregistered?)",
            str(cm.exception),
        )

    def test_unregister_hat_bricks02(self):
        "Secondary classes."
        class BaseFakeContactHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactHatBrick1(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_1')

        class FakeContactHatBrick2(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_2')

        class FakeContactHatBrick3(BaseFakeContactHatBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'test_get_compatible_hat_bricks03_3')

        brick_registry = BrickRegistry().register_hat(
            FakeContact,
            secondary_brick_classes=(
                FakeContactHatBrick1, FakeContactHatBrick2, FakeContactHatBrick3,
            ),
        )

        brick_registry.unregister_hat(
            FakeContact,
            secondary_brick_classes=(FakeContactHatBrick1, FakeContactHatBrick3),
        )
        self.assertCountEqual(
            [SimpleBrick, FakeContactHatBrick2],
            [brick.__class__ for brick in brick_registry.get_compatible_hat_bricks(FakeContact)],
        )

        # ---
        self.maxDiff = None
        with self.assertRaises(brick_registry.UnRegistrationError) as cm:
            brick_registry.unregister_hat(
                FakeContact,
                secondary_brick_classes=(FakeContactHatBrick2, FakeContactHatBrick1),
            )

        self.assertEqual(
            '''Invalid hat brick for model '''
            '''<class 'creme.creme_core.tests.fake_models.FakeContact'> '''
            '''with id="hat-creme_core-test_get_compatible_hat_bricks03_1" '''
            '''(already unregistered?)''',
            str(cm.exception),
        )

    def test_get_compatible_home_bricks(self):
        class FoobarBrick1(Brick):
            id = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_1',
            )
            verbose_name = 'Testing purpose'

            # NB: only home_display() method
            # def detailview_display(self, context): [...]
            def home_display(self, context):
                return f'<table id="{self.html_id}"></table>'

        class FoobarBrick2(Brick):
            id = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_2',
            )
            verbose_name = 'Testing purpose'
            configurable = False  # <----

            def home_display(self, context):
                return f'<table id="{self.html_id}"></table>'

        class FoobarBrick3(Brick):
            id = Brick.generate_id(
                'creme_core', 'BrickRegistryTestCase__test_get_compatible_home_bricks_3',
            )
            verbose_name = 'Testing purpose'

            def detailview_display(self, context):
                return f'<table id="{self.html_id}"></table>'
            # def home_display(self, context): [...]

        brick_registry = BrickRegistry()
        brick_registry.register(FoobarBrick1, FoobarBrick2, FoobarBrick3)

        brick = self.get_alone_element(brick_registry.get_compatible_home_bricks())
        self.assertIsInstance(brick, FoobarBrick1)

    def test_get_bricks(self):
        class QuuxBrick1(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_1')
            verbose_name = 'Testing purpose #1'

        class QuuxBrick2(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_2')
            verbose_name = 'Testing purpose #2'

        class QuuxBrick3(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_3')
            verbose_name = 'Testing purpose #3'

        brick_registry = BrickRegistry()
        brick_registry.register(QuuxBrick1, QuuxBrick2, QuuxBrick3)

        def assertBricks(brick_classes, bricks):
            self.assertIsList(bricks, length=len(brick_classes))

            for brick_cls, brick in zip(brick_classes, bricks):
                self.assertIsInstance(brick, brick_cls)

        assertBricks(
            [QuuxBrick1, QuuxBrick2],
            [*brick_registry.get_bricks([QuuxBrick1.id, QuuxBrick2.id])],
        )

        # Not registered -------------
        brick = self.get_alone_element(
            brick_registry.get_bricks([
                SimpleBrick.generate_id('creme_core', 'BrickRegistryTestCase__test_get_bricks_4'),
            ])
        )
        self.assertIsInstance(brick, Brick)

    def test_get_bricks__model(self):
        "Model brick."
        user = self.get_root_user()

        class ContactBrick(EntityBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = BrickRegistry()
        brick_registry.register_4_model(FakeContact, ContactBrick)

        # No entity
        self.assertFalse([*brick_registry.get_bricks([MODELBRICK_ID])])

        # No registered model brick
        orga = FakeOrganisation.objects.create(user=user, name='Hawk')
        orga_brick = next(brick_registry.get_bricks([MODELBRICK_ID], entity=orga))
        self.assertIsInstance(orga_brick, EntityBrick)

        # Registered model brick
        contact = FakeContact.objects.create(user=user, first_name='Casca', last_name='Mylove')
        contact_brick = next(brick_registry.get_bricks([MODELBRICK_ID], entity=contact))
        self.assertIsInstance(contact_brick, ContactBrick)

    def test_get_bricks__relation(self):
        "Specific relation bricks."
        class QuuxBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_get_bricks__relation')
            verbose_name = 'Testing purpose #1'

        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
        ).symmetric(id='test-object_loved', predicate='is loved by').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype)

        brick_registry = BrickRegistry()
        brick_registry.register(QuuxBrick)

        # No entity
        self.assertFalse([*brick_registry.get_bricks([rbi.brick_id])])

        # ---
        bricks = [*brick_registry.get_bricks(
            brick_ids=[QuuxBrick.id, rbi.brick_id], entity=FakeContact(),
        )]
        self.assertEqual(2, len(bricks))

        self.assertIsInstance(bricks[0], QuuxBrick)

        rel_brick = bricks[1]
        self.assertIsInstance(rel_brick, SpecificRelationsBrick)
        self.assertEqual((rtype.id,), rel_brick.relation_type_deps)

    def test_get_bricks__custom(self):
        "Custom bricks."
        class QuuxBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_get_bricks__custom')
            verbose_name = 'Testing purpose #1'

        cbci = CustomBrickConfigItem.objects.create(
            # id='tests-organisations01',
            name='General', content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        brick_registry = BrickRegistry()
        brick_registry.register(QuuxBrick)

        # No entity
        self.assertFalse([*brick_registry.get_bricks([cbci.brick_id])])

        # Entity with bad type
        self.assertFalse([*brick_registry.get_bricks(
            brick_ids=[cbci.brick_id], entity=FakeContact(),
        )])

        # ---
        bricks = [*brick_registry.get_bricks(
            brick_ids=[QuuxBrick.id, cbci.brick_id], entity=FakeOrganisation(),
        )]
        self.assertEqual(2, len(bricks))

        self.assertIsInstance(bricks[0], QuuxBrick)

        custom_brick = bricks[1]
        self.assertIsInstance(custom_brick, CustomBrick)
        self.assertEqual(cbci.brick_id,      custom_brick.id)
        self.assertEqual([FakeOrganisation], custom_brick.dependencies)
        self.assertEqual(cbci.name,          custom_brick.verbose_name)

    def test_get_bricks__hat(self):
        "Hat brick."
        user = self.get_root_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        class FakeContactBasicHatBrick(SimpleBrick):
            template_name = 'creme_core/bricks/fake_contact_hat.html'  # (does not exists)

        class FakeContactCardHatBrick(SimpleBrick):
            id = SimpleBrick._generate_hat_id('creme_core', 'fake_contact_card')
            template_name = 'creme_core/bricks/fake_contact_hat_card.html'  # (does not exists)

        brick_registry = BrickRegistry()
        brick_registry.register_hat(
            FakeContact,
            main_brick_cls=FakeContactBasicHatBrick,
            secondary_brick_classes=[FakeContactCardHatBrick],
        )

        brick_id = SimpleBrick.GENERIC_HAT_BRICK_ID
        self.assertFalse([*brick_registry.get_bricks([brick_id])])

        # ----
        brick1 = self.get_alone_element(brick_registry.get_bricks([brick_id], entity=casca))
        self.assertIsInstance(brick1, FakeContactBasicHatBrick)

        # ----
        brick2 = self.get_alone_element(
            brick_registry.get_bricks([FakeContactCardHatBrick.id], entity=casca)
        )
        self.assertIsInstance(brick2, FakeContactCardHatBrick)

        # ----
        brick3 = self.get_alone_element(
            brick_registry.get_bricks(
                [SimpleBrick._generate_hat_id('creme_core', 'invalid')],
                entity=casca,
            )
        )
        self.assertIsInstance(brick3, FakeContactBasicHatBrick)

    def test_get_bricks__permissions(self):
        root = self.get_root_user()
        user = self.create_user(
            role=self.create_role(name='Basic', allowed_apps=['creme_core']),
        )

        class AllowedBrick1(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_1')
            verbose_name = 'Always allowed'

        class AllowedBrick2(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_2')
            verbose_name = 'Allowed'
            permissions = 'creme_core'

        class NotAllowedBrick1(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_3')
            verbose_name = 'Forbidden block #1'
            permissions = 'persons'

        class NotAllowedBrick2(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_4')
            verbose_name = 'Forbidden block #2'
            permissions = ['persons']

        all_bricks = [AllowedBrick1, AllowedBrick2, NotAllowedBrick1, NotAllowedBrick2]
        brick_registry = BrickRegistry().register(*all_bricks)

        def assertBricks(brick_classes, bricks):
            self.assertIsList(bricks, length=len(brick_classes))

            for brick_cls, brick in zip(brick_classes, bricks):
                self.assertIsInstance(brick, brick_cls)

        all_brick_ids = [b.id for b in all_bricks]
        assertBricks(all_bricks, [*brick_registry.get_bricks(all_brick_ids)])
        assertBricks(all_bricks, [*brick_registry.get_bricks(brick_ids=all_brick_ids, user=root)])

        user_bricks = [*brick_registry.get_bricks(brick_ids=all_brick_ids, user=user)]
        self.assertEqual(len(all_brick_ids), len(user_bricks))

        self.assertIsInstance(user_bricks[0], AllowedBrick1)
        self.assertIsInstance(user_bricks[1], AllowedBrick2)

        brick3 = user_bricks[2]
        self.assertIsInstance(brick3, ForbiddenBrick)
        self.assertEqual(NotAllowedBrick1.id,           brick3.id)
        self.assertEqual(NotAllowedBrick1.verbose_name, brick3.verbose_name)
        self.assertEqual(
            _('You are not allowed to access to the app: {}').format(
                _('Accounts and Contacts')
            ),
            brick3.error,
        )

        brick4 = user_bricks[3]
        self.assertIsInstance(brick4, ForbiddenBrick)
        self.assertEqual(NotAllowedBrick2.id,           brick4.id)
        self.assertEqual(NotAllowedBrick2.verbose_name, brick4.verbose_name)

    def test_brick_4_model01(self):
        brick_registry = BrickRegistry()

        brick = brick_registry.get_brick_4_object(FakeOrganisation)
        self.assertEqual(MODELBRICK_ID, brick.id)
        self.assertEqual((FakeOrganisation,), brick.dependencies)

    def test_brick_4_model02(self):
        brick_registry = BrickRegistry()

        user = self.get_root_user()
        casca = FakeContact.objects.create(
            user=user, first_name='Casca', last_name='Mylove',
        )

        brick = brick_registry.get_brick_4_object(casca)
        self.assertEqual(brick.__class__, EntityBrick)
        self.assertEqual(MODELBRICK_ID, brick.id)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_model03(self):
        class ContactBrick(EntityBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = BrickRegistry()
        brick_registry.register_4_model(FakeContact, ContactBrick)

        brick = brick_registry.get_brick_4_object(FakeContact)
        self.assertIsInstance(brick, ContactBrick)
        self.assertEqual(MODELBRICK_ID, brick.id)
        self.assertEqual((FakeContact,), brick.dependencies)

    def test_brick_4_model04(self):
        "Custom brick does not inherit EntityBrick."
        class ContactBrick(SimpleBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = BrickRegistry()
        with self.assertRaises(AssertionError):
            brick_registry.register_4_model(FakeContact, ContactBrick)

    def test_unregister_4_model(self):
        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='Casca', last_name='Mylove',
        )

        class ContactBrick(EntityBrick):
            template_name = 'persons/bricks/my_contact.html'

        brick_registry = BrickRegistry().register_4_model(FakeContact, ContactBrick)

        brick_registry.unregister_4_model(FakeContact)
        brick = next(brick_registry.get_bricks([MODELBRICK_ID], entity=contact))
        self.assertIsInstance(brick, EntityBrick)
        self.assertFalse(isinstance(brick, ContactBrick))

        # ---
        with self.assertRaises(brick_registry.UnRegistrationError) as cm:
            brick_registry.unregister_4_model(FakeContact)

        self.assertEqual(
            "Invalid Brick for model <class 'creme.creme_core.tests.fake_models.FakeContact'> "
            "(already unregistered?)",
            str(cm.exception),
        )

    def test_brick_4_instance01(self):
        user = self.get_root_user()

        create_contact = FakeContact.objects.create
        casca = create_contact(user=user, first_name='Casca', last_name='Mylove')

        class ContactBrick(InstanceBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_block')
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist.html'

            def detailview_display(self, context):
                return (
                    f'<table id="brick-{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )  # useless :)

        ibci = InstanceBrickConfigItem.objects.create(
            entity=casca,
            brick_class_id=ContactBrick.id,
        )

        brick_registry = BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)

        brick_id = ibci.brick_id
        brick1 = self.get_alone_element(brick_registry.get_bricks([brick_id]))
        self.assertIsInstance(brick1, ContactBrick)
        self.assertEqual(ibci, brick1.config_item)
        self.assertEqual(brick_id, brick1.id)
        self.assertEqual((FakeOrganisation,), brick1.dependencies)

        # ----------------------------------------------------------------------
        # In detail-views of an entity we give it in order to compute dependencies correctly.
        judo = create_contact(user=user, first_name='Judo',  last_name='Doe')
        brick2 = next(brick_registry.get_bricks([brick_id], entity=judo))
        self.assertEqual((FakeOrganisation, FakeContact), brick2.dependencies)

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
        brick3 = self.get_alone_element(brick_registry.get_bricks([bad_ibci.brick_id]))
        self.assertIsInstance(brick3, Brick)

    def test_brick_4_instance02(self):
        class BaseBrick(InstanceBrick):
            # Used twice !!
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'base_brick')

            template_name = 'persons/templatetags/block_thatdoesnotexist.html'

            def detailview_display(self, context):
                return (
                    f'<table id="brick-{self.html_id}">'
                    f'<thead><tr>{self.config_item.entity}</tr></thead>'
                    f'</table>'
                )  # Useless :)

        class ContactBrick(BaseBrick):
            pass

        class OrgaBrick(BaseBrick):
            pass

        brick_registry = BrickRegistry()
        brick_registry.register_4_instance(ContactBrick)
        self.assertRaises(
            BrickRegistry.RegistrationError,
            brick_registry.register_4_instance,
            OrgaBrick,
        )

    def test_deep_copy(self):
        class FoobarBrick1(Brick):
            id = Brick.generate_id('creme_core', 'foobar_brick_1')

        class FoobarBrick2(Brick):
            id = Brick.generate_id('creme_core', 'foobar_brick_2')

        class FoobarBrick3(Brick):
            id = Brick.generate_id('creme_core', 'foobar_brick_3')

        brick_registry = BrickRegistry().register(
            FoobarBrick1, FoobarBrick2,
        ).register_invalid_models(FakeContact)
        copied = deepcopy(brick_registry)

        expected = [
            (FoobarBrick1.id, FoobarBrick1),
            (FoobarBrick2.id, FoobarBrick2),
        ]
        self.assertListEqual(expected, [*brick_registry])
        self.assertListEqual(expected, [*copied])

        self.assertTrue(brick_registry.is_model_invalid(FakeContact))
        self.assertFalse(brick_registry.is_model_invalid(FakeOrganisation))
        self.assertTrue(copied.is_model_invalid(FakeContact))
        self.assertFalse(copied.is_model_invalid(FakeOrganisation))

        # ---
        brick_registry.unregister(FoobarBrick2)
        copied.register(FoobarBrick3)

        self.assertListEqual([(FoobarBrick1.id, FoobarBrick1),], [*brick_registry])
        self.assertListEqual(
            [
                *expected,
                (FoobarBrick3.id, FoobarBrick3),
            ],
            [*copied],
        )

        # ---
        copied.register_invalid_models(FakeOrganisation)
        self.assertTrue(copied.is_model_invalid(FakeContact))
        self.assertTrue(copied.is_model_invalid(FakeOrganisation))
        self.assertFalse(brick_registry.is_model_invalid(FakeOrganisation))

    def test_deep_copy__hat(self):
        class FakeContactHatBrick1(Brick):
            template_name = 'creme_core/bricks/fake_contact_hat1.html'

        class OtherFakeContactHatBrick1(Brick):
            id = Brick._generate_hat_id('creme_core', 'other_hat_brick1')
            template_name = 'creme_core/bricks/other_fake_contact_hat1.html'

        class OtherFakeContactHatBrick2(Brick):
            id = Brick._generate_hat_id('creme_core', 'other_hat_brick2')
            template_name = 'creme_core/bricks/other_fake_contact_hat2.html'

        class OtherFakeContactHatBrick3(Brick):
            id = Brick._generate_hat_id('creme_core', 'other_hat_brick3')
            template_name = 'creme_core/bricks/other_fake_contact_hat3.html'

        brick_registry = BrickRegistry().register_hat(
            FakeContact,
            main_brick_cls=FakeContactHatBrick1,
            secondary_brick_classes=(OtherFakeContactHatBrick1, OtherFakeContactHatBrick2),
        )
        copied = deepcopy(brick_registry)

        expected = [
            FakeContactHatBrick1.template_name,
            OtherFakeContactHatBrick1.template_name,
            OtherFakeContactHatBrick2.template_name,
        ]

        def templates(registry):
            return [b.template_name for b in registry.get_compatible_hat_bricks(FakeContact)]

        self.assertListEqual(expected, templates(brick_registry))
        self.assertListEqual(expected, templates(copied))

        # ---
        brick_registry.unregister_hat(
            FakeContact, secondary_brick_classes=[OtherFakeContactHatBrick1],
        )
        copied.register_hat(
            FakeContact, secondary_brick_classes=[OtherFakeContactHatBrick3],
        )
        self.assertListEqual(
            [
                FakeContactHatBrick1.template_name,
                # OtherFakeContactHatBrick1.template_name,
                OtherFakeContactHatBrick2.template_name,
            ],
            templates(brick_registry),
        )
        self.assertListEqual(
            [*expected, OtherFakeContactHatBrick3.template_name],
            templates(copied),
        )

    def test_deep_copy__model(self):
        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Hawk')

        class OrgaBrick1(EntityBrick):
            template_name = 'persons/bricks/my_orga1.html'

        class OrgaBrick2(EntityBrick):
            template_name = 'persons/bricks/my_orga2.html'

        brick_registry = BrickRegistry().register_4_model(
            model=FakeOrganisation, brick_cls=OrgaBrick1,
        )
        copied = deepcopy(brick_registry)

        def get_brick(registry):
            return next(registry.get_bricks([MODELBRICK_ID], entity=orga))

        self.assertIsInstance(get_brick(brick_registry), OrgaBrick1)
        self.assertIsInstance(get_brick(copied),         OrgaBrick1)

        # ---
        brick_registry.unregister_4_model(FakeOrganisation)
        copied.register_4_model(FakeOrganisation, OrgaBrick2)
        self.assertNotIn(
            get_brick(brick_registry).__class__,
            (OrgaBrick1, OrgaBrick2),
        )
        self.assertIsInstance(get_brick(copied), OrgaBrick2)

    def test_deep_copy__instance(self):
        orga = FakeOrganisation.objects.create(user=self.get_root_user(), name='Hawk')

        class BaseOrgaBrick(InstanceBrick):
            dependencies = (FakeOrganisation,)
            template_name = 'persons/bricks/itdoesnotexist1.html'

        class OrgaBrick1(BaseOrgaBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'deep_copy1')

        brick_registry = BrickRegistry().register_4_instance(OrgaBrick1)
        copied = deepcopy(brick_registry)

        ibci1 = InstanceBrickConfigItem(
            entity=orga, brick_class_id=OrgaBrick1.id,
        )

        ibrick11 = brick_registry.get_brick_4_instance(ibci1)
        self.assertIsInstance(ibrick11, OrgaBrick1)
        self.assertIsNone(ibrick11.errors)

        ibrick12 = copied.get_brick_4_instance(ibci1)
        self.assertIsInstance(ibrick12, OrgaBrick1)
        self.assertIsNone(ibrick12.errors)

        # ---
        class OrgaBrick2(BaseOrgaBrick):
            id = InstanceBrickConfigItem.generate_base_id('creme_core', 'deep_copy2')

        brick_registry.register_4_instance(OrgaBrick2)

        ibci2 = InstanceBrickConfigItem(
            entity=orga, brick_class_id=OrgaBrick2.id,
        )

        ibrick21 = brick_registry.get_brick_4_instance(ibci2)
        self.assertIsInstance(ibrick21, OrgaBrick2)
        self.assertIsNone(ibrick21.errors)

        self.assertListEqual(
            [_('Unknown type of block (bad uninstall?)')],
            copied.get_brick_4_instance(ibci2).errors,
        )

    # TODO different keys


class BricksManagerTestCase(CremeTestCase):
    def test_manage01(self):
        class TestBlock(SimpleBrick):
            verbose_name = 'Testing purpose'

        class FoobarBrick1(TestBlock):
            id = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_1')

        class FoobarBrick2(TestBlock):
            id = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_2')
            dependencies = (FakeContact,)

        class FoobarBrick3(TestBlock):
            id = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_3')
            dependencies = (FakeOrganisation,)

        class FoobarBrick4(TestBlock):
            id = TestBlock.generate_id('creme_core', 'BricksManagerTestCase__manage01_4')
            dependencies = (FakeContact, FakeOrganisation)

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()

        mngr = BrickManager()
        self.assertFalse(mngr.brick_is_registered(brick1))
        self.assertHasAttr(BrickManager, 'Error')

        name1 = 'gname1'
        mngr.add_group(name1, brick1, brick2, brick3)
        self.assertTrue(mngr.brick_is_registered(brick1))
        self.assertFalse(mngr.brick_is_registered(brick4))
        self.assertCountEqual(
            [brick1, brick2, brick3],
            [*mngr.bricks],
        )
        self.assertRaises(BrickManager.Error, mngr.add_group, name1, brick4)  # Same name

    def test_manage02(self):
        class TestBrick(SimpleBrick):
            verbose_name = 'Testing purpose'

        class FoobarBrick1(TestBrick):
            id = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_1')

        class FoobarBrick2(TestBrick):
            id = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_2')
            dependencies = (FakeContact,)

        class FoobarBrick3(TestBrick):
            id = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_3')
            dependencies = (FakeOrganisation,)

        class FoobarBrick4(TestBrick):
            id = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage02_4')
            dependencies = (FakeContact, FakeOrganisation)

        brick1 = FoobarBrick1()
        brick2 = FoobarBrick2()
        brick3 = FoobarBrick3()
        brick4 = FoobarBrick4()

        mngr = BrickManager()
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

    def test_manage03(self):
        "Relation bricks."

        class TestBrick(SimpleBrick):
            verbose_name = 'Testing purpose'

        class FoobarBrick3(TestBrick):
            id_ = TestBrick.generate_id('creme_core', 'BricksManagerTestCase__manage03_3')
            dependencies = (Relation,)

        self.assertEqual((), FoobarBrick3.relation_type_deps)

        class FoobarBrick6(SpecificRelationsBrick):
            verbose_name = 'Testing purpose'

        self.assertEqual((Relation,), FoobarBrick6.dependencies)

    def test_get(self):
        mngr = BrickManager()

        with self.assertNoException():
            fake_context = {mngr.var_name: mngr}

        self.assertIs(mngr, BrickManager.get(fake_context))

    # TODO: test def get_state(self, brick_id, user)


class BrickTestCase(BrickTestCaseMixin, CremeTestCase):
    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    class OrderedBrick(QuerysetBrick):
        id = QuerysetBrick.generate_id('creme_core', 'BrickTestCase-test_queryset_brick_order')
        dependencies = (FakeContact,)
        page_size = 10
        order_by = 'last_name'

    def _assertPageOrderedLike(self, page, ordered_instances):
        ids = {c.id for c in ordered_instances}
        self.assertListEqual(
            ordered_instances,
            [c for c in page.object_list if c.id in ids],
        )

    def test_html_id(self):
        class MyBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_html_id')

        brick = MyBrick()
        self.assertEqual('regular-creme_core-test_html_id',       brick.id)
        self.assertEqual('brick-regular-creme_core-test_html_id', brick.html_id)

    # def test_has_perms(self):
    def test_check_permissions(self):
        root = self.get_root_user()
        user = self.create_user(
            role=self.create_role(name='Basic', allowed_apps=['creme_core', 'documents']),
        )
        self.assertTrue(user.has_perm('creme_core'))
        self.assertTrue(user.has_perms(['documents', 'creme_core']))
        self.assertFalse(user.has_perm('persons'))
        self.assertFalse(user.has_perms(['persons', 'documents']))

        class AlwaysAllowedBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_1')
            verbose_name = 'Always allowed'

        brick1 = AlwaysAllowedBrick()
        self.assertEqual('', brick1.permissions)
        # self.assertIs(brick1.has_perms(root), True)
        # self.assertIs(brick1.has_perms(user), True)
        with self.assertNoException():
            brick1.check_permissions(root)
            brick1.check_permissions(user)

        # ---
        class SimpleAllowedBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_2')
            verbose_name = 'Allowed (simple)'
            permissions = 'creme_core'

        brick2 = SimpleAllowedBrick()
        # self.assertIs(brick2.has_perms(root), True)
        # self.assertIs(brick2.has_perms(user), True)
        with self.assertNoException():
            brick2.check_permissions(root)
            brick2.check_permissions(user)

        # ---
        class MultiAllowedBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_3')
            verbose_name = 'Allowed (multi)'
            permissions = ['creme_core', 'documents']

        brick3 = MultiAllowedBrick()
        # self.assertIs(brick3.has_perms(root), True)
        # self.assertIs(brick3.has_perms(user), True)
        with self.assertNoException():
            brick3.check_permissions(root)
            brick3.check_permissions(user)

        # ---
        class SimpleForbiddenBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_4')
            verbose_name = 'Forbidden (simple)'
            permissions = 'persons'

        brick4 = SimpleForbiddenBrick()
        # self.assertIs(brick4.has_perms(root), True)
        # self.assertIs(brick4.has_perms(user), False)
        with self.assertNoException():
            brick4.check_permissions(root)

        with self.assertRaises(PermissionDenied):
            brick4.check_permissions(user)

        # ---
        class MultiForbiddenBrick(SimpleBrick):
            id = SimpleBrick.generate_id('creme_core', 'test_perms_5')
            verbose_name = 'Forbidden (multi)'
            permissions = ['documents', 'persons']

        brick5 = MultiForbiddenBrick()
        # self.assertIs(brick5.has_perms(root), True)
        # self.assertIs(brick5.has_perms(user), False)
        with self.assertNoException():
            brick5.check_permissions(root)

        with self.assertRaises(PermissionDenied):
            brick5.check_permissions(user)

    def test_relation_type_deps(self):
        class OKBrick1(Brick):
            dependencies = (FakeOrganisation, Relation)
            # relation_type_deps = ()

        class OKBrick2(Brick):
            dependencies = (FakeOrganisation, Relation)
            relation_type_deps = (FAKE_REL_OBJ_EMPLOYED_BY,)

        with self.assertNoException():
            OKBrick1()
            OKBrick2()

        class KOBrick(Brick):
            dependencies = (FakeOrganisation,)  # Relation
            relation_type_deps = (FAKE_REL_OBJ_EMPLOYED_BY,)

        with self.assertRaises(ValueError) as cm:
            KOBrick()

        self.assertEqual(
            'The Brick <KOBrick> gets RelationTypes dependencies but the model '
            'Relation is not a dependence.',
            str(cm.exception),
        )

    def test_void_brick(self):
        user = self.get_root_user()
        brick = VoidBrick(id=Brick.generate_id('creme_core', 'test_void'))

        render = brick.detailview_display(self.build_context(user=user))
        self.get_brick_node(self.get_html_tree(render), brick=brick)

    def test_custom_brick01(self):
        cbci = CustomBrickConfigItem.objects.create(
            name='General', content_type=FakeOrganisation,
            cells=[EntityCellRegularField.build(FakeOrganisation, 'name')],
        )

        cbrick = CustomBrick(cbci.brick_id, cbci)
        self.assertEqual([FakeOrganisation], cbrick.dependencies)
        self.assertFalse(cbrick.relation_type_deps)

    def test_custom_brick02(self):
        "Relation + dependencies."
        rtype = RelationType.objects.builder(
            id='test-subject_employs', predicate='employs',
        ).symmetric(id='test-object_employs', predicate='is employed by').get_or_create()[0]

        cbci = CustomBrickConfigItem.objects.create(
            name='General', content_type=FakeOrganisation,
            cells=[
                EntityCellRegularField.build(FakeOrganisation, 'name'),
                EntityCellRelation(model=FakeOrganisation, rtype=rtype),
            ],
        )

        cbrick = CustomBrick(cbci.brick_id, cbci)
        self.assertEqual([FakeOrganisation, Relation], cbrick.dependencies)
        self.assertEqual([rtype.id], cbrick.relation_type_deps)

    def test_paginated_brick01(self):
        user = self.get_root_user()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz',  last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        template_context = brick.get_template_context(
            self.build_context(user=user),
            FakeContact.objects.filter(description=description),
        )

        with self.assertNoException():
            page = template_context['page']

        self.assertEqual(2, page.paginator.per_page)
        self.assertEqual(2, page.paginator.num_pages)
        self.assertEqual(1, page.number)

    def test_paginated_brick02(self):
        "Page in request."
        user = self.get_root_user()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz',  last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_page=2'),
            FakeContact.objects.filter(description=description),
        )

        page = template_context['page']
        self.assertEqual(2, page.number)

    def test_paginated_brick03(self):
        "Page in request: invalid number (not int)."
        user = self.get_root_user()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz', last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_page=NaN'),
            FakeContact.objects.filter(description=description),
        )

        page = template_context['page']
        self.assertEqual(1, page.number)

    def test_paginated_brick04(self):
        "Page in request: number too great."
        user = self.get_root_user()

        description = 'Dungeon explorer'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        create_contact(first_name='Aiz', last_name='Wallenstein')
        create_contact(first_name='Bell', last_name='Cranel')
        create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        brick.page_size = 2
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_page=3'),
            FakeContact.objects.filter(description=description),
        )

        page = template_context['page']
        self.assertEqual(2, page.number)

    def test_queryset_brick_order01(self):
        "No order in request."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        template_context = brick.get_template_context(
            self.build_context(user=user),
            FakeContact.objects.all(),
        )

        with self.assertNoException():
            page = template_context['page']
            model = page.object_list.model

        self.assertEqual(FakeContact, model)
        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order02(self):
        "No order in request: invalid field in Brick class."
        user = self.get_root_user()

        class ProblematicBrick(QuerysetBrick):
            id = QuerysetBrick.generate_id(
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
            self.build_context(user=user),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [cranel, crozzo, wallen])

    def test_queryset_brick_order03(self):
        "Order in request: valid field."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        aiz  = create_contact(first_name='Aiz',      last_name='Wallenstein')
        lili = create_contact(first_name='Liliruca', last_name='Arde')
        bell = create_contact(first_name='Bell',     last_name='Cranel')
        welf = create_contact(first_name='Welf',     last_name='Crozzo')

        brick = self.OrderedBrick()

        # ASC
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_order=first_name'),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [aiz, bell, lili, welf])

        # DESC
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_order=-first_name'),
            FakeContact.objects.all(),
        )
        self._assertPageOrderedLike(template_context['page'], [welf, lili, bell, aiz])

    def test_queryset_brick_order04(self):
        "Order in request: invalid field."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_order=unknown'),
            FakeContact.objects.all()
        )

        with self.assertNoException():
            page = template_context['page']
            [*page.object_list]  # NOQA

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_queryset_brick_order05(self):
        "Order in request: not sortable field."
        user = self.get_root_user()

        create_contact = partial(FakeContact.objects.create, user=user)
        wallen = create_contact(first_name='Aiz',  last_name='Wallenstein')
        cranel = create_contact(first_name='Bell', last_name='Cranel')
        crozzo = create_contact(first_name='Welf', last_name='Crozzo')

        brick = self.OrderedBrick()
        template_context = brick.get_template_context(
            self.build_context(user=user, url=f'/?{brick.id}_order=languages'),
            FakeContact.objects.all()
        )

        with self.assertNoException():
            page = template_context['page']
            [*page.object_list]  # NOQA

        self._assertPageOrderedLike(page, [cranel, crozzo, wallen])

    def test_specific_relations_brick01(self):
        rtype = RelationType.objects.builder(
            id='test-subject_designed', predicate='designed',
        ).symmetric(id='test-object_designed_by', predicate='is designed by').get_or_create()[0]
        rbi = RelationBrickItem.objects.create(relation_type=rtype)

        brick = SpecificRelationsBrick(relationbrick_item=rbi)
        self.assertEqual((Relation,), brick.dependencies)
        self.assertEqual((rtype.id,), brick.relation_type_deps)
        self.assertEqual(
            _('Relationship block: «{predicate}»').format(predicate=rtype.predicate),
            brick.verbose_name,
        )
        self.assertEqual((), brick.target_ctypes)

        # ---
        # Important for ID
        get_ct = ContentType.objects.get_for_model
        self.assertLess(get_ct(FakeContact).id, get_ct(FakeOrganisation).id)

        user = self.get_root_user()
        # NB: we try to get various IDs for different types
        create_contact = partial(FakeContact.objects.create, user=user)
        wily = create_contact(first_name='John', last_name='Wily')
        wood   = create_contact(first_name='Wood',   last_name='Man')
        bubble = create_contact(first_name='Bubble', last_name='Man')
        hq = FakeOrganisation.objects.create(user=user, name='HeadQuarter')
        metal  = create_contact(first_name='Metal',  last_name='Man')
        quick  = create_contact(first_name='Quick',  last_name='Man')

        create_rel = partial(Relation.objects.create, user=user, type=rtype, subject_entity=wily)
        create_rel(object_entity=wood)
        create_rel(object_entity=metal)
        create_rel(object_entity=hq)
        create_rel(object_entity=bubble)
        create_rel(object_entity=quick)

        brick.page_size = 3
        # page 1 ---
        context = self.build_context(user=user, instance=wily)

        # Fill cache
        [*entity_ctypes()]  # NOQA
        ContentType.objects.get_for_model(Relation)
        ContentType.objects.get_for_model(CremeEntity)

        # Queries:
        #   - COUNT Relations
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Relations
        #   - Contacts (only first page, no Organisation)
        #   - Compatible ContentTypes (see all_ctypes_configured())
        with self.assertNumQueries(6):
            render = brick.detailview_display(context)

        brick_node1 = self.get_brick_node(self.get_html_tree(render), brick=brick)
        self.assertEqual(
            f'{_("{count} Entities").format(count=5)} — {rtype.predicate}',
            self.get_brick_title(brick_node1),
        )
        self.assertInstanceLink(brick_node1, bubble)
        self.assertInstanceLink(brick_node1, metal)
        self.assertInstanceLink(brick_node1, quick)
        self.assertNoInstanceLink(brick_node1, hq)
        self.assertNoInstanceLink(brick_node1, wood)

        # page 2 ---
        render2 = brick.detailview_display(
            self.build_context(user=user, instance=wily, request_data={f'{brick.id}_page': 2})
        )
        brick_node2 = self.get_brick_node(self.get_html_tree(render2), brick=brick)
        self.assertInstanceLink(brick_node2, hq)
        self.assertInstanceLink(brick_node2, wood)
        self.assertNoInstanceLink(brick_node2, bubble)
        self.assertNoInstanceLink(brick_node2, quick)
        self.assertNoInstanceLink(brick_node2, metal)

        # TODO: test with configured cells for ContentTypes

    def test_specific_relations_brick02(self):
        "ContentType constraints."
        rtype = RelationType.objects.builder(
            id='test-subject_loves', predicate='loves',
            models=[FakeOrganisation, FakeContact],
        ).symmetric(
            id='test-object_loved', predicate='is loved by',
        ).get_or_create()[0]
        rbi = RelationBrickItem.objects.get_or_create(relation_type=rtype)[0]

        brick = SpecificRelationsBrick(relationbrick_item=rbi)
        expected_models = [FakeOrganisation, FakeContact]

        with self.assertNumQueries(1):
            models = brick.target_ctypes

        self.assertIsInstance(models, tuple)
        self.assertCountEqual(expected_models, [*models])

        with self.assertNumQueries(0):
            self.assertCountEqual(expected_models, [*brick.target_ctypes])
