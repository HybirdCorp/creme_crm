# -*- coding: utf-8 -*-

from django.conf.urls.defaults import patterns


urlpatterns = patterns('opportunities.views',
    (r'^$', 'portal.portal'),

    (r'^opportunities$',                            'opportunity.listview'),
    (r'^opportunity/add$',                          'opportunity.add'),
    (r'^opportunity/add_to_orga/(?P<orga_id>\d+)$', 'opportunity.add_to_orga'),
    (r'^opportunity/edit/(?P<opp_id>\d+)$',         'opportunity.edit'),
    (r'^opportunity/(?P<opp_id>\d+)$',              'opportunity.detailview'),

    (r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)$', 'opportunity.generate_new_doc'),

    (r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/set_current/$', 'links.set_current_quote'),

    (r'^opportunity/(?P<opp_id>\d+)/responsibles/reload/$',        'ajax.reload_responsibles'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/contacts/reload/$',     'ajax.reload_linked_contacts'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/invoices/reload/$',     'ajax.reload_linked_invoices'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/products/reload/$',     'ajax.reload_linked_products'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/services/reload/$',     'ajax.reload_linked_services'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/quotes/reload/$',       'ajax.reload_linked_quotes'),
    (r'^opportunity/(?P<opp_id>\d+)/linked/sales_orders/reload/$', 'ajax.reload_linked_salesorders'),

    (r'^productline/(?P<line_id>\d*)/edit$', 'line.edit_productline'),
    (r'^serviceline/(?P<line_id>\d*)/edit$', 'line.edit_serviceline'),

    (r'^(?P<opp_id>\d*)/product_lines/reload/$', 'line.reload_product_lines'),
    (r'^(?P<opp_id>\d*)/service_lines/reload/$', 'line.reload_service_lines'),
)

urlpatterns += patterns('creme_core.views.generic',
    (r'^opportunity/delete/(?P<object_id>\d+)$',               'delete_entity'),
    (r'^opportunity/delete_js/(?P<entities_ids>([\d]+[,])+)$', 'delete_entities_js'),
)
