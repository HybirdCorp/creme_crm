# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import tickets
# from .views import portal
from .views import ticket, template


urlpatterns = [
    # url(r'^$', portal.portal, name='tickets__portal'),
]

# if not tickets.ticket_model_is_custom():
#     urlpatterns += [
#         url(r'^tickets[/]?$',                        ticket.listview,   name='tickets__list_tickets'),
#         url(r'^ticket/add[/]?$',                     ticket.add,        name='tickets__create_ticket'),
#         url(r'^ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.edit,       name='tickets__edit_ticket'),
#         url(r'^ticket/(?P<ticket_id>\d+)[/]?$',      ticket.detailview, name='tickets__view_ticket'),
#     ]
urlpatterns += swap_manager.add_group(
    tickets.ticket_model_is_custom,
    Swappable(url(r'^tickets[/]?$',                        ticket.listview,                 name='tickets__list_tickets')),
    Swappable(url(r'^ticket/add[/]?$',                     ticket.TicketCreation.as_view(), name='tickets__create_ticket')),
    Swappable(url(r'^ticket/edit/(?P<ticket_id>\d+)[/]?$', ticket.TicketEdition.as_view(),  name='tickets__edit_ticket'), check_args=Swappable.INT_ID),
    Swappable(url(r'^ticket/(?P<ticket_id>\d+)[/]?$',      ticket.TicketDetail.as_view(),   name='tickets__view_ticket'), check_args=Swappable.INT_ID),
    app_name='tickets',
).kept_patterns()

# if not tickets.tickettemplate_model_is_custom():
#     urlpatterns += [
#         url(r'^templates[/]?$',                          template.listview,   name='tickets__list_templates'),
#         url(r'^template/edit/(?P<template_id>\d+)[/]?$', template.edit,       name='tickets__edit_template'),
#         url(r'^template/(?P<template_id>\d+)[/]?$',      template.detailview, name='tickets__view_template'),
#     ]
urlpatterns += swap_manager.add_group(
    tickets.tickettemplate_model_is_custom,
    Swappable(url(r'^templates[/]?$',                          template.listview,                        name='tickets__list_templates')),
    Swappable(url(r'^template/edit/(?P<template_id>\d+)[/]?$', template.TicketTemplateEdition.as_view(), name='tickets__edit_template'), check_args=Swappable.INT_ID),
    Swappable(url(r'^template/(?P<template_id>\d+)[/]?$',      template.TicketTemplateDetail.as_view(),  name='tickets__view_template'), check_args=Swappable.INT_ID),
    app_name='tickets',
).kept_patterns()
