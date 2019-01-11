# -*- coding: utf-8 -*-

from django.conf.urls import url

from creme.geolocation import views


urlpatterns = [
    url(r'^set_address_info[/]?$', views.set_address_info, name='geolocation__set_address_info'),
    url(r'^get_addresses[/]?$', views.get_addresses_from_filter, name='geolocation__addresses'),
    url(r'^get_neighbours[/]?$', views.get_neighbours, name='geolocation__neighbours'),
]
