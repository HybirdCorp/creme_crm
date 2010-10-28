# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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

from creme_core.registry import creme_registry
from creme_core.gui.menu import creme_menu
from creme_core.gui.block import block_registry

from reports.models import Report, report_prefix_url
from reports.blocks import report_fields_block, report_graphs_block

REPORT_APP = Report._meta.app_label

creme_registry.register_app(REPORT_APP, _(u'Reports'), report_prefix_url)
creme_registry.register_entity_models(Report)

reg_item = creme_menu.register_app(REPORT_APP, '%s/' % report_prefix_url).register_item
reg_item('%s/' % report_prefix_url,           _(u'Portal'),       'reports')
reg_item('%s/reports' % report_prefix_url,    _(u'All reports'),  'reports')
reg_item('%s/report/add' % report_prefix_url, _(u'Add a report'), 'reports.add_report')

block_registry.register(report_fields_block)
block_registry.register(report_graphs_block)
