# -*- coding: utf-8 -*-

from django.utils.translation import ugettext_lazy as _

NOT_STARTED_PK      = 1
CURRENT_PK          = 2
CANCELED_PK         = 3
RESTARTED_PK        = 4
TERMINATED_PK       = 5

TASK_STATUS = {
                NOT_STARTED_PK:        _(u'Non commencée'),
                CURRENT_PK:            _(u'En cours'),
                CANCELED_PK:           _(u'Annulée'),
                RESTARTED_PK:          _(u'Redémarrée'),
                TERMINATED_PK:         _(u"Terminée"),
              }

REL_SUB_PROJECT_MANAGER = 'projects-subject_project_manager'
REL_OBJ_PROJECT_MANAGER = 'projects-object_project_manager'
