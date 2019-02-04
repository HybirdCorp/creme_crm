# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import url, include

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import emails
from .views import campaign, sending, recipient, mailing_list, template, mail, signature


urlpatterns = [
    # Campaign: mailing_list brick
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/add[/]?$',    campaign.MailingListsAdding.as_view(), name='emails__add_mlists_to_campaign'),
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete[/]?$', campaign.delete_ml,                    name='emails__remove_mlist_from_campaign'),

    # Campaign: sending brick
    url(r'^campaign/(?P<campaign_id>\d+)/sending/add[/]?$', sending.SendingCreation.as_view(), name='emails__create_sending'),

    # Campaign: sending details brick
    # url(r'^campaign/sending/(?P<sending_id>\d+)/mails/reload[/]?$', sending.reload_mails_brick, name='emails__reload_lw_mails_brick'),
    url(r'^sending/(?P<sending_id>\d+)[/]?$',          sending.SendingDetail.as_view(), name='emails__view_sending'),
    url(r'^sending/(?P<sending_id>\d+)/get_body[/]?$', sending.SendingBody.as_view(),   name='emails__sending_body'),
    url(r'^sending/(?P<sending_id>\d+)/reload[/]?$',   sending.reload_sending_bricks,   name='emails__reload_sending_bricks'),

    # Mailing list: recipients brick
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add[/]?$',     recipient.RecipientsAdding.as_view(),        name='emails__add_recipients'),
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv[/]?$', recipient.RecipientsAddingFromCSV.as_view(), name='emails__add_recipients_from_csv'),

    # Mailing list: contacts brick
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add[/]?$',             mailing_list.ContactsAdding.as_view(),           name='emails__add_contacts_to_mlist'),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter[/]?$', mailing_list.ContactsAddingFromFilter.as_view(), name='emails__add_contacts_to_mlist_from_filter'),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/delete[/]?$',          mailing_list.delete_contact,                     name='emails__remove_contact_from_mlist'),

    # Mailing list: organisations brick
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add[/]?$',             mailing_list.OrganisationsAdding.as_view(),           name='emails__add_orgas_to_mlist'),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter[/]?$', mailing_list.OrganisationsAddingFromFilter.as_view(), name='emails__add_orgas_to_mlist_from_filter'),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/delete[/]?$',          mailing_list.delete_organisation,                     name='emails__remove_orga_from_mlist'),

    # Mailing list: child lists brick
    url(r'^mailing_list/(?P<ml_id>\d+)/child/add[/]?$',    mailing_list.ChildrenAdding.as_view(), name='emails__add_child_mlists'),
    url(r'^mailing_list/(?P<ml_id>\d+)/child/delete[/]?$', mailing_list.delete_child,             name='emails__remove_child_mlist'),

    # Template: attachment brick
    url(r'^template/(?P<template_id>\d+)/attachment/add[/]?$',    template.AttachmentsAdding.as_view(), name='emails__add_attachments_to_template'),
    url(r'^template/(?P<template_id>\d+)/attachment/delete[/]?$', template.delete_attachment,           name='emails__remove_attachment_from_template'),

    # Mails history bricks
    url(r'^mails_history/(?P<mail_id>\w+)[/]?$', mail.LightWeightEmailPopup.as_view(), name='emails__view_lw_mail'),
    url(r'^mail/get_body/(?P<mail_id>\w+)[/]?$', mail.get_lightweight_mail_body,       name='emails__lw_mail_body'),
    url(r'^mail/resend[/]?$',                    mail.resend_mails,                    name='emails__resend_emails'),

    # Signature
    url(r'^signature/', include([
        url(r'^add[/]?$',                        signature.SignatureCreation.as_view(), name='emails__create_signature'),
        url(r'^edit/(?P<signature_id>\d+)[/]?$', signature.SignatureEdition.as_view(),  name='emails__edit_signature'),
        url(r'^delete[/]?$',                     signature.delete,                      name='emails__delete_signature'),
    ])),
]

