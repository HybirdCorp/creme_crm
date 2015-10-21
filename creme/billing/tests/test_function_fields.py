# -*- coding: utf-8 -*-

try:
    import datetime
    from itertools import chain

    from django.utils.formats import number_format
    from django.utils.translation import ugettext as _

    from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
    from creme.creme_core.core.function_field import FunctionField
    from creme.creme_core.models import CremeProperty, FieldsConfig

    from creme.persons import get_contact_model
    from creme.persons.models import Organisation #, Contact
    from creme.persons.tests.base import skipIfCustomOrganisation

    from ..function_fields import (get_total_pending,
            get_total_won_quote_last_year, get_total_won_quote_this_year)
    from ..models import Quote, QuoteStatus, InvoiceStatus, ProductLine
    from .base import (_BillingTestCase, skipIfCustomProductLine,
            skipIfCustomQuote, skipIfCustomInvoice)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomOrganisation
class FunctionFieldTestCase(_BillingTestCase):
    def setUp(self):
        #_BillingTestCase.setUp(self)
        self.login()
        self.won_status = QuoteStatus.objects.create(name='won_status', won=True)
        self.pending_payment_status = InvoiceStatus.objects.create(name='pending_payment',
                                                                   pending_payment=True,
                                                                  )
        self.today_date = datetime.date.today()

    def _set_manages_by_creme(self, entity):
        CremeProperty.objects.create(type_id=PROP_IS_MANAGED_BY_CREME,
                                     creme_entity=entity,
                                    )

    def create_line(self, related_document, unit_price, quantity):
        return ProductLine.objects.create(user=self.user,
                                          on_the_fly_item="on_the_fly_item",
                                          related_document=related_document,
                                          unit_price=unit_price,
                                          quantity=quantity,
                                         )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending(self):
        invoice, source, target = self.create_invoice_n_orgas("SWAG")
        invoice.status = self.pending_payment_status
        invoice.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_pending(target))

        self.create_line(invoice, 5000, 1)
        self.assertEqual(5000, get_total_pending(target))

        funf = target.function_fields.get('total_pending_payment')
        self.assertIsNotNone(funf)

        val = number_format('5000.00', use_l10n=True)
        self.assertEqual(val, funf(target).for_html())
        self.assertEqual(val, funf(target).for_csv())

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year01(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")
        quote.status = self.won_status
        year = datetime.timedelta(days=365)
        quote.acceptation_date = self.today_date - year
        quote.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_won_quote_last_year(target))

        self.create_line(quote, 5000, 1)
        self.assertEqual(5000, get_total_won_quote_last_year(target))

        funf = target.function_fields.get('total_won_quote_last_year')
        self.assertIsNotNone(funf)

        val = number_format('5000.00', use_l10n=True)
        self.assertEqual(val, funf(target).for_html())
        self.assertEqual(val, funf(target).for_csv())

        # TODO: use self.assertNumQueries()

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year02(self):
        "'acceptation_date' is hidden"
        quote, source, target = self.create_quote_n_orgas("YOLO")

        FieldsConfig.create(Quote,
                            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})]
                           )

        quote.acceptation_date = self.today_date #- year
        self._set_manages_by_creme(source)

        with self.assertNumQueries(1):
            total = get_total_won_quote_last_year(target)

        self.assertEqual(_(u'Error: «Acceptation date» is hidden'), total)

        with self.assertNumQueries(0):
            get_total_won_quote_last_year(target)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year03(self):
        "'acceptation_date' is hidden + populate_entities()"
        quote1, source1, target1 = self.create_quote_n_orgas("Quote1")
        quote2, source2, target2 = self.create_quote_n_orgas("Quote2")

        FieldsConfig.create(Quote,
                            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})]
                           )

        funf = target1.function_fields.get('total_won_quote_last_year')

        with self.assertNumQueries(1):
            funf.populate_entities([target1, target2])

        with self.assertNumQueries(0):
            get_total_won_quote_last_year(target1)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year01(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")
        quote.status = self.won_status
        quote.acceptation_date = self.today_date
        quote.save()
        self._set_manages_by_creme(source)
        self.assertEqual(0, get_total_won_quote_this_year(target))

        self.create_line(quote, 5000, 1)
        self.assertEqual(5000, get_total_won_quote_this_year(target))

        funf = target.function_fields.get('total_won_quote_this_year')
        self.assertIsNotNone(funf)

        val = number_format('5000.00', use_l10n=True)
        self.assertEqual(val, funf(target).for_html())
        self.assertEqual(val, funf(target).for_csv())

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year02(self):
        "'acceptation_date' is hidden + populate_entities()"
        quote1, source1, target1 = self.create_quote_n_orgas("Quote1")
        quote2, source2, target2 = self.create_quote_n_orgas("Quote2")

        FieldsConfig.create(Quote,
                            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})]
                           )

        funf = target1.function_fields.get('total_won_quote_this_year')

        with self.assertNumQueries(1):
            funf.populate_entities([target1, target2])

        with self.assertNumQueries(0):
            total = funf(target1).for_csv()

        self.assertEqual(_(u'Error: «Acceptation date» is hidden'), total)

    @skipIfCustomQuote
    def test_functionfields(self):
        quote, source, target = self.create_quote_n_orgas("YOLO")

        with self.assertNoException():
            off_mngr = Organisation.function_fields
#            cff_mngr = Contact.function_fields
            cff_mngr = get_contact_model().function_fields

        for funf in chain(off_mngr, cff_mngr):
            self.assertIsInstance(funf, FunctionField)

            if funf.name in ('total_pending_payment',
                             'total_won_quote_this_year',
                             'total_won_quote_last_year'):
                self.assertEqual('0', funf(target).for_html())
