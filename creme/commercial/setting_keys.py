# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from . import constants

orga_approaches_key = SettingKey(
    id=constants.DISPLAY_ONLY_ORGA_COM_APPROACH_ON_ORGA_DETAILVIEW,
    description=_(
        "Display only organisations' commercial approaches on organisations' file."
        " (Otherwise, display organisations', managers', employees', "
        "related opportunities' commercial approaches)"
    ),
    app_label='commercial', type=SettingKey.BOOL,
)
