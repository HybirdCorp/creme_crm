# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('emails.views',
    (r'^$', 'portal.portal'),

    (r'^campaigns$',                          'campaign.listview'),
    (r'^campaign/add$',                       'campaign.add'),
    (r'^campaign/edit/(?P<campaign_id>\d+)$', 'campaign.edit'),
    (r'^campaign/(?P<campaign_id>\d+)$',      'campaign.detailview'),

    #Campaign: mailing_list block
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/add$',      'campaign.add_ml'),
    (r'^campaign/(?P<campaign_id>\d+)/mailing_list/delete$',   'campaign.delete_ml'),
    (r'^campaign/(?P<campaign_id>\d+)/mailing_lists/reload/$', 'campaign.reload_block_ml'),

    #Campaign: sending block
    (r'^campaign/(?P<campaign_id>\d+)/sending/add$',      'sending.add'),
    (r'^campaign/sending/delete$',                        'sending.delete'),
    (r'^campaign/(?P<campaign_id>\d+)/sendings/reload/$', 'sending.reload_block_sendings'),

    #Campaign: sending details block
    (r'^campaign/sending/(?P<sending_id>\d+)$',               'sending.detailview'),
    (r'^campaign/sending/mail/delete$',                       'sending.delete_mail'),
    (r'^campaign/sending/(?P<sending_id>\d+)/mails/reload/$', 'sending.reload_block_mails'),

    (r'^mailing_lists$',                    'mailing_list.listview'),
    (r'^mailing_list/add$',                 'mailing_list.add'),
    (r'^mailing_list/edit/(?P<ml_id>\d+)$', 'mailing_list.edit'),
    (r'^mailing_list/(?P<ml_id>\d+)$',      'mailing_list.detailview'),

    #Mailing list: recipients block
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add$',      'recipient.add'),
    (r'^mailing_list/(?P<ml_id>\d+)/recipient/add_csv$',  'recipient.add_from_csv'),
    (r'^mailing_list/recipient/delete$',                  'recipient.delete'),
    (r'^mailing_list/(?P<ml_id>\d+)/recipients/reload/$', 'recipient.reload_block_recipients'),

    #Mailing list: contacts block
    (r'^mailing_list/(?P<ml_id>\d+)/contact/add$',             'mailing_list.add_contacts'),
    (r'^mailing_list/(?P<ml_id>\d+)/contact/add_from_filter$', 'mailing_list.add_contacts_from_filter'),
    (r'^mailing_list/(?P<ml_id>\d+)/contact/delete$',          'mailing_list.delete_contact'),
    (r'^mailing_list/(?P<ml_id>\d+)/contacts/reload/$',        'mailing_list.reload_block_contacts'),

    #Mailing list: organisations block
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/add$',             'mailing_list.add_organisations'),
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/add_from_filter$', 'mailing_list.add_organisations_from_filter'),
    (r'^mailing_list/(?P<ml_id>\d+)/organisation/delete$',          'mailing_list.delete_organisation'),
    (r'^mailing_list/(?P<ml_id>\d+)/organisations/reload/$',        'mailing_list.reload_block_organisations'),

    #Mailing list: child lists block
    (r'^mailing_list/(?P<ml_id>\d+)/child/add$',        'mailing_list.add_children'),
    (r'^mailing_list/(?P<ml_id>\d+)/child/delete$',     'mailing_list.delete_child'),
    (r'^mailing_list/(?P<ml_id>\d+)/children/reload/$', 'mailing_list.reload_block_child_lists'),

    #Mailing list: parent lists block
    (r'^mailing_list/(?P<ml_id>\d+)/parents/reload/$',  'mailing_list.reload_block_parent_lists'),

    (r'^templates$',                          'template.listview'),
    (r'^template/add$',                       'template.add'),
    (r'^template/edit/(?P<template_id>\d+)$', 'template.edit'),
    (r'^template/(?P<template_id>\d+)$',      'template.detailview'),

    #Template: attachment block
    (r'^template/(?P<template_id>\d+)/attachment/add$',      'template.add_attachment'),
    (r'^template/(?P<template_id>\d+)/attachment/delete$',   'template.delete_attachment'),
    (r'^template/(?P<template_id>\d+)/attachments/reload/$', 'template.reload_block_attachments'),

    #mails history block
    (r'^entity/(?P<entity_id>\d+)/mails_history/reload/$', 'mail.reload_block_mails_history'),
    (r'^mails_history/(?P<mail_id>\w+)$',                  'mail.view_mail'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^campaign/delete/(?P<object_id>\d+)$',     'delete_entity'),
    (r'^mailing_list/delete/(?P<object_id>\d+)$', 'delete_entity'),
    (r'^template/delete/(?P<object_id>\d+)$',     'delete_entity'),
)
