# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from .constants import DISPLAY_REVIEW_ACTIVITIES_BLOCKS, SETTING_AUTO_ORGA_SUBJECTS


review_key = SettingKey(id=DISPLAY_REVIEW_ACTIVITIES_BLOCKS,
                        description=_(u"Display minutes information in activities blocks"),
                        app_label='activities', type=SettingKey.BOOL,
                       )
auto_subjects_key = SettingKey(id=SETTING_AUTO_ORGA_SUBJECTS,
                               description=_(u"Add automatically the organisations of the participants as activities subjects"),
                               app_label='activities', type=SettingKey.BOOL,
                              )
