# -*- coding: utf-8 -*-

skip_billing = False

try:
    from datetime import date
    from decimal import Decimal
    from functools import partial
    from unittest import skipIf

    from django.apps import apps
    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Relation, RelationType, SettingValue, SetCredentials

    from creme.persons.constants import REL_SUB_PROSPECT, REL_SUB_CUSTOMER_SUPPLIER
    from creme.persons.tests.base import skipIfCustomOrganisation

    if apps.is_installed('creme.billing'):
        from creme import billing
        from creme.billing.models import QuoteStatus
        from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED

        Invoice     = billing.get_invoice_model()
        Quote       = billing.get_quote_model()
        SalesOrder  = billing.get_sales_order_model()
        ServiceLine = billing.get_service_line_model()
    else:
        skip_billing = True

    from creme.opportunities import constants

    from .base import OpportunitiesBaseTestCase, skipIfCustomOpportunity, Opportunity, Contact
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIf(skip_billing, '"Billing" app is not installed.')
@skipIfCustomOpportunity
class BillingTestCase(OpportunitiesBaseTestCase):
    def _build_currentquote_url(self, opportunity, quote, action='set_current'):
        return reverse('opportunities__linked_quote_is_current',
                       args=(opportunity.id, quote.id, action),
                      )

    def _build_gendoc_url(self, opportunity, model=None):
        model = model or Quote
        return reverse('opportunities__generate_billing_doc',
                       args=(opportunity.id, ContentType.objects.get_for_model(model).id),
                      )

    def _set_quote_config(self, use_current_quote):
        sv = SettingValue.objects.get(key_id=constants.SETTING_USE_CURRENT_QUOTE)
        sv.value = use_current_quote
        sv.save()

    def test_populate(self):
        ct = ContentType.objects.get_for_model(Opportunity)
        relation_types = RelationType.get_compatible_ones(ct).in_bulk()

        self.assertIn(constants.REL_OBJ_LINKED_SALESORDER, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_SALESORDER, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder])

        self.assertIn(constants.REL_OBJ_LINKED_INVOICE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_INVOICE, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice])

        self.assertIn(constants.REL_OBJ_LINKED_QUOTE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_QUOTE, relation_types)
        self.get_relationtype_or_fail(constants.REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote])

        self.get_relationtype_or_fail(constants.REL_OBJ_CURRENT_DOC, [Opportunity], [Invoice, Quote, SalesOrder])

    @skipIfCustomOrganisation
    def test_generate_new_doc01(self):
        self.login()

        self.assertEqual(0, Quote.objects.count())

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity)

        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        quotes = Quote.objects.all()
        self.assertEqual(1, len(quotes))

        quote = quotes[0]
        self.assertDatetimesAlmostEqual(date.today(), quote.issuing_date)
        self.assertEqual(1, quote.status_id)
        self.assertTrue(quote.number)

        name = quote.name
        self.assertIn(str(quote.number), name)
        self.assertIn(str(opportunity.name), name)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_generate_new_doc02(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity)

        self.client.post(url)
        quote1 = Quote.objects.all()[0]

        self.client.post(url)
        quotes = Quote.objects.exclude(pk=quote1.id)
        self.assertEqual(1, len(quotes))
        quote2 = quotes[0]

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, target, REL_SUB_PROSPECT, emitter)

    @skipIfCustomOrganisation
    def test_generate_new_doc03(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        url = self._build_gendoc_url(opportunity, Invoice)

        self.client.post(url)
        invoice1 = Invoice.objects.all()[0]

        self.client.post(url)
        invoices = Invoice.objects.exclude(pk=invoice1.id)
        self.assertEqual(1, len(invoices))

        invoices2 = invoices[0]
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoices2, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoices2, constants.REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, invoice1, REL_SUB_BILL_ISSUED,    emitter)
        self.assertRelationCount(1, invoice1, REL_SUB_BILL_RECEIVED,  target)
        self.assertRelationCount(1, invoice1, constants.REL_SUB_LINKED_INVOICE, opportunity)

        self.assertRelationCount(1, target, REL_SUB_CUSTOMER_SUPPLIER, emitter)

    @skipIfCustomOrganisation
    def test_generate_new_doc_error01(self):
        "Invalid target type"
        self.login()

        contact_count = Contact.objects.count()

        opportunity = self._create_opportunity_n_organisations()[0]
        self.assertPOST404(self._build_gendoc_url(opportunity, Contact))
        self.assertEqual(contact_count, Contact.objects.count())  # No Contact created

    @skipIfCustomOrganisation
    def test_generate_new_doc_error02(self):
        "Credentials problems"
        self.login(is_superuser=False, allowed_apps=['billing', 'opportunities'],
                   creatable_models=[Opportunity],  # Not Quote
                  )

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity)
        self.assertPOST403(url)

        role = self.role
        get_ct = ContentType.objects.get_for_model
        quote_ct = get_ct(Quote)
        role.creatable_ctypes.add(quote_ct)
        self.assertPOST403(url)

        create_sc = partial(SetCredentials.objects.create, role=role,
                            set_type=SetCredentials.ESET_ALL,
                           )
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE)
        self.assertPOST403(url)

        create_sc(value=EntityCredentials.LINK, ctype=get_ct(Opportunity))
        self.assertPOST403(url)

        create_sc(value=EntityCredentials.LINK, ctype=quote_ct)
        self.assertPOST200(url, follow=True)

    @skipIfCustomOrganisation
    def test_current_quote_1(self):
        self.login()

        opportunity, target, emitter = self._create_opportunity_n_organisations()
        gendoc_url = self._build_gendoc_url(opportunity)

        self.client.post(gendoc_url)
        quote1 = Quote.objects.all()[0]

        self.client.post(gendoc_url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        url = self._build_currentquote_url(opportunity, quote1)
        self.assertGET404(url)
        self.assertPOST200(url, follow=True)

        self.assertRelationCount(1, quote2, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote2, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote2, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC,   opportunity)

        self.assertRelationCount(1, quote1, REL_SUB_BILL_ISSUED,   emitter)
        self.assertRelationCount(1, quote1, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, quote1, constants.REL_SUB_LINKED_QUOTE,  opportunity)
        self.assertRelationCount(1, quote1, constants.REL_SUB_CURRENT_DOC,   opportunity)

    @skipIfCustomOrganisation
    def test_current_quote_2(self):
        "Refresh the estimated_sales when we change which quote is the current"
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        url = self._build_gendoc_url(opportunity)

        opportunity.estimated_sales = Decimal('1000')
        opportunity.made_sales = Decimal('0')
        opportunity.save()

        create_sline = partial(ServiceLine.objects.create, user=user)
        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        create_sline(related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal('300'))

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        quote2.status = QuoteStatus.objects.create(name="WONStatus", order=15, won=True)
        quote2.save()

        create_sline(related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal('500'))
        self.assertPOST200(self._build_currentquote_url(opportunity, quote1, action='unset_current'), follow=True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote2, action='unset_current'), follow=True)

        self._set_quote_config(True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat)  # 300
        self.assertEqual(opportunity.made_sales, Decimal('0'))  # 300

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1, action='unset_current'), follow=True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote2), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote2.total_no_vat)  # 500
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat + quote2.total_no_vat)  # 800
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

    @skipIfCustomOrganisation
    def test_current_quote_3(self):
        user = self.login()

        opportunity = self._create_opportunity_n_organisations()[0]
        self._set_quote_config(False)

        estimated_sales = Decimal('69')
        opportunity.estimated_sales = estimated_sales
        opportunity.save()

        self.client.post(self._build_gendoc_url(opportunity))
        quote1 = Quote.objects.all()[0]
        ServiceLine.objects.create(user=user, related_document=quote1,
                                   on_the_fly_item='Foobar', unit_price=Decimal("300")
                                  )

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, opportunity.get_total())  # 69
        self.assertEqual(opportunity.estimated_sales, estimated_sales)  # 69

    @skipIfCustomOrganisation
    def test_current_quote_4(self):
        user = self.login()
        self._set_quote_config(True)

        opportunity = self._create_opportunity_n_organisations()[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        ServiceLine.objects.create(user=user, related_document=quote,
                                   on_the_fly_item='Stuff', unit_price=Decimal("300"),
                                  )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

    @skipIfCustomOrganisation
    def test_current_quote_5(self):
        user = self.login()
        self._set_quote_config(True)

        opportunity = self._create_opportunity_n_organisations()[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        self.assertEqual(0, self.refresh(quote).total_no_vat)
        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

        ServiceLine.objects.create(user=user, related_document=quote,
                                   on_the_fly_item='Stuff', unit_price=Decimal("300"),
                                  )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

        Relation.objects.filter(type__in=(constants.REL_SUB_CURRENT_DOC,
                                          constants.REL_OBJ_CURRENT_DOC
                                         ),
                               ).delete()

        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

    def test_current_quote_6(self):
        "Avoid queries when the billing instance has just been created"
        if billing.quote_model_is_custom():
            return

        user = self.login()

        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]

        with context:
            quote = Quote.objects.create(user=user,
                                         name='My Quote',
                                         status=status,
                                        )

        self.assertTrue(quote.pk)

        key_id = constants.SETTING_USE_CURRENT_QUOTE

        for query_info in context.captured_queries:
            self.assertNotIn(key_id, query_info['sql'])

    @skipIfCustomOrganisation
    def test_current_quote_7(self):
        "Delete the relationship REL_SUB_LINKED_QUOTE => REL_SUB_CURRENT_DOC is deleted too."
        user = self.login()
        self._set_quote_config(True)

        opp1, target, emitter = self._create_opportunity_n_organisations(name='Opp#1')
        self.client.post(self._build_gendoc_url(opp1))

        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2',
            sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )
        self.client.post(self._build_gendoc_url(opp2))

        linked_rel1 = self.get_object_or_fail(Relation,
                                             subject_entity=opp1.id,
                                             type=constants.REL_OBJ_LINKED_QUOTE,
                                            )
        quote1 = linked_rel1.object_entity.get_real_entity()
        self.assertRelationCount(1, quote1, constants.REL_SUB_CURRENT_DOC, opp1)

        ServiceLine.objects.create(user=user, related_document=quote1,
                                   on_the_fly_item='Stuff', unit_price=Decimal('42'),
                                  )
        self.assertEqual(42, self.refresh(quote1).total_no_vat)
        self.assertEqual(42, self.refresh(opp1).estimated_sales)

        linked_rel2 = self.get_object_or_fail(Relation,
                                              subject_entity=opp2.id,
                                              type=constants.REL_OBJ_LINKED_QUOTE,
                                             )
        quote2 = linked_rel2.object_entity.get_real_entity()
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC, opp2)

        linked_rel1.delete()
        self.assertRelationCount(0, quote1, constants.REL_SUB_CURRENT_DOC, opp1)
        self.assertRelationCount(1, quote2, constants.REL_SUB_CURRENT_DOC, opp2)  # Not deleted

        self.assertFalse(self.refresh(opp1).estimated_sales)  # estimated_sales refreshed
