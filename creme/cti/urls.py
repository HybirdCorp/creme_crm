# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.persons import contact_model_is_custom, organisation_model_is_custom

from creme.activities import activity_model_is_custom

from creme.cti import views


urlpatterns = [
    url(r'^respond_to_a_call$', views.respond_to_a_call),
]

if not contact_model_is_custom():
    urlpatterns += [
        url(r'^contact/add/(?P<number>\w+)$', views.add_contact, name='cti__create_contact'),
    ]

if not organisation_model_is_custom():
    urlpatterns += [
        url(r'^organisation/add/(?P<number>\w+)$', views.add_orga, name='cti__create_organisation'),
    ]

if not activity_model_is_custom():
    urlpatterns += [
        url(r'^add_phonecall$',                    views.create_phonecall_as_caller, name='cti__create_phonecall_as_caller'),
        url(r'^phonecall/add/(?P<entity_id>\d+)$', views.add_phonecall,              name='cti__create_phonecall'),
    ]
