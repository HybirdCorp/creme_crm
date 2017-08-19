import warnings

from .bricks import (
    ProjectExtraInfoBrick as ProjectExtraInfo,
    TaskExtraInfoBrick as TaskExtraInfo,
    ParentTasksBrick as ParentTasksBlock,
    ProjectTasksBrick as ProjectTasksBlock,
    TaskResourcesBrick as TaskResourcesBlock,
    TaskActivitiesBrick as TaskActivitiesBlock,
)

warnings.warn('projects.blocks is deprecated ; use projects.bricks instead.', DeprecationWarning)

project_extra_info    = ProjectExtraInfo()
task_extra_info       = TaskExtraInfo()
project_tasks_block   = ProjectTasksBlock()
task_resources_block  = TaskResourcesBlock()
task_activities_block = TaskActivitiesBlock()
parent_tasks_block    = ParentTasksBlock()

block_list = (
    project_extra_info,
    task_extra_info,
    project_tasks_block,
    task_resources_block,
    task_activities_block,
    parent_tasks_block,
)
