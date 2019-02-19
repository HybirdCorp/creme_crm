# -*- coding: utf-8 -*-

from django.urls import re_path

from creme.geolocation import views


urlpatterns = [
    re_path(r'^set_address_info[/]?$', views.set_address_info, name='geolocation__set_address_info'),
    re_path(r'^get_addresses[/]?$', views.get_addresses_from_filter, name='geolocation__addresses'),
    re_path(r'^get_neighbours[/]?$', views.get_neighbours, name='geolocation__neighbours'),
]
