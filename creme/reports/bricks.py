################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2025  Hybird
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
# from .core.graph import GraphFetcher
from .core.chart.fetcher import ChartFetcher
from .core.chart.plot import plot_registry
# from .report_chart_registry import report_chart_registry
from .models import Field, ReportChart

# ReportGraph = reports.get_rgraph_model()
Report = reports.get_report_model()


# class ReportGraphMixin:
#     def merge_graph_data(self, x, y, colors: dict):
#         return [{
#             'x': x,
#             'y': y[0],
#             'url': y[1],
#             'color': colors.get(x),
#         } for x, y in zip(x, y)]
class ReportChartMixin:
    def merge_chart_data(self, x, y, colors: dict):
        return [
            {
                'x': x,
                'y': y[0],
                'url': y[1],
                'color': colors.get(x),
            } for x, y in zip(x, y)
        ]


class ReportBarHatBrick(core_bricks.SimpleBrick):
    template_name = 'reports/bricks/report-hat-bar.html'


class ReportFieldsBrick(core_bricks.SimpleBrick):
    id = core_bricks.SimpleBrick.generate_id('reports', 'fields')
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

    def get_template_context(self, context, **extra_kwargs):
        columns = context['object'].columns

        return super().get_template_context(
            context,
            columns=columns,
            expand=any(field.sub_report_id for field in columns),
            **extra_kwargs
        )


# class ReportGraphChartListBrick(ReportGraphMixin, core_bricks.QuerysetBrick):
#     id = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
#     verbose_name = _('Report charts')
#     description = _(
#         'Adds & edits some charts related to a report.\n'
#         'A chart displays visually computed values, like the number of '
#         'Invoices created per month for example.\n'
#         'App: Reports'
#     )
#     # dependencies = (ReportGraph,)
#     dependencies = (ReportChart,)
#     template_name = 'reports/bricks/report-chart-list.html'
#     target_ctypes = (Report,)
#     permissions = 'reports'
#     order_by = 'created'
#
#     def detailview_display(self, context):
#         context = self.get_template_context(
#             context,
#             ReportGraph.objects.filter(linked_report=context['object']),
#             charts=[chart for _, chart in report_chart_registry]
#         )
#
#         graphs = context['page'].object_list
#
#         counter = Counter(
#             InstanceBrickConfigItem.objects.filter(
#                 entity__in=[g.id for g in graphs],
#                 brick_class_id=ReportGraphChartInstanceBrick.id,
#             ).values_list('entity', flat=True)
#         )
#
#         context['rows'] = []
#
#         user = context['user']
#         request_order = context['request'].GET.get('order', None)
#
#         for graph in graphs:
#             order = 'ASC' if graph.asc else 'DESC'
#
#             x, y = graph.fetch(
#                 user=user,
#                 order=request_order or order
#             )
#
#             data = self.merge_graph_data(
#                 x, y, colors=graph.fetch_colormap(user)
#             )
#
#             context['rows'].append({
#                 'graph': graph,
#                 'data': data,
#                 'instance_brick_count': counter[graph.id],
#                 'settings_update_url': reverse(
#                     'reports__update_graph_fetch_settings', args=(graph.id,)
#                 ),
#                 'props': {
#                     name: chart.props(graph, data) for name, chart in report_chart_registry
#                 }
#             })
#
#         return self._render(context)
class ReportChartsBrick(ReportChartMixin, core_bricks.QuerysetBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'report_charts')
    verbose_name = _('Report charts')
    description = _(
        'Adds & edits some charts related to a report.\n'
        'A chart displays visually computed values, like the number of '
        'Invoices created per month for example.\n'
        'App: Reports'
    )
    dependencies = (ReportChart,)
    template_name = 'reports/bricks/report-charts.html'
    target_ctypes = (Report,)
    permissions = 'reports'
    # order_by = 'created'
    order_by = 'id'

    def detailview_display(self, context):
        report = context['object']
        context = self.get_template_context(
            context,
            ReportChart.objects.filter(linked_report=report),
            plots=[*plot_registry],
        )

        charts = context['page'].object_list

        counter = Counter(
            ibci.get_extra_data(ReportChartInstanceBrick.chart_key)
            for ibci in InstanceBrickConfigItem.objects.filter(
                entity__in=[chart.linked_report_id for chart in charts],
                brick_class_id=ReportChartInstanceBrick.id,
            )
        )

        context['rows'] = []

        user = context['user']
        request_order = context['request'].GET.get('order', None)

        for chart in charts:
            chart.linked_report = report  # For credentials

            order = 'ASC' if chart.asc else 'DESC'
            x, y = chart.fetch(user=user, order=request_order or order)
            data = self.merge_chart_data(x, y, colors=chart.fetch_colormap(user))

            context['rows'].append({
                'chart': chart,
                'data': data,
                'instance_brick_count': counter[str(chart.uuid)],
                'settings_update_url': reverse(
                    'reports__update_chart_fetch_settings', args=(chart.id,)
                ),
                'props': {
                    plot.name: plot.props(chart=chart, data=data)
                    for plot in plot_registry
                },
            })

        return self._render(context)


