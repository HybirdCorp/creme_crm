# -*- coding: utf-8 -*-

from django.test.client import RequestFactory
from django.urls.base import reverse
from parameterized import parameterized

from creme.creme_core.tests.base import (
    OverrideSettingValueContext,
    skipIfNotInstalled,
)
from creme.mobile import setting_keys
from creme.mobile.templatetags.mobile_tags import (
    mobile_document_class,
    mobile_location_map_url,
)
from creme.mobile.tests.base import MobileBaseTestCase
from creme.persons import get_address_model, get_contact_model

Address = get_address_model()
Contact = get_contact_model()


class MobileTemplatetagsTestCase(MobileBaseTestCase):
    @staticmethod
    def create_address(user):
        return Address.objects.create(
            address='154 hopper avenue',
            zipcode='61045',
            city='Fair Lawn',
            state='New Jersey',
            country='USA',
            owner=Contact.objects.create(
                user=user,
                first_name='Henri',
                last_name='Krinkle'
            )
        )

    @parameterized.expand([
        ('google/maps?q={search}',
         'google/maps?q=154+hopper+avenue+61045+Fair+Lawn'),
        ('google/maps/place?{lat},{lng}', 'google/maps/place?,'),
        ('osm/place?q={search}&mlat={lat}&mlng={lng}',
         'osm/place?q=154+hopper+avenue+61045+Fair+Lawn&mlat=&mlng='),
        ('google/maps', 'google/maps'),
    ])
    @skipIfNotInstalled('creme.geolocation')
    def test_mobile_location_map_url(self, pattern, expected):
        user = self.login()
        address = self.create_address(user)

        with OverrideSettingValueContext(setting_keys.LOCATION_MAP_URL, pattern):
            self.assertEqual(mobile_location_map_url(address), expected)

    @parameterized.expand([
        ('google/maps?q={search}',
         'google/maps?q=154+hopper+avenue+61045+Fair+Lawn'),
        ('google/maps/place?{lat},{lng}', 'google/maps/place?42.33,5.28'),
        ('osm/place?q={search}&mlat={lat}&mlng={lng}',
         'osm/place?q=154+hopper+avenue+61045+Fair+Lawn&mlat=42.33&mlng=5.28'),
        ('google/maps', 'google/maps'),
    ])
    @skipIfNotInstalled('creme.geolocation')
    def test_mobile_location_map_url_geoaddress(self, pattern, expected):
        from creme.geolocation.models import GeoAddress

        user = self.login()
        address = self.create_address(user)

        # address.geoaddress.status = GeoAddress.COMPLETE
        address.geoaddress.status = GeoAddress.Status.COMPLETE
        address.geoaddress.latitude = 42.33
        address.geoaddress.longitude = 5.28
        address.geoaddress.save()

        with OverrideSettingValueContext(setting_keys.LOCATION_MAP_URL, pattern):
            self.assertEqual(mobile_location_map_url(address), expected)

    @parameterized.expand([
        ('Android', 'android'),
        ('Android-10+', 'android'),
        ('Ipad', 'ios'),
        ('IPHONE', 'ios'),
        ('IOS', 'all'),
    ])
    def test_document_class(self, useragent, expected):
        request = RequestFactory().get(reverse('mobile__portal'))
        request.META['HTTP_USER_AGENT'] = useragent

        self.assertEqual(mobile_document_class(request), expected)
