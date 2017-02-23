# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.activities import activity_model_is_custom

from . import project_model_is_custom, task_model_is_custom
from .views import portal, project, task, resource


urlpatterns = [
    url(r'^$', portal.portal, name='projects__portal'),

    # TODO: Define what user could do or not if projet is 'close'
    #       (with the use of the button that sets an effective end date)
    # TODO: change url ?? project/close/(?P<project_id>\d+)
    url(r'^project/(?P<project_id>\d+)/close$',  project.close, name='projects__close_project'),

    url(r'^task/parent/delete$',               task.delete_parent, name='projects__remove_parent_task'),
    url(r'^task/(?P<task_id>\d+)/parent/add$', task.add_parent,    name='projects__add_parent_task'),

    # Task: Resource block
    url(r'^task/(?P<task_id>\d+)/resource/add$', resource.add,    name='projects__create_resource'),
    url(r'^resource/edit/(?P<resource_id>\d+)$', resource.edit,   name='projects__edit_resource'),
    url(r'^resource/delete$',                    resource.delete, name='projects__delete_resource'),

    # Task: related activities block
    url(r'^activity/delete$', task.delete_activity, name='projects__delete_activity'),
]

if not activity_model_is_custom():
    urlpatterns += [
        url(r'^task/(?P<task_id>\d+)/activity/add$', task.add_activity,  name='projects__create_activity'),
        url(r'^activity/edit/(?P<activity_id>\d+)$', task.edit_activity, name='projects__edit_activity'),
    ]

if not project_model_is_custom():
    urlpatterns += [
        url(r'^projects$',                         project.listview,   name='projects__list_projects'),
        url(r'^project/add$',                      project.add,        name='projects__create_project'),
        url(r'^project/edit/(?P<project_id>\d+)$', project.edit,       name='projects__edit_project'),
        url(r'^project/(?P<project_id>\d+)$',      project.detailview, name='projects__view_project'),
    ]

if not task_model_is_custom():
    urlpatterns += [
        url(r'^project/(?P<project_id>\d+)/task/add', task.add,         name='projects__create_task'),
        url(r'^task/edit/(?P<task_id>\d+)$',          task.edit,        name='projects__edit_task'),
        url(r'^task/edit/(?P<task_id>\d+)/popup$',    task.edit_popup,  name='projects__edit_task_popup'),  # TODO: Merge with edit ?
        url(r'^task/(?P<task_id>\d+)$',               task.detailview,  name='projects__view_task'  ),
    ]
