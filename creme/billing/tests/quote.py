# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal

    from creme.creme_core.models import Currency

    from creme.persons.constants import REL_SUB_PROSPECT

    from ..models import QuoteStatus, Quote
    from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
    from .base import _BillingTestCase
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('QuoteTestCase',)


class QuoteTestCase(_BillingTestCase):
    def setUp(self):
        #_BillingTestCase.setUp(self)
        self.login()

    def test_createview01(self):
        self.assertGET200('/billing/quote/add')

        quote, source, target = self.create_quote_n_orgas('My Quote')
        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)

        self.assertRelationCount(1, quote,  REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote,  REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT,      source)

        quote, source, target = self.create_quote_n_orgas('My Quote Two')
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, source)

    def test_editview(self):
        name = 'my quote'
        quote, source, target = self.create_quote_n_orgas(name)

        url = '/billing/quote/edit/%s' % quote.id
        self.assertGET200(url)

        name     = name.title()
        currency = Currency.objects.create(name=u'Marsian dollar', local_symbol=u'M$', international_symbol=u'MUSD', is_custom=True)
        status   = QuoteStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            self.user.pk,
                                          'name':            name,
                                          'issuing_date':    '2012-2-12',
                                          'expiration_date': '2012-3-13',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        quote = self.refresh(quote)
        self.assertEqual(name,                             quote.name)
        self.assertEqual(date(year=2012, month=2, day=12), quote.issuing_date)
        self.assertEqual(date(year=2012, month=3, day=13), quote.expiration_date)
        self.assertEqual(currency,                         quote.currency)
        self.assertEqual(status,                           quote.status)

    def test_listview(self):
        quote1 = self.create_quote_n_orgas('Quote1')[0]
        quote2 = self.create_quote_n_orgas('Quote2')[0]

        response = self.assertGET200('/billing/quotes')

        with self.assertNoException():
            quotes_page = response.context['entities']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertEqual(set([quote1, quote2]), set(quotes_page.paginator.object_list))

    def test_delete_status01(self):
        status = QuoteStatus.objects.create(name='OK')
        self.assertDeleteStatusOK(status, 'quote_status')

    def test_delete_status02(self):
        status = QuoteStatus.objects.create(name='OK')
        quote = self.create_quote_n_orgas('Nerv', status=status)[0]

        self.assertDeleteStatusKO(status, 'quote_status', quote)

    def test_csv_import(self):
        self._aux_test_csv_import(Quote, QuoteStatus)
