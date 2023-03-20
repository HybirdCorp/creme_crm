################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2023  Hybird
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

from django.conf import settings
from django.urls import reverse
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

import creme.creme_core.gui.bricks as core_bricks
from creme import reports
from creme.creme_core.models import InstanceBrickConfigItem

from .core.graph import GraphFetcher
from .models import Field
from .report_chart_registry import report_chart_registry

Report = reports.get_report_model()
ReportGraph = reports.get_rgraph_model()


class ReportBarHatBrick(core_bricks.SimpleBrick):
    template_name = 'reports/bricks/report-hat-bar.html'


class ReportFieldsBrick(core_bricks.Brick):
    # id_ = core_bricks.Brick.generate_id('reports', 'fields')
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

    def detailview_display(self, context):
        columns = context['object'].columns

        return self._render(self.get_template_context(
            context,
            columns=columns,
            expand=any(field.sub_report_id for field in columns),
        ))


if settings.USE_JQPLOT:
    class ReportGraphChartListBrick(core_bricks.QuerysetBrick):
        # id_ = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
        id = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
        verbose_name = _("Report's graphs")
        description = _(
            'Adds & edits some graphs related to a report.\n'
            'A graph displays visually computed values, like the number of '
            'Invoices created per month for example.\n'
            'App: Reports'
        )
        dependencies = (ReportGraph,)
        template_name = 'reports/bricks/graphs.html'
        # order_by = 'name'
        order_by = 'created'
        target_ctypes = (Report,)

        def detailview_display(self, context):
            btc = self.get_template_context(
                context,
                ReportGraph.objects.filter(linked_report=context['object']),
                report_charts=report_chart_registry,
            )
            graphs = btc['page'].object_list
            counter = Counter(
                InstanceBrickConfigItem.objects.filter(
                    entity__in=[g.id for g in graphs],
                    # brick_class_id=ReportGraphChartInstanceBrick.id_,
                    brick_class_id=ReportGraphChartInstanceBrick.id,
                ).values_list('entity', flat=True)
            )

            for graph in graphs:
                graph.instance_bricks_count = counter[graph.id]

            return self._render(btc)

    class ReportGraphChartInstanceBrick(core_bricks.InstanceBrick):
        # id_ = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
        id = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
        dependencies = (ReportGraph,)
        verbose_name = "Report's graph"  # Overloaded by __init__()
        template_name = 'reports/bricks/graph.html'

        def __init__(self, instance_brick_config_item):
            super().__init__(instance_brick_config_item)
            get_data = instance_brick_config_item.get_extra_data
            graph = instance_brick_config_item.entity.get_real_entity()
            self.fetcher = fetcher = ReportGraph.fetcher_registry.get(
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

        def _auxiliary_display(self, context, x, y, error=None, **extra_context):
            fetcher = self.fetcher

            return self._render(self.get_template_context(
                context,
                graph=fetcher.graph,
                x=x, y=y,
                error=fetcher.error or error,
                volatile_column=fetcher.verbose_name,
                instance_brick_id=self.config_item.id,
                report_charts=report_chart_registry,
                **extra_context
            ))

        def detailview_display(self, context):
            kwargs = {}
            try:
                x, y = self.fetcher.fetch_4_entity(
                    entity=context['object'],
                    user=context['user'],
                )
            except GraphFetcher.IncompatibleContentType as e:
                x = y = None
                kwargs['error'] = str(e)
            except GraphFetcher.UselessResult:
                x = y = None
                kwargs['hide_brick'] = True

            return self._auxiliary_display(context=context, x=x, y=y, **kwargs)

        def home_display(self, context):
            x, y = self.fetcher.fetch(user=context['user'])

            return self._auxiliary_display(context=context, x=x, y=y)

        @property
        def target_ctypes(self):
            return self.fetcher.linked_models
else:
    class ReportGraphChartListBrick(core_bricks.QuerysetBrick):
        # id_ = core_bricks.QuerysetBrick.generate_id('reports', 'graphs')
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
        # order_by = 'name'
        order_by = 'created'
        target_ctypes = (Report,)

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

            for graph in graphs:
                order = 'ASC' if graph.asc else 'DESC'

                x, y = graph.fetch(
                    user=context['user'],
                    order=context['request'].GET.get('order', order)
                )

                data = [{'x': x, 'y': y[0], 'url': y[1]} for x, y in zip(x, y)]

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

    class ReportGraphChartInstanceBrick(core_bricks.InstanceBrick):
        # id_ = InstanceBrickConfigItem.generate_base_id('reports', 'graph')
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
            graph = self.fetcher.graph
            data = []
            error = None

            try:
                x, y = self.fetcher.fetch_4_entity(
                    entity=entity,
                    user=context['user'],
                    order='ASC' if graph.asc else 'DESC'
                )
                data = [{'x': x, 'y': y[0], 'url': y[1]} for x, y in zip(x, y)]
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
            x, y = self.fetcher.fetch(
                user=context['user'],
                order='ASC' if self.fetcher.graph.asc else 'DESC'
            )
            data = [{'x': x, 'y': y[0], 'url': y[1]} for x, y in zip(x, y)]

            return self._render_graph(
                context,
                graph=self.fetcher.graph,
                data=data,
            )

        @property
        def target_ctypes(self):
            return self.fetcher.linked_models


class ReportGraphChartBrick(core_bricks.Brick):
    # id_ = core_bricks.Brick.generate_id('reports', 'graph-chart')
    id = core_bricks.Brick.generate_id('reports', 'graph-chart')
    dependencies = (ReportGraph,)
    verbose_name = _("Report's graph")
    template_name = 'reports/bricks/report-chart.html'

    def detailview_display(self, context):
        graph = context['object']
        order = 'ASC' if graph.asc else 'DESC'

        x, y = graph.fetch(
            user=context['user'],
            order=context['request'].GET.get('order', order)
        )

        data = [{'x': x, 'y': y[0], 'url': y[1]} for x, y in zip(x, y)]

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

    @property
    def target_ctypes(self):
        return (ReportGraph,)


class InstanceBricksInfoBrick(core_bricks.QuerysetBrick):
    # id_ = core_bricks.QuerysetBrick.generate_id('reports', 'instance_bricks_info')
    id = core_bricks.QuerysetBrick.generate_id('reports', 'instance_bricks_info')
    verbose_name = _('Blocks')
    dependencies = (InstanceBrickConfigItem,)
    template_name = 'reports/bricks/instance-bricks-info.html'
    configurable = False

    def detailview_display(self, context):
        return self._render(self.get_template_context(
            context,
            InstanceBrickConfigItem.objects.filter(
                # brick_class_id=ReportGraphChartInstanceBrick.id_,
                brick_class_id=ReportGraphChartInstanceBrick.id,
                entity=context['object'].id,
            ),
        ))
