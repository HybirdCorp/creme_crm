# -*- coding: utf-8 -*-

# from django.conf.urls import url
from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import tickets
from .views import ticket, template


urlpatterns = [
    *swap_manager.add_group(
        tickets.ticket_model_is_custom,
        # Swappable(url(r'^tickets[/]?$',                        ticket.listview,                 name='tickets__list_tickets')),
        Swappable(re_path(r'^tickets[/]?$',                        ticket.TicketsList.as_view(),    name='tickets__list_tickets')),
        Swappable(re_path(r'^ticket/add[/]?$',                     ticket.TicketCreation.as_view(), name='tickets__create_ticket')),
        Swappable(re_path(r'^ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.TicketEdition.as_view(),  name='tickets__edit_ticket'), check_args=Swappable.INT_ID),
        Swappable(re_path(r'^ticket/(?P<ticket_id>\d+)[/]?$',      ticket.TicketDetail.as_view(),   name='tickets__view_ticket'), check_args=Swappable.INT_ID),
        app_name='tickets',
    ).kept_patterns(),

    *swap_manager.add_group(
        tickets.tickettemplate_model_is_custom,
        # Swappable(url(r'^templates[/]?$',                          template.listview,                        name='tickets__list_templates')),
        Swappable(re_path(r'^templates[/]?$',                          template.TicketTemplatesList.as_view(),   name='tickets__list_templates')),
        Swappable(re_path(r'^template/edit/(?P<template_id>\d+)[/]?$', template.TicketTemplateEdition.as_view(), name='tickets__edit_template'), check_args=Swappable.INT_ID),
        Swappable(re_path(r'^template/(?P<template_id>\d+)[/]?$',      template.TicketTemplateDetail.as_view(),  name='tickets__view_template'), check_args=Swappable.INT_ID),
        app_name='tickets',
    ).kept_patterns(),
]
