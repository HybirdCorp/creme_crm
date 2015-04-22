# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import ticket_model_is_custom, tickettemplate_model_is_custom


urlpatterns = patterns('creme.tickets.views',
    (r'^$', 'portal.portal'),
)

if not ticket_model_is_custom():
    urlpatterns += patterns('creme.tickets.views.ticket',
        url(r'^tickets$',                        'listview',   name='tickets__list_tickets'),
        url(r'^ticket/add$',                     'add',        name='tickets__create_ticket'),
        url(r'^ticket/edit/(?P<ticket_id>\d+)$', 'edit',       name='tickets__edit_ticket'),
        url(r'^ticket/(?P<ticket_id>\d+)$',      'detailview', name='tickets__view_ticket'),
    )

if not tickettemplate_model_is_custom():
    urlpatterns += patterns('creme.tickets.views.template',
        url(r'^templates$',                          'listview',   name='tickets__list_templates'),
        url(r'^template/edit/(?P<template_id>\d+)$', 'edit',       name='tickets__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      'detailview', name='tickets__view_template'),
    )
