# -*- coding: utf-8 -*-

from activities.models import ActivityType, PhoneCallType, Calendar
from activities.forms.activity_type import ActivityTypeForm
from activities.forms.calendar import CalendarConfigForm


to_register = ((ActivityType, 'activity_type', ActivityTypeForm),
               (Calendar,     'calendar',      CalendarConfigForm),)
