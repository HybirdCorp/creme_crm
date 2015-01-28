# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _

    from creme.persons.models import Address, Organisation, Contact

    from ..models import GeoAddress, Town
    from .base import GeoLocationBaseTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

__all__ = ('GeoLocationModelsTestCase',)


create_town = Town.objects.create
create_address = Address.objects.create

class GeoLocationModelsTestCase(GeoLocationBaseTestCase):
    def setUp(self):
        self.login()

        self.marseille1 = create_town(name='Marseille', zipcode='13001', country='FRANCE', latitude=43.299985, longitude=5.378865)
        self.marseille2 = create_town(name='Marseille', zipcode='13002', country='FRANCE', latitude=43.298642, longitude=5.364956)

        self.aubagne = create_town(name='Aubagne', zipcode='13400', country='FRANCE', latitude=43.2833, longitude=5.56667)

        self.orga = Organisation.objects.create(name='Orga 1', user=self.user)

    def test_create(self):
        address = self.create_address(self.orga,  address='La Major', zipcode='13002', town=u'Marseille')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

    def test_create_empty_address(self):
        address = create_address(owner=self.orga)
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_create_zipcode(self):
        address = create_address(owner=self.orga, zipcode='13002')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = create_address(owner=self.orga, zipcode='13400')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

    def test_create_zipcode_duplicate_towns(self):
        create_town(name='Marseille', zipcode='13000', country='FRANCE', latitude=43.299985, longitude=5.378865)
        create_town(name='Marseille Bis', zipcode='13000', country='FRANCE', latitude=43.298642, longitude=5.364956)
        create_town(name='Marseille', zipcode='13000', country='FRANCE', latitude=43.2833, longitude=5.56667)

        # duplicates zipcode, no names, no geoaddres
        address = create_address(owner=self.orga, zipcode='13000')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

        # duplicates zipcode, names => Marseille Bis
        address = create_address(owner=self.orga, zipcode='13000', city='Marseille Bis')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        # duplicates zipcode, duplicate names => First one
        address = create_address(owner=self.orga, zipcode='13000', city='Marseille')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

    def test_create_unknown_zipcode(self):
        address = create_address(owner=self.orga, zipcode='12100')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_create_city(self):
        address = create_address(owner=self.orga, city='Marseille')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = create_address(owner=self.orga, city='Aubagne')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

    def test_create_unknown_city(self):
        address = create_address(owner=self.orga, city='Unknown')
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_update_city(self):
        address = create_address(owner=self.orga, city='Marseille')
        self.assertGeoAddress(address.geoaddress, address_id=address.pk, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address.city = 'Aubagne'
        address.save()

        self.assertGeoAddress(address.geoaddress, address_id=address.pk, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

    def test_update_unkown_city(self):
        address = create_address(owner=self.orga, city='Marseille')
        self.assertGeoAddress(address.geoaddress, address_id=address.pk, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address.city = 'Not a city'
        address.save()

        self.assertGeoAddress(address.geoaddress, address_id=address.pk, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_populate_address(self):
        address = create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille')
        address_no_town = create_address(owner=self.orga, address='La Major')

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        GeoAddress.populate_geoaddress(address)

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        GeoAddress.populate_geoaddress(address_no_town)

        self.assertEqual(GeoAddress.objects.count(), 2)
        self.assertGeoAddress(address_no_town.geoaddress, address=address_no_town, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_populate_address_no_town(self):
        address = create_address(owner=self.orga, address='La Major')

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        GeoAddress.populate_geoaddress(address)

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_populate_addresses(self):
        addresses = [create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13001', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13400'),
                     create_address(owner=self.orga, address='Mairie', city='Marseille'),
                     create_address(owner=self.orga, address='Mairie'),]

        GeoAddress.objects.all().delete()
        self.assertEqual(GeoAddress.objects.count(), 0)

        GeoAddress.populate_geoaddresses(addresses)

        self.assertEqual(GeoAddress.objects.count(), 5)
        addresses = Address.objects.all()

        address = addresses[0]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[1]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[2]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[3]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL) # 13001 first

        address = addresses[4]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

        GeoAddress.populate_geoaddresses(addresses)
        self.assertEqual(GeoAddress.objects.count(), 5)

    def test_populate_addresses_update(self):
        addresses = [create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13001', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13400'),
                     create_address(owner=self.orga, address='Mairie', city='Marseille'),
                     create_address(owner=self.orga, address='Mairie'),]

        GeoAddress.objects.filter(latitude=43.299985).update(latitude=None, longitude=None) # 4th address

        self.assertEqual(GeoAddress.objects.count(), 5)
        address = addresses[0]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[1]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[2]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[3]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL) # invalid status

        address = addresses[4]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

        GeoAddress.populate_geoaddresses(addresses)

        self.assertEqual(GeoAddress.objects.count(), 5)
        addresses = Address.objects.all()

        address = addresses[0]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.298642, longitude=5.364956, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        # updated !
        address = addresses[1]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        address = addresses[2]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.2833, longitude=5.56667, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL)

        # updated !
        address = addresses[3]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=43.299985, longitude=5.378865, draggable=True, geocoded=False,
                              status=GeoAddress.PARTIAL) # 13001 first

        address = addresses[4]
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False,
                              status=GeoAddress.UNDEFINED)

    def test_dispose_on_address_delete(self):
        address = create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille')

        self.assertEqual(GeoAddress.objects.count(), 1)
        self.assertIsNotNone(address.geoaddress)

        address.delete()

        self.assertEqual(GeoAddress.objects.count(), 0)

    def test_dispose_on_address_delete_no_geoaddress(self):
        address = create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille')

        GeoAddress.objects.all().delete()

        self.assertEqual(GeoAddress.objects.count(), 0)

        with self.assertRaises(GeoAddress.DoesNotExist):
            address.geoaddress

        address.delete()

        self.assertEqual(GeoAddress.objects.count(), 0)

    def test_status_label(self):
        geoaddress = create_address(owner=self.orga, city='Marseille').geoaddress
        self.assertGeoAddress(geoaddress, status=GeoAddress.PARTIAL)
        self.assertEqual(geoaddress.get_status_display(), _('Partially matching location'))

        geoaddress.status = GeoAddress.UNDEFINED
        self.assertEqual(geoaddress.get_status_display(), _('No matching location'))

        geoaddress.status = GeoAddress.COMPLETE
        self.assertEqual(geoaddress.get_status_display(), '')

        geoaddress.status = GeoAddress.MANUAL
        self.assertEqual(geoaddress.get_status_display(), _('Manual location'))

    def test_neighbours(self):
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)
        orga2 = Organisation.objects.create(name='Orga 2', user=self.user)

        ST_VICTOR   = self.create_address(self.orga, address='St Victor', zipcode='13007', town=u'Marseille', geoloc=(43.290347, 5.365572))
        COMMANDERIE = self.create_address(contact, address='Commanderie', zipcode='13011', town=u'Marseille', geoloc=(43.301963, 5.462410))
        AUBAGNE     = self.create_address(orga2, address='Maire Aubagne', zipcode='13400', town=u'Aubagne',   geoloc=(43.295783, 5.565589))

        self.assertListEqual(list(ST_VICTOR.geoaddress.neighbours(distance=1000)), [])
        self.assertListEqual(list(ST_VICTOR.geoaddress.neighbours(distance=10000)), [COMMANDERIE.geoaddress])

        self.assertListEqual(list(COMMANDERIE.geoaddress.neighbours(distance=1000)), [])
        self.assertListEqual(list(COMMANDERIE.geoaddress.neighbours(distance=10000)), [ST_VICTOR.geoaddress, AUBAGNE.geoaddress])

    def test_neighbours_with_same_owner(self):
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)

        ST_VICTOR   = self.create_address(self.orga, address='St Victor',   zipcode='13007', town=u'Marseille', geoloc=(43.290347, 5.365572))
        COMMANDERIE = self.create_address(contact, address='Commanderie',   zipcode='13011', town=u'Marseille', geoloc=(43.301963, 5.462410))
        _AUBAGNE    = self.create_address(contact, address='Maire Aubagne', zipcode='13400', town=u'Aubagne',   geoloc=(43.295783, 5.565589))

        self.assertListEqual(list(ST_VICTOR.geoaddress.neighbours(distance=1000)), [])
        self.assertListEqual(list(ST_VICTOR.geoaddress.neighbours(distance=10000)), [COMMANDERIE.geoaddress])

        self.assertListEqual(list(COMMANDERIE.geoaddress.neighbours(distance=1000)), [])
        self.assertListEqual(list(COMMANDERIE.geoaddress.neighbours(distance=10000)), [ST_VICTOR.geoaddress]) # ignore aubagne, same owner !

    def test_neighbours_with_empty_coordinates(self):
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)

        self.create_address(self.orga, address='St Victor', zipcode='13007', town=u'Marseille', geoloc=(43.290347, 5.365572))
        self.create_address(contact, address='Commanderie', zipcode='13011', town=u'Marseille', geoloc=(43.301963, 5.462410))

        address = self.create_address(contact, address='Maire Aubagne', zipcode='0', town=u'Unknown')
        GeoAddress.populate_geoaddress(address)

        self.assertEqual((None, None), (address.geoaddress.latitude, address.geoaddress.longitude))

        self.assertListEqual(list(address.geoaddress.neighbours(distance=1000)), [])
        self.assertListEqual(list(address.geoaddress.neighbours(distance=10000)), [])

    def test_town_unicode(self):
        self.assertEqual(u'13001 Marseille FRANCE', unicode(self.marseille1))
        self.assertEqual(u'13002 Marseille FRANCE', unicode(self.marseille2))

    def test_town_search(self):
        address = create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille')
        self.assertEqual(Town.objects.get(zipcode=13002), Town.search(address))

        address = create_address(owner=self.orga, address='Mairie', zipcode='13001', city=u'Marseille')
        self.assertEqual(Town.objects.get(zipcode=13001), Town.search(address))

        address = create_address(owner=self.orga, address='Mairie', zipcode='13400')
        self.assertEqual(Town.objects.get(zipcode=13400), Town.search(address))

        # zipcode has priority on city name.
        address = create_address(owner=self.orga, address='Mairie', zipcode='13400', city=u'Marseille')
        self.assertEqual(Town.objects.get(zipcode=13400), Town.search(address))

        address = create_address(owner=self.orga, address='Mairie', city='Marseille')
        self.assertEqual(Town.objects.get(zipcode=13001), Town.search(address))

        address = create_address(owner=self.orga, address='Mairie')
        self.assertEqual(None, Town.search(address))

        address = create_address(owner=self.orga, address='Mairie', zipcode='unknown')
        self.assertEqual(None, Town.search(address))

        address = create_address(owner=self.orga, address='Mairie', city='unknown')
        self.assertEqual(None, Town.search(address))

    def test_town_search_all(self):
        addresses = [create_address(owner=self.orga, address='La Major', zipcode='13002', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13001', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13400'),
                     create_address(owner=self.orga, address='Mairie', zipcode='13400', city=u'Marseille'),
                     create_address(owner=self.orga, address='Mairie'),
                     create_address(owner=self.orga, address='Mairie', zipcode='unknown'),
                     create_address(owner=self.orga, address='Mairie', city='Marseille'),
                     create_address(owner=self.orga, address='Mairie', city='unknown'),]

        self.assertListEqual([
                                 Town.objects.get(zipcode=13002),
                                 Town.objects.get(zipcode=13001),
                                 Town.objects.get(zipcode=13400),
                                 Town.objects.get(zipcode=13400),
                                 None,
                                 None,
                                 Town.objects.get(zipcode=13001),
                                 None,
                             ],
                             list(Town.search_all(addresses)))
