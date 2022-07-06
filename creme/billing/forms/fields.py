################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2015-2019  Hybird
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

from django.forms.fields import DecimalField
from django.forms.utils import ValidationError
from django.utils.translation import gettext as _


class BillingDiscountField(DecimalField):
    def validate(self, value):
        super().validate(value)

        if not (0 <= value <= 100):
            raise ValidationError(_('Enter a number between 0 and 100 (it is a percentage).'))
