from django.urls import re_path

from creme.activities import activity_model_is_custom
from creme.creme_core.conf.urls import Swappable, swap_manager

from . import project_model_is_custom, task_model_is_custom
from .views import project, resource, task

urlpatterns = [
    # TODO: Define what user could do or not if project is 'close'
    #       (with the use of the button that sets an effective end date)
    # TODO: change url ?? project/close/(?P<project_id>\d+) ? 'id' as POST argument ?
    re_path(
        r'^project/(?P<project_id>\d+)/close[/]?$',
        project.ProjectClosure.as_view(),
        name='projects__close_project',
    ),

    re_path(
        r'^task/parent/delete[/]?$',
        task.ParentRemoving.as_view(),
        name='projects__remove_parent_task',
    ),
    re_path(
        r'^task/(?P<task_id>\d+)/parent/add[/]?$',
        task.ParentsAdding.as_view(),
        name='projects__add_parent_task',
    ),

    # Task: Resource brick
    re_path(
        r'^task/(?P<task_id>\d+)/resource/add[/]?$',
        resource.ResourceCreation.as_view(),
        name='projects__create_resource',
    ),
    re_path(
        r'^resource/edit/(?P<resource_id>\d+)[/]?$',
        resource.ResourceEdition.as_view(),
        name='projects__edit_resource',
    ),
    re_path(
        r'^resource/delete[/]?$',
        resource.ResourceDeletion.as_view(),
        name='projects__delete_resource',
    ),

    # Task: related activities brick
    re_path(
        r'^activity/delete[/]?$',
        task.ActivityDeletion.as_view(),
        name='projects__delete_activity',
    ),

    *swap_manager.add_group(
        activity_model_is_custom,
        Swappable(
            re_path(
                r'^task/(?P<task_id>\d+)/activity/add[/]?$',
                task.RelatedActivityCreation.as_view(),
                name='projects__create_activity',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^activity/edit/(?P<activity_id>\d+)[/]?$',
                task.ActivityEditionPopup.as_view(),
                name='projects__edit_activity',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='projects',
    ).kept_patterns(),

    *swap_manager.add_group(
        project_model_is_custom,
        Swappable(
            re_path(
                r'^projects[/]?$',
                project.ProjectsList.as_view(),
                name='projects__list_projects',
            ),
        ),
        Swappable(
            re_path(
                r'^project/add[/]?$',
                project.ProjectCreation.as_view(),
                name='projects__create_project',
            ),
        ),
        Swappable(
            re_path(
                r'^project/edit/(?P<project_id>\d+)[/]?$',
                project.ProjectEdition.as_view(),
                name='projects__edit_project',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^project/(?P<project_id>\d+)[/]?$',
                project.ProjectDetail.as_view(),
                name='projects__view_project',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='projects',
    ).kept_patterns(),

    *swap_manager.add_group(
        task_model_is_custom,
        Swappable(
            re_path(
                r'^project/(?P<project_id>\d+)/task/add[/]?$',
                task.TaskCreation.as_view(),
                name='projects__create_task',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^task/edit/(?P<task_id>\d+)[/]?$',
                task.TaskEdition.as_view(),
                name='projects__edit_task',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^task/edit/(?P<task_id>\d+)/popup[/]?$',
                task.TaskEditionPopup.as_view(),
                name='projects__edit_task_popup',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^task/(?P<task_id>\d+)[/]?$',
                task.TaskDetail.as_view(),
                name='projects__view_task',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='projects',
    ).kept_patterns(),
]
