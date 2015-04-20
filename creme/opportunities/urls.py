# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import patterns


urlpatterns = patterns('creme.opportunities.views',
    (r'^$', 'portal.portal'),

    (r'^opportunities$',                           'opportunity.listview'),
    (r'^opportunity/add$',                         'opportunity.add'),
    (r'^opportunity/add_to/(?P<ce_id>\d+)$',       'opportunity.add_to'),
    (r'^opportunity/add_to/(?P<ce_id>\d+)/popup$', 'opportunity.add_to', {'inner_popup': True}),
    (r'^opportunity/edit/(?P<opp_id>\d+)$',        'opportunity.edit'),
    (r'^opportunity/(?P<opp_id>\d+)$',             'opportunity.detailview'),
)

if apps.is_installed('creme.billing'):
    urlpatterns += patterns('creme.opportunities.views.billing',
        (r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)$',                                       'generate_new_doc'),
        (r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/(?P<action>set_current|unset_current)/$', 'current_quote'),
    )
