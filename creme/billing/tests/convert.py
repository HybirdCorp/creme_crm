# -*- coding: utf-8 -*-

try:
    from datetime import datetime, timedelta
    from decimal import Decimal
    from functools import partial

    from django.db.models.query_utils import Q
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import CremePropertyType, CremeProperty, SetCredentials

    from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER

    from creme.billing.models import *
    from creme.billing.constants import *
    from creme.billing.tests.base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('ConvertTestCase',)


class ConvertTestCase(_BillingTestCase, CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons', 'billing')

    def _convert(self, status_code, src, dest_type):
        self.assertPOST(status_code, '/billing/%s/convert/' % src.id,
                        data={'type': dest_type}, follow=True
                       )

    def test_convert01(self):
        self.login()

        quote, source, target = self.create_quote_n_orgas('My Quote')
        self.assertFalse(Invoice.objects.count())

        self._convert(200, quote, 'invoice')

        invoices = Invoice.objects.all()
        self.assertEqual(1, len(invoices))

        invoice = invoices[0]
        self.assertEqual(quote.issuing_date,    invoice.issuing_date)
        self.assertEqual(quote.expiration_date, invoice.expiration_date)
        self.assertEqual(quote.discount,        invoice.discount)
        self.assertEqual(quote.total_vat,       invoice.total_vat)
        self.assertEqual(quote.total_no_vat,    invoice.total_no_vat)
        self.assertEqual(quote.currency,        invoice.currency)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,       source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED,     object_entity=target)
        self.assertRelationCount(1, target,  REL_SUB_CUSTOMER_SUPPLIER, object_entity=source)

    def test_convert02(self):
        "SalesOrder + not superuser"
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote), get_ct(SalesOrder)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = self.create_quote_n_orgas('My Quote')[0]

        self._convert(200, quote, 'sales_order')
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual(1, SalesOrder.objects.count())

    def test_convert03(self):
        "Credentials (creation) errors"
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote)] #not get_ct(Invoice)
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = self.create_quote_n_orgas('My Quote')[0]
        self._convert(403, quote, 'invoice')
        self.assertFalse(Invoice.objects.exists())

    def test_convert04(self):
        "Credentials (view) errors"
        self.login(is_superuser=False, allowed_apps=['billing', 'persons'])

        get_ct = ContentType.objects.get_for_model
        self.role.creatable_ctypes = [get_ct(Quote), get_ct(Invoice)]
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   | EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   | EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        quote = Quote.objects.create(user=self.other_user, name='My Quote',
                                     issuing_date=datetime.now(),
                                     expiration_date=datetime.now() + timedelta(days=10),
                                     status=QuoteStatus.objects.all()[0],
                                     )
        self.assertFalse(quote.can_view(self.user))

        self._convert(403, quote, 'invoice')
        self.assertFalse(Invoice.objects.exists())

    def test_convert05(self):
        "Quote to Invoice with lines"
        self.login()

        quote, source, target = self.create_quote_n_orgas('My Quote')
        user = self.user

        create_pline = partial(ProductLine.objects.create, user=user, related_document=quote)
        product_line_otf = create_pline(on_the_fly_item="otf1",             unit_price=Decimal("1"))
        product_line     = create_pline(related_item=self.create_product(), unit_price=Decimal("2"))

        create_sline = partial(ServiceLine.objects.create, user=user, related_document=quote)
        service_line_otf = create_sline(on_the_fly_item="otf2",             unit_price=Decimal("4"))
        service_line     = create_sline(related_item=self.create_service(), unit_price=Decimal("5"))

        #quote.save()#To set total_vat...
        quote = self.refresh(quote)

        quote_property = CremeProperty.objects.create(creme_entity=quote, type=CremePropertyType.objects.all()[0])

        self.assertEqual(2, quote.get_lines(ServiceLine).count())
        self.assertEqual(2, quote.get_lines(ProductLine).count())

        self.assertFalse(Invoice.objects.exists())

        self._convert(200, quote, 'invoice')

        invoices = Invoice.objects.all()
        self.assertEqual(1, len(invoices))

        invoice = invoices[0]
        self.assertEqual(2, invoice.get_lines(ServiceLine).count())
        self.assertEqual(2, invoice.get_lines(ProductLine).count())

        q_otf_item = Q(on_the_fly_item=None)
        invoice_service_line     = invoice.get_lines(ServiceLine).get(q_otf_item)#Should be with the related_item
        invoice_service_line_otf = invoice.get_lines(ServiceLine).get(~q_otf_item)

        self.assertEqual(service_line.related_item,     invoice_service_line.related_item)
        self.assertEqual(service_line_otf.related_item, invoice_service_line_otf.related_item)

        invoice_product_line     = invoice.get_lines(ProductLine).get(q_otf_item)#Should be with the related_item
        invoice_product_line_otf = invoice.get_lines(ProductLine).get(~q_otf_item)

        self.assertEqual(product_line.related_item,     invoice_product_line.related_item)
        self.assertEqual(product_line_otf.related_item, invoice_product_line_otf.related_item)

        self.assertEqual(quote.issuing_date,    invoice.issuing_date)
        self.assertEqual(quote.expiration_date, invoice.expiration_date)
        self.assertEqual(quote.discount,        invoice.discount)
        self.assertEqual(quote.total_no_vat,    invoice.total_no_vat)
        self.assertEqual(quote.total_vat,       invoice.total_vat)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)

        properties = invoice.properties.all()
        self.assertEqual(1, len(properties))
        self.assertEqual(quote_property.type, properties[0].type)

    def test_convert06(self):
        "Quote -> SalesOrder : status id can not be converted (bugfix)"
        self.login()

        status = QuoteStatus.objects.create(name='Cashing', order=5)
        self.assertFalse(SalesOrderStatus.objects.filter(pk=status.pk).exists())

        quote = self.create_quote_n_orgas('My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'sales_order')

        orders = SalesOrder.objects.all()
        self.assertEqual(1, len(orders))
        self.assertEqual(1, orders[0].status_id)

    def test_convert07(self):
        "Quote -> Invoice : status id can not be converted (bugfix)"
        self.login()

        pk = 12
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk).exists())

        with self.assertNoException():
            status = QuoteStatus.objects.create(pk=pk, name='Cashing', order=5)

        quote = self.create_quote_n_orgas('My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'invoice')

        invoices = Invoice.objects.all()
        self.assertEqual(1, len(invoices))
        self.assertEqual(1, invoices[0].status_id)
