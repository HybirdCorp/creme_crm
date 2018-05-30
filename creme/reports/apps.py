# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2018  Hybird
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
        super(ReportsConfig, self).all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Report)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.ReportFieldsBrick,
                                bricks.ReportGraphsBrick,
                               )
        brick_registry.register_4_instance(bricks.ReportGraphBrick)
        brick_registry.register_hat(self.Report, main_brick_cls=bricks.ReportBarHatBrick)

    def register_bulk_update(self, bulk_update_registry):
        from .forms.bulk import ReportFilterBulkForm

        register = bulk_update_registry.register
        register(self.Report, exclude=['ct', 'columns'],
                 innerforms={'filter': ReportFilterBulkForm},
                )
        register(self.ReportGraph, exclude=['days', 'is_count', 'chart'])  # TODO: chart -> innerform

    def register_icons(self, icon_registry):
        reg_icon = icon_registry.register
        reg_icon(self.Report,      'images/report_%(size)s.png')
        reg_icon(self.ReportGraph, 'images/graph_%(size)s.png')

    def register_menu(self, creme_menu):
        # from django.conf import settings

        Report = self.Report

        # if settings.OLD_MENU:
        #     from django.urls import reverse_lazy as reverse
        #     from creme.creme_core.auth import build_creation_perm as cperm
        #
        #     reg_item = creme_menu.register_app('reports', '/reports/').register_item
        #     reg_item(reverse('reports__portal'),        _(u'Portal of reports'), 'reports')
        #     reg_item(reverse('reports__list_reports'),  _(u'All reports'),       'reports')
        #     reg_item(reverse('reports__create_report'), Report.creation_label,   cperm(Report))
        # else:
        creme_menu.get('features') \
                  .get_or_create(creme_menu.ContainerItem, 'analysis', priority=500,
                                 defaults={'label': _(u'Analysis')},
                                ) \
                  .add(creme_menu.URLItem.list_view('reports-reports', model=Report), priority=20)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('analysis', _(u'Analysis'), priority=500) \
                  .add_link('reports-create_report', Report, priority=20)
