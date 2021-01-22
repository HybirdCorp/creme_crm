# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

from . import constants

review_key = SettingKey(
    id=constants.SETTING_DISPLAY_REVIEW,
    description=_('Display minutes information in activities blocks'),
    app_label='activities', type=SettingKey.BOOL,
)
auto_subjects_key = SettingKey(
    id=constants.SETTING_AUTO_ORGA_SUBJECTS,
    description=_(
        'Add automatically the organisations of the participants as activities subjects'
    ),
    app_label='activities', type=SettingKey.BOOL,
)
# # DEPRECATED
# form_user_messages_key = SettingKey(
#     id=constants.SETTING_FORM_USERS_MSG,
#     description=_(
#         'In the activities form, propose to keep users informed '
#         'with user messages (the application «Assistants» is needed). '
#         'DEPRECATED (use custom forms instead).'
#     ),
#     app_label='activities', type=SettingKey.BOOL,
# )
