# -*- coding: utf-8 -*-

try:
    from creme.persons.models import Address, Organisation

    from ..models import Town, GeoAddress
    from ..populate import Populator

    from .base import GeoLocationBaseTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

__all__ = ('PopulatorTestCase',)


class PopulatorTestCase(GeoLocationBaseTestCase):
    OZAN     = ["1","01","ozan","OZAN","ozan","Ozan","O250","OSN","01190","284","01284","2","26","6","618","469","500","93","6.6","4.91667","46.3833","2866","51546","+45456","462330","170","205"]
    PERON    = ["9","01","peron","PERON","peron","Péron","P650","PRN","01630","288","01288","3","12","6","2143","1578","1900","82","26.01","5.93333","46.2","3989","51322","+55535","461124","411","1501"]
    ACOUA    = ["36810","976","acoua","ACOUA","acoua","Acoua","A200","AK","97630","601","97601","0","01",None,"4714","4714","4714","373","12.62","45.0645","-12.7239",None,None,None,None,None,None]
    STBONNET = ["6307","17","saint-bonnet-sur-gironde","SAINT-BONNET-SUR-GIRONDE","saint bonnet sur gironde","Saint-Bonnet-sur-Gironde","S53153262653","SNTBNTSRJRNT","17150","312","17312","1","16","6","869","838","900","28","30.6","-0.666667","45.35","-3329","50394","-03936","452116","0","87"]
    INVALID  = ["36810","976","acoua","ACOUA","acoua","Acoua","A200","AK",None,"601","97601","0","01",None,"4714","4714","4714","373","12.62","45.0645","-12.7239",None,None,None,None,None,None]

    def setUp(self):
        self.populator = Populator(verbosity=3, app='geolocation', all_apps=frozenset(('creme_core', 'persons',)), options={'verbosity': 3})

    def assertTown(self, town, **kwargs):
        self.assertModelInstance(town, Town, **kwargs)

    def test_populate_does_not_exist(self):
        self.assertEqual(0, Town.objects.count())

        self.populator.populate_towns([self.OZAN, self.PERON, self.ACOUA, self.STBONNET])
        self.assertEqual(4, Town.objects.count())

        self.assertTown(Town.objects.get(zipcode='01190'), zipcode='01190', name='Ozan', slug='ozan', longitude=4.91667, latitude=46.3833)
        self.assertTown(Town.objects.get(zipcode='01630'), zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2)
        self.assertTown(Town.objects.get(zipcode='97630'), zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239)
        self.assertTown(Town.objects.get(zipcode='17150'), zipcode='17150', name='Saint-Bonnet-sur-Gironde', slug='saint-bonnet-sur-gironde', longitude=-0.666667, latitude=45.35)

    def test_populate_exists_ignored(self):
        Town.objects.create(zipcode='01190', name='Ozan', slug='ozan', longitude=0.0, latitude=0.0)
        self.assertEqual(1, Town.objects.count())

        self.populator.populate_towns([self.OZAN, self.PERON, self.ACOUA, self.STBONNET])
        self.assertEqual(4, Town.objects.count())
        self.assertTown(Town.objects.get(zipcode='01190'), zipcode='01190', name='Ozan', slug='ozan', longitude=0.0, latitude=0.0)
        self.assertTown(Town.objects.get(zipcode='01630'), zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2)
        self.assertTown(Town.objects.get(zipcode='97630'), zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239)
        self.assertTown(Town.objects.get(zipcode='17150'), zipcode='17150', name='Saint-Bonnet-sur-Gironde', slug='saint-bonnet-sur-gironde', longitude=-0.666667, latitude=45.35)

    def test_populate_invalid_ignored(self):
        self.populator.populate_towns([self.OZAN, self.PERON, self.INVALID, self.ACOUA])
        self.assertEqual(3, Town.objects.count())
        self.assertTown(Town.objects.get(zipcode='01190'), zipcode='01190', name='Ozan', slug='ozan', longitude=4.91667, latitude=46.3833)
        self.assertTown(Town.objects.get(zipcode='01630'), zipcode='01630', name='Péron', slug='peron', longitude=5.93333, latitude=46.2)
        self.assertTown(Town.objects.get(zipcode='97630'), zipcode='97630', name='Acoua', slug='acoua', longitude=45.0645, latitude=-12.7239)

    def test_create_geoaddress_no_town(self):
        self.login()

        self.assertEqual(0, GeoAddress.objects.count())

        self.populator.populate_addresses()
        self.assertEqual(0, GeoAddress.objects.count())

        orga = Organisation.objects.create(name='Orga 1', user=self.user)

        Address.objects.create(name='Addresse',
                               address='13 rue du yahourt',
                               po_box='',
                               zipcode='13008',
                               city='Marseille',
                               department='13',
                               state=None,
                               country='FRANCE',
                               owner=orga
                              )

        GeoAddress.objects.all().delete()

        with self.assertRaises(GeoAddress.DoesNotExist):
            Address.objects.get().geoaddress

        self.populator.populate_addresses()
        self.assertEqual(1, GeoAddress.objects.count())

        address = Address.objects.get()
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(address.geoaddress, address=address, latitude=None, longitude=None, draggable=True, geocoded=False)

    def test_create_geoaddress_with_town(self):
        self.login()
        self.populator.populate_towns([self.OZAN, self.PERON, self.ACOUA, self.STBONNET])

        orga = Organisation.objects.create(name='Orga 1', user=self.user)

        Address.objects.create(name='Addresse',
                               address='13 rue du yahourt',
                               po_box='',
                               zipcode='01630',
                               city=u'Péron',
                               department='01',
                               state=None,
                               country='FRANCE',
                               owner=orga
                              )

        GeoAddress.objects.all().delete()

        with self.assertRaises(GeoAddress.DoesNotExist):
            Address.objects.get().geoaddress

        self.populator.populate_addresses()
        self.assertEqual(1, GeoAddress.objects.count())

        address = Address.objects.get()
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(address.geoaddress, address=address, longitude=5.93333, latitude=46.2, draggable=True, geocoded=False)