# class ReportGraphChartInstanceBrick(ReportGraphMixin, core_bricks.InstanceBrick):
#     id = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
#     dependencies = (ReportGraph,)
#     verbose_name = 'Report chart'
#     template_name = 'reports/bricks/report-chart.html'
#
#     def __init__(self, instance_brick_config_item):
#         super().__init__(instance_brick_config_item)
#         get_data = instance_brick_config_item.get_extra_data
#         graph = instance_brick_config_item.entity.get_real_entity()
#
#         fetcher = self.fetcher = ReportGraph.fetcher_registry.get(
#             graph=graph,
#             fetcher_dict={
#                 key: get_data(key)
#                 for key in GraphFetcher.DICT_KEYS
#             },
#         )
#
#         fetcher_vname = fetcher.verbose_name
#         self.verbose_name = (
#             f'{fetcher.chart} - {fetcher_vname}'
#             if fetcher_vname else
#             str(fetcher.chart)
#         )
#         self.description = gettext(
#             'This block displays the chart «{chart}», contained by the report «{report}».\n'
#             'App: Reports'
#         ).format(chart=graph, report=graph.linked_report)
#
#         error = fetcher.error
#         self.errors = [error] if error else None
#
#     def _render_graph(self, context, graph, data, **kwargs):
#         context = self.get_template_context(
#             context,
#             graph=graph,
#             data=data,
#             settings_update_url=reverse(
#                 'reports__update_graph_fetch_settings', args=(graph.id,)
#             ),
#             charts=[chart for _, chart in report_chart_registry],
#             props={
#                 name: chart.props(graph, data) for name, chart in report_chart_registry
#             },
#             **kwargs
#         )
#
#         return self._render(context)
#
#     def detailview_display(self, context):
#         entity = context['object']
#         user = context['user']
#         graph = self.fetcher.chart
#         data = []
#         error = None
#
#         try:
#             x, y = self.fetcher.fetch_4_entity(
#                 entity=entity,
#                 user=context['user'],
#                 order='ASC' if graph.asc else 'DESC'
#             )
#
#             data = self.merge_graph_data(
#                 x, y, colors=graph.fetch_colormap(user)
#             )
#         except GraphFetcher.IncompatibleContentType as e:
#             error = str(e)
#         except GraphFetcher.UselessResult:
#             pass
#
#         return self._render_graph(
#             context,
#             graph=graph,
#             data=data,
#             error=error,
#             fetcher=self.fetcher
#         )
#
#     def home_display(self, context):
#         user = context['user']
#         graph = self.fetcher.chart
#
#         x, y = self.fetcher.fetch(
#             user=user,
#             order='ASC' if self.fetcher.chart.asc else 'DESC'
#         )
#
#         data = self.merge_graph_data(
#             x, y, colors=graph.fetch_colormap(user)
#         )
#
#         return self._render_graph(
#             context,
#             graph=self.fetcher.chart,
#             data=data,
#         )
#
#     @property
#     def target_ctypes(self):
#         return self.fetcher.linked_models
class ReportChartInstanceBrick(ReportChartMixin, core_bricks.InstanceBrick):
    id = InstanceBrickConfigItem.generate_base_id('reports', 'chart')
    dependencies = (ReportChart,)
    verbose_name = 'Report chart'
    template_name = 'reports/bricks/report-chart.html'

    # Key on the ReportChart's UUID in JSON data.
    chart_key = 'chart'

    def __init__(self, instance_brick_config_item):
        super().__init__(instance_brick_config_item)
        get_data = instance_brick_config_item.get_extra_data
        # TODO: manage error (it seems template/js has to be reworked)
        chart = ReportChart.objects.get(uuid=get_data(self.chart_key))

        fetcher = self.fetcher = ReportChart.fetcher_registry.get(
            chart=chart,
            fetcher_dict={key: get_data(key) for key in ChartFetcher.DICT_KEYS},
        )

        fetcher_vname = fetcher.verbose_name
        self.verbose_name = f'{chart} - {fetcher_vname}' if fetcher_vname else str(chart)

        self.description = gettext(
            'This block displays the chart «{chart}», contained by the report «{report}».\n'
            'App: Reports'
        ).format(chart=chart, report=chart.linked_report)

        error = fetcher.error
        self.errors = [error] if error else None

    def _render_chart(self, context, chart, data, **kwargs):
        context = self.get_template_context(
            context,
            chart=chart,
            data=data,
            settings_update_url=reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
            plots=[*plot_registry],
            props={
                plot.name: plot.props(chart=chart, data=data)
                for plot in plot_registry
            },
            **kwargs
        )

        return self._render(context)

    def detailview_display(self, context):
        entity = context['object']
        user = context['user']
        chart = self.fetcher.chart
        data = []
        error = None

        try:
            x, y = self.fetcher.fetch_4_entity(
                entity=entity,
                user=user,
                order='ASC' if chart.asc else 'DESC',  # TODO: factorise
            )

            data = self.merge_chart_data(
                x, y, colors=chart.fetch_colormap(user),
            )
        except ChartFetcher.IncompatibleContentType as e:
            error = str(e)
        except ChartFetcher.UselessResult:
            pass

        return self._render_chart(
            context, chart=chart, data=data, error=error, fetcher=self.fetcher,
        )

    def home_display(self, context):
        user = context['user']
        fetcher = self.fetcher
        chart = fetcher.chart
        x, y = fetcher.fetch(user=user, order='ASC' if chart.asc else 'DESC')
        return self._render_chart(
            context,
            chart=chart,
            data=self.merge_chart_data(x, y, colors=chart.fetch_colormap(user)),
        )

    @property
    def target_ctypes(self):
        return self.fetcher.linked_models


