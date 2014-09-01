# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA


payment_info_key = SettingKey(id=DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
                              description=_(u"Display payment information block only on the detailview of organisations managed by Creme"),
                              app_label='billing', type=SettingKey.BOOL,
                             )
