from datetime import date
from decimal import Decimal
from functools import partial
from unittest import skipIf

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import Relation, RelationType, SettingValue, Vat
from creme.opportunities import constants
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER, REL_SUB_PROSPECT
from creme.persons.tests.base import skipIfCustomOrganisation
from creme.products import get_product_model, get_service_model
from creme.products.models import SubCategory
from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

from .. import setting_keys
from ..models import SalesPhase
from .base import (
    Contact,
    OpportunitiesBaseTestCase,
    Opportunity,
    Organisation,
    skipIfCustomOpportunity,
)

if apps.is_installed('creme.billing'):
    skip_billing = False

    from creme import billing
    from creme.billing.constants import (
        REL_SUB_BILL_ISSUED,
        REL_SUB_BILL_RECEIVED,
    )
    from creme.billing.models import QuoteStatus

    Invoice     = billing.get_invoice_model()
    Quote       = billing.get_quote_model()
    SalesOrder  = billing.get_sales_order_model()
    ServiceLine = billing.get_service_line_model()
else:
    skip_billing = True


@skipIf(skip_billing, '"Billing" app is not installed.')
@skipIfCustomOpportunity
class BillingTestCase(OpportunitiesBaseTestCase):
    SELECTION_URL = reverse('opportunities__select_billing_objs_to_link')

    @staticmethod
    def _build_currentquote_url(opportunity, quote, action='set_current'):
        return reverse(
            'opportunities__linked_quote_is_current',
            args=(opportunity.id, quote.id, action),
        )

    @staticmethod
    def _build_gendoc_url(opportunity, model=None):
        model = model or Quote
        return reverse(
            'opportunities__generate_billing_doc',
            args=(opportunity.id, ContentType.objects.get_for_model(model).id),
        )

    @staticmethod
    def _set_quote_config(use_current_quote):
        sv = SettingValue.objects.get_4_key(setting_keys.quote_key)
        sv.value = use_current_quote
        sv.save()

    def test_populate(self):
        relation_types = RelationType.objects.compatible(Opportunity).in_bulk()

        self.assertIn(constants.REL_OBJ_LINKED_SALESORDER, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_SALESORDER, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_SALESORDER, [Opportunity], [SalesOrder],
        )

        self.assertIn(constants.REL_OBJ_LINKED_INVOICE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_INVOICE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_INVOICE, [Opportunity], [Invoice],
        )

        self.assertIn(constants.REL_OBJ_LINKED_QUOTE, relation_types)
        self.assertNotIn(constants.REL_SUB_LINKED_QUOTE, relation_types)
        self.get_relationtype_or_fail(
            constants.REL_OBJ_LINKED_QUOTE, [Opportunity], [Quote],
        )

        self.get_relationtype_or_fail(
            constants.REL_OBJ_CURRENT_DOC,
            [Opportunity],
            [Invoice, Quote, SalesOrder],
        )

    @skipIfCustomOrganisation
    @skipIfCustomProduct
    @skipIfCustomService
    def test_generate_new_doc__quote(self):
        user = self.login_as_root_and_get()
        self.assertEqual(0, Quote.objects.count())

        subcat = SubCategory.objects.first()
        product = get_product_model().objects.create(
            user=user,
            category=subcat.category,
            sub_category=subcat,
            unit_price=Decimal('12'),
            unit='pack',
        )
        service = get_service_model().objects.create(
            user=user,
            category=subcat.category,
            sub_category=subcat,
            unit_price=Decimal('15'),
            unit='week',
        )

        opp, target, emitter = self._create_opportunity_n_organisations(user=user)

        create_rel = partial(Relation.objects.create, user=user, object_entity=opp)
        create_rel(subject_entity=product, type_id=constants.REL_SUB_LINKED_PRODUCT)
        create_rel(subject_entity=service, type_id=constants.REL_SUB_LINKED_SERVICE)

        url = self._build_gendoc_url(opp)
        self.assertGET405(url)
        self.assertPOST200(url, follow=True)

        quote = self.get_alone_element(Quote.objects.all())
        self.assertEqual(date.today(), quote.issuing_date)
        self.assertEqual(1, quote.status_id)
        self.assertTrue(quote.number)
        self.assertEqual(f'{quote.number} — {opp.name}', quote.name)

        self.assertHaveRelation(quote, type=REL_SUB_BILL_ISSUED,   object=emitter)
        self.assertHaveRelation(quote, type=REL_SUB_BILL_RECEIVED, object=target)

        self.assertHaveRelation(quote, type=constants.REL_SUB_LINKED_QUOTE,  object=opp)
        self.assertHaveRelation(quote, type=constants.REL_SUB_CURRENT_DOC,   object=opp)

        self.assertHaveRelation(target, type=REL_SUB_PROSPECT, object=emitter)

        lines = [*quote.iter_all_lines()]
        self.assertEqual(2, len(lines))

        line1 = lines[0]
        self.assertEqual(product.unit_price,    line1.unit_price)
        self.assertEqual(product.unit,          line1.unit)
        self.assertEqual(Vat.objects.default(), line1.vat_value)
        self.assertEqual(product,               line1.related_item)

        line2 = lines[1]
        self.assertEqual(service.unit_price, line2.unit_price)
        self.assertEqual(service.unit,       line2.unit)
        self.assertEqual(service,            line2.related_item)

    @skipIfCustomOrganisation
    def test_generate_new_doc__salesorder(self):
        user = self.login_as_root_and_get()

        opp, target, emitter = self._create_opportunity_n_organisations(user=user)
        url = self._build_gendoc_url(opp, model=SalesOrder)

        self.client.post(url)
        s_order1 = SalesOrder.objects.all()[0]

        self.client.post(url)
        s_order2 = self.get_alone_element(SalesOrder.objects.exclude(pk=s_order1.id))

        self.assertHaveRelation(s_order2, type=REL_SUB_BILL_ISSUED,   object=emitter)
        self.assertHaveRelation(s_order2, type=REL_SUB_BILL_RECEIVED, object=target)
        self.assertHaveRelation(s_order2, type=constants.REL_SUB_LINKED_SALESORDER, object=opp)
        self.assertHaveNoRelation(s_order2, type=constants.REL_SUB_CURRENT_DOC,  object=opp)

        self.assertHaveRelation(s_order1, type=REL_SUB_BILL_ISSUED,   object=emitter)
        self.assertHaveRelation(s_order1, type=REL_SUB_BILL_RECEIVED, object=target)
        self.assertHaveRelation(s_order1, type=constants.REL_SUB_LINKED_SALESORDER, object=opp)
        self.assertHaveNoRelation(s_order1, type=constants.REL_SUB_CURRENT_DOC,  object=opp)

    @skipIfCustomOrganisation
    def test_generate_new_doc__invoice(self):
        user = self.login_as_root_and_get()

        opportunity, target, emitter = self._create_opportunity_n_organisations(user=user)
        url = self._build_gendoc_url(opportunity, Invoice)

        self.client.post(url)
        invoice1 = Invoice.objects.all()[0]

        self.client.post(url)
        invoice2 = self.get_alone_element(Invoice.objects.exclude(pk=invoice1.id))

        LINKED = constants.REL_SUB_LINKED_INVOICE
        self.assertHaveRelation(subject=invoice2, type=REL_SUB_BILL_ISSUED,    object=emitter)
        self.assertHaveRelation(subject=invoice2, type=REL_SUB_BILL_RECEIVED,  object=target)
        self.assertHaveRelation(subject=invoice2, type=LINKED, object=opportunity)

        self.assertHaveRelation(subject=invoice1, type=REL_SUB_BILL_ISSUED,    object=emitter)
        self.assertHaveRelation(subject=invoice1, type=REL_SUB_BILL_RECEIVED,  object=target)
        self.assertHaveRelation(subject=invoice1, type=LINKED, object=opportunity)

        self.assertHaveRelation(subject=target, type=REL_SUB_CUSTOMER_SUPPLIER, object=emitter)

    @skipIfCustomOrganisation
    def test_generate_new_doc__error__invalid_target_type(self):
        user = self.login_as_root_and_get()

        contact_count = Contact.objects.count()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        self.assertPOST404(self._build_gendoc_url(opportunity, Contact))
        self.assertEqual(contact_count, Contact.objects.count())  # No Contact created

    @skipIfCustomOrganisation
    def test_generate_new_doc__error__credentials(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'opportunities'],
            creatable_models=[Opportunity],  # Not Quote
        )

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        url = self._build_gendoc_url(opportunity)
        self.assertPOST403(url)

        role = user.role
        role.creatable_ctypes.add(ContentType.objects.get_for_model(Quote))
        self.assertPOST403(url)

        self.add_credentials(user.role, all=['VIEW', 'CHANGE', 'DELETE'])
        self.assertPOST403(url)

        self.add_credentials(user.role, all=['LINK'], model=Opportunity)
        self.assertPOST403(url)

        self.add_credentials(user.role, all=['LINK'], model=Quote)
        self.assertPOST200(url, follow=True)

    @skipIfCustomOrganisation
    def test_generate_new_doc__error__disabled_rtype(self):
        user = self.login_as_root_and_get()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]

        rtype = self.get_object_or_fail(RelationType, id=constants.REL_SUB_LINKED_QUOTE)
        rtype.enabled = False
        rtype.save()

        try:
            self.assertPOST409(self._build_gendoc_url(opportunity))
        finally:
            rtype.enabled = True
            rtype.save()

    @skipIfCustomOrganisation
    def test_current_quote(self):
        user = self.login_as_root_and_get()

        opp, target, emitter = self._create_opportunity_n_organisations(user=user)
        gendoc_url = self._build_gendoc_url(opp)

        self.client.post(gendoc_url)
        quote1 = Quote.objects.all()[0]

        self.client.post(gendoc_url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]

        self.assertHaveRelation(quote2, type=REL_SUB_BILL_ISSUED,            object=emitter)
        self.assertHaveRelation(quote2, type=REL_SUB_BILL_RECEIVED,          object=target)
        self.assertHaveRelation(quote2, type=constants.REL_SUB_LINKED_QUOTE, object=opp)
        self.assertHaveRelation(quote2, type=constants.REL_SUB_CURRENT_DOC,  object=opp)

        url1 = self._build_currentquote_url(opp, quote1)
        self.assertGET405(url1)
        self.assertPOST200(url1, follow=True)

        self.assertHaveRelation(quote2, type=REL_SUB_BILL_ISSUED,             object=emitter)
        self.assertHaveRelation(quote2, type=REL_SUB_BILL_RECEIVED,           object=target)
        self.assertHaveRelation(quote2, type=constants.REL_SUB_LINKED_QUOTE,  object=opp)
        self.assertHaveRelation(quote2, type=constants.REL_SUB_CURRENT_DOC,   object=opp)

        self.assertHaveRelation(quote1, type=REL_SUB_BILL_ISSUED,             object=emitter)
        self.assertHaveRelation(quote1, type=REL_SUB_BILL_RECEIVED,           object=target)
        self.assertHaveRelation(quote1, type=constants.REL_SUB_LINKED_QUOTE,  object=opp)
        self.assertHaveRelation(quote1, type=constants.REL_SUB_CURRENT_DOC,   object=opp)

        # Unset ---
        url2 = self._build_currentquote_url(opp, quote1, action='unset_current')
        self.assertGET405(url2)
        self.assertPOST200(url2, follow=True)
        self.assertHaveRelation(quote2, type=constants.REL_SUB_CURRENT_DOC, object=opp)
        self.assertHaveNoRelation(quote1, type=constants.REL_SUB_CURRENT_DOC, object=opp)

    @skipIfCustomOrganisation
    def test_current_quote__existing(self):
        "Relation should be considered even if the user is different."
        user1 = self.login_as_root_and_get()
        user2 = self.create_user()

        opp, target, emitter = self._create_opportunity_n_organisations(user=user1)
        quote = Quote.objects.create(
            user=user2, name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=emitter, target=target,
        )

        Relation.objects.create(
            user=user2,
            subject_entity=quote,
            type_id=constants.REL_SUB_CURRENT_DOC,
            object_entity=opp,
        )
        build_url = partial(self._build_currentquote_url, opp, quote)
        self.assertPOST200(build_url(), follow=True)

        self.assertPOST200(build_url(action='unset_current'), follow=True)
        self.assertHaveNoRelation(quote, type=constants.REL_SUB_CURRENT_DOC, object=opp)

    @skipIfCustomOrganisation
    def test_current_quote__estimated_sales(self):
        "Refresh the estimated_sales when we change which quote is the current."
        user = self.login_as_root_and_get()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        url = self._build_gendoc_url(opportunity)

        opportunity.estimated_sales = Decimal('1000')
        opportunity.made_sales = Decimal('0')
        opportunity.save()

        create_sline = partial(ServiceLine.objects.create, user=user)
        self.client.post(url)
        quote1 = Quote.objects.all()[0]
        create_sline(
            related_document=quote1, on_the_fly_item='Stuff1', unit_price=Decimal('300'),
        )

        self.client.post(url)
        quote2 = Quote.objects.exclude(pk=quote1.id)[0]
        quote2.status = QuoteStatus.objects.create(name="WONStatus", order=15, won=True)
        quote2.save()

        create_sline(
            related_document=quote2, on_the_fly_item='Stuff1', unit_price=Decimal('500'),
        )
        self.assertPOST200(
            self._build_currentquote_url(opportunity, quote1, action='unset_current'),
            follow=True,
        )
        self.assertPOST200(
            self._build_currentquote_url(opportunity, quote2, action='unset_current'),
            follow=True,
        )

        self._set_quote_config(True)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote1.total_no_vat)  # 300
        self.assertEqual(opportunity.made_sales, Decimal('0'))  # 300

        self.assertPOST200(
            self._build_currentquote_url(opportunity, quote1, action='unset_current'),
            follow=True,
        )
        self.assertPOST200(
            self._build_currentquote_url(opportunity, quote2), follow=True,
        )
        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, quote2.total_no_vat)  # 500
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)
        opportunity = self.refresh(opportunity)
        self.assertEqual(
            opportunity.estimated_sales,
            quote1.total_no_vat + quote2.total_no_vat,
        )  # 800
        self.assertEqual(opportunity.made_sales, quote2.total_no_vat)  # 300

    @skipIfCustomOrganisation
    def test_current_quote__do_not_use_for_estimation(self):
        user = self.login_as_root_and_get()

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        self._set_quote_config(use_current_quote=False)

        estimated_sales = Decimal('69')
        opportunity.estimated_sales = estimated_sales
        opportunity.save()

        self.client.post(self._build_gendoc_url(opportunity))
        quote1 = Quote.objects.all()[0]
        ServiceLine.objects.create(
            user=user, related_document=quote1,
            on_the_fly_item='Foobar', unit_price=Decimal('300'),
        )

        self.assertPOST200(self._build_currentquote_url(opportunity, quote1), follow=True)

        opportunity = self.refresh(opportunity)
        self.assertEqual(opportunity.estimated_sales, opportunity.get_total())  # 69
        self.assertEqual(opportunity.estimated_sales, estimated_sales)  # 69

    @skipIfCustomOrganisation
    def test_current_quote__use_for_estimation(self):
        user = self.login_as_root_and_get()
        self._set_quote_config(use_current_quote=True)

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        ServiceLine.objects.create(
            user=user, related_document=quote,
            on_the_fly_item='Stuff', unit_price=Decimal('300'),
        )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

    @skipIfCustomOrganisation
    def test_current_quote__relations_deleted(self):
        user = self.login_as_root_and_get()
        self._set_quote_config(use_current_quote=True)

        opportunity = self._create_opportunity_n_organisations(user=user)[0]
        self.client.post(self._build_gendoc_url(opportunity))

        quote = Quote.objects.all()[0]
        self.assertEqual(self.refresh(opportunity).estimated_sales, quote.total_no_vat)
        self.assertPOST200(self._build_currentquote_url(opportunity, quote), follow=True)

        self.assertEqual(0, self.refresh(quote).total_no_vat)
        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

        ServiceLine.objects.create(
            user=user, related_document=quote,
            on_the_fly_item='Stuff', unit_price=Decimal('300'),
        )
        self.assertEqual(300, self.refresh(quote).total_no_vat)
        self.assertEqual(300, self.refresh(opportunity).estimated_sales)

        Relation.objects.filter(
            type__in=(
                constants.REL_SUB_CURRENT_DOC,
                constants.REL_OBJ_CURRENT_DOC,
            ),
        ).delete()

        self.assertEqual(0, self.refresh(opportunity).estimated_sales)

    def test_current_quote__creation_optimization(self):
        "Avoid queries when the billing instance has just been created."
        if billing.quote_model_is_custom():
            return

        user = self.login_as_root_and_get()

        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source')
        target = create_orga(name='Target')

        with context:
            quote = Quote.objects.create(
                user=user, name='My Quote', status=status,
                source=source, target=target,
            )

        self.assertTrue(quote.pk)

        key_id = setting_keys.quote_key.id

        for query_info in context.captured_queries:
            self.assertNotIn(key_id, query_info['sql'])

    @skipIfCustomOrganisation
    def test_current_quote__sync_deletion_of_relations(self):
        "Delete the relationship REL_SUB_LINKED_QUOTE => REL_SUB_CURRENT_DOC is deleted too."
        user = self.login_as_root_and_get()
        self._set_quote_config(True)

        opp1, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        self.client.post(self._build_gendoc_url(opp1))

        opp2 = Opportunity.objects.create(
            user=user, name='Opp#2',
            sales_phase=opp1.sales_phase,
            emitter=emitter, target=target,
        )
        self.client.post(self._build_gendoc_url(opp2))

        linked_rel1 = self.get_object_or_fail(
            Relation,
            subject_entity=opp1.id,
            type=constants.REL_OBJ_LINKED_QUOTE,
        )
        quote1 = linked_rel1.real_object
        self.assertHaveRelation(subject=quote1, type=constants.REL_SUB_CURRENT_DOC, object=opp1)

        ServiceLine.objects.create(
            user=user, related_document=quote1,
            on_the_fly_item='Stuff', unit_price=Decimal('42'),
        )
        self.assertEqual(42, self.refresh(quote1).total_no_vat)
        self.assertEqual(42, self.refresh(opp1).estimated_sales)

        linked_rel2 = self.get_object_or_fail(
            Relation,
            subject_entity=opp2.id, type=constants.REL_OBJ_LINKED_QUOTE,
        )
        quote2 = linked_rel2.real_object
        self.assertHaveRelation(subject=quote2, type=constants.REL_SUB_CURRENT_DOC, object=opp2)

        linked_rel1.delete()
        self.assertHaveNoRelation(quote1, type=constants.REL_SUB_CURRENT_DOC, object=opp1)
        # Not deleted
        self.assertHaveRelation(quote2, type=constants.REL_SUB_CURRENT_DOC, object=opp2)

        self.assertFalse(self.refresh(opp1).estimated_sales)  # estimated_sales refreshed

    @skipIfCustomOrganisation
    def test_select_relations_billing_objects01(self):
        user = self.login_as_root_and_get()

        get_4_key = SettingValue.objects.get_4_key

        sv_target = get_4_key(setting_keys.target_constraint_key)
        sv_target.value = False
        sv_target.save()

        sv_emitter = get_4_key(setting_keys.emitter_constraint_key)
        sv_emitter.value = False
        sv_emitter.save()

        opp, target1, emitter1 = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        target2, emitter2 = self._create_target_n_emitter(user=user, managed=False)

        qstatus = QuoteStatus.objects.all()[0]
        create_rel = partial(Relation.objects.create, user=user)

        def create_quote(name, emitter=emitter1, target=target1):
            return Quote.objects.create(
                user=user, name=name, status=qstatus, source=emitter, target=target,
            )

        quote1 = create_quote('Quote#1')
        quote2 = create_quote('Quote#2')
        quote3 = create_quote('Quote#3', target=target2)
        quote4 = create_quote('Quote#4', emitter=emitter2)

        # 'quote2' should not be proposed
        create_rel(
            subject_entity=quote2, type_id=constants.REL_SUB_LINKED_QUOTE, object_entity=opp,
        )

        url = self.SELECTION_URL
        get_ct = ContentType.objects.get_for_model
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_QUOTE,
                'objects_ct_id': get_ct(Quote).id,
            },
        )
        context = response.context

        try:
            entities = context['page_obj']
        except KeyError:
            self.fail(response.content)

        quotes = entities.object_list
        self.assertEqual(3, len(quotes))
        self.assertTrue(all(isinstance(q, Quote) for q in quotes))
        self.assertCountEqual([quote1, quote3, quote4], quotes)

        self.assertEqual(
            _('List of {models}').format(models=_('Quotes')),
            context.get('list_title'),
        )

        # Other CT ---
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_INVOICE,
                'objects_ct_id': get_ct(Invoice).id,
            },
        )
        self.assertEqual(
            _('List of {models}').format(models=_('Invoices')),
            response.context.get('list_title'),
        )

    @skipIfCustomOrganisation
    def test_select_relations_billing_objects__same_target(self):
        user = self.login_as_root_and_get()

        get_4_key = SettingValue.objects.get_4_key
        self.assertTrue(get_4_key(setting_keys.target_constraint_key).value)

        sv = get_4_key(setting_keys.emitter_constraint_key)
        sv.value = False
        sv.save()

        opp, target1, emitter1 = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        target2, emitter2 = self._create_target_n_emitter(user=user, managed=False)

        qstatus = QuoteStatus.objects.all()[0]
        create_rel = partial(Relation.objects.create, user=user)

        def create_quote(name, emitter=emitter1, target=target1):
            return Quote.objects.create(
                user=user, name=name, status=qstatus, source=emitter, target=target,
            )

        quote1 = create_quote('Quote#1')
        quote2 = create_quote('Quote#2')
        create_quote('Quote#3', target=target2)
        quote4 = create_quote('Quote#4', emitter=emitter2)

        # 'quote2' should not be proposed
        create_rel(
            subject_entity=quote2, type_id=constants.REL_SUB_LINKED_QUOTE, object_entity=opp,
        )

        url = self.SELECTION_URL
        get_ct = ContentType.objects.get_for_model
        response1 = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_QUOTE,
                'objects_ct_id': get_ct(Quote).id,
            },
        )
        context = response1.context

        try:
            entities = context['page_obj']
        except KeyError:
            self.fail(response1.content)

        self.assertCountEqual([quote1, quote4], entities.object_list)

        fmt = _('List of {models} received by {target}').format
        self.assertEqual(
            fmt(models=_('Quotes'), target=target1), context.get('list_title'),
        )

        # Other CT ---
        response2 = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_INVOICE,
                'objects_ct_id': get_ct(Invoice).id,
            },
        )
        self.assertEqual(
            fmt(models=_('Invoices'), target=target1),
            response2.context.get('list_title'),
        )

    @skipIfCustomOrganisation
    def test_select_relations_billing_objects__same_emitter(self):
        "Same emitter."
        user = self.login_as_root_and_get()

        get_4_key = SettingValue.objects.get_4_key
        self.assertTrue(get_4_key(setting_keys.emitter_constraint_key).value)

        sv = get_4_key(setting_keys.target_constraint_key)
        sv.value = False
        sv.save()

        opp, target1, emitter1 = self._create_opportunity_n_organisations(user=user, name='Opp#1')
        target2, emitter2 = self._create_target_n_emitter(user=user, managed=False)

        qstatus = QuoteStatus.objects.all()[0]
        create_rel = partial(Relation.objects.create, user=user)

        def create_quote(name, emitter=emitter1, target=target1):
            return Quote.objects.create(
                user=user, name=name, status=qstatus, source=emitter, target=target,
            )

        quote1 = create_quote('Quote#1')
        quote2 = create_quote('Quote#2')
        quote3 = create_quote('Quote#3', target=target2)
        create_quote('Quote#4', emitter=emitter2)

        # 'quote2' should not be proposed
        create_rel(
            subject_entity=quote2, type_id=constants.REL_SUB_LINKED_QUOTE, object_entity=opp,
        )

        url = self.SELECTION_URL
        get_ct = ContentType.objects.get_for_model
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_QUOTE,
                'objects_ct_id': get_ct(Quote).id,
            },
        )
        context = response.context

        try:
            entities = context['page_obj']
        except KeyError:
            self.fail(response.content)

        self.assertCountEqual([quote1, quote3], entities.object_list)

        fmt = _('List of {models} issued by {emitter}').format
        self.assertEqual(
            fmt(models=_('Quotes'), emitter=emitter1),
            context.get('list_title'),
        )

        # Other CT ---
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_INVOICE,
                'objects_ct_id': get_ct(Invoice).id,
            },
        )
        self.assertEqual(
            fmt(models=_('Invoices'), emitter=emitter1),
            response.context.get('list_title'),
        )

    @skipIfCustomOrganisation
    def test_select_relations_billing_objects__two_constraints(self):
        user = self.login_as_root_and_get()

        get_4_key = SettingValue.objects.get_4_key
        self.assertTrue(get_4_key(setting_keys.emitter_constraint_key).value)
        self.assertTrue(get_4_key(setting_keys.emitter_constraint_key).value)

        opp, target, emitter = self._create_opportunity_n_organisations(user=user, name='Opp#1')

        url = self.SELECTION_URL
        get_ct = ContentType.objects.get_for_model
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_QUOTE,
                'objects_ct_id': get_ct(Quote).id,
            },
        )

        fmt = _('List of {models} issued by {emitter} and received by {target}').format
        self.assertEqual(
            fmt(models=_('Quotes'), emitter=emitter, target=target),
            response.context.get('list_title'),
        )

        # Other CT ---
        response = self.assertGET200(
            url,
            data={
                'subject_id': opp.id,
                'rtype_id': constants.REL_OBJ_LINKED_INVOICE,
                'objects_ct_id': get_ct(Invoice).id,
            },
        )
        self.assertEqual(
            fmt(models=_('Invoices'), emitter=emitter, target=target),
            response.context.get('list_title'),
        )

    def test_convert__quote_to_salesorder(self):
        "Some Relations are added during conversion (Quote to SalesOrder)."
        user = self.login_as_root_and_get()
        target_orga, emitter_orga = self._create_target_n_emitter(user=user, managed=False)

        create_opp = partial(
            Opportunity.objects.create,
            user=user, emitter=emitter_orga, target=target_orga,
            sales_phase=SalesPhase.objects.all()[0],
        )
        opp1 = create_opp(name='Opp #1')
        opp2 = create_opp(name='Opp #2')

        quote = Quote.objects.create(
            user=user, name='Quote for my opp', source=emitter_orga, target=target_orga,
        )

        REL_SUB_LINKED_QUOTE = constants.REL_SUB_LINKED_QUOTE
        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=quote, type_id=REL_SUB_LINKED_QUOTE,
        )
        create_rel(object_entity=opp1)
        create_rel(object_entity=opp2)

        self.assertPOST200(
            reverse('billing__convert', args=(quote.id,)),
            data={'type': 'sales_order'}, follow=True,
        )

        sales_order = SalesOrder.objects.order_by('-id')[0]
        self.assertEqual(
            _('{src} (converted into {dest._meta.verbose_name})').format(
                src=quote.name, dest=SalesOrder,
            ),
            sales_order.name,
        )
        self.assertHaveNoRelation(subject=sales_order, type=REL_SUB_LINKED_QUOTE, object=opp1)

        REL_SUB_LINKED_SALESORDER = constants.REL_SUB_LINKED_SALESORDER
        self.assertHaveRelation(subject=sales_order, type=REL_SUB_LINKED_SALESORDER, object=opp1)
        self.assertHaveRelation(subject=sales_order, type=REL_SUB_LINKED_SALESORDER, object=opp2)

    def test_convert__quote_to_invoice(self):
        "Some Relations are added during conversion (Quote to Invoice)."
        user = self.login_as_root_and_get()
        target_orga, emitter_orga = self._create_target_n_emitter(user=user, managed=False)

        create_opp = partial(
            Opportunity.objects.create,
            user=user, emitter=emitter_orga, target=target_orga,
            sales_phase=SalesPhase.objects.all()[0],
        )
        opp1 = create_opp(name='Opp #1')
        opp2 = create_opp(name='Opp #2')

        quote = Quote.objects.create(
            user=user, name='Quote for my opp', source=emitter_orga, target=target_orga,
        )

        REL_SUB_LINKED_QUOTE = constants.REL_SUB_LINKED_QUOTE
        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=quote, type_id=REL_SUB_LINKED_QUOTE,
        )
        create_rel(object_entity=opp1)
        create_rel(object_entity=opp2)

        self.assertPOST200(
            reverse('billing__convert', args=(quote.id,)),
            data={'type': 'invoice'}, follow=True,
        )

        invoice = Invoice.objects.order_by('-id')[0]
        self.assertEqual(
            _('{src} (converted into {dest._meta.verbose_name})').format(
                src=quote.name, dest=Invoice,
            ),
            invoice.name,
        )
        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_LINKED_QUOTE, object=opp1)

        REL_SUB_LINKED_INVOICE = constants.REL_SUB_LINKED_INVOICE
        self.assertHaveRelation(subject=invoice, type=REL_SUB_LINKED_INVOICE, object=opp1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_LINKED_INVOICE, object=opp2)

    def test_convert__salesorder_to_invoice(self):
        "Some Relations are added during conversion (SalesOrder to Invoice)."
        user = self.login_as_root_and_get()
        target_orga, emitter_orga = self._create_target_n_emitter(user=user, managed=False)

        create_opp = partial(
            Opportunity.objects.create,
            user=user, emitter=emitter_orga, target=target_orga,
            sales_phase=SalesPhase.objects.all()[0],
        )
        opp1 = create_opp(name='Opp #1')
        opp2 = create_opp(name='Opp #2')

        sales_order = SalesOrder.objects.create(
            user=user, name='Order for my opp', source=emitter_orga, target=target_orga,
        )

        REL_SUB_LINKED_SALESORDER = constants.REL_SUB_LINKED_SALESORDER
        create_rel = partial(
            Relation.objects.create,
            user=user, subject_entity=sales_order, type_id=REL_SUB_LINKED_SALESORDER,
        )
        create_rel(object_entity=opp1)
        create_rel(object_entity=opp2)

        self.assertPOST200(
            reverse('billing__convert', args=(sales_order.id,)),
            data={'type': 'invoice'}, follow=True,
        )

        invoice = Invoice.objects.order_by('-id')[0]
        self.assertEqual(
            _('{src} (converted into {dest._meta.verbose_name})').format(
                src=sales_order.name, dest=Invoice,
            ),
            invoice.name,
        )
        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_LINKED_SALESORDER, object=opp1)

        REL_SUB_LINKED_INVOICE = constants.REL_SUB_LINKED_INVOICE
        self.assertHaveRelation(subject=invoice, type=REL_SUB_LINKED_INVOICE, object=opp1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_LINKED_INVOICE, object=opp2)

    @parameterized.expand(['enabled', 'is_copiable'])
    def test_convert__disabled_source_rtype(self, rtype_attr):
        user = self.login_as_root_and_get()
        target_orga, emitter_orga = self._create_target_n_emitter(user=user, managed=False)
        opp = Opportunity.objects.create(
            user=user, name='Opp', emitter=emitter_orga, target=target_orga,
            sales_phase=SalesPhase.objects.all()[0],
        )
        sales_order = SalesOrder.objects.create(
            user=user, name='Order for my opp', source=emitter_orga, target=target_orga,
        )

        rtype = self.get_object_or_fail(RelationType, id=constants.REL_SUB_LINKED_SALESORDER)
        setattr(rtype, rtype_attr, False)
        rtype.save()

        Relation.objects.create(
            user=user, subject_entity=sales_order, type=rtype, object_entity=opp,
        )

        self.assertPOST200(
            reverse('billing__convert', args=(sales_order.id,)),
            data={'type': 'invoice'}, follow=True,
        )

        invoice = Invoice.objects.order_by('-id')[0]
        self.assertHaveNoRelation(
            subject=invoice, type=constants.REL_SUB_LINKED_INVOICE, object=opp,
        )

    @parameterized.expand(['enabled', 'is_copiable'])
    def test_convert__disabled_target_rtype(self, rtype_attr):
        user = self.login_as_root_and_get()
        target_orga, emitter_orga = self._create_target_n_emitter(user=user, managed=False)
        opp = Opportunity.objects.create(
            user=user, name='Opp', emitter=emitter_orga, target=target_orga,
            sales_phase=SalesPhase.objects.all()[0],
        )
        sales_order = SalesOrder.objects.create(
            user=user, name='Order for my opp', source=emitter_orga, target=target_orga,
        )

        Relation.objects.create(
            user=user,
            subject_entity=sales_order,
            type_id=constants.REL_SUB_LINKED_SALESORDER,
            object_entity=opp,
        )

        rtype = self.get_object_or_fail(RelationType, id=constants.REL_SUB_LINKED_INVOICE)
        setattr(rtype, rtype_attr, False)
        rtype.save()

        self.assertPOST200(
            reverse('billing__convert', args=(sales_order.id,)),
            data={'type': 'invoice'}, follow=True,
        )

        invoice = Invoice.objects.order_by('-id')[0]
        self.assertHaveNoRelation(subject=invoice, type=rtype, object=opp)
