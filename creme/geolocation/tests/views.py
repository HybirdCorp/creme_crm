# -*- coding: utf-8 -*-

try:
    from json import loads as json_decode

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models.auth import SetCredentials
    from creme.creme_core.models.entity_filter import EntityFilter, EntityFilterCondition

    from creme.persons.models import Organisation, Contact, Address

    from ..models import GeoAddress, Town
    from ..utils import address_as_dict
    from .base import GeoLocationBaseTestCase
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('SetAddressInfoTestCase',
           'GetAddressesTestCase',
           'GetNeighboursTestCase',)


create_town = Town.objects.create
create_orga = Organisation.objects.create


class SetAddressInfoTestCase(GeoLocationBaseTestCase):
    SET_ADDRESS_URL = '/geolocation/set_address_info/%s'

    def build_set_address_url(self, address_id):
        return self.SET_ADDRESS_URL % address_id

    def test_set_address_info(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        address = self.create_address(orga)

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertPOST(200, self.build_set_address_url(address.id),
                        data=dict(latitude=45.22454,
                                  longitude=-1.22121,
                                  status=GeoAddress.COMPLETE,
                                  geocoded=True,))

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(address.geoaddress, address=address, latitude=45.22454, longitude=-1.22121, draggable=True, geocoded=True,
                              status=GeoAddress.COMPLETE)

        self.assertPOST(200, self.build_set_address_url(address.id),
                        data=dict(latitude=28.411,
                                  longitude=45.44,
                                  status=GeoAddress.MANUAL,
                                  geocoded=True,))

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGeoAddress(GeoAddress.objects.get(), address=address, latitude=28.411, longitude=45.44, draggable=True, geocoded=True,
                              status=GeoAddress.MANUAL)

    def test_set_address_info_GET_request(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        address = self.create_address(orga)

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGET404(self.build_set_address_url(address.id))

    def test_set_address_info_without_geoaddress(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        address = self.create_address(orga)

        address.geoaddress.delete()

        self.assertEqual(0, GeoAddress.objects.count())

        self.assertPOST(200, self.build_set_address_url(address.id),
                        data={'latitude':  45.22454,
                              'longitude': -1.22121,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})

        address = Address.objects.get(pk=address.id)

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(GeoAddress.objects.get(), address=address, latitude=45.22454, longitude=-1.22121, draggable=True, geocoded=True)

        self.assertPOST(200, self.build_set_address_url(address.id),
                        data={'latitude':  28.411,
                              'longitude': 45.44,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGeoAddress(GeoAddress.objects.get(), address=address, latitude=28.411, longitude=45.44, draggable=True, geocoded=True)

    def test_set_address_info_missing_address(self):
        self.login()

        self.assertEqual(0, GeoAddress.objects.count())

        self.assertPOST(404, self.build_set_address_url('000'),
                        data={'latitude':  45.22454,
                              'longitude': -1.22121,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})

    def test_set_address_info_missing_argument(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        address = self.create_address(orga)

        self.assertPOST(200, self.build_set_address_url(address.id),
                        data={'latitude':  45.22454,
                              'longitude': -1.22121,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGeoAddress(address.geoaddress, address=address, latitude=45.22454, longitude=-1.22121, draggable=True, geocoded=True)

        self.assertPOST(404, self.build_set_address_url(address.id),
                        data={'latitude':  45.22454,
                              'geocoded':  True,})

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGeoAddress(GeoAddress.objects.get(), address=address, latitude=45.22454, longitude=-1.22121, draggable=True, geocoded=True)

    def test_set_address_info_credentials(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons',))

        SetCredentials.objects.create(role=self.user.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN)

        orga = create_orga(name='Orga 1', user=self.other_user)
        address = self.create_address(orga)

        self.assertPOST(403, self.build_set_address_url(address.id),
                        data={'latitude':  45.22454,
                              'longitude': -1.22121,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        self.assertPOST(200, self.build_set_address_url(address.id),
                        data={'latitude':  45.22454,
                              'longitude': -1.22121,
                              'status': GeoAddress.COMPLETE,
                              'geocoded':  True,})


class GetAddressesTestCase(GeoLocationBaseTestCase):
    GET_ADDRESSES_URL = '/geolocation/get_addresses_from_filter/%s'

    def build_get_addresses_url(self, filter):
        return self.GET_ADDRESSES_URL % filter

    def test_get_addresses_empty_filter(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.user)
        orga3 = create_orga(name='Orga 3', user=self.user)

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': []})

        address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_address(orga3, zipcode='01630', town=u'Péron')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(address),
                                                                           address_as_dict(address2),
                                                                           address_as_dict(address3),]})

    def test_get_addresses_priority(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.user)
        contact = Contact.objects.create(last_name='Contact 1', user=self.user)

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': []})

        orga_address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        _orga_address2 = self.create_shipping_address(orga, zipcode='01190', town=u'Ozan')
        _orga_address3 = self.create_address(orga, zipcode='01630', town=u'Péron')

        orga2_address = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        _orga2_address2 = self.create_address(orga2, zipcode='01630', town=u'Péron')

        contact_address = self.create_address(contact, zipcode='01630', town=u'Péron')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(contact_address),
                                                                           address_as_dict(orga_address),
                                                                           address_as_dict(orga2_address),]})

    def test_get_addresses_first_other_address(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)

        orga_address = self.create_address(orga, zipcode='13012', town=u'Marseille')
        _orga_address2 = self.create_address(orga, zipcode='01190', town=u'Ozan')
        _orga_address3 = self.create_address(orga, zipcode='01630', town=u'Péron')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(orga_address),]})

    def test_get_addresses_invalid_filter(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        self.create_billing_address(orga, zipcode='13012', town=u'Marseille')

        self.assertGET404(self.build_get_addresses_url('unknown'))

    def test_get_addresses_credentials(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons',))

        SetCredentials.objects.create(role=self.user.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN)

        orga = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.other_user)

        orga_address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        orga2_address = self.create_billing_address(orga2, zipcode='01190', town=u'Ozan')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(orga_address),]})

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(orga_address),
                                                                           address_as_dict(orga2_address),]})

    def test_get_addresses(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.user)
        orga3 = create_orga(name='Orga 3', user=self.user)

        address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town=u'Péron')

        efilter = EntityFilter.create('test-filter', 'Orga 1', Organisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.EQUALS,
                                                                    name='name', values=['Orga 1'],
                                                                   )
                               ])

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(address),
                                                                           address_as_dict(address2),
                                                                           address_as_dict(address3),]})

        response = self.assertGET200(self.build_get_addresses_url(efilter.pk))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(address),]})

    def test_get_addresses_populate(self):
        self.login()

        orga = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.user)
        orga3 = create_orga(name='Orga 3', user=self.user)

        address = self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town=u'Péron')

        GeoAddress.objects.all().delete()
        self.assertEqual(0, GeoAddress.objects.count())

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(address),
                                                                           address_as_dict(address2),
                                                                           address_as_dict(address3),]})

        self.assertEqual(3, GeoAddress.objects.count())


