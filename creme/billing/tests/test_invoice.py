# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.conf import settings
    from django.core.urlresolvers import reverse
    from django.db.models.deletion import ProtectedError
    from django.utils.translation import ugettext as _

    from creme.creme_core.tests.base import CremeTransactionTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import (CremeEntity, RelationType, Relation,
            SetCredentials, Currency, Vat)

    from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
    from creme.persons.tests.base import skipIfCustomOrganisation, skipIfCustomAddress

    from ..constants import (REL_SUB_BILL_ISSUED, REL_OBJ_BILL_ISSUED,
            REL_SUB_BILL_RECEIVED, REL_OBJ_BILL_RECEIVED, REL_SUB_HAS_LINE, AMOUNT_PK, PERCENT_PK)
    from ..models import InvoiceStatus, AdditionalInformation, PaymentTerms
    from .base import (_BillingTestCase, _BillingTestCaseMixin, skipIfCustomInvoice,
            skipIfCustomProductLine, skipIfCustomServiceLine,
            Organisation, Address, Invoice, ProductLine, ServiceLine)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceTestCase(_BillingTestCase):
    def _build_gennumber_url(self, invoice):
        return reverse('billing__generate_invoice_number', args=(invoice.id,))

    def test_createview01(self):
        user = self.login()

        self.assertGET200(reverse('billing__create_invoice'))

        name = 'Invoice001'
        currency = Currency.objects.all()[0]

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        self.assertFalse(target.billing_address)
        self.assertFalse(target.shipping_address)

        invoice = self.create_invoice(name, source, target, currency)
        self.assertEqual(1,        invoice.status_id)
        self.assertEqual(currency, invoice.currency)
        self.assertEqual(date(year=2010, month=10, day=13), invoice.expiration_date)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,       source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED,     target)
        self.assertRelationCount(1, target,  REL_SUB_CUSTOMER_SUPPLIER, source)

        self.assertEqual(source, invoice.get_source().get_real_entity())
        self.assertEqual(target, invoice.get_target().get_real_entity())

        target = self.refresh(target)
        self.assertIsNone(target.billing_address)
        self.assertIsNone(target.shipping_address)

        b_addr = invoice.billing_address
        self.assertEqual(invoice,                b_addr.owner)
        self.assertEqual(_(u'Billing address'),  b_addr.name)
        self.assertEqual(_(u'Billing address'),  b_addr.address)

        s_addr = invoice.shipping_address
        self.assertEqual(invoice,                s_addr.owner)
        self.assertEqual(_(u'Shipping address'), s_addr.name)
        self.assertEqual(_(u'Shipping address'), s_addr.address)

        self.create_invoice('Invoice002', source, target, currency)
        self.assertRelationCount(1, target, REL_SUB_CUSTOMER_SUPPLIER, source)

    @skipIfCustomAddress
    def test_createview02(self):
        user = self.login()

        name = 'Invoice001'
        source = Organisation.objects.filter(is_managed=True)[0]
        target = Organisation.objects.create(user=user, name='Target Orga')

        create_addr = partial(Address.objects.create, owner=target)
        target.shipping_address = create_addr(name='ShippingAddr', address='Temple of fire',
                                              po_box='6565', zipcode='789', city='Konoha',
                                              department='dep1', state='Stuff', country='Land of Fire'
                                             )
        target.billing_address  = create_addr(name='BillingAddr', address='Temple of sand',
                                              po_box='8778', zipcode='123', city='Suna',
                                              department='dep2', state='Foo', country='Land of Sand'
                                             )
        target.save()

        self.assertEqual(source.id,
                         self.client.get(reverse('billing__create_invoice'))
                                    .context['form']['source'].field.initial
                        )

        invoice = self.create_invoice(name, source, target)

        self.assertAddressContentEqual(target.billing_address, invoice.billing_address)
        self.assertEqual(invoice, invoice.billing_address.owner)

        self.assertAddressContentEqual(target.shipping_address, invoice.shipping_address)
        self.assertEqual(invoice, invoice.shipping_address.owner)

        self.assertGET200(invoice.get_absolute_url())

    def test_createview03(self):
        "Credentials errors with Organisation"
        user = self.login(is_superuser=False, creatable_models=[Invoice])
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.UNLINK,  # Not LINK
                  set_type=SetCredentials.ESET_ALL,
                 )
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE | EntityCredentials.LINK |
                        EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN,
                 )

        source = Organisation.objects.create(user=self.other_user, name='Source Orga')
        self.assertFalse(user.has_perm_to_link(source))

        target = Organisation.objects.create(user=self.other_user, name='Target Orga')
        self.assertFalse(user.has_perm_to_link(target))

        url = reverse('billing__create_invoice')
        response = self.client.get(url, follow=True)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('source', form.fields, 'Bad form ?!')

        response = self.assertPOST200(url, follow=True,
                                      data={'user':            user.pk,
                                            'name':            'Invoice001',
                                            'issuing_date':    '2011-9-7',
                                            'expiration_date': '2011-10-13',
                                            'status':          1,
                                            'source':          source.id,
                                            'target':          self.genericfield_format_entity(target),
                                           }
                                     )
        link_error = _(u'You are not allowed to link this entity: %s')
        not_viewable_error = _(u'Entity #%s (not viewable)')
        self.assertFormError(response, 'form', 'source',
                             link_error % (not_viewable_error % source.id)
                            )
        self.assertFormError(response, 'form', 'target',
                             link_error % (not_viewable_error % target.id)
                            )

    def test_create_related(self):
        user = self.login()
        source, target = self.create_orgas()
        url = reverse('billing__create_related_invoice', args=(target.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual({'status': 1,
                          'target': target,
                         },
                         form.initial
                        )

        name = 'Invoice#1'
        currency = Currency.objects.all()[0]
        status   = InvoiceStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2013-12-15',
                                          'expiration_date': '2014-1-22',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertEqual(date(year=2013, month=12, day=15), invoice.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=22), invoice.expiration_date)
        self.assertEqual(currency, invoice.currency)
        self.assertEqual(status,   invoice.status)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)

    def test_listview(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        invoice1 = self.create_invoice('invoice 01', source, target)
        invoice2 = self.create_invoice('invoice 02', source, target)

        response = self.assertGET200(reverse('billing__list_invoices'))

        with self.assertNoException():
            invoices_page = response.context['entities']

        self.assertEqual(2, invoices_page.paginator.count)
        self.assertEqual({invoice1, invoice2}, set(invoices_page.paginator.object_list))

    def test_editview01(self):
        user = self.login()

        # Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001', currency_id=1
                                        )
        self.assertGET200(invoice.get_edit_absolute_url())

    def test_editview02(self):
        user = self.login()

        name = 'Invoice001'
        invoice, source, target = self.create_invoice_n_orgas(name)

        url = invoice.get_edit_absolute_url()
        self.assertGET200(url)

        name += '_edited'

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga 2')
        target = create_orga(name='Target Orga 2')

        currency = Currency.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2011-11-14',
                                          'status':          1,
                                          'currency':        currency.pk,
                                          'discount':        Decimal(),
                                          # 'discount_unit':   1,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertRedirects(response, invoice.get_absolute_url())

        invoice = self.refresh(invoice)
        self.assertEqual(name, invoice.name)
        self.assertEqual(date(year=2011, month=11, day=14), invoice.expiration_date)

        self.assertEqual(source, invoice.get_source().get_real_entity())
        self.assertEqual(target, invoice.get_target().get_real_entity())

        self.assertRelationCount(1, source, REL_OBJ_BILL_ISSUED,   invoice)
        self.assertRelationCount(1, target, REL_OBJ_BILL_RECEIVED, invoice)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_editview03(self):
        "User changes => lines user changes"
        user = self.login()

        # Simpler to test with 2 super users (do not have to create SetCredentials etc...)
        other_user = self.other_user
        other_user.superuser = True
        other_user.save()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001', user=user)
        self.assertEqual(user, invoice.user)

        create_pline = partial(ProductLine.objects.create, user=user, related_document=invoice)
        create_sline = partial(ServiceLine.objects.create, user=user, related_document=invoice)
        lines = [create_pline(on_the_fly_item="otf1",             unit_price=Decimal("1")),
                 create_pline(related_item=self.create_product(), unit_price=Decimal("2")),
                 create_sline(on_the_fly_item="otf2",             unit_price=Decimal("4")),
                 create_sline(related_item=self.create_service(), unit_price=Decimal("5")),
                ]

        response = self.client.post(invoice.get_edit_absolute_url(), follow=True,
                                    data={'user':            other_user.pk,
                                          'name':            invoice.name,
                                          'expiration_date': '2011-11-14',
                                          'status':          invoice.status.id,
                                          'currency':        invoice.currency.id,
                                          'discount':        invoice.discount,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)
        self.assertEqual(other_user, invoice.user)

        self.assertEqual([other_user.id] * 4,
                         list(CremeEntity.objects.filter(pk__in=[l.pk for l in lines])
                                          .values_list('user', flat=True)
                             )  # Refresh
                        )

    def test_editview04(self):
        "Error on discount"
        user = self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        url = invoice.get_edit_absolute_url()

        def post(discount):
            return self.assertPOST200(url, follow=True,
                                      data={'user':              user.id,
                                              'name':            invoice.name,
                                              'status':          invoice.status_id,
                                              'currency':        invoice.currency.pk,
                                              'discount':        discount,
                                              'source':          source.id,
                                              'target':          self.genericfield_format_entity(target),
                                              }
                                     )

        msg = _(u'Enter a number between 0 and 100 (it is a percentage).')
        self.assertFormError(post('150'), 'form', 'discount', msg)
        self.assertFormError(post('-10'), 'form', 'discount', msg)

    def test_inner_edit01(self):
        user = self.login()

        name = 'invoice001'
        invoice = self.create_invoice_n_orgas(name, user=user)[0]

        build_url = partial(self.build_inneredit_url, entity=invoice)
        url = build_url(fieldname='name')
        self.assertGET200(url)

        name = name.title()
        response = self.client.post(url, data={'entities_lbl': [unicode(invoice)],
                                               'field_value':  name,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(invoice).name)

        # Addresses should not be editable
        self.assertGET(400, build_url(fieldname='billing_address'))
        self.assertGET(400, build_url(fieldname='shipping_address'))

    def test_inner_edit02(self):
        "Discount"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=user)[0]
        url = self.build_inneredit_url(entity=invoice, fieldname='discount')
        self.assertGET200(url)

        response = self.assertPOST200(url, data={'entities_lbl': [unicode(invoice)],
                                                 'field_value':  '110',
                                                }
                                     )
        self.assertFormError(response, 'form', 'field_value',
                             _(u'Enter a number between 0 and 100 (it is a percentage).')
                            )

    def test_generate_number01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.number)
        self.assertEqual(1, invoice.status_id)

        issuing_date = invoice.issuing_date
        self.assertTrue(issuing_date)

        url = self._build_gennumber_url(invoice)
        self.assertGET404(url, follow=True)
        self.assertPOST200(url, follow=True)

        invoice = self.refresh(invoice)
        number    = invoice.number
        status_id = invoice.status_id
        self.assertTrue(number)
        self.assertEqual(2,            status_id)
        self.assertEqual(issuing_date, invoice.issuing_date)

        # Already generated
        self.assertPOST404(url, follow=True)
        invoice = self.refresh(invoice)
        self.assertEqual(number,    invoice.number)
        self.assertEqual(status_id, invoice.status_id)

    def test_generate_number02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice.issuing_date = None
        invoice.save()

        self.assertPOST200(self._build_gennumber_url(invoice), follow=True)
        invoice = self.refresh(invoice)
        self.assertTrue(invoice.issuing_date)
        self.assertEqual(date.today(), invoice.issuing_date)  # NB: this test can fail if run at midnight...

    def test_generate_number03(self):
        "Managed orga"
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self._set_managed(source)

        self.assertPOST200(self._build_gennumber_url(invoice), follow=True)
        self.assertTrue(settings.INVOICE_NUMBER_PREFIX + '1', self.refresh(invoice).number)

    # @skipIfCustomProductLine
    # def test_product_lines_property01(self):
    #     user = self.login()
    #     invoice = self.create_invoice_n_orgas('Invoice001')[0]
    #
    #     with self.assertNumQueries(1):
    #         length = len(invoice.product_lines)
    #
    #     self.assertEqual(0, length)
    #
    #     with self.assertNumQueries(0):
    #         bool(invoice.product_lines)
    #
    #     product_line = ProductLine.objects.create(user=user, related_document=invoice,
    #                                               on_the_fly_item='Flyyyyy',
    #                                              )
    #     self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, product_line)
    #
    #     invoice = self.refresh(invoice)
    #     self.assertEqual([product_line], list(invoice.product_lines))
    #
    #     product_line.delete()
    #     self.assertFalse(self.refresh(invoice).product_lines)

    # @skipIfCustomProductLine
    # @skipIfCustomServiceLine
    # def test_product_lines_property02(self):
    #     user = self.login()
    #     invoice = self.create_invoice_n_orgas('Invoice001')[0]
    #
    #     kwargs = {'user': user, 'related_document': invoice}
    #     create_pline = partial(ProductLine.objects.create, **kwargs)
    #     product_line1 = create_pline(on_the_fly_item='Flyyy product')
    #     product_line2 = create_pline(on_the_fly_item='Flyyy product2')
    #     ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)
    #     self.assertEqual([product_line1, product_line2], list(self.refresh(invoice).product_lines))

    # @skipIfCustomServiceLine
    # def test_service_lines_property01(self):
    #     user = self.login()
    #     invoice = self.create_invoice_n_orgas('Invoice001')[0]
    #     self.assertFalse(invoice.service_lines)
    #
    #     service_line = ServiceLine.objects.create(user=user, related_document=invoice,
    #                                               on_the_fly_item='Flyyyyy'
    #                                              )
    #     self.assertEqual([service_line], list(self.refresh(invoice).service_lines))
    #
    #     service_line.delete()
    #     self.assertFalse(self.refresh(invoice).service_lines)

    # @skipIfCustomProductLine
    # @skipIfCustomServiceLine
    # def test_service_lines_property02(self):
    #     user = self.login()
    #     invoice = self.create_invoice_n_orgas('Invoice001')[0]
    #
    #     kwargs = {'user': user, 'related_document': invoice}
    #     ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
    #
    #     create_sline = partial(ServiceLine.objects.create, **kwargs)
    #     service_line1 = create_sline(on_the_fly_item='Flyyy service1')
    #     service_line2 = create_sline(on_the_fly_item='Flyyy service2')
    #
    #     self.assertEqual([service_line1, service_line2], list(self.refresh(invoice).service_lines))

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines01(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.get_lines(ProductLine))
        self.assertFalse(invoice.get_lines(ServiceLine))

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)

        self.assertEqual([product_line.pk], list(invoice.get_lines(ProductLine).values_list('pk', flat=True)))
        self.assertEqual([service_line.pk], list(invoice.get_lines(ServiceLine).values_list('pk', flat=True)))

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines02(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        kwargs = {'user': user, 'related_document': invoice}

        # ----
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        plines = list(invoice.get_lines(ProductLine))

        self.assertEqual([product_line], plines)

        with self.assertNumQueries(0):
            list(invoice.get_lines(ProductLine))

        # ----
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)
        slines = list(invoice.get_lines(ServiceLine))

        self.assertEqual([service_line], slines)

        with self.assertNumQueries(0):
            list(invoice.get_lines(ServiceLine))

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_iter_all_lines(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)

        self.assertEqual([product_line, service_line],
                         list(invoice.iter_all_lines())
                        )

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_total_vat(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertEqual(0, invoice._get_total_with_tax())

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product',
                                                  quantity=3, unit_price=Decimal("5"),
                                                  **kwargs
                                                 )
        expected = product_line.get_price_inclusive_of_tax()
        self.assertEqual(Decimal('15.00'), expected)

        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service',
                                                  quantity=9, unit_price=Decimal("10"),
                                                  **kwargs
                                                 )
        expected = product_line.get_price_inclusive_of_tax() + service_line.get_price_inclusive_of_tax()
        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

    @skipIfCustomAddress
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_clone(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        create_address = Address.objects.create
        target.billing_address = b_addr = \
            create_address(name="Billing address 01",
                           address="BA1 - Address", po_box="BA1 - PO box",
                           zipcode="BA1 - Zip code", city="BA1 - City",
                           department="BA1 - Department",
                           state="BA1 - State", country="BA1 - Country",
                           owner=target,
                          )
        target.shipping_address = s_addr = \
            create_address(name="Shipping address 01",
                           address="SA1 - Address", po_box="SA1 - PO box",
                           zipcode="SA1 - Zip code", city="SA1 - City",
                           department="SA1 - Department",
                           state="SA1 - State", country="SA1 - Country",
                           owner=target,
                          )
        target.save()

        currency = Currency.objects.create(name=u'Marsian dollar', local_symbol=u'M$',
                                           international_symbol=u'MUSD', is_custom=True,
                                          )
        invoice = self.create_invoice('Invoice001', source, target, currency=currency)
        invoice.additional_info = AdditionalInformation.objects.all()[0]
        invoice.payment_terms   = PaymentTerms.objects.all()[0]
        invoice.save()

        kwargs = {'user': user, 'related_document': invoice}
        ServiceLine.objects.create(related_item=self.create_service(), **kwargs)
        ServiceLine.objects.create(on_the_fly_item="otf service", **kwargs)
        ProductLine.objects.create(related_item=self.create_product(), **kwargs)
        ProductLine.objects.create(on_the_fly_item="otf product", **kwargs)

        cloned = self.refresh(invoice.clone())
        invoice = self.refresh(invoice)

        self.assertNotEqual(invoice, cloned)  # Not the same pk
        self.assertEqual(invoice.name,     cloned.name)
        self.assertEqual(currency,         cloned.currency)
        self.assertIsNone(cloned.additional_info) # Should not be cloned
        self.assertIsNone(cloned.payment_terms)   # Should not be cloned
        self.assertEqual(source, cloned.get_source().get_real_entity())
        self.assertEqual(target, cloned.get_target().get_real_entity())

        # Lines are cloned
        src_line_ids = [l.id for l in invoice.iter_all_lines()]
        self.assertEqual(4, len(src_line_ids))

        cloned_line_ids = [l.id for l in cloned.iter_all_lines()]
        self.assertEqual(4, len(cloned_line_ids))

        self.assertFalse(set(src_line_ids) & set(cloned_line_ids))

        # Addresses are cloned
        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,      billing_address.owner)
        self.assertEqual(b_addr.name, billing_address.name)
        self.assertEqual(b_addr.city, billing_address.city)

        shipping_address = cloned.shipping_address
        self.assertIsInstance(shipping_address, Address)
        self.assertEqual(cloned,            shipping_address.owner)
        self.assertEqual(s_addr.name,       shipping_address.name)
        self.assertEqual(s_addr.department, shipping_address.department)

    def test_clone_source_n_target(self):
        "Internal relationtypes should not be cloned"
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        cloned_source = source.clone()
        cloned_target = target.clone()

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED,   cloned_source)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, cloned_target)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discounts(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=10)[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product',
                                                  unit_price=Decimal('1000.00'), quantity=2,
                                                  discount=Decimal('10.00'),
                                                  discount_unit=PERCENT_PK,
                                                  total_discount=False,
                                                  vat_value=Vat.get_default_vat(),
                                                  **kwargs
                                                 )
        self.assertEqual(1620, product_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1620, invoice._get_total())
        self.assertEqual(1620, invoice.total_no_vat)

        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service',
                                                  unit_price=Decimal('20.00'), quantity=10,
                                                  discount=Decimal('100.00'),
                                                  discount_unit=AMOUNT_PK,
                                                  total_discount=True,
                                                  vat_value=Vat.get_default_vat(),
                                                  **kwargs
                                                 )
        self.assertEqual(90, service_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1710, invoice._get_total())  # total_exclusive_of_tax
        self.assertEqual(1710, invoice.total_no_vat)

    def test_delete_status01(self):
        self.login()

        status = InvoiceStatus.objects.create(name='OK')
        self.assertDeleteStatusOK(status, 'invoice_status')

    def test_delete_status02(self):
        self.login()

        status = InvoiceStatus.objects.create(name='OK')
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.status = status
        invoice.save()

        self.assertDeleteStatusKO(status, 'invoice_status', invoice)

    def test_delete_paymentterms(self):
        self.login()

        self.assertGET200(reverse('creme_config__model_portal', args=('billing', 'payment_terms')))

        pterms = PaymentTerms.objects.create(name='3 months')

        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.payment_terms = pterms
        invoice.save()

        self.assertPOST200(reverse('creme_config__delete_instance', args=('billing', 'payment_terms')),
                           data={'id': pterms.pk}
                          )
        self.assertDoesNotExist(pterms)

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertIsNone(invoice.payment_terms)

    def test_delete_currency(self):
        self.login()

        currency = Currency.objects.create(name=u'Berry', local_symbol=u'B', international_symbol=u'BRY')
        invoice = self.create_invoice_n_orgas('Nerv', currency=currency)[0]

        self.assertPOST404(reverse('creme_config__delete_instance', args=('creme_core', 'currency')),
                           data={'id': currency.pk}
                          )
        self.get_object_or_fail(Currency, pk=currency.pk)

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertEqual(currency, invoice.currency)

    def test_delete_additional_info(self):
        self.login()

        info = AdditionalInformation.objects.create(name='Agreement')
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.additional_info = info
        invoice.save()

        self.assertPOST200(reverse('creme_config__delete_instance', args=('billing', 'additional_information')),
                           data={'id': info.pk}
                          )
        self.assertDoesNotExist(info)

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertIsNone(invoice.additional_info)

    @skipIfCustomAddress
    def test_csv_import(self):
        self.login()
        self._aux_test_csv_import(Invoice, InvoiceStatus)

    @skipIfCustomAddress
    def test_csv_import_update01(self):
        self.login()
        self._aux_test_csv_import_update(Invoice, InvoiceStatus,
                                         override_billing_addr=False,
                                         override_shipping_addr=True,
                                        )

    @skipIfCustomAddress
    def test_csv_import_update02(self):
        self.login()
        self._aux_test_csv_import_update(Invoice, InvoiceStatus,
                                         override_billing_addr=True,
                                         override_shipping_addr=False,
                                        )

    @skipIfCustomAddress
    def test_csv_import_update03(self):
        self.login()
        self._aux_test_csv_import_update(Invoice, InvoiceStatus,
                                         target_billing_address=False,
                                         override_billing_addr=True,
                                        )

    @skipIfCustomAddress
    def test_csv_import_update04(self):
        self.login()
        self._aux_test_csv_import(Invoice, InvoiceStatus, update=True)


