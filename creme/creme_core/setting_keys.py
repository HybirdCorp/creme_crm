# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from . import constants
from .core.setting_key import SettingKey


block_opening_key = SettingKey(id=constants.SETTING_BLOCK_DEFAULT_STATE_IS_OPEN,
                               description=_(u'By default, are blocks open ?'),
                               app_label='creme_core', type=SettingKey.BOOL,
                              )
block_showempty_key = SettingKey(id=constants.SETTING_BLOCK_DEFAULT_STATE_SHOW_EMPTY_FIELDS,
                                 description=_(u'By default, are empty fields displayed ?'),
                                 app_label='creme_core', type=SettingKey.BOOL,
                                )
currency_symbol_key = SettingKey(id=constants.DISPLAY_CURRENCY_LOCAL_SYMBOL,
                                 description=_(u'Display the currency local symbol (ex: €) ? '
                                               u'If no the international symbol will be used (ex: EUR)'
                                              ),
                                 app_label='creme_core', type=SettingKey.BOOL,
                                )
