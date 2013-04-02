# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.opportunities.views',
    (r'^$', 'portal.portal'),

    (r'^opportunities$',                           'opportunity.listview'),
    (r'^opportunity/add$',                         'opportunity.add'),
    (r'^opportunity/add_to/(?P<ce_id>\d+)$',       'opportunity.add_to'),
    (r'^opportunity/add_to/(?P<ce_id>\d+)/popup$', 'opportunity.add_to', {'inner_popup': True}),
    (r'^opportunity/edit/(?P<opp_id>\d+)$',        'opportunity.edit'),
    (r'^opportunity/(?P<opp_id>\d+)$',             'opportunity.detailview'),

    (r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)$', 'opportunity.generate_new_doc'),

    (r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/set_current/$', 'links.set_current_quote'),
)
