# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015  Hybird
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

from creme.creme_core.apps import CremeAppConfig


class ReportsConfig(CremeAppConfig):
    name = 'creme.reports'
    verbose_name = _(u'Reports')
    dependencies = ['creme.creme_core']

    def ready(self):
        from . import signals

    def all_apps_ready(self):
        from . import get_report_model, get_rgraph_model

        self.Report = get_report_model()
        self.ReportGraph = get_rgraph_model()
#        super(ReportsConfig, self).ready()
        super(ReportsConfig, self).all_apps_ready()

    def register_creme_app(self, creme_registry):
        creme_registry.register_app('reports', _(u'Reports'), '/reports')

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Report)

    def register_blocks(self, block_registry):
        from .blocks import report_fields_block, report_graphs_block, ReportGraphBlock

        block_registry.register(report_fields_block, report_graphs_block)
        block_registry.register_4_instance(ReportGraphBlock)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.bulk import ReportFilterBulkForm

        register = bulk_update_registry.register
        register(self.Report, exclude=['ct', 'columns'],
                 innerforms={'filter': ReportFilterBulkForm},
                )
        register(self.ReportGraph, exclude=['days', 'is_count', 'chart']) # TODO: chart -> innerform

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Report,      'images/report_%(size)s.png')
        reg_icon(self.ReportGraph, 'images/graph_%(size)s.png')

    def register_menu(self, creme_menu):
        from django.core.urlresolvers import reverse_lazy as reverse

        from creme.creme_core.auth import build_creation_perm as cperm

        Report = self.Report
        reg_item = creme_menu.register_app('reports', '/reports/').register_item
        reg_item('/reports/',                       _(u'Portal of reports'), 'reports')
        reg_item(reverse('reports__list_reports'),  _(u'All reports'),       'reports')
        reg_item(reverse('reports__create_report'), Report.creation_label,   cperm(Report))
