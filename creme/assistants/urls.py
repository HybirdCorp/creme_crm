# -*- coding: utf-8 -*-

from django.conf.urls import url

from .views import memo, alert, todo, action, user_message


urlpatterns = [
    url(r'^memo/add/(?P<entity_id>\d+)/$', memo.add),
    url(r'^memo/edit/(?P<memo_id>\d+)/$',  memo.edit),

    url(r'^alert/add/(?P<entity_id>\d+)/$',     alert.add),
    url(r'^alert/edit/(?P<alert_id>\d+)/$',     alert.edit),
    url(r'^alert/validate/(?P<alert_id>\d+)/$', alert.validate),

    url(r'^todo/add/(?P<entity_id>\d+)/$',    todo.add),
    url(r'^todo/edit/(?P<todo_id>\d+)/$',     todo.edit),
    url(r'^todo/validate/(?P<todo_id>\d+)/$', todo.validate),

    url(r'^action/add/(?P<entity_id>\d+)/$',      action.add),
    url(r'^action/edit/(?P<action_id>\d+)/$',     action.edit),
    url(r'^action/validate/(?P<action_id>\d+)/$', action.validate),

    url(r'^message/add/$',                    user_message.add),
    url(r'^message/add/(?P<entity_id>\d+)/$', user_message.add_to_entity),
    url(r'^message/delete$',                  user_message.delete),
]
