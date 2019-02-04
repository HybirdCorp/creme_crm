# -*- coding: utf-8 -*-

from django.apps import apps
from django.conf.urls import url

from creme.creme_core.conf.urls import Swappable, swap_manager

from . import opportunity_model_is_custom
from .views import opportunity


urlpatterns = [

]

urlpatterns += swap_manager.add_group(
    opportunity_model_is_custom,
    # Swappable(url(r'^opportunities[/]?$',   opportunity.listview,                      name='opportunities__list_opportunities')),
    Swappable(url(r'^opportunities[/]?$',   opportunity.OpportunitiesList.as_view(),   name='opportunities__list_opportunities')),
    Swappable(url(r'^opportunity/add[/]?$', opportunity.OpportunityCreation.as_view(), name='opportunities__create_opportunity')),
    Swappable(url(r'^opportunity/add_to/(?P<person_id>\d+)[/]?$',
                  opportunity.RelatedOpportunityCreation.as_view(),
                  name='opportunities__create_related_opportunity',
                 ),
              check_args=Swappable.INT_ID,
             ),
    Swappable(url(r'^opportunity/add_to/(?P<person_id>\d+)/popup[/]?$',
                  opportunity.RelatedOpportunityCreationPopup.as_view(),
                  name='opportunities__create_related_opportunity_popup',
                 ),
              check_args=Swappable.INT_ID,
             ),
    Swappable(url(r'^opportunity/edit/(?P<opp_id>\d+)[/]?$', opportunity.OpportunityEdition.as_view(), name='opportunities__edit_opportunity'), check_args=Swappable.INT_ID),
    Swappable(url(r'^opportunity/(?P<opp_id>\d+)[/]?$',      opportunity.OpportunityDetail.as_view(),  name='opportunities__view_opportunity'), check_args=Swappable.INT_ID),
    app_name='opportunities',
).kept_patterns()

if apps.is_installed('creme.billing'):
    from .views import billing

    urlpatterns += [
        url(r'^opportunity/generate_new_doc/(?P<opp_id>\d+)/(?P<ct_id>\d+)[/]?$',
            billing.generate_new_doc, name='opportunities__generate_billing_doc',
           ),
        url(r'^opportunity/(?P<opp_id>\d+)/linked/quote/(?P<quote_id>\d+)/(?P<action>set_current|unset_current)[/]?$',
            billing.current_quote, name='opportunities__linked_quote_is_current',
           ),
    ]
