from django.utils.translation import gettext_lazy as _

from creme.creme_core.core.setting_key import SettingKey

review_key = SettingKey(
    id='activities-display_review_activities_blocks',  # TODO: rename with "bricks"
    description=_('Display minutes information in activities blocks'),
    app_label='activities', type=SettingKey.BOOL,
)
auto_subjects_key = SettingKey(
    id='activities-auto_orga_subjects',
    description=_(
        'Add automatically the organisations of the participants as activities subjects'
    ),
    app_label='activities', type=SettingKey.BOOL,
)

# Button "Unsuccessful phone call" ---
unsuccessful_subtype_key = SettingKey(
    id='activities-unsuccessful_call_subtype',
    description=_('Sub-type'),
    app_label='activities',
    type=SettingKey.STRING,  # Contains an ActivitySubType's UUID
    hidden=True,
)
unsuccessful_title_key = SettingKey(
    id='activities-unsuccessful_call_title',
    description=_('Title'),
    app_label='activities', type=SettingKey.STRING,
    hidden=True,
)
unsuccessful_status_key = SettingKey(
    id='activities-unsuccessful_call_status',
    description=_('Status'),
    app_label='activities',
    type=SettingKey.STRING,  # Contains a Status' UUID
    hidden=True,
)
unsuccessful_duration_key = SettingKey(
    id='activities-unsuccessful_call_duration',
    description=_('Duration (in minutes)'),
    app_label='activities', type=SettingKey.INT,
    hidden=True,
)
