# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2019  Hybird
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

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.forms.models import modelformset_factory
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import Brick, SimpleBrick, PaginatedBrick, QuerysetBrick
from creme.creme_core.models import SettingValue, Relation

from creme import persons
from creme.persons import bricks as persons_bricks

from creme import billing
from . import constants, function_fields
from .models import PaymentInformation
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


class BillingBarHatBrick(Brick):
    template_name = 'billing/bricks/billing-hat-bar.html'
    download_button = True

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    download_button=self.download_button,
        ))


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


class _LinesBrick(SimpleBrick):
    dependencies        = (Relation, CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    relation_type_deps  = (constants.REL_SUB_HAS_LINE, )
    target_ctypes       = (CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    line_model          = 'OVERLOAD_ME'
    related_item_model  = 'OVERLOAD_ME'
    related_item_label  = 'OVERLOAD_ME'

    def _get_document_lines(self, document):
        raise NotImplementedError

    # TODO: factorise with views.line.multi_save_lines() ?
    def detailview_display(self, context):
        from .forms.line import LineEditForm
        from .views.line import LINE_FORMSET_PREFIX

        document = context['object']
        lines = self._get_document_lines(document)

        class _LineForm(LineEditForm):
            def __init__(self, *args, **kwargs):
                self.empty_permitted = False
                super().__init__(user=context['user'], related_document=document, *args, **kwargs)

        line_model = self.line_model
        lineformset_class = modelformset_factory(line_model, can_delete=True, form=_LineForm, extra=0)
        lineformset = lineformset_class(prefix=LINE_FORMSET_PREFIX[line_model], queryset=lines)

        get_ct = ContentType.objects.get_for_model
        return self._render(self.get_template_context(
                    context,
                    ct_id=get_ct(line_model).id,  # TODO:  templatetag instead ?
                    formset=lineformset,
                    item_count=len(lines),
                    related_item_ct=get_ct(self.related_item_model),  # TODO:  templatetag instead ?
                    related_item_label=self.related_item_label,
        ))


class ProductLinesBrick(_LinesBrick):
    id_                = SimpleBrick.generate_id('billing', 'product_lines')
    verbose_name       = _('Product lines')
    template_name      = 'billing/bricks/product-lines.html'
    line_model         = ProductLine
    related_item_model = ProductLine.related_item_class()
    related_item_label = related_item_model._meta.verbose_name

    def _get_document_lines(self, document):
        return document.get_lines(ProductLine)


class ServiceLinesBrick(_LinesBrick):
    id_                = SimpleBrick.generate_id('billing', 'service_lines')
    verbose_name       = _('Service lines')
    template_name      = 'billing/bricks/service-lines.html'
    line_model         = ServiceLine
    related_item_model  = ServiceLine.related_item_class()
    related_item_label = related_item_model._meta.verbose_name

    def _get_document_lines(self, document):
        return document.get_lines(ServiceLine)


class CreditNotesBrick(PaginatedBrick):
    id_                 = PaginatedBrick.generate_id('billing', 'credit_notes')
    dependencies        = (Relation, CreditNote)
    relation_type_deps  = (constants.REL_OBJ_CREDIT_NOTE_APPLIED, )
    verbose_name        = _('Related Credit Notes')
    template_name       = 'billing/bricks/credit-notes.html'
    target_ctypes       = (Invoice, SalesOrder, Quote,)

    def detailview_display(self, context):
        billing_document = context['object']
        is_hidden = context['fields_configs'].get_4_model(CreditNote).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    billing_document.get_credit_notes(),
                    rtype_id=self.relation_type_deps[0],
                    add_title=_('Create a credit note'),
                    hidden_fields={fname
                                       for fname in ('issuing_date', 'expiration_date', 'comment')
                                           if is_hidden(fname)
                                  },
        ))


class TotalBrick(Brick):
    id_                 = SimpleBrick.generate_id('billing', 'total')
    dependencies        = (ProductLine, ServiceLine, Relation, CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    relation_type_deps  = (constants.REL_OBJ_CREDIT_NOTE_APPLIED,)
    verbose_name        = _('Total')
    template_name       = 'billing/bricks/total.html'
    target_ctypes       = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)

    def detailview_display(self, context):
        return self._render(self.get_template_context(
                    context,
                    cell_class=getattr(settings, 'CSS_NUMBER_LISTVIEW', ''),
        ))


class TargetBrick(SimpleBrick):
    id_           = SimpleBrick.generate_id('billing', 'target')
    dependencies  = (Invoice, CreditNote, SalesOrder, Quote, TemplateBase)
    verbose_name  = _('Target and source')
    template_name = 'billing/bricks/target.html'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


class ReceivedInvoicesBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('billing', 'received_invoices')
    dependencies  = (Relation, Invoice)
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _('Received invoices')
    template_name = 'billing/bricks/received-invoices.html'
    target_ctypes = (Contact, Organisation)
    order_by      = '-expiration_date'

    def detailview_display(self, context):
        person_id = context['object'].id
        is_hidden = context['fields_configs'].get_4_model(Invoice).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    Invoice.objects.filter(relations__object_entity=person_id,
                                           relations__type=constants.REL_SUB_BILL_RECEIVED,
                                          ),
                    hidden_fields={fname for fname in ('expiration_date',) if is_hidden(fname)},
        ))


class _ReceivedBillingDocumentsBrick(QuerysetBrick):
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _('Received billing documents')
    template_name = 'billing/bricks/received-billing-documents.html'
    target_ctypes = (Contact, Organisation)
    order_by      = '-expiration_date'

    _billing_model = None  # OVERLOAD ME
    _title         = _('{count} Received billing document')  # OVERLOAD ME
    _title_plural  = _('{count} Received billing documents')  # OVERLOAD ME
    _empty_title   = _('Received billing documents')  # OVERLOAD ME
    _empty_msg     = _('No received billing document for the moment')  # OVERLOAD ME

    def detailview_display(self, context):
        person_id = context['object'].id
        model = self._billing_model
        is_hidden = context['fields_configs'].get_4_model(model).is_fieldname_hidden

        return self._render(self.get_template_context(
                    context,
                    model.objects.filter(relations__object_entity=person_id,
                                         relations__type=constants.REL_SUB_BILL_RECEIVED,
                                        ),
                    title=self._title,
                    title_plural=self._title_plural,
                    empty_title=self._empty_title,
                    empty_msg=self._empty_msg,
                    hidden_fields={fname for fname in ('expiration_date',) if is_hidden(fname)},
        ))


class ReceivedQuotesBrick(_ReceivedBillingDocumentsBrick):
    id_          = QuerysetBrick.generate_id('billing', 'received_quotes')
    dependencies = (Relation, Quote)
    verbose_name = _('Received quotes')

    _billing_model = Quote
    _title         = _('{count} Received quote')
    _title_plural  = _('{count} Received quotes')
    _empty_title   = _('Received quotes')
    _empty_msg     = _('No received quote for the moment')


class ReceivedSalesOrdersBrick(_ReceivedBillingDocumentsBrick):
    id_          = QuerysetBrick.generate_id('billing', 'received_sales_orders')
    dependencies = (Relation, SalesOrder)
    verbose_name = _('Received sales orders')

    _billing_model = SalesOrder
    _title         = _('{count} Received sales order')
    _title_plural  = _('{count} Received sales orders')
    _empty_title   = _('Received sales orders')
    _empty_msg     = _('No received sales order for the moment')


class ReceivedCreditNotesBrick(_ReceivedBillingDocumentsBrick):
    id_          = QuerysetBrick.generate_id('billing', 'received_credit_notes')
    dependencies = (Relation, CreditNote)
    verbose_name = _('Received credit notes')

    _billing_model = CreditNote
    _title         = _('{count} Received credit note')
    _title_plural  = _('{count} Received credit notes')
    _empty_title   = _('Received credit notes')
    _empty_msg     = _('No received credit note for the moment')


class PaymentInformationBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('billing', 'payment_information')
    verbose_name  = _('Payment information')
    template_name = 'billing/bricks/orga-payment-information.html'
    target_ctypes = (Organisation, )
    order_by      = 'name'

    def detailview_display(self, context):
        organisation = context['object']

        if not organisation.is_managed and SettingValue.objects.get_4_key(payment_info_key, default=True).value:
            return ''  # TODO: in template ? empty <table> ?

        return self._render(self.get_template_context(
                context,
                PaymentInformation.objects.filter(organisation=organisation),
        ))


class BillingPaymentInformationBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('billing', 'billing_payment_information')
    verbose_name  = _('Default payment information')
    template_name = 'billing/bricks/billing-payment-information.html'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)
    dependencies  = (Relation, PaymentInformation)
    relation_type_deps = (constants.REL_OBJ_BILL_ISSUED, constants.REL_SUB_BILL_ISSUED,
                          constants.REL_OBJ_BILL_RECEIVED, constants.REL_SUB_BILL_RECEIVED,
                         )
    order_by      = 'name'

    def detailview_display(self, context):
        billing = context['object']
        pi_qs = PaymentInformation.objects.none()
        hidden = context['fields_configs'].get_4_model(billing.__class__)\
                                          .is_fieldname_hidden('payment_info')
        organisation = billing.get_source()

        if not hidden and organisation is not None:
            pi_qs = PaymentInformation.objects.filter(organisation=organisation)

        return self._render(self.get_template_context(
                    context, pi_qs,
                    organisation=organisation,
                    field_hidden=hidden,
        ))


class BillingDetailedAddressBrick(persons_bricks.DetailedAddressesBrick):
    id_ = persons_bricks.DetailedAddressesBrick.generate_id('billing', 'address')  # TODO: renames 'addresses'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


class BillingPrettyAddressBrick(persons_bricks.PrettyAddressesBrick):
    id_ = persons_bricks.PrettyAddressesBrick.generate_id('billing', 'addresses_pretty')
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


class PersonsStatisticsBrick(Brick):
    id_           = Brick.generate_id('billing', 'persons__statistics')
    verbose_name  = _('Billing statistics')
    template_name = 'billing/bricks/persons-statistics.html'
    target_ctypes = (Organisation, Contact)

    def detailview_display(self, context):
        person = context['object']
        user = context['user']
        return self._render(self.get_template_context(
                    context,
                    total_pending=function_fields.get_total_pending(person, user),
                    total_won_quote_last_year=function_fields.get_total_won_quote_last_year(person, user),
                    total_won_quote_this_year=function_fields.get_total_won_quote_this_year(person, user),
        ))
