from django.urls import re_path

from creme import sms
from creme.creme_core.conf.urls import Swappable, swap_manager

from .views import campaign, messaging_list, recipient, sending, template

urlpatterns = [
    # Campaign: messaging_lists brick
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/messaging_list/add[/]?$',
        campaign.MessagingListsAdding.as_view(),
        name='sms__add_mlists_to_campaign',
    ),
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/messaging_list/delete[/]?$',
        campaign.MessagingListRemoving.as_view(),
        name='sms__remove_mlist_from_campaign',
    ),

    # Campaign: sending brick
    re_path(
        r'^campaign/(?P<campaign_id>\d+)/sending/add[/]?$',
        sending.SendingCreation.as_view(),
        name='sms__create_sending',
    ),
    re_path(
        r'^campaign/sending/delete[/]?$',
        sending.delete,
        name='sms__delete_sending',
    ),

    # Campaign: sending details brick
    re_path(
        r'^campaign/sending/(?P<id>\d+)[/]?$',
        sending.Messages.as_view(),
        name='sms__view_sending',
    ),
    re_path(
        r'^campaign/sending/message/delete[/]?$',
        sending.delete_message,
        name='sms__delete_message',
    ),
    re_path(
        r'^campaign/sending/(?P<id>\d+)/messages/sync[/]?$',
        sending.sync_messages,
        name='sms__sync_messages',
    ),
    re_path(
        r'^campaign/sending/(?P<id>\d+)/messages/send[/]?$',
        sending.send_messages,
        name='sms__send_messages',
    ),
    re_path(
        r'^campaign/sending/(?P<sending_id>\d+)/messages/reload[/]?$',
        sending.MessagesBrickReloading.as_view(),
        name='sms__reload_messages_brick',
    ),

    # MessagingList list: recipients brick
    re_path(
        r'^messaging_list/(?P<mlist_id>\d+)/recipient/add[/]?$',
        recipient.RecipientsAdding.as_view(),
        name='sms__add_recipients',
    ),
    re_path(
        r'^messaging_list/(?P<mlist_id>\d+)/recipient/add_csv[/]?$',
        recipient.RecipientsAddingFromCSV.as_view(),
        name='sms__add_recipients_from_csv',
    ),

    # MessagingList list: contacts brick
    re_path(
        r'^messaging_list/(?P<mlist_id>\d+)/contact/add[/]?$',
        messaging_list.ContactsAdding.as_view(),
        name='sms__add_contacts_to_mlist',
    ),
    re_path(
        r'^messaging_list/(?P<mlist_id>\d+)/contact/add_from_filter[/]?$',
        messaging_list.ContactsAddingFromFilter.as_view(),
        name='sms__add_contacts_to_mlist_from_filter'
    ),
    re_path(
        r'^messaging_list/(?P<mlist_id>\d+)/contact/delete[/]?',
        messaging_list.ContactRemoving.as_view(),
        name='sms__remove_contact_from_mlist'
    ),

    *swap_manager.add_group(
        sms.smscampaign_model_is_custom,
        Swappable(
            re_path(
                r'^campaigns[/]?$',
                campaign.SMSCampaignsList.as_view(),
                name='sms__list_campaigns',
            )
        ),
        Swappable(
            re_path(
                r'^campaign/add[/]?$',
                campaign.SMSCampaignCreation.as_view(),
                name='sms__create_campaign',
            )
        ),
        Swappable(
            re_path(
                r'^campaign/edit/(?P<campaign_id>\d+)[/]?$',
                campaign.SMSCampaignEdition.as_view(),
                name='sms__edit_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^campaign/(?P<campaign_id>\d+)[/]?$',
                campaign.SMSCampaignDetail.as_view(),
                name='sms__view_campaign',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='sms',
    ).kept_patterns(),

    *swap_manager.add_group(
        sms.messaginglist_model_is_custom,
        Swappable(
            re_path(
                r'^messaging_lists[/]?$',
                messaging_list.MessagingListsList.as_view(),
                name='sms__list_mlists',
            ),
        ),
        Swappable(
            re_path(
                r'^messaging_list/add[/]?$',
                messaging_list.MessagingListCreation.as_view(),
                name='sms__create_mlist',
            ),
        ),
        Swappable(
            re_path(
                r'^messaging_list/edit/(?P<mlist_id>\d+)[/]?$',
                messaging_list.MessagingListEdition.as_view(),
                name='sms__edit_mlist',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^messaging_list/(?P<mlist_id>\d+)[/]?$',
                messaging_list.MessagingListDetail.as_view(),
                name='sms__view_mlist',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='sms',
    ).kept_patterns(),

    *swap_manager.add_group(
        sms.messagetemplate_model_is_custom,
        Swappable(
            re_path(
                r'^templates[/]?$',
                template.MessageTemplatesList.as_view(),
                name='sms__list_templates',
            ),
        ),
        Swappable(
            re_path(
                r'^template/add[/]?$',
                template.MessageTemplateCreation.as_view(),
                name='sms__create_template',
            ),
        ),
        Swappable(
            re_path(
                r'^template/edit/(?P<template_id>\d+)[/]?$',
                template.MessageTemplateEdition.as_view(),
                name='sms__edit_template',
            ),
            check_args=Swappable.INT_ID,
        ),
        Swappable(
            re_path(
                r'^template/(?P<template_id>\d+)[/]?$',
                template.MessageTemplateDetail.as_view(),
                name='sms__view_template',
            ),
            check_args=Swappable.INT_ID,
        ),
        app_name='sms',
    ).kept_patterns(),
]
