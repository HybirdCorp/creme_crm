# -*- coding: utf-8 -*-

from functools import partial

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import USER_THEME_NAME, USER_TIMEZONE


build_skey = partial(SettingKey, description='', hidden=True,
                     app_label='creme_config', type=SettingKey.STRING,
                    )
theme_key    = build_skey(id=USER_THEME_NAME)
timezone_key = build_skey(id=USER_TIMEZONE)
