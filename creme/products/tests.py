# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from django.core.serializers.json import simplejson

    #from creme_core import autodiscover
    from creme_core.tests.base import CremeTestCase
    from creme_core.tests.forms import FieldTestCase

    from products.models import Category, SubCategory, Product, Service
    from products.forms.product import ProductCategoryField
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


class ProductCategoryFieldTestCase(FieldTestCase):
    format_str = '{"category": %s, "subcategory": %s}'

    def test_categories(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat2 = Category.objects.create(name='cat2', description='description')

        field = ProductCategoryField(categories=[cat1.id, cat2.id])
        self.assertEqual(2, len(field.categories))
        self.assertEqual(cat1, field._get_categories_objects()[0])
        self.assertEqual(cat2, field._get_categories_objects()[1])

    def test_default_ctypes(self):
        #autodiscover()
        self.populate('creme_core', 'products')

        field = ProductCategoryField()
        self.assertEqual(len(Category.objects.all()), len(field._get_categories_objects()))
        self.assertEqual(set(c.pk for c in Category.objects.all()), set(c.pk for c in field._get_categories_objects()))

    def test_format_object(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)
        cat12 = SubCategory.objects.create(name='sub12', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id])
        format_str = self.format_str
        self.assertEqual(format_str % (cat1.id, cat11.id), field.from_python((cat1.id, cat11.id)))
        self.assertEqual(format_str % (cat1.id, cat11.id), field.from_python(cat11))
        self.assertEqual(format_str % (cat1.id, cat12.id), field.from_python(cat12))

    def test_clean_empty_required(self):
        field = ProductCategoryField(required=True)
        self.assertFieldValidationError(ProductCategoryField, 'required', field.clean, None)
        self.assertFieldValidationError(ProductCategoryField, 'required', field.clean, "{}")

    def test_clean_empty_not_required(self):
        field = ProductCategoryField(required=False)
        field.clean(None)

    def test_clean_invalid_json(self):
        field = ProductCategoryField(required=False)
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"12","subcategory":"1"')

    def test_clean_invalid_data_type(self):
        field = ProductCategoryField(required=False)
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '"this is a string"')
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, "[]")

    def test_clean_invalid_data(self):
        field = ProductCategoryField(required=False)
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"notanumber","subcategory":"1"}')
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"12","category":"notanumber"}')

    def test_clean_incomplete_data_required(self):
        field = ProductCategoryField()
        self.assertFieldValidationError(ProductCategoryField, 'required', field.clean, '{"category":"1"}')
        self.assertFieldValidationError(ProductCategoryField, 'required', field.clean, '{"category":"12"}')

    #data injection : unallowed category
    def test_clean_unallowed_category(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(name='sub21', description='description', category=cat2)

        field = ProductCategoryField(categories=[cat1.id])
        value = self.format_str % (cat2.id, cat21.id)
        self.assertFieldValidationError(ProductCategoryField, 'categorynotallowed', field.clean, value)

    #data injection : category doesn't exist
    def test_clean_unknown_category(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id, 0])
        value = self.format_str % (0, cat11.id)
        # same error has unallowed, cause unknown category cannot be in list
        self.assertFieldValidationError(ProductCategoryField, 'categorynotallowed', field.clean, value)

    #data injection : subcategory doesn't exist
    def test_clean_unknown_subcategory(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        field = ProductCategoryField(categories=[cat1.id])
        value = self.format_str % (cat1.id, 0)
        self.assertFieldValidationError(ProductCategoryField, 'doesnotexist', field.clean, value)

    #data injection : use incompatible category/subcategory pair
    def test_clean_invalid_category_pair(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(name='sub21', description='description', category=cat2)

        field = ProductCategoryField(categories=[cat1.id, cat2.id])
        value = self.format_str % (cat1.id, cat21.id)
        self.assertFieldValidationError(ProductCategoryField, 'subcategorynotallowed', field.clean, value)

    def test_clean(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id])
        value = self.format_str % (cat1.id, cat11.id);
        self.assertEqual(cat11, field.clean(value))


class _ProductsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'products')

    def _cat_field(self, category, sub_category):
        return '{"category": %s, "subcategory": %s}' % (category.id, sub_category.id)


