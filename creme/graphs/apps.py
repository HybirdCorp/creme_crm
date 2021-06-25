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
from django.utils.translation import pgettext_lazy

from creme.creme_core.apps import CremeAppConfig


class GraphsConfig(CremeAppConfig):
    default = True
    name = 'creme.graphs'
    verbose_name = pgettext_lazy('graphs', 'Graphs')
    dependencies = ['creme.creme_core']

    def all_apps_ready(self):
        from . import get_graph_model

        self.Graph = get_graph_model()
        super().all_apps_ready()

    def register_entity_models(self, creme_registry):
        creme_registry.register_entity_models(self.Graph)

    def register_bricks(self, brick_registry):
        from . import bricks

        brick_registry.register(
            bricks.RootNodesBrick,
            bricks.OrbitalRelationTypesBrick,
        ).register_hat(
            self.Graph,
            main_brick_cls=bricks.GraphBarHatBrick,
        )

    def register_custom_forms(self, cform_registry):
        from . import custom_forms

        cform_registry.register(
            custom_forms.GRAPH_CREATION_CFORM,
            custom_forms.GRAPH_EDITION_CFORM,
        )

    def register_fields_config(self, fields_config_registry):
        fields_config_registry.register_models(self.Graph)

    def register_icons(self, icon_registry):
        icon_registry.register(self.Graph, 'images/graph_%(size)s.png')

    # def register_menu(self, creme_menu):
    #     Graph = self.Graph
    #
    #     creme_menu.get(
    #         'features',
    #     ).get_or_create(
    #         creme_menu.ContainerItem, 'analysis',
    #         priority=500, defaults={'label': _('Analysis')},
    #     ).add(
    #         creme_menu.URLItem.list_view('graphs-graphs', model=Graph), priority=50,
    #     )
    #     creme_menu.get(
    #         'creation', 'any_forms',
    #     ).get_or_create_group(
    #         'analysis', _('Analysis'), priority=500,
    #     ).add_link(
    #         'graphs-create_graph', Graph, priority=50,
    #     )

    def register_menu_entries(self, menu_registry):
        from . import menu

        menu_registry.register(
            menu.GraphsEntry,
            menu.GraphCreationEntry,
        )

    def register_creation_menu(self, creation_menu_registry):
        creation_menu_registry.get_or_create_group(
            'analysis', _('Analysis'), priority=500,
        ).add_link(
            'graphs-create_graph', self.Graph, priority=50,
        )
