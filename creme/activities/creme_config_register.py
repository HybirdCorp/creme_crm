# -*- coding: utf-8 -*-

from activities.models import ActivityType, PhoneCallType, Calendar
from activities.forms.activity_type import ActivityTypeForm
from activities.forms.calendar import CalendarConfigForm
from activities.blocks import user_calendars_block


#TODO: add Status and PhoneCallType (add 'is_custom' attr)
to_register = ((ActivityType, 'activity_type', ActivityTypeForm),
               (Calendar,     'calendar',      CalendarConfigForm),
              )

userblocks_to_register = (user_calendars_block,)