from functools import partial

from django.utils.translation import gettext as _

from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..models import GeoAddress, Town
from .base import Address, Contact, GeoLocationBaseTestCase, Organisation


@skipIfCustomOrganisation
@skipIfCustomAddress
class GeoLocationModelsTestCase(GeoLocationBaseTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = cls.create_user()

    def setUp(self):
        super().setUp()

        create_town = partial(Town.objects.create, name='Marseille', country='FRANCE')
        self.marseille1 = create_town(zipcode='13001', latitude=43.299985, longitude=5.378865)
        self.marseille2 = create_town(zipcode='13002', latitude=43.298642, longitude=5.364956)
        self.aubagne    = create_town(
            zipcode='13400', latitude=43.2833, longitude=5.56667, name='Aubagne',
        )

        self.orga = Organisation.objects.create(name='Orga 1', user=self.user)

    def test_create(self):
        town = self.marseille2
        address = self.create_address(
            self.orga,
            address='La Major', zipcode=town.zipcode, town=town.name,
        )

        with self.assertNoException():
            geoaddress = address.geoaddress

        self.assertGeoAddress(
            geoaddress,
            address=address,
            latitude=town.latitude, longitude=town.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

    def test_cache(self):
        town = self.marseille2
        address = self.create_address(
            self.orga,
            address='La Major', zipcode=town.zipcode, town=town.name,
        )

        with self.assertNumQueries(0):
            _ = address.geoaddress

    def test_create_empty_address(self):
        address = Address.objects.create(owner=self.orga)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_create_zipcode(self):
        town1 = self.marseille2
        create_address = partial(Address.objects.create, owner=self.orga)
        address = create_address(zipcode=town1.zipcode)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        town2 = self.aubagne
        address = create_address(zipcode=town2.zipcode)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

    def test_create_zipcode_duplicate_towns(self):
        town1 = self.marseille1
        town2 = self.marseille2
        town3 = self.aubagne

        zipcode = '13000'

        create_town = partial(Town.objects.create, zipcode=zipcode, country='FRANCE')
        create_town(name=town1.name, latitude=town1.latitude, longitude=town1.longitude)
        create_town(name=town2.name, latitude=town3.latitude, longitude=town3.longitude)
        town6 = create_town(
            name=town2.name + ' Bis', latitude=town2.latitude, longitude=town2.longitude,
        )

        # duplicates zipcode, no names, no geoaddress
        create_address = partial(Address.objects.create, owner=self.orga, zipcode=zipcode)
        address = create_address()
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

        # duplicates zipcode, names => Marseille Bis
        address = create_address(city=town6.name)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town6.latitude, longitude=town6.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        # duplicates zipcode, duplicate names => First one
        address = create_address(city=town1.name)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

    def test_create_unknown_zipcode(self):
        address = Address.objects.create(owner=self.orga, zipcode='12100')
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_create_city(self):
        town1 = self.marseille1
        create_address = partial(Address.objects.create, owner=self.orga)
        address = create_address(city=town1.name)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        town2 = self.aubagne
        address = create_address(city=town2.name)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

    def test_create_unknown_city(self):
        address = Address.objects.create(owner=self.orga, city='Unknown')
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_update_city(self):
        town1 = self.marseille1
        address = Address.objects.create(owner=self.orga, city=town1.name)
        self.assertGeoAddress(
            address.geoaddress,
            address_id=address.pk,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        town2 = self.aubagne
        address.city = town2.name
        address.save()

        self.assertGeoAddress(
            address.geoaddress,
            address_id=address.pk,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

    def test_update_unknown_city(self):
        town = self.marseille1
        address = Address.objects.create(owner=self.orga, city=town.name)
        self.assertGeoAddress(
            address.geoaddress,
            address_id=address.pk,
            latitude=town.latitude, longitude=town.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address.city = 'Not a city'
        address.save()

        self.assertGeoAddress(
            address.geoaddress,
            address_id=address.pk,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_populate_address(self):
        town = self.marseille2

        create_address = partial(Address.objects.create, owner=self.orga, address='La Major')
        address = create_address(zipcode=town.zipcode, city=town.name)
        address_no_town = create_address()

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)
        address = self.refresh(address)
        address_no_town = self.refresh(address_no_town)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress  # NOQA

        GeoAddress.populate_geoaddress(address)

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town.latitude, longitude=town.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        GeoAddress.populate_geoaddress(address_no_town)

        self.assertEqual(GeoAddress.objects.count(), 2)
        self.assertGeoAddress(
            address_no_town.geoaddress,
            address=address_no_town,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_populate_address_no_town(self):
        address = Address.objects.create(owner=self.orga, address='La Major')

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)
        address = self.refresh(address)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress  # NOQA

        GeoAddress.populate_geoaddress(address)

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_populate_addresses(self):
        town1 = self.marseille1
        town2 = self.marseille2
        town3 = self.aubagne

        create_address = partial(Address.objects.create, owner=self.orga, address='Mairie')
        addresses = [
            create_address(address='La Major', zipcode=town2.zipcode, city=town2.name),
            create_address(zipcode=town1.zipcode, city=town1.name),
            create_address(zipcode=town3.zipcode),
            create_address(city=town1.name),
            create_address(),
        ]

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)
        addresses = [self.refresh(address) for address in addresses]

        GeoAddress.populate_geoaddresses(addresses)

        self.assertEqual(GeoAddress.objects.count(), 5)
        addresses = Address.objects.all()

        address = addresses[0]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[1]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[2]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town3.latitude, longitude=town3.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[3]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )  # 13001 first

        address = addresses[4]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

        GeoAddress.populate_geoaddresses(addresses)
        self.assertEqual(GeoAddress.objects.count(), 5)

    def test_populate_addresses_update(self):
        town1 = self.marseille1
        town2 = self.marseille2
        town3 = self.aubagne

        create_address = partial(Address.objects.create, owner=self.orga, address='Mairie')
        addresses = [
            create_address(zipcode=town2.zipcode, city=town2.name, address='La Major'),
            create_address(zipcode=town1.zipcode, city=town1.name),
            create_address(zipcode=town3.zipcode),
            create_address(city=town1.name),
            create_address(),
        ]

        # 4th address
        GeoAddress.objects.filter(
            latitude=self.marseille1.latitude,
        ).update(latitude=None, longitude=None)

        addresses = [self.refresh(address) for address in addresses]

        self.assertEqual(GeoAddress.objects.count(), 5)
        address = addresses[0]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[1]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[2]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town3.latitude, longitude=town3.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[3]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )  # invalid status

        address = addresses[4]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

        GeoAddress.populate_geoaddresses(addresses)

        self.assertEqual(GeoAddress.objects.count(), 5)
        addresses = Address.objects.all()

        address = addresses[0]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town2.latitude, longitude=town2.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        # updated !
        address = addresses[1]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        address = addresses[2]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town3.latitude, longitude=town3.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )

        # updated !
        address = addresses[3]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=town1.latitude, longitude=town1.longitude,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.PARTIAL,
        )  # 13001 first

        address = addresses[4]
        self.assertGeoAddress(
            address.geoaddress,
            address=address,
            latitude=None, longitude=None,
            draggable=True, geocoded=False,
            status=GeoAddress.Status.UNDEFINED,
        )

    def test_dispose_on_address_delete(self):
        town = self.marseille2
        address = Address.objects.create(
            owner=self.orga,
            address='La Major', zipcode=town.zipcode, city=town.name,
        )

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertIsNotNone(address.geoaddress)

        address.delete()
        self.assertEqual(GeoAddress.objects.count(), 0)

    def test_dispose_on_address_delete_no_geoaddress(self):
        town = self.marseille2
        address = Address.objects.create(
            owner=self.orga,
            address='La Major', zipcode=town.zipcode, city=town.name,
        )

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)
        address = self.refresh(address)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress  # NOQA

        address.delete()
        self.assertEqual(GeoAddress.objects.count(), 0)

    def test_status_label(self):
        geoaddress = Address.objects.create(owner=self.orga, city=self.marseille1.name).geoaddress
        self.assertGeoAddress(geoaddress, status=GeoAddress.Status.PARTIAL)
        self.assertEqual(
            geoaddress.get_status_display(), _('Partially matching location'),
        )

        geoaddress.status = GeoAddress.Status.UNDEFINED
        self.assertEqual(
            geoaddress.get_status_display(), _('Not localized'),
        )

        geoaddress.status = GeoAddress.Status.COMPLETE
        self.assertEqual(geoaddress.get_status_display(), '')

        geoaddress.status = GeoAddress.Status.MANUAL
        self.assertEqual(geoaddress.get_status_display(), _('Manual location'))

    @skipIfCustomContact
    def test_neighbours(self):
        user = self.user
        contact = Contact.objects.create(last_name='Contact 1', user=user)
        orga2   = Organisation.objects.create(name='Orga 2', user=user)

        town1 = self.marseille1
        town2 = self.aubagne

        create_address = self.create_address
        ST_VICTOR   = create_address(
            self.orga, address='St Victor', zipcode='13007', town=town1.name,
            geoloc=(43.290347, 5.365572),
        )
        COMMANDERIE = create_address(
            contact, address='Commanderie', zipcode='13011', town=town1.name,
            geoloc=(43.301963, 5.462410),
        )
        AUBAGNE = create_address(
            orga2, address='Maire Aubagne', zipcode=town2.zipcode, town=town2.name,
            geoloc=(43.295783, 5.565589),
        )

        self.assertFalse(ST_VICTOR.geoaddress.neighbours(distance=1000))
        self.assertListEqual(
            [*ST_VICTOR.geoaddress.neighbours(distance=10000)],
            [COMMANDERIE.geoaddress],
        )

        self.assertFalse(COMMANDERIE.geoaddress.neighbours(distance=1000))
        self.assertListEqual(
            [*COMMANDERIE.geoaddress.neighbours(distance=10000)],
            [ST_VICTOR.geoaddress, AUBAGNE.geoaddress],
        )

    @skipIfCustomContact
    def test_neighbours_with_same_owner(self):
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)

        town1 = self.marseille1
        town2 = self.aubagne

        create_address = self.create_address
        ST_VICTOR = create_address(
            self.orga, address='St Victor', zipcode='13007', town=town1.name,
            geoloc=(43.290347, 5.365572),
        )
        COMMANDERIE = create_address(
            contact, address='Commanderie', zipcode='13011', town=town1.name,
            geoloc=(43.301963, 5.462410),
        )
        create_address(
            contact, address='Maire Aubagne', zipcode=town2.zipcode, town=town2.name,
            geoloc=(43.295783, 5.565589),
        )

        self.assertFalse(ST_VICTOR.geoaddress.neighbours(distance=1000))
        self.assertListEqual(
            [*ST_VICTOR.geoaddress.neighbours(distance=10000)],
            [COMMANDERIE.geoaddress],
        )

        self.assertFalse(COMMANDERIE.geoaddress.neighbours(distance=1000))
        self.assertListEqual(
            [*COMMANDERIE.geoaddress.neighbours(distance=10000)],
            [ST_VICTOR.geoaddress],
        )  # ignore aubagne, same owner !

    @skipIfCustomContact
    def test_neighbours_with_empty_coordinates(self):
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)
        town = self.marseille1

        create_address = self.create_address
        create_address(
            self.orga, address='St Victor', zipcode='13007', town=town.name,
            geoloc=(43.290347, 5.365572),
        )
        create_address(
            contact, address='Commanderie', zipcode='13011', town=town.name,
            geoloc=(43.301963, 5.462410),
        )

        address = create_address(contact, address='Maire Aubagne', zipcode='0', town='Unknown')
        GeoAddress.populate_geoaddress(address)

        self.assertTupleEqual(
            (None, None),
            (address.geoaddress.latitude, address.geoaddress.longitude),
        )

        self.assertFalse(address.geoaddress.neighbours(distance=1000))
        self.assertFalse(address.geoaddress.neighbours(distance=10000))

    def test_town_unicode(self):
        self.assertEqual('13001 Marseille FRANCE', str(self.marseille1))
        self.assertEqual('13002 Marseille FRANCE', str(self.marseille2))

    def test_town_search(self):
        town1 = self.marseille1
        town2 = self.marseille2
        town3 = self.aubagne

        create_address = partial(Address.objects.create, owner=self.orga, address='Mairie')
        self.assertEqual(
            town2,
            Town.search(
                create_address(address='La Major', zipcode=town2.zipcode, city=town2.name)
            )
        )

        self.assertEqual(
            town1,
            Town.search(create_address(zipcode=town1.zipcode, city=town1.name))
        )

        self.assertEqual(
            Town.objects.get(zipcode=town3.zipcode),
            Town.search(create_address(zipcode=town3.zipcode)),
        )

        # zipcode has priority on city name.
        self.assertEqual(
            Town.objects.get(zipcode=town3.zipcode),
            Town.search(create_address(zipcode=town3.zipcode, city=town1.name)),
        )

        self.assertEqual(town1, Town.search(create_address(city=town1.name)))

        self.assertIsNone(Town.search(create_address()))
        self.assertIsNone(Town.search(create_address(zipcode='unknown')))
        self.assertIsNone(Town.search(create_address(city='unknown')))

    def test_town_search_all(self):
        town1 = self.marseille1
        town2 = self.marseille2
        town3 = self.aubagne

        create_address = partial(Address.objects.create, owner=self.orga, address='Mairie')
        addresses = [
            create_address(address='La Major', zipcode=town2.zipcode, city=town2.name),
            create_address(zipcode=town1.zipcode, city=town1.name),
            create_address(zipcode=town3.zipcode),
            create_address(zipcode=town3.zipcode, city=town1.name),
            create_address(),
            create_address(zipcode='unknown'),
            create_address(city=town1.name),
            create_address(city='unknown'),
        ]

        self.assertListEqual(
            [town2, town1, town3, town3, None, None, town1, None],
            [*Town.search_all(addresses)],
        )
