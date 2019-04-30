# -*- coding: utf-8 -*-

from django.utils.translation import gettext_lazy as _

NOT_STARTED_PK  = 1
IN_PROGRESS_PK  = 2
CANCELED_PK     = 3
RESTARTED_PK    = 4
COMPLETED_PK    = 5


class TaskStatusDesc:
    __slots__ = ('name', 'verbose_name')

    def __init__(self, name, verbose_name):
        self.name = name
        self.verbose_name = verbose_name


TASK_STATUS = {
    NOT_STARTED_PK: TaskStatusDesc(_('Not started'), _('The task as not started yet')),
    IN_PROGRESS_PK: TaskStatusDesc(_('In progress'), _('The task is in progress')),
    CANCELED_PK:    TaskStatusDesc(_('Canceled'),    _('The task has been canceled')),
    RESTARTED_PK:   TaskStatusDesc(_('Restarted'),   _('The task has been restarted')),
    COMPLETED_PK:   TaskStatusDesc(_('Completed'),   _('The task is finished')),
}

REL_SUB_PROJECT_MANAGER = 'projects-subject_project_manager'
REL_OBJ_PROJECT_MANAGER = 'projects-object_project_manager'

REL_SUB_LINKED_2_PTASK = 'projects-subject_linked_2_projecttask'
REL_OBJ_LINKED_2_PTASK = 'projects-object_linked_2_projecttask'

REL_SUB_PART_AS_RESOURCE = 'projects-subject_part_as_resource'
REL_OBJ_PART_AS_RESOURCE = 'projects-object_part_as_resource'

DEFAULT_HFILTER_PROJECT = 'projects-hf_project'
