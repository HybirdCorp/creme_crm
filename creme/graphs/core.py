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

from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import InstanceBrickConfigItem
from creme.graphs.bricks import GraphInstanceBrick
from creme.graphs.models import AbstractGraph


class InstanceBrickMixin:
    brick_class = GraphInstanceBrick

    def no_brick_instance_or_die(self, graph: AbstractGraph) -> None:
        if InstanceBrickConfigItem.objects.filter(
            entity_id=graph.id, brick_class_id=self.brick_class.id,
        ).exists():
            raise ConflictError(_(
                'A block is already available in the configuration'
            ))
