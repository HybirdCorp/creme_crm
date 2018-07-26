# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2018  Hybird
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

from django.utils.translation import ugettext_lazy as _, ugettext

from creme.creme_core.core import function_field
from creme.creme_core.models import FieldsConfig


class TurnoverField(function_field.FunctionField):
    name         = 'get_weighted_sales'
    verbose_name = _('Weighted sales')
    result_type  = function_field.FunctionFieldDecimal

    def __call__(self, entity, user):
        is_hidden = FieldsConfig.get_4_model(entity.__class__).is_fieldname_hidden

        if is_hidden('estimated_sales'):
            value = ugettext('Error: «Estimated sales» is hidden')
        elif is_hidden('chance_to_win'):
            value = ugettext(r'Error: «% of chance to win» is hidden')
        else:
            value = (entity.estimated_sales or 0) * (entity.chance_to_win or 0) / 100.0

        return self.result_type(value)
