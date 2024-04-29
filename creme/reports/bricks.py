################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

from collections import Counter

from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_config.bricks as config_bricks
import creme.creme_core.gui.bricks as core_bricks
from creme import reports
from creme.creme_core.models import InstanceBrickConfigItem

from .constants import EF_REPORTS
from .core.graph import GraphFetcher
from .models import Field
from .report_chart_registry import report_chart_registry

Report = reports.get_report_model()
ReportGraph = reports.get_rgraph_model()


class ReportGraphMixin:
    def merge_graph_data(self, x, y, colors: dict):
        return [{
            'x': x,
            'y': y[0],
            'url': y[1],
            'color': colors.get(x),
        } for x, y in zip(x, y)]


class ReportBarHatBrick(core_bricks.SimpleBrick):
    template_name = 'reports/bricks/report-hat-bar.html'


class ReportFieldsBrick(core_bricks.Brick):
    id = core_bricks.Brick.generate_id('reports', 'fields')
    verbose_name = _('Columns of the report')
    description = _(
        'Displays & edits the columns of a report.\n'
        'Columns correspond to fields, custom fields, relationships…\n'
        'App: Reports'
    )
    dependencies = (Field,)
    template_name = 'reports/bricks/fields.html'
    target_ctypes = (Report,)
    permissions = 'reports'

    def detailview_display(self, context):
        columns = context['object'].columns

        return self._render(self.get_template_context(
            context,
            columns=columns,
            expand=any(field.sub_report_id for field in columns),
        ))


