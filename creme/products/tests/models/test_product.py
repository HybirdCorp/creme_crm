from decimal import Decimal
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.products.models import Category, SubCategory

from ..base import Folder, Product, _ProductsTestCase, skipIfCustomProduct


@skipIfCustomProduct
class ProductTestCase(_ProductsTestCase):
    def _build_product_cat_subcat(self, user):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(
            name='Eva', description='Fake gods', category=cat,
        )
        product = Product.objects.create(
            user=user,
            name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=cat, sub_category=sub_cat,
        )

        return product, cat, sub_cat

    def test_delete_sub_category__not_used(self):
        self.login_as_root()

        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(
            name='Eva', description='Fake gods', category=cat,
        )

        self.assertNoFormError(self.client.post(reverse(
            'creme_config__delete_instance',
            args=('products', 'subcategory', sub_cat.id),
        )))

        job = self.get_deletion_command_or_fail(SubCategory).job
        job.type.execute(job)
        self.assertDoesNotExist(sub_cat)

    def test_delete_sub_category__used(self):
        user = self.login_as_root_and_get()

        product, cat, sub_cat = self._build_product_cat_subcat(user=user)
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'subcategory', sub_cat.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_products__product_sub_category',
            errors=_('Deletion is not possible.'),
        )

    def test_delete_category__used(self):
        user = self.login_as_root_and_get()

        product, cat, sub_cat = self._build_product_cat_subcat(user=user)
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'category', cat.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_products__product_category',
            errors=_('Deletion is not possible.'),
        )

    def test_clone(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'), code=42,
            category=sub_cat.category, sub_category=sub_cat,
        )

        create_image = partial(
            self._create_image, user=user,
            folder=Folder.objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)

        product.images.set([img_1, img_2])

        cloned_product = self.clone(product)
        self.assertIsInstance(cloned_product, Product)
        self.assertNotEqual(product.pk, cloned_product.pk)
        self.assertEqual(product.name, cloned_product.name)
        self.assertEqual(sub_cat, cloned_product.sub_category)
        self.assertCountEqual([img_1, img_2], cloned_product.images.all())

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     sub_cat = SubCategory.objects.all()[0]
    #     product = Product.objects.create(
    #         user=user, name='Eva00', description='A fake god',
    #         unit_price=Decimal('1.23'), code=42,
    #         category=sub_cat.category, sub_category=sub_cat,
    #     )
    #
    #     create_image = partial(
    #         self._create_image, user=user,
    #         folder=get_folder_model().objects.create(user=user, title=_('My Images')),
    #     )
    #     img_1 = create_image(ident=1)
    #     img_2 = create_image(ident=2)
    #
    #     product.images.set([img_1, img_2])
    #
    #     cloned_product = product.clone()
    #     self.assertIsInstance(cloned_product, Product)
    #     self.assertNotEqual(product.pk, cloned_product.pk)
    #     self.assertEqual(product.name, cloned_product.name)
    #     self.assertEqual(sub_cat, cloned_product.sub_category)
    #     self.assertCountEqual([img_1, img_2], cloned_product.images.all())
