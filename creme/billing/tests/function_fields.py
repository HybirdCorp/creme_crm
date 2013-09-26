# -*- coding: utf-8 -*-

try:
    from itertools import chain
    import datetime

    from creme.creme_core.models import CremeProperty
    from creme.creme_core.core.function_field import FunctionField, FunctionFieldResult
    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

    from creme.persons.models import Organisation, Contact

    from ..models import QuoteStatus, InvoiceStatus, ProductLine
    from ..function_fields import (get_total_pending,
                                   get_total_won_quote_last_year,
                                   get_total_won_quote_this_year)
    from .base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('FunctionFieldTestCase',)


class FunctionFieldTestCase(_BillingTestCase):
    def setUp(self):
        #_BillingTestCase.setUp(self)
        self.login()
        self.won_status = QuoteStatus.objects.create(name='won_status',
                                                     won=True)
        self.pending_payment_status = InvoiceStatus.objects.create(name='pending_payment',
                                                                    pending_payment=True)
        self.today_date = datetime.date.today()

    def _set_manages_by_creme(self, entity):
        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME,
                                     creme_entity=entity)

    def create_line(self, related_document, unit_price, quantity):
        return ProductLine.objects.create(user=self.user,
                                          on_the_fly_item="on_the_fly_item",
                                          related_document=related_document,
                                          unit_price=unit_price,
                                          quantity=quantity,
                                          )

    def test_get_total_pending(self):
        invoice, source, target = self.create_invoice_n_orgas("SWAG")
        invoice.status = self.pending_payment_status
        invoice.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_pending(target))
        self.create_line(invoice, 5000, 1)
        self.assertEqual(5000, get_total_pending(target))

    def test_get_total_won_quote_last_year(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")
        quote.status = self.won_status
        year = datetime.timedelta(days=365)
        quote.acceptation_date = self.today_date - year
        quote.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_won_quote_last_year(target))
        self.create_line(quote, 5000, 1)
        self.assertEqual(5000, get_total_won_quote_last_year(target))

    def test_get_total_won_quote_this_year(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")
        quote.status = self.won_status
        quote.acceptation_date = self.today_date
        quote.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_won_quote_this_year(target))
        self.create_line(quote, 5000, 1)
        self.assertEqual(5000, get_total_won_quote_this_year(target))

    def test_functionfields(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")

        with self.assertNoException():
            off_mngr = Organisation.function_fields
            cff_mngr = Contact.function_fields

        for funf in chain(off_mngr, cff_mngr):
            self.assertIsInstance(funf, FunctionField)

            if funf.name in ('total_pending_payment',
                             'total_won_quote_this_year',
                             'total_won_quote_last_year'):
                self.assertEqual('0', funf(target).for_html())
