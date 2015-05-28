# -*- coding: utf-8 -*-

from django.conf.urls import patterns, url

from creme.persons import contact_model_is_custom, organisation_model_is_custom

from creme.activities import activity_model_is_custom


urlpatterns = patterns('creme.cti.views',
    (r'^respond_to_a_call$', 'respond_to_a_call'),
)

if not contact_model_is_custom():
    urlpatterns += patterns('creme.cti.views',
        url(r'^contact/add/(?P<number>\w+)$', 'add_contact', name='cti__create_contact'),
    )

if not organisation_model_is_custom():
    urlpatterns += patterns('creme.cti.views',
        url(r'^organisation/add/(?P<number>\w+)$', 'add_orga', name='cti__create_organisation'),
    )

if not activity_model_is_custom():
    urlpatterns += patterns('creme.cti.views',
        url(r'^add_phonecall$',                    'create_phonecall_as_caller', name='cti__create_phonecall_as_caller'),
        url(r'^phonecall/add/(?P<entity_id>\d+)$', 'add_phonecall',              name='cti__create_phonecall'),
    )
