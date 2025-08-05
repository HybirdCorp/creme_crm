from django.conf import settings
from django.utils.translation import gettext as _

from creme.creme_core.tests.base import OverrideSettingValueContext
from creme.geolocation.utils import get_openstreetmap_settings
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import constants, setting_keys
from ..models import GeoAddress
from ..utils import (
    address_as_dict,
    addresses_from_persons,
    get_google_api_key,
    get_radius,
    location_bounding_box,
    use_entity_icon,
)
from .base import Address, Contact, GeoLocationBaseTestCase, Organisation


class GeoLocationUtilsTestCase(GeoLocationBaseTestCase):
    @skipIfCustomOrganisation
    @skipIfCustomAddress
    @OverrideSettingValueContext(setting_keys.use_entity_icon_key, False)
    def test_address_as_dict(self):
        user = self.get_root_user()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(
            orga, zipcode='13012', town='Marseille', geoloc=(43.299991, 5.364832),
        )

        self.assertDictEqual(
            {
                'id': address.pk,
                'content': '27 bis rue du yahourt 13012 Marseille 13',
                'title': '27 bis rue du yahourt',
                'owner': 'Orga 1',
                'is_shipping': False,
                'is_billing': False,
                'is_complete': True,
                'latitude': 43.299991,
                'longitude': 5.364832,
                'draggable': True,
                'geocoded': False,
                'status_label': '',
                'status': GeoAddress.Status.COMPLETE,
                'url': orga.get_absolute_url(),
                'icon': None,
            },
            address_as_dict(address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    @OverrideSettingValueContext(setting_keys.use_entity_icon_key, False)
    def test_address_as_dict_empty_billing_shipping(self):
        user = self.get_root_user()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_billing_address(
            orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832),
        )

        self.assertDictEqual(
            {
                'id': address.pk,
                'content': '',
                'title': _('Billing address'),
                'owner': 'Orga 1',
                'is_shipping': False,
                'is_billing': True,
                'is_complete': True,
                'latitude': 43.299991,
                'longitude': 5.364832,
                'draggable': True,
                'geocoded': False,
                'status_label': '',
                'status': GeoAddress.Status.COMPLETE,
                'url': orga.get_absolute_url(),
                'icon': None,
            },
            address_as_dict(address),
        )

        address = self.create_shipping_address(
            orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832),
        )

        self.assertDictEqual(
            {
                'id': address.id,
                'content': '',
                'title': _('Shipping address'),
                'owner': 'Orga 1',
                'is_shipping': True,
                'is_complete': True,
                'is_billing': False,
                'latitude': 43.299991,
                'longitude': 5.364832,
                'draggable': True,
                'geocoded': False,
                'status_label': '',
                'status': GeoAddress.Status.COMPLETE,
                'url': orga.get_absolute_url(),
                'icon': None,
            },
            address_as_dict(address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    @OverrideSettingValueContext(setting_keys.use_entity_icon_key, False)
    def test_address_as_dict_empty(self):
        user = self.get_root_user()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(
            orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832),
        )

        self.assertDictEqual(
            {
                'id': address.pk,
                'content': '',
                'title': '',
                'owner': 'Orga 1',
                'is_shipping': False,
                'is_billing': False,
                'is_complete': True,
                'latitude': 43.299991,
                'longitude': 5.364832,
                'draggable': True,
                'geocoded': False,
                'status_label': '',
                'status': GeoAddress.Status.COMPLETE,
                'url': orga.get_absolute_url(),
                'icon': None
            },
            address_as_dict(address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    @OverrideSettingValueContext(setting_keys.use_entity_icon_key, False)
    def test_address_as_dict_missing_geoaddress01(self):
        user = self.get_root_user()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(
            orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832),
        )
        GeoAddress.objects.filter(address=address).delete()

        address = self.refresh(address)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        self.assertDictEqual(
            {
                'id': address.pk,
                'content': '',
                'title': '',
                'owner': 'Orga 1',
                'is_shipping': False,
                'is_billing': False,
                'is_complete': False,
                'latitude': None,
                'longitude': None,
                'draggable': True,
                'geocoded': False,
                'status_label': _('Not localized'),
                'status': GeoAddress.Status.UNDEFINED,
                'url': orga.get_absolute_url(),
                'icon': None,
            },
            address_as_dict(address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    @OverrideSettingValueContext(setting_keys.use_entity_icon_key, False)
    def test_address_as_dict_missing_geoaddress02(self):
        "With select_related."
        user = self.get_root_user()

        orga = Organisation.objects.create(name='Orga 1', user=user)
        address = self.create_address(
            orga, address='', zipcode='', town='', geoloc=(43.299991, 5.364832),
        )
        GeoAddress.objects.filter(address=address).delete()
        address = Address.objects.select_related('geoaddress').get(pk=address.pk)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        self.assertDictEqual(
            {
                'id': address.pk,
                'content': '',
                'title': '',
                'owner': 'Orga 1',
                'is_shipping': False,
                'is_billing': False,
                'is_complete': False,
                'latitude': None,
                'longitude': None,
                'draggable': True,
                'geocoded': False,
                'status_label': _('Not localized'),
                'status': GeoAddress.Status.UNDEFINED,
                'url': orga.get_absolute_url(),
                'icon': None,
            },
            address_as_dict(address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomContact
    def test_addresses_from_persons(self):
        user = self.get_root_user()

        orga1 = Organisation.objects.create(name='Orga 1', user=user)
        orga2 = Organisation.objects.create(name='Orga 2', user=user)
        contact = Contact.objects.create(last_name='Contact 1', user=user)

        orga_address = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        self.create_shipping_address(orga1, zipcode='01190', town='Ozan')
        self.create_address(orga1, zipcode='01630', town='Péron')

        orga2_address = self.create_shipping_address(orga2, zipcode='01190', town='Ozan')
        self.create_address(orga2, zipcode='01630', town='Péron')

        contact_address = self.create_address(contact, zipcode='01630', town='Péron')
        self.assertListEqual(
            [*addresses_from_persons(Contact.objects.all(), user)],
            [contact_address],
        )

        self.assertListEqual(
            sorted(
                [*addresses_from_persons(Organisation.objects.all(), user)],
                key=lambda a: a.pk
            ),
            sorted([orga_address, orga2_address], key=lambda a: a.pk),
        )

    def test_get_radius(self):
        self.assertEqual(get_radius(), constants.DEFAULT_SEPARATING_NEIGHBOURS)

        with OverrideSettingValueContext(setting_keys.neighbourhood_distance_key, 12500):
            self.assertEqual(get_radius(), 12500)

    # def test_get_radius__deprecated(self):
    #     self.assertEqual(get_radius(), constants.DEFAULT_SEPARATING_NEIGHBOURS)
    #
    #     with OverrideSettingValueContext(setting_keys.NEIGHBOURHOOD_DISTANCE, 12500):
    #         self.assertEqual(get_radius(), 12500)

    def test_get_google_api_key(self):
        self.assertEqual(get_google_api_key(), '')

        with OverrideSettingValueContext(setting_keys.google_api_key, 'thegoldenticket'):
            self.assertEqual(get_google_api_key(), 'thegoldenticket')

    # def test_get_google_api_key__deprecated(self):
    #     self.assertEqual(get_google_api_key(), '')
    #
    #     with OverrideSettingValueContext(setting_keys.GOOGLE_API_KEY, 'thegoldenticket'):
    #         self.assertEqual(get_google_api_key(), 'thegoldenticket')

    def test_use_entity_icon_key(self):
        self.assertEqual(use_entity_icon(), False)

        with OverrideSettingValueContext(setting_keys.use_entity_icon_key, True):
            self.assertEqual(use_entity_icon(), True)

    def test_get_openstreetmap_settings(self):
        self.assertDictEqual(
            {
                'nominatim_url': settings.GEOLOCATION_OSM_NOMINATIM_URL,
                'tilemap_url': settings.GEOLOCATION_OSM_TILEMAP_URL,
                'copyright_url': settings.GEOLOCATION_OSM_COPYRIGHT_URL,
                'copyright_title': settings.GEOLOCATION_OSM_COPYRIGHT_TITLE,
            },
            get_openstreetmap_settings(),
        )

        tilemap_url = '{s}othermap.com/{x}/{y}/{z}.jpeg'
        copyright_url = '{s}othermap.com/copyright'

        with self.settings(
            GEOLOCATION_OSM_NOMINATIM_URL='',
            GEOLOCATION_OSM_TILEMAP_URL=tilemap_url,
            GEOLOCATION_OSM_COPYRIGHT_URL=copyright_url,
        ):
            self.assertDictEqual(
                {
                    'nominatim_url': '',
                    'tilemap_url': tilemap_url,
                    'copyright_url': copyright_url,
                    'copyright_title': settings.GEOLOCATION_OSM_COPYRIGHT_TITLE,
                },
                get_openstreetmap_settings(),
            )

    def test_location_bounding_box(self):
        # 10 km ~ 0.09046499004885108 lat, 0.12704038469036066 long (for 45° lat)
        self.assertTupleEqual(
            (
                (45.0 - 0.09046499004885108, 5.0 - 0.12704038469036066),
                (45.0 + 0.09046499004885108, 5.0 + 0.12704038469036066),
            ),
            location_bounding_box(45.0, 5.0, 10000),
        )

        # 10 km ~ 0.09046499004885108 lat, 0.09559627851921597 long (for 20° lat)
        self.assertTupleEqual(
            (
                (20.0 - 0.09046499004885108, 5.0 - 0.09559627851921597),
                (20.0 + 0.09046499004885108, 5.0 + 0.09559627851921597),
            ),
            location_bounding_box(20.0, 5.0, 10000),
        )
