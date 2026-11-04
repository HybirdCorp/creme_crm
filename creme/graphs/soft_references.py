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

from typing import override

from creme.creme_core.core.soft_reference import SoftReferenceCollector
from creme.creme_core.models import RelationType

from . import get_graph_model


class GraphRelationTypeRefCollector(SoftReferenceCollector):
    """Collect the Graphs which reference a RelationType ("peripheral relationships").

    Notice that these references are stored in ManyToManyFields, & this type of
    fields has no attribute 'on_delete' like ForeignKeys.
    """
    id = 'graphs-graph-rtype'
    model = RelationType

    @override
    def collect(self, instance):
        assert isinstance(instance, self.model)

        yield from get_graph_model().objects.filter(
            orbital_relation_types=instance,
        )