@skipIfCustomOrganisation
@skipIfCustomInvoice
@skipIfCustomProductLine
@skipIfCustomServiceLine
class BillingDeleteTestCase(_BillingTestCaseMixin, CremeTransactionTestCase):
    def setUp(self):  # setUpClass does not work here
        self.populate('creme_core', 'creme_config', 'billing')
        self.login()

    def test_delete01(self):
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        product_line  = ProductLine.objects.create(user=self.user,
                                                   related_document=invoice,
                                                   on_the_fly_item='My product',
                                                  )
        service_line = ServiceLine.objects.create(user=self.user,
                                                  related_document=invoice,
                                                  on_the_fly_item='My service',
                                                 )

        b_addr = invoice.billing_address
        self.assertIsInstance(b_addr, Address)

        s_addr = invoice.billing_address
        self.assertIsInstance(s_addr, Address)

        invoice.delete()
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)

        self.assertStillExists(source)
        self.assertStillExists(target)

        self.assertDoesNotExist(b_addr)
        self.assertDoesNotExist(s_addr)

    def test_delete02(self):
        "Can't be deleted"
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        service_line = ServiceLine.objects.create(user=user, related_document=invoice,
                                                  on_the_fly_item='Flyyyyy',
                                                 )
        rel1 = Relation.objects.get(subject_entity=invoice.id, object_entity=service_line.id)

        # This relation prohibits the deletion of the invoice
        ce = CremeEntity.objects.create(user=user)
        rtype = RelationType.create(('test-subject_linked', 'is linked to'),
                                    ('test-object_linked',  'is linked to'),
                                    is_internal=True,
                                   )[0]
        rel2 = Relation.objects.create(subject_entity=invoice, object_entity=ce, type=rtype, user=user)

        self.assertRaises(ProtectedError, invoice.delete)

        try:
            Invoice.objects.get(pk=invoice.pk)
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)

            CremeEntity.objects.get(pk=ce.id)
            Relation.objects.get(pk=rel2.id)

            ServiceLine.objects.get(pk=service_line.pk)
            Relation.objects.get(pk=rel1.id)
        except Exception as e:
            self.fail("Exception: (%s). Maybe the db doesn't support transaction ?" % e)
