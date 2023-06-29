from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_config.registry import config_registry
from creme.creme_core.tests.base import CremeTestCase

from ..models import Category, SubCategory


class CreateCategoryTestCase(CremeTestCase):
    def test_create_subcategory_from_widget(self):
        user = self.login_as_root_and_get()

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
                        'value': str(cat12.id),
                        'label': str(cat12),
                        'group': str(cat1)
                    },
                ],
                'value': str(cat12.id),
            },
            response2.json(),
        )

    def test_create_subcategory_from_widget__unknown_category(self):
        user = self.login_as_root_and_get()

        url, _allowed = config_registry.get_model_creation_info(SubCategory, user)
        self.assertGET200(url)

        count = SubCategory.objects.count()

        self.client.post(
            url, data={'name': 'sub12', 'description': 'sub12', 'category': 99999},
        )
        self.assertEqual(count, SubCategory.objects.count())

    def test_create_category_from_widget(self):
        user = self.login_as_root_and_get()

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
