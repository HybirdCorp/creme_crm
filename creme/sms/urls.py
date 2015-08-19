# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import (smscampaign_model_is_custom, messaginglist_model_is_custom,
        messagetemplate_model_is_custom)
from .views import portal, campaign, sending, recipient, messaging_list


urlpatterns = [
    url(r'^$', portal.portal),

    #Campaign: messaging_lists block
    url(r'^campaign/(?P<campaign_id>\d+)/messaging_list/add$',    campaign.add_messaging_list),
    url(r'^campaign/(?P<campaign_id>\d+)/messaging_list/delete$', campaign.delete_messaging_list),

    #Campaign: sending block
    url(r'^campaign/(?P<campaign_id>\d+)/sending/add$', sending.add),
    url(r'^campaign/sending/delete$',                   sending.delete),

    #Campaign: sending details block
    url(r'^campaign/sending/(?P<id>\d+)$',                  sending.detailview),
    url(r'^campaign/sending/message/delete$',               sending.delete_message),
    url(r'^campaign/sending/(?P<id>\d+)/messages/sync/$',   sending.sync_messages),
    url(r'^campaign/sending/(?P<id>\d+)/messages/send/$',   sending.send_messages),
    url(r'^campaign/sending/(?P<id>\d+)/messages/reload/$', sending.reload_block_messages),

    #MessagingList list: recipients block
    url(r'^messaging_list/(?P<mlist_id>\d+)/recipient/add$',     recipient.add),
    url(r'^messaging_list/(?P<mlist_id>\d+)/recipient/add_csv$', recipient.add_from_csv),

    #MessagingList list: contacts block
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/add$',             messaging_list.add_contacts),
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/add_from_filter$', messaging_list.add_contacts_from_filter),
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/delete',           messaging_list.delete_contact),
]

if not smscampaign_model_is_custom():
    urlpatterns += [
        url(r'^campaigns$',                          campaign.listview,   name='sms__list_campaigns'),
        url(r'^campaign/add$',                       campaign.add,        name='sms__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', campaign.edit,       name='sms__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      campaign.detailview, name='sms__view_campaign'),
    ]

if not messaginglist_model_is_custom():
    urlpatterns += [
        url(r'^messaging_lists$',                       messaging_list.listview,   name='sms__list_mlists'),
        url(r'^messaging_list/add$',                    messaging_list.add,        name='sms__create_mlist'),
        url(r'^messaging_list/edit/(?P<mlist_id>\d+)$', messaging_list.edit,       name='sms__edit_mlist'),
        url(r'^messaging_list/(?P<mlist_id>\d+)$',      messaging_list.detailview, name='sms__view_mlist'),
    ]

if not messagetemplate_model_is_custom():
    from .views import template

    urlpatterns += [
        url(r'^templates$',                          template.listview,   name='sms__list_templates'),
        url(r'^template/add$',                       template.add,        name='sms__create_template'),
        url(r'^template/edit/(?P<template_id>\d+)$', template.edit,       name='sms__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      template.detailview, name='sms__view_template'),
    ]
