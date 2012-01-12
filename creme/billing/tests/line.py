# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    #from creme_core import autodiscover
    from creme_core.models import Relation, SetCredentials
    from creme_core.tests.base import CremeTestCase

    from persons.models import Contact, Organisation

    from products.models import Product, Service, Category, SubCategory

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error:', e


__all__ = ('LineTestCase',)


class LineTestCase(_BillingTestCase, CremeTestCase):
    def test_add_product_lines01(self):
        self.login()

        #simpler to test with 2 super users (do not have to create SetCredentials etc...)
        other_user = self.other_user
        other_user.superuser = True
        other_user.save()

        invoice  = self.create_invoice_n_orgas('Invoice001', user=other_user)[0]
        url = '/billing/%s/product_line/add' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.0')
        product = self.create_product(unit_price=unit_price) 
        response = self.client.post(url, data={'related_item':  product.id,
                                               'comment':       'no comment !',
                                               'quantity':      1,
                                               'unit_price':    unit_price,
                                               'discount':      Decimal(),
                                               'discount_unit': 1,
                                               'vat_value':     Vat.objects.get(value='0.0').id,
#                                               'credit':       Decimal(),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(other_user, line.user)
        self.assertEqual(product,    line.related_item)
        self.assertEqual(unit_price, line.unit_price)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line)
        self.assertRelationCount(1, line,    REL_SUB_LINE_RELATED_ITEM, product)

        self.assertEqual(unit_price, invoice.get_total())
        self.assertEqual(unit_price, invoice.get_total_with_tax())

    def test_add_product_lines02(self): #on-the-fly
        self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/product_line/add_on_the_fly' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.0')
        name = 'Awesomo'
        response = self.client.post(url, data={'on_the_fly_item': name,
                                               'comment':         'no comment !',
                                               'quantity':        1,
                                               'unit_price':      unit_price,
                                               'discount':        Decimal(),
                                               'discount_unit':   1,
                                               'vat_value':       Vat.objects.get(value='0.0').id,
#                                               'credit':          Decimal(),
                                             }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(name, line.on_the_fly_item)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, line)
        self.assertEqual(0, Relation.objects.filter(subject_entity=line, type=REL_SUB_LINE_RELATED_ITEM).count())

        self.assertEqual(unit_price, invoice.get_total())
        self.assertEqual(unit_price, invoice.get_total_with_tax())

    def test_add_product_lines03(self): #on-the-fly + product creation
        self.login()

        self.assertEqual(0, Product.objects.count())

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('1.0')
        name    = 'Awesomo'
        cat, subcat = self.create_cat_n_subcat()
        response = self.client.post('/billing/%s/product_line/add_on_the_fly' % invoice.id,
                                    data={'on_the_fly_item':    name,
                                          'comment':            'no comment !',
                                          'quantity':           1,
                                          'unit_price':         unit_price,
                                          'discount':           Decimal(),
                                          'discount_unit':      1,
                                          'vat_value':          Vat.objects.get(value='0.0').id,
#                                          'credit':             Decimal(),
                                          'has_to_register_as': 'on',
                                          'sub_category':       '{"category":%s, "subcategory":%s}' % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        product = self.get_object_or_fail(Product, name=name)
        self.assertEqual(cat,        product.category)
        self.assertEqual(subcat,     product.sub_category)
        self.assertEqual(unit_price, product.unit_price)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertFalse(line.on_the_fly_item)
        self.assertEqual(product, line.related_item)

    def test_add_product_lines04(self): #on-the-fly + product creation + no creation creds
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Contact, Organisation] #not 'Product'
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat    = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.client.post('/billing/%s/product_line/add_on_the_fly' % invoice.id,
                                    data={'on_the_fly_item':     'Awesomo',
                                          'comment':             'no comment !',
                                          'quantity':            1,
                                          'unit_price':          Decimal('1.0'),
                                          'discount':            Decimal(),
                                          'discount_unit':       1,
                                          'vat_value':           Vat.objects.get(value='0.0').id,
#                                          'credit':              Decimal(),
                                          'has_to_register_as':  'on',
                                          'category':            cat.id,
                                          'sub_category':        subcat.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'has_to_register_as', [_(u'You are not allowed to create Products')])
        self.assertFalse(invoice.product_lines)
        self.assertFalse(Product.objects.exists())

    def test_delete_product_line01(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')

        response = self.client.post('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertFalse(self.refresh(invoice).product_lines)
        self.assertFalse(ProductLine.objects.exists())

# commented on 19/11/2011 Edit line using this way is no longer possible
#    def test_invoice_edit_product_lines01(self):
##        self.populate('creme_core', 'persons')
#        self.login()
#
#        name = 'Stuff'
#        unit_price = Decimal('42.0')
#        quantity = 1
#        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
#        line = ProductLine.objects.create(on_the_fly_item=name, quantity=quantity,
#                                          unit_price=unit_price, user=self.user,
#                                         )
#        line.related_document = invoice
#
#        url = '/billing/productline/%s/edit' % line.id
#        self.assertEqual(200, self.client.get(url).status_code)
#
#        name += '_edited'
#        unit_price += Decimal('1.0')
#        quantity *= 2
#        response = self.client.post(url, data={
#                                                #'user':            self.user.pk,
#                                                'on_the_fly_item': name,
#                                                'comment':         'no comment !',
#                                                'quantity':        quantity,
#                                                'unit_price':      unit_price,
#                                                'discount':        Decimal(),
#                                                'discount_unit':   1,
#                                                'vat_value':       Vat.objects.get(value='0.0').id,
##                                                'credit':          Decimal(),
#                                              }
#                                   )
#        self.assertNoFormError(response)
#        self.assertEqual(200, response.status_code)
#
#        line = self.refresh(line)
#        self.assertEqual(name,       line.on_the_fly_item)
#        self.assertEqual(unit_price, line.unit_price)
#        self.assertEqual(quantity,   line.quantity)

    def test_add_service_lines01(self):
        self.login()
        self.populate('products')

        #simpler to test with 2 super users (do not have to create SetCredentials etc...)
        other_user = self.other_user
        other_user.superuser = True
        other_user.save()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        url = '/billing/%s/service_line/add' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)
        self.assertFalse(invoice.service_lines)

        unit_price = Decimal('1.33')
        service = self.create_service()
        vat = Vat.objects.get_or_create(value=Decimal('19.60'))[0]
        response = self.client.post(url, data={'related_item': service.id,
                                               'comment':      'no comment !',
                                               'quantity':     2,
                                               'unit_price':   unit_price,
                                               'discount':     Decimal(),
                                               'discount_unit':1,
                                               #'vat_value':    Vat.get_default_vat().id,
                                               'vat_value':    vat.id,
#                                               'credit':       Decimal(),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        invoice = self.refresh(invoice) #refresh lines cache
        self.assertEqual(1, len(invoice.service_lines))

        line = invoice.service_lines[0]
        self.assertEqual(self.other_user, line.user)
        self.assertEqual(service,         line.related_item)
        self.assertEqual(unit_price,      line.unit_price)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line)
        self.assertRelationCount(1, line,    REL_SUB_LINE_RELATED_ITEM, service)

        self.assertEqual(Decimal('2.66'), invoice.get_total()) # 2 * 1.33
        self.assertEqual(Decimal('3.19'), invoice.get_total_with_tax()) #2.66 * 1.196 == 3.18136

    def test_add_service_lines02(self): #on-the-fly
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/service_line/add_on_the_fly' % invoice.id
        self.assertEqual(200, self.client.get(url).status_code)

        unit_price = Decimal('1.33')
        name = 'Car wash'
        response = self.client.post(url, data={'on_the_fly_item': name,
                                               'comment':         'no comment !',
                                               'quantity':        2,
                                               'unit_price':      unit_price,
                                               'discount':        Decimal(),
                                               'discount_unit':   1,
                                               'vat_value':       Vat.objects.get(value='0.0').id,
#                                               'credit':          Decimal(),
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        invoice = self.refresh(invoice) #refresh lines cache
        lines = invoice.service_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(name, line.on_the_fly_item)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, line)
        self.assertEqual(0, Relation.objects.filter(subject_entity=line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_add_service_lines03(self): #on-the-fly + Service creation
        self.login()

        self.assertEqual(0, Service.objects.count())

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        unit_price = Decimal('1.33')
        name = 'Car wash'
        cat     = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat  = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.client.post('/billing/%s/service_line/add_on_the_fly' % invoice.id,
                                    data={'on_the_fly_item':    name,
                                          'comment':            'no comment !',
                                          'quantity':           2,
                                          'unit_price':         unit_price,
                                          'discount':           Decimal(),
                                          'discount_unit':      1,
                                          'vat_value':          Vat.get_default_vat().id,
#                                          'credit':             Decimal(),
                                          'has_to_register_as': 'on',
                                          'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        service = self.get_object_or_fail(Service, name=name)

        self.assertEqual(cat,        service.category)
        self.assertEqual(subcat,     service.sub_category)
        self.assertEqual(unit_price, service.unit_price)

        invoice = self.refresh(invoice) #refresh lines cache
        lines = invoice.service_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertFalse(line.on_the_fly_item)
        self.assertEqual(service, line.related_item)

    def test_add_service_lines04(self): #on-the-fly + service creation + no creation creds
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Contact, Organisation], #not 'Service'
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW   | SetCredentials.CRED_CHANGE | \
                                            SetCredentials.CRED_DELETE | SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat, subcat = self.create_cat_n_subcat()
        response = self.client.post('/billing/%s/service_line/add_on_the_fly' % invoice.id,
                                    data={'on_the_fly_item':    'Car wash',
                                          'comment':            'no comment !',
                                          'quantity':           2,
                                          'unit_price':         Decimal('1.33'),
                                          'discount':           Decimal(),
                                          'discount_unit':      1,
                                          'vat_value':          Vat.objects.get(value='0.0').id,
#                                          'credit':             Decimal(),
                                          'has_to_register_as': 'on',
                                          'sub_category':       '{"category": %s, "subcategory": %s}' % (cat.id, subcat.id)
                                         }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertFormError(response, 'form', 'has_to_register_as', [_(u'You are not allowed to create Services')])
        self.assertFalse(invoice.service_lines)
        self.assertFalse(Service.objects.exists())

# commented on 19/11/2011 Edit line using this way is no longer possible
#    def test_invoice_edit_service_lines01(self):
#        self.login()
#
#        name = 'Stuff'
#        unit_price = Decimal('42.0')
#        quantity = 1
#        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
#        line = ServiceLine.objects.create(on_the_fly_item=name, quantity=quantity,
#                                          unit_price=unit_price, user=self.user,
#                                         )
#        line.related_document = invoice
#
#        url = '/billing/serviceline/%s/edit' % line.id
#        self.assertEqual(200, self.client.get(url).status_code)
#
#        name += '_edited'
#        unit_price += Decimal('1.0')
#        quantity *= 2
#        response = self.client.post(url, data={
#                                                #'user':            self.user.pk,
#                                                'on_the_fly_item': name,
#                                                'comment':         'no comment !',
#                                                'quantity':        quantity,
#                                                'unit_price':      unit_price,
#                                                'discount':        Decimal(),
#                                                'discount_unit':   1,
#                                                'vat_value':       Vat.objects.get(value='0.0').id,
##                                                'credit':          Decimal(),
#                                              }
#                                   )
#        self.assertNoFormError(response)
#        self.assertEqual(200, response.status_code)
#
#        line = self.refresh(line)
#        self.assertEqual(name,       line.on_the_fly_item)
#        self.assertEqual(unit_price, line.unit_price)
#        self.assertEqual(quantity,   line.quantity)

    def test_related_document01(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')
        self.assertEqual(invoice, product_line.related_document)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, product_line)

    def test_related_item01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product = self.create_product()

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, related_item=product)
        self.assertEqual(product, product_line.related_item)
        self.assertRelationCount(1, product_line, REL_SUB_LINE_RELATED_ITEM, product)

    def test_related_item02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')
        self.assertIsNone(product_line.related_item)

    def test_product_line_clone(self):
        self.login()

        product = self.create_product()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, related_item=product)
        product_line2 = product_line.clone(invoice2)

        product_line2 = self.refresh(product_line2)
        self.assertEqual(invoice2, product_line2.related_document)
        self.assertEqual(product, product_line2.related_item)

        rel_filter = Relation.objects.filter
        self.assertEqual([product_line2.pk],
                         list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True))
                        )
        self.assertEqual(set([product_line.pk, product_line2.pk]),
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=product).values_list('subject_entity', flat=True))
                        )

    def test_service_line_clone(self):
        self.login()

        service = self.create_service()
        invoice1 = self.create_invoice_n_orgas('Invoice001')[0]
        invoice2 = self.create_invoice_n_orgas('Invoice002')[0]

        service_line1 = ServiceLine.objects.create(user=self.user, related_document=invoice1, related_item=service)

        service_line2 = service_line1.clone(invoice2)
        service_line2 = self.refresh(service_line2)
        self.assertEqual(invoice2, service_line2.related_document)
        self.assertEqual(service, service_line2.related_item)
        self.assertNotEqual(service_line, service_line2)

        rel_filter = Relation.objects.filter
        self.assertEqual([service_line1.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice1).values_list('object_entity', flat=True)))
        self.assertEqual([service_line2.pk], list(rel_filter(type=REL_SUB_HAS_LINE, subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual(set([service_line1.pk, service_line2.pk]),
                         set(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=service).values_list('subject_entity', flat=True))
                        )

    def test_get_verbose_type(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        pl = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item="otf1", unit_price=Decimal("1"))
        verbose_type = _(u"Product")
        self.assertEqual(verbose_type, unicode(pl.get_verbose_type()))

        funf = pl.function_fields.get('get_verbose_type')
        self.assertIsNotNone(funf)
        self.assertEqual(verbose_type, funf(pl).for_html())

        sl = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item="otf2", unit_price=Decimal("4"))
        verbose_type = _(u"Service")
        self.assertEqual(verbose_type, unicode(sl.get_verbose_type()))
        self.assertEqual(verbose_type, sl.function_fields.get('get_verbose_type')(sl).for_html())

    def test_discount_rules(self):
        is_valid = Line.is_discount_valid

        self.assertFalse(is_valid(100, 1, 150, PERCENT_PK, True))
        self.assertFalse(is_valid(100, 1, 101, AMOUNT_PK,  True))
        self.assertFalse(is_valid(100, 2, 201, AMOUNT_PK,  True))
        self.assertFalse(is_valid(100, 1, 101, AMOUNT_PK,  False))
        self.assertFalse(is_valid(100, 4, 101, AMOUNT_PK,  False))

        self.assertTrue(is_valid(100, 2.1, 95.8, PERCENT_PK, False))
        self.assertTrue(is_valid(100, 2,   101,  AMOUNT_PK,  True))
        self.assertTrue(is_valid(100, 2,   99,   AMOUNT_PK,  False))
        self.assertTrue(is_valid(20,  20,  399,  AMOUNT_PK,  True))

    def test_inline_edit(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        pl = ProductLine.objects.create(user=self.user, unit_price=Decimal("10"),
                                        vat_value=Vat.get_default_vat(),
                                        related_document=invoice, on_the_fly_item='Flyyyyy',
                                       )

        self.assertEqual(DEFAULT_VAT, pl.vat_value.value)
        self.assertEqual(Decimal('0'), pl.discount)
        self.assertFalse(pl.total_discount)

        null_vat = Vat.objects.get(value=0)
        response = self.client.post('/billing/line/%s/update' % pl.id, follow=True,
                                    data={'unit_price':       20,
                                          'quantity':         20,
                                          'discount':         10,
                                          'discount_unit':    AMOUNT_PK,
                                          'total_discount':   '2',
                                          'vat':              null_vat.id,
                                         }
                                   )
        self.assertEqual(200, response.status_code, response.content)
        self.assertNoFormError(response)

        pl = self.refresh(pl)
        invoice = self.refresh(invoice)

        self.assertTrue(Line.is_discount_valid(20, 20, 10, AMOUNT_PK, False))

        self.assertEqual(Decimal('20'),  pl.unit_price)
        self.assertEqual(Decimal('20'),  pl.quantity)
        self.assertEqual(null_vat,       pl.vat_value)
        self.assertEqual(Decimal('200'), invoice.get_total())
        self.assertEqual(Decimal('200'), invoice.get_total_with_tax())
        self.assertEqual(Decimal('200'), invoice.total_no_vat)
        self.assertEqual(Decimal('200'), invoice.total_vat)

    def test_multiple_delete01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        user = self.user
        create_line = ProductLine.objects.create
        ids = tuple(create_line(user=user, related_document=invoice,
                                on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        invoice.save() # updates totals

        self.assertEqual(2, len(invoice.product_lines))
        expected_total = Decimal('30')
        self.assertEqual(expected_total, invoice.get_total())
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.get_total_with_tax())
        self.assertEqual(expected_total, invoice.total_vat)

        response = self.client.post('/creme_core/delete_js', follow=True, data={'ids': '%s,%s' % ids})
        self.assertEqual(200, response.status_code, response.content)
        self.assertFalse(ProductLine.objects.filter(pk__in=ids))

        invoice = self.refresh(invoice)
        self.assertFalse(invoice.product_lines)

        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.get_total())
        self.assertEqual(expected_total, invoice.get_total_with_tax())
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_multiple_delete02(self):
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Organisation]
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=SetCredentials.CRED_VIEW | SetCredentials.CRED_DELETE | \
                                            SetCredentials.CRED_LINK | SetCredentials.CRED_UNLINK, #not SetCredentials.CRED_CHANGE |
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        self.assertFalse(invoice.can_change(self.user))

        user = self.user
        create_line = ProductLine.objects.create
        ids = tuple(create_line(user=user, related_document=invoice,
                                on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        response = self.client.post('/creme_core/delete_js', follow=True, data={'ids': '%s,%s' % ids})
        self.assertEqual(403, response.status_code, response.content)
        self.assertEqual(2, ProductLine.objects.filter(pk__in=ids).count())

    def _build_bulk_url(self, line_class, *lines):
        return u'/creme_core/entity/bulk_update/%(ct_id)s/?persist=ids&ids=%(ids)s' % { #TODO: ids=&ids=9 etc.... ok ??
                'ct_id': ContentType.objects.get_for_model(line_class).id,
                'ids':   '&ids='.join(str(line.id) for line in lines),
                }

    def test_bulk_update(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]

        def create_line(cls, price):
            return cls.objects.create(user=self.user, related_document=invoice,
                                      on_the_fly_item='Fly ' + price,
                                      unit_price=Decimal(price),
                                      quantity=1,
                                     )

        pl1 = create_line(ProductLine, '10')
        pl2 = create_line(ProductLine, '20')
        sl1 = create_line(ServiceLine, '100')
        sl2 = create_line(ServiceLine, '300')

        invoice.save() # updates totals

        self.assertEqual(2, len(invoice.product_lines))
        self.assertEqual(2, len(invoice.service_lines))

        expected_total = Decimal('430')
        self.assertEqual(expected_total, invoice.get_total())
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.get_total_with_tax())
        self.assertEqual(expected_total, invoice.total_vat)

        url = self._build_bulk_url(ProductLine, pl1, pl2)
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'field_name':   'quantity',
                                               'field_value':  2,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        url = self._build_bulk_url(ServiceLine, sl1, sl2)
        self.assertEqual(200, self.client.get(url).status_code)

        response = self.client.post(url, data={'field_name':   'unit_price',
                                               'field_value':  500,
                                               'entities_lbl': 'whatever',
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)
        expected_total = Decimal('1060')
        self.assertEqual(expected_total, invoice.get_total())
        self.assertEqual(expected_total, invoice.get_total_with_tax())
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)
