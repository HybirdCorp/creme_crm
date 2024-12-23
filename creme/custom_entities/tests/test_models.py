from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CustomEntityType,
    FakeContact,
    FakeOrganisation,
)
from creme.creme_core.models.utils import (
    model_verbose_name,
    model_verbose_name_plural,
)

from ..models import CustomEntity1  # NOQA
from ..models import CustomEntity2  # NOQA
from .base import CustomEntitiesBaseTestCase


class CustomEntityModelsTestCase(CustomEntitiesBaseTestCase):
    def test_populate(self):
        types = [*CustomEntityType.objects.order_by('id')]
        self.assertEqual(20, len(types))

        type1 = types[0]
        self.assertEqual(1,                 type1.id)
        self.assertEqual('Placeholder #1',  type1.name)
        self.assertEqual('Placeholders #1', type1.plural_name)
        self.assertFalse(type1.enabled)

        type20 = types[19]
        self.assertEqual(20,                 type20.id)
        self.assertEqual('Placeholder #20',  type20.name)
        self.assertEqual('Placeholders #20', type20.plural_name)
        self.assertFalse(type20.enabled)

    def test_manager_get_for_id(self):
        self._enable_type(id=1, name='Shop')
        self._enable_type(id=2, name='Building')

        with self.assertNumQueries(1):
            ce_type1 = CustomEntityType.objects.get_for_id(1)
        self.assertIsInstance(ce_type1, CustomEntityType)
        self.assertEqual(1,       ce_type1.id)
        self.assertEqual('Shop',  ce_type1.name)
        self.assertEqual('Shops', ce_type1.plural_name)

        with self.assertNumQueries(0):
            ce_type2 = CustomEntityType.objects.get_for_id(2)
        self.assertIsInstance(ce_type2, CustomEntityType)
        self.assertEqual(2,          ce_type2.id)
        self.assertEqual('Building', ce_type2.name)

        with self.assertNumQueries(0):
            ce_type3 = CustomEntityType.objects.get_for_id(3)
        self.assertEqual(3,                ce_type3.id)
        self.assertEqual('Placeholder #3', ce_type3.name)

    def test_manager_get_for_model(self):
        self._enable_type(id=1, name='Shop')
        self._enable_type(id=2, name='Building')

        with self.assertNumQueries(1):
            ce_type1 = CustomEntityType.objects.get_for_model(CustomEntity1)
        self.assertIsInstance(ce_type1, CustomEntityType)
        self.assertEqual(1, ce_type1.id)

        with self.assertNumQueries(0):
            ce_type2 = CustomEntityType.objects.get_for_model(CustomEntity2)
        self.assertEqual(2, ce_type2.id)

        self.assertIsNone(CustomEntityType.objects.get_for_model(FakeContact))

    def test_manager_all_types(self):
        self._enable_type(id=1, name='Shop')
        self._enable_type(id=2, name='Building')

        with self.assertNumQueries(1):
            ce_types = {
                ce_type.id: ce_type
                for ce_type in CustomEntityType.objects.all_types()
            }
        self.assertEqual(20, len(ce_types))

        ce_type1 = ce_types[1]
        self.assertIsInstance(ce_type1, CustomEntityType)
        self.assertEqual(1,      ce_type1.id)
        self.assertEqual('Shop', ce_type1.name)

        ce_type2 = ce_types[2]
        self.assertIsInstance(ce_type2, CustomEntityType)
        self.assertEqual(2,          ce_type2.id)
        self.assertEqual('Building', ce_type2.name)

        with self.assertNumQueries(0):
            [*CustomEntityType.objects.all_types()]  # NOQA

        with self.assertNumQueries(0):
            CustomEntityType.objects.get_for_id(2)  # NOQA

    def test_custom_entity_type(self):
        ce_type1 = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertIs(CustomEntity1, ce_type1.entity_model)

        ce_type2 = self.get_object_or_fail(CustomEntityType, id=2)
        self.assertIs(CustomEntity2, ce_type2.entity_model)

    def test_model_verbose_name(self):
        ce_type1 = self._enable_type(id=1, name='Shop')

        self.assertEqual('Test Contact',      model_verbose_name(FakeContact))
        self.assertEqual('Test Organisation', model_verbose_name(FakeOrganisation))
        self.assertEqual(ce_type1.name,       model_verbose_name(ce_type1.entity_model))

    def test_model_verbose_name__disabled(self):
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)
        self.assertEqual(_('Invalid custom type'), model_verbose_name(ce_type.entity_model))

    def test_model_verbose_name__deleted(self):
        ce_type = self._enable_type(id=1, name='Building', deleted=True)
        self.assertEqual(
            _('{custom_model} [deleted]').format(custom_model=ce_type.name),
            model_verbose_name(ce_type.entity_model),
        )

    def test_model_verbose_name_plural(self):
        ce_type1 = self._enable_type(id=1, name='Shop', plural_name='Shops')

        self.assertEqual('Test Contacts',      model_verbose_name_plural(FakeContact))
        self.assertEqual('Test Organisations', model_verbose_name_plural(FakeOrganisation))
        self.assertEqual(ce_type1.plural_name, model_verbose_name_plural(ce_type1.entity_model))

    def test_model_verbose_name_plural__disabled(self):
        ce_type = self.get_object_or_fail(CustomEntityType, id=1)
        self.assertFalse(ce_type.enabled)
        self.assertEqual('?', model_verbose_name_plural(ce_type.entity_model))

    def test_model_verbose_name_plural__deleted(self):
        ce_type = self._enable_type(
            id=1, name='Country', plural_name='Countries', deleted=True,
        )
        self.assertEqual(
            _('{custom_model} [deleted]').format(custom_model=ce_type.plural_name),
            model_verbose_name_plural(ce_type.entity_model),
        )

    def test_content_type__disabled(self):
        ct1 = ContentType.objects.get_for_model(FakeContact)
        self.assertEqual('Test Contact', str(ct1))

        ct2 = ContentType.objects.get_for_model(CustomEntity1)
        self.assertEqual(_('Invalid custom type'), str(ct2))

    def test_content_type__enabled(self):
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

    def test_content_type__deleted(self):
        name = 'Shop'
        ce_type1 = self._enable_type(id=1, name=name, deleted=True)

        ct = ContentType.objects.get_for_model(ce_type1.entity_model)
        with self.assertNumQueries(1):
            label = str(ct)
        self.assertEqual(_('{custom_model} [deleted]').format(custom_model=name), label)
