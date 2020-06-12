# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

REL_SUB_IS_INVITED_TO = 'events-subject_is_invited_to'
REL_OBJ_IS_INVITED_TO = 'events-object_is_invited_to'

REL_SUB_ACCEPTED_INVITATION = 'events-subject_accepted_invitation'
REL_OBJ_ACCEPTED_INVITATION = 'events-object_accepted_invitation'

REL_SUB_REFUSED_INVITATION = 'events-subject_refused_invitation'
REL_OBJ_REFUSED_INVITATION = 'events-object_refused_invitation'

REL_SUB_CAME_EVENT = 'events-subject_came_event'
REL_OBJ_CAME_EVENT = 'events-object_came_event'

REL_SUB_NOT_CAME_EVENT = 'events-subject_not_came_event'
REL_OBJ_NOT_CAME_EVENT = 'events-object_not_came_event'

REL_SUB_GEN_BY_EVENT = 'events-subject_gen_by_event'
REL_OBJ_GEN_BY_EVENT = 'events-object_gen_by_event'

DEFAULT_HFILTER_EVENT = 'events-hf'

# Invitation status
INV_STATUS_NOT_INVITED  = 1
INV_STATUS_NO_ANSWER    = 2
INV_STATUS_ACCEPTED     = 3
INV_STATUS_REFUSED      = 4

INV_STATUS_MAP = {
    INV_STATUS_NOT_INVITED: _('Not invited'),
    INV_STATUS_NO_ANSWER:   _('Did not answer'),
    INV_STATUS_ACCEPTED:    _('Accepted the invitation'),
    INV_STATUS_REFUSED:     _('Refused the invitation'),
}


# Presence status
PRES_STATUS_DONT_KNOW = 1
PRES_STATUS_COME      = 2
PRES_STATUS_NOT_COME  = 3

PRES_STATUS_MAP = {
    PRES_STATUS_DONT_KNOW: _('N/A'),
    PRES_STATUS_COME:      pgettext_lazy('events-presence_status', 'Come'),
    PRES_STATUS_NOT_COME:  pgettext_lazy('events-presence_status', 'Not come'),
}
