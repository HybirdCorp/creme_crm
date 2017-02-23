# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import url, include

from creme import emails
from .views import portal, campaign, sending, recipient, mailing_list, template, mail, signature


urlpatterns = [
    url(r'^$', portal.portal, name='emails__portal'),

    # Campaign: mailing_list block
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/add$',    campaign.add_ml,    name='emails__add_mlists_to_campaign'),
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete$', campaign.delete_ml, name='emails__remove_mlist_from_campaign'),

    # Campaign: sending block
    url(r'^campaign/(?P<campaign_id>\d+)/sending/add$', sending.add, name='emails__create_sending'),

    # Campaign: sending details block (TODO: remove 'campaign/' from url ??)
    url(r'^campaign/sending/(?P<sending_id>\d+)$',               sending.detailview,         name='emails__view_sending'),
    url(r'^campaign/sending/(?P<sending_id>\d+)/mails/reload/$', sending.reload_block_mails, name='emails__reload_lw_mails_block'),

    # Mailing list: recipients block
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add$',     recipient.add,          name='emails__add_recipients'),
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv$', recipient.add_from_csv, name='emails__add_recipients_from_csv'),

    # Mailing list: contacts block
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add$',             mailing_list.add_contacts,             name='emails__add_contacts_to_mlist'),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter$', mailing_list.add_contacts_from_filter, name='emails__add_contacts_to_mlist_from_filter'),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/delete$',          mailing_list.delete_contact,           name='emails__remove_contact_from_mlist'),

    # Mailing list: organisations block
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add$',             mailing_list.add_organisations,             name='emails__add_orgas_to_mlist'),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter$', mailing_list.add_organisations_from_filter, name='emails__add_orgas_to_mlist_from_filter'),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/delete$',          mailing_list.delete_organisation,           name='emails__remove_orga_from_mlist'),

    # Mailing list: child lists block
    url(r'^mailing_list/(?P<ml_id>\d+)/child/add$',    mailing_list.add_children, name='emails__add_child_mlists'),
    url(r'^mailing_list/(?P<ml_id>\d+)/child/delete$', mailing_list.delete_child, name='emails__remove_child_mlist'),

    # Template: attachment block
    url(r'^template/(?P<template_id>\d+)/attachment/add$',    template.add_attachment,    name='emails__add_attachments_to_template'),
    url(r'^template/(?P<template_id>\d+)/attachment/delete$', template.delete_attachment, name='emails__remove_attachment_from_template'),

    # Mails history blocks
    url(r'^mails_history/(?P<mail_id>\w+)$', mail.view_lightweight_mail,     name='emails__view_lw_mail'),
    url(r'^mail/get_body/(?P<mail_id>\w+)$', mail.get_lightweight_mail_body, name='emails__lw_mail_body'),
    url(r'^mail/resend$',                    mail.resend_mails,              name='emails__resend_emails'),

    # Signature
    url(r'^signature/', include([
        url(r'^add$',                        signature.add,    name='emails__create_signature'),
        url(r'^edit/(?P<signature_id>\d+)$', signature.edit,   name='emails__edit_signature'),
        url(r'^delete$',                     signature.delete, name='emails__delete_signature'),
    ])),
]

if not emails.emailcampaign_model_is_custom():
    urlpatterns += [
        url(r'^campaigns$',                          campaign.listview,   name='emails__list_campaigns'),
        url(r'^campaign/add$',                       campaign.add,        name='emails__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', campaign.edit,       name='emails__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      campaign.detailview, name='emails__view_campaign'),
    ]

if not emails.emailtemplate_model_is_custom():
    urlpatterns += [
        url(r'^templates$',                          template.listview,   name='emails__list_templates'),
        url(r'^template/add$',                       template.add,        name='emails__create_template'),
        url(r'^template/edit/(?P<template_id>\d+)$', template.edit,       name='emails__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      template.detailview, name='emails__view_template'),
    ]

if not emails.entityemail_model_is_custom():
    urlpatterns += [
        url(r'^mails$',                                     mail.listview,                    name='emails__list_emails'),
        url(r'^mail/add/(?P<entity_id>\d+)$',               mail.create_n_send,               name='emails__create_email'),
        url(r'^mail/add_from_template/(?P<entity_id>\d+)$', mail.create_from_template_n_send, name='emails__create_email_from_template'),
        url(r'^mail/(?P<mail_id>\d+)$',                     mail.detailview,                  name='emails__view_email'),
        url(r'^mail/(?P<mail_id>\d+)/popup$',               mail.popupview,                   name='emails__view_email_popup'),
    ]

if not emails.mailinglist_model_is_custom():
    urlpatterns += [
        url(r'^mailing_lists$',                    mailing_list.listview,   name='emails__list_mlists'),
        url(r'^mailing_list/add$',                 mailing_list.add,        name='emails__create_mlist'),
        url(r'^mailing_list/edit/(?P<ml_id>\d+)$', mailing_list.edit,       name='emails__edit_mlist'),
        url(r'^mailing_list/(?P<ml_id>\d+)$',      mailing_list.detailview, name='emails__view_mlist'),
    ]


if apps.is_installed('creme.crudity'):
    from .views import crudity

    urlpatterns += [
        url(r'^mail/spam$',          crudity.spam,               name='emails__crudity_spam'),
        url(r'^mail/validated$',     crudity.validated,          name='emails__crudity_validated'),
        url(r'^mail/waiting$',       crudity.waiting,            name='emails__crudity_waiting'),
        url(r'^synchronization$',    crudity.synchronisation,    name='emails__crudity_sync'),
        url(r'^sync_blocks/reload$', crudity.reload_sync_blocks, name='emails__crudity_reload_sync_blocks'),
    ]
