# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('creme.assistants.views',
    (r'^memo/add/(?P<entity_id>\d+)/$',            'memo.add'),
    (r'^memo/edit/(?P<memo_id>\d+)/$',             'memo.edit'),
    (r'^memo/delete$',                             'memo.delete'),
    (r'^memos/reload/(?P<entity_id>\d+)/$',        'memo.reload_detailview'),
    (r'^memos/reload/home/$',                      'memo.reload_home'),
    (r'^memos/reload/portal/(?P<ct_ids>[\d,]+)/$', 'memo.reload_portal'),

    (r'^alert/add/(?P<entity_id>\d+)/$',            'alert.add'),
    (r'^alert/edit/(?P<alert_id>\d+)/$',            'alert.edit'),
    (r'^alert/delete$',                             'alert.delete'),
    (r'^alert/validate/(?P<alert_id>\d{1,20})/$',   'alert.validate'),
    (r'^alerts/reload/(?P<entity_id>\d+)/$',        'alert.reload_detailview'),
    (r'^alerts/reload/home/$',                      'alert.reload_home'),
    (r'^alerts/reload/portal/(?P<ct_ids>[\d,]+)/$', 'alert.reload_portal'),

    (r'^todo/add/(?P<entity_id>\d+)/$',            'todo.add'),
    (r'^todo/edit/(?P<todo_id>\d+)/$',             'todo.edit'),
    (r'^todo/delete$',                             'todo.delete'),
    (r'^todo/validate/(?P<todo_id>\d+)/$',         'todo.validate'),
    (r'^todos/reload/(?P<entity_id>\d+)/$',        'todo.reload_detailview'),
    (r'^todos/reload/home/$',                      'todo.reload_home'),
    (r'^todos/reload/portal/(?P<ct_ids>[\d,]+)/$', 'todo.reload_portal'),

    (r'^action/add/(?P<entity_id>\d+)/$',            'action.add'),
    (r'^action/edit/(?P<action_id>\d+)/$',           'action.edit'),
    (r'^action/delete$',                             'action.delete'),
    (r'^action/validate/(?P<action_id>\d+)/$',       'action.validate'),
    (r'^actions/reload/(?P<entity_id>\d+)/$',        'action.reload_detailview'),
    (r'^actions/reload/home/$',                      'action.reload_home'),
    (r'^actions/reload/portal/(?P<ct_ids>[\d,]+)/$', 'action.reload_portal'),
)
