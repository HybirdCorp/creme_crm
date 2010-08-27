# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _

NOT_STARTED_PK      = 1
IN_PROGRESS_PK      = 2
CANCELED_PK         = 3
RESTARTED_PK        = 4
COMPLETED_PK        = 5


class TaskStatusDesc(object):
    __slots__ = ('name', 'verbose_name')

    def __init__(self, name, verbose_name):
        self.name = name
        self.verbose_name = verbose_name


TASK_STATUS = {
                NOT_STARTED_PK: TaskStatusDesc(_(u'Not started'), _(u"The task as not started yet")),
                IN_PROGRESS_PK: TaskStatusDesc(_(u'In progress'), _(u"The task is in progress")),
                CANCELED_PK:    TaskStatusDesc(_(u'Canceled'),    _(u"The task has been canceled")),
                RESTARTED_PK:   TaskStatusDesc(_(u'Restarted'),   _(u"The task has been restarted")),
                COMPLETED_PK:   TaskStatusDesc(_(u"Completed"),   _(u"The task is finished")),
              }

REL_SUB_PROJECT_MANAGER = 'projects-subject_project_manager'
REL_OBJ_PROJECT_MANAGER = 'projects-object_project_manager'
