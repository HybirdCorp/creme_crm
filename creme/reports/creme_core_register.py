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

from reports.models import Report, Graph


creme_registry.register_app('reports', _(u'Rapports'), '/reports')
creme_registry.register_entity_models(Report, Graph)

creme_menu.register_app('reports', '/reports/', 'Rapports et Graphes')
reg_menu = creme_menu.register_menu
reg_menu('reports', '/reports/reports',    'Liste des rapports générés')
reg_menu('reports', '/reports/report/add', 'Créer un rapport')
reg_menu('reports', '/reports/graphs',     'Liste des graphes générés')
reg_menu('reports', '/reports/graph/add',  'Créer un graphe')
