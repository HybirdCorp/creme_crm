# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import SETTING_CRUDITY_SANDBOX_BY_USER

sandbox_key = SettingKey(
    id=SETTING_CRUDITY_SANDBOX_BY_USER,
    description=_('Are waiting actions are by user?'),
    app_label='crudity',
    type=SettingKey.BOOL,
)
