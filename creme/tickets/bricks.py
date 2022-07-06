################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2020  Hybird
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

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.gui.bricks import EntityBrick

from . import get_ticket_model
from .function_fields import ResolvingDurationField


class TicketBrick(EntityBrick):
    verbose_name = _('Information on the ticket')

    def _get_cells(self, entity, context):
        cells = super()._get_cells(entity=entity, context=context)

        cells.append(EntityCellFunctionField(
            model=get_ticket_model(),
            func_field=ResolvingDurationField(),
        ))
        return cells

    def _get_title(self, entity, context):
        return self.verbose_name
