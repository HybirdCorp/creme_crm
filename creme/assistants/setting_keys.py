# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import MIN_HOUR_4_TODO_REMINDER

todo_reminder_key = SettingKey(
    id=MIN_HOUR_4_TODO_REMINDER,
    description=_('Minimum hour to send the mails related to Todos'),
    app_label='assistants',
    type=SettingKey.HOUR,
)
