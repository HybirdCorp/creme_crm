# -*- coding: utf-8 -*-

from activities.models import ActivityType, PhoneCallType, Calendar
from activities.forms.activity_type import ActivityTypeForm
from activities.forms.calendar import CalendarForm


to_register = ((ActivityType, 'activity_type', ActivityTypeForm),
               (Calendar,     'calendar',      CalendarForm),)
