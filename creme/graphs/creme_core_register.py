# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2011  Hybird
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
from creme_core.gui import creme_menu, block_registry, icon_registry

from graphs.models import Graph
from graphs.blocks import root_nodes_block, orbital_rtypes_block


creme_registry.register_app('graphs', _(u'Graphs'), '/graphs')
creme_registry.register_entity_models(Graph)

reg_item = creme_menu.register_app('graphs', '/graphs/').register_item
reg_item('/graphs/',           _(u'Portal of graphs'), 'graphs')
reg_item('/graphs/graphs',     _(u'All graphs'),       'graphs')
reg_item('/graphs/graph/add',  _(u'Add a graph'),      'graphs.add_graph')

block_registry.register(root_nodes_block, orbital_rtypes_block)

icon_registry.register(Graph, 'images/graph_%(size)s.png')
