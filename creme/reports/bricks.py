# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

import warnings

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.gui.bricks import Brick, SimpleBrick, QuerysetBrick
from creme.creme_core.models import InstanceBlockConfigItem

from creme import reports
from .models import Field
from .report_chart_registry import report_chart_registry


Report = reports.get_report_model()
ReportGraph = reports.get_rgraph_model()


class ReportBarHatBrick(SimpleBrick):
    template_name = 'reports/bricks/report-hat-bar.html'


class ReportFieldsBrick(Brick):
    id_           = Brick.generate_id('reports', 'fields')
    dependencies  = (Field,)
    verbose_name  = _(u'Columns of the report')
    template_name = 'reports/bricks/fields.html'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        report = context['object']
        columns = report.columns

        return self._render(self.get_template_context(
                    context,
                    columns=columns,
                    expand=any(field.sub_report_id for field in columns),
        ))


class ReportGraphsBrick(QuerysetBrick):
    id_           = QuerysetBrick.generate_id('reports', 'graphs')
    dependencies  = (ReportGraph,)
    verbose_name  = _(u"Report's graphs")
    template_name = 'reports/bricks/graphs.html'
    order_by      = 'name'
    target_ctypes = (Report,)

    def detailview_display(self, context):
        report = context['object']

        return self._render(self.get_template_context(
                    context,
                    # ReportGraph.objects.filter(report=report),
                    ReportGraph.objects.filter(linked_report=report),
                    report_charts=report_chart_registry,
        ))


class ReportGraphBrick(Brick):
    id_           = InstanceBlockConfigItem.generate_base_id('reports', 'graph')
    dependencies  = (ReportGraph,)
    verbose_name  = "Report's graph"  # Overloaded by __init__()
    template_name = 'reports/bricks/graph.html'

    def __init__(self, instance_block_config):
        super(ReportGraphBrick, self).__init__()
        # self.verbose = instance_block_config.verbose #TODO: delete 'verbose' field ?
        self.instance_block_id = instance_block_config.id
        self.fetcher = fetcher = ReportGraph.get_fetcher_from_instance_block(instance_block_config)
        self.verbose_name = fetcher.verbose_name

        # Used by InstanceBlockConfigItem.errors, to display errors in creme_config
        error = fetcher.error
        self.errors = [error] if error else None

    def detailview_display(self, context):
        entity = context['object']
        fetcher = self.fetcher
        x, y = fetcher.fetch_4_entity(entity)

        return self._render(self.get_template_context(
                    context,
                    graph=fetcher.graph,
                    x=x, y=y,
                    error=fetcher.error,
                    volatile_column=fetcher.verbose_volatile_column,
                    instance_block_id=self.instance_block_id,  # TODO: rename instance_brick_id
                    report_charts=report_chart_registry,
        ))

    def portal_display(self, context, ct_ids):
        warnings.warn('reports.bricks.ReportGraphBrick.portal_display() is deprecated.', DeprecationWarning)

        # No specific things on portals so we use home display
        return self.home_display(context)

    def home_display(self, context):  # TODO: factorise detailview_display()
        fetcher = self.fetcher
        x, y = fetcher.fetch()

        # TODO: update_url ??
        return self._render(self.get_template_context(
                                context,
                                graph=fetcher.graph,
                                x=x, y=y,
                                error=fetcher.error,
                                volatile_column=fetcher.verbose_volatile_column,
                                instance_block_id=self.instance_block_id,
                                report_charts=report_chart_registry,
                               )
                           )
