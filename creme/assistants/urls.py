# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('creme.assistants.views',
    (r'^memo/add/(?P<entity_id>\d+)/$', 'memo.add'),
    (r'^memo/edit/(?P<memo_id>\d+)/$',  'memo.edit'),

    (r'^alert/add/(?P<entity_id>\d+)/$',     'alert.add'),
    (r'^alert/edit/(?P<alert_id>\d+)/$',     'alert.edit'),
    (r'^alert/validate/(?P<alert_id>\d+)/$', 'alert.validate'),

    (r'^todo/add/(?P<entity_id>\d+)/$',    'todo.add'),
    (r'^todo/edit/(?P<todo_id>\d+)/$',     'todo.edit'),
    (r'^todo/validate/(?P<todo_id>\d+)/$', 'todo.validate'),

    (r'^action/add/(?P<entity_id>\d+)/$',      'action.add'),
    (r'^action/edit/(?P<action_id>\d+)/$',     'action.edit'),
    (r'^action/validate/(?P<action_id>\d+)/$', 'action.validate'),

    (r'^message/add/$',                    'user_message.add'),
    (r'^message/add/(?P<entity_id>\d+)/$', 'user_message.add_to_entity'),
    (r'^message/delete$',                  'user_message.delete'),
)
