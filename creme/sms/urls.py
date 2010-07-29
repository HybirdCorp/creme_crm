# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('sms.views',
    (r'^$', 'portal.portal'),

    (r'^campaigns$',                 'campaign.listview'),
    (r'^campaign/add$',              'campaign.add'),
    (r'^campaign/edit/(?P<id>\d+)$', 'campaign.edit'),
    (r'^campaign/(?P<id>\d+)$',      'campaign.detailview'),

    #Campaign: mailing_list block
    (r'^campaign/(?P<id>\d+)/sendlist/add$',             'campaign.add_sendlist'),
    (r'^campaign/(?P<campaign_id>\d+)/sendlist/delete$', 'campaign.delete_sendlist'),

    #Campaign: sending block
    (r'^campaign/(?P<id>\d+)/sending/add$',      'sending.add'),
    #(r'^campaign/sending/delete/(?P<id>\d+)$',   'sending.delete'),
    (r'^campaign/sending/delete$',               'sending.delete'),

    #Campaign: sending details block
    (r'^campaign/sending/(?P<id>\d+)$',                  'sending.detailview'),
    #(r'^campaign/sending/message/delete/(?P<id>\w+)$',   'sending.delete_message'),
    (r'^campaign/sending/message/delete$',               'sending.delete_message'),
    (r'^campaign/sending/(?P<id>\d+)/messages/sync/$',   'sending.sync_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/send/$',   'sending.send_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/reload/$', 'sending.reload_block_messages'),

    (r'^sendlists$',                 'sendlist.listview'),
    (r'^sendlist/add$',              'sendlist.add'),
    (r'^sendlist/edit/(?P<id>\d+)$', 'sendlist.edit'),
    (r'^sendlist/(?P<id>\d+)$',      'sendlist.detailview'),

    #Mailing list: recipients block
    (r'^sendlist/(?P<id>\d+)/recipient/add$',     'recipient.add'),
    (r'^sendlist/(?P<id>\d+)/recipient/add_csv$', 'recipient.add_from_csv'),
    (r'^sendlist/recipient/delete$',              'recipient.delete'),

    #Mailing list: contacts block
    (r'^sendlist/(?P<id>\d+)/contact/add$',             'sendlist.add_contacts'),
    (r'^sendlist/(?P<id>\d+)/contact/add_from_filter$', 'sendlist.add_contacts_from_filter'),
    (r'^sendlist/(?P<sendlist_id>\d+)/contact/delete',  'sendlist.delete_contact'),

    (r'^templates$',                          'template.listview'),
    (r'^template/add$',                       'template.add'),
    (r'^template/edit/(?P<template_id>\d+)$', 'template.edit'),
    (r'^template/(?P<template_id>\d+)$',      'template.detailview'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^campaign/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^sendlist/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^template/delete/(?P<object_id>\d+)$', 'delete_entity'),
)
