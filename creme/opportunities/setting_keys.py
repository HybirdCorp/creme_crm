# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

quote_key = SettingKey(
    id='opportunities-use_current_quote',
    description=_(
        "Use current associated quote to "
        "determine an estimation of the opportunity's turnover"
    ),
    app_label='opportunities', type=SettingKey.BOOL,
)
target_constraint_key = SettingKey(
    id='opportunities-target_constraint',
    description=_(
        'When selecting an Invoice/Quote/Sales order to link, only the '
        'ones which have the same target than the Opportunity are proposed.'
    ),
    app_label='opportunities', type=SettingKey.BOOL,
)
emitter_constraint_key = SettingKey(
    id='opportunities-emitter_constraint',
    description=_(
        'When selecting an Invoice/Quote/Sales order to link, only the '
        'ones which have the same emitter than the Opportunity are proposed.'
    ),
    app_label='opportunities', type=SettingKey.BOOL,
)
