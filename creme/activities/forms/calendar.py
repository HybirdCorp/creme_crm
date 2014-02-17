# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2009-2014  Hybird
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

from django.contrib.auth.models import User
from django.forms import ModelChoiceField
from django.utils.translation import ugettext as _

from creme.creme_core.forms.base import CremeModelForm, CremeForm
from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.forms.fields import ColorField

from ..models import Calendar


class CalendarForm(CremeModelForm):
    color = ColorField(label=_(u'Color'), required=False)

    class Meta:
        model = Calendar
        exclude = ('user',)

    def get_user(self):
        return self.user

    def save(self):
        self.instance.user = self.get_user()
        return super(CalendarForm, self).save()


class CalendarConfigForm(CalendarForm):
    def __init__(self, *args, **kwargs):
        super(CalendarForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['user'] = ModelChoiceField(label=_('User'),
                                                   queryset=User.objects.filter(is_staff=False),
                                                   empty_label=None,
                                                   initial=self.user.id,
                                                  )

    def get_user(self):
        return self.cleaned_data.get('user') or self.instance.user


#TODO: manage multi-calendar better
class ActivityCalendarLinkerForm(CremeForm):
    calendar = ModelChoiceField(label=_('Calendar'), queryset=None, empty_label=None)

    #def __init__(self, activity, *args, **kwargs):
        #self.activity = activity
    def __init__(self, instance, *args, **kwargs):
        self.activity = instance
        super(ActivityCalendarLinkerForm, self).__init__(*args, **kwargs)
        user = self.user
        #self.calendar = calendar = activity.calendars.get(user=user)
        calendars = instance.calendars.filter(user=user)[:2]

        if len(calendars) > 1:
            raise ConflictError("You can change the calendar only when there "
                                "is only one calendar related to the activity"
                               )

        self.calendar = calendar = calendars[0]

        calendar_field = self.fields['calendar']
        calendar_field.queryset = Calendar.objects.filter(user=user)
        calendar_field.initial = calendar.id

    def save(self, *args, **kwargs):
        old_calendar = self.calendar
        new_calendar = self.cleaned_data.get('calendar')

        if new_calendar != old_calendar:
            calendars = self.activity.calendars
            calendars.remove(old_calendar)
            calendars.add(new_calendar)
