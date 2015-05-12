# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import patterns, url

from . import opportunity_model_is_custom


urlpatterns = patterns('creme.opportunities.views',
    (r'^$', 'portal.portal'),
)

if not opportunity_model_is_custom():
    urlpatterns += patterns('creme.opportunities.views.opportunity',
        url(r'^opportunities$',                           'listview', name='opportunities__list_opportunities'),
        url(r'^opportunity/add$',                         'add',      name='opportunities__create_opportunity'),
        url(r'^opportunity/add_to/(?P<ce_id>\d+)$',       'add_to',   name='opportunities__create_related_opportunity'),
        url(r'^opportunity/add_to/(?P<ce_id>\d+)/popup$', 'add_to', {'inner_popup': True},
            name='opportunities__create_related_opportunity_popup',
           ),
        url(r'^opportunity/edit/(?P<opp_id>\d+)$',        'edit',       name='opportunities__edit_opportunity'),
        url(r'^opportunity/(?P<opp_id>\d+)$',             'detailview', name='opportunities__view_opportunity'),
    )

if apps.is_installed('creme.billing'):
    urlpatterns += patterns('creme.opportunities.views.billing',
        (r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)$',                                       'generate_new_doc'),
        (r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/(?P<action>set_current|unset_current)/$', 'current_quote'),
    )
