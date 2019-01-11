# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import sms
from .views import campaign, sending, recipient, messaging_list, template


urlpatterns = [
    # Campaign: messaging_lists brick
    url(r'^campaign/(?P<campaign_id>\d+)/messaging_list/add[/]?$',    campaign.MessagingListsAdding.as_view(), name='sms__add_mlists_to_campaign'),
    url(r'^campaign/(?P<campaign_id>\d+)/messaging_list/delete[/]?$', campaign.delete_messaging_list, name='sms__remove_mlist_from_campaign'),

    # Campaign: sending brick
    url(r'^campaign/(?P<campaign_id>\d+)/sending/add[/]?$', sending.SendingCreation.as_view(), name='sms__create_sending'),
    url(r'^campaign/sending/delete[/]?$',                   sending.delete,                    name='sms__delete_sending'),

    # Campaign: sending details brick
    url(r'^campaign/sending/(?P<id>\d+)[/]?$',                 sending.Messages.as_view(),    name='sms__view_sending'),
    url(r'^campaign/sending/message/delete[/]?$',              sending.delete_message,        name='sms__delete_message'),
    url(r'^campaign/sending/(?P<id>\d+)/messages/sync[/]?$',   sending.sync_messages,         name='sms__sync_messages'),
    url(r'^campaign/sending/(?P<id>\d+)/messages/send[/]?$',   sending.send_messages,         name='sms__send_messages'),
    url(r'^campaign/sending/(?P<id>\d+)/messages/reload[/]?$', sending.reload_messages_brick, name='sms__reload_messages_brick'),

    # MessagingList list: recipients brick
    url(r'^messaging_list/(?P<mlist_id>\d+)/recipient/add[/]?$',     recipient.RecipientsAdding.as_view(),        name='sms__add_recipients'),
    url(r'^messaging_list/(?P<mlist_id>\d+)/recipient/add_csv[/]?$', recipient.RecipientsAddingFromCSV.as_view(), name='sms__add_recipients_from_csv'),

    # MessagingList list: contacts brick
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/add[/]?$',             messaging_list.ContactsAdding.as_view(),           name='sms__add_contacts_to_mlist'),
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/add_from_filter[/]?$', messaging_list.ContactsAddingFromFilter.as_view(), name='sms__add_contacts_to_mlist_from_filter'),
    url(r'^messaging_list/(?P<mlist_id>\d+)/contact/delete[/]?',           messaging_list.delete_contact,           name='sms__remove_contact_from_mlist'),
]

urlpatterns += swap_manager.add_group(
    sms.smscampaign_model_is_custom,
    Swappable(url(r'^campaigns[/]?$',                          campaign.listview,                      name='sms__list_campaigns')),
    Swappable(url(r'^campaign/add[/]?$',                       campaign.SMSCampaignCreation.as_view(), name='sms__create_campaign')),
    Swappable(url(r'^campaign/edit/(?P<campaign_id>\d+)[/]?$', campaign.SMSCampaignEdition.as_view(),  name='sms__edit_campaign'), check_args=Swappable.INT_ID),
    Swappable(url(r'^campaign/(?P<campaign_id>\d+)[/]?$',      campaign.SMSCampaignDetail.as_view(),   name='sms__view_campaign'), check_args=Swappable.INT_ID),
    app_name='sms',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    sms.messaginglist_model_is_custom,
    Swappable(url(r'^messaging_lists[/]?$',                       messaging_list.listview,                        name='sms__list_mlists')),
    Swappable(url(r'^messaging_list/add[/]?$',                    messaging_list.MessagingListCreation.as_view(), name='sms__create_mlist')),
    Swappable(url(r'^messaging_list/edit/(?P<mlist_id>\d+)[/]?$', messaging_list.MessagingListEdition.as_view(),  name='sms__edit_mlist'), check_args=Swappable.INT_ID),
    Swappable(url(r'^messaging_list/(?P<mlist_id>\d+)[/]?$',      messaging_list.MessagingListDetail.as_view(),   name='sms__view_mlist'), check_args=Swappable.INT_ID),
    app_name='sms',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    sms.messagetemplate_model_is_custom,
    Swappable(url(r'^templates[/]?$',                          template.listview,                          name='sms__list_templates')),
    Swappable(url(r'^template/add[/]?$',                       template.MessageTemplateCreation.as_view(), name='sms__create_template')),
    Swappable(url(r'^template/edit/(?P<template_id>\d+)[/]?$', template.MessageTemplateEdition.as_view(),  name='sms__edit_template'), check_args=Swappable.INT_ID),
    Swappable(url(r'^template/(?P<template_id>\d+)[/]?$',      template.MessageTemplateDetail.as_view(),   name='sms__view_template'), check_args=Swappable.INT_ID),
    app_name='sms',
).kept_patterns()
