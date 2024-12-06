from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntity2  # NOQA
from creme.creme_core.models import CustomEntityType, FakeContact

from ..base import CremeTestCase


class CustomEntityTypeTestCase(CremeTestCase):
    def _enable_type(self, id, name):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.save()

    def test_populate(self):
        types = [*CustomEntityType.objects.order_by('id')]
        self.assertEqual(10, len(types))

        type1 = types[0]
        self.assertEqual(1,                type1.id)
        self.assertEqual('Placeholder #1', type1.name)
        self.assertFalse(type1.enabled)

        type10 = types[9]
        self.assertEqual(10,                type10.id)
        self.assertEqual('Placeholder #10', type10.name)
        self.assertFalse(type10.enabled)

    def test_manager_get_for_id(self):
        self._enable_type(id=1, name='Shop')
        self._enable_type(id=2, name='Building')

        with self.assertNumQueries(1):
            ce_type1 = CustomEntityType.objects.get_for_id(1)
        self.assertIsInstance(ce_type1, CustomEntityType)
        self.assertEqual(1,      ce_type1.id)
        self.assertEqual('Shop', ce_type1.name)

        with self.assertNumQueries(0):
            ce_type2 = CustomEntityType.objects.get_for_id(2)
        self.assertIsInstance(ce_type2, CustomEntityType)
        self.assertEqual(2,          ce_type2.id)
        self.assertEqual('Building', ce_type2.name)

        with self.assertNumQueries(0):
            ce_type3 = CustomEntityType.objects.get_for_id(3)
        self.assertEqual(3,                ce_type3.id)
        self.assertEqual('Placeholder #3', ce_type3.name)

    def test_manager_items(self):
        self._enable_type(id=1, name='Shop')
        self._enable_type(id=2, name='Building')

        with self.assertNumQueries(1):
            ce_types = {
                ce_type.id: ce_type
                for ce_type in CustomEntityType.objects.items()
            }
        self.assertEqual(10, len(ce_types))

        ce_type1 = ce_types[1]
        self.assertIsInstance(ce_type1, CustomEntityType)
        self.assertEqual(1,      ce_type1.id)
        self.assertEqual('Shop', ce_type1.name)

        ce_type2 = ce_types[2]
        self.assertIsInstance(ce_type2, CustomEntityType)
        self.assertEqual(2,          ce_type2.id)
        self.assertEqual('Building', ce_type2.name)

        with self.assertNumQueries(0):
            [*CustomEntityType.objects.items()]  # NOQA

        with self.assertNumQueries(0):
            CustomEntityType.objects.get_for_id(2)  # NOQA

    def test_custom_entity_type(self):
        ce_type1 = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertIs(CustomEntity1, ce_type1.entity_model)

        ce_type2 = self.get_object_or_fail(CustomEntityType, id=2)
        self.assertIs(CustomEntity2, ce_type2.entity_model)

    def test_content_type1(self):
        ct1 = ContentType.objects.get_for_model(FakeContact)
        self.assertEqual('Test Contact', str(ct1))

        ct2 = ContentType.objects.get_for_model(CustomEntity1)
        self.assertEqual('?', str(ct2))

    def test_content_type2(self):
        name1 = 'Shop'
        name2 = 'Foundation'

        self._enable_type(id=1, name=name1)
        self._enable_type(id=2, name=name2)

        ct1 = ContentType.objects.get_for_model(CustomEntity1)
        with self.assertNumQueries(1):
            label1 = str(ct1)
        self.assertEqual(name1, label1)

        # ---
        ct2 = ContentType.objects.get_for_model(CustomEntity2)
        with self.assertNumQueries(0):
            label2 = str(ct2)
        self.assertEqual(name2, label2)
