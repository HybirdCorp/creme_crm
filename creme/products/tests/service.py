# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from creme.products.tests.base import _ProductsTestCase
    from creme.products.models import Category, SubCategory, Service
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ServiceTestCase',)


class ServiceTestCase(_ProductsTestCase):
    def setUp(self):
        self.login()

    def test_createview(self):
        self.assertEqual(0, Service.objects.count())

        url = '/products/service/add'
        self.assertGET200(url)

        name = 'Eva washing'
        description = 'Your Eva is washed by pretty girls'
        reference = '42'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        unit = 'A wash'
        unit_price = '1.23'
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'reference':    reference,
                                          'description':  description,
                                          'unit':         unit,
                                          'unit_price':   unit_price,
                                          'sub_category': self._cat_field(cat, sub_cat),
                                         }
                                   )
        self.assertNoFormError(response)

        services = Service.objects.all()
        self.assertEqual(1, len(services))

        service = services[0]
        self.assertEqual(name,                service.name)
        self.assertEqual(reference,           service.reference)
        self.assertEqual(description,         service.description)
        self.assertEqual(unit,                service.unit)
        self.assertEqual(Decimal(unit_price), service.unit_price)
        self.assertEqual(cat,                 service.category)
        self.assertEqual(sub_cat,             service.sub_category)

        self.assertRedirects(response, service.get_absolute_url())

    def test_editview(self):
        name = 'Eva washing'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(user=self.user, name=name, description='Blabla',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='A wash',
                                        )

        url = '/products/service/edit/%s' % service.id
        self.assertGET200(url)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'reference':    service.reference,
                                          'description':  service.description,
                                          'unit_price':   unit_price,
                                          'sub_category': self._cat_field(service.category,
                                                                          service.sub_category
                                                                         ),
                                          'unit':         service.unit,
                                         }
                                   )
        self.assertNoFormError(response)

        service = self.refresh(service)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_listview(self):
        cat = Category.objects.all()[0]
        create_serv = partial(Service.objects.create, user=self.user, unit='unit',
                              category=cat, sub_category=SubCategory.objects.all()[0],
                             )
        services = [create_serv(name='Eva00', description='description#1',
                                unit_price=Decimal('1.23'), reference='42',
                               ),
                    create_serv(name='Eva01', description='description#2',
                                unit_price=Decimal('6.58'), reference='43',
                               ),
                   ]

        response = self.client.get('/products/services')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            services_page = response.context['entities']

        self.assertEqual(2, services_page.paginator.count)
        self.assertEqual(set(services), set(services_page.object_list))

    def _build_service_cat_subcat(self):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)
        service = Service.objects.create(user=self.user, name='Eva00', description='description#1',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='unit'
                                        )
        return service, cat, sub_cat

    def test_delete_subcategory(self):
        service, cat, sub_cat = self._build_service_cat_subcat()

        self.assertPOST404('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.get_object_or_fail(SubCategory, pk=sub_cat.pk)

        service = self.get_object_or_fail(Service, pk=service.pk)
        self.assertEqual(sub_cat, service.sub_category)

    def test_delete_category(self):
        service, cat, sub_cat = self._build_service_cat_subcat()

        self.assertPOST404('/creme_config/products/category/delete', data={'id': cat.pk})
        self.get_object_or_fail(SubCategory, pk=sub_cat.pk)
        self.get_object_or_fail(Category, pk=cat.pk)

        service = self.get_object_or_fail(Service, pk=service.pk)
        self.assertEqual(sub_cat, service.sub_category)
        self.assertEqual(cat,     service.category)
