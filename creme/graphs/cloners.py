################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2024  Hybird
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

from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.core.copying import PostSaveCopier

from .models import RootNode


class RootNodesCopier(PostSaveCopier):
    def copy_to(self, target):
        for node in RootNode.objects.filter(graph=self._source):
            rn = RootNode.objects.create(graph=target, real_entity=node.entity)
            rn.relation_types.set(node.relation_types.all())


class GraphCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        RootNodesCopier,
    ]
