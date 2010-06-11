# -*- coding: utf-8 -*-

from activities.models import ActivityType, PhoneCallType
from activities.forms.activity_type import ActivityTypeForm


to_register = ((ActivityType, 'activity_type', ActivityTypeForm),)
