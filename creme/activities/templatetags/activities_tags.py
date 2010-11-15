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

from activities.models import CalendarActivityLink, Calendar

register = template.Library()

@register.filter(name="get_activity_calendars")
def get_activity_calendars(activity, only_publics=False):
    calendars_ids = CalendarActivityLink.objects.filter(activity=activity.pk).values_list('calendar', flat=True)
    calendars = Calendar.objects.filter(pk__in=calendars_ids)
    if only_publics:
        calendars = calendars.filter(is_public=True)
    return calendars
