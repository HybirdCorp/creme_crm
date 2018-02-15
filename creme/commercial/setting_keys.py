# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from . import constants


orga_approaches_key = SettingKey(id=constants.DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW,
                                 description=_(u"Display only organisations' commercial approaches on organisations' file."
                                               u" (Otherwise, display organisations', managers', employees', "
                                               u"related opportunities' commercial approaches)"
                                              ),
                                 app_label='commercial', type=SettingKey.BOOL,
                                )
