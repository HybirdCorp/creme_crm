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

from graphs.models import Graph


creme_registry.register_app('graphs', _(u'Graphs'), '/graphs')
creme_registry.register_entity_models(Graph)

creme_menu.register_app('graphs', '/graphs/', 'Graphes')
reg_menu = creme_menu.register_menu
reg_menu('graphs', '/graphs/',           _(u'Portal'))
reg_menu('graphs', '/graphs/graphs',     _(u'All graphs'))
reg_menu('graphs', '/graphs/graph/add',  _(u'Add a graphe'))
