# -*- coding: utf-8 -*-

from decimal import Decimal

from django.test import TestCase
from django.core.serializers.json import simplejson
from django.contrib.auth.models import User

from creme_core.management.commands.creme_populate import Command as PopulateCommand

from products.models import *


class ProductsTestCase(TestCase):
    def login(self):
        if not self.user:
            user = User.objects.create(username='user01')
            user.set_password(self.password)
            user.is_superuser = True
            user.save()
            self.user = user

        logged = self.client.login(username=self.user.username, password=self.password)
        self.assert_(logged, 'Not logged in')

    def setUp(self):
        PopulateCommand().handle(application=['creme_core', 'products'])
        self.password = 'test'
        self.user = None

    def test_populate(self):
        self.assert_(ServiceCategory.objects.exists())
        self.assert_(Category.objects.exists())
        self.assert_(SubCategory.objects.exists())

    def test_portal(self):
        self.login()
        response = self.client.get('/products/')
        self.assertEqual(200, response.status_code)

    def test_ajaxview01(self):
        self.login()

        response = self.client.post('/products/sub_category/load')
        self.assertEqual(response.status_code, 200)

        #{'result': [{'text': u'Choose a category', 'id': ''}]}
        try:
            content = simplejson.loads(response.content)['result']
            self.assertEqual(1, len(content))

            dic = content[0]
            self.assert_(dic['text'])
            self.failIf(dic['id'])
        except Exception, e:
            self.fail(str(e))

        name1 = 'subcat1'
        name2 = 'subcat2'
        cat = Category.objects.create(name='category', description='description')
        subcat1 = SubCategory.objects.create(name=name1, description='description', category=cat)
        subcat2 = SubCategory.objects.create(name=name2, description='description', category=cat)

        response = self.client.post('/products/sub_category/load', data={'record_id': cat.id})
        self.assertEqual(200, response.status_code)

        #{'result': [{'text': 'subcat1', 'id': 8}, {'text': 'subcat2', 'id': 9}]}
        try:
            content = simplejson.loads(response.content)['result']
            self.assertEqual(2, len(content))
            dic = content[0]
            self.assertEqual(name1,      dic['text'])
            self.assertEqual(subcat1.id, dic['id'])

            dic = content[1]
            self.assertEqual(name2,      dic['text'])
            self.assertEqual(subcat2.id, dic['id'])
        except Exception, e:
            self.fail(str(e))

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
                                            'category':     cat.id,
                                            'sub_category': sub_cat.id,
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            print 'Exception', e
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
                                            'category':     product.category_id,
                                            'sub_category': product.sub_category_id,
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
        cat = ServiceCategory.objects.all()[0]
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
                                            'category':     cat.id,
                                         }
                                   )
        try:
            form = response.context['form']
        except Exception, e:
            print 'Exception', e
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

        self.assertEqual(200, response.status_code)
        self.assert_(response.redirect_chain)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assert_(response.redirect_chain[0][0].endswith('/products/service/%s' % service.id))

        response = self.client.get('/products/service/%s' % service.id)
        self.assertEqual(response.status_code, 200)

    def test_service_editview(self):
        self.login()

        name = 'Eva washing'
        cat  = ServiceCategory.objects.all()[0]
        service = Service.objects.create(user=self.user, name=name, description='Blabla',
                                         unit_price=Decimal('1.23'), reference='42',
                                         category=cat, unit='A wash')

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
                                            'category':     service.category_id,
                                            'unit':         service.unit,
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
        except Exception, e:
            print 'Exception', e
        else:
            self.fail(form.errors)

        service = Service.objects.get(pk=service.id)
        self.assertEqual(name,                service.name)
        self.assertEqual(Decimal(unit_price), service.unit_price)

    def test_service_listview(self):
        self.login()

        cat = ServiceCategory.objects.all()[0]

        create_serv = Service.objects.create
        serv01 = create_serv(user=self.user, name='Eva00', description='description#1',
                            unit_price=Decimal('1.23'), reference='42',
                            category=cat, unit='unit')
        serv02 = create_serv(user=self.user, name='Eva01', description='description#2',
                            unit_price=Decimal('6.58'), reference='43',
                            category=cat, unit='unit')

        response = self.client.get('/products/services')
        self.assertEqual(200, response.status_code)

        try:
            services_page = response.context['entities']
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(2, services_page.paginator.count)
        self.assertEqual(set([serv01.id, serv02.id]), set([s.id for s in services_page.object_list]))

