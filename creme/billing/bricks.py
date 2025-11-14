################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

from collections import defaultdict

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db.models import FilteredRelation, Q
from django.utils.translation import gettext_lazy as _

import creme.persons.bricks as persons_bricks
from creme import billing, persons
from creme.creme_core.auth import EntityCredentials
from creme.creme_core.gui.bricks import (
    Brick,
    PaginatedBrick,
    QuerysetBrick,
    SimpleBrick,
)
from creme.creme_core.models import CremeEntity, Relation, SettingValue
from creme.creme_core.utils.paginators import OnePagePaginator
from creme.creme_core.utils.unicode_collation import collator

from . import constants, function_fields
from .exporters import BillingExportEngineManager
from .forms import line as line_forms
from .models import (
    ExporterConfigItem,
    Line,
    NumberGeneratorItem,
    PaymentInformation,
)
from .setting_keys import payment_info_key

Contact      = persons.get_contact_model()
Organisation = persons.get_organisation_model()

CreditNote   = billing.get_credit_note_model()
Invoice      = billing.get_invoice_model()
Quote        = billing.get_quote_model()
SalesOrder   = billing.get_sales_order_model()
TemplateBase = billing.get_template_base_model()

ProductLine = billing.get_product_line_model()
ServiceLine = billing.get_service_line_model()


# Hat bars ---------------------------------------------------------------------
class BillingBarHatBrick(SimpleBrick):
    template_name = 'billing/bricks/billing-hat-bar.html'
    download_button = True

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            download_button=self.download_button,
            **extra_kwargs
        )


class CreditNoteBarHatBrick(BillingBarHatBrick):
    pass


class InvoiceBarHatBrick(BillingBarHatBrick):
    pass


class QuoteBarHatBrick(BillingBarHatBrick):
    pass


class SalesOrderBarHatBrick(BillingBarHatBrick):
    pass


class TemplateBaseBarHatBrick(BillingBarHatBrick):
    download_button = False


# Hat cards --------------------------------------------------------------------
# TODO: move to creme core? (factorise with persons)
class CardSummary:
    dependencies: list[type[CremeEntity]] = []
    relation_type_deps: list[str] = []
    template_name = ''

    def get_context(self, *, entity: CremeEntity, brick_context: dict) -> dict:
        """Context used by the template system to render the summary."""
        template_name = self.template_name
        return {'template_name': template_name} if template_name else {}


if apps.is_installed('creme.opportunities'):
    import creme.opportunities.constants as opp_constants
    from creme.opportunities import get_opportunity_model

    Opportunity = get_opportunity_model()

    class _LinkedOpportunitySummary(CardSummary):
        dependencies = [Opportunity]
        template_name = 'billing/bricks/frags/card-summary-opportunity.html'

        # relation_type_deps = []
        rtype_id = None  # OVERRIDE ME

        def get_context(self, *, entity, brick_context):
            context = super().get_context(entity=entity, brick_context=brick_context)

            # TODO: manage several? internal type to limit to 1?
            context['opportunity'] = Opportunity.objects.filter(
                relations__type=self.rtype_id,
                relations__object_entity=entity.id,
            ).first()

            return context

    class InvoiceOpportunitySummary(_LinkedOpportunitySummary):
        relation_type_deps = [opp_constants.REL_SUB_LINKED_INVOICE]
        rtype_id = opp_constants.REL_OBJ_LINKED_INVOICE

    class QuoteOpportunitySummary(_LinkedOpportunitySummary):
        relation_type_deps = [opp_constants.REL_SUB_LINKED_QUOTE]
        rtype_id = opp_constants.REL_OBJ_LINKED_QUOTE

    class SalesOrderOpportunitySummary(_LinkedOpportunitySummary):
        relation_type_deps = [opp_constants.REL_SUB_LINKED_SALESORDER]
        rtype_id = opp_constants.REL_OBJ_LINKED_SALESORDER
else:
    class InvoiceOpportunitySummary(CardSummary):
        pass

    class QuoteOpportunitySummary(CardSummary):
        pass

    class SalesOrderOpportunitySummary(CardSummary):
        pass


