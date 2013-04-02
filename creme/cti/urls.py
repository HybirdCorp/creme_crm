# -*- coding: utf-8 -*-

from django.conf.urls import patterns

urlpatterns = patterns('creme.cti.views',
    (r'^add_phonecall$',                    'create_phonecall_as_caller'),
    (r'^respond_to_a_call$',                'respond_to_a_call'),

    (r'^phonecall/add/(?P<entity_id>\d+)$', 'add_phonecall'),
    (r'^contact/add/(?P<number>\w+)$',      'add_contact'),
    (r'^organisation/add/(?P<number>\w+)$', 'add_orga'),
)
