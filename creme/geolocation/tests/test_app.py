# -*- coding: utf-8 -*-

from django.urls import reverse

from ..models import Town
from .base import GeoLocationBaseTestCase, Organisation


class GeolocationAppTestCase(GeoLocationBaseTestCase):
    def test_geoaddress_config(self):
        user = self.login()

        town = Town.objects.create(
            name='Marseille', country='FRANCE',
            zipcode='13001', latitude=43.299985, longitude=5.378865,
        )
        orga = Organisation.objects.create(name='Orga 1', user=user)

        address = self.create_address(
            orga,
            address='La Major', zipcode=town.zipcode, town=town.name,
        )
        geo_address = getattr(address, 'geoaddress', None)
        self.assertIsNotNone(geo_address)

        self.assertGET200(reverse(
            'creme_config__model_portal', args=('geolocation', 'geoaddress'),
        ))
        self.assertGET409(reverse(
            'creme_config__create_instance', args=('geolocation', 'geoaddress'),
        ))
        self.assertGET409(reverse(
            'creme_config__edit_instance',
            args=('geolocation', 'geoaddress', geo_address.pk),
        ))
        self.assertGET409(reverse(
            'creme_config__delete_instance',
            args=('geolocation', 'geoaddress', geo_address.pk),
        ))
