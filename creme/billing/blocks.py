# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from django.db.models.query_utils import Q
from django.utils.simplejson.encoder import JSONEncoder
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_config.models.setting import SettingValue

from creme_core.gui.block import Block, PaginatedBlock, QuerysetBlock
from creme_core.models import CremeEntity, Relation
from creme_core.constants import PROP_IS_MANAGED_BY_CREME

from persons.models import Contact, Organisation

from billing.models import (ProductLine, ServiceLine, Invoice, SalesOrder, Quote, PaymentInformation, Base,
                            PRODUCT_LINE_TYPE, SERVICE_LINE_TYPE, TemplateBase)

from billing.constants import REL_OBJ_BILL_RECEIVED, REL_SUB_BILL_RECEIVED, REL_SUB_BILL_ISSUED, REL_OBJ_BILL_ISSUED, DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA, REL_OBJ_HAS_LINE


#NB PaginatedBlock and not QuerysetBlock to avoid the retrieving of a sliced
#   queryset of lines : we retrieve all the lines to compute the totals any way.
class ProductLinesBlock(PaginatedBlock):
    id_           = PaginatedBlock.generate_id('billing', 'product_lines')
    dependencies  = (ProductLine,)
    verbose_name  = _(u'Product lines')
    template_name = 'billing/templatetags/block_product_line.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(context, document.product_lines,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                                                            ct_id=ContentType.objects.get_for_model(ProductLine).id,
                                                            q_filter=JSONEncoder().encode({'type':PRODUCT_LINE_TYPE, 'relations__type': REL_OBJ_HAS_LINE, 'relations__object_entity': document.id}),
                                                           ))


class ServiceLinesBlock(PaginatedBlock):
    id_           = PaginatedBlock.generate_id('billing', 'service_lines')
    dependencies  = (ServiceLine,)
    verbose_name  = _(u'Service lines')
    template_name = 'billing/templatetags/block_service_line.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(context, document.service_lines,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                                                            ct_id=ContentType.objects.get_for_model(ServiceLine).id,
                                                            q_filter=JSONEncoder().encode({'type':SERVICE_LINE_TYPE, 'relations__type': REL_OBJ_HAS_LINE, 'relations__object_entity': document.id}),
                                                            ))


class TotalBlock(Block):
    id_           = Block.generate_id('billing', 'total')
    dependencies  = (ProductLine, ServiceLine)
    verbose_name  = _(u'Total')
    template_name = 'billing/templatetags/block_total.html'

    #TODO: move in Block ??
    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context))


class TargetBlock(Block):
    id_           = Block.generate_id('billing', 'target')
    dependencies  = (Invoice, SalesOrder, Quote)
    verbose_name  = _(u'Target Organisation')
    template_name = 'billing/templatetags/block_target.html'

    #TODO: move in Block ??
    def detailview_display(self, context):
        return self._render(self.get_block_template_context(context))


class ReceivedInvoicesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'received_invoices')
    dependencies  = (Relation,) #Invoice
    relation_type_deps = (REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u"Received invoices")
    template_name = 'billing/templatetags/block_received_invoices.html'
    configurable  = True
    target_ctypes = (Contact, Organisation)

    def detailview_display(self, context):
        person = context['object']

        btc= self.get_block_template_context(context,
                                             Invoice.objects.filter(relations__object_entity=person.id, relations__type=REL_SUB_BILL_RECEIVED),
                                             update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                            )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class ReceivedBillingDocumentBlock(QuerysetBlock):#TODO: Check out and exclude TemplateBase if needed
    id_           = QuerysetBlock.generate_id('billing', 'received_billing_document')
    dependencies  = (Relation,) #billing.Base subclasses except Invoice
    relation_type_deps = (REL_OBJ_BILL_RECEIVED, )
    verbose_name  = _(u"Received billing documents")
    template_name = 'billing/templatetags/block_received_billing_document.html'
    configurable  = True
    target_ctypes = (Contact, Organisation)
    order_by      = 'name'

    def detailview_display(self, context):
        person = context['object']

        qs = Base.objects.filter(relations__object_entity=person.id, relations__type=REL_SUB_BILL_RECEIVED)\
                         .filter(~Q(entity_type=ContentType.objects.get_for_model(TemplateBase)))

        CremeEntity.populate_real_entities(qs)

        btc= self.get_block_template_context(context,
                                             qs,
                                             update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, person.pk),
                                            )

        CremeEntity.populate_credentials(btc['page'].object_list, context['user'])

        return self._render(btc)


class PaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'payment_information')
    verbose_name  = _(u"Payment information")
    template_name = "billing/templatetags/block_payment_information.html"
    configurable  = True
    target_ctypes = (Organisation, )
    order_by      = 'name'

    def detailview_display(self, context):
        organisation = context['object']

        has_to_be_displayed = True
        try:
            has_to_be_displayed_cfg = SettingValue.objects.get(key__id=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA).value
            is_managed_by_creme     = organisation.properties.filter(type=PROP_IS_MANAGED_BY_CREME)

            if has_to_be_displayed_cfg and not is_managed_by_creme:
                    has_to_be_displayed = False

        except SettingValue.DoesNotExist:
            #Populate error ?
            pass

        if not has_to_be_displayed:
            return ""


        btc= self.get_block_template_context(context,
                                             PaymentInformation.objects.filter(organisation=organisation),
                                             update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, organisation.pk),
                                             ct_id=ContentType.objects.get_for_model(PaymentInformation).id
                                            )

        return self._render(btc)


class BillingPaymentInformationBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'billing_payment_information')
    verbose_name  = _(u"Default payment information")
    template_name = "billing/templatetags/block_billing_payment_information.html"
    configurable  = False
    target_ctypes = (Base, )
    dependencies  = (Relation, )
    relation_type_deps = (REL_OBJ_BILL_ISSUED, REL_SUB_BILL_ISSUED, REL_OBJ_BILL_RECEIVED, REL_SUB_BILL_RECEIVED)
    order_by      = 'name'

    def detailview_display(self, context):
        billing = context['object']
        organisation = billing.get_source()

        if organisation is not None:
            pi_qs = PaymentInformation.objects.filter(organisation=organisation)
        else:
            pi_qs = PaymentInformation.objects.none()

        btc= self.get_block_template_context(context,
                                             pi_qs,
                                             update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, billing.pk),
                                             ct_id=ContentType.objects.get_for_model(PaymentInformation).id,
                                             organisation=organisation,
                                            )

        return self._render(btc)


product_lines_block                = ProductLinesBlock()
service_lines_block                = ServiceLinesBlock()
total_block                        = TotalBlock()
target_block                       = TargetBlock()
received_invoices_block            = ReceivedInvoicesBlock()
payment_information_block          = PaymentInformationBlock()
billing_payment_information_block  = BillingPaymentInformationBlock()
received_billing_document_block    = ReceivedBillingDocumentBlock()
