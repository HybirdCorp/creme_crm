from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from creme.products.models import Category, SubCategory

from .base import Product, _ProductsTestCase


class SubCategoryEnumeratorTestCase(_ProductsTestCase):
    @staticmethod
    def _build_choices_url():
        return reverse(
            'creme_core__enumerable_choices',
            args=(ContentType.objects.get_for_model(Product).id, 'sub_category'),
        )

    def _assertChoice(self, sub_cat, choices):
        pk = sub_cat.id
        for index, choice in enumerate(choices):
            if choice['value'] == pk:
                self.assertEqual(sub_cat.name, choice['label'])
                self.assertEqual(sub_cat.category.name, choice['group'])

                return index

        self.fail(f'{sub_cat} not found in {choices}')  # pragma: no cover

    def test_simple(self):
        self.login_as_root()

        create_cat = Category.objects.create
        cat1 = create_cat(name='Category A')
        cat2 = create_cat(name='Category B')

        create_sub_cat = SubCategory.objects.create
        sub_cat11 = create_sub_cat(name='Sub cat #001', category=cat1)
        sub_cat2  = create_sub_cat(name='Sub cat #001', category=cat2)
        sub_cat13 = create_sub_cat(name='Sub cat #003', category=cat1)
        sub_cat12 = create_sub_cat(name='Sub cat #002', category=cat1)

        url = self._build_choices_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.json()

        self.assertIsInstance(choices, list)
        index11 = self._assertChoice(sub_cat11, choices)
        index12 = self._assertChoice(sub_cat12, choices)
        index13 = self._assertChoice(sub_cat13, choices)
        index2  = self._assertChoice(sub_cat2, choices)

        self.assertEqual(index11 + 1, index12)
        self.assertEqual(index12 + 1, index13)
        self.assertGreater(index2, index13)
