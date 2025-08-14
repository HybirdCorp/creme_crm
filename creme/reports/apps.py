################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2025  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.apps import CremeAppConfig


class ReportsConfig(CremeAppConfig):
    default = True
    name = 'creme.reports'
    verbose_name = _('Reports')
    dependencies = ['creme.creme_core', 'creme.sketch']

    def ready(self):
        self.register_reports_aggregations()
        # self.register_reports_charts()
        self.register_reports_plots()
        # self.register_reports_graph_fetchers()
        self.register_reports_chart_fetchers()
        self.register_reports_efilter_registry()

        from . import signals  # NOQA

    def all_apps_ready(self):
        from . import get_report_model  # get_rgraph_model

        self.Report = get_report_model()
        # self.ReportGraph = get_rgraph_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Report)

    def register_actions(self, action_registry):
        from . import actions

        action_registry.register_instance_actions(actions.ExportReportAction)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ReportFieldsBrick,
            # bricks.ReportGraphChartListBrick,
            bricks.ReportChartsBrick,
            # bricks.ReportGraphChartBrick,
            # NB: have them own reloading views
            #  - bricks.ReportChartBrick,
            #  - bricks.InstanceBricksInfoBrick,
        ).register_4_instance(
            # bricks.ReportGraphChartInstanceBrick,
            bricks.ReportChartInstanceBrick,
        ).register_hat(
            self.Report,
            main_brick_cls=bricks.ReportBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms import bulk

        bulk_update_registry.register(
            self.Report
        ).exclude('ct').add_overriders(bulk.ReportFilterOverrider)
        # TODO: self.ReportGraph? (beware to 'chart')

    def register_creme_config(self, config_registry):
        from . import bricks

        config_registry.register_app_bricks(
            'reports',
            bricks.ReportEntityFiltersBrick,
        )

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.REPORT_CREATION_CFORM,
            custom_forms.REPORT_EDITION_CFORM,
        )

    def register_cloners(self, entity_cloner_registry):
        from . import cloners

        entity_cloner_registry.register(
            model=self.Report, cloner_class=cloners.ReportCloner,
        )

    def register_deletors(self, entity_deletor_registry):
        entity_deletor_registry.register(
            model=self.Report,
        )  # .register(model=self.ReportGraph)

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Report,
            # TODO: self.ReportGraph ?
        )

    def register_icons(self, icon_registry):
        from creme.reports.models import ReportChart

        icon_registry.register(
            self.Report, 'images/report_%(size)s.png',
        ).register(
            # self.ReportGraph, 'images/graph_%(size)s.png',
            ReportChart, 'images/graph_%(size)s.png',
        )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.ReportsEntry,
            menu.ReportCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            group_id='analysis', label=_('Analysis'), priority=500,
        ).add_link(
            'reports-create_report', self.Report, priority=20,
        )

    def register_reports_aggregations(self):
        from django.db.models import aggregates

        from .report_aggregation_registry import FieldAggregation
        from .report_aggregation_registry import (
            field_aggregation_registry as registry,
        )

        registry.register(
            FieldAggregation('avg', aggregates.Avg, '{}__avg', _('Average'))
        ).register(
            FieldAggregation('min', aggregates.Min, '{}__min', _('Minimum'))
        ).register(
            FieldAggregation('max', aggregates.Max, '{}__max', _('Maximum'))
        ).register(
            FieldAggregation('sum', aggregates.Sum, '{}__sum', _('Sum'))
        )

    # def register_reports_charts(self):
    #     from . import report_chart_registry as charts
    #
    #     charts.report_chart_registry.register(
    #         charts.ReportBarChart(name='barchart', label=_('Histogram')),
    #         charts.ReportPieChart(name='piechart', label=_('Pie')),
    #         charts.ReportLineChart(name='linechart', label=_('Curve')),
    #         charts.ReportTubeChart(name='tubechart', label=_('Tube')),
    #     )
    def register_reports_plots(self):
        from .core.chart import plot

        plot.plot_registry.register(
            plot.Bar(name='barchart', label=_('Histogram')),
            plot.Pie(name='piechart', label=_('Pie')),
            plot.Line(name='linechart', label=_('Curve')),
            plot.Tube(name='tubechart', label=_('Tube')),
        )

    # def register_reports_graph_fetchers(self):
    #     from .core.graph import fetcher
    #     from .graph_fetcher_registry import graph_fetcher_registry
    #
    #     graph_fetcher_registry.register(
    #         fetcher.SimpleChartFetcher,
    #         fetcher.RegularFieldLinkedChartFetcher,
    #         fetcher.RelationLinkedChartFetcher,
    #     )
    def register_reports_chart_fetchers(self):
        from .core.chart import fetcher

        fetcher.chart_fetcher_registry.register(
            fetcher.SimpleChartFetcher,
            fetcher.RegularFieldLinkedChartFetcher,
            fetcher.RelationLinkedChartFetcher,
        )

    def register_reports_efilter_registry(self):
        from creme.creme_core.core import entity_filter
        from creme.creme_core.core.entity_filter import (
            condition_handler,
            operands,
            operators,
        )
        from creme.reports.constants import EF_REPORTS

        from .core import entity_filter as reports_filter

        entity_filter.entity_filter_registries.register(
            entity_filter.EntityFilterRegistry(
                id=EF_REPORTS,
                verbose_name=_('Reports filter'),
                detail_url_name='reports__efilter',
                edition_url_name='reports__edit_efilter',
                deletion_url_name='reports__delete_efilter',
                tag=_('Report'),
            ).register_condition_handlers(
                condition_handler.RegularFieldConditionHandler,
                condition_handler.DateRegularFieldConditionHandler,

                condition_handler.CustomFieldConditionHandler,
                condition_handler.DateCustomFieldConditionHandler,

                condition_handler.RelationConditionHandler,
                reports_filter.ReportRelationSubFilterConditionHandler,

                condition_handler.PropertyConditionHandler,

                reports_filter.ReportSubFilterConditionHandler,
            ).register_operators(
                *operators.all_operators,
            ).register_operands(
                *operands.all_operands,
            ),
        )
