################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2026  Hybird
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

from django.http import HttpResponse

from creme import graphs
from creme.creme_core.models import InstanceBrickConfigItem
from creme.creme_core.views import generic

from ..core import InstanceBrickMixin


class GraphInstanceBrickCreation(generic.base.EntityRelatedMixin,
                                 InstanceBrickMixin,
                                 generic.CheckedView):
    permissions = 'graphs.can_admin'
    entity_id_url_kwarg = 'graph_id'
    entity_classes = graphs.get_graph_model()

    def check_related_entity_permissions(self, entity, user):
        pass  # NB: only admin credentials are needed

    def post(self, *args, **kwargs):
        graph = self.get_related_entity()
        self.no_brick_instance_or_die(graph=graph)

        InstanceBrickConfigItem.objects.create(
            real_entity=graph, brick_class_id=self.brick_class.id,
        )

        return HttpResponse()