class UsingInvoiceSummary(CardSummary):
    dependencies = [Invoice]
    relation_type_deps = [constants.REL_SUB_CREDIT_NOTE_APPLIED]
    template_name = 'billing/bricks/frags/card-summary-using-invoice.html'

    def get_context(self, *, entity, brick_context):
        context = super().get_context(entity=entity, brick_context=brick_context)
        context['invoice'] = Invoice.objects.filter(
            relations__type=constants.REL_OBJ_CREDIT_NOTE_APPLIED,
            relations__object_entity=entity.id,
        ).first()

        return context


class SourceQuoteSummary(CardSummary):
    dependencies = [Quote]
    relation_type_deps = [constants.REL_SUB_INVOICE_FROM_QUOTE]
    template_name = 'billing/bricks/frags/card-summary-source-quote.html'

    def get_context(self, *, entity, brick_context):
        context = super().get_context(entity=entity, brick_context=brick_context)
        context['quote'] = Quote.objects.filter(
            relations__type=constants.REL_OBJ_INVOICE_FROM_QUOTE,
            relations__object_entity=entity.id,
        ).first()

        return context


# TODO: factorise (persons.bricks.CommercialActsSummary ...)
class InvoicesGeneratedFromQuoteSummary(CardSummary):
    dependencies = [Invoice]
    # TODO: what if RelationType.enable == False?
    relation_type_deps = [constants.REL_OBJ_INVOICE_FROM_QUOTE]
    template_name = 'billing/bricks/frags/card-summary-generated-invoices.html'

    displayed_invoices_number = 5

    def get_context(self, *, entity, brick_context):
        context = super().get_context(entity=entity, brick_context=brick_context)
        rtype_id = constants.REL_SUB_INVOICE_FROM_QUOTE
        context['REL_SUB_INVOICE_FROM_QUOTE'] = rtype_id
        context['invoices'] = OnePagePaginator(
            EntityCredentials.filter(
                user=brick_context['user'],
                queryset=Invoice.objects.annotate(
                    relations_w_person=FilteredRelation(
                        'relations',
                        condition=Q(relations__object_entity=entity.id),
                    ),
                ).filter(
                    is_deleted=False,
                    relations_w_person__type=rtype_id,
                ),
            ),
            per_page=self.displayed_invoices_number,
        ).page(1)

        return context


class _BillingCardHatBrick(SimpleBrick):
    verbose_name = _('Card header block')
    template_name = 'billing/bricks/billing-hat-card.html'
    summaries = []

    def __init__(self):
        super().__init__()
        # NB: we use sets to avoid duplicates
        summaries = self.summaries
        self.dependencies = [*{
            *self.dependencies,
            *(model for summary in summaries for model in summary.dependencies),
        }]
        self.relation_type_deps = [*{
            *self.relation_type_deps,
            *(rtype_id for summary in summaries for rtype_id in summary.relation_type_deps),
        }]

    def is_expiration_passed(self, entity, today):
        return False

    def get_template_context(self, context, **extra_kwargs):
        entity = context['object']

        return super().get_template_context(
            context,
            summaries=[
                summary_cls().get_context(entity=entity, brick_context=context)
                for summary_cls in self.summaries
            ],
            is_expiration_passed=(
                self.is_expiration_passed(entity=entity, today=context['today'].date())
                if entity.expiration_date else
                False
            ),
            **extra_kwargs
        )


class CreditNoteCardHatBrick(_BillingCardHatBrick):
    id = Brick._generate_hat_id('billing', 'credit_note_card')
    dependencies = [CreditNote]
    summaries = [
        UsingInvoiceSummary,
    ]


class InvoiceCardHatBrick(_BillingCardHatBrick):
    id = Brick._generate_hat_id('billing', 'invoice_card')
    dependencies = [Invoice]
    summaries = [
        InvoiceOpportunitySummary,
        SourceQuoteSummary,
    ]

    def is_expiration_passed(self, entity, today):
        return entity.status.pending_payment and entity.expiration_date < today


class QuoteCardHatBrick(_BillingCardHatBrick):
    id = Brick._generate_hat_id('billing', 'quote_card')
    dependencies = [Quote]
    summaries = [
        QuoteOpportunitySummary,
        InvoicesGeneratedFromQuoteSummary,
        # SalesOrderGeneratedFromQuoteSummary, TODO?
    ]

    def is_expiration_passed(self, entity, today):
        return entity.status.won and entity.expiration_date < today


