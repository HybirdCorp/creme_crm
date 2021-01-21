# -*- coding: utf-8 -*-

from django.urls import re_path

from creme.geolocation import views

urlpatterns = [
    re_path(
        r'^set_address_info[/]?$',
        views.AddressInfoSetting.as_view(),
        name='geolocation__set_address_info',
    ),
    re_path(
        r'^get_addresses[/]?$',
        views.AddressesInformation.as_view(),
        name='geolocation__addresses',
    ),
    re_path(
        r'^get_neighbours[/]?$',
        views.NeighboursInformation.as_view(),
        name='geolocation__neighbours',
    ),
]
