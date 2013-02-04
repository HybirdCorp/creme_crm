# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.db.models.deletion import ProtectedError
    from django.utils.translation import ugettext as _
    from django.contrib.contenttypes.models import ContentType

    from creme_core.tests.base import CremeTestCase, CremeTransactionTestCase
    from creme_core.auth.entity_credentials import EntityCredentials
    from creme_core.models import CremeEntity, Relation, SetCredentials, Currency #CremeProperty
    from creme_core.constants import PROP_IS_MANAGED_BY_CREME, REL_SUB_HAS

    from persons.models import Organisation, Address
    from persons.constants import REL_SUB_CUSTOMER_SUPPLIER

    from billing.models import *
    from billing.constants import *
    from billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('InvoiceTestCase', 'BillingDeleteTestCase')


class InvoiceTestCase(_BillingTestCase, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'billing')

    def test_createview01(self):
        self.login()

        self.assertEqual(200, self.client.get('/billing/invoice/add').status_code)

        name = 'Invoice001'
        currency = Currency.objects.all()[0]
        source = Organisation.objects.create(user=self.user, name='Source Orga')
        target = Organisation.objects.create(user=self.user, name='Target Orga')

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

        #target = Organisation.objects.get(pk=target.id)
        target = self.refresh(target)
        #b_addr = target.billing_address
        #s_addr = target.shipping_address
        #self.assertTrue(b_addr)
        #self.assertTrue(s_addr)
        #self.assertEqual(b_addr, invoice.billing_address)
        #self.assertEqual(s_addr, invoice.shipping_address)
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

    def assertAddressContentEqual(self, address1, address2): #TODO: move in persons ??
        for f in ('name', 'address', 'po_box', 'zipcode', 'city', 'department', 'state', 'country'):
            self.assertEqual(getattr(address1, f), getattr(address1, f))

    def test_createview02(self):
        self.login()

        name = 'Invoice001'

        #source = Organisation.objects.create(user=self.user, name='Source Orga')
        #CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=source)
        source = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]

        target = Organisation.objects.create(user=self.user, name='Target Orga')

        create_addr = partial(Address.objects.create, owner=target)
        target.shipping_address = create_addr(name='ShippingAddr', address='Temple of fire',
                                              po_box='6565', zipcode='789', city='Konoha',
                                              department='dep1', state='Stuff', country='Land of Fire'
                                             )
        target.billing_address  = create_addr(name='BillingAddr', address='Temple of sand',
                                              po_box='8778', zipcode='123', city='Suna',
                                              department='dep2', state='Foo',   country='Land of Sand'
                                             )
        target.save()

        self.assertEqual(source.id, self.client.get('/billing/invoice/add').context['form']['source'].field.initial)

        invoice = self.create_invoice(name, source, target)

        #self.assertEqual(target.billing_address.id,  invoice.billing_address_id)
        #self.assertEqual(target.shipping_address.id, invoice.shipping_address_id)
        self.assertAddressContentEqual(target.billing_address, invoice.billing_address)
        self.assertEqual(invoice, invoice.billing_address.owner)

        self.assertAddressContentEqual(target.shipping_address, invoice.shipping_address)
        self.assertEqual(invoice, invoice.shipping_address.owner)

        url = invoice.get_absolute_url()
        self.assertEqual('/billing/invoice/%s' % invoice.id, url)
        self.assertEqual(200, self.client.get(url).status_code)

    def test_createview03(self): #creds errors with Organisation
        self.login(is_superuser=False)

        role = self.user.role
        create_sc = SetCredentials.objects.create
        create_sc(role=role,
                  value=EntityCredentials.VIEW | EntityCredentials.CHANGE | \
                        EntityCredentials.DELETE | EntityCredentials.UNLINK, #no LINK
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(role=role,
                  value=EntityCredentials.VIEW | EntityCredentials.CHANGE | \
                        EntityCredentials.DELETE | EntityCredentials.LINK | \
                        EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )
        role.creatable_ctypes = [ContentType.objects.get_for_model(Invoice)]

        source = Organisation.objects.create(user=self.other_user, name='Source Orga')
        self.assertFalse(source.can_link(self.user))

        target = Organisation.objects.create(user=self.other_user, name='Target Orga')
        self.assertFalse(target.can_link(self.user))

        response = self.client.get('/billing/invoice/add', follow=True)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('source', form.fields, 'Bad form ?!')

        response = self.client.post('/billing/invoice/add', follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            'Invoice001',
                                          'issuing_date':    '2011-9-7',
                                          'expiration_date': '2011-10-13',
                                          'status':          1,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertEqual(200, response.status_code)

        #TODO: use assertFormError()
        try:
            errors = response.context['form'].errors
        except Exception as e:
            self.fail(str(e))

        self.assertTrue(errors)
        self.assertIn('source', errors)
        self.assertIn('target', errors)

    def test_create_from_a_detailview01(self):
        self.login()

        name = 'Invoice001'
        #source = Organisation.objects.create(user=self.user, name='Source Orga')
        #CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME, creme_entity=source)
        source = Organisation.objects.filter(properties__type=PROP_IS_MANAGED_BY_CREME)[0]
        target = Organisation.objects.create(user=self.user, name='Target Orga')

        url = '/billing/invoice/add/%s' % target.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(source.id, form['source'].field.initial)
        #self.assertEqual(target.id, form['target'].field.initial) #TODO: should work ?
        self.assertEqual(target, form.initial.get('target'))

        currency = Currency.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2010-10-13',
                                          'status':          1,
                                          'currency':        currency.pk,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertEqual(target, invoice.get_target().get_real_entity())

    def test_listview(self):
        self.login()

        create = Organisation.objects.create
        source = create(user=self.user, name='Source Orga')
        target = create(user=self.user, name='Target Orga')

        invoice1 = self.create_invoice('invoice 01', source, target)
        invoice2 = self.create_invoice('invoice 02', source, target)

        response = self.client.get('/billing/invoices')
        self.assertEqual(200, response.status_code)

        with self.assertNoException():
            invoices_page = response.context['entities']

        self.assertEqual(2, invoices_page.paginator.count)
        self.assertEqual(set([invoice1, invoice2]), set(invoices_page.paginator.object_list))

    def test_editview01(self):
        self.login()

        #Test when not all relation with organisations exist
        invoice = Invoice.objects.create(user=self.user, name='invoice01',
                                         expiration_date=date(year=2010, month=12, day=31),
                                         status_id=1, number='INV0001', currency_id=1
                                        )

        self.assertGET200('/billing/invoice/edit/%s' % invoice.id)

    def test_editview02(self):
        self.login()

        name = 'Invoice001'
        invoice, source, target = self.create_invoice_n_orgas(name)

        url = '/billing/invoice/edit/%s' % invoice.id
        self.assertGET200(url)

        name += '_edited'

        create_orga = Organisation.objects.create
        source = create_orga(user=self.user, name='Source Orga 2')
        target = create_orga(user=self.user, name='Target Orga 2')

        currency = Currency.objects.all()[0]
        response = self.client.post(url, follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2010-9-7',
                                          'expiration_date': '2011-11-14',
                                          'status':          1,
                                          'currency':        currency.pk,
                                          'discount':        Decimal(),
                                          'discount_unit':   1,
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        self.assertEqual(1, len(response.redirect_chain))
        self.assertTrue(response.redirect_chain[0][0].endswith('/billing/invoice/%s' % invoice.id))

        invoice = self.refresh(invoice)
        self.assertEqual(name, invoice.name)
        self.assertEqual(date(year=2011, month=11, day=14), invoice.expiration_date)

        self.assertEqual(source, invoice.get_source().get_real_entity())
        self.assertEqual(target, invoice.get_target().get_real_entity())

        self.assertRelationCount(1, source, REL_OBJ_BILL_ISSUED,   invoice)
        self.assertRelationCount(1, target, REL_OBJ_BILL_RECEIVED, invoice)

    def test_editview03(self): #user changes => lines user changes
        self.login()

        user = self.user

        #simpler to test with 2 super users (do not have to create SetCredentials etc...)
        other_user = self.other_user
        other_user.superuser = True
        other_user.save()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001', user=user)
        self.assertEqual(user, invoice.user)


        lines = [ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item="otf1",             unit_price=Decimal("1")),
                 ProductLine.objects.create(user=user, related_document=invoice, related_item=self.create_product(), unit_price=Decimal("2")),
                 ServiceLine.objects.create(user=user, related_document=invoice, on_the_fly_item="otf2",             unit_price=Decimal("4")),
                 ServiceLine.objects.create(user=user, related_document=invoice, related_item=self.create_service(), unit_price=Decimal("5")),
                ]

        response = self.client.post('/billing/invoice/edit/%s' % invoice.id, follow=True,
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
                         list(Line.objects.filter(pk__in=[l.pk for l in lines]).values_list('user', flat=True)) #refresh
                        )

    def test_generate_number01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.number)
        self.assertEqual(1, invoice.status_id)
        self.assertEqual(1, invoice.currency_id)

        issuing_date = invoice.issuing_date
        self.assertTrue(issuing_date)

        url = '/billing/invoice/generate_number/%s' % invoice.id
        self.assertGET404(url, follow=True)
        self.assertPOST200(url, follow=True)

        invoice = self.refresh(invoice)
        number    = invoice.number
        status_id = invoice.status_id
        self.assertTrue(number)
        self.assertEqual(2,            status_id)
        self.assertEqual(issuing_date, invoice.issuing_date)

        #already generated
        self.assertPOST404(url, follow=True)
        invoice = self.refresh(invoice)
        self.assertEqual(number,    invoice.number)
        self.assertEqual(status_id, invoice.status_id)

    def test_generate_number02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice.issuing_date = None
        invoice.save()

        self.assertPOST200('/billing/invoice/generate_number/%s' % invoice.id, follow=True)

        invoice = self.refresh(invoice)
        self.assertTrue(invoice.issuing_date)
        self.assertEqual(date.today(), invoice.issuing_date) #NB this test can fail if run at midnight...

    def test_product_lines_property01(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        with self.assertNumQueries(1):
            length = len(invoice.product_lines)

        self.assertEqual(0, length)

        with self.assertNumQueries(0):
            bool(invoice.product_lines)

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')
        self.assertRelationCount(1, invoice, REL_SUB_HAS_LINE, product_line)

        invoice = self.refresh(invoice)
        self.assertEqual([product_line], invoice.product_lines)

        product_line.delete()
        self.assertFalse(self.refresh(invoice).product_lines)

    def test_product_lines_property02(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        product_line1 = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy product') #TODO: factorise
        product_line2 = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy product2')
        ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy service')
        self.assertEqual([product_line1, product_line2], self.refresh(invoice).product_lines)

    def test_service_lines_property01(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.service_lines)

        service_line = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')
        self.assertEqual([service_line], self.refresh(invoice).service_lines)

        service_line.delete()
        self.assertFalse(self.refresh(invoice).service_lines)

    def test_service_lines_property02(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

        ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy product')
        service_line1 = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy service1')
        service_line2 = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy service2')
        self.assertEqual([service_line1, service_line2], self.refresh(invoice).service_lines)

    def test_get_lines01(self):
        self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.get_lines(Line))

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy product')
        service_line = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy service')

        self.assertEqual(set([product_line.id, service_line.id]),
                         set(invoice.get_lines(Line).values_list('pk', flat=True))
                        )

        self.assertEqual([product_line.pk], list(invoice.get_lines(ProductLine).values_list('pk', flat=True)))
        self.assertEqual([service_line.pk], list(invoice.get_lines(ServiceLine).values_list('pk', flat=True)))

    def test_total_vat(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertEqual(0, invoice._get_total_with_tax())

        product_line = ProductLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy product', quantity=3, unit_price=Decimal("5"))
        expected = product_line.get_price_inclusive_of_tax()
        self.assertEqual(Decimal('15.00'), expected)

        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

        service_line = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyy service', quantity=9, unit_price=Decimal("10"))
        expected = product_line.get_price_inclusive_of_tax() + service_line.get_price_inclusive_of_tax()
        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

    def test_clone_with_lines01(self):
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        user = self.user

        ServiceLine.objects.create(user=user, related_document=invoice, related_item=self.create_service())
        ServiceLine.objects.create(user=user, related_document=invoice, on_the_fly_item="otf service")
        ProductLine.objects.create(user=user, related_document=invoice, related_item=self.create_product())
        ProductLine.objects.create(user=user, related_document=invoice, on_the_fly_item="otf product")

        cloned = invoice.clone()

        cloned = self.refresh(cloned)
        invoice = self.refresh(invoice)

        self.assertNotEqual(invoice, cloned)#Not the same pk
        self.assertEqual(invoice.get_source(), cloned.get_source())
        self.assertEqual(invoice.get_target(), cloned.get_target())

        self.assertEqual(2, len(invoice.service_lines))
        self.assertEqual(2, len(invoice.product_lines))

        self.assertEqual(2, len(cloned.service_lines))
        self.assertEqual(2, len(cloned.product_lines))

        self.assertFalse(set(p.pk for p in invoice.service_lines) & set(p.pk for p in cloned.service_lines))
        self.assertFalse(set(p.pk for p in invoice.product_lines) & set(p.pk for p in cloned.product_lines))

    def test_clone_source_n_target(self): #internal relationtypes should not be cloned
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        cloned_source = source.clone()
        cloned_target = target.clone()

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED,   cloned_source)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, cloned_target)

    def test_discounts(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=10)[0]

        product_line = ProductLine.objects.create(user=self.user,
                                                  related_document=invoice,
                                                  on_the_fly_item='Flyyy product',
                                                  unit_price=Decimal('1000.00'), quantity=2,
                                                  discount=Decimal('10.00'), discount_unit=PERCENT_PK, total_discount=False,
                                                  vat_value=Vat.get_default_vat(),
                                                 )
        self.assertEqual(1620, product_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1620, invoice._get_total())
        self.assertEqual(1620, invoice.total_no_vat)

        service_line = ServiceLine.objects.create(user=self.user,
                                                  related_document=invoice,
                                                  on_the_fly_item='Flyyy service',
                                                  unit_price=Decimal('20.00'), quantity=10,
                                                  discount=Decimal('100.00'), discount_unit=AMOUNT_PK, total_discount=True,
                                                  vat_value=Vat.get_default_vat(),
                                                 )
        self.assertEqual(90, service_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1710, invoice._get_total()) #total_exclusive_of_tax
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

        self.assertGET200('/creme_config/billing/payment_terms/portal/')

        pterms = PaymentTerms.objects.create(name='3 months')

        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.payment_terms = pterms
        invoice.save()

        self.assertPOST200('/creme_config/billing/payment_terms/delete', data={'id': pterms.pk})
        self.assertFalse(PaymentTerms.objects.filter(pk=pterms.pk).exists())

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertIsNone(invoice.payment_terms)

    def test_delete_currency(self):
        self.login()

        currency = Currency.objects.create(name=u'Berry', local_symbol=u'B', international_symbol=u'BRY')
        invoice = self.create_invoice_n_orgas('Nerv', currency=currency)[0]

        self.assertPOST404('/creme_config/creme_core/currency/delete', data={'id': currency.pk})
        self.assertTrue(Currency.objects.filter(pk=currency.pk).exists())

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertEqual(currency, invoice.currency)

    def test_delete_additional_info(self):
        self.login()

        info = AdditionalInformation.objects.create(name='Agreement')
        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.additional_info = info
        invoice.save()

        self.assertPOST200('/creme_config/billing/additional_information/delete', data={'id': info.pk})
        self.assertFalse(AdditionalInformation.objects.filter(pk=info.pk).exists())

        invoice = self.get_object_or_fail(Invoice, pk=invoice.pk)
        self.assertIsNone(invoice.additional_info)


class BillingDeleteTestCase(_BillingTestCase, CremeTransactionTestCase):
    def setUp(self): #setUpClass does not work here
        #_BillingTestCase.setUp(self)
        self.populate('creme_core', 'creme_config', 'billing')
        self.login()

    def test_delete01(self):
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        service_line = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')

        b_addr = invoice.billing_address
        self.assertIsInstance(b_addr, Address)

        s_addr = invoice.billing_address
        self.assertIsInstance(s_addr, Address)

        invoice.delete()
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())
        self.assertFalse(ServiceLine.objects.filter(pk=service_line.pk).exists())

        with self.assertNoException(): #TODO: use get_object_or_fail
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)

        self.assertFalse(Address.objects.filter(pk=b_addr.id).exists())
        self.assertFalse(Address.objects.filter(pk=s_addr.id).exists())

    def test_delete02(self):#Can't be deleted
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        service_line = ServiceLine.objects.create(user=self.user, related_document=invoice, on_the_fly_item='Flyyyyy')
        rel1 = Relation.objects.get(subject_entity=invoice.id, object_entity=service_line.id)

        #This relation prohibits the deletion of the invoice
        ce = CremeEntity.objects.create(user=self.user)
        rel2 = Relation.objects.create(subject_entity=invoice, object_entity=ce, type_id=REL_SUB_HAS, user=self.user)

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