class ReportGraphChartListBrick(ReportGraphMixin, core_bricks.QuerysetBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
    verbose_name = _("Report's graphs")
    description = _(
        'Adds & edits some graphs related to a report.\n'
        'A graph displays visually computed values, like the number of '
        'Invoices created per month for example.\n'
        'App: Reports'
    )
    dependencies = (ReportGraph,)
    template_name = 'reports/bricks/report-chart-list.html'
    target_ctypes = (Report,)
    permissions = 'reports'
    # order_by = 'name'
    order_by = 'created'

    def detailview_display(self, context):
        context = self.get_template_context(
            context,
            ReportGraph.objects.filter(linked_report=context['object']),
            charts=[chart for _, chart in report_chart_registry]
        )

        graphs = context['page'].object_list

        counter = Counter(
            InstanceBrickConfigItem.objects.filter(
                entity__in=[g.id for g in graphs],
                # brick_class_id=ReportGraphChartInstanceBrick.id_,
                brick_class_id=ReportGraphChartInstanceBrick.id,
            ).values_list('entity', flat=True)
        )

        context['rows'] = []

        user = context['user']
        request_order = context['request'].GET.get('order', None)

        for graph in graphs:
            order = 'ASC' if graph.asc else 'DESC'

            x, y = graph.fetch(
                user=user,
                order=request_order or order
            )

            data = self.merge_graph_data(
                x, y, colors=graph.fetch_colormap(user)
            )

            context['rows'].append({
                'graph': graph,
                'data': data,
                'instance_brick_count': counter[graph.id],
                'settings_update_url': reverse(
                    'reports__update_graph_fetch_settings', args=(graph.id,)
                ),
                'props': {
                    name: chart.props(graph, data) for name, chart in report_chart_registry
                }
            })

        return self._render(context)


class ReportGraphChartInstanceBrick(ReportGraphMixin, core_bricks.InstanceBrick):
    id = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
    dependencies = (ReportGraph,)
    verbose_name = "Report's graph"
    template_name = 'reports/bricks/report-chart.html'

    def __init__(self, instance_brick_config_item):
        super().__init__(instance_brick_config_item)
        get_data = instance_brick_config_item.get_extra_data
        graph = instance_brick_config_item.entity.get_real_entity()

        fetcher = self.fetcher = ReportGraph.fetcher_registry.get(
            graph=graph,
            fetcher_dict={
                key: get_data(key)
                for key in GraphFetcher.DICT_KEYS
            },
        )

        fetcher_vname = fetcher.verbose_name
        self.verbose_name = (
            f'{fetcher.graph} - {fetcher_vname}'
            if fetcher_vname else
            str(fetcher.graph)
        )
        self.description = gettext(
            'This block displays the graph «{graph}», contained by the report «{report}».\n'
            'App: Reports'
        ).format(graph=graph, report=graph.linked_report)

        error = fetcher.error
        self.errors = [error] if error else None

    def _render_graph(self, context, graph, data, **kwargs):
        context = self.get_template_context(
            context,
            graph=graph,
            data=data,
            settings_update_url=reverse(
                'reports__update_graph_fetch_settings_for_instance',
                args=(self.config_item.id, graph.id,)
            ),
            charts=[chart for _, chart in report_chart_registry],
            props={
                name: chart.props(graph, data) for name, chart in report_chart_registry
            },
            **kwargs
        )

        return self._render(context)

    def detailview_display(self, context):
        entity = context['object']
        user = context['user']
        graph = self.fetcher.graph
        data = []
        error = None

        try:
            x, y = self.fetcher.fetch_4_entity(
                entity=entity,
                user=context['user'],
                order='ASC' if graph.asc else 'DESC'
            )

            data = self.merge_graph_data(
                x, y, colors=graph.fetch_colormap(user)
            )
        except GraphFetcher.IncompatibleContentType as e:
            error = str(e)
        except GraphFetcher.UselessResult:
            pass

        return self._render_graph(
            context,
            graph=graph,
            data=data,
            error=error,
            fetcher=self.fetcher
        )

    def home_display(self, context):
        user = context['user']
        graph = self.fetcher.graph

        x, y = self.fetcher.fetch(
            user=user,
            order='ASC' if self.fetcher.graph.asc else 'DESC'
        )

        data = self.merge_graph_data(
            x, y, colors=graph.fetch_colormap(user)
        )

        return self._render_graph(
            context,
            graph=self.fetcher.graph,
            data=data,
        )

    @property
    def target_ctypes(self):
        return self.fetcher.linked_models


class ReportGraphChartBrick(ReportGraphMixin, core_bricks.Brick):
    id = core_bricks.Brick.generate_id('reports', 'graph-chart')
    dependencies = (ReportGraph,)
    verbose_name = _("Report's graph")
    template_name = 'reports/bricks/report-chart.html'
    target_ctypes = (ReportGraph,)
    permissions = 'reports'

    def detailview_display(self, context):
        graph = context['object']
        user = context['user']
        order = 'ASC' if graph.asc else 'DESC'

        x, y = graph.fetch(
            user=user,
            order=context['request'].GET.get('order', order)
        )

        data = self.merge_graph_data(
            x, y, colors=graph.fetch_colormap(user)
        )

        return self._render(self.get_template_context(
            context,
            graph=graph,
            data=data,
            settings_update_url=reverse(
                'reports__update_graph_fetch_settings', args=(graph.id,)
            ),
            charts=[chart for _, chart in report_chart_registry],
            props={
                name: chart.props(graph, data) for name, chart in report_chart_registry
            }
        ))

    # @property
    # def target_ctypes(self):
    #     return (ReportGraph,)


class InstanceBricksInfoBrick(core_bricks.QuerysetBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'instance_bricks_info')
    verbose_name = _('Blocks')
    dependencies = (InstanceBrickConfigItem,)
    template_name = 'reports/bricks/instance-bricks-info.html'
    configurable = False
    target_ctypes = (Report,)  # Security purpose only
    permissions = 'reports'

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            InstanceBrickConfigItem.objects.filter(
                brick_class_id=ReportGraphChartInstanceBrick.id,
                entity=context['object'].id,
            ),
        ))


class ReportEntityFiltersBrick(config_bricks.EntityFiltersBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'entity_filters')
    verbose_name = 'Filters specific to Reports'
    template_name = 'reports/bricks/entity-filters.html'

    filter_type = EF_REPORTS
    edition_url_name = 'reports__edit_efilter_popup'
