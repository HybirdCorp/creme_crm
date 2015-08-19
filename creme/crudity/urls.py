# -*- coding: utf-8 -*-

from django.conf.urls import url

from .views import actions, history, infopath, email


urlpatterns = [
    url(r'^waiting_actions$',          actions.fetch),
    url(r'^waiting_actions/delete$',   actions.delete),
    url(r'^waiting_actions/validate$', actions.validate),

    url(r'^waiting_actions_blocks/block_crudity-(?P<ct_id>\d+)-(?P<backend_subject>\w+)/reload$', actions.reload),

    url(r'^history$',                                           history.history),
    url(r'^history_block/block_crudity-(?P<ct_id>\d+)/reload$', history.reload),

    url(r'^infopath/create_form/(?P<subject>\w+)$', infopath.create_form),

    url(r'^download_email_template/(?P<subject>\w+)$', email.download_email_template),
]
