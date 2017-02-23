# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import url

from . import opportunity_model_is_custom
from .views import portal


urlpatterns = [
    url(r'^$', portal.portal, name='opportunities__portal'),
]

if not opportunity_model_is_custom():
    from .views import opportunity

    urlpatterns += [
        url(r'^opportunities$',                           opportunity.listview, name='opportunities__list_opportunities'),
        url(r'^opportunity/add$',                         opportunity.add,      name='opportunities__create_opportunity'),
        url(r'^opportunity/add_to/(?P<ce_id>\d+)$',       opportunity.add_to,   name='opportunities__create_related_opportunity'),
        url(r'^opportunity/add_to/(?P<ce_id>\d+)/popup$', opportunity.add_to, {'inner_popup': True},
            name='opportunities__create_related_opportunity_popup',
           ),
        url(r'^opportunity/edit/(?P<opp_id>\d+)$',        opportunity.edit,       name='opportunities__edit_opportunity'),
        url(r'^opportunity/(?P<opp_id>\d+)$',             opportunity.detailview, name='opportunities__view_opportunity'),
    ]

if apps.is_installed('creme.billing'):
    from .views import billing

    urlpatterns += [
        url(r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)$',
            billing.generate_new_doc, name='opportunities__generate_billing_doc',
           ),
        url(r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/(?P<action>set_current|unset_current)/$',
            billing.current_quote, name='opportunities__linked_quote_is_current',
           ),
    ]
