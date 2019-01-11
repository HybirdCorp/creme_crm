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

from django import template
from django.utils.translation import ungettext

register = template.Library()


@register.filter(name='date_timedelta_pprint')
def timedelta_pprint(timedelta_):
    days = timedelta_.days

    if days > 0:
        return ungettext('{number} day', '{number} days', days).format(number=days)

    hours, hour_remain = divmod(timedelta_.seconds, 3600)

    if hours > 0:
        return ungettext('{number} hour', '{number} hours', hours).format(number=hours)

    minutes, seconds = divmod(hour_remain, 60)

    if minutes > 0:
        return ungettext('{number} minute', '{number} minutes', minutes).format(number=minutes)

    return ungettext('{number} second', '{number} seconds', seconds).format(number=seconds)
