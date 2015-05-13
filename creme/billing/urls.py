# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from . import (credit_note_model_is_custom, invoice_model_is_custom,
        quote_model_is_custom, sales_order_model_is_custom, template_base_model_is_custom,
        product_line_model_is_custom, service_line_model_is_custom)


urlpatterns = patterns('creme.billing.views',
    (r'^$', 'portal.portal'),

    (r'^generate_pdf/(?P<base_id>\d+)$', 'export.export_as_pdf'),

    (r'^payment_information/add/(?P<entity_id>\d+)$',                                          'payment_information.add'),
    (r'^payment_information/edit/(?P<payment_information_id>\d+)$',                            'payment_information.edit'),
    (r'^payment_information/set_default/(?P<payment_information_id>\d+)/(?P<billing_id>\d+)$', 'payment_information.set_default'),

    (r'^(?P<document_id>\d+)/convert/$', 'convert.convert'),

#    (r'^lines$',                                'line.listview'),
    (r'^line/(?P<line_id>\d+)/add_to_catalog',  'line.add_to_catalog'),
    (r'^(?P<document_id>\d+)/multi_save_lines', 'line.multi_save_lines'),
)

if not invoice_model_is_custom():
    urlpatterns += patterns('creme.billing.views.invoice',
        url(r'^invoices$',                                    'listview',        name='billing__list_invoices'),
        url(r'^invoice/add$',                                 'add',             name='billing__create_invoice'),
#        url(r'^invoice/add/(?P<entity_id>\d+)$',                           'add_from_detailview', name='billing__create_invoice_for_target'),
#        url(r'^invoice/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations',  name='billing__create_related_invoice'),
        url(r'^invoice/add/(?P<target_id>\d+)$',              'add_related',     name='billing__create_related_invoice'),
        url(r'^invoice/edit/(?P<invoice_id>\d+)$',            'edit',            name='billing__edit_invoice'),
        url(r'^invoice/generate_number/(?P<invoice_id>\d+)$', 'generate_number', name='billing__generate_invoice_number'),
        url(r'^invoice/(?P<invoice_id>\d+)$',                 'detailview',      name='billing__view_invoice'),
    )

if not quote_model_is_custom():
    urlpatterns += patterns('creme.billing.views.quote',
        url(r'^quotes$',                       'listview',    name='billing__list_quotes'),
        url(r'^quote/add$',                    'add',         name='billing__create_quote'),
#        url(r'^quote/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations', name='billing__create_related_quote'),
        url(r'^quote/add/(?P<target_id>\d+)$', 'add_related', name='billing__create_related_quote'),
        url(r'^quote/edit/(?P<quote_id>\d+)$', 'edit',        name='billing__edit_quote'),
        url(r'^quote/(?P<quote_id>\d+)$',      'detailview',  name='billing__view_quote'),
    )

if not sales_order_model_is_custom():
    urlpatterns += patterns('creme.billing.views.sales_order',
        url(r'^sales_orders$',                       'listview',    name='billing__list_orders'),
        url(r'^sales_order/add$',                    'add',         name='billing__create_order'),
#        url(r'^sales_order/add/(?P<target_id>\d+)/source/(?P<source_id>\d+)$', 'add_with_relations', name='billing__create_related_order'),
        url(r'^sales_order/add/(?P<target_id>\d+)$', 'add_related', name='billing__create_related_order'),
        url(r'^sales_order/edit/(?P<order_id>\d+)$', 'edit',        name='billing__edit_order'),
        url(r'^sales_order/(?P<order_id>\d+)$',      'detailview',  name='billing__view_order'),
    )

if not credit_note_model_is_custom():
    urlpatterns += patterns('creme.billing.views.credit_note',
        url(r'^credit_note$',                                                               'listview',                   name='billing__list_cnotes'), #TODO: change to '^credit_noteS'
        url(r'^credit_note/add$',                                                           'add',                        name='billing__create_cnote'),
        url(r'^credit_note/edit/(?P<credit_note_id>\d+)$',                                  'edit',                       name='billing__edit_cnote'),
        url(r'^credit_note/(?P<credit_note_id>\d+)$',                                       'detailview',                 name='billing__view_cnote'),
        url(r'^credit_note/editcomment/(?P<credit_note_id>\d+)/$',                          'edit_comment',               name='billing__edit_cnote_comment'),
        url(r'^credit_note/add_related_to/(?P<base_id>\d+)/$',                              'add_related_credit_note',    name='billing__create_related_cnote'),
        url(r'^credit_note/delete_related/(?P<credit_note_id>\d+)/from/(?P<base_id>\d+)/$', 'delete_related_credit_note', name='billing__delete_related_cnote'),
    )

if not template_base_model_is_custom():
    urlpatterns += patterns('creme.billing.views.templatebase',
        url(r'^templates$',                          'listview',   name='billing__list_templates'),
        url(r'^template/edit/(?P<template_id>\d+)$', 'edit',       name='billing__edit_template'),
        url(r'^template/(?P<template_id>\d+)$',      'detailview', name='billing__view_template'),
    )

if not product_line_model_is_custom():
    urlpatterns += patterns('creme.billing.views.line',
        url(r'^product_lines$',                                  'listview_product_line',     name='billing__list_product_lines'),
        url(r'^(?P<document_id>\d+)/product_line/add_multiple$', 'add_multiple_product_line', name='billing__create_product_lines'),
    )

if not service_line_model_is_custom():
    urlpatterns += patterns('creme.billing.views.line',
        url(r'^service_lines$',                                  'listview_service_line',     name='billing__list_service_lines'),
        url(r'^(?P<document_id>\d+)/service_line/add_multiple$', 'add_multiple_service_line', name='billing__create_service_lines'),
    )
