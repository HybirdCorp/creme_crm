# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump

from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_config.registry import config_registry
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.forms.base import FieldTestCase

from ..forms.fields import CategoryField
from ..models import Category, SubCategory


class CategoryFieldTestCase(FieldTestCase):
    @staticmethod
    def _build_value(cat_id, subcat_id):
        return json_dump(
            {'category': cat_id, 'subcategory': subcat_id},
            separators=(',', ':'),
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        SubCategory.objects.all().delete()
        Category.objects.all().delete()

    def test_void(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(
            name='sub11', description='description', category=cat1,
        )

        with self.assertNumQueries(0):
            field = CategoryField()

        self.assertEqual(cat11, field.clean(self._build_value(cat1.id, cat11.id)))

    def test_no_user(self):
        field = CategoryField()

        self.assertIsNone(field.user)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual('', field.widget.creation_url)

    def test_user01(self):
        "In property."
        user = self.login()

        field = CategoryField()
        field.user = user

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        self.assertEqual(user, field.user)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(url, field.widget.creation_url)

    def test_user02(self):
        "In constructor."
        user = self.login()
        field = CategoryField(user=user)

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        self.assertEqual(user, field.user)
        self.assertTrue(field.widget.creation_allowed)
        self.assertEqual(url, field.widget.creation_url)

    def test_user_not_allowed(self):
        user = self.login(is_superuser=False)

        field = CategoryField()
        field.user = user

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        self.assertEqual(user, field.user)
        self.assertFalse(field.widget.creation_allowed)
        self.assertEqual(url, field.widget.creation_url)

    def test_categories01(self):
        create_cat = partial(Category.objects.create, description='description')
        cat1 = create_cat(name='cat1')
        cat2 = create_cat(name='cat2')

        field = CategoryField()
        self.assertListEqual([cat1, cat2], [*field.categories])

    def test_categories02(self):
        "Fixed Categories"
        create_cat = partial(Category.objects.create, description='description')
        cat1 = create_cat(name='cat1')
        cat2 = create_cat(name='cat2')
        create_cat(name='cat3')

        field = CategoryField(categories=[cat1.id, cat2.id])

        self.assertListEqual([cat1, cat2], [*field.categories])

    def test_format_object(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        create_subcat = partial(SubCategory.objects.create, category=cat1)
        cat11 = create_subcat(name='sub11', description='description')
        cat12 = create_subcat(name='sub12', description='description')

        from_python = CategoryField(categories=[cat1.id]).from_python
        self.assertEqual(self._build_value(cat1.id, cat11.id), from_python((cat1.id, cat11.id)))
        self.assertEqual(self._build_value(cat1.id, cat11.id), from_python(cat11))
        self.assertEqual(self._build_value(cat1.id, cat12.id), from_python(cat12))

    def test_clean_empty_required(self):
        clean = CategoryField(required=True).clean
        self.assertFieldValidationError(CategoryField, 'required', clean, None)
        self.assertFieldValidationError(CategoryField, 'required', clean, '{}')

    def test_clean_empty_not_required(self):
        clean = CategoryField(required=False).clean

        with self.assertNoException():
            value = clean(None)

        self.assertIsNone(value)

        with self.assertNoException():
            value = clean('{}')

        self.assertIsNone(value)

    def test_clean_invalid_json(self):
        clean = CategoryField(required=False).clean
        self.assertFieldValidationError(
            CategoryField, 'invalidformat', clean,
            '{"category":"12","subcategory":"1"'
        )

    def test_clean_invalid_data_type(self):
        clean = CategoryField(required=False).clean
        self.assertFieldValidationError(
            CategoryField, 'invalidtype', clean, '"this is a string"',
        )
        self.assertFieldValidationError(CategoryField, 'invalidtype', clean, '12')

    def test_clean_invalid_data(self):
        clean = CategoryField(required=False).clean
        self.assertFieldValidationError(
            CategoryField, 'invalidformat', clean,
            '{"category":"notanumber","subcategory":"1"}'
        )
        self.assertFieldValidationError(
            CategoryField, 'invalidformat', clean,
            '{"category":"12","category":"notanumber"}'
        )

    def test_clean_incomplete_data_required(self):
        clean = CategoryField().clean
        self.assertFieldValidationError(CategoryField, 'required', clean, '{"category":"1"}')
        self.assertFieldValidationError(CategoryField, 'required', clean, '{"category":"12"}')

    def test_clean_unallowed_category(self):
        "Data injection : forbidden category"
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(name='sub21', description='description', category=cat2)

        with self.assertNumQueries(0):
            field = CategoryField(categories=[cat1.id])

        value = self._build_value(cat2.id, cat21.id)
        self.assertFieldValidationError(CategoryField, 'categorynotallowed', field.clean, value)

    def test_clean_unknown_category(self):
        "Data injection : category doesn't exist"
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)

        clean = CategoryField(categories=[cat1.id, 0]).clean
        # Same error than 'forbidden', cause unknown category cannot be in list
        self.assertFieldValidationError(
            CategoryField, 'categorynotallowed', clean, self._build_value(0, cat11.id),
        )

    def test_clean_unknown_subcategory(self):
        "Data injection : subcategory doesn't exist"
        cat1 = Category.objects.create(name='cat1', description='description')

        field = CategoryField(categories=[cat1.id])
        value = self._build_value(cat1.id, 0)
        self.assertTrue(field.required)
        self.assertFieldValidationError(CategoryField, 'doesnotexist', field.clean, value)

        field.required = False
        self.assertFieldValidationError(CategoryField, 'doesnotexist', field.clean, value)

    def test_clean_invalid_category_pair(self):
        "Data injection : use incompatible category/subcategory pair"
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(
            name='sub21', description='description', category=cat2,
        )

        clean = CategoryField(categories=[cat1.id, cat2.id]).clean
        self.assertFieldValidationError(
            CategoryField, 'subcategorynotallowed', clean,
            self._build_value(cat1.id, cat21.id),
        )

    def test_clean01(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(
            name='sub11', description='description', category=cat1,
        )

        field = CategoryField(categories=[cat1.id])
        self.assertEqual(cat11, field.clean(self._build_value(cat1.id, cat11.id)))

    def test_clean02(self):
        "Use 'categories' setter."
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(
            name='sub11', description='description', category=cat1,
        )

        field = CategoryField()
        field.categories = [cat1.id]
        self.assertEqual(cat11, field.clean(self._build_value(cat1.id, cat11.id)))


class CreateCategoryTestCase(CremeTestCase):
    def test_create_subcategory_from_widget(self):
        user = self.login()

        cat1 = Category.objects.create(name='cat1', description='description')
        count = SubCategory.objects.count()

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/form/add-popup.html')

        context = response1.context
        self.assertEqual(
            pgettext('products-sub_category', 'Create a sub-category'),
            context.get('title'),
        )
        self.assertEqual(_('Save'), context.get('submit_label'))

        # ---
        response2 = self.client.post(
            url,
            data={
                'name': 'sub12',
                'description': 'sub12',
                'category': cat1.id,
            },
        )
        self.assertNoFormError(response2)
        self.assertEqual(count + 1, SubCategory.objects.count())

        cat12 = self.get_object_or_fail(SubCategory, name='sub12')

        self.assertDictEqual(
            {
                'added': [
                    {
                        'category': [str(cat1.id), str(cat1)],
                        'subcategory': [str(cat12.id), str(cat12)],
                    },
                ],
                'value': {
                    'category': str(cat1.id),
                    'subcategory': str(cat12.id),
                },
            },
            response2.json(),
        )

    def test_create_subcategory_from_widget__unknown_category(self):
        user = self.login()

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        self.assertGET200(url)

        count = SubCategory.objects.count()

        self.client.post(
            url, data={'name': 'sub12', 'description': 'sub12', 'category': 99999},
        )
        self.assertEqual(count, SubCategory.objects.count())

    def test_create_category_from_widget(self):
        user = self.login()

        url, _allowed = config_registry.get_model_creation_info(Category, user)
        self.assertGET200(url)

        response = self.client.post(
            url,
            data={
                'name': 'cat1',
                'description': 'cat1',
                'category': 'unknown',
            },
        )
        self.assertNoFormError(response)

        cat1 = self.get_object_or_fail(Category, name='cat1')
        self.assertDictEqual(
            {
                'added': [[cat1.id, str(cat1)]],
                'value': cat1.id,
            },
            response.json(),
        )
