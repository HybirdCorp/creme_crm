# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('emails.views',
    (r'^$', 'portal.portal'),

    (r'^campaigns$',                          'campaign.listview'),
    (r'^campaign/add$',                       'campaign.add'),
    (r'^campaign/edit/(?P<campaign_id>\d+)$', 'campaign.edit'),
    (r'^campaign/(?P<campaign_id>\d+)$',      'campaign.detailview'),

    #Campaign: mailing_list block
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/add$',    'campaign.add_ml'),
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete$', 'campaign.delete_ml'),

    #Campaign: sending block
    (r'^campaign/(?P<campaign_id>\d+)/sending/add$', 'sending.add'),
    (r'^campaign/sending/delete$',                   'sending.delete'),

    #Campaign: sending details block
    (r'^campaign/sending/(?P<sending_id>\d+)$',               'sending.detailview'),
    (r'^campaign/sending/mail/delete$',                       'sending.delete_mail'),
    (r'^campaign/sending/(?P<sending_id>\d+)/mails/reload/$', 'sending.reload_block_mails'),

    (r'^mailing_lists$',                    'mailing_list.listview'),
    (r'^mailing_list/add$',                 'mailing_list.add'),
    (r'^mailing_list/edit/(?P<ml_id>\d+)$', 'mailing_list.edit'),
    (r'^mailing_list/(?P<ml_id>\d+)$',      'mailing_list.detailview'),

    #Mailing list: recipients block
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add$',     'recipient.add'),
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv$', 'recipient.add_from_csv'),
    (r'^mailing_list/recipient/delete$',                 'recipient.delete'),

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

    (r'^templates$',                          'template.listview'),
    (r'^template/add$',                       'template.add'),
    (r'^template/edit/(?P<template_id>\d+)$', 'template.edit'),
    (r'^template/(?P<template_id>\d+)$',      'template.detailview'),

    #Template: attachment block
    (r'^template/(?P<template_id>\d+)/attachment/add$',    'template.add_attachment'),
    (r'^template/(?P<template_id>\d+)/attachment/delete$', 'template.delete_attachment'),

    #mails history block
    #(r'^entity/(?P<entity_id>\d+)/mails_history/reload/$', 'mail.reload_block_mails_history'),
    (r'^mails_history/(?P<mail_id>\w+)$',                  'mail.view_lightweight_mail'),
    (r'^mail/delete$',                                     'mail.delete'),
    (r'^mail/spam$',                                       'mail.spam'),
    (r'^mail/validated$',                                  'mail.validated'),
    (r'^mail/waiting$',                                    'mail.waiting'),
    (r'^mail/(?P<mail_id>\w+)$',                           'mail.detailview'),
    (r'^mails$',                                           'mail.listview'),
    (r'^synchronization$',                                 'mail.synchronisation'),
    (r'^sync_blocks/reload$',                              'mail.reload_sync_blocks'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^entitymail/delete/(?P<object_id>\d+)$',   'delete_entity'),
    (r'^campaign/delete/(?P<object_id>\d+)$',     'delete_entity'),
    (r'^mailing_list/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^template/delete/(?P<object_id>\d+)$',     'delete_entity'),
)
