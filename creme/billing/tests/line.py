# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial

    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.tests.base import CremeTestCase
    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.models import Relation, SetCredentials

    from persons.models import Contact, Organisation

    from products.models import Product, Service, Category, SubCategory

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('LineTestCase',)


class LineTestCase(_BillingTestCase, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'products', 'billing')

    def test_add_product_lines01(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        url = '/billing/%s/product_line/add_multiple' % invoice.id
        self.assertGET200(url)
        self.assertFalse(invoice.service_lines)

        product1 = self.create_product()
        product2 = self.create_product()
        vat = Vat.objects.get_or_create(value=Decimal('5.5'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': '%s,%s' % (product1.id, product2.id),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('20'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice) #refresh lines cache
        self.assertEqual(2, len(invoice.product_lines))

        lines = invoice.product_lines
        line0 = lines[0]
        line1 = lines[1]
        self.assertEqual(quantity,        line0.quantity)
        self.assertEqual(quantity,        line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, product1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, product2)

        self.assertEqual(Decimal('3.2'), invoice.total_no_vat) # 2 * 0.8 + 2 * 0.8
        self.assertEqual(Decimal('3.38'), invoice.total_vat) # 3.2 * 1.07 = 3.38

    def test_add_product_lines02(self): #on-the-fly
        self.login()

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/product_line/add_on_the_fly' % invoice.id
        self.assertGET200(url)

        unit_price = Decimal('1.0')
        name = 'Awesomo'
        response = self.client.post(url, data={'on_the_fly_item': name,
                                               'comment':         'no comment !',
                                               'quantity':        1,
                                               'unit_price':      unit_price,
                                               'unit':            'Box',
                                               'discount':        Decimal(),
                                               'discount_unit':   1,
                                               'vat_value':       Vat.objects.get(value='0.0').id,
                                             }
                                   )
        self.assertNoFormError(response)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(name, line.on_the_fly_item)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, line)
        self.assertEqual(0, Relation.objects.filter(subject_entity=line, type=REL_SUB_LINE_RELATED_ITEM).count())

        self.assertEqual(unit_price, invoice._get_total())
        self.assertEqual(unit_price, invoice._get_total_with_tax())

    def test_add_product_lines03(self):
        "On-the-fly + product creation"
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
                                          'unit':               'Box',
                                          'discount':           Decimal(),
                                          'discount_unit':      1,
                                          'vat_value':          Vat.objects.get(value='0.0').id,
                                          'has_to_register_as': 'on',
                                          'sub_category':       '{"category":%s, "subcategory":%s}' % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)

        product = self.get_object_or_fail(Product, name=name)
        self.assertEqual(cat,        product.category)
        self.assertEqual(subcat,     product.sub_category)
        self.assertEqual(unit_price, product.unit_price)

        lines = invoice.product_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertFalse(line.on_the_fly_item)
        self.assertEqual(product, line.related_item)

    def test_add_product_lines04(self):
        "On-the-fly + product creation + no creation creds"
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Contact, Organisation] #not 'Product'
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat    = Category.objects.create(name='Cat', description='DESCRIPTION')
        subcat = SubCategory.objects.create(name='Cat', description='DESCRIPTION', category=cat)
        response = self.assertPOST200('/billing/%s/product_line/add_on_the_fly' % invoice.id,
                                      data={'on_the_fly_item':     'Awesomo',
                                            'comment':             'no comment !',
                                            'quantity':            1,
                                            'unit_price':          Decimal('1.0'),
                                            'discount':            Decimal(),
                                            'discount_unit':       1,
                                            'vat_value':           Vat.objects.get(value='0.0').id,
                                            'has_to_register_as':  'on',
                                            'category':            cat.id,
                                            'sub_category':        subcat.id,
                                           }
                                   )
        self.assertFormError(response, 'form', 'has_to_register_as',
                             [_(u'You are not allowed to create this entity')]
                            )
        self.assertFalse(invoice.product_lines)
        self.assertFalse(Product.objects.exists())

    def test_delete_product_line01(self):
        self.login()
        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        product_line = ProductLine.objects.create(user=self.user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy'
                                                 )
        self.assertPOST404('/creme_core/entity/delete_related/%s' % product_line.entity_type_id,
                           data={'id': product_line.id},
                          )
        self.assertPOST200('/creme_core/entity/delete/%s' % product_line.id, data={}, follow=True)
        self.assertFalse(self.refresh(invoice).product_lines)
        self.assertFalse(ProductLine.objects.exists())

    def test_add_service_lines01(self):
        "Multiple adding"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=self.other_user)[0]
        url = '/billing/%s/service_line/add_multiple' % invoice.id
        self.assertGET200(url)
        self.assertFalse(invoice.service_lines)

        service1 = self.create_service()
        service2 = self.create_service()
        vat = Vat.objects.get_or_create(value=Decimal('19.6'))[0]
        quantity = 2
        response = self.client.post(url, data={'items': '%s,%s' % (service1.id, service2.id),
                                               'quantity':       quantity,
                                               'discount_value': Decimal('10'),
                                               'vat':            vat.id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice) #refresh lines cache
        self.assertEqual(2, len(invoice.service_lines))

        lines = invoice.service_lines
        line0 = lines[0]
        line1 = lines[1]
        self.assertEqual(quantity,        line0.quantity)
        self.assertEqual(quantity,        line1.quantity)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line0)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE,          line1)
        self.assertRelationCount(1, line0,   REL_SUB_LINE_RELATED_ITEM, service1)
        self.assertRelationCount(1, line1,   REL_SUB_LINE_RELATED_ITEM, service2)

        self.assertEqual(Decimal('21.6'), invoice.total_no_vat) # 2 * 5.4 + 2 * 5.4
        self.assertEqual(Decimal('25.84'), invoice.total_vat) # 21.6 * 1.196 = 25.84

    def test_add_service_lines02(self):
        "On-the-fly"
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        url = '/billing/%s/service_line/add_on_the_fly' % invoice.id
        self.assertGET200(url)

        unit_price = Decimal('1.33')
        name = 'Car wash'
        response = self.client.post(url, data={'on_the_fly_item': name,
                                               'comment':         'no comment !',
                                               'quantity':        2,
                                               'unit_price':      unit_price,
                                               'unit':            'Day',
                                               'discount':        Decimal(),
                                               'discount_unit':   1,
                                               'vat_value':       Vat.objects.get(value='0.0').id,
                                              }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice) #refresh lines cache
        lines = invoice.service_lines
        self.assertEqual(1, len(lines))

        line = lines[0]
        self.assertEqual(name, line.on_the_fly_item)
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, line)
        self.assertEqual(0, Relation.objects.filter(subject_entity=line, type=REL_SUB_LINE_RELATED_ITEM).count())

    def test_add_service_lines03(self):
        "On-the-fly + Service creation"
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
                                          'unit':               'Day',
                                          'discount':           Decimal(),
                                          'discount_unit':      1,
                                          'vat_value':          Vat.get_default_vat().id,
                                          'has_to_register_as': 'on',
                                          'sub_category': """{"category":%s, "subcategory":%s}""" % (cat.id, subcat.id)
                                         }
                                   )
        self.assertNoFormError(response)

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

    def test_add_service_lines04(self):
        "On-the-fly + service creation + no creation creds"
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Contact, Organisation], #not 'Service'
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE | EntityCredentials.LINK |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        invoice  = self.create_invoice_n_orgas('Invoice001')[0]
        cat, subcat = self.create_cat_n_subcat()
        response = self.assertPOST200('/billing/%s/service_line/add_on_the_fly' % invoice.id,
                                      data={'on_the_fly_item':    'Car wash',
                                            'comment':            'no comment !',
                                            'quantity':           2,
                                            'unit_price':         Decimal('1.33'),
                                            'discount':           Decimal(),
                                            'discount_unit':      1,
                                            'vat_value':          Vat.objects.get(value='0.0').id,
                                            'has_to_register_as': 'on',
                                            'sub_category':       '{"category": %s, "subcategory": %s}' % (cat.id, subcat.id)
                                         }
                                   )
        self.assertFormError(response, 'form', 'has_to_register_as',
                             [_(u'You are not allowed to create this entity')]
                            )
        self.assertFalse(invoice.service_lines)
        self.assertFalse(Service.objects.exists())

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
        kwargs = {'user': self.user, 'related_document': invoice}
        pl = ProductLine.objects.create(on_the_fly_item="otf1", unit_price=Decimal("1"), **kwargs)
        verbose_type = _(u"Product")
        self.assertEqual(verbose_type, unicode(pl.get_verbose_type()))

        funf = pl.function_fields.get('get_verbose_type')
        self.assertIsNotNone(funf)
        self.assertEqual(verbose_type, funf(pl).for_html())

        sl = ServiceLine.objects.create(on_the_fly_item="otf2", unit_price=Decimal("4"), **kwargs)
        verbose_type = _(u"Service")
        self.assertEqual(verbose_type, unicode(sl.get_verbose_type()))
        self.assertEqual(verbose_type, sl.function_fields.get('get_verbose_type')(sl).for_html())

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
        response = self.client.post('/billing/line/%s/edit_inner' % pl.id, follow=True,
                                    data={'unit_price':       20,
                                          'quantity':         20,
                                          'discount':         10,
                                          'discount_unit':    AMOUNT_PK,
                                          'total_discount':   '2',
                                          'vat':              null_vat.id,
                                         }
                                   )
        self.assertNoFormError(response)

        pl = self.refresh(pl)
        invoice = self.refresh(invoice)

        self.assertEqual(Decimal('20'),  pl.unit_price)
        self.assertEqual(Decimal('20'),  pl.quantity)
        self.assertEqual(null_vat,       pl.vat_value)
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
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        self.assertPOST200('/creme_core/entity/delete/multi', follow=True,
                           data={'ids': '%s,%s' % ids}
                          )
        self.assertFalse(ProductLine.objects.filter(pk__in=ids))

        invoice = self.refresh(invoice)
        self.assertFalse(invoice.product_lines)

        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_multiple_delete02(self):
        self.login(is_superuser=False, allowed_apps=['persons', 'billing'],
                   creatable_models=[Invoice, Organisation]
                  )

        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW | EntityCredentials.DELETE | \
                                            EntityCredentials.LINK | EntityCredentials.UNLINK, #not EntityCredentials.CHANGE |
                                      set_type=SetCredentials.ESET_OWN
                                     )

        user = self.user
        invoice = self.create_invoice_n_orgas('Invoice001', discount=0)[0]
        self.assertFalse(invoice.can_change(user))

        create_line = partial(ProductLine.objects.create, user=user,
                              related_document=invoice
                             )
        ids = tuple(create_line(on_the_fly_item='Fly ' + price,
                                unit_price=Decimal(price)
                               ).id for price in ('10', '20')
                   )

        self.assertPOST403('/creme_core/entity/delete/multi', follow=True,
                           data={'ids': '%s,%s' % ids}
                          )
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
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        url = self._build_bulk_url(ProductLine, pl1, pl2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'field_name':   'quantity',
                                                           'field_value':  2,
                                                           'entities_lbl': 'whatever',
                                                          }
                                                )
                              )

        url = self._build_bulk_url(ServiceLine, sl1, sl2)
        self.assertGET200(url)
        self.assertNoFormError(self.client.post(url, data={'field_name':   'unit_price',
                                                           'field_value':  500,
                                                           'entities_lbl': 'whatever',
                                                          }
                                               )
                              )

        invoice = self.refresh(invoice)
        expected_total = Decimal('1060')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    def test_delete_vat01(self):
        self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        self.assertPOST200('/creme_config/billing/vat_value/delete', data={'id': vat.pk})
        self.assertFalse(Vat.objects.filter(pk=vat.pk).exists())

    def test_delete_vat02(self):
        self.login()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        line = ProductLine.objects.create(user=self.user, related_document=invoice,
                                          on_the_fly_item='Flyyyyy', vat_value=vat,
                                         )

        self.assertPOST404('/creme_config/billing/vat_value/delete', data={'id': vat.pk})
        self.assertTrue(Vat.objects.filter(pk=vat.pk).exists())

        self.get_object_or_fail(Invoice, pk=invoice.pk)

        line = self.get_object_or_fail(ProductLine, pk=line.pk)
        self.assertEqual(vat, line.vat_value)
