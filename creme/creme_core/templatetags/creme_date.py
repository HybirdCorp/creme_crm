# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2010  Hybird
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
from django.utils.translation import ugettext as _


register = template.Library()

@register.filter(name="timedelta_pprint")
def timedelta_pprint(timedelta_):
    days = timedelta_.days

    if days > 0:
        return _('%s day(s)') % days

    hours, hour_remain = divmod(timedelta_.seconds, 3600)

    if hours > 0:
        return _('%s hour(s)') % hours

    minutes, seconds = divmod(hour_remain, 60)

    if minutes > 0:
        return _('%s minute(s)') % minutes

    return _('%s second(s)') % seconds
