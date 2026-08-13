################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2026  Hybird
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

from django.db.models import F
from django.db.models.functions import Coalesce
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core import sorter
from creme.creme_core.core.function_field import (
    FunctionField,
    FunctionFieldDecimal,
    FunctionFieldResult,
)
from creme.creme_core.models import FieldsConfig
from creme.opportunities.models import AbstractOpportunity


class TurnoverSorter(sorter.AbstractCellSorter):
    @override
    def get_sorting_item(self, cell):
        is_hidden = FieldsConfig.objects.get_for_model(cell.model).is_fieldname_hidden
        if is_hidden('estimated_sales') or is_hidden('chance_to_win'):
            return None

        return sorter.AnnotationSortingItem(
            name='opportunities-weighted_sales',
            model=AbstractOpportunity,
            # NB: no need to divide by 100, th relative order remains the same
            db_expression=Coalesce(F('estimated_sales'), 0) * Coalesce(F('chance_to_win'), 0),
        )


class TurnoverField(FunctionField):
    name         = 'get_weighted_sales'
    verbose_name = _('Weighted sales')
    result_type  = FunctionFieldDecimal
    sorter_class = TurnoverSorter

    @override
    def __call__(self, entity, user):
        is_hidden = FieldsConfig.objects.get_for_model(entity.__class__).is_fieldname_hidden

        if is_hidden('estimated_sales'):
            return FunctionFieldResult(gettext('Error: «Estimated sales» is hidden'))

        if is_hidden('chance_to_win'):
            return FunctionFieldResult(gettext(r'Error: «% of chance to win» is hidden'))

        return self.result_type(
            (entity.estimated_sales or 0) * (entity.chance_to_win or 0) / 100.0
        )
