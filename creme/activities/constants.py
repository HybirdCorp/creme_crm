# import warnings
from django.utils.translation import gettext_lazy as _

REL_SUB_LINKED_2_ACTIVITY = 'activities-subject_linked_2_activity'
REL_OBJ_LINKED_2_ACTIVITY = 'activities-object_linked_2_activity'

REL_SUB_ACTIVITY_SUBJECT = 'activities-subject_activity_subject'
REL_OBJ_ACTIVITY_SUBJECT = 'activities-object_activity_subject'

# TODO: participates IN...
REL_SUB_PART_2_ACTIVITY = 'activities-subject_participates_to_activity'
REL_OBJ_PART_2_ACTIVITY = 'activities-object_participates_to_activity'

# TYPES ------------------------------------------------------------------------
UUID_TYPE_UNAVAILABILITY = '1cd1de3d-1fad-4eb6-82a8-93059f1b5ea3'
UUID_TYPE_TASK           = '7fda7c3f-f0e8-47f9-9d90-7931293fdff9'
UUID_TYPE_MEETING        = '5943b787-441f-453d-a96a-ff436fd37f2f'
UUID_TYPE_PHONECALL      = '86934e63-1ba5-4b19-b2a5-43f9412fddc3'
UUID_TYPE_GATHERING      = 'a8295a0b-7823-4cce-9ea0-307640eaf4a3'
UUID_TYPE_SHOW           = '59772b5c-e034-4499-a9cd-7f32d7ede8de'
UUID_TYPE_DEMO           = 'a9a13fc8-cf00-46e4-b2dc-8e98c086c186'

CREATION_LABELS = {
    UUID_TYPE_UNAVAILABILITY: _('Create an unavailability'),
    UUID_TYPE_TASK:           _('Create a task'),
    UUID_TYPE_MEETING:        _('Create a meeting'),
    UUID_TYPE_PHONECALL:      _('Create a phone call'),
    UUID_TYPE_GATHERING:      _('Create a gathering'),
    UUID_TYPE_SHOW:           _('Create a show'),
    UUID_TYPE_DEMO:           _('Create a demo'),
}
ICONS = {
    UUID_TYPE_MEETING:   ('meeting', _('Meeting')),
    UUID_TYPE_PHONECALL: ('phone',   _('Phone call')),
    UUID_TYPE_TASK:      ('task',    _('Task')),
}

# SUB-TYPES --------------------------------------------------------------------
UUID_SUBTYPE_UNAVAILABILITY = 'cf5d1b51-e949-43cb-a347-99a8992f6030'

UUID_SUBTYPE_MEETING_MEETING       = 'e129154e-0d33-4f1e-9d2f-2ece81688e31'
UUID_SUBTYPE_MEETING_QUALIFICATION = 'f6db7626-8138-4529-b2c6-530387da10a7'
UUID_SUBTYPE_MEETING_REVIVAL       = '9d65111b-767a-41d2-b03b-81bc9ca0c7a5'
UUID_SUBTYPE_MEETING_NETWORK       = '7a42a5a2-e554-44fa-8d10-84ac0ef6ebda'
UUID_SUBTYPE_MEETING_OTHER         = 'ad81256c-dac8-4d33-b0b6-79b0f142496b'

UUID_SUBTYPE_PHONECALL_INCOMING   = '49b2ce30-fe7b-409b-b4ef-4749400b88c7'
UUID_SUBTYPE_PHONECALL_OUTGOING   = '38729b63-8133-4244-84c4-082364846638'
UUID_SUBTYPE_PHONECALL_CONFERENCE = '55aebf7f-ef4f-4c1c-a3c6-1a68ba330d7d'
UUID_SUBTYPE_PHONECALL_FAILED     = 'e0cf04b0-b407-413e-b6d4-8946ea815041'

# ------------------------------------------------------------------------------
UUID_STATUS_PLANNED      = '7efc9a5d-eacd-4be0-afa8-3277256bfcac'
UUID_STATUS_IN_PROGRESS  = '5152460c-18c3-4b8e-a780-ac286294a46e'
UUID_STATUS_DONE         = '4c7f518b-6bd5-44ea-a867-5e33f50646da'
UUID_STATUS_DELAYED      = '98f1990a-049a-4ff9-9a52-957a90e43bbd'
UUID_STATUS_CANCELLED    = '9c23117f-a2eb-4284-8cc2-0c541f87e7ef'
UUID_STATUS_UNSUCCESSFUL = '480717eb-f4cf-4075-ad9f-24b650e3d538'

# ------------------------------------------------------------------------------
EFILTER_MEETINGS    = 'activities-meetings'
EFILTER_PHONECALLS  = 'activities-phonecalls'
EFILTER_TASKS       = 'activities-tasks'
EFILTER_PARTICIPATE = 'activities-participate'

DEFAULT_HFILTER_ACTIVITY = 'activities-hf_activity'


# def __getattr__(name):
#     if name == 'NARROW':
#         warnings.warn(
#             '"NARROW" is deprecated; use Activity.FloatingType.NARROW instead.',
#             DeprecationWarning,
#         )
#         return 1
#
#     if name == 'FLOATING_TIME':
#         warnings.warn(
#             '"FLOATING_TIME" is deprecated; use Activity.FloatingType.FLOATING_TIME instead.',
#             DeprecationWarning,
#         )
#         return 2
#
#     if name == 'FLOATING':
#         warnings.warn(
#             '"FLOATING" is deprecated; use Activity.FloatingType.FLOATING instead.',
#             DeprecationWarning,
#         )
#         return 3
#
#     if name == 'SETTING_DISPLAY_REVIEW':
#         warnings.warn(
#             '"SETTING_DISPLAY_REVIEW" is deprecated; '
#             'use activities.setting_keys.review_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-display_review_activities_blocks'
#
#     if name == 'SETTING_AUTO_ORGA_SUBJECTS':
#         warnings.warn(
#             '"SETTING_AUTO_ORGA_SUBJECTS" is deprecated; '
#             'use activities.setting_keys.auto_subjects_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-auto_orga_subjects'
#
#     if name == 'SETTING_UNSUCCESSFUL_SUBTYPE_UUID':
#         warnings.warn(
#             '"SETTING_UNSUCCESSFUL_SUBTYPE_UUID" is deprecated; '
#             'use activities.setting_keys.unsuccessful_subtype_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-unsuccessful_call_subtype'
#
#     if name == 'SETTING_UNSUCCESSFUL_TITLE':
#         warnings.warn(
#             '"SETTING_UNSUCCESSFUL_TITLE" is deprecated; '
#             'use activities.setting_keys.unsuccessful_title_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-unsuccessful_call_title'
#
#     if name == 'SETTING_UNSUCCESSFUL_STATUS_UUID':
#         warnings.warn(
#             '"SETTING_UNSUCCESSFUL_STATUS_UUID" is deprecated; '
#             'use activities.setting_keys.unsuccessful_status_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-unsuccessful_call_status'
#
#     if name == 'SETTING_UNSUCCESSFUL_DURATION':
#         warnings.warn(
#             '"SETTING_UNSUCCESSFUL_DURATION" is deprecated; '
#             'use activities.setting_keys.unsuccessful_duration_key.id instead.',
#             DeprecationWarning,
#         )
#         return 'activities-unsuccessful_call_duration'
#
#     raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
