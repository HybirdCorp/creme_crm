# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('creme.assistants.views',
    (r'^memo/add/(?P<entity_id>\d+)/$',            'memo.add'),
    (r'^memo/edit/(?P<memo_id>\d+)/$',             'memo.edit'),
    (r'^memo/delete$',                             'memo.delete'),

    (r'^alert/add/(?P<entity_id>\d+)/$',            'alert.add'),
    (r'^alert/edit/(?P<alert_id>\d+)/$',            'alert.edit'),
    (r'^alert/delete$',                             'alert.delete'),
    (r'^alert/validate/(?P<alert_id>\d{1,20})/$',   'alert.validate'),

    (r'^todo/add/(?P<entity_id>\d+)/$',            'todo.add'),
    (r'^todo/edit/(?P<todo_id>\d+)/$',             'todo.edit'),
    (r'^todo/delete$',                             'todo.delete'),
    (r'^todo/validate/(?P<todo_id>\d+)/$',         'todo.validate'),

    (r'^action/add/(?P<entity_id>\d+)/$',            'action.add'),
    (r'^action/edit/(?P<action_id>\d+)/$',           'action.edit'),
    (r'^action/delete$',                             'action.delete'),
    (r'^action/validate/(?P<action_id>\d+)/$',       'action.validate'),
)
