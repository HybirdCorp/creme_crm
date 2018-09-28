# -*- coding: utf-8 -*-

from django.conf.urls import url, include

from .. import billing
from .views import export, payment_information, convert, line  # portal


urlpatterns = [
    # url(r'^$', portal.portal, name='billing__portal'),

    url(r'^generate_pdf/(?P<base_id>\d+)[/]?$', export.export_as_pdf, name='billing__export'),

    url(r'^payment_information/', include([
        # url(r'^add/(?P<entity_id>\d+)[/]?$',                                          payment_information.add,         name='billing__create_payment_info'),
        url(r'^add/(?P<orga_id>\d+)[/]?$',                                            payment_information.PaymentInformationCreation.as_view(), name='billing__create_payment_info'),
        url(r'^edit/(?P<payment_information_id>\d+)[/]?$',                            payment_information.edit,        name='billing__edit_payment_info'),
        url(r'^set_default/(?P<payment_information_id>\d+)/(?P<billing_id>\d+)[/]?$', payment_information.set_default, name='billing__set_default_payment_info'),
    ])),

    url(r'^(?P<document_id>\d+)/convert[/]?$', convert.convert, name='billing__convert'),

    url(r'^line/(?P<line_id>\d+)/add_to_catalog[/]*',  line.add_to_catalog,   name='billing__add_to_catalog'),
    url(r'^(?P<document_id>\d+)/multi_save_lines[/]*', line.multi_save_lines, name='billing__multi_save_lines'),
]

if not billing.invoice_model_is_custom():
    from .views import invoice

    urlpatterns += [
        url(r'^invoices[/]?$',                                    invoice.listview,                         name='billing__list_invoices'),
        # url(r'^invoice/add[/]?$',                                 invoice.add,             name='billing__create_invoice'),
        url(r'^invoice/add[/]?$',                                 invoice.InvoiceCreation.as_view(),        name='billing__create_invoice'),
        # url(r'^invoice/add/(?P<target_id>\d+)[/]?$',              invoice.add_related,     name='billing__create_related_invoice'),
        url(r'^invoice/add/(?P<target_id>\d+)[/]?$',              invoice.RelatedInvoiceCreation.as_view(), name='billing__create_related_invoice'),
        # url(r'^invoice/edit/(?P<invoice_id>\d+)[/]?$',            invoice.edit,            name='billing__edit_invoice'),
        url(r'^invoice/edit/(?P<invoice_id>\d+)[/]?$',            invoice.InvoiceEdition.as_view(),         name='billing__edit_invoice'),
        url(r'^invoice/generate_number/(?P<invoice_id>\d+)[/]?$', invoice.generate_number,                  name='billing__generate_invoice_number'),
        # url(r'^invoice/(?P<invoice_id>\d+)[/]?$',                 invoice.detailview,      name='billing__view_invoice'),
        url(r'^invoice/(?P<invoice_id>\d+)[/]?$',                 invoice.InvoiceDetail.as_view(),          name='billing__view_invoice'),
    ]

if not billing.quote_model_is_custom():
    from .views import quote

    urlpatterns += [
        url(r'^quotes[/]?$',                       quote.listview,                       name='billing__list_quotes'),
        # url(r'^quote/add[/]?$',                    quote.add,         name='billing__create_quote'),
        url(r'^quote/add[/]?$',                    quote.QuoteCreation.as_view(),        name='billing__create_quote'),
        # url(r'^quote/add/(?P<target_id>\d+)[/]?$', quote.add_related, name='billing__create_related_quote'),
        url(r'^quote/add/(?P<target_id>\d+)[/]?$', quote.RelatedQuoteCreation.as_view(), name='billing__create_related_quote'),
        # url(r'^quote/edit/(?P<quote_id>\d+)[/]?$', quote.edit,        name='billing__edit_quote'),
        url(r'^quote/edit/(?P<quote_id>\d+)[/]?$', quote.QuoteEdition.as_view(),         name='billing__edit_quote'),
        # url(r'^quote/(?P<quote_id>\d+)[/]?$',      quote.detailview,  name='billing__view_quote'),
        url(r'^quote/(?P<quote_id>\d+)[/]?$',      quote.QuoteDetail.as_view(),          name='billing__view_quote'),
    ]

