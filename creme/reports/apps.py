# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2021  Hybird
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
    dependencies = ['creme.creme_core']

    def ready(self):
        self.register_reports_aggregations()
        self.register_reports_charts()
        self.register_reports_graph_fetchers()

        from . import signals  # NOQA

    def all_apps_ready(self):
        from . import get_report_model, get_rgraph_model

        self.Report = get_report_model()
        self.ReportGraph = get_rgraph_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Report)

    def register_actions(self, actions_registry):
        from . import actions

        actions_registry.register_instance_actions(actions.ExportReportAction)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.ReportFieldsBrick,
            bricks.ReportGraphsBrick,
            bricks.InstanceBricksInfoBrick,
        ).register_4_instance(
            bricks.ReportGraphBrick,
        ).register_hat(
            self.Report,
            main_brick_cls=bricks.ReportBarHatBrick,
        )

    def register_bulk_update(self, bulk_update_registry):
        from .forms.bulk import ReportFilterBulkForm

        register = bulk_update_registry.register
        register(
            self.Report,
            exclude=['ct'],
            innerforms={'filter': ReportFilterBulkForm},
        )
        register(
            self.ReportGraph,
            exclude=['chart'],
        )  # TODO: chart -> innerform

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.REPORT_CREATION_CFORM,
            custom_forms.REPORT_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(
            self.Report,
            # TODO: self.ReportGraph ?
        )

    def register_icons(self, icon_registry):
        icon_registry.register(
            self.Report, 'images/report_%(size)s.png',
        ).register(
            self.ReportGraph, 'images/graph_%(size)s.png',
        )

    # def register_menu(self, creme_menu):
    #     Report = self.Report
    #     creme_menu.get(
    #         'features',
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'analysis',
    #         priority=500,
    #         defaults={'label': _('Analysis')},
    #     ).add(
    #         creme_menu.URLItem.list_view('reports-reports', model=Report),
    #         priority=20,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms',
    #     ).get_or_create_group(
    #         'analysis', _('Analysis'), priority=500,
    #     ).add_link(
    #         'reports-create_report', Report, priority=20,
    #     )

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

    def register_reports_charts(self):
        from .report_chart_registry import ReportChart, report_chart_registry

        # TODO: register several at once
        report_chart_registry.register(
            ReportChart('barchart',  _('Histogram')),
        ).register(
            ReportChart('piechart',  _('Pie')),
        ).register(
            ReportChart('tubechart', _('Tube')),
        )

    def register_reports_graph_fetchers(self):
        from .core.graph import fetcher
        from .graph_fetcher_registry import graph_fetcher_registry

        graph_fetcher_registry.register(
            fetcher.SimpleGraphFetcher,
            fetcher.RegularFieldLinkedGraphFetcher,
            fetcher.RelationLinkedGraphFetcher,
        )
