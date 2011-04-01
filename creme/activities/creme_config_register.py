# -*- coding: utf-8 -*-

from activities.models import ActivityType, PhoneCallType, Calendar
from activities.forms.activity_type import ActivityTypeForm
from activities.forms.calendar import CalendarForm


#TODO: add Status and PhoneCallType (add 'is_custom' attr)
to_register = ((ActivityType, 'activity_type', ActivityTypeForm),
               (Calendar,     'calendar',      CalendarForm),)
