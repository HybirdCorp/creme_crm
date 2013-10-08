# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from django.forms.models import modelformset_factory
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme.creme_core.gui.block import Block, SimpleBlock, QuerysetBlock
from creme.creme_core.models import CremeEntity, Relation
from creme.creme_core.constants import PROP_IS_MANAGED_BY_CREME

from creme.creme_config.models.setting import SettingValue

from creme.persons.models import Contact, Organisation
from creme.persons.blocks import AddressBlock

from creme.products.models import Product, Service

from .models import *
from .constants import *
from .function_fields import get_total_pending, get_total_won_quote_last_year, get_total_won_quote_this_year


class BillingBlock(Block):
    template_name = 'billing/templatetags/block_billing.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                                                            is_invoice=isinstance(document, Invoice),
                                                            is_quote=isinstance(document, Quote),
                                                           )
                           )


class _LineBlock(SimpleBlock):
    dependencies        = (Base, CreditNote, Quote, Invoice, SalesOrder)
    target_ctypes       = (Base, CreditNote, Quote, Invoice, SalesOrder)
    line_model          = "OVERLOAD_ME"
    line_type           = "OVERLOAD_ME"
    related_item_ct     = "OVERLOAD_ME"
    related_item_label  = "OVERLOAD_ME"

    def _get_document_lines(self, document):
        raise NotImplementedError

    def detailview_display(self, context):
        from .forms.line import LineEditForm
        from .views.line import LINE_FORMSET_PREFIX

        document = context['object']
        lines = self._get_document_lines(document)

        class _LineForm(LineEditForm):
            def __init__(self, *args, **kwargs):
                self.empty_permitted = False
                super(_LineForm, self).__init__(user=context['user'], related_document=document, *args, **kwargs)

        lineformset_class = modelformset_factory(self.line_model,
                                                 # TODO can always delete ??? for example a quote accepted
                                                 # can we really delete a line of this document ???
                                                 can_delete=True,
                                                 form=_LineForm,
                                                 extra=0)

        lineformset = lineformset_class(prefix=LINE_FORMSET_PREFIX[self.line_model], queryset=lines)

        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                                                            ct_id=ContentType.objects.get_for_model(self.line_model).id,
                                                            formset=lineformset,
                                                            item_count=lines.count(),
                                                            related_item_ct=self.related_item_ct,
                                                            related_item_label=self.related_item_label,
                                                            q_filter=JSONEncoder().encode({'type':self.line_type,
                                                                                           'relations__type': REL_OBJ_HAS_LINE,
                                                                                           'relations__object_entity': document.id}),
                                                            )
        )


class ProductLinesBlock(_LineBlock):
    id_                 = SimpleBlock.generate_id('billing', 'product_lines')
    verbose_name        = _(u'Product lines')
    template_name       = 'billing/templatetags/block_product_line.html'
    line_model          = ProductLine
    line_type           = PRODUCT_LINE_TYPE
    related_item_ct     = ContentType.objects.get_for_model(Product)
    related_item_label  = _(u'Product')

    def _get_document_lines(self, document):
        return document.product_lines


class ServiceLinesBlock(_LineBlock):
    id_                 = SimpleBlock.generate_id('billing', 'service_lines')
    verbose_name        = _(u'Service lines')
    template_name       = 'billing/templatetags/block_service_line.html'
    line_model          = ServiceLine
    line_type           = SERVICE_LINE_TYPE
    related_item_ct     = ContentType.objects.get_for_model(Service)
    related_item_label  = _(u'Service')

    def _get_document_lines(self, document):
        return document.service_lines


class CreditNoteBlock(QuerysetBlock):
    id_                 = QuerysetBlock.generate_id('billing', 'credit_notes')
    dependencies        = (Relation, CreditNote)
    relation_type_deps  = (REL_OBJ_CREDIT_NOTE_APPLIED, )
    verbose_name        = _(u"Related Credit Notes")
    template_name       = 'billing/templatetags/block_credit_note.html'
    target_ctypes       = (Invoice, SalesOrder, Quote,)

    def detailview_display(self, context):
        billing_document = context['object']
        btc = self.get_block_template_context(context,
                                              billing_document.get_credit_notes(),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, billing_document.pk),
                                              rtype_id=self.relation_type_deps[0],
                                              ct=ContentType.objects.get_for_model(CreditNote),
                                              add_title=_(u'Add a credit note'),
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class TotalBlock(SimpleBlock):
    id_                 = SimpleBlock.generate_id('billing', 'total')
    dependencies        = (ProductLine, ServiceLine, Relation, Base, CreditNote, Quote, Invoice, SalesOrder)
    relation_type_deps  = (REL_OBJ_CREDIT_NOTE_APPLIED,)
    verbose_name        = _(u'Total')
    template_name       = 'billing/templatetags/block_total.html'
    target_ctypes       = (Base, Invoice, CreditNote, Quote, SalesOrder)


class TargetBlock(SimpleBlock):
    id_           = SimpleBlock.generate_id('billing', 'target')
    dependencies  = (Invoice, SalesOrder, Quote)
    verbose_name  = _(u'Target organisation')
    template_name = 'billing/templatetags/block_target.html'
    target_ctypes = (Base, Invoice, CreditNote, Quote, SalesOrder)


class ReceivedInvoicesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'received_invoices')
    dependencies  = (Relation, Invoice)
    relation_type_deps = (REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u"Received invoices")
    template_name = 'billing/templatetags/block_received_invoices.html'
    #configurable  = True
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        person = context['object']
        btc = self.get_block_template_context(context,
                                              Invoice.objects.filter(relations__object_entity=person.id,
                                                                     relations__type=REL_SUB_BILL_RECEIVED)\
                                                     .order_by('expiration_date'),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class ReceivedBillingDocumentBlock(QuerysetBlock):#TODO: Check out and exclude TemplateBase if needed
    id_           = QuerysetBlock.generate_id('billing', 'received_billing_document')
    dependencies  = (Relation, CreditNote, Quote, SalesOrder)
    relation_type_deps = (REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u"Received billing documents")
    template_name = 'billing/templatetags/block_received_billing_document.html'
    #configurable  = True
    target_ctypes = (Contact, Organisation)
    order_by      = 'name'

    def detailview_display(self, context):
        person = context['object']
        get_ct = ContentType.objects.get_for_model
        qs = Base.objects.filter(relations__object_entity=person.id, relations__type=REL_SUB_BILL_RECEIVED)\
                         .exclude(entity_type__in=[get_ct(TemplateBase), get_ct(Invoice)])\
                         .order_by('expiration_date')

        CremeEntity.populate_real_entities(qs)

        btc = self.get_block_template_context(context, qs,
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                             )

        #CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class PaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'payment_information')
    verbose_name  = _(u"Payment information")
    template_name = "billing/templatetags/block_payment_information.html"
    target_ctypes = (Organisation, )
    order_by      = 'name'

    def detailview_display(self, context):
        organisation = context['object']
        has_to_be_displayed = True

        try:
            if SettingValue.objects.get(key__id=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA).value \
               and not organisation.properties.filter(type=PROP_IS_MANAGED_BY_CREME).exists():
                has_to_be_displayed = False
        except SettingValue.DoesNotExist:
            #Populate error ?
            pass

        if not has_to_be_displayed:
            return ""

        btc = self.get_block_template_context(context,
                                              PaymentInformation.objects.filter(organisation=organisation),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, organisation.pk),
                                              ct_id=ContentType.objects.get_for_model(PaymentInformation).id
                                             )

        return self._render(btc)


class BillingPaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'billing_payment_information')
    verbose_name  = _(u"Default payment information")
    template_name = "billing/templatetags/block_billing_payment_information.html"
    #configurable  = False
    target_ctypes = (Base, Invoice, CreditNote, Quote, SalesOrder)
    dependencies  = (Relation, PaymentInformation)
    relation_type_deps = (REL_OBJ_BILL_ISSUED, REL_SUB_BILL_ISSUED, REL_OBJ_BILL_RECEIVED, REL_SUB_BILL_RECEIVED)
    order_by      = 'name'

    def detailview_display(self, context):
        billing = context['object']
        organisation = billing.get_source()

        if organisation is not None:
            pi_qs = PaymentInformation.objects.filter(organisation=organisation)
        else:
            pi_qs = PaymentInformation.objects.none()

        btc = self.get_block_template_context(context, pi_qs,
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, billing.pk),
                                              ct_id=ContentType.objects.get_for_model(PaymentInformation).id,
                                              organisation=organisation,
                                             )

        return self._render(btc)


class BillingAddressBlock(AddressBlock):
    id_  = Block.generate_id('billing', 'address')
    target_ctypes = (Base, Invoice, CreditNote, Quote, SalesOrder)


class PersonsStatisticsBlock(Block):
    id_  = Block.generate_id('billing', 'persons__statistics')
    verbose_name  = _(u"Statistics")
    template_name = 'billing/templatetags/block_persons_statistics.html'
    target_ctypes = (Organisation, Contact)

    def detailview_display(self, context):
        person = context['object']
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                                            total_pending=get_total_pending(person),
                                                            total_won_quote_last_year=get_total_won_quote_last_year(person),
                                                            total_won_quote_this_year=get_total_won_quote_this_year(person),
                                                           )
                           )


product_lines_block             = ProductLinesBlock()
service_lines_block             = ServiceLinesBlock()
credit_note_block               = CreditNoteBlock()
total_block                     = TotalBlock()
target_block                    = TargetBlock()
received_invoices_block         = ReceivedInvoicesBlock()
payment_information_block       = PaymentInformationBlock()
billing_payment_block           = BillingPaymentInformationBlock()
received_billing_document_block = ReceivedBillingDocumentBlock()
billing_address_block           = BillingAddressBlock()
persons_statistics_block        = PersonsStatisticsBlock()

block_list = (
        product_lines_block,
        service_lines_block,
        credit_note_block,
        total_block,
        target_block,
        received_invoices_block,
        payment_information_block,
        billing_payment_block,
        received_billing_document_block,
        billing_address_block,
        persons_statistics_block,
    )
