# -*- coding: utf-8 -*-

# from django.conf.urls import url
from django.urls import re_path

from creme.creme_core.conf.urls import Swappable, swap_manager

from creme import persons, activities

from creme.cti import views


urlpatterns = [
    re_path(r'^respond_to_a_call[/]?$',                     views.AnswerToACall.as_view(), name='cti__respond_to_a_call'),
    re_path(r'^bricks/reload/callers/(?P<number>\w+)[/]?$', views.reload_callers_brick,    name='cti__reload_callers_brick'),
]

urlpatterns += swap_manager.add_group(
    persons.contact_model_is_custom,
    Swappable(re_path(r'^contact/add/(?P<number>\w+)[/]?$',
                  views.CTIContactCreation.as_view(),
                  name='cti__create_contact',
                 ),
              check_args=('123',),
             ),
    app_name='cti',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    persons.organisation_model_is_custom,
    Swappable(re_path(r'^organisation/add/(?P<number>\w+)[/]?$',
                  views.CTIOrganisationCreation.as_view(),
                  name='cti__create_organisation',
                 ),
              check_args=('123',),
             ),
    app_name='cti',
).kept_patterns()

urlpatterns += swap_manager.add_group(
    activities.activity_model_is_custom,
    Swappable(re_path(r'^add_phonecall[/]?$',                    views.create_phonecall_as_caller, name='cti__create_phonecall_as_caller')),
    Swappable(re_path(r'^phonecall/add/(?P<entity_id>\d+)[/]?$', views.add_phonecall,              name='cti__create_phonecall'), check_args=Swappable.INT_ID),
    app_name='cti',
).kept_patterns()
