################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2024  Hybird
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

import logging

from django.utils.functional import partition
from django.utils.translation import gettext_lazy as _

from creme.creme_core.gui.bricks import QuerysetBrick
from creme.sketch.bricks import ChartBrick

from . import get_graph_model
from .models import RootNode

logger = logging.getLogger(__name__)


class RelationChartBrick(ChartBrick):
    id = ChartBrick.generate_id('graphs', 'relation_chart')
    verbose_name = _('Relationship graph')
    dependencies = (RootNode,)
    template_name = 'graphs/bricks/relation-chart.html'
    target_ctypes = (get_graph_model(),)
    permissions = 'graphs'

    enable_transition = False
    enable_legend = True

    node_fill_color = "white"
    node_stroke_color = "#ccc"
    node_stroke_size = 2
    node_edgecount_step = 4
    node_size = 5
    node_text_color = "black"
    edge_color_range = None

    def get_chart_props(self, context):
        return {
            "transition": self.enable_transition,
            "showLegend": self.enable_legend,
            "nodeFillColor": self.node_fill_color,
            "nodeStrokeColor": self.node_stroke_color,
            "nodeTextColor": self.node_text_color,
            "nodeStrokeSize": self.node_stroke_size,
            "nodeEdgeCountStep": self.node_edgecount_step,
            "nodeSize": self.node_size,
            "edgeColors": self.edge_color_range,
        }

    def get_graph_chart_data(self, graph, user):
        root_nodes = graph.get_root_nodes(user)
        orbital_entities = {}

        for node in root_nodes:
            root_entity = node.real_entity
            relations = sorted(
                graph.get_root_node_relations(node, user),
                key=lambda r: r.type.id
            )

            yield {
                'id': root_entity.pk,
                'label': str(root_entity),
                'url': root_entity.get_absolute_url()
            }

            for relation in relations:
                entity = orbital_entities.get(relation.object_entity_id)

                if entity is None:
                    entity = relation.real_object
                    orbital_entities[relation.object_entity_id] = entity

                yield {
                    'id': entity.pk,
                    'parent': root_entity.pk,
                    'label': str(entity),
                    'relation': {
                        'label': str(relation.type.predicate),
                        'id': relation.type.id,
                    },
                    'url': entity.get_absolute_url(),
                }

        orbital_relations = graph.get_orbital_relations(limit_to=orbital_entities.keys())

        for relation in orbital_relations:
            entity = orbital_entities[relation.object_entity_id]

            yield {
                'id': relation.object_entity_id,
                'parent': relation.subject_entity_id,
                'label': str(entity),
                'relation': {
                    'label': str(relation.type.predicate),
                    'id': relation.type.id,
                },
                'url': entity.get_absolute_url(),
            }

    def get_chart_data(self, context):
        return list(
            self.get_graph_chart_data(context['object'], context['user'])
        )

    def detailview_display(self, context):
        return self._render_chart(context)


class RootNodesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('graphs', 'root_nodes')
    verbose_name = _('Root nodes')
    description = _(
        'The Root nodes are the entities in the center of the Graph, associated '
        'with some relationship types, to retrieve entities linked to the root entities.\n'
        'App: Graphs'
    )
    dependencies = (RootNode,)
    template_name = 'graphs/bricks/root-nodes.html'
    target_ctypes = (get_graph_model(),)
    permissions = 'graphs'
    order_by = 'entity__header_filter_search_field'

    def detailview_display(self, context):
        graph = context['object']
        btc = self.get_template_context(
            context,
            graph.roots.prefetch_related(
                'real_entity', 'relation_types', 'relation_types__symmetric_type',
            ),
        )

        for root_node in btc['page'].object_list:
            root_node.disabled_rtypes_list, root_node.rtypes_list = partition(
                (lambda rtype: rtype.enabled),
                root_node.relation_types.all()
            )

        return self._render(btc)


class OrbitalRelationTypesBrick(QuerysetBrick):
    id = QuerysetBrick.generate_id('graphs', 'orbital_rtypes')
    verbose_name = _('Peripheral types of relationship')
    description = _(
        'These types of relationship are displayed in the Graph between entities '
        'which are linked to the root entities.\n'
        'App: Graphs'
    )
    dependencies = (RootNode,)
    template_name = 'graphs/bricks/orbital-rtypes.html'
    target_ctypes = (get_graph_model(),)
    permissions = 'graphs'

    def detailview_display(self, context):
        graph = context['object']
        return self._render(self.get_template_context(
            context,
            graph.orbital_relation_types.select_related('symmetric_type'),
        ))
