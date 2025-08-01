from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

todo_reminder_key = SettingKey(
    id='assistants-min_hour_4_todo_reminder',
    description=_('Minimum hour to send the mails related to Todos'),
    app_label='assistants',
    type=SettingKey.HOUR,
)
