# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.crudity.views',
    (r'^waiting_actions$',          'actions.fetch'),
    (r'^waiting_actions/delete$',   'actions.delete'),
    (r'^waiting_actions/validate$', 'actions.validate'),

    (r'^waiting_actions_blocks/block_crudity-(?P<ct_id>\d+)-(?P<backend_subject>\w+)/reload$', 'actions.reload'),

    (r'^history$',                                           'history.history'),
    (r'^history_block/block_crudity-(?P<ct_id>\d+)/reload$', 'history.reload'),

    (r'^infopath/create_form/(?P<subject>\w+)$', 'infopath.create_form'),

    (r'^download_email_template/(?P<subject>\w+)$', 'email.download_email_template'),
)
