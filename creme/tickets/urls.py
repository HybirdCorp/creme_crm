# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns

urlpatterns = patterns('tickets.views',
    (r'^$', 'portal.portal'),

    (r'^tickets$',                        'ticket.listview'),
    (r'^ticket/add$',                     'ticket.add'),
    (r'^ticket/edit/(?P<ticket_id>\d+)$', 'ticket.edit'),
    (r'^ticket/(?P<ticket_id>\d+)$',      'ticket.detailview'),

    (r'^templates$',                          'template.listview'),
    (r'^template/edit/(?P<template_id>\d+)$', 'template.edit'),
    (r'^template/(?P<template_id>\d+)$',      'template.detailview'),
)
