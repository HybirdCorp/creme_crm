# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.core.serializers.json import simplejson
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import SetCredentials

    from creme.persons.models import Contact

    from .base import _ProductsTestCase
    from ..models import Category, SubCategory, Product
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


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

        response = self.assertGET200('/products/sub_category/%s/json' % cat.id)
        self.assertEqual([[subcat1.id, name1], [subcat2.id, name2]],
                         simplejson.loads(response.content)
                        )

    def test_createview01(self):
        self.login()

        self.assertEqual(0, Product.objects.count())

        url = '/products/product/add'
        self.assertGET200(url)

        name = 'Eva00'
        code = 42
        sub_cat = SubCategory.objects.all()[0]
        cat = sub_cat.category
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
        self.assertTemplateUsed(response, 'products/block_images.html')

    def test_createview02(self):
        "Images + credentials"
        self.login(is_superuser=False, allowed_apps=['products', 'media_managers'],
                   creatable_models=[Product],
                  )
        user = self.user

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            #EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        img_1 = self.create_image(ident=1, user=user)
        img_2 = self.create_image(ident=2, user=user)
        img_3 = self.create_image(ident=3, user=self.other_user)
        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_3))

        name = 'Eva00'
        sub_cat = SubCategory.objects.all()[0]

        def post(*images):
            return self.client.post('/products/product/add', follow=True,
                                    data={'user':       user.pk,
                                          'name':         name,
                                          'code':         42,
                                          'description':  'A fake god',
                                          'unit_price':   '1.23',
                                          'unit':         "anything",
                                          'sub_category': self._cat_field(sub_cat.category, sub_cat),
                                          'images':       '[%s]' % ','.join(str(img.id) for img in images),
                                        }
                                    )

        response = post(img_1, img_3)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'images', _(u"Some entities are not linkable: %s") % img_3)

        response = post(img_1, img_2)
        self.assertNoFormError(response)

        product = self.get_object_or_fail(Product, name=name)
        self.assertEqual({img_1, img_2}, set(product.images.all()))

    def test_editview(self):
        self.login()

        name    = 'Eva00'
        code    = 42
        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(user=self.user, name=name, description='A fake god',
                                         unit_price=Decimal('1.23'), code=code,
                                         category=sub_cat.category, sub_category=sub_cat
                                        )
        url = product.get_edit_absolute_url()
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('images', fields)

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

        response = self.assertGET200('/products/products')

        with self.assertNoException():
            products_page = response.context['entities']

        self.assertEqual(2, products_page.paginator.count)
        self.assertEqual(set(products), set(products_page.object_list))

    def test_delete_category01(self):
        self.login()

        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)

        self.assertPOST200('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertDoesNotExist(sub_cat)

    def _build_product_cat_subcat(self):
        cat = Category.objects.create(name='Mecha', description='Mechanical devices')
        sub_cat = SubCategory.objects.create(name='Eva', description='Fake gods', category=cat)
        product = Product.objects.create(user=self.user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'), code=42,
                                         category=cat, sub_category=sub_cat,
                                        )

        return product, cat, sub_cat

    def test_delete_category02(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()

        self.assertPOST404('/creme_config/products/subcategory/delete', data={'id': sub_cat.pk})
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())

        product = self.assertStillExists(product)
        self.assertEqual(sub_cat, product.sub_category)

    def test_delete_category03(self):
        self.login()

        product, cat, sub_cat = self._build_product_cat_subcat()

        self.assertPOST404('/creme_config/products/category/delete', data={'id': cat.pk})
        self.assertTrue(SubCategory.objects.filter(pk=sub_cat.pk).exists())
        self.assertTrue(Category.objects.filter(pk=cat.pk).exists())

        product = self.assertStillExists(product)
        self.assertEqual(sub_cat, product.sub_category)
        self.assertEqual(cat,     product.category)

    def test_add_images(self):
        #TODO: factorise
        self.login(is_superuser=False, allowed_apps=['products', 'media_managers'],
                   creatable_models=[Product],
                  )
        user = self.user

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            #EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        img_1 = self.create_image(ident=1, user=user)
        img_2 = self.create_image(ident=2, user=user)
        img_3 = self.create_image(ident=3, user=user)
        img_4 = self.create_image(ident=4, user=self.other_user)
        self.assertTrue(user.has_perm_to_link(img_1))
        self.assertFalse(user.has_perm_to_link(img_4))

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(user=self.user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'), code=42,
                                         category=sub_cat.category,
                                         sub_category=sub_cat,
                                        )
        product.images = [img_3]

        url = '/products/product/%s/add_images' % product.id
        self.assertGET200(url)

        def post(*images):
            return self.client.post(url, follow=True,
                                    data={'images': '[%s]' % ','.join(str(img.id) for img in images)}
                                   )

        response = post(img_1, img_4)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'images', _(u"Some entities are not linkable: %s") % img_4)

        response = post(img_1, img_2)
        self.assertNoFormError(response)
        self.assertEqual({img_1, img_2, img_3}, set(product.images.all()))

        #------------
        img_5 = self.create_image(ident=5, user=user)
        response = post(img_1, img_5)
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'images', _("This entity doesn't exist.")) 

    def test_remove_image(self):
        self.login()
        user = self.user

        img_1 = self.create_image(ident=1, user=user)
        img_2 = self.create_image(ident=2, user=user)

        sub_cat = SubCategory.objects.all()[0]
        product = Product.objects.create(user=self.user, name='Eva00', description='A fake god',
                                         unit_price=Decimal('1.23'), code=42,
                                         category=sub_cat.category,
                                         sub_category=sub_cat,
                                        )
        product.images = [img_1, img_2]

        url = '/products/images/remove/%s' % product.id
        data = {'id': img_1.id}
        self.assertGET404(url, data=data)

        self.assertPOST200(url, data=data, follow=True)
        self.assertEqual([img_2], list(product.images.all()))

        rei = Contact.objects.create(user=user, first_name='Rei', last_name='Aynami')
        self.assertPOST404('/products/images/remove/%s' % rei.id, data={'id': img_2.id})
