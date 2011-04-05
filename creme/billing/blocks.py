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

from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType

from creme_core.gui.block import Block, PaginatedBlock, QuerysetBlock
from creme_core.models import CremeEntity, Relation

from persons.models import Contact, Organisation

from billing.models import ProductLine, ServiceLine, Invoice, SalesOrder, Quote
from billing.constants import REL_OBJ_BILL_RECEIVED, REL_SUB_BILL_RECEIVED


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
                                                           ))


class  ServiceLinesBlock(PaginatedBlock):
    id_           = PaginatedBlock.generate_id('billing', 'service_lines')
    dependencies  = (ServiceLine,)
    verbose_name  = _(u'Service lines')
    template_name = 'billing/templatetags/block_service_line.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(context, document.service_lines,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, document.pk),
                                                            ct_id=ContentType.objects.get_for_model(ServiceLine).id,
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


product_lines_block     = ProductLinesBlock()
service_lines_block     = ServiceLinesBlock()
total_block             = TotalBlock()
target_block            = TargetBlock()
received_invoices_block = ReceivedInvoicesBlock()
