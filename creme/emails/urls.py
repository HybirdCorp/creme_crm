# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import (emailcampaign_model_is_custom, emailtemplate_model_is_custom,
        entityemail_model_is_custom, mailinglist_model_is_custom)
from .views import portal, campaign, sending, recipient, mailing_list, template, mail, signature

urlpatterns = [
    url(r'^$', portal.portal),

    # Campaign: mailing_list block
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/add$',    campaign.add_ml),
    url(r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete$', campaign.delete_ml),

    # Campaign: sending block
    url(r'^campaign/(?P<campaign_id>\d+)/sending/add$', sending.add),

    # Campaign: sending details block (TODO: remove campaign/ from url ??)
    url(r'^campaign/sending/(?P<sending_id>\d+)$',               sending.detailview),
    url(r'^campaign/sending/(?P<sending_id>\d+)/mails/reload/$', sending.reload_block_mails),

    # Mailing list: recipients block
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add$',     recipient.add),
    url(r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv$', recipient.add_from_csv),

    # Mailing list: contacts block
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add$',             mailing_list.add_contacts),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter$', mailing_list.add_contacts_from_filter),
    url(r'^mailing_list/(?P<ml_id>\d+)/contact/delete$',          mailing_list.delete_contact),

    # Mailing list: organisations block
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add$',             mailing_list.add_organisations),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter$', mailing_list.add_organisations_from_filter),
    url(r'^mailing_list/(?P<ml_id>\d+)/organisation/delete$',          mailing_list.delete_organisation),

    # Mailing list: child lists block
    url(r'^mailing_list/(?P<ml_id>\d+)/child/add$',    mailing_list.add_children),
    url(r'^mailing_list/(?P<ml_id>\d+)/child/delete$', mailing_list.delete_child),

    # Template: attachment block
    url(r'^template/(?P<template_id>\d+)/attachment/add$',    template.add_attachment),
    url(r'^template/(?P<template_id>\d+)/attachment/delete$', template.delete_attachment),

    # Mails history blocks
    url(r'^mails_history/(?P<mail_id>\w+)$',          mail.view_lightweight_mail),
    url(r'^mail/get_body/(?P<mail_id>\w+)$',          mail.get_lightweight_mail_body),
    url(r'^mail/get_entity_body/(?P<entity_id>\d+)$', mail.get_entity_mail_body),
    url(r'^mail/resend$',                             mail.resend_mails),
    url(r'^mail/spam$',                               mail.spam),
    url(r'^mail/validated$',                          mail.validated),
    url(r'^mail/waiting$',                            mail.waiting),
    url(r'^synchronization$',                         mail.synchronisation),
    url(r'^sync_blocks/reload$',                      mail.reload_sync_blocks),

    # Signature
    url(r'^signature/add$',                        signature.add),
    url(r'^signature/edit/(?P<signature_id>\d+)$', signature.edit),
    url(r'^signature/delete$',                     signature.delete),
]

if not emailcampaign_model_is_custom():
    urlpatterns += [
        url(r'^campaigns$',                          campaign.listview,   name='emails__list_campaigns'),
        url(r'^campaign/add$',                       campaign.add,        name='emails__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', campaign.edit,       name='emails__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      campaign.detailview, name='emails__view_campaign'),
    ]

if not emailtemplate_model_is_custom():
    urlpatterns += [
        url(r'^templates$',                          template.listview,   name='emails__list_templates'),
        url(r'^template/add$',                       template.add,        name='emails__create_template'),
        url(r'^template/edit/(?P<template_id>\d+)$', template.edit,       name='emails__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      template.detailview, name='emails__view_template'),
    ]

if not entityemail_model_is_custom():
    urlpatterns += [
        url(r'^mails$',                                     mail.listview,                    name='emails__list_emails'),
        url(r'^mail/add/(?P<entity_id>\d+)$',               mail.create_n_send,               name='emails__create_email'),
        url(r'^mail/add_from_template/(?P<entity_id>\d+)$', mail.create_from_template_n_send, name='emails__create_email_from_template'),
        url(r'^mail/(?P<mail_id>\d+)$',                     mail.detailview,                  name='emails__view_email'),
        url(r'^mail/(?P<mail_id>\d+)/popup$',               mail.popupview,                   name='emails__view_email_popup'),
    ]

if not mailinglist_model_is_custom():
    urlpatterns += [
        url(r'^mailing_lists$',                    mailing_list.listview,   name='emails__list_mlists'),
        url(r'^mailing_list/add$',                 mailing_list.add,        name='emails__create_mlist'),
        url(r'^mailing_list/edit/(?P<ml_id>\d+)$', mailing_list.edit,       name='emails__edit_mlist'),
        url(r'^mailing_list/(?P<ml_id>\d+)$',      mailing_list.detailview, name='emails__view_mlist'),
    ]
