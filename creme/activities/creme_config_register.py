# -*- coding: utf-8 -*-

from creme.activities.models import ActivityType, Calendar #PhoneCallType
from creme.activities.forms.activity_type import ActivityTypeForm
from creme.activities.forms.calendar import CalendarConfigForm
from creme.activities.blocks import user_calendars_block


#TODO: add Status and PhoneCallType (add 'is_custom' attr)
to_register = ((ActivityType, 'activity_type', ActivityTypeForm),
               (Calendar,     'calendar',      CalendarConfigForm),
              )

userblocks_to_register = (user_calendars_block,)