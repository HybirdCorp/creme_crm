from django.contrib.contenttypes.models import ContentType

from creme.creme_core.models import CustomEntity1  # NOQA
from creme.creme_core.models import CustomEntity2  # NOQA
from creme.creme_core.models import CustomEntityType, FakeContact

from ..base import CremeTestCase


class CustomEntityTypeTestCase(CremeTestCase):
    def test_manager_get_for_id(self):
        create_type = CustomEntityType.objects.create
        create_type(number=1, name='Shop')
        create_type(number=2, name='Building')

        with self.assertNumQueries(1):
            item1 = CustomEntityType.objects.get_for_id(1)
        self.assertIsInstance(item1, CustomEntityType)
        self.assertEqual(1,      item1.number)
        self.assertEqual('Shop', item1.name)

        with self.assertNumQueries(0):
            item2 = CustomEntityType.objects.get_for_id(2)
        self.assertIsInstance(item2, CustomEntityType)
        self.assertEqual(2,          item2.number)
        self.assertEqual('Building', item2.name)

    def test_manager_items(self):
        create_type = CustomEntityType.objects.create
        create_type(number=1, name='Shop')
        create_type(number=2, name='Building')

        with self.assertNumQueries(1):
            items = {
                ce_type.number: ce_type
                for ce_type in CustomEntityType.objects.items()
            }
        self.assertEqual(2, len(items))

        item1 = items[1]
        self.assertIsInstance(item1, CustomEntityType)
        self.assertEqual(1,      item1.number)
        self.assertEqual('Shop', item1.name)

        item2 = items[2]
        self.assertIsInstance(item2, CustomEntityType)
        self.assertEqual(2,          item2.number)
        self.assertEqual('Building', item2.name)

        with self.assertNumQueries(0):
            [*CustomEntityType.objects.items()]  # NOQA

        with self.assertNumQueries(0):
            CustomEntityType.objects.get_for_id(2)  # NOQA

    def test_custom_entity_type(self):
        item1 = CustomEntityType.objects.create(number=1, name='Shop')
        self.assertIs(CustomEntity1, item1.entity_model)

        item2 = CustomEntityType.objects.create(number=2, name='Store')
        self.assertIs(CustomEntity2, item2.entity_model)

    def test_content_type1(self):
        ct1 = ContentType.objects.get_for_model(FakeContact)
        self.assertEqual('Test Contact', str(ct1))

        ct2 = ContentType.objects.get_for_model(CustomEntity1)
        self.assertEqual('?', str(ct2))

    def test_content_type2(self):
        name1 = 'Shop'
        name2 = 'Foundation'

        create_item = CustomEntityType.objects.create
        create_item(number=1, name=name1)
        create_item(number=2, name=name2)

        ct1 = ContentType.objects.get_for_model(CustomEntity1)
        with self.assertNumQueries(1):
            label1 = str(ct1)
        self.assertEqual(name1, label1)

        # ---
        ct2 = ContentType.objects.get_for_model(CustomEntity2)
        with self.assertNumQueries(0):
            label2 = str(ct2)
        self.assertEqual(name2, label2)
