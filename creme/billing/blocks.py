# -*- coding: utf-8 -*-

import warnings

from django.core.urlresolvers import reverse

from creme.creme_core.gui.bricks import Brick

from creme.persons.blocks import AddressBlock

from .bricks import (
    CreditNote, Invoice, Quote, SalesOrder, TemplateBase,

    _LinesBrick as _LineBlock,
    ProductLinesBrick as ProductLinesBlock,
    ServiceLinesBrick as ServiceLinesBlock,
    CreditNotesBrick as CreditNoteBlock,
    TotalBrick as TotalBlock,
    TargetBrick as TargetBlock,
    ReceivedInvoicesBrick as ReceivedInvoicesBlock,
    _ReceivedBillingDocumentsBrick as _ReceivedBillingDocumentsBlock,
    ReceivedQuotesBrick as ReceivedQuotesBlock,
    ReceivedSalesOrdersBrick as ReceivedSalesOrdersBlock,
    ReceivedCreditNotesBrick as ReceivedCreditNotesBlock,
    PaymentInformationBrick as PaymentInformationBlock,
    BillingPaymentInformationBrick as BillingPaymentInformationBlock,
    PersonsStatisticsBrick as PersonsStatisticsBlock,
)

warnings.warn('billing.blocks is deprecated ; use billing.bricks instead.', DeprecationWarning)


class BillingBlock(Brick):
    template_name = 'billing/templatetags/block_billing.html'  # TODO: remove template file too

    def detailview_display(self, context):
        document = context['object']
        # return self._render(self.get_block_template_context(
        return self._render(self.get_template_context(
                    context,
                    # update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                    update_url=reverse('creme_core__reload_detailview_blocks', args=(self.id_, document.pk)),
                    is_invoice=isinstance(document, Invoice),
                    is_quote=isinstance(document, Quote),
                    is_templatebase=isinstance(document, TemplateBase),
        ))


class BillingAddressBlock(AddressBlock):
    id_  = AddressBlock.generate_id('billing', 'address')
    target_ctypes = (Invoice, CreditNote, Quote, SalesOrder, TemplateBase)


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