class GetNeighboursTestCase(GeoLocationBaseTestCase):
    GET_NEIGHBOURS_URL = '/geolocation/get_neighbours/%s/%s'

    def build_get_neighbours_url(self, source_id, filter):
        return self.GET_NEIGHBOURS_URL % (source_id, filter)

    def populate_addresses(self, user):
        orga = create_orga(name='A', user=user)
        orga2 = create_orga(name='B', user=user)
        orga3 = create_orga(name='C', user=user)
        orga4 = create_orga(name='D', user=user)

        self.MARSEILLE_LA_MAJOR    = self.create_billing_address(orga,  address='La Major',      zipcode='13002', town=u'Marseille',    geoloc=(43.299991, 5.364832))
        self.MARSEILLE_MAIRIE      = self.create_billing_address(orga2, address='Mairie Marseille', zipcode='13002', town=u'Marseille', geoloc=(43.296524, 5.369821))
        self.MARSEILLE_ST_VICTOR   = self.create_billing_address(orga3, address='St Victor',        zipcode='13007', town=u'Marseille', geoloc=(43.290347, 5.365572))
        self.MARSEILLE_COMMANDERIE = self.create_billing_address(orga4, address='Commanderie',      zipcode='13011', town=u'Marseille', geoloc=(43.301963, 5.462410))

        orga5 = create_orga(name='E', user=user)

        self.AUBAGNE_MAIRIE = self.create_billing_address(orga5, address='Maire Aubagne',    zipcode='13400', town=u'Aubagne',   geoloc=(43.295783, 5.565589))

    def test_get_neighbours(self):
        self.login()
        self.populate_addresses(self.user)

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),]})


        response = self.assertGET200(self.build_get_neighbours_url(self.AUBAGNE_MAIRIE.pk, ''))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE),]})

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_COMMANDERIE.pk, ''))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_COMMANDERIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_MAIRIE),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.AUBAGNE_MAIRIE),]})

    def test_get_neighbours_distance(self):
        self.login()
        self.populate_addresses(self.user)

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''), data={'distance': 1000})
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),]})

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''), data={'distance': 20000})
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),
                                                                           address_as_dict(self.AUBAGNE_MAIRIE),]})

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''), data={'distance': 'NaN'})
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),]})

    def test_get_neighbours_filtered(self):
        self.login()
        self.populate_addresses(self.user)

        efilter = EntityFilter.create('test-filter', 'test', Organisation, is_custom=True)
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.EQUALS_NOT,
                                                                    name='name', values=['C'],
                                                                   )
                               ]) # filter ST-VICTOR

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, efilter.pk))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),]})

        response = self.assertGET200(self.build_get_neighbours_url(self.AUBAGNE_MAIRIE.pk, efilter.pk))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE),]})

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_COMMANDERIE.pk, efilter.pk))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_COMMANDERIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_MAIRIE),
                                                                           address_as_dict(self.AUBAGNE_MAIRIE),]})
    def test_get_neighbours_credentials(self):
        self.maxDiff = None

        self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons',))

        SetCredentials.objects.create(role=self.user.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN)

        self.populate_addresses(self.user)

        # updating an address resets the position, so create a correct town.
        create_town(name='Marseille', zipcode='13002', country='FRANCE', latitude=43.296524, longitude=5.369821)

        self.MARSEILLE_LA_MAJOR.owner = self.other_user.linked_contact
        self.MARSEILLE_LA_MAJOR.save()

        # "la major" is filtered (owned by different user)
        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),]})

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''))
        self.assertDictEqual(json_decode(response.content), {'source_address': address_as_dict(self.MARSEILLE_MAIRIE),
                                                             'addresses': [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                                                           address_as_dict(self.MARSEILLE_ST_VICTOR),
                                                                           address_as_dict(self.MARSEILLE_COMMANDERIE),]})

    def test_get_neighbours_invalid_filter(self):
        self.login()
        self.populate_addresses(self.user)

        self.assertGET404(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, 'unknown'))

    def test_get_neighbours_missing_address(self):
        self.login()
        self.assertGET404(self.build_get_neighbours_url('unknown', ''))

