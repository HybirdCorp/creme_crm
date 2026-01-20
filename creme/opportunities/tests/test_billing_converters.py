from functools import partial
from unittest import skipIf

from django.apps import apps
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.creme_core.models import Relation, RelationType
from creme.opportunities import constants
from creme.opportunities.models import SalesPhase
from creme.opportunities.tests.base import (
    OpportunitiesBaseTestCase,
    Opportunity,
    skipIfCustomOpportunity,
)

if apps.is_installed('creme.billing'):
    skip_billing = False

    from creme import billing

    Invoice     = billing.get_invoice_model()
    Quote       = billing.get_quote_model()
    SalesOrder  = billing.get_sales_order_model()
    ServiceLine = billing.get_service_line_model()
else:
    skip_billing = True


@skipIf(skip_billing, '"Billing" app is not installed.')
@skipIfCustomOpportunity
class ConversionTestCase(OpportunitiesBaseTestCase):
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
