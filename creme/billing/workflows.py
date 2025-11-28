################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2025  Hybird
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

from creme.billing.models import Line
from creme.creme_core.core import workflow

# TODO: doc-strings


class LineUpdated(workflow.WorkflowEvent):
    def __init__(self, line: Line):
        # self.line = line TODO?
        self.related_document = line.related_document

    # TODO: test (+ test queries?)
    # NB: we merge event related to the same Invoice/Quote...
    def inhibits(self, /, other):
        return (
            isinstance(other, type(self))
            and self.related_document.id == other.related_document.id
        )


class LineUpdateTrigger(workflow.WorkflowTrigger):
    event_class = LineUpdated
    entity_key = 'billing_entity'

    def _activate(self, event):
        return {self.entity_key: event.related_document}


class TotalUpdateAction(workflow.WorkflowAction):
    # """Action which adds a CremeProperty to the chosen source."""
    # type_id = 'creme_core-property_adding'  # TODO: error if type_id?
    # verbose_name = _('Adding a property')

    entity_key = LineUpdateTrigger.entity_key

    def execute(self, context, user=None):
        # TODO: update()?
        # print('EXECUTE', context.get(self.entity_key))
        context.get(self.entity_key).save()  # Update totals
