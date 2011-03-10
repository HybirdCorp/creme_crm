# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('billing.views',
    (r'^$', 'portal.portal'),

    (r'^odt/(?P<base_id>\d+)$',          'export.export_odt'), #TODO: delete ??
    (r'^pdf/(?P<base_id>\d+)$',          'export.export_pdf'), #TODO: delete ??
    (r'^generate_pdf/(?P<base_id>\d+)$', 'export.export_pdf_by_latex'),

    (r'^templates$',                            'templatebase.listview'),
    (r'^template/edit/(?P<template_id>\d+)$',   'templatebase.edit'),
    (r'^template/(?P<template_id>\d+)$',        'templatebase.detailview'),
    #(r'^template/delete/(?P<template_id>\d+)$', 'templatebase.delete'),

    (r'^sales_orders$',                       'sales_order.listview'),
    (r'^sales_order/add$',                    'sales_order.add'),
    (r'^sales_order/edit/(?P<order_id>\d+)$', 'sales_order.edit'),
    (r'^sales_order/(?P<order_id>\d+)$',      'sales_order.detailview'),

    (r'^quotes$',                       'quote.listview'),
    (r'^quote/add$',                    'quote.add'),
    (r'^quote/edit/(?P<quote_id>\d+)$', 'quote.edit'),
    (r'^quote/(?P<quote_id>\d+)$',      'quote.detailview'),

    (r'^credit_note$',                              'credit_note.listview'),
    (r'^credit_note/add$',                          'credit_note.add'),
    (r'^credit_note/edit/(?P<credit_note_id>\d+)$', 'credit_note.edit'),
    (r'^credit_note/(?P<credit_note_id>\d+)$',      'credit_note.detailview'),

    (r'^invoices$',                                    'invoice.listview'),
    (r'^invoice/add$',                                 'invoice.add'),
    (r'^invoice/edit/(?P<invoice_id>\d+)$',            'invoice.edit'),
    (r'^invoice/generate_number/(?P<invoice_id>\d+)$', 'invoice.generate_number'),
    (r'^invoice/(?P<invoice_id>\d+)$',                 'invoice.detailview'),

    (r'^(?P<document_id>\d+)/convert/$', 'convert.convert'),

    (r'^(?P<document_id>\d+)/product_line/add$',            'line.add_product_line'),
    (r'^(?P<document_id>\d+)/product_line/add_on_the_fly$', 'line.add_product_line_on_the_fly'),
    (r'^(?P<document_id>\d+)/service_line/add$',            'line.add_service_line'),
    (r'^(?P<document_id>\d+)/service_line/add_on_the_fly$', 'line.add_service_line_on_the_fly'),
    (r'^line/(?P<line_id>\d+)/update$',                     'line.update'),
    (r'^productline/(?P<line_id>\d+)/edit$',                'line.edit_productline'),
    (r'^serviceline/(?P<line_id>\d+)/edit$',                'line.edit_serviceline'),
)
