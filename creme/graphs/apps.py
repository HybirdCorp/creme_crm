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

from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from creme.creme_core.apps import CremeAppConfig


class GraphsConfig(CremeAppConfig):
    name = 'creme.graphs'
    verbose_name = pgettext_lazy('graphs', u'Graphs')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_graph_model

        self.Graph = get_graph_model()
        super(GraphsConfig, self).all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Graph)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(bricks.RootNodesBrick,
                                bricks.OrbitalRelationTypesBrick,
                               )
        brick_registry.register_hat(self.Graph, main_brick_cls=bricks.GraphBarHatBrick)

    def register_bulk_update(self, bulk_update_registry):
        bulk_update_registry.register(self.Graph, exclude=('orbital_relation_types',))

    def register_icons(self, icon_registry):
        icon_registry.register(self.Graph, 'images/graph_%(size)s.png')

    def register_menu(self, creme_menu):
        # from django.conf import settings

        Graph = self.Graph

        # if settings.OLD_MENU:
        #     from django.urls import reverse_lazy as reverse
        #     from creme.creme_core.auth import build_creation_perm
        #
        #     reg_item = creme_menu.register_app('graphs', '/graphs/').register_item
        #     reg_item(reverse('graphs__portal'),       _(u'Portal of graphs'), 'graphs')
        #     reg_item(reverse('graphs__list_graphs'),  _(u'All graphs'),       'graphs')
        #     reg_item(reverse('graphs__create_graph'), Graph.creation_label,   build_creation_perm(Graph))
        # else:
        creme_menu.get('features') \
                  .get_or_create(creme_menu.ContainerItem, 'analysis', priority=500,
                                 defaults={'label': _(u'Analysis')},
                                ) \
                  .add(creme_menu.URLItem.list_view('graphs-graphs', model=Graph), priority=50)
        creme_menu.get('creation', 'any_forms') \
                  .get_or_create_group('analysis', _(u'Analysis'), priority=500) \
                  .add_link('graphs-create_graph', Graph, priority=50)
