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

from creme.activities.constants import REL_OBJ_PART_2_ACTIVITY
from creme.creme_core.core.cloning import EntityCloner
from creme.creme_core.core.copying import PreSaveCopier, RelationsCopier
from creme.creme_core.utils.collections import FluentList


# TODO: explicit this into description? move the activity to another time-slot?
class BusyCopier(PreSaveCopier):
    def copy_to(self, target):
        target.busy = False


class ActivityRelationsCopier(RelationsCopier):
    allowed_internal_rtype_ids = [REL_OBJ_PART_2_ACTIVITY]


class ActivityCloner(EntityCloner):
    pre_save_copiers = [
        *EntityCloner.pre_save_copiers,
        BusyCopier,
    ]
    post_save_copiers = FluentList(
        EntityCloner.post_save_copiers
    ).replace(old=RelationsCopier, new=ActivityRelationsCopier)
