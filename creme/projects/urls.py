# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.activities import activity_model_is_custom

from . import project_model_is_custom, task_model_is_custom
from .views import portal, project, task, resource


urlpatterns = [
    url(r'^$', portal.portal),

    # TODO : Define what user could do or not if projet is 'close' (with the use of the buttom that sets an effective end date)
    url(r'^project/(?P<project_id>\d+)/close$',  project.close), #TODO: change url ?? project/close/(?P<project_id>\d+)

    url(r'^task/parent/delete$',               task.delete_parent),
    url(r'^task/(?P<task_id>\d+)/parent/add$', task.add_parent),

    #Task: Resource block
    url(r'^task/(?P<task_id>\d+)/resource/add$', resource.add),
    url(r'^resource/edit/(?P<resource_id>\d+)$', resource.edit),
    url(r'^resource/delete$',                    resource.delete),

    #Task: Working periods block
#    (r'^task/(?P<task_id>\d+)/period/add$', 'workingperiod.add'),
#    (r'^period/edit/(?P<period_id>\d+)$',   'workingperiod.edit'),
#    (r'^period/delete$',                    'workingperiod.delete'),
    url(r'^activity/delete$', task.delete_activity),
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
#        (r'^task/delete$',                         'delete'),
#        (r'^task/(?P<object_id>\d+)$',             'detailview'),
        url(r'^task/edit/(?P<task_id>\d+)$',          task.edit,        name='projects__edit_task'),
        url(r'^task/edit/(?P<task_id>\d+)/popup$',    task.edit_popup,  name='projects__edit_task_popup'),#TODO: Merge with edit ?
        url(r'^task/(?P<task_id>\d+)$',               task.detailview,  name='projects__view_task'  ),
    ]
