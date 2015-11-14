# -*- coding: utf-8 -*-

from django.conf.urls import url

from . import (credit_note_model_is_custom, invoice_model_is_custom,
        quote_model_is_custom, sales_order_model_is_custom, template_base_model_is_custom,
        product_line_model_is_custom, service_line_model_is_custom)
from .views import portal, export, payment_information, convert, line

urlpatterns = [
    url(r'^$', portal.portal),

    url(r'^generate_pdf/(?P<base_id>\d+)$', export.export_as_pdf),

    url(r'^payment_information/add/(?P<entity_id>\d+)$',                                          payment_information.add),
    url(r'^payment_information/edit/(?P<payment_information_id>\d+)$',                            payment_information.edit),
    url(r'^payment_information/set_default/(?P<payment_information_id>\d+)/(?P<billing_id>\d+)$', payment_information.set_default),

    url(r'^(?P<document_id>\d+)/convert/$', convert.convert),

#    url(r'^lines$',                                line.listview),
    url(r'^line/(?P<line_id>\d+)/add_to_catalog',  line.add_to_catalog),
    url(r'^(?P<document_id>\d+)/multi_save_lines', line.multi_save_lines),
]

if not invoice_model_is_custom():
    from .views import invoice

    urlpatterns += [
        url(r'^invoices$',                                    invoice.listview,        name='billing__list_invoices'),
        url(r'^invoice/add$',                                 invoice.add,             name='billing__create_invoice'),
#        url(r'^invoice/add/(?P<entity_id>\d+)$',                           'add_from_detailview', name='billing__create_invoice_for_target'),
#        url(r'^invoice/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations',  name='billing__create_related_invoice'),
        url(r'^invoice/add/(?P<target_id>\d+)$',              invoice.add_related,     name='billing__create_related_invoice'),
        url(r'^invoice/edit/(?P<invoice_id>\d+)$',            invoice.edit,            name='billing__edit_invoice'),
        url(r'^invoice/generate_number/(?P<invoice_id>\d+)$', invoice.generate_number, name='billing__generate_invoice_number'),
        url(r'^invoice/(?P<invoice_id>\d+)$',                 invoice.detailview,      name='billing__view_invoice'),
    ]

if not quote_model_is_custom():
    from .views import quote

    urlpatterns += [
        url(r'^quotes$',                       quote.listview,    name='billing__list_quotes'),
        url(r'^quote/add$',                    quote.add,         name='billing__create_quote'),
#        url(r'^quote/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations', name='billing__create_related_quote'),
        url(r'^quote/add/(?P<target_id>\d+)$', quote.add_related, name='billing__create_related_quote'),
        url(r'^quote/edit/(?P<quote_id>\d+)$', quote.edit,        name='billing__edit_quote'),
        url(r'^quote/(?P<quote_id>\d+)$',      quote.detailview,  name='billing__view_quote'),
    ]

if not sales_order_model_is_custom():
    from .views import sales_order

    urlpatterns += [
        url(r'^sales_orders$',                       sales_order.listview,    name='billing__list_orders'),
        url(r'^sales_order/add$',                    sales_order.add,         name='billing__create_order'),
#        url(r'^sales_order/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations', name='billing__create_related_order'),
        url(r'^sales_order/add/(?P<target_id>\d+)$', sales_order.add_related, name='billing__create_related_order'),
        url(r'^sales_order/edit/(?P<order_id>\d+)$', sales_order.edit,        name='billing__edit_order'),
        url(r'^sales_order/(?P<order_id>\d+)$',      sales_order.detailview,  name='billing__view_order'),
    ]

if not credit_note_model_is_custom():
    from .views import credit_note

    urlpatterns += [
        url(r'^credit_note$',                                                               credit_note.listview,                   name='billing__list_cnotes'), #TODO: change to '^credit_noteS'
        url(r'^credit_note/add$',                                                           credit_note.add,                        name='billing__create_cnote'),
        url(r'^credit_note/edit/(?P<credit_note_id>\d+)$',                                  credit_note.edit,                       name='billing__edit_cnote'),
        url(r'^credit_note/(?P<credit_note_id>\d+)$',                                       credit_note.detailview,                 name='billing__view_cnote'),
        url(r'^credit_note/editcomment/(?P<credit_note_id>\d+)/$',                          credit_note.edit_comment,               name='billing__edit_cnote_comment'),
        url(r'^credit_note/add_related_to/(?P<base_id>\d+)/$',                              credit_note.link_to_credit_notes,       name='billing__link_to_cnotes'),
        url(r'^credit_note/delete_related/(?P<credit_note_id>\d+)/from/(?P<base_id>\d+)/$', credit_note.delete_related_credit_note, name='billing__delete_related_cnote'),
    ]

if not template_base_model_is_custom():
    from .views import templatebase

    urlpatterns += [
        url(r'^templates$',                          templatebase.listview,   name='billing__list_templates'),
        url(r'^template/edit/(?P<template_id>\d+)$', templatebase.edit,       name='billing__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      templatebase.detailview, name='billing__view_template'),
    ]

if not product_line_model_is_custom():
    urlpatterns += [
        url(r'^product_lines$',                                  line.listview_product_line,     name='billing__list_product_lines'),
        url(r'^(?P<document_id>\d+)/product_line/add_multiple$', line.add_multiple_product_line, name='billing__create_product_lines'),
    ]

if not service_line_model_is_custom():
    urlpatterns += [
        url(r'^service_lines$',                                  line.listview_service_line,     name='billing__list_service_lines'),
        url(r'^(?P<document_id>\d+)/service_line/add_multiple$', line.add_multiple_service_line, name='billing__create_service_lines'),
    ]
