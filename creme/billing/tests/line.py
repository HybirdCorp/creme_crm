# -*- coding: utf-8 -*-

try:
    from decimal import Decimal

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core import autodiscover
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
        product = self.create_product(unit_price)
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
        self.assertEqual(name, lines[0].on_the_fly_item)

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

        self.assertEqual(0, len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)
        product_line.related_document = invoice

        response = self.client.post('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(invoice.product_lines))
        self.assertFalse(ProductLine.objects.exists())

    def test_delete_product_line02(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertEqual(0, len(invoice.product_lines))

        product_line = ProductLine.objects.create(user=self.user)
        response = self.client.post('/creme_core/entity/delete/%s' % product_line.id, follow=True)
        self.assertEqual(403, response.status_code)

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
        response = self.client.post(url, data={'related_item': service.id,
                                               'comment':      'no comment !',
                                               'quantity':     2,
                                               'unit_price':   unit_price,
                                               'discount':     Decimal(),
                                               'discount_unit':1,
                                               'vat_value':    Vat.get_default_vat().id,
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
        self.assertEqual(name, lines[0].on_the_fly_item)

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
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product_line = ProductLine.objects.create(user=self.user)
        pl_rel = Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)
        self.assertEqual(invoice.pk, product_line.related_document.id)

        #Tries for testing there is only one relation created between product_line and invoice
        for i in xrange(2):
            Relation.objects.create(subject_entity=invoice, object_entity=product_line, type_id=REL_SUB_HAS_LINE, user=self.user)

        self.assertEqual(1, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

    def test_related_document02(self):
        self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product_line = ProductLine.objects.create(user=self.user)
        self.assertIsNone(product_line.related_document)
        self.assertEqual(0, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

        product_line.related_document = invoice
        self.assertEqual(invoice, product_line.related_document)
        self.assertEqual(1, Relation.objects.filter(subject_entity=invoice, object_entity=product_line, type=REL_SUB_HAS_LINE).count())

    def test_related_item01(self):
        self.login()

        autodiscover()#To connect signals

        product = self.create_product()
        product_line = ProductLine.objects.create(user=self.user)
        self.assertIsNone(product_line.related_item)

        create_rel = Relation.objects.create

        pl_rel = create_rel(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)
        self.assertEqual(product.pk, product_line.related_item.id)

        #Tries for testing there is only one relation created between product_line and product
        pl_rel2 = create_rel(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)
        pl_rel3 = create_rel(object_entity=product, subject_entity=product_line, type_id=REL_SUB_LINE_RELATED_ITEM, user=self.user)

        self.assertEqual(1, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_related_item02(self):
        self.login()

        autodiscover()#To connect signals

        product = self.create_product()
        product_line = ProductLine.objects.create(user=self.user)

        self.assertIsNone(product_line.related_item)
        self.assertEqual(0, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

        product_line.related_item = product
        self.assertEqual(product, product_line.related_item)
        self.assertEqual(1, Relation.objects.filter(object_entity=product, subject_entity=product_line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_product_line_clone(self):
        self.login()

        autodiscover()#To connect signals

        product = self.create_product()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        product2 = self.create_product()
        invoice2, source2, target2 = self.create_invoice_n_orgas('Invoice002')

        product_line = ProductLine.objects.create(user=self.user)
        product_line.related_document = invoice
        product_line.related_item     = product

        product_line2 = product_line.clone()
        product_line2.related_document = invoice2
        product_line2.related_item     = product2

        product_line2 = self.refresh(product_line2)
        self.assertEqual(invoice2, product_line2.related_document)
        self.assertEqual(product2, product_line2.related_item)

        rel_filter = Relation.objects.filter
        self.assertEqual([product_line2.pk], list(rel_filter(type=REL_SUB_HAS_LINE,          subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual([product_line2.pk], list(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=product2).values_list('subject_entity', flat=True)))

    def test_service_line_clone(self):
        self.login()

        autodiscover()#To connect signals

        service = self.create_service()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        service2 = self.create_service()
        invoice2, source2, target2 = self.create_invoice_n_orgas('Invoice002')
        service_line = ServiceLine.objects.create(user=self.user)
        service_line.related_document = invoice
        service_line.related_item     = service

        service_line2 = service_line.clone()
        service_line2.related_document = invoice2
        service_line2.related_item     = service2

        service_line2 = ServiceLine.objects.get(pk=service_line2.id)#Refresh
        self.assertEqual(invoice2, service_line2.related_document)
        self.assertEqual(service2, service_line2.related_item)
        self.assertNotEqual(service_line, service_line2)

        rel_filter = Relation.objects.filter
        self.assertEqual([service_line2.pk], list(rel_filter(type=REL_SUB_HAS_LINE,          subject_entity=invoice2).values_list('object_entity', flat=True)))
        self.assertEqual([service_line2.pk], list(rel_filter(type=REL_SUB_LINE_RELATED_ITEM, object_entity=service2).values_list('subject_entity', flat=True)))

    def test_get_verbose_type(self):
        self.login()

        pl = ProductLine.objects.create(user=self.user, on_the_fly_item="otf1", unit_price=Decimal("1"))
        verbose_type = _(u"Product")
        self.assertEqual(verbose_type, unicode(pl.get_verbose_type()))

        funf = pl.function_fields.get('get_verbose_type')
        self.assertIsNotNone(funf)
        self.assertEqual(verbose_type, funf(pl).for_html())

        sl = ServiceLine.objects.create(user=self.user, on_the_fly_item="otf2", unit_price=Decimal("4"))
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

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')
        invoice = self.create_invoice('Invoice0001', source, target, discount=0)

        pl = ProductLine.objects.create(user=self.user, unit_price=Decimal("10"), vat_value=Vat.get_default_vat())
        pl.related_document = invoice

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

        pl = self.refresh(pl)
        invoice = self.refresh(invoice)

        self.assertEqual(200,  response.status_code)
        self.assertTrue(Line.is_discount_valid(20, 20, 10, AMOUNT_PK, False))

        self.assertEqual(Decimal('20'),  pl.unit_price)
        self.assertEqual(Decimal('20'),  pl.quantity)
        self.assertEqual(null_vat,       pl.vat_value)
        self.assertEqual(Decimal('200'), invoice.get_total())
        self.assertEqual(Decimal('200'), invoice.get_total_with_tax())
        self.assertEqual(Decimal('200'), invoice.total_no_vat)
        self.assertEqual(Decimal('200'), invoice.total_vat)

    def test_multiple_delete(self):
        self.login()

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')
        invoice = self.create_invoice('Invoice0001', source, target, discount=0)

        pl1 = ProductLine.objects.create(user=self.user, unit_price=Decimal("10"))
        pl1.related_document = invoice
        pl2 = ProductLine.objects.create(user=self.user, unit_price=Decimal("20"))
        pl2.related_document = invoice

        invoice.save() # updates totals

        self.assertEqual(2, len(invoice.product_lines))
        self.assertEqual(Decimal('30'), invoice.get_total())
        self.assertEqual(Decimal('30'), invoice.total_no_vat)
        self.assertEqual(Decimal('30'), invoice.get_total_with_tax())
        self.assertEqual(Decimal('30'), invoice.total_vat)

        #ids = '%s,%s' % (pl1.id, pl2.id)
        #response = self.client.post('/creme_core/delete_js', follow=True, data={'ids': ids})
        response = self.client.post('/creme_core/delete_js', follow=True, data={'ids': '%s,%s' % (pl1.id, pl2.id)})

        invoice = self.refresh(invoice)

        self.assertEqual(200, response.status_code)
        self.assertEqual(0, len(invoice.product_lines))
        self.assertEqual(Decimal('0'), invoice.get_total())
        self.assertEqual(Decimal('0'), invoice.get_total_with_tax())
        # TODO these two last tests are not working for the moment because delete_js wiew doesnt contact the billing document (signal or anything else)
        # a billing document save is necessary to update the totals fields after the multiple js delete
#        self.assertEqual(Decimal('0'), invoice.total_no_vat)
#        self.assertEqual(Decimal('0'), invoice.total_vat)

    def _build_bulk_url(self, line_class, *lines):
        return u'/creme_core/entity/bulk_update/%(ct_id)s/?persist=ids&ids=%(ids)s' % { #TODO: ids=&ids=9 etc.... ok ??
                'ct_id': ContentType.objects.get_for_model(line_class).id,
                'ids':   '&ids='.join(str(line.id) for line in lines),
                }

    def test_bulk_update(self):
        self.login()

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')
        invoice = self.create_invoice('Invoice0001', source, target, discount=0)

        pl1 = ProductLine.objects.create(user=self.user, unit_price=Decimal("10"))
        pl1.related_document = invoice
        pl2 = ProductLine.objects.create(user=self.user, unit_price=Decimal("20"))
        pl2.related_document = invoice

        sl1 = ServiceLine.objects.create(user=self.user, unit_price=Decimal("100"))
        sl1.related_document = invoice
        sl2 = ServiceLine.objects.create(user=self.user, unit_price=Decimal("300"))
        sl2.related_document = invoice

        invoice.save() # updates totals

        self.assertEqual(2, len(invoice.product_lines))
        self.assertEqual(2, len(invoice.service_lines))
        self.assertEqual(Decimal('430'), invoice.get_total())
        self.assertEqual(Decimal('430'), invoice.total_no_vat)
        self.assertEqual(Decimal('430'), invoice.get_total_with_tax())
        self.assertEqual(Decimal('430'), invoice.total_vat)

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
        self.assertEqual(Decimal('1060'), invoice.get_total())
        self.assertEqual(Decimal('1060'), invoice.get_total_with_tax())
        # TODO these two last tests are not working for the moment because bulk update doesnt contact the billing document (signal or anything else)
        # a billing document save is necessary to update the totals fields after the bulk update
#        self.assertEqual(Decimal('1060'), invoice.total_no_vat)
#        self.assertEqual(Decimal('1060'), invoice.total_vat)
