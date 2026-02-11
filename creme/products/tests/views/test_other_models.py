from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import pgettext

from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.products.models import Category, SubCategory
from creme.products.views.other_models import NarrowedSubCategoriesBrick


class SubCategoryConfigViewsTestCase(BrickTestCaseMixin, CremeTestCase):
    def test_portal(self):
        self.login_as_standard(admin_4_apps=('products',))

        cat1, cat2 = Category.objects.all()[:2]
        response = self.assertGET200(
            reverse('products__category_portal', args=(cat1.id,)),
        )
        self.assertTemplateUsed(response, 'products/config/category-portal.html')

        get_context = response.context.get
        self.assertEqual(cat1, get_context('category'))
        self.assertEqual(_('Products and services'), get_context('app_verbose_name'))
        self.assertEqual(
            reverse('products__reload_category_brick', args=(cat1.id,)),
            get_context('bricks_reload_url'),
        )

        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=NarrowedSubCategoriesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=SubCategory.objects.filter(category=cat1).count(),
            title='{count} Sub-category in this category',
            plural_title='{count} Sub-categories in this category',
        )
        self.assertBrickHeaderHasButton(
            self.get_brick_header_buttons(brick_node),
            url=reverse('products__create_subcategory', args=(cat1.id,)),
            label=pgettext('products', 'Create a sub-category'),
        )

        texts = {
            text
            for row in self.get_brick_table_rows(brick_node)
            for cell in row.findall('.//td') if (text := cell.text.strip())
        }
        self.assertIn(
            SubCategory.objects.filter(category=cat1).first().name,
            texts,
        )
        self.assertNotIn(
            SubCategory.objects.filter(category=cat2).first().name,
            texts,
        )

    def test_creation(self):
        self.login_as_standard(admin_4_apps=('products',))

        cat = Category.objects.all()[0]
        url = reverse('products__create_subcategory', args=(cat.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(
            pgettext('products', 'New sub-category for «{category}»').format(category=cat),
            context.get('title'),
        )
        self.assertEqual(
            pgettext('products', 'Save the sub-category'),
            context.get('submit_label'),
        )

        with self.assertNoException():
            fields = context['form'].fields
        self.assertIn('name', fields)
        self.assertIn('description', fields)
        self.assertEqual(2, len(fields))

        # POST ---
        name = 'New subtype'
        description = 'Blabla'
        self.assertNoFormError(self.client.post(
            url, data={'name': name, 'description': description})
        )
        sub_cat = self.get_object_or_fail(SubCategory, name=name, category=cat)
        self.assertEqual(description, sub_cat.description)

    def test_reload_brick(self):
        self.login_as_standard(admin_4_apps=('products',))

        cat = Category.objects.all()[0]
        url = reverse('products__reload_category_brick', args=(cat.id,))
        self.assertGET404(url)  # No brick ID
        self.assertGET404(url, data={'brick_id': 'invalid'})

        response = self.assertGET200(url, data={'brick_id': NarrowedSubCategoriesBrick.id})
        self.assertEqual('application/json', response['Content-Type'])

        content = response.json()
        self.assertIsList(content, length=1)

        brick_data = content[0]
        self.assertEqual(2, len(brick_data))
        self.assertEqual(NarrowedSubCategoriesBrick.id, brick_data[0])
        self.assertIn(f' id="brick-{NarrowedSubCategoriesBrick.id}"', brick_data[1])
        self.assertIn(f' data-brick-id="{NarrowedSubCategoriesBrick.id}"', brick_data[1])

    def test_forbidden(self):
        self.login_as_standard(allowed_apps=('products',))  # admin_4_apps=('products',)

        cat_id = Category.objects.first().id
        self.assertGET403(reverse('products__category_portal', args=(cat_id,)))
        self.assertGET403(reverse('products__create_subcategory', args=(cat_id,)))
        self.assertGET403(reverse('products__reload_category_brick', args=(cat_id,)))
