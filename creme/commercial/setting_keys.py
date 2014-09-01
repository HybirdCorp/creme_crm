# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import (IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED,
        DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW)


notification_key = SettingKey(id=IS_COMMERCIAL_APPROACH_EMAIL_NOTIFICATION_ENABLED,
                              description=_(u"Enable email reminder for commercial approaches"),
                              app_label='commercial', type=SettingKey.BOOL,
                             )
orga_approaches_key = SettingKey(id=DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW,
                                 description=_(u"Display only organisations' commercial approaches on organisations' file. (Otherwise, display organisations', managers', employees', related opportunities' commercial approaches)"),
                                 app_label='commercial', type=SettingKey.BOOL,
                                )
