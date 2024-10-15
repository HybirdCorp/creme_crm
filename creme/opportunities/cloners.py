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
from creme.creme_core.core.copying import PreSaveCopier


# TODO: rename property Opportunity.target to "receiver"
class EmitterAndReceiverCopier(PreSaveCopier):
    def copy_to(self, target):
        source = self._source
        target.emitter = source.emitter
        target.target  = source.target


class OpportunityCloner(EntityCloner):
    pre_save_copiers = [
        *EntityCloner.pre_save_copiers,
        EmitterAndReceiverCopier,
    ]
