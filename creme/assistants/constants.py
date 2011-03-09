# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _


PRIO_IMP_PK      = 1
PRIO_VERY_IMP_PK = 2
PRIO_NOT_IMP_PK  = 3

USERMESSAGE_PRIORITIES = {
        PRIO_IMP_PK:      _(u'Important'),
        PRIO_VERY_IMP_PK: _(u'Very important'),
        PRIO_NOT_IMP_PK:  _(u'Not important'),
    }
