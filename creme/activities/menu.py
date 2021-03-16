# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from creme.creme_core.auth import build_creation_perm
from creme.creme_core.gui import menu

from . import get_activity_model

Activity = get_activity_model()
creation_perm = build_creation_perm(Activity)


class _ActivitiesURLEntry(menu.FixedURLEntry):
    permissions = 'activities'


class CalendarEntry(_ActivitiesURLEntry):
    id = 'activities-calendar'
    label = _('Calendar')
    url_name = 'activities__calendar'


class ActivitiesEntry(menu.ListviewEntry):
    id = 'activities-activities'
    model = Activity


class PhoneCallsEntry(_ActivitiesURLEntry):
    id = 'activities-phone_calls'
    label = _('Phone calls')
    url_name = 'activities__list_phone_calls'


class MeetingsEntry(_ActivitiesURLEntry):
    id = 'activities-meetings'
    label = _('Meetings')
    url_name = 'activities__list_meetings'


class ActivityCreationEntry(menu.CreationEntry):
    id = 'activities-create_activity'
    model = Activity


class PhoneCallCreationEntry(_ActivitiesURLEntry):
    id = 'activities-create_phonecall'
    label = _('Create a phone call')
    permissions = creation_perm

    @property
    def url(self):
        return reverse('activities__create_activity', args=('phonecall',))


class MeetingCreationEntry(_ActivitiesURLEntry):
    id = 'activities-create_meeting'
    label = _('Create a meeting')
    permissions = creation_perm

    @property
    def url(self):
        return reverse('activities__create_activity', args=('meeting',))
