# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

PRIO_IMP_PK      = 1
PRIO_VERY_IMP_PK = 2
PRIO_NOT_IMP_PK  = 3

USERMESSAGE_PRIORITIES = {
    PRIO_IMP_PK:      _('Important'),
    PRIO_VERY_IMP_PK: _('Very important'),
    PRIO_NOT_IMP_PK:  _('Not important'),
}

MIN_HOUR_4_TODO_REMINDER = 'assistants-min_hour_4_todo_reminder'

BRICK_STATE_HIDE_VALIDATED_ALERTS = 'assistants-hide_validated_alerts'
BRICK_STATE_HIDE_VALIDATED_TODOS  = 'assistants-hide_validated_todos'
