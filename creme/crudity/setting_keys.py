from django.utils.translation import gettext_lazy as _

# from .constants import SETTING_CRUDITY_SANDBOX_BY_USER
from creme.creme_core.core.setting_key import SettingKey

sandbox_key = SettingKey(
    # id=SETTING_CRUDITY_SANDBOX_BY_USER,
    id='crudity-crudity_sandbox_by_user',
    description=_('Are waiting actions are by user?'),
    app_label='crudity',
    type=SettingKey.BOOL,
)
