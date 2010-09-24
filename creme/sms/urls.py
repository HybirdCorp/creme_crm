# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('sms.views',
    (r'^$', 'portal.portal'),

    (r'^campaigns$',                          'campaign.listview'),
    (r'^campaign/add$',                       'campaign.add'),
    (r'^campaign/edit/(?P<campaign_id>\d+)$', 'campaign.edit'),
    (r'^campaign/(?P<campaign_id>\d+)$',      'campaign.detailview'),

    #Campaign: mailing_list block
    (r'^campaign/(?P<campaign_id>\d+)/messaging_list/add$',    'campaign.add_messaging_list'),
    (r'^campaign/(?P<campaign_id>\d+)/messaging_list/delete$', 'campaign.delete_messaging_list'),

    #Campaign: sending block
    (r'^campaign/(?P<campaign_id>\d+)/sending/add$', 'sending.add'),
    (r'^campaign/sending/delete$',                   'sending.delete'),

    #Campaign: sending details block
    (r'^campaign/sending/(?P<id>\d+)$',                  'sending.detailview'),
    #(r'^campaign/sending/message/delete/(?P<id>\w+)$',   'sending.delete_message'),
    (r'^campaign/sending/message/delete$',               'sending.delete_message'),
    (r'^campaign/sending/(?P<id>\d+)/messages/sync/$',   'sending.sync_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/send/$',   'sending.send_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/reload/$', 'sending.reload_block_messages'),

    (r'^messaging_lists$',                       'messaging_list.listview'),
    (r'^messaging_list/add$',                    'messaging_list.add'),
    (r'^messaging_list/edit/(?P<mlist_id>\d+)$', 'messaging_list.edit'),
    (r'^messaging_list/(?P<mlist_id>\d+)$',      'messaging_list.detailview'),

    #Mailing list: recipients block
    (r'^messaging_list/(?P<mlist_id>\d+)/recipient/add$',     'recipient.add'),
    (r'^messaging_list/(?P<mlist_id>\d+)/recipient/add_csv$', 'recipient.add_from_csv'),
    (r'^messaging_list/recipient/delete$',                    'recipient.delete'),

    #Mailing list: contacts block
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/add$',             'messaging_list.add_contacts'),
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/add_from_filter$', 'messaging_list.add_contacts_from_filter'),
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/delete',           'messaging_list.delete_contact'),

    (r'^templates$',                          'template.listview'),
    (r'^template/add$',                       'template.add'),
    (r'^template/edit/(?P<template_id>\d+)$', 'template.edit'),
    (r'^template/(?P<template_id>\d+)$',      'template.detailview'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^campaign/delete/(?P<object_id>\d+)$',       'delete_entity'),
    (r'^messaging_list/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^template/delete/(?P<object_id>\d+)$',       'delete_entity'),
)
