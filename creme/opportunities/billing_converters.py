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

from creme.creme_core.core.copying import Copier
from creme.creme_core.models import Relation, RelationType

from . import constants


class OpportunitiesRelationAdder(Copier):
    source_rtype_id = ''
    target_rtype_id = ''

    def copy_to(self, target):
        assert self.target_rtype_id
        target_rtype = RelationType.objects.get(id=self.target_rtype_id)

        if target_rtype.enabled and target_rtype.is_copiable:
            # TODO: populate objects entities?
            for rel in self._source.relations.filter(
                type=self.source_rtype_id, type__enabled=True, type__is_copiable=True,
            ):
                Relation.objects.safe_create(
                    user=self._user,
                    subject_entity=target,
                    type=target_rtype,
                    object_entity=rel.object_entity,
                )


class QuoteToSalesOrderRelationAdder(OpportunitiesRelationAdder):
    source_rtype_id = constants.REL_SUB_LINKED_QUOTE
    target_rtype_id = constants.REL_SUB_LINKED_SALESORDER


class QuoteToInvoiceRelationAdder(OpportunitiesRelationAdder):
    source_rtype_id = constants.REL_SUB_LINKED_QUOTE
    target_rtype_id = constants.REL_SUB_LINKED_INVOICE


class SalesOrderToInvoiceRelationAdder(OpportunitiesRelationAdder):
    source_rtype_id = constants.REL_SUB_LINKED_SALESORDER
    target_rtype_id = constants.REL_SUB_LINKED_INVOICE
