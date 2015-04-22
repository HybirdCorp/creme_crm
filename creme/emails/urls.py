# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import (emailcampaign_model_is_custom, emailtemplate_model_is_custom,
        entityemail_model_is_custom, mailinglist_model_is_custom)


urlpatterns = patterns('creme.emails.views',
    (r'^$', 'portal.portal'),

    #Campaign: mailing_list block
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/add$',    'campaign.add_ml'),
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete$', 'campaign.delete_ml'),

    #Campaign: sending block
    (r'^campaign/(?P<campaign_id>\d+)/sending/add$', 'sending.add'),

    #Campaign: sending details block (TODO: remove campaign/ from url ??)
    (r'^campaign/sending/(?P<sending_id>\d+)$',               'sending.detailview'),
    (r'^campaign/sending/(?P<sending_id>\d+)/mails/reload/$', 'sending.reload_block_mails'),

    #Mailing list: recipients block
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add$',     'recipient.add'),
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv$', 'recipient.add_from_csv'),

    #Mailing list: contacts block
    (r'^mailing_list/(?P<ml_id>\d+)/contact/add$',             'mailing_list.add_contacts'),
    (r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter$', 'mailing_list.add_contacts_from_filter'),
    (r'^mailing_list/(?P<ml_id>\d+)/contact/delete$',          'mailing_list.delete_contact'),

    #Mailing list: organisations block
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/add$',             'mailing_list.add_organisations'),
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter$', 'mailing_list.add_organisations_from_filter'),
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/delete$',          'mailing_list.delete_organisation'),

    #Mailing list: child lists block
    (r'^mailing_list/(?P<ml_id>\d+)/child/add$',    'mailing_list.add_children'),
    (r'^mailing_list/(?P<ml_id>\d+)/child/delete$', 'mailing_list.delete_child'),

    #Template: attachment block
    (r'^template/(?P<template_id>\d+)/attachment/add$',    'template.add_attachment'),
    (r'^template/(?P<template_id>\d+)/attachment/delete$', 'template.delete_attachment'),

    #mails history blocks
    (r'^mails_history/(?P<mail_id>\w+)$',          'mail.view_lightweight_mail'),
    (r'^mail/get_body/(?P<mail_id>\w+)$',          'mail.get_lightweight_mail_body'),
    (r'^mail/get_entity_body/(?P<entity_id>\w+)$', 'mail.get_entity_mail_body'),
    (r'^mail/resend$',                             'mail.resend_mails'),
    (r'^mail/spam$',                               'mail.spam'),
    (r'^mail/validated$',                          'mail.validated'),
    (r'^mail/waiting$',                            'mail.waiting'),
    (r'^synchronization$',                         'mail.synchronisation'),
    (r'^sync_blocks/reload$',                      'mail.reload_sync_blocks'),

    #Signatures
    (r'^signature/add$',                        'signature.add'),
    (r'^signature/edit/(?P<signature_id>\d+)$', 'signature.edit'),
    (r'^signature/delete$',                     'signature.delete'),
)

if not emailcampaign_model_is_custom():
    urlpatterns += patterns('creme.emails.views.campaign',
        url(r'^campaigns$',                          'listview',   name='emails__list_campaigns'),
        url(r'^campaign/add$',                       'add',        name='emails__create_campaign'),
        url(r'^campaign/edit/(?P<campaign_id>\d+)$', 'edit',       name='emails__edit_campaign'),
        url(r'^campaign/(?P<campaign_id>\d+)$',      'detailview', name='emails__view_campaign'),
    )

if not emailtemplate_model_is_custom():
    urlpatterns += patterns('creme.emails.views.template',
        url(r'^templates$',                          'listview',   name='emails__list_templates'),
        url(r'^template/add$',                       'add',        name='emails__create_template'),
        url(r'^template/edit/(?P<template_id>\d+)$', 'edit',       name='emails__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      'detailview', name='emails__view_template'),
    )

if not entityemail_model_is_custom():
    urlpatterns += patterns('creme.emails.views.mail',
        url(r'^mails$',                                     'listview',                    name='emails__list_emails'),
        url(r'^mail/add/(?P<entity_id>\w+)$',               'create_n_send',               name='emails__create_email'),
        url(r'^mail/add_from_template/(?P<entity_id>\w+)$', 'create_from_template_n_send', name='emails__create_email_from_template'),
        url(r'^mail/(?P<mail_id>\w+)$',                     'detailview',                  name='emails__view_email'),
        url(r'^mail/(?P<mail_id>\w+)/popup$',               'popupview',                   name='emails__view_email_popup'),
    )

if not mailinglist_model_is_custom():
    urlpatterns += patterns('creme.emails.views.mailing_list',
        url(r'^mailing_lists$',                    'listview',   name='emails__list_mlists'),
        url(r'^mailing_list/add$',                 'add',        name='emails__create_mlist'),
        url(r'^mailing_list/edit/(?P<ml_id>\d+)$', 'edit',       name='emails__edit_mlist'),
        url(r'^mailing_list/(?P<ml_id>\d+)$',      'detailview', name='emails__view_mlist'),
    )
