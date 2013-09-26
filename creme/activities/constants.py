# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

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

CREATION_LABELS = {ACTIVITYTYPE_TASK:       _(u'Add a task'),
                   ACTIVITYTYPE_MEETING:    _(u'Add a meeting'),
                   ACTIVITYTYPE_PHONECALL:  _(u'Add a phonecall'),
                   ACTIVITYTYPE_GATHERING:  _(u'Add a gathering'),
                   ACTIVITYTYPE_SHOW:       _(u'Add a show'),
                   ACTIVITYTYPE_DEMO:       _(u'Add a demo'),
                   ACTIVITYTYPE_INDISPO:    _(u'Add an indisponibility'),
                  }

ACTIVITYSUBTYPE_PHONECALL_INCOMING   = 'activities-activitysubtype_incoming'
ACTIVITYSUBTYPE_PHONECALL_OUTGOING   = 'activities-activitysubtype_outgoing'
ACTIVITYSUBTYPE_PHONECALL_CONFERENCE = 'activities-activitysubtype_conference'

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

DISPLAY_REVIEW_ACTIVITIES_BLOCKS = 'activities-display_review_activities_blocks'

# Floating styles
NARROW          = 1
FLOATING_TIME   = 2
FLOATING        = 3

EFILTER_MEETINGS   = 'activities-meetings'
EFILTER_PHONECALLS = 'activities-phonecalls'
EFILTER_TASKS      = 'activities-tasks'

DEFAULT_CALENDAR_COLOR = 'C1D9EC'
COLOR_POOL = ('c1d9ec', '94c6db', #blue icecream
              'f7cbc6', 'f7b5ad', #pink icecream
              'b9fae5', '61ffcd', #turquoises
              'fff4b8', 'ffe96e', #yellows
              'd4ffb8', 'b4ff82', #greens
              'f9b3ff', 'f36bff', #pink-mallow
              'ffcea6', 'ffab66', #oranges
             )

MAX_ELEMENT_SEARCH = 10
