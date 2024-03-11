# from django.utils.translation import gettext_lazy as _
#
# NOT_STARTED_PK  = 1
# IN_PROGRESS_PK  = 2
# CANCELED_PK     = 3
# RESTARTED_PK    = 4
# COMPLETED_PK    = 5
#
# class TaskStatusDesc:
#     __slots__ = ('name', 'verbose_name')
#
#     def __init__(self, name, verbose_name):
#         self.name = name
#         self.verbose_name = verbose_name
#
# TASK_STATUS = {
#     NOT_STARTED_PK: TaskStatusDesc(_('Not started'), _('The task as not started yet')),
#     IN_PROGRESS_PK: TaskStatusDesc(_('In progress'), _('The task is in progress')),
#     CANCELED_PK:    TaskStatusDesc(_('Canceled'),    _('The task has been canceled')),
#     RESTARTED_PK:   TaskStatusDesc(_('Restarted'),   _('The task has been restarted')),
#     COMPLETED_PK:   TaskStatusDesc(_('Completed'),   _('The task is finished')),
# }
UUID_TSTATUS_NOT_STARTED  = '23cea775-dfed-44d4-82c0-809708618798'
UUID_TSTATUS_IN_PROGRESS  = 'c05da59c-4a58-49b3-99af-c922c796caa7'
UUID_TSTATUS_CANCELED     = '0a345a07-9790-4278-ab1a-e568b90efd0e'
UUID_TSTATUS_RESTARTED    = '35fbdfa6-d4ba-4f49-8e5f-60ccb6c4b8b2'
UUID_TSTATUS_COMPLETED    = '2f74b370-a381-44cb-8e01-5bfc3ab4a8da'

REL_SUB_PROJECT_MANAGER = 'projects-subject_project_manager'
REL_OBJ_PROJECT_MANAGER = 'projects-object_project_manager'

REL_SUB_LINKED_2_PTASK = 'projects-subject_linked_2_projecttask'
REL_OBJ_LINKED_2_PTASK = 'projects-object_linked_2_projecttask'

REL_SUB_PART_AS_RESOURCE = 'projects-subject_part_as_resource'
REL_OBJ_PART_AS_RESOURCE = 'projects-object_part_as_resource'

DEFAULT_HFILTER_PROJECT = 'projects-hf_project'
