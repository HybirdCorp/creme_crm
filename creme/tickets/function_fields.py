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
from django.utils.translation import gettext_lazy as _

from creme.creme_core.core import sorter
from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.templatetags.creme_date import timedelta_pprint
from creme.tickets.models import AbstractTicket


class ResolvingDurationSorter(sorter.AbstractCellSorter):
    @override
    def get_sorting_item(self, cell):
        return sorter.AnnotationSortingItem(
            name='tickets-duration',
            model=AbstractTicket,
            db_expression=F('closing_date') - F('created'),
        )


class ResolvingDurationField(FunctionField):
    name         = 'get_resolving_duration'
    verbose_name = _('Resolving duration')
    # search_field_builder = TODO: filter min < duration < max
    sorter_class = ResolvingDurationSorter

    @override
    def __call__(self, entity, user):
        if entity.status.is_closed:
            closing_date = entity.closing_date

            value = timedelta_pprint(closing_date - entity.created) if closing_date else '?'
        else:
            value = ''

        return self.result_type(value)
