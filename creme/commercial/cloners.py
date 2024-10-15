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


class ObjectivesCopier(PostSaveCopier):
    def copy_to(self, target):
        from .models import ActObjective

        ActObjective.objects.bulk_create([
            ActObjective(
                name=objective.name,
                act=target,
                counter=objective.counter,
                counter_goal=objective.counter_goal,
                ctype=objective.ctype,
            ) for objective in ActObjective.objects.filter(act=self._source).order_by('id')
        ])


class ComponentsCopier(PostSaveCopier):
    def copy_to(self, target):
        for pattern_component in self._source.get_components_tree():
            pattern_component.clone(target)


class ActCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        ObjectivesCopier,
    ]


class PatternCloner(EntityCloner):
    post_save_copiers = [
        *EntityCloner.post_save_copiers,
        ComponentsCopier,
    ]
