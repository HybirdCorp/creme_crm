# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import SETTING_EMAILCAMPAIGN_SENDER

emailcampaign_sender = SettingKey(
    id=SETTING_EMAILCAMPAIGN_SENDER,
    description=_('Allowed email campaign sender.'),
    app_label='emails',
    type=SettingKey.EMAIL,
)
