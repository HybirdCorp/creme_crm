# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('crudity.views',
    (r'^email/waiting_actions$', 'email.fetch_emails'),

    (r'^waiting_actions/delete$',   'actions.delete'),
    (r'^waiting_actions/validate$', 'actions.validate'),
    (r'^waiting_actions_blocks/block_crudity-(?P<ct_id>\d+)-(?P<waiting_type>\d+)/reload$', 'actions.reload'),

    (r'^history$',                                                         'history.history'),
    (r'^history_block/block_crudity-(?P<ct_id>\d+)-(?P<type>\d+)/reload$', 'history.reload'),

    (r'^infopath/create_form/(?P<subject>\w+)$', 'infopath.create_form'),
)
