from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

sandbox_key = SettingKey(
    id='crudity-crudity_sandbox_by_user',
    description=_('Are waiting actions are by user?'),
    app_label='crudity',
    type=SettingKey.BOOL,
)
