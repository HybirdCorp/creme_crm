# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.gui.block import Block, QuerysetBlock
from creme_core.models import CremeEntity

from billing.models import ProductLine, ServiceLine
from django.db.models.query import QuerySet


class ProductLinesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'product_lines')
    verbose_name  = _(u'Lignes produit')
    template_name = 'billing/templatetags/block_product_line.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, ProductLine.objects.filter(document=pk),
                                                            update_url='/billing/%s/product_lines/reload/' % pk))

class  ServiceLinesBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('billing', 'service_lines')
    verbose_name  = _(u'Lignes service')
    template_name = 'billing/templatetags/block_service_line.html'

    def detailview_display(self, context):
        pk = context['object'].pk
        return self._render(self.get_block_template_context(context, ServiceLine.objects.filter(document=pk),
                                                            update_url='/billing/%s/service_lines/reload/' % pk))


class TotalBlock(Block):
    id_           = Block.generate_id('billing', 'total')
    verbose_name  = _(u'Total')
    template_name = 'billing/templatetags/block_total.html'

    def detailview_display(self, context):
        document = context['object']
        return self._render(self.get_block_template_context(context,
                                                            update_url='/billing/%s/total/reload/' % document.pk, #useful ??
                                                            total=document.get_total(),
                                                            total_with_tax=document.get_total_with_tax())
                            )


product_lines_block = ProductLinesBlock()
service_lines_block = ServiceLinesBlock()
total_block         = TotalBlock()
