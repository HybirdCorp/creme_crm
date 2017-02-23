# -*- coding: utf-8 -*-

from django.conf.urls import url

from .views import actions, history, infopath, email


urlpatterns = [
    url(r'^waiting_actions$',          actions.fetch,    name='crudity__actions'),
    url(r'^waiting_actions/delete$',   actions.delete,   name='crudity__delete_actions'),
    url(r'^waiting_actions/validate$', actions.validate, name='crudity__validate_actions'),

    url(r'^waiting_actions_blocks/block_crudity-(?P<ct_id>\d+)-(?P<backend_subject>\w+)/reload$',
        actions.reload, name='crudity__reload_actions_block',
       ),

    url(r'^history$',                                           history.history, name='crudity__history'),
    url(r'^history_block/block_crudity-(?P<ct_id>\d+)/reload$', history.reload,  name='crudity__reload_history_block'),

    url(r'^infopath/create_form/(?P<subject>\w+)$', infopath.create_form, name='crudity__dl_infopath_form'),
    url(r'^download_email_template/(?P<subject>\w+)$', email.download_email_template, name='crudity__dl_email_template'),
]
