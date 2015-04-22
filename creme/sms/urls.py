# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import (smscampaign_model_is_custom, messaginglist_model_is_custom,
            messagetemplate_model_is_custom)


urlpatterns = patterns('creme.sms.views',
    (r'^$', 'portal.portal'),

    #Campaign: messaging_lists block
    (r'^campaign/(?P<campaign_id>\d+)/messaging_list/add$',    'campaign.add_messaging_list'),
    (r'^campaign/(?P<campaign_id>\d+)/messaging_list/delete$', 'campaign.delete_messaging_list'),

    #Campaign: sending block
    (r'^campaign/(?P<campaign_id>\d+)/sending/add$', 'sending.add'),
    (r'^campaign/sending/delete$',                   'sending.delete'),

    #Campaign: sending details block
    (r'^campaign/sending/(?P<id>\d+)$',                  'sending.detailview'),
    (r'^campaign/sending/message/delete$',               'sending.delete_message'),
    (r'^campaign/sending/(?P<id>\d+)/messages/sync/$',   'sending.sync_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/send/$',   'sending.send_messages'),
    (r'^campaign/sending/(?P<id>\d+)/messages/reload/$', 'sending.reload_block_messages'),

    #MessagingList list: recipients block
    (r'^messaging_list/(?P<mlist_id>\d+)/recipient/add$',     'recipient.add'),
    (r'^messaging_list/(?P<mlist_id>\d+)/recipient/add_csv$', 'recipient.add_from_csv'),

    #MessagingList list: contacts block
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/add$',             'messaging_list.add_contacts'),
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/add_from_filter$', 'messaging_list.add_contacts_from_filter'),
    (r'^messaging_list/(?P<mlist_id>\d+)/contact/delete',           'messaging_list.delete_contact'),
)

if not smscampaign_model_is_custom():
    urlpatterns += patterns('creme.sms.views.campaign',
        url(r'^campaigns$',                          'listview',   name='sms__list_campaigns'),
        url(r'^campaign/add$',                       'add',        name='sms__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', 'edit',       name='sms__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      'detailview', name='sms__view_campaign'),
    )

if not messaginglist_model_is_custom():
    urlpatterns += patterns('creme.sms.views.messaging_list',
        url(r'^messaging_lists$',                       'listview',   name='sms__list_mlists'),
        url(r'^messaging_list/add$',                    'add',        name='sms__create_mlist'),
        url(r'^messaging_list/edit/(?P<mlist_id>\d+)$', 'edit',       name='sms__edit_mlist'),
        url(r'^messaging_list/(?P<mlist_id>\d+)$',      'detailview', name='sms__view_mlist'),
    )

if not messagetemplate_model_is_custom():
    urlpatterns += patterns('creme.sms.views.template',
        url(r'^templates$',                          'listview',   name='sms__list_templates'),
        url(r'^template/add$',                       'add',        name='sms__create_template'),
        url(r'^template/edit/(?P<template_id>\d+)$', 'edit',       name='sms__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      'detailview', name='sms__view_template'),
    )
