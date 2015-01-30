# -*- coding: utf-8 -*-

from django.conf.urls import patterns


urlpatterns = patterns('creme.geolocation.views',
    (r'^set_address_info/(?P<address_id>\d+)$', 'set_address_info'),
    (r'^get_addresses_from_filter/(?P<filter_id>[\w-]*)$', 'get_addresses_from_filter'),
    (r'^get_neighbours/(?P<address_id>\d+)/(?P<filter_id>[\w-]*)$', 'get_neighbours'),
)
