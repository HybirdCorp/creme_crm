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

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.models import InstanceBlockConfigItem
from creme.creme_core.gui.block import Block, QuerysetBlock

from .constants import RFT_FIELD, RFT_RELATION, RFT_RELATED
from .core.graph import fetch_graph_from_instance_block
from .models import Report, Field, ReportGraph


class ReportFieldsBlock(Block):
    id_           = Block.generate_id('reports', 'fields')
    dependencies  = (Field,)
    verbose_name  = _(u"Columns of the report")
    template_name = 'reports/templatetags/block_report_fields.html'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        report = context['object']
        return self._render(self.get_block_template_context(context,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, report.pk),
                                                            #columns=report.columns.all(),
                                                            columns=report.fields,
                                                            #expand=any(field.report_id for field in report.columns.all()),
                                                            expand=any(field.sub_report_id for field in report.fields),
                                                            RFT_FIELD=RFT_FIELD,
                                                            RFT_RELATION=RFT_RELATION,
                                                            RFT_RELATED=RFT_RELATED,
                                                           )
                            )


class ReportGraphsBlock(QuerysetBlock):
    id_           = QuerysetBlock.generate_id('reports', 'graphs')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graphs")
    template_name = 'reports/templatetags/block_report_graphs.html'
    order_by      = 'name'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        report = context['object']

        return self._render(self.get_block_template_context(context,
                                ReportGraph.objects.filter(report=report),
                                update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, report.pk),
                                #is_ajax=context['request'].is_ajax(),
                                user_can_admin_report=context['user'].has_perm('reports.can_admin'),
                               )
                           )


class ReportGraphBlock(Block):
    id_           = InstanceBlockConfigItem.generate_base_id('reports', 'graph')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graph")
    template_name = 'reports/templatetags/block_report_graph.html'
    order_by      = 'name'

    def __init__(self, instance_block_config):
        super(ReportGraphBlock, self).__init__()
        self.graph                 = instance_block_config.entity.get_real_entity() #TODO: avoid a query ?
        self.block_id              = instance_block_config.block_id
        self.volatile_column       = instance_block_config.data
        self.verbose               = instance_block_config.verbose
        self.instance_block_id     = instance_block_config.id
        self.instance_block_config = instance_block_config
        self.verbose_name          = self.verbose

    def detailview_display(self, context):
        entity  = context['object']
        graph   = self.graph

        x, y = fetch_graph_from_instance_block(self.instance_block_config, entity, order='ASC')

        return self._render(self.get_block_template_context(context,
                                                            graph=graph,
                                                            x=x,
                                                            y=y,
                                                            volatile_column=self.verbose.split(' - ')[1],
                                                            instance_block_id=self.instance_block_id,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                                            #is_ajax=context['request'].is_ajax(),
                                                           )
                           )

    def portal_display(self, context, ct_ids):
        #No specific things on portals so we use home display
        return self.home_display(context)

    def home_display(self, context): #TODO: factorise detailview_display()
        graph = self.graph
        x, y = graph.fetch()

        #TODO: update_url ??
        return self._render(self.get_block_template_context(context,
                                                            graph=graph,
                                                            x=x,
                                                            y=y,
                                                            volatile_column=self.verbose.split(' - ')[1],
                                                            instance_block_id=self.instance_block_id,
                                                            #is_ajax=context['request'].is_ajax(),
                                                           )
                            )


report_fields_block = ReportFieldsBlock()
report_graphs_block = ReportGraphsBlock()
