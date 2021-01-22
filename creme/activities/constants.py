# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

REL_SUB_LINKED_2_ACTIVITY = 'activities-subject_linked_2_activity'
REL_OBJ_LINKED_2_ACTIVITY = 'activities-object_linked_2_activity'

REL_SUB_ACTIVITY_SUBJECT = 'activities-subject_activity_subject'
REL_OBJ_ACTIVITY_SUBJECT = 'activities-object_activity_subject'

REL_SUB_PART_2_ACTIVITY = 'activities-subject_participates_to_activity'
REL_OBJ_PART_2_ACTIVITY = 'activities-object_participates_to_activity'

ACTIVITYTYPE_TASK      = 'activities-activitytype_task'
ACTIVITYTYPE_MEETING   = 'activities-activitytype_meeting'
ACTIVITYTYPE_PHONECALL = 'activities-activitytype_phonecall'
ACTIVITYTYPE_GATHERING = 'activities-activitytype_gathering'
ACTIVITYTYPE_SHOW      = 'activities-activitytype_show'
ACTIVITYTYPE_DEMO      = 'activities-activitytype_demo'
ACTIVITYTYPE_INDISPO   = 'activities-activitytype_indispo'

CREATION_LABELS = {
    ACTIVITYTYPE_TASK:       _('Create a task'),
    ACTIVITYTYPE_MEETING:    _('Create a meeting'),
    ACTIVITYTYPE_PHONECALL:  _('Create a phone call'),
    ACTIVITYTYPE_GATHERING:  _('Create a gathering'),
    ACTIVITYTYPE_SHOW:       _('Create a show'),
    ACTIVITYTYPE_DEMO:       _('Create a demo'),
    ACTIVITYTYPE_INDISPO:    _('Create an unavailability'),
}
ICONS = {
    ACTIVITYTYPE_MEETING:   ('meeting', _('Meeting')),
    ACTIVITYTYPE_PHONECALL: ('phone',   _('Phone call')),
    ACTIVITYTYPE_TASK:      ('task',    _('Task')),
}

ACTIVITYSUBTYPE_PHONECALL_INCOMING   = 'activities-activitysubtype_incoming'
ACTIVITYSUBTYPE_PHONECALL_OUTGOING   = 'activities-activitysubtype_outgoing'
ACTIVITYSUBTYPE_PHONECALL_CONFERENCE = 'activities-activitysubtype_conference'
ACTIVITYSUBTYPE_PHONECALL_FAILED     = 'activities-activitysubtype_failed'

ACTIVITYSUBTYPE_MEETING_MEETING       = 'activities-activitysubtype_meeting'
ACTIVITYSUBTYPE_MEETING_QUALIFICATION = 'activities-activitysubtype_qualification'
ACTIVITYSUBTYPE_MEETING_REVIVAL       = 'activities-activitysubtype_revival'
ACTIVITYSUBTYPE_MEETING_NETWORK       = 'activities-activitysubtype_network'
ACTIVITYSUBTYPE_MEETING_OTHER         = 'activities-activitysubtype_other'

STATUS_PLANNED     = 1
STATUS_IN_PROGRESS = 2
STATUS_DONE        = 3
STATUS_DELAYED     = 4
STATUS_CANCELLED   = 5

SETTING_DISPLAY_REVIEW     = 'activities-display_review_activities_blocks'
SETTING_AUTO_ORGA_SUBJECTS = 'activities-auto_orga_subjects'
# SETTING_FORM_USERS_MSG     = 'activities-form_user_messages'  # DEPRECATED

# Floating styles
NARROW        = 1
FLOATING_TIME = 2
FLOATING      = 3

EFILTER_MEETINGS    = 'activities-meetings'
EFILTER_PHONECALLS  = 'activities-phonecalls'
EFILTER_TASKS       = 'activities-tasks'
EFILTER_PARTICIPATE = 'activities-participate'

DEFAULT_HFILTER_ACTIVITY = 'activities-hf_activity'

DEFAULT_CALENDAR_COLOR = 'C1D9EC'
COLOR_POOL = (
    'c1d9ec', '94c6db',  # Blue icecream
    'f7cbc6', 'f7b5ad',  # Pink icecream
    'b9fae5', '61ffcd',  # Turquoises
    'fff4b8', 'ffe96e',  # Yellows
    'd4ffb8', 'b4ff82',  # Greens
    'f9b3ff', 'f36bff',  # Pink-mallow
    'ffcea6', 'ffab66',  # Oranges
)
