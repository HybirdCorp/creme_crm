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

from creme_core.gui.block import Block
from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
from creme_core.gui.block import QuerysetBlock

from reports.models import Field, report_template_dir
from reports.models.graph import ReportGraph, verbose_report_graph_types

class ReportFieldsBlock(Block):
    id_           = Block.generate_id('reports', 'fields')
    dependencies  = (Field,)
    verbose_name  = _(u"Columns of the report")
    template_name = '%s/templatetags/block_report_fields.html' % report_template_dir

    def detailview_display(self, context):
        object = context['object']
        return self._render(self.get_block_template_context(context,
                                                            #update_url='%s/%s/fields_block/reload/' % (report_prefix_url, object.id),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, object.pk),
                                                            HFI_FIELD=HFI_FIELD,
                                                            HFI_RELATION=HFI_RELATION)
                            )

class ReportGraphBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('reports', 'graphs')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graphs")
    template_name = '%s/templatetags/block_report_graphs.html' % report_template_dir
    order_by      = 'name'

    def detailview_display(self, context):
        report = context['object']
        request = context['request']

        return self._render(self.get_block_template_context(context, ReportGraph.objects.filter(report=report),
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, report.pk),
                                                            verbose_report_graph_types=verbose_report_graph_types,
                                                            is_ajax=request.is_ajax()
                                                            )
                            )


report_fields_block = ReportFieldsBlock()
report_graphs_block = ReportGraphBlock()