class ProductTestCase(_ProductsTestCase):
    def test_populate(self):
        self.assertTrue(Category.objects.exists())
        self.assertTrue(SubCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertEqual(200, self.client.get('/products/').status_code)

    def test_ajaxview01(self):
        self.login()

        response = self.client.get('/products/sub_category/0/json')
        self.assertEqual(response.status_code, 404)

        #{'result': [{'text': u'Choose a category', 'id': ''}]}
#        try:
#            content = simplejson.loads(response.content)['result']
#            self.assertEqual(1, len(content))
#
#            dic = content[0]
#            self.assert_(dic['text'])
#            self.failIf(dic['id'])
#        except Exception, e:
#            self.fail(str(e))

        name1 = 'subcat1'
        name2 = 'subcat2'
        cat = Category.objects.create(name='category', description='description')

        create_subcat = SubCategory.objects.create
        subcat1 = create_subcat(name=name1, description='description', category=cat)
        subcat2 = create_subcat(name=name2, description='description', category=cat)

        response = self.client.get('/products/sub_category/%s/json' % cat.id)
        self.assertEqual(200, response.status_code)

        self.assertEqual([[subcat1.id, name1], [subcat2.id, name2]],
                         simplejson.loads(response.content)
                        )

    def test_createview(self):
        self.login()

        self.assertEqual(0, Product.objects.count())

        url = '/products/product/add'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Eva00'
        code = 42
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        description = 'A fake god'
        unit_price = '1.23'
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'code':         code,
                                          'description':  description,
                                          'unit_price':   unit_price,
                                          'unit':         "anything",
                                          'sub_category': self._cat_field(cat, sub_cat)
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        products = Product.objects.all()
        self.assertEqual(1, len(products))

        product = products[0]
        self.assertEqual(name,                product.name)
        self.assertEqual(code,                product.code)
        self.assertEqual(description,         product.description)
        self.assertEqual(Decimal(unit_price), product.unit_price)
        self.assertEqual(cat,                 product.category)
        self.assertEqual(sub_cat,             product.sub_category)

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(response.redirect_chain[0][0].endswith('/products/product/%s' % product.id))

        response = self.client.get('/products/product/%s' % product.id)
        self.assertEqual(response.status_code, 200)

    def test_editview(self):
        self.login()

        name    = 'Eva00'
        code    = 42
        cat     = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(user=self.user, name=name, description='A fake god',
                                         unit_price=Decimal('1.23'), code=code,
                                         category=cat, sub_category=sub_cat
                                        )

        url = '/products/product/edit/%s' % product.id
        self.assertEqual(200, self.client.get(url).status_code)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post(url, follow=True,
                                    data={'user':         self.user.pk,
                                          'name':         name,
                                          'code':         product.code,
                                          'description':  product.description,
                                          'unit_price':   unit_price,
                                          'unit':         "anything",
                                          'sub_category': self._cat_field(product.category,
                                                                          product.sub_category
                                                                         ),
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(name,                product.name)
        self.assertEqual(Decimal(unit_price), product.unit_price)

    def test_listview(self):
        self.login()

        cat     = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]

        create_prod = Product.objects.create
        products = [create_prod(user=self.user, name='Eva00', description='A fake god',
                                unit_price=Decimal('1.23'), code=42,
                                category=cat, sub_category=sub_cat
                               ),
                    create_prod(user=self.user, name='Eva01', description='A fake god',
                                unit_price=Decimal('1.23'), code=43,
                                category=cat, sub_category=sub_cat
                               ),
                   ]

        response = self.client.get('/products/products')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            products_page = response.context['entities']

        self.assertEqual(2, products_page.paginator.count)
        self.assertEqual(set(products), set(products_page.object_list))

    def test_delete_category01(self):
        self.login()

        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)

        response = self.client.post('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertEqual(200, response.status_code)
        self.assertFalse(SubCategory.objects.filter(pk=sub_cat.pk).exists())

    def _build_product_cat_subcat(self):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)
        product = Product.objects.create(user=self.user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'), code=42,
                                         category=cat, sub_category=sub_cat
                                        )

        return product, cat, sub_cat

    def test_delete_category02(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()

        response = self.client.post('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())

        product = self.get_object_or_fail(Product, pk=product.pk)
        self.assertEqual(sub_cat, product.sub_category)

    def test_delete_category03(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()

        response = self.client.post('/creme_config/products/category/delete', data={'id': cat.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

        product = self.get_object_or_fail(Product, pk=product.pk)
        self.assertEqual(sub_cat, product.sub_category)
        self.assertEqual(cat,     product.category)


class ServiceTestCase(_ProductsTestCase):
    def setUp(self):
        self.login()

    def test_createview(self):
        self.assertEqual(0, Service.objects.count())

        url = '/products/service/add'
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)
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

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertTrue(response.redirect_chain[0][0].endswith('/products/service/%s' % service.id))

        response = self.client.get('/products/service/%s' % service.id)
        self.assertEqual(response.status_code, 200)

    def test_editview(self):
        name = 'Eva washing'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(user=self.user, name=name, description='Blabla',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='A wash')

        url = '/products/service/edit/%s' % service.id
        self.assertEqual(200, self.client.get(url).status_code)

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
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        service = self.refresh(service)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_listview(self):
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]

        create_serv = Service.objects.create
        services = [create_serv(user=self.user, name='Eva00', description='description#1',
                                unit_price=Decimal('1.23'), reference='42',
                                category=cat, sub_category=sub_cat, unit='unit'
                               ),
                    create_serv(user=self.user, name='Eva01', description='description#2',
                                unit_price=Decimal('6.58'), reference='43',
                                category=cat, sub_category=sub_cat, unit='unit'
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

    def test_delete_category01(self):
        service, cat, sub_cat = self._build_service_cat_subcat()

        response = self.client.post('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())

        service = self.get_object_or_fail(Service, pk=service.pk)
        self.assertEqual(sub_cat, service.sub_category)

    def test_delete_category02(self):
        service, cat, sub_cat = self._build_service_cat_subcat()

        response = self.client.post('/creme_config/products/category/delete', data={'id': cat.pk})
        self.assertEqual(404, response.status_code)
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

        service = self.get_object_or_fail(Service, pk=service.pk)
        self.assertEqual(sub_cat, service.sub_category)
        self.assertEqual(cat,     service.category)
