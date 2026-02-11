from decimal import Decimal
from functools import partial

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.products.models import Category, SubCategory

from ..base import Folder, Service, _ProductsTestCase, skipIfCustomService


@skipIfCustomService
class ServiceViewsTestCase(_ProductsTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(
            user=user, name='Eva washing', reference='42', description='Blabla',
            unit_price=Decimal('1.23'),  unit='A wash',
            category=sub_cat.category, sub_category=sub_cat,
        )

        response = self.assertGET200(service.get_absolute_url())
        self.assertTemplateUsed(response, 'products/view_service.html')
        self.assertTemplateUsed(response, 'products/bricks/images.html')

    def test_creation(self):
        user = self.login_as_root_and_get()
        self.assertEqual(0, Service.objects.count())

        url = reverse('products__create_service')
        self.assertGET200(url)

        name = 'Eva washing'
        description = 'Your Eva is washed by pretty girls'
        reference = '42'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.filter(category=cat)[0]
        unit = 'A wash'
        unit_price = '1.23'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'reference':    reference,
                'description':  description,
                'unit':         unit,
                'unit_price':   unit_price,

                self.EXTRA_CATEGORY_KEY: str(sub_cat.pk),
            },
        )
        self.assertNoFormError(response)

        service = self.get_alone_element(Service.objects.all())
        self.assertEqual(name,                service.name)
        self.assertEqual(reference,           service.reference)
        self.assertEqual(description,         service.description)
        self.assertEqual(unit,                service.unit)
        self.assertEqual(Decimal(unit_price), service.unit_price)
        self.assertEqual(cat,                 service.category)
        self.assertEqual(sub_cat,             service.sub_category)

        self.assertRedirects(response, service.get_absolute_url())
        self.assertTemplateUsed(response, 'products/view_service.html')

    def test_edition(self):
        user = self.login_as_root_and_get()

        name = 'Eva washing'
        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(
            user=user, name=name, reference='42', description='Blabla',
            unit_price=Decimal('1.23'),  unit='A wash',
            category=sub_cat.category, sub_category=sub_cat,
        )

        url = service.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post(
            url,
            follow=True,
            data={
                'user':         user.pk,
                'name':         name,
                'reference':    service.reference,
                'description':  service.description,
                'unit_price':   unit_price,
                'unit':         service.unit,

                self.EXTRA_CATEGORY_KEY: str(sub_cat.pk),
            },
        )
        self.assertNoFormError(response)

        service = self.refresh(service)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_listview(self):
        user = self.login_as_root_and_get()

        cat = Category.objects.all()[0]
        create_serv = partial(
            Service.objects.create,
            user=user, unit='unit',
            category=cat, sub_category=SubCategory.objects.all()[0],
        )
        services = [
            create_serv(
                name='Eva00', description='description#1',
                unit_price=Decimal('1.23'), reference='42',
            ),
            create_serv(
                name='Eva01', description='description#2',
                unit_price=Decimal('6.58'), reference='43',
            ),
        ]

        response = self.assertGET200(Service.get_lv_absolute_url())

        with self.assertNoException():
            services_page = response.context['page_obj']

        self.assertEqual(2, services_page.paginator.count)
        self.assertCountEqual(services, services_page.object_list)

    def test_add_images(self):
        user = self.login_as_basic_user(Service)

        create_image = partial(
            self._create_image, user=user,
            folder=Folder.objects.create(user=user, title=_('My Images')),
        )
        img_1 = create_image(ident=1)
        img_2 = create_image(ident=2)
        img_3 = create_image(ident=3)
        img_4 = create_image(ident=4, user=self.get_root_user())
        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_4))

        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(
            user=user, name='Eva00', description='A fake god',
            unit_price=Decimal('1.23'),
            category=sub_cat.category, sub_category=sub_cat,
        )
        service.images.set([img_3])

        url = reverse('products__add_images_to_service', args=(service.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/link-popup.html')

        get_ctxt1 = response1.context.get
        self.assertEqual(
            _('New images for «{entity}»').format(entity=service),
            get_ctxt1('title'),
        )
        self.assertEqual(_('Link the images'), get_ctxt1('submit_label'))

        # ---
        def post(*images):
            return self.client.post(
                url,
                follow=True,
                data={'images': self.formfield_value_multi_creator_entity(*images)},
            )

        response2 = post(img_1, img_4)
        self.assertEqual(200, response2.status_code)
        self.assertFormError(
            response2.context['form'],
            field='images',
            errors=_('Some entities are not linkable: {}').format(img_4),
        )

        # ---
        response3 = post(img_1, img_2)
        self.assertNoFormError(response3)
        self.assertCountEqual([img_1, img_2, img_3], service.images.all())

    def test_remove_image(self):
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

        url = reverse('products__remove_image', args=(service.id,))
        data = {'id': img_1.id}
        self.assertGET405(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertListEqual([img_2], [*service.images.all()])
