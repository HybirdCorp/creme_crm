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

unsuccessful_subtype_key = SettingKey(
    id=constants.SETTING_UNSUCCESSFUL_SUBTYPE_UUID,
    description=_('Sub-type'),
    app_label='activities', type=SettingKey.STRING,
    hidden=True,
)
unsuccessful_title_key = SettingKey(
    id=constants.SETTING_UNSUCCESSFUL_TITLE,
    description=_('Title'),
    app_label='activities', type=SettingKey.STRING,
    hidden=True,
)
unsuccessful_status_key = SettingKey(
    id=constants.SETTING_UNSUCCESSFUL_STATUS_UUID,
    description=_('Status'),
    app_label='activities', type=SettingKey.STRING,
    hidden=True,
)
unsuccessful_duration_key = SettingKey(
    id=constants.SETTING_UNSUCCESSFUL_DURATION,
    description=_('Duration (in minutes)'),
    app_label='activities', type=SettingKey.INT,
    hidden=True,
)