if not billing.sales_order_model_is_custom():
    from .views import sales_order

    urlpatterns += [
        url(r'^sales_orders[/]?$',                       sales_order.listview,                            name='billing__list_orders'),
        # url(r'^sales_order/add[/]?$',                    sales_order.add,         name='billing__create_order'),
        url(r'^sales_order/add[/]?$',                    sales_order.SalesOrderCreation.as_view(),        name='billing__create_order'),
        # url(r'^sales_order/add/(?P<target_id>\d+)[/]?$', sales_order.add_related, name='billing__create_related_order'),
        url(r'^sales_order/add/(?P<target_id>\d+)[/]?$', sales_order.RelatedSalesOrderCreation.as_view(), name='billing__create_related_order'),
        # url(r'^sales_order/edit/(?P<order_id>\d+)[/]?$', sales_order.edit,        name='billing__edit_order'),
        url(r'^sales_order/edit/(?P<order_id>\d+)[/]?$', sales_order.SalesOrderEdition.as_view(),         name='billing__edit_order'),
        # url(r'^sales_order/(?P<order_id>\d+)[/]?$',      sales_order.detailview,  name='billing__view_order'),
        url(r'^sales_order/(?P<order_id>\d+)[/]?$',      sales_order.SalesOrderDetail.as_view(),          name='billing__view_order'),
    ]

if not billing.credit_note_model_is_custom():
    from .views import credit_note

    urlpatterns += [
        # url(r'^credit_note[/]?$',                                     credit_note.listview,                     name='billing__list_cnotes'),
        url(r'^credit_notes[/]?$',                                    credit_note.listview,                     name='billing__list_cnotes'),
        # url(r'^credit_note/add[/]?$',                                 credit_note.add,                        name='billing__create_cnote'),
        url(r'^credit_note/add[/]?$',                                 credit_note.CreditNoteCreation.as_view(), name='billing__create_cnote'),
        # url(r'^credit_note/edit/(?P<credit_note_id>\d+)[/]?$',        credit_note.edit,                       name='billing__edit_cnote'),
        url(r'^credit_note/edit/(?P<cnote_id>\d+)[/]?$',              credit_note.CreditNoteEdition.as_view(),  name='billing__edit_cnote'),
        # url(r'^credit_note/(?P<credit_note_id>\d+)[/]?$',             credit_note.detailview,                 name='billing__view_cnote'),
        url(r'^credit_note/(?P<cnote_id>\d+)[/]?$',                   credit_note.CreditNoteDetail.as_view(),   name='billing__view_cnote'),
        url(r'^credit_note/editcomment/(?P<credit_note_id>\d+)[/]?$', credit_note.edit_comment,                 name='billing__edit_cnote_comment'),
        # url(r'^credit_note/add_related_to/(?P<base_id>\d+)[/]?$',     credit_note.link_to_credit_notes,         name='billing__link_to_cnotes'),
        url(r'^credit_note/add_related_to/(?P<base_id>\d+)[/]?$',     credit_note.CreditNotesLinking.as_view(), name='billing__link_to_cnotes'),
        url(r'^credit_note/delete_related/(?P<credit_note_id>\d+)/from/(?P<base_id>\d+)[/]?$',
            credit_note.delete_related_credit_note,
            name='billing__delete_related_cnote',
        ),
    ]

if not billing.template_base_model_is_custom():
    from .views import templatebase

    urlpatterns += [
        url(r'^templates[/]?$',                          templatebase.listview,   name='billing__list_templates'),
        # url(r'^template/edit/(?P<template_id>\d+)[/]?$', templatebase.edit,       name='billing__edit_template'),
        url(r'^template/edit/(?P<template_id>\d+)[/]?$', templatebase.TemplateBaseEdition.as_view(), name='billing__edit_template'),
        # url(r'^template/(?P<template_id>\d+)[/]?$',      templatebase.detailview, name='billing__view_template'),
        url(r'^template/(?P<template_id>\d+)[/]?$',      templatebase.TemplateBaseDetail.as_view(), name='billing__view_template'),
    ]

if not billing.product_line_model_is_custom():
    urlpatterns += [
        url(r'^product_lines[/]?$',                                  line.listview_product_line,     name='billing__list_product_lines'),
        # url(r'^(?P<document_id>\d+)/product_line/add_multiple[/]?$', line.add_multiple_product_line, name='billing__create_product_lines'),
        url(r'^(?P<entity_id>\d+)/product_line/add_multiple[/]?$', line.ProductLinesCreation.as_view(), name='billing__create_product_lines'),
    ]

if not billing.service_line_model_is_custom():
    urlpatterns += [
        url(r'^service_lines[/]?$',                                  line.listview_service_line,     name='billing__list_service_lines'),
        # url(r'^(?P<document_id>\d+)/service_line/add_multiple[/]?$', line.add_multiple_service_line, name='billing__create_service_lines'),
        url(r'^(?P<entity_id>\d+)/service_line/add_multiple[/]?$', line.ServiceLinesCreation.as_view(), name='billing__create_service_lines'),
    ]
