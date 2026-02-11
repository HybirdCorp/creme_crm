from creme.products.models import Category, SubCategory

from ..base import _ProductsTestCase


class SubCategoryTestCase(_ProductsTestCase):
    def test_populate(self):
        self.assertTrue(Category.objects.exists())
        self.assertTrue(SubCategory.objects.exists())

    def test_is_custom(self):
        cat = Category.objects.create(name='Category', description='description')
        self.assertTrue(cat.is_custom)
        sub_cat = SubCategory(name='Sub cat', category=cat, description='description')
        self.assertTrue(sub_cat.is_custom)

        with self.assertNoException():
            sub_cat.save()

        # ---
        sub_cat.is_custom = False

        with self.assertRaises(ValueError) as cm:
            sub_cat.save()

        self.assertEqual(
            f'The SubCategory id="{sub_cat.id}" is not custom,'
            f'so the related Category cannot be custom.',
            str(cm.exception),
        )

        # ---
        cat.is_custom = False

        with self.assertNoException():
            sub_cat.save()
