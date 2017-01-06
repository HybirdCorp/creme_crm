# -*- coding: utf-8 -*-

from . import models, blocks
from .forms import activity_type as type_forms
from .forms.calendar import CalendarConfigForm


to_register = ((models.ActivityType,    'activity_type',     type_forms.ActivityTypeForm),
               (models.ActivitySubType, 'activity_sub_type', type_forms.ActivitySubTypeForm),
               (models.Status,          'status'),
               (models.Calendar,        'calendar',          CalendarConfigForm),
              )

userblocks_to_register = (blocks.user_calendars_block,)
