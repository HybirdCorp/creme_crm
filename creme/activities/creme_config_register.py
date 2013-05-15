# -*- coding: utf-8 -*-

from .models import ActivityType, ActivitySubType, Status, Calendar
from .forms.activity_type import ActivityTypeForm, ActivitySubTypeForm
from .forms.calendar import CalendarConfigForm
from .blocks import user_calendars_block


to_register = ((ActivityType,    'activity_type',     ActivityTypeForm),
               (ActivitySubType, 'activity_sub_type', ActivitySubTypeForm),
               (Status,          'status'),
               (Calendar,        'calendar',          CalendarConfigForm),
              )

userblocks_to_register = (user_calendars_block,)
