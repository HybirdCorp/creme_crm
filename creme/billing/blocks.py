# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2017  Hybird
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
from django.utils.translation import ugettext_lazy as _

# from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME
from creme.creme_core.gui.block import Block, SimpleBlock, QuerysetBlock
from creme.creme_core.models import SettingValue, Relation

from creme import persons
from creme.persons.blocks import AddressBlock

# from creme.products import get_product_model, get_service_model

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


# DEPRECATED
# TODO: remove template file too
class BillingBlock(Block):
    template_name = 'billing/templatetags/block_billing.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(
                    context,
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                    is_invoice=isinstance(document, Invoice),
                    is_quote=isinstance(document, Quote),
                    is_templatebase=isinstance(document, TemplateBase),
                   ))


class _LineBlock(SimpleBlock):
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
                super(_LineForm, self).__init__(user=context['user'], related_document=document, *args, **kwargs)

        line_model = self.line_model
        lineformset_class = modelformset_factory(line_model, can_delete=True, form=_LineForm, extra=0)
        lineformset = lineformset_class(prefix=LINE_FORMSET_PREFIX[line_model], queryset=lines)

        return self._render(self.get_block_template_context(
                    context,
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                    ct_id=ContentType.objects.get_for_model(line_model).id,
                    formset=lineformset,
                    # item_count=lines.count(),
                    item_count=len(lines),
                    related_item_ct=ContentType.objects.get_for_model(self.related_item_model),
                    related_item_label=self.related_item_label,
                   ))


class ProductLinesBlock(_LineBlock):
    id_                = SimpleBlock.generate_id('billing', 'product_lines')
    verbose_name       = _(u'Product lines')
    template_name      = 'billing/templatetags/block_product_line.html'
    line_model         = ProductLine
    # related_item_model  = get_product_model()
    related_item_model = ProductLine.related_item_class()
    # related_item_label = _(u'Product')
    related_item_label = related_item_model._meta.verbose_name

    def _get_document_lines(self, document):
        return document.get_lines(ProductLine)


class ServiceLinesBlock(_LineBlock):
    id_                = SimpleBlock.generate_id('billing', 'service_lines')
    verbose_name       = _(u'Service lines')
    template_name      = 'billing/templatetags/block_service_line.html'
    line_model         = ServiceLine
    # related_item_model  = get_service_model()
    related_item_model  = ServiceLine.related_item_class()
    # related_item_label = _(u'Service')
    related_item_label = related_item_model._meta.verbose_name

    def _get_document_lines(self, document):
        return document.get_lines(ServiceLine)


class CreditNoteBlock(QuerysetBlock):
    id_                 = QuerysetBlock.generate_id('billing', 'credit_notes')
    dependencies        = (Relation, CreditNote)
    relation_type_deps  = (constants.REL_OBJ_CREDIT_NOTE_APPLIED, )
    verbose_name        = _(u'Related Credit Notes')
    template_name       = 'billing/templatetags/block_credit_note.html'
    target_ctypes       = (Invoice, SalesOrder, Quote,)

    def detailview_display(self, context):
        billing_document = context['object']
        is_hidden = context['fields_configs'].get_4_model(CreditNote).is_fieldname_hidden

        return self._render(self.get_block_template_context(
                    context,
                    billing_document.get_credit_notes(),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (
                                    self.id_, billing_document.pk,
                                ),
                    rtype_id=self.relation_type_deps[0],
                    ct=ContentType.objects.get_for_model(CreditNote),
                    add_title=_(u'Create a credit note'),
                    hidden_fields={fname
                                       for fname in ('issuing_date', 'expiration_date', 'comment')
                                           if is_hidden(fname)
                                  },
                ))


class TotalBlock(Block):
    id_                 = SimpleBlock.generate_id('billing', 'total')
    dependencies        = (ProductLine, ServiceLine, Relation, CreditNote, Quote, Invoice, SalesOrder, TemplateBase)
    relation_type_deps  = (constants.REL_OBJ_CREDIT_NOTE_APPLIED,)
    verbose_name        = _(u'Total')
    template_name       = 'billing/templatetags/block_total.html'
    target_ctypes       = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)

    def detailview_display(self, context):
        return self._render(self.get_block_template_context(
                    context,
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, context['object'].pk),
                    cell_class=getattr(settings, 'CSS_NUMBER_LISTVIEW', ''),
                   ))


class TargetBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('billing', 'target')
    dependencies  = (Invoice, CreditNote, SalesOrder, Quote, TemplateBase)
    verbose_name  = _(u'Target organisation')
    template_name = 'billing/templatetags/block_target.html'
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


class ReceivedInvoicesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'received_invoices')
    dependencies  = (Relation, Invoice)
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u'Received invoices')
    template_name = 'billing/templatetags/block_received_invoices.html'
    target_ctypes = (Contact, Organisation)
    order_by      = '-expiration_date'

    def detailview_display(self, context):
        person_id = context['object'].id
        is_hidden = context['fields_configs'].get_4_model(Invoice).is_fieldname_hidden

        return self._render(self.get_block_template_context(
                    context,
                    Invoice.objects.filter(relations__object_entity=person_id,
                                           relations__type=constants.REL_SUB_BILL_RECEIVED,
                                          ),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person_id),
                    hidden_fields={fname for fname in ('expiration_date',) if is_hidden(fname)},
                ))


class _ReceivedBillingDocumentsBlock(QuerysetBlock):
    relation_type_deps = (constants.REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u'Received billing documents')
    template_name = 'billing/templatetags/block_received_billing_document.html'
    target_ctypes = (Contact, Organisation)
    order_by      = '-expiration_date'

    _billing_model = None  # OVERLOAD ME
    _title         = _('%s Received billing document')  # OVERLOAD ME
    _title_plural  = _('%s Received billing documents')  # OVERLOAD ME
    _empty_msg     = _('No received billing document for the moment')  # OVERLOAD ME

    def detailview_display(self, context):
        person_id = context['object'].id
        model = self._billing_model
        is_hidden = context['fields_configs'].get_4_model(model).is_fieldname_hidden

        return self._render(self.get_block_template_context(
                    context,
                    model.objects.filter(relations__object_entity=person_id,
                                         relations__type=constants.REL_SUB_BILL_RECEIVED,
                                        ),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person_id),
                    title=self._title,
                    title_plural=self._title_plural,
                    empty_msg=self._empty_msg,
                    hidden_fields={fname for fname in ('expiration_date',) if is_hidden(fname)},
                ))


class ReceivedQuotesBlock(_ReceivedBillingDocumentsBlock):
    id_          = QuerysetBlock.generate_id('billing', 'received_quotes')
    dependencies = (Relation, Quote)
    verbose_name = _(u'Received quotes')

    _billing_model = Quote
    _title         = _('%s Received quote')
    _title_plural  = _('%s Received quotes')
    _empty_msg     = _('No received quote for the moment')


class ReceivedSalesOrdersBlock(_ReceivedBillingDocumentsBlock):
    id_          = QuerysetBlock.generate_id('billing', 'received_sales_orders')
    dependencies = (Relation, SalesOrder)
    verbose_name = _(u'Received sales orders')

    _billing_model = SalesOrder
    _title         = _('%s Received sales order')
    _title_plural  = _('%s Received sales orders')
    _empty_msg     = _('No received sales order for the moment')


class ReceivedCreditNotesBlock(_ReceivedBillingDocumentsBlock):
    id_          = QuerysetBlock.generate_id('billing', 'received_credit_notes')
    dependencies = (Relation, CreditNote)
    verbose_name = _(u'Received credit notes')

    _billing_model = CreditNote
    _title         = _('%s Received credit note')
    _title_plural  = _('%s Received credit notes')
    _empty_msg     = _('No received credit note for the moment')


class PaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'payment_information')
    verbose_name  = _(u'Payment information')
    template_name = 'billing/templatetags/block_payment_information.html'
    target_ctypes = (Organisation, )
    order_by      = 'name'

    def detailview_display(self, context):
        organisation = context['object']
        has_to_be_displayed = True

        try:
            # if SettingValue.objects.get(key_id=constants.DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA).value \
            #    and not organisation.properties.filter(type=PROP_IS_MANAGED_BY_CREME).exists():
            if not organisation.is_managed and SettingValue.objects.get(key_id=payment_info_key.id).value:
                has_to_be_displayed = False
        except SettingValue.DoesNotExist:
            # Populate error ?
            pass

        if not has_to_be_displayed:
            return ''  # TODO: in template ? empty <table> ?

        return self._render(self.get_block_template_context(context,
                    PaymentInformation.objects.filter(organisation=organisation),
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, organisation.pk),
                    ct_id=ContentType.objects.get_for_model(PaymentInformation).id,
                   ))


class BillingPaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'billing_payment_information')
    verbose_name  = _(u'Default payment information')
    template_name = 'billing/templatetags/block_billing_payment_information.html'
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

        return self._render(self.get_block_template_context(
                    context, pi_qs,
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, billing.pk),
                    ct_id=ContentType.objects.get_for_model(PaymentInformation).id,
                    organisation=organisation,
                    field_hidden=hidden,
                   ))


class BillingAddressBlock(AddressBlock):
    id_  = Block.generate_id('billing', 'address')
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


class PersonsStatisticsBlock(Block):
    id_  = Block.generate_id('billing', 'persons__statistics')
    verbose_name  = _(u'Statistics')
    template_name = 'billing/templatetags/block_persons_statistics.html'
    target_ctypes = (Organisation, Contact)

    def detailview_display(self, context):
        person = context['object']
        user = context['user']
        return self._render(self.get_block_template_context(
                    context,
                    update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                    total_pending=function_fields.get_total_pending(person, user),
                    total_won_quote_last_year=function_fields.get_total_won_quote_last_year(person, user),
                    total_won_quote_this_year=function_fields.get_total_won_quote_this_year(person, user),
                   ))


product_lines_block       = ProductLinesBlock()
service_lines_block       = ServiceLinesBlock()
credit_note_block         = CreditNoteBlock()
total_block               = TotalBlock()
target_block              = TargetBlock()
received_invoices_block   = ReceivedInvoicesBlock()
payment_information_block = PaymentInformationBlock()
billing_payment_block     = BillingPaymentInformationBlock()
received_quotes_block     = ReceivedQuotesBlock()
billing_address_block     = BillingAddressBlock()
persons_statistics_block  = PersonsStatisticsBlock()

block_list = (
        product_lines_block,
        service_lines_block,
        credit_note_block,
        total_block,
        target_block,
        received_invoices_block,
        payment_information_block,
        billing_payment_block,
        received_quotes_block,
        ReceivedSalesOrdersBlock(),
        ReceivedCreditNotesBlock(),
        billing_address_block,
        persons_statistics_block,
    )
