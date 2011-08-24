# -*- coding: utf-8 -*-

from decimal import Decimal

from django.core.serializers.json import simplejson

from creme_core import autodiscover
from creme_core.tests.base import CremeTestCase
from creme_core.tests.forms import FieldTestCase

from products.models import Category, SubCategory, Product, Service
from products.forms.product import ProductCategoryField

class ProductCategoryFieldTestCase(FieldTestCase):
    def test_categories(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat2 = Category.objects.create(name='cat2', description='description')

        field = ProductCategoryField(categories=[cat1.id, cat2.id])
        self.assertEquals(2, len(field.categories))
        self.assertEquals(cat1, field._get_categories_objects()[0])
        self.assertEquals(cat2, field._get_categories_objects()[1])

    def test_default_ctypes(self):
        autodiscover()
        self.populate('creme_core', 'products')

        field = ProductCategoryField()
        self.assertEquals(len(Category.objects.all()), len(field._get_categories_objects()))
        self.assertEquals(set(c.pk for c in Category.objects.all()), set(c.pk for c in field._get_categories_objects()))

    def test_format_object(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)
        cat12 = SubCategory.objects.create(name='sub12', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id])
        self.assertEquals('{"category": %s, "subcategory": %s}' % (cat1.id, cat11.id), field.from_python((cat1.id, cat11.id)))
        self.assertEquals('{"category": %s, "subcategory": %s}' % (cat1.id, cat11.id), field.from_python(cat11))
        self.assertEquals('{"category": %s, "subcategory": %s}' % (cat1.id, cat12.id), field.from_python(cat12))

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
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"1"}')
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"12"}')
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"notanumber","subcategory":"1"}')
        self.assertFieldValidationError(ProductCategoryField, 'invalidformat', field.clean, '{"category":"12","category":"notanumber"}')

    # data injection : unallowed category
    def test_clean_unallowed_category(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(name='sub21', description='description', category=cat2)

        field = ProductCategoryField(categories=[cat1.id])

        value = '{"category":"%s","subcategory":"%s"}' % (cat2.id, cat21.id)

        self.assertFieldValidationError(ProductCategoryField, 'categorynotallowed', field.clean, value)

    # data injection : category doesn't exist
    def test_clean_unknown_category(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id, 0])

        value = '{"category":"%s","subcategory":"%s"}' % (0, cat11.id)

        # same error has unallowed, cause unknown category cannot be in list
        self.assertFieldValidationError(ProductCategoryField, 'categorynotallowed', field.clean, value)

    # data injection : subcategory doesn't exist
    def test_clean_unknown_subcategory(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        field = ProductCategoryField(categories=[cat1.id])

        value = '{"category":"%s","subcategory":"%s"}' % (cat1.id, 0)

        self.assertFieldValidationError(ProductCategoryField, 'doesnotexist', field.clean, value)

    # data injection : use incompatible category/subcategory pair
    def test_clean_invalid_category_pair(self):
        cat1 = Category.objects.create(name='cat1', description='description')

        cat2 = Category.objects.create(name='cat2', description='description')
        cat21 = SubCategory.objects.create(name='sub21', description='description', category=cat2)

        field = ProductCategoryField(categories=[cat1.id, cat2.id])

        value = '{"category":"%s","subcategory":"%s"}' % (cat1.id, cat21.id)

        self.assertFieldValidationError(ProductCategoryField, 'subcategorynotallowed', field.clean, value)

    def test_clean(self):
        cat1 = Category.objects.create(name='cat1', description='description')
        cat11 = SubCategory.objects.create(name='sub11', description='description', category=cat1)

        field = ProductCategoryField(categories=[cat1.id])

        value = '{"category":"%s","subcategory":"%s"}' % (cat1.id, cat11.id);

        self.assertEquals(cat11, field.clean(value))

class ProductsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'products')

    def test_populate(self):
        self.assert_(Category.objects.exists())
        self.assert_(SubCategory.objects.exists())

    def test_portal(self):
        self.login()
        response = self.client.get('/products/')
        self.assertEqual(200, response.status_code)

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
        subcat1 = SubCategory.objects.create(name=name1, description='description', category=cat)
        subcat2 = SubCategory.objects.create(name=name2, description='description', category=cat)

        response = self.client.get('/products/sub_category/%s/json' % cat.id)
        self.assertEqual(200, response.status_code)

        content = simplejson.loads(response.content)

        self.assertEqual(content, [[subcat1.id, name1],
                                   [subcat2.id, name2]])

    def test_product_createview(self):
        self.login()

        self.assertEqual(0, Product.objects.count())

        response = self.client.get('/products/product/add')
        self.assertEqual(200, response.status_code)

        name = 'Eva00'
        code = 42
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        description = 'A fake god'
        unit_price = '1.23'
        response = self.client.post('/products/product/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'code':         code,
                                            'description':  description,
                                            'unit_price':   unit_price,
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id,
                                                                                                       sub_cat.id)
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            #print 'Exception', e
            pass
        else:
            self.fail(form.errors)

        products = Product.objects.all()
        self.assertEqual(1, len(products))

        product = products[0]
        self.assertEqual(name,                product.name)
        self.assertEqual(code,                product.code)
        self.assertEqual(description,         product.description)
        self.assertEqual(Decimal(unit_price), product.unit_price)
        self.assertEqual(cat.id,              product.category_id)
        self.assertEqual(sub_cat.id,          product.sub_category_id)

        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/products/product/%s' % product.id))

        response = self.client.get('/products/product/%s' % product.id)
        self.assertEqual(response.status_code, 200)

    def test_product_editview(self):
        self.login()

        name    = 'Eva00'
        code    = 42
        cat     = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(user=self.user, name=name, description='A fake god',
                                         unit_price=Decimal('1.23'), code=code,
                                         category=cat, sub_category=sub_cat)

        response = self.client.get('/products/product/edit/%s' % product.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post('/products/product/edit/%s' % product.id, follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'code':         product.code,
                                            'description':  product.description,
                                            'unit_price':   unit_price,
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (product.category_id,
                                                                                                       product.sub_category_id)
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        product = Product.objects.get(pk=product.id)
        self.assertEqual(name,                product.name)
        self.assertEqual(Decimal(unit_price), product.unit_price)

    def test_product_listview(self):
        self.login()

        cat     = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]

        create_prod = Product.objects.create
        eva00 = create_prod(user=self.user, name='Eva00', description='A fake god',
                            unit_price=Decimal('1.23'), code=42,
                            category=cat, sub_category=sub_cat)
        eva01 = create_prod(user=self.user, name='Eva01', description='A fake god',
                            unit_price=Decimal('1.23'), code=43,
                            category=cat, sub_category=sub_cat)

        response = self.client.get('/products/products')
        self.assertEqual(200, response.status_code)

        try:
            products_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(2, products_page.paginator.count)
        self.assertEqual(set([eva00.id, eva01.id]), set([p.id for p in products_page.object_list]))

    def test_service_createview(self):
        self.login()

        self.assertEqual(0, Service.objects.count())

        response = self.client.get('/products/product/add')
        self.assertEqual(200, response.status_code)

        name = 'Eva washing'
        description = 'Your Eva is washed by pretty girls'
        reference = '42'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        unit = 'A wash'
        unit_price = '1.23'
        response = self.client.post('/products/service/add', follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'reference':    reference,
                                            'description':  description,
                                            'unit':         unit,
                                            'unit_price':   unit_price,
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id,
                                                                                                       sub_cat.id)
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            #print 'Exception', e
            pass
        else:
            self.fail(form.errors)

        services = Service.objects.all()
        self.assertEqual(1, len(services))

        service = services[0]
        self.assertEqual(name,                service.name)
        self.assertEqual(reference,           service.reference)
        self.assertEqual(description,         service.description)
        self.assertEqual(unit,                service.unit)
        self.assertEqual(Decimal(unit_price), service.unit_price)
        self.assertEqual(cat.id,              service.category_id)
        self.assertEqual(sub_cat.id,          service.sub_category_id)

        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/products/service/%s' % service.id))

        response = self.client.get('/products/service/%s' % service.id)
        self.assertEqual(response.status_code, 200)

    def test_service_editview(self):
        self.login()

        name = 'Eva washing'
        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]
        service = Service.objects.create(user=self.user, name=name, description='Blabla',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, sub_category=sub_cat, unit='A wash')

        response = self.client.get('/products/service/edit/%s' % service.id)
        self.assertEqual(200, response.status_code)

        name += '_edited'
        unit_price = '4.53'
        response = self.client.post('/products/service/edit/%s' % service.id, follow=True,
                                    data={
                                            'user':         self.user.pk,
                                            'name':         name,
                                            'reference':    service.reference,
                                            'description':  service.description,
                                            'unit_price':   unit_price,
                                            'sub_category': """{"category":%s, "subcategory":%s}""" % (service.category_id,
                                                                                                       service.sub_category_id),
                                            'unit':         service.unit,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            #print 'Exception', e
            pass
        else:
            self.fail(form.errors)

        service = Service.objects.get(pk=service.id)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_service_listview(self):
        self.login()

        cat = Category.objects.all()[0]
        sub_cat = SubCategory.objects.all()[0]

        create_serv = Service.objects.create
        serv01 = create_serv(user=self.user, name='Eva00', description='description#1',
                            unit_price=Decimal('1.23'), reference='42',
                            category=cat, sub_category=sub_cat, unit='unit')
        serv02 = create_serv(user=self.user, name='Eva01', description='description#2',
                            unit_price=Decimal('6.58'), reference='43',
                            category=cat, sub_category=sub_cat, unit='unit')

        response = self.client.get('/products/services')
        self.assertEqual(200, response.status_code)

        try:
            services_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(2, services_page.paginator.count)
        self.assertEqual(set([serv01.id, serv02.id]), set([s.id for s in services_page.object_list]))
