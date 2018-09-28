# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from .views import memo, alert, todo, action, user_message


urlpatterns = [
    url(r'^memo/', include([
        # url(r'^add/(?P<entity_id>\d+)[/]?$', memo.add,  name='assistants__create_memo'),
        url(r'^add/(?P<entity_id>\d+)[/]?$', memo.MemoCreation.as_view(), name='assistants__create_memo'),
        # url(r'^edit/(?P<memo_id>\d+)[/]?$',  memo.edit, name='assistants__edit_memo'),
        url(r'^edit/(?P<memo_id>\d+)[/]?$',  memo.MemoEdition.as_view(),  name='assistants__edit_memo'),
    ])),
    url(r'^alert/', include([
        # url(r'^add/(?P<entity_id>\d+)[/]?$',     alert.add,      name='assistants__create_alert'),
        url(r'^add/(?P<entity_id>\d+)[/]?$',     alert.AlertCreation.as_view(), name='assistants__create_alert'),
        # url(r'^edit/(?P<alert_id>\d+)[/]?$',     alert.edit,     name='assistants__edit_alert'),
        url(r'^edit/(?P<alert_id>\d+)[/]?$',     alert.AlertEdition.as_view(),  name='assistants__edit_alert'),
        url(r'^validate/(?P<alert_id>\d+)[/]?$', alert.validate,                name='assistants__validate_alert'),
    ])),
    url(r'^todo/', include([
        # url(r'^add/(?P<entity_id>\d+)[/]?$',    todo.add,      name='assistants__create_todo'),
        url(r'^add/(?P<entity_id>\d+)[/]?$',    todo.ToDoCreation.as_view(), name='assistants__create_todo'),
        # url(r'^edit/(?P<todo_id>\d+)[/]?$',     todo.edit,     name='assistants__edit_todo'),
        url(r'^edit/(?P<todo_id>\d+)[/]?$',     todo.ToDoEdition.as_view(),  name='assistants__edit_todo'),
        url(r'^validate/(?P<todo_id>\d+)[/]?$', todo.validate,               name='assistants__validate_todo'),
    ])),
    url(r'^action/', include([
        # url(r'^add/(?P<entity_id>\d+)[/]?$',      action.add,      name='assistants__create_action'),
        url(r'^add/(?P<entity_id>\d+)[/]?$',      action.ActionCreation.as_view(), name='assistants__create_action'),
        # url(r'^edit/(?P<action_id>\d+)[/]?$',     action.edit,     name='assistants__edit_action'),
        url(r'^edit/(?P<action_id>\d+)[/]?$',     action.ActionEdition.as_view(),  name='assistants__edit_action'),
        url(r'^validate/(?P<action_id>\d+)[/]?$', action.validate,                 name='assistants__validate_action'),
    ])),
    url(r'^message/', include([
        url(r'^add[/]?$',                    user_message.add,           name='assistants__create_message'),
        # url(r'^add/(?P<entity_id>\d+)[/]?$', user_message.add_to_entity, name='assistants__create_related_message'),
        url(r'^add/(?P<entity_id>\d+)[/]?$', user_message.RelatedUserMessageCreation.as_view(), name='assistants__create_related_message'),
        url(r'^delete[/]?$',                 user_message.delete,        name='assistants__delete_message'),
    ])),
]