class SalesOrderCardHatBrick(_BillingCardHatBrick):
    id = Brick._generate_hat_id('billing', 'sales_order_card')
    dependencies = [SalesOrder]
    summaries = [
        SalesOrderOpportunitySummary,
        # InvoicesGeneratedFromSalesOrderSummary,  TODO?
    ]


# TODO? (TemplateBase is not registered as entity & so bricks cannot be configured by users)
# class TemplateBaseCardHatBrick(_BillingCardHatBrick):
#     id = Brick._generate_hat_id('billing', 'template_base_card')
#     dependencies = [TemplateBase]


# Other ------------------------------------------------------------------------
class _LinesBrick(SimpleBrick):
    dependencies = (Relation, CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    relation_type_deps = (constants.REL_SUB_HAS_LINE, )
    target_ctypes = (CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    permissions = 'billing'

    line_model = Line
    line_edit_form_template = 'billing/bricks/frags/line-fields.html'

    # TODO: factorise with <views.line.multi_save_lines()>?
    def get_template_context(self, context, **extra_kwargs):
        from .views.line import LINE_FORMSET_PREFIX

        document = context['object']
        user = context['user']
        line_model = self.line_model
        lines = document.get_lines(line_model)

        line_formset = line_forms.BaseLineEditionFormset(
            line_model,
            user,
            related_document=document,
            prefix=LINE_FORMSET_PREFIX[line_model],
            queryset=lines,
        )
        get_ct = ContentType.objects.get_for_model
        related_item_model = line_model.related_item_class()

        return super().get_template_context(
            context,
            ct_id=get_ct(line_model).id,  # TODO: templatetag instead?
            formset=line_formset,
            item_count=len(lines),
            related_item_ct=get_ct(related_item_model),  # TODO: templatetag instead?
            related_item_label=related_item_model._meta.verbose_name,
            line_edit_form_template=self.line_edit_form_template,
            **extra_kwargs
        )


class ProductLinesBrick(_LinesBrick):
    id = _LinesBrick.generate_id('billing', 'product_lines')
    verbose_name = _('Product lines')
    template_name = 'billing/bricks/product-lines.html'
    line_model = ProductLine


class ServiceLinesBrick(_LinesBrick):
    id = _LinesBrick.generate_id('billing', 'service_lines')
    verbose_name = _('Service lines')
    template_name = 'billing/bricks/service-lines.html'
    line_model = ServiceLine


class CreditNotesBrick(PaginatedBrick):
    id = PaginatedBrick.generate_id('billing', 'credit_notes')
    verbose_name = _('Related Credit Notes')
    description = _(
        'Displays the Credit Notes linked to the current entity with a relationship '
        '«is used in the billing document»/«uses the credit note».\n'
        'App: Billing'
    )
    dependencies = (Relation, CreditNote)
    relation_type_deps = (constants.REL_OBJ_CREDIT_NOTE_APPLIED, )
    template_name = 'billing/bricks/credit-notes.html'
    target_ctypes = (Invoice, SalesOrder, Quote)
    permissions = 'billing'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            context['object'].get_credit_notes(),
            rtype_id=self.relation_type_deps[0],
        ))


class TotalBrick(SimpleBrick):
    id = SimpleBrick.generate_id('billing', 'total')
    dependencies = (
        ProductLine, ServiceLine,
        Relation,
        CreditNote, Quote, Invoice, SalesOrder, TemplateBase,
    )
    relation_type_deps = (constants.REL_OBJ_CREDIT_NOTE_APPLIED,)
    verbose_name = _('Totals')
    template_name = 'billing/bricks/total.html'  # TODO: totals.html ?
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    permissions = 'billing'

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            cell_class=getattr(settings, 'CSS_NUMBER_LISTVIEW', ''),
            **extra_kwargs
        )


class TargetBrick(SimpleBrick):
    id = SimpleBrick.generate_id('billing', 'target')
    dependencies = (Invoice, CreditNote, SalesOrder, Quote, TemplateBase)
    verbose_name = _('Target and source')
    template_name = 'billing/bricks/target.html'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    permissions = 'billing'


class ReceivedInvoicesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('billing', 'received_invoices')
    dependencies = (Relation, Invoice)
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name = _('Received invoices')
    template_name = 'billing/bricks/received-invoices.html'
    target_ctypes = (Contact, Organisation)
    permissions = 'billing'
    order_by = '-expiration_date'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            Invoice.objects.filter(
                relations__object_entity=context['object'].id,  # Contact/Organisation
                relations__type=constants.REL_SUB_BILL_RECEIVED,
            ).select_related('status', 'currency'),
        ))


class _ReceivedBillingDocumentsBrick(QuerysetBrick):
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name = _('Received billing documents')
    template_name = 'billing/bricks/received-billing-documents.html'
    target_ctypes = (Contact, Organisation)
    permissions = 'billing'
    order_by = '-expiration_date'

    _billing_model = None  # OVERRIDE ME

    _title         = _('{count} Received billing document')  # OVERRIDE ME
    _title_plural  = _('{count} Received billing documents')  # OVERRIDE ME

    _empty_title = _('Received billing documents')  # OVERRIDE ME
    _empty_msg   = _('No received billing document for the moment')  # OVERRIDE ME

    def detailview_display(self, context):
        model = self._billing_model

        return self._render(self.get_template_context(
            context,
            model.objects.filter(
                relations__object_entity=context['object'].id,  # Contact/Organisation
                relations__type=constants.REL_SUB_BILL_RECEIVED,
            ),
            title=self._title,
            title_plural=self._title_plural,
            empty_title=self._empty_title,
            empty_msg=self._empty_msg,
        ))


class ReceivedQuotesBrick(_ReceivedBillingDocumentsBrick):
    id = _ReceivedBillingDocumentsBrick.generate_id('billing', 'received_quotes')
    dependencies = (Relation, Quote)
    verbose_name = _('Received quotes')

    _billing_model = Quote

    _title        = _('{count} Received quote')
    _title_plural = _('{count} Received quotes')

    _empty_title = _('Received quotes')
    _empty_msg   = _('No received quote for the moment')


class ReceivedSalesOrdersBrick(_ReceivedBillingDocumentsBrick):
    id = _ReceivedBillingDocumentsBrick.generate_id('billing', 'received_sales_orders')
    dependencies = (Relation, SalesOrder)
    verbose_name = _('Received sales orders')

    _billing_model = SalesOrder

    _title        = _('{count} Received sales order')
    _title_plural = _('{count} Received sales orders')

    _empty_title = _('Received sales orders')
    _empty_msg   = _('No received sales order for the moment')


class ReceivedCreditNotesBrick(_ReceivedBillingDocumentsBrick):
    id = _ReceivedBillingDocumentsBrick.generate_id('billing', 'received_credit_notes')
    dependencies = (Relation, CreditNote)
    verbose_name = _('Received credit notes')

    _billing_model = CreditNote

    _title        = _('{count} Received credit note')
    _title_plural = _('{count} Received credit notes')

    _empty_title = _('Received credit notes')
    _empty_msg   = _('No received credit note for the moment')


class PaymentInformationBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('billing', 'payment_information')
    verbose_name = _('Payment information')
    description = _(
        'Allows to add bank information (bank code, IBAN…) for an Organisation.\n'
        'App: Billing'
    )
    dependencies = (PaymentInformation,)
    template_name = 'billing/bricks/orga-payment-information.html'
    target_ctypes = (Organisation, )
    # permissions = 'billing' ??
    order_by = 'name'

    def detailview_display(self, context):
        organisation = context['object']

        # if not organisation.is_managed and \
        #    SettingValue.objects.get_4_key(payment_info_key, default=True).value:
        #     return ''
        #
        # return self._render(self.get_template_context(
        #     context,
        #     PaymentInformation.objects.filter(organisation=organisation),
        # ))
        if (
            organisation.is_managed
            or not SettingValue.objects.get_4_key(payment_info_key, default=True).value
        ):
            btc = self.get_template_context(
                context, PaymentInformation.objects.filter(organisation=organisation),
            )
        else:
            btc = self.get_template_context(
                context,
                PaymentInformation.objects.none(),
                template_name='creme_core/bricks/generic/void.html',
            )

        return self._render(btc)


class BillingPaymentInformationBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('billing', 'billing_payment_information')
    verbose_name = _('Default payment information')
    description = _(
        'Displays bank information (bank code, IBAN…) of the source '
        'Organisation used for the current billing entity.\n'
        'App: Billing'
    )
    template_name = 'billing/bricks/billing-payment-information.html'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    permissions = 'billing'
    dependencies = (Relation, PaymentInformation)
    relation_type_deps = (
        constants.REL_OBJ_BILL_ISSUED, constants.REL_SUB_BILL_ISSUED,
        constants.REL_OBJ_BILL_RECEIVED, constants.REL_SUB_BILL_RECEIVED,
    )
    order_by = 'name'

    def detailview_display(self, context):
        billing_doc = context['object']
        pi_qs = PaymentInformation.objects.none()
        hidden = context['fields_configs'].get_for_model(
            type(billing_doc)
        ).is_fieldname_hidden('payment_info')
        organisation = billing_doc.source

        if not hidden and organisation is not None:
            pi_qs = PaymentInformation.objects.filter(organisation=organisation)

        return self._render(self.get_template_context(
            context, pi_qs,
            organisation=organisation,
            field_hidden=hidden,
        ))


class BillingDetailedAddressBrick(persons_bricks.DetailedAddressesBrick):
    # TODO: renames 'addresses'
    id = persons_bricks.DetailedAddressesBrick.generate_id('billing', 'address')
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    permissions = 'billing'


class BillingPrettyAddressBrick(persons_bricks.PrettyAddressesBrick):
    id = persons_bricks.PrettyAddressesBrick.generate_id('billing', 'addresses_pretty')
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    permissions = 'billing'


class NumberGeneratorItemsBrick(SimpleBrick):
    id = SimpleBrick.generate_id('billing', 'number_generators')
    verbose_name = 'Number generation'
    template_name = 'billing/bricks/number-generators.html'
    dependencies = (NumberGeneratorItem,)
    # configurable = False
    # permissions = 'billing.can_admin' => auto by creme_config views

    class OrganisationWrapper:
        def __init__(self, organisation, items):
            self.organisation = organisation

            sort_key = collator.sort_key
            items.sort(key=lambda item: sort_key(str(item.numbered_type)))
            self.items = items

    def _get_wrapped_organisations(self):
        items_per_orga = defaultdict(list)
        for item in NumberGeneratorItem.objects.all():
            items_per_orga[item.organisation_id].append(item)

        Wrapper = self.OrganisationWrapper
        return [
            Wrapper(organisation=orga, items=items_per_orga[orga.id])
            for orga in Organisation.objects.filter(id__in=items_per_orga.keys())
        ]

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context,
            organisations=self._get_wrapped_organisations(),
            **extra_kwargs
        )


class BillingExportersBrick(SimpleBrick):
    id = SimpleBrick.generate_id('billing', 'exporters')
    verbose_name = _('Exporters')
    template_name = 'billing/bricks/exporters.html'
    dependencies = (ExporterConfigItem,)
    # configurable = False
    # permissions = 'billing.can_admin' => auto by creme_config views

    def _get_config_items(self):
        items = [*ExporterConfigItem.objects.all()]

        sort_key = collator.sort_key
        items.sort(key=lambda item: sort_key(str(item.content_type)))

        manager = BillingExportEngineManager()

        for conf_item in items:
            conf_item.exporter = manager.exporter(
                engine_id=conf_item.engine_id,
                flavour_id=conf_item.flavour_id,
                model=conf_item.content_type.model_class(),
            )

        return items

    def get_template_context(self, context, **extra_kwargs):
        return super().get_template_context(
            context, config_items=self._get_config_items(), **extra_kwargs
        )


class PersonsStatisticsBrick(SimpleBrick):
    id = SimpleBrick.generate_id('billing', 'persons__statistics')
    verbose_name = _('Billing statistics')
    description = _(
        'Displays some statistics concerning Invoices & Quotes:\n'
        '- Total won Quotes last year\n'
        '- Total won Quotes this year\n'
        '- Total pending payment\n'
        'App: Billing'
    )
    template_name = 'billing/bricks/persons-statistics.html'
    target_ctypes = (Organisation, Contact)
    permissions = 'billing'

    def get_template_context(self, context, **extra_kwargs):
        person = context['object']
        user = context['user']

        return super().get_template_context(
            context,
            total_pending=function_fields.get_total_pending(person, user),
            total_won_quote_last_year=function_fields.get_total_won_quote_last_year(person, user),
            total_won_quote_this_year=function_fields.get_total_won_quote_this_year(person, user),
            **extra_kwargs
        )
