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
from django.db.models.fields import FieldDoesNotExist
from django.utils.translation import ugettext_lazy as _

from creme_core.models import CremeEntity, RelationType, InstanceBlockConfigItem
from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_RELATED
from creme_core.gui.block import Block, QuerysetBlock, list4url

from reports.models import Report, Field
from reports.models.graph import ReportGraph, verbose_report_graph_types, fetch_graph_from_instance_block


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
                                                            HFI_FIELD=HFI_FIELD,
                                                            HFI_RELATION=HFI_RELATION,
                                                            HFI_RELATED=HFI_RELATED,
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
        report  = context['object']
        request = context['request']
        user    = context['user']
        user_can_admin = user.has_perm('reports.can_admin')

        btc = self.get_block_template_context(context,
                                              ReportGraph.objects.filter(report=report),
                                              update_url='/creme_core/blocks/reload/%s/%s/' % (self.id_, report.pk),
                                              verbose_report_graph_types=verbose_report_graph_types,
                                              is_ajax=request.is_ajax(),
                                              user_can_admin_report=user_can_admin
                                             )

        CremeEntity.populate_credentials(btc['page'].object_list, user)

        return self._render(btc)


class ReportGraphBlock(Block):
#    id_           = Block.generate_id('reports', 'graph')
    #id_           = InstanceBlockConfigItem.generate_id('reports', 'graph')
    id_           = InstanceBlockConfigItem.generate_base_id('reports', 'graph')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graph")
    template_name = 'reports/templatetags/block_report_graph.html'
    order_by      = 'name'

    #def __init__(self, id_, instance_block_config):
    def __init__(self, instance_block_config):
        super(ReportGraphBlock, self).__init__()
        #self.id_                   = id_
        self.graph                 = instance_block_config.entity.get_real_entity() #TODO: avoid a query ?
        self.block_id              = instance_block_config.block_id
        self.volatile_column       = instance_block_config.data
        self.verbose               = instance_block_config.verbose
        self.instance_block_id     = instance_block_config.id
        self.instance_block_config = instance_block_config
        self.verbose_name          = self.verbose

    #@staticmethod
    #def generate_id(app_name, name):
        #app_name = app_name.replace('-', '_')
        #name = name.replace('-', '_')
        #return InstanceBlockConfigItem.generate_id('reports_blocks_ReportGraphBlock', app_name, name)

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
        #No specific things on portals so we use home display
        return self.home_display(context)

    def home_display(self, context): #TODO: factorise detailview_display()
        request = context['request']
        graph = self.graph
        x, y = graph.fetch()

        #TODO: update_url ??
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