urlpatterns += swap_manager.add_group(
    emails.emailcampaign_model_is_custom,
    # Swappable(url(r'^campaigns[/]?$',                          campaign.listview,                        name='emails__list_campaigns')),
    Swappable(url(r'^campaigns[/]?$',                          campaign.EmailCampaignsList.as_view(),    name='emails__list_campaigns')),
    Swappable(url(r'^campaign/add[/]?$',                       campaign.EmailCampaignCreation.as_view(), name='emails__create_campaign')),
    Swappable(url(r'^campaign/edit/(?P<campaign_id>\d+)[/]?$', campaign.EmailCampaignEdition.as_view(),  name='emails__edit_campaign'), check_args=Swappable.INT_ID),
    Swappable(url(r'^campaign/(?P<campaign_id>\d+)[/]?$',      campaign.EmailCampaignDetail.as_view(),   name='emails__view_campaign'), check_args=Swappable.INT_ID),
    app_name='emails',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    emails.emailtemplate_model_is_custom,
    # Swappable(url(r'^templates[/]?$',                          template.listview,                        name='emails__list_templates')),
    Swappable(url(r'^templates[/]?$',                          template.EmailTemplatesList.as_view(),    name='emails__list_templates')),
    Swappable(url(r'^template/add[/]?$',                       template.EmailTemplateCreation.as_view(), name='emails__create_template')),
    Swappable(url(r'^template/edit/(?P<template_id>\d+)[/]?$', template.EmailTemplateEdition.as_view(),  name='emails__edit_template'), check_args=Swappable.INT_ID),
    Swappable(url(r'^template/(?P<template_id>\d+)[/]?$',      template.EmailTemplateDetail.as_view(),   name='emails__view_template'), check_args=Swappable.INT_ID),
    app_name='emails',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    emails.entityemail_model_is_custom,
    # Swappable(url(r'^mails[/]?$',                                     mail.listview,                      name='emails__list_emails')),
    Swappable(url(r'^mails[/]?$',                                     mail.EntityEmailsList.as_view(),    name='emails__list_emails')),
    Swappable(url(r'^mail/add/(?P<entity_id>\d+)[/]?$',               mail.EntityEmailCreation.as_view(), name='emails__create_email'),               check_args=Swappable.INT_ID),
    Swappable(url(r'^mail/add_from_template/(?P<entity_id>\d+)[/]?$', mail.EntityEmailWizard.as_view(),   name='emails__create_email_from_template'), check_args=Swappable.INT_ID),
    Swappable(url(r'^mail/(?P<mail_id>\d+)[/]?$',                     mail.EntityEmailDetail.as_view(),   name='emails__view_email'),                 check_args=Swappable.INT_ID),
    Swappable(url(r'^mail/(?P<mail_id>\d+)/popup[/]?$',               mail.EntityEmailPopup.as_view(),    name='emails__view_email_popup'),           check_args=Swappable.INT_ID),
    app_name='emails',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    emails.mailinglist_model_is_custom,
    # Swappable(url(r'^mailing_lists[/]?$',                    mailing_list.listview,                      name='emails__list_mlists')),
    Swappable(url(r'^mailing_lists[/]?$',                    mailing_list.MailingListsList.as_view(),    name='emails__list_mlists')),
    Swappable(url(r'^mailing_list/add[/]?$',                 mailing_list.MailingListCreation.as_view(), name='emails__create_mlist')),
    Swappable(url(r'^mailing_list/edit/(?P<ml_id>\d+)[/]?$', mailing_list.MailingListEdition.as_view(),  name='emails__edit_mlist'), check_args=Swappable.INT_ID),
    Swappable(url(r'^mailing_list/(?P<ml_id>\d+)[/]?$',      mailing_list.MailingListDetail.as_view(),   name='emails__view_mlist'), check_args=Swappable.INT_ID),
    app_name='emails',
).kept_patterns()

if apps.is_installed('creme.crudity'):
    from .views import crudity

    urlpatterns += [
        url(r'^mail/spam[/]?$',       crudity.spam,                      name='emails__crudity_spam'),
        url(r'^mail/validated[/]?$',  crudity.validated,                 name='emails__crudity_validated'),
        url(r'^mail/waiting[/]?$',    crudity.waiting,                   name='emails__crudity_waiting'),
        url(r'^synchronization[/]?$', crudity.Synchronisation.as_view(), name='emails__crudity_sync'),
    ]
