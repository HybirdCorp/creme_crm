################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2013-2025  Hybird
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

from django.db.models.query_utils import Q

from creme.creme_core.models import CremeEntity, EntityFilter
from creme.creme_core.utils.queries import QSerializer
from creme.creme_core.views.generic import EntitiesList


# TODO: move to creme_core ?
class ListViewURLBuilder:
    entity_filter_id_arg = EntitiesList.entity_filter_id_arg
    requested_q_arg      = EntitiesList.requested_q_arg

    def __init__(self,
                 model: type[CremeEntity],
                 filter: EntityFilter | None = None,
                 common_q: Q | None = None):
        fmt = getattr(model, 'get_lv_absolute_url', None)

        if fmt:
            fmt = '{url}?{arg}={value}'.format(
                url=model.get_lv_absolute_url(),
                arg=self.requested_q_arg,
                value='{}',
            )

            if filter:
                fmt += f'&{self.entity_filter_id_arg}={filter.id}'

        self._fmt = fmt
        self._common_q = common_q or Q()

    def __call__(self, q_filter: dict | None = None) -> str | None:
        fmt = self._fmt

        if not fmt:
            return None

        final_q = self._common_q & Q(**q_filter) if q_filter else self._common_q

        return fmt.format(
            QSerializer().dumps(final_q) if final_q else ''
        )
