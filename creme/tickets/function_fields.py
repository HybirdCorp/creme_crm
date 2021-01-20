# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2021  Hybird
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

from creme.creme_core.core.function_field import FunctionField
from creme.creme_core.templatetags.creme_date import timedelta_pprint


class ResolvingDurationField(FunctionField):
    name         = 'get_resolving_duration'
    verbose_name = _('Resolving duration')

    def __call__(self, entity, user):
        if entity.status.is_closed:
            closing_date = entity.closing_date

            value = timedelta_pprint(closing_date - entity.created) if closing_date else '?'
        else:
            value = ''

        return self.result_type(value)
