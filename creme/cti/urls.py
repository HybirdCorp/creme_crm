# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme import persons, activities

from creme.cti import views


urlpatterns = [
    url(r'^respond_to_a_call[/]?$',                     views.respond_to_a_call,    name='cti__respond_to_a_call'),
    url(r'^bricks/reload/callers/(?P<number>\w+)[/]?$', views.reload_callers_brick, name='cti__reload_callers_brick'),
]

if not persons.contact_model_is_custom():
    urlpatterns += [
        # url(r'^contact/add/(?P<number>\w+)[/]?$', views.add_contact, name='cti__create_contact'),
        url(r'^contact/add/(?P<number>\w+)[/]?$', views.CTIContactCreation.as_view(), name='cti__create_contact'),
    ]

if not persons.organisation_model_is_custom():
    urlpatterns += [
        # url(r'^organisation/add/(?P<number>\w+)[/]?$', views.add_orga, name='cti__create_organisation'),
        url(r'^organisation/add/(?P<number>\w+)[/]?$', views.CTIOrganisationCreation.as_view(), name='cti__create_organisation'),
    ]

if not activities.activity_model_is_custom():
    urlpatterns += [
        url(r'^add_phonecall[/]?$',                    views.create_phonecall_as_caller, name='cti__create_phonecall_as_caller'),
        url(r'^phonecall/add/(?P<entity_id>\d+)[/]?$', views.add_phonecall,              name='cti__create_phonecall'),
    ]
