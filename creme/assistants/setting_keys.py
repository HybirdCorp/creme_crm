from django.utils.translation import gettext_lazy as _

# from .constants import MIN_HOUR_4_TODO_REMINDER
from creme.creme_core.core.setting_key import SettingKey

todo_reminder_key = SettingKey(
    # id=MIN_HOUR_4_TODO_REMINDER,
    id='assistants-min_hour_4_todo_reminder',
    description=_('Minimum hour to send the mails related to Todos'),
    app_label='assistants',
    type=SettingKey.HOUR,
)
