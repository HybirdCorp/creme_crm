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

from django import template

register = template.Library()


@register.filter(name='sms_phonenumber')
def phonenumber(value):
    return ''.join(c for c in value if c.isdigit())


@register.filter(name='sms_formatphone')
def formatphone(value):
    if not value:
        return ''

    length = len(value)

    if length < 6:
        return value

    if length % 2:
        return value[:3] + ''.join(
            f' {c}' if not i % 2 else c for i, c in enumerate(value[3:])
        )

    return ''.join(f' {c}' if i and not i % 2 else c for i, c in enumerate(value))
