# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme import tickets
from .views import portal


urlpatterns = [
    url(r'^$', portal.portal, name='tickets__portal'),
]

if not tickets.ticket_model_is_custom():
    from .views import ticket

    urlpatterns += [
        url(r'^tickets$',                        ticket.listview,   name='tickets__list_tickets'),
        url(r'^ticket/add$',                     ticket.add,        name='tickets__create_ticket'),
        url(r'^ticket/edit/(?P<ticket_id>\d+)$', ticket.edit,       name='tickets__edit_ticket'),
        url(r'^ticket/(?P<ticket_id>\d+)$',      ticket.detailview, name='tickets__view_ticket'),
    ]

if not tickets.tickettemplate_model_is_custom():
    from .views import template

    urlpatterns += [
        url(r'^templates$',                          template.listview,   name='tickets__list_templates'),
        url(r'^template/edit/(?P<template_id>\d+)$', template.edit,       name='tickets__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      template.detailview, name='tickets__view_template'),
    ]
