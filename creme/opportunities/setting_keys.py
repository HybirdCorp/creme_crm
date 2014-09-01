# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import SETTING_USE_CURRENT_QUOTE


quote_key = SettingKey(id=SETTING_USE_CURRENT_QUOTE,
                       description=_(u"Use current associated quote to determine an estimation of the opportunity's turnover"),
                       app_label='opportunities', type=SettingKey.BOOL,
                      )