# class ReportGraphChartBrick(ReportGraphMixin, core_bricks.Brick):
#     id = core_bricks.Brick.generate_id('reports', 'graph-chart')
#     dependencies = (ReportGraph,)
#     verbose_name = _('Report chart')
#     template_name = 'reports/bricks/report-chart.html'
#     target_ctypes = (ReportGraph,)
#     permissions = 'reports'
#
#     def detailview_display(self, context):
#         graph = context['object']
#         user = context['user']
#         order = 'ASC' if graph.asc else 'DESC'
#
#         x, y = graph.fetch(
#             user=user,
#             order=context['request'].GET.get('order', order)
#         )
#
#         data = self.merge_graph_data(
#             x, y, colors=graph.fetch_colormap(user)
#         )
#
#         return self._render(self.get_template_context(
#             context,
#             graph=graph,
#             data=data,
#             settings_update_url=reverse(
#                 'reports__update_graph_fetch_settings', args=(graph.id,)
#             ),
#             charts=[chart for _, chart in report_chart_registry],
#             props={
#                 name: chart.props(graph, data) for name, chart in report_chart_registry
#             }
#         ))
class ReportChartBrick(ReportChartMixin, core_bricks.SimpleBrick):
    id = core_bricks.SimpleBrick.generate_id('reports', 'chart')
    dependencies = (ReportChart,)
    verbose_name = _('Report chart')
    template_name = 'reports/bricks/report-chart.html'
    target_ctypes = (ReportChart,)
    permissions = 'reports'

    def get_template_context(self, context, **extra_kwargs):
        chart = context['object']
        user = context['user']
        order = 'ASC' if chart.asc else 'DESC'

        x, y = chart.fetch(
            user=user,
            order=context['request'].GET.get('order', order),
        )
        data = self.merge_chart_data(x, y, colors=chart.fetch_colormap(user))

        return super().get_template_context(
            context,
            chart=chart,
            data=data,
            settings_update_url=reverse(
                'reports__update_chart_fetch_settings', args=(chart.id,),
            ),
            plots=[*plot_registry],
            props={
                plot.name: plot.props(chart=chart, data=data)
                for plot in plot_registry
            },
            **extra_kwargs
        )


class InstanceBricksInfoBrick(core_bricks.QuerysetBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'instance_bricks_info')
    verbose_name = _('Blocks')
    dependencies = (InstanceBrickConfigItem,)
    template_name = 'reports/bricks/instance-bricks-info.html'
    configurable = False
    target_ctypes = (Report,)  # Security purpose only
    permissions = 'reports'

    def detailview_display(self, context):
        chart = context['object']

        return self._render(self.get_template_context(
            context,
            # InstanceBrickConfigItem.objects.filter(
            #     brick_class_id=ReportGraphChartInstanceBrick.id,
            #     entity=context['object'].id,
            # ),
            InstanceBrickConfigItem.objects.filter(
                brick_class_id=ReportChartInstanceBrick.id,
                entity=chart.linked_report_id,
                **{f'json_extra_data__{ReportChartInstanceBrick.chart_key}': str(chart.uuid)},
            ),
        ))


class ReportEntityFiltersBrick(config_bricks.EntityFiltersBrick):
    id = core_bricks.QuerysetBrick.generate_id('reports', 'entity_filters')
    verbose_name = 'Filters specific to Reports'
    template_name = 'reports/bricks/entity-filters.html'

    filter_type = EF_REPORTS
    edition_url_name = 'reports__edit_efilter_popup'
