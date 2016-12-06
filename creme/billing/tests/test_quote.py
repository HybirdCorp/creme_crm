# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial

    from django.core.urlresolvers import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth import EntityCredentials
    from creme.creme_core.models import SetCredentials, Currency

    from creme.persons.constants import REL_SUB_PROSPECT
    from creme.persons.tests.base import skipIfCustomOrganisation, skipIfCustomAddress

    from ..models import QuoteStatus
    from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
    from .base import (_BillingTestCase, skipIfCustomQuote, skipIfCustomServiceLine,
           Organisation, Address, Quote, ServiceLine)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteTestCase(_BillingTestCase):
    # def setUp(self):
    #     # _BillingTestCase.setUp(self)
    #     self.login()

    def test_createview01(self):
        self.login()
        self.assertGET200(reverse('billing__create_quote'))

        quote, source, target = self.create_quote_n_orgas('My Quote')
        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)

        self.assertRelationCount(1, quote,  REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote,  REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT,      source)

        quote, source, target = self.create_quote_n_orgas('My Quote Two')
        self.assertRelationCount(1, target, REL_SUB_PROSPECT, source)

    def test_create_related(self):
        user = self.login()

        source, target = self.create_orgas()
        url = reverse('billing__create_related_quote', args=(target.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual({'status': 1,
                          'target': target,
                         },
                         form.initial
                        )

        name = 'Quote#1'
        currency = Currency.objects.all()[0]
        status   = QuoteStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2013-12-14',
                                          'expiration_date': '2014-1-21',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertEqual(date(year=2013, month=12, day=14), quote.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=21), quote.expiration_date)
        self.assertEqual(currency, quote.currency)
        self.assertEqual(status,   quote.status)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_editview01(self):
        user = self.login()

        name = 'my quote'
        quote, source, target = self.create_quote_n_orgas(name)

        url = quote.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        currency = Currency.objects.create(name=u'Marsian dollar', local_symbol=u'M$',
                                           international_symbol=u'MUSD', is_custom=True,
                                          )
        status = QuoteStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':     '2012-2-12',
                                          'expiration_date':  '2012-3-14',
                                          'acceptation_date': '2012-3-13',
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
        self.assertEqual(date(year=2012, month=3, day=14), quote.expiration_date)
        self.assertEqual(date(year=2012, month=3, day=13), quote.acceptation_date)
        self.assertEqual(currency,                         quote.currency)
        self.assertEqual(status,                           quote.status)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_editview02(self):
        "Change source/target + perms"
        user = self.login(is_superuser=False,
                          allowed_apps=('persons', 'billing'),
                          creatable_models=[Quote],
                         )

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE |
                        EntityCredentials.LINK | EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc(value=EntityCredentials.VIEW,
                  set_type=SetCredentials.ESET_ALL,
                 )

        quote, source1, target1 = self.create_quote_n_orgas('My quote')

        unlinkable_source, unlinkable_target = self.create_orgas(user=self.other_user)
        self.assertFalse(user.has_perm_to_link(unlinkable_source))
        self.assertFalse(user.has_perm_to_link(unlinkable_target))

        def post(source, target):
            return self.client.post(quote.get_edit_absolute_url(), follow=True,
                                    data={'user':       user.pk,
                                          'name':       quote.name,
                                          'status':     quote.status_id,
                                          'currency':   quote.currency_id,
                                          'discount':   quote.discount,
                                          'source':     source.id,
                                          'target':     self.genericfield_format_entity(target),
                                         }
                                   )

        response = post(unlinkable_source, unlinkable_target)
        self.assertEqual(200, response.status_code)
        msg_fmt = _(u'You are not allowed to link this entity: %s')
        self.assertFormError(response, 'form', 'source', msg_fmt % unlinkable_source)
        self.assertFormError(response, 'form', 'target', msg_fmt % unlinkable_target)

        # ----
        source2, target2 = self.create_orgas(user=user)
        self.assertNoFormError(post(source2, target2))

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source2)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target2)

        self.assertRelationCount(0, quote, REL_SUB_BILL_ISSUED,   source1)
        self.assertRelationCount(0, quote, REL_SUB_BILL_RECEIVED, target1)

    def test_editview03(self):
        "Change source/target + perms: unlinkable but not changed"
        user = self.login(is_superuser=False,
                          allowed_apps=('persons', 'billing'),
                          creatable_models=[Quote],
                         )

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE |
                        EntityCredentials.DELETE |
                        EntityCredentials.LINK | EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN,
                 )
        create_sc(value=EntityCredentials.VIEW,
                  set_type=SetCredentials.ESET_ALL,
                 )

        quote, source, target = self.create_quote_n_orgas('My quote')

        source.user = target.user = self.other_user
        source.save(); target.save()
        self.assertFalse(user.has_perm_to_link(source))
        self.assertFalse(user.has_perm_to_link(target))

        status = QuoteStatus.objects.exclude(id=quote.status_id).first()
        response = self.client.post(quote.get_edit_absolute_url(), follow=True,
                                    data={'user':     user.pk,
                                          'name':     quote.name,
                                          'status':   status.id,
                                          'currency': quote.currency_id,
                                          'discount': quote.discount,
                                          'source':   source.id,
                                          'target':   self.genericfield_format_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(status, self.refresh(quote).status)
        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_listview(self):
        self.login()

        quote1 = self.create_quote_n_orgas('Quote1')[0]
        quote2 = self.create_quote_n_orgas('Quote2')[0]

        response = self.assertGET200(Quote.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['entities']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertEqual({quote1, quote2}, set(quotes_page.paginator.object_list))

    def test_delete_status01(self):
        self.login()
        status = QuoteStatus.objects.create(name='OK')
        self.assertDeleteStatusOK(status, 'quote_status')

    def test_delete_status02(self):
        self.login()
        status = QuoteStatus.objects.create(name='OK')
        quote = self.create_quote_n_orgas('Nerv', status=status)[0]

        self.assertDeleteStatusKO(status, 'quote_status', quote)

    @skipIfCustomAddress
    def test_csv_import(self):
        self.login()
        self._aux_test_csv_import(Quote, QuoteStatus)

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        target.billing_address = b_addr = \
            Address.objects.create(name="Billing address 01",
                                   address="BA1 - Address", city="BA1 - City",
                                   owner=target,
                                  )
        target.save()

        # status = QuoteStatus.objects.filter(is_default=False)[0] TODO

        quote = self.create_quote('Quote001', source, target,
                                  # status=status,
                                 )
        quote.acceptation_date = date.today()
        quote.save()

        sl = ServiceLine.objects.create(related_item=self.create_service(),
                                        user=user, related_document=quote,
                                       )

        cloned = self.refresh(quote.clone())
        quote = self.refresh(quote)

        self.assertIsNone(cloned.acceptation_date)
        # self.assertTrue(cloned.status.is_default) TODO

        self.assertNotEqual(quote, cloned)  # Not the same pk
        self.assertEqual(source, cloned.get_source().get_real_entity())
        self.assertEqual(target, cloned.get_target().get_real_entity())

        # Lines are cloned
        self.assertEqual(1, len(cloned.service_lines))
        self.assertNotEqual([sl], list(cloned.service_lines))

        # Addresses are cloned
        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,      billing_address.owner)
        self.assertEqual(b_addr.name, billing_address.name)
        self.assertEqual(b_addr.city, billing_address.city)

    def test_num_queries(self):
        "Avoid the queries about line sa creation (because these queries can be really slow with a lot of entities)"
        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        user = self.login()

        # NB: we do not use assertNumQueries, because external signal handlers can add their owns queries
        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]

        with context:
            quote = Quote.objects.create(user=user, name='My Quote', status=status)

        self.assertTrue(quote.pk)
        self.assertEqual(0, quote.total_no_vat)
        self.assertEqual(0, quote.total_vat)

        for query_info in context.captured_queries:
            query = query_info['sql']
            self.assertNotIn('billing_productline', query)
            self.assertNotIn('billing_serviceline', query)
