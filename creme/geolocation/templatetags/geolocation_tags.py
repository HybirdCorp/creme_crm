################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2014-2022  Hybird
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

from django.template import Library
from django.utils.translation import ngettext

register = Library()


@register.filter
def geolocation_distance(value):
    if value < 1000:
        return ngettext(
            '{distance} meter',
            '{distance} meters',
            value
        ).format(distance=value)

    # NB: ngettext() warns if you pass a float ;
    #     is round() always the right plural rules in all languages??
    value = value / 1000.0
    return ngettext(
        '{distance:.1f} Km',
        '{distance:.1f} Km',
        round(value)
    ).format(distance=value)
