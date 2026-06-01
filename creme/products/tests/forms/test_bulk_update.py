from decimal import Decimal
from functools import partial

from django.utils.timezone import now
from parameterized import parameterized

from creme.products.forms.fields import SubCategoryField
from creme.products.models import Category, SubCategory

from ..base import Product, _ProductsTestCase, skipIfCustomProduct


@skipIfCustomProduct
class CategoryOverriderTestCase(_ProductsTestCase):
    def test_edit_inner__category(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.order_by('category')[0]
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        field_name = 'category'
        uri = self.build_inneredit_uri(product, field_name, 'sub_category')
        response1 = self.assertGET200(uri)

        formfield_name = f'override-{field_name}'
        with self.assertNoException():
            fields = response1.context['form'].fields
            cat_f = fields[formfield_name]

        self.assertEqual(1, len(fields))

        self.assertIsInstance(cat_f, SubCategoryField)
        self.assertEqual(sub_cat, cat_f.initial)

        # ---
        next_sub_cat = SubCategory.objects.order_by('category')[1]
        response2 = self.client.post(
            uri, data={formfield_name: str(next_sub_cat.pk)},
        )
        self.assertNoFormError(response2)

        product = self.refresh(product)
        self.assertEqual(next_sub_cat, product.sub_category)
        self.assertEqual(next_sub_cat.category, product.category)

    @parameterized.expand([
        (True, False),
        (False, True),
    ])
    def test_edit_inner__category__disabled(self, enabled_category, enabled_sub_category):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.order_by('category')[0]
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        new_cat = Category.objects.create(
            name='Mecha', disabled=None if enabled_category else now(),
        )
        new_sub_cat = SubCategory.objects.create(
            name='EVA',
            category=new_cat,
            disabled=None if enabled_sub_category else now(),
        )

        field_name = 'category'
        formfield_name = f'override-{field_name}'
        response = self.assertPOST200(
            self.build_inneredit_uri(product, field_name),
            data={formfield_name: str(new_sub_cat.pk)},
        )
        self.assertFormError(
            response.context['form'],
            field=formfield_name,
            errors=SubCategoryField.default_error_messages['invalid_choice'],
        )

    def test_edit_inner__category__disabled__no_change(self):
        user = self.login_as_root_and_get()

        cat = Category.objects.create(name='Mecha', disabled=now())
        sub_cat = SubCategory.objects.create(
            name='EVA', category=cat, disabled=now(),
        )
        product = Product.objects.create(
            user=user, name='Eva00',
            description='A fake god', unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        field_name = 'category'
        self.assertNoFormError(self.client.post(
            self.build_inneredit_uri(product, field_name),
            data={f'override-{field_name}': str(sub_cat.pk)},
        ))

    def test_bulk_update__category(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.order_by('category')[0]
        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )

        product1 = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        field_name = 'category'
        build_uri = partial(self.build_bulkupdate_uri, model=Product, field=field_name)
        response1 = self.assertGET200(build_uri(entities=[product1, product2]))

        formfield_name = f'override-{field_name}'
        with self.assertNoException():
            cat_f = response1.context['form'].fields[formfield_name]

        self.assertIsInstance(cat_f, SubCategoryField)
        self.assertIsNone(cat_f.initial)

        # ---
        next_sub_cat = SubCategory.objects.order_by('category')[1]
        response2 = self.client.post(
            build_uri(),
            data={
                'entities': [product1.pk, product2.pk],
                formfield_name: str(next_sub_cat.pk),
            },
        )
        self.assertNoFormError(response2)

        product1 = self.refresh(product1)
        self.assertEqual(next_sub_cat,          product1.sub_category)
        self.assertEqual(next_sub_cat.category, product1.category)

        product2 = self.refresh(product2)
        self.assertEqual(next_sub_cat,          product2.sub_category)
        self.assertEqual(next_sub_cat.category, product2.category)

    def test_bulk_update__sub_category(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.order_by('category')[0]

        create_product = partial(
            Product.objects.create,
            user=user, description='A fake god', unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        product1 = create_product(name='Eva00', code=42)
        product2 = create_product(name='Eva01', code=43)

        field_name = 'sub_category'
        response = self.assertGET200(self.build_bulkupdate_uri(
            model=Product, field=field_name, entities=[product1, product2],
        ))

        with self.assertNoException():
            type_f = response.context['form'].fields[f'override-{field_name}']

        self.assertIsInstance(type_f, SubCategoryField)
