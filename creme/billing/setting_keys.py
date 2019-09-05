# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

# from . import constants


payment_info_key = SettingKey(
    # id=constants.DISPLAY_PAYMENT_INFO_ONLY_CREME_ORGA,
    id='billing-display_payment_info_only_creme_orga',
    description=_('Display payment information block only on the '
                  'detailview of organisations managed by Creme'
                 ),
    app_label='billing', type=SettingKey.BOOL,
)
