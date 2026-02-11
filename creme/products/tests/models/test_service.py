from decimal import Decimal

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.products.models import Category, SubCategory

from ..base import Service, _ProductsTestCase, skipIfCustomService


@skipIfCustomService
class ServiceTestCase(_ProductsTestCase):
    def _build_service_cat_subcat(self, user):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(
            name='Eva', description='Fake gods', category=cat,
        )
        service = Service.objects.create(
            user=user,
            name='Eva00', description='description#1',
            unit_price=Decimal('1.23'), reference='42', unit='unit',
            category=cat, sub_category=sub_cat,
        )
        return service, cat, sub_cat

    def test_delete_subcategory(self):
        user = self.login_as_root_and_get()

        service, cat, sub_cat = self._build_service_cat_subcat(user=user)
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'subcategory', sub_cat.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_products__service_sub_category',
            errors=_('Deletion is not possible.'),
        )

    def test_delete_category(self):
        user = self.login_as_root_and_get()

        service, cat, sub_cat = self._build_service_cat_subcat(user=user)
        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('products', 'category', cat.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_products__service_category',
            errors=_('Deletion is not possible.'),
        )

    def test_clone(self):
        user = self.login_as_root_and_get()

        create_image = self._create_image
        img_1 = create_image(ident=1, user=user)
        img_2 = create_image(ident=2, user=user)

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        service.images.set([img_1, img_2])

        cloned_service = self.clone(service)
        self.assertIsInstance(cloned_service, Service)
        self.assertNotEqual(service.pk, cloned_service.pk)
        self.assertEqual(service.name, cloned_service.name)
        self.assertEqual(sub_cat, cloned_service.sub_category)
        self.assertCountEqual([img_1, img_2], cloned_service.images.all())

    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     create_image = self._create_image
    #     img_1 = create_image(ident=1, user=user)
    #     img_2 = create_image(ident=2, user=user)
    #
    #     sub_cat = SubCategory.objects.all()[0]
    #     service = Service.objects.create(
    #         user=user, name='Eva00', description='A fake god',
    #         unit_price=Decimal('1.23'),
    #         category=sub_cat.category, sub_category=sub_cat,
    #     )
    #     service.images.set([img_1, img_2])
    #
    #     cloned_service = service.clone()
    #     self.assertIsInstance(cloned_service, Service)
    #     self.assertNotEqual(service.pk, cloned_service.pk)
    #     self.assertEqual(service.name, cloned_service.name)
    #     self.assertEqual(sub_cat, cloned_service.sub_category)
    #     self.assertCountEqual([img_1, img_2], cloned_service.images.all())
