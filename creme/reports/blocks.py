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

from django.db.models.query_utils import Q
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _

from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION
from creme_core.gui.block import Block, QuerysetBlock, list4url
from creme_core.models.block import InstanceBlockConfigItem
from creme_core.models.relation import RelationType

from creme.reports.models.graph import fetch_graph_from_instance_block
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

class ReportGraphsBlock(QuerysetBlock):
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


class ReportGraphBlock(Block):
#    id_           = Block.generate_id('reports', 'graph')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graphs")
    template_name = '%s/templatetags/block_report_graph.html' % report_template_dir
    order_by      = 'name'

    def __init__(self, id_, instance_block_config):
        self.id_                   = id_
        self.graph                 = instance_block_config.entity.get_real_entity()
        self.block_id              = instance_block_config.block_id
        self.volatile_column       = instance_block_config.data
        self.verbose               = instance_block_config.verbose
        self.instance_block_id     = instance_block_config.id
        self.instance_block_config = instance_block_config

    @staticmethod
    def generate_id(app_name, name):
        app_name = app_name.replace('-','_')
        name = name.replace('-','_')
        return InstanceBlockConfigItem.generate_id('reports_blocks_ReportGraphBlock', app_name, name)

    def detailview_display(self, context):
        entity  = context['object']
        request = context['request']
        graph   = self.graph
        
        x, y = fetch_graph_from_instance_block(self.instance_block_config, entity, order='ASC')

        return self._render(self.get_block_template_context(context,
                                                            graph=graph,
                                                            x=x,
                                                            y=y,
                                                            volatile_column=self.verbose.split(' - ')[1],
                                                            instance_block_id=self.instance_block_id,
                                                            update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, entity.pk),
                                                            verbose_report_graph_types=verbose_report_graph_types,
                                                            is_ajax=request.is_ajax(),
                                                            )
                            )

    def portal_display(self, context, ct_ids):
        request = context['request']
        graph = self.graph
        x, y = graph.fetch()
        return self._render(self.get_block_template_context(context,
                                                            graph=graph,
                                                            x=x,
                                                            y=y,
                                                            volatile_column=self.verbose.split(' - ')[1],
                                                            instance_block_id=self.instance_block_id,
                                                            verbose_report_graph_types=verbose_report_graph_types,
                                                            is_ajax=request.is_ajax(),
                                                            )
                            )

    def home_display(self, context):
        request = context['request']
        graph = self.graph
        x, y = graph.fetch()
        return self._render(self.get_block_template_context(context,
                                                            graph=graph,
                                                            x=x,
                                                            y=y,
                                                            volatile_column=self.verbose.split(' - ')[1],
                                                            instance_block_id=self.instance_block_id,
                                                            verbose_report_graph_types=verbose_report_graph_types,
                                                            is_ajax=request.is_ajax(),
                                                            )
                            )


report_fields_block = ReportFieldsBlock()
report_graphs_block = ReportGraphsBlock()
