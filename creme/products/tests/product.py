# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.core.serializers.json import simplejson

    from creme.products.tests.base import _ProductsTestCase
    from creme.products.models import Category, SubCategory, Product
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ProductTestCase',)


class ProductTestCase(_ProductsTestCase):
    def test_populate(self):
        self.assertTrue(Category.objects.exists())
        self.assertTrue(SubCategory.objects.exists())

    def test_portal(self):
        self.login()
        self.assertGET200('/products/')

    def test_ajaxview01(self):
        self.login()

        self.assertGET404('/products/sub_category/0/json')

        name1 = 'subcat1'
        name2 = 'subcat2'
        cat = Category.objects.create(name='category', description='description')

        create_subcat = partial(SubCategory.objects.create, category=cat)
        subcat1 = create_subcat(name=name1, description='description')
        subcat2 = create_subcat(name=name2, description='description')

        response = self.client.get('/products/sub_category/%s/json' % cat.id)
        self.assertEqual(200, response.status_code)

        self.assertEqual([[subcat1.id, name1], [subcat2.id, name2]],
                         simplejson.loads(response.content)
                        )

    def test_createview(self):
        self.login()

        self.assertEqual(0, Product.objects.count())

        url = '/products/product/add'
        self.assertGET200(url)

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

        self.assertRedirects(response, product.get_absolute_url())

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
        self.assertGET200(url)

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
        self.assertNoFormError(response)

        product = self.refresh(product)
        self.assertEqual(name,                product.name)
        self.assertEqual(Decimal(unit_price), product.unit_price)

    def test_listview(self):
        self.login()

        cat = Category.objects.all()[0]
        create_prod = partial(Product.objects.create, user=self.user, 
                              description='A fake god', unit_price=Decimal('1.23'),
                              category=cat, sub_category=SubCategory.objects.all()[0],
                             )
        products = [create_prod(name='Eva00', code=42),
                    create_prod(name='Eva01', code=43),
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

        self.assertPOST200('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
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

        self.assertPOST404('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())

        product = self.get_object_or_fail(Product, pk=product.pk)
        self.assertEqual(sub_cat, product.sub_category)

    def test_delete_category03(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()

        self.assertPOST404('/creme_config/products/category/delete', data={'id': cat.pk})
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

        product = self.get_object_or_fail(Product, pk=product.pk)
        self.assertEqual(sub_cat, product.sub_category)
        self.assertEqual(cat,     product.category)
