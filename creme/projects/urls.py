# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('projects.views',
    (r'^$', 'portal.portal'),

    # TODO : Define what user could do or not if projet is 'close' (with the use of the buttom that sets an effective end date)
    #Project : button for effective end date of project
    (r'^projects$',                           'project.listview'),
    (r'^project/add$',                        'project.add'),
    (r'^project/edit/(?P<project_id>\d+)$',   'project.edit'),
    (r'^project/(?P<project_id>\d+)$',        'project.detailview'),
    (r'^project/(?P<project_id>\d+)/close$',  'project.close'), #TODO: change url ?? project/close/(?P<project_id>\d+)

    #Project: Task block
    (r'^project/(?P<project_id>\d+)/task/add', 'task.add'),
    (r'^task/delete/(?P<task_id>\d+)$',        'task.delete'),#Keeps detailview delete compatibility
    (r'^task/delete$',                         'task.delete'),
    (r'^task/(?P<object_id>\d+)$',             'task.detailview'),
    (r'^task/edit/(?P<task_id>\d+)$',          'task.edit'),
    (r'^task/parent/delete$',                  'task.delete_parent'),

    #Task: Resource block
    (r'^task/(?P<task_id>\d+)/resource/add$',  'resource.add'),
    (r'^resource/edit/(?P<resource_id>\d+)$',  'resource.edit'),
    (r'^resource/delete$',                     'resource.delete'),

    #Task: Working periods block
    (r'^task/(?P<task_id>\d+)/period/add$', 'workingperiod.add'),
    (r'^period/edit/(?P<period_id>\d+)$',   'workingperiod.edit'),
    (r'^period/delete$',                    'workingperiod.delete'),
)

urlpatterns += patterns('creme_core.views',
    (r'^project/edit_js/$',                  'ajax.edit_js'),
    (r'^project/delete/(?P<object_id>\d+)$', 'generic.delete_entity', {'callback_url': '/projects/projects'}),
)
