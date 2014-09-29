# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2013  Hybird
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

from creme.creme_core.registry import creme_registry
from creme.creme_core.gui import creme_menu, block_registry, icon_registry, bulk_update_registry

from .blocks import report_fields_block, report_graphs_block, ReportGraphBlock
from .forms.bulk import ReportFilterBulkForm
from .models import Report, ReportGraph

creme_registry.register_app('reports', _(u'Reports'), '/reports')
creme_registry.register_entity_models(Report)

reg_item = creme_menu.register_app('reports', '/reports/').register_item
reg_item('/reports/',           _(u'Portal of reports'), 'reports')
reg_item('/reports/reports',    _(u'All reports'),       'reports')
reg_item('/reports/report/add', Report.creation_label,   'reports.add_report')

block_registry.register(report_fields_block, report_graphs_block)
block_registry.register_4_instance(ReportGraphBlock)

reg_icon = icon_registry.register
reg_icon(Report,      'images/report_%(size)s.png')
reg_icon(ReportGraph, 'images/graph_%(size)s.png')

bulk_update_registry.register(Report, exclude=['ct', 'columns'], innerforms={'filter': ReportFilterBulkForm})
