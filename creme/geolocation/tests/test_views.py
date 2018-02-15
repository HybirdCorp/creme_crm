# -*- coding: utf-8 -*-

try:
    from json import loads as json_decode

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models.auth import SetCredentials
    from creme.creme_core.models.entity_filter import EntityFilter, EntityFilterCondition

    from creme.persons.tests.base import (skipIfCustomAddress,
            skipIfCustomContact, skipIfCustomOrganisation)

    from ..models import GeoAddress, Town
    from ..utils import address_as_dict
    from .base import GeoLocationBaseTestCase, Organisation, Contact
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


create_town = Town.objects.create
create_orga = Organisation.objects.create


class SetAddressInfoTestCase(GeoLocationBaseTestCase):
    SET_ADDRESS_URL = reverse('geolocation__set_address_info')

    def build_set_address_url(self, address_id):  # DEPRECATED # TODO: remove in Creme1.8
        return reverse('geolocation__set_address_info', args=(address_id,))

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info(self):
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)
        self.assertEqual(1, GeoAddress.objects.count())

        data = {'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.COMPLETE,
                'geocoded':  True,
               }
        self.assertPOST200(self.SET_ADDRESS_URL, data=dict(data, id=address.id))

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))

        geoaddress = geoaddresses[0]
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data)
        self.assertEqual(self.refresh(address).geoaddress, geoaddress)

        data = {'latitude':  28.411,
                'longitude': 45.44,
                'status':    GeoAddress.MANUAL,
                'geocoded':  True,
               }
        self.assertPOST200(self.SET_ADDRESS_URL, data=dict(data, id=address.id))

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))
        self.assertGeoAddress(geoaddresses[0], address=address, draggable=True, **data)

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_legacy(self):  # TODO: remove in Creme1.8
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)
        self.assertEqual(1, GeoAddress.objects.count())

        data = {'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.COMPLETE,
                'geocoded':  True,
               }
        self.assertPOST200(self.build_set_address_url(address.id), data=data)

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))

        geoaddress = geoaddresses[0]
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data)
        self.assertEqual(self.refresh(address).geoaddress, geoaddress)

        data = {'latitude':  28.411,
                'longitude': 45.44,
                'status':    GeoAddress.MANUAL,
                'geocoded':  True,
               }
        self.assertPOST200(self.build_set_address_url(address.id), data=data)

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))
        self.assertGeoAddress(geoaddresses[0], address=address, draggable=True, **data)

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_GET_request(self):
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)

        self.assertEqual(1, GeoAddress.objects.count())
        self.assertGET404(self.build_set_address_url(address.id))

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_without_geoaddress(self):
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)

        address.geoaddress.delete()
        self.assertEqual(0, GeoAddress.objects.count())

        data = {'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.COMPLETE,
                'geocoded':  True,
               }
        self.assertPOST200(self.build_set_address_url(address.id), data=data)

        address = self.refresh(address)
        self.assertEqual(1, GeoAddress.objects.count())
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(GeoAddress.objects.get(), address=address,
                              draggable=True, **data
                             )

        data = {'latitude':  28.411,
                'longitude': 45.44,
                'status':    GeoAddress.COMPLETE,
                'geocoded':  True,
               }
        self.assertPOST200(self.build_set_address_url(address.id), data=data)

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))
        self.assertGeoAddress(geoaddresses[0], address=address,
                              draggable=True, **data
                             )

    def test_set_address_info_missing_address(self):
        self.login()

        self.assertEqual(0, GeoAddress.objects.count())
        self.assertPOST404(self.build_set_address_url('000'),
                           data={'latitude':  45.22454,
                                 'longitude': -1.22121,
                                 'status':    GeoAddress.COMPLETE,
                                 'geocoded':  True,
                                }
                          )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_missing_argument(self):
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)

        data = {'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.COMPLETE,
                'geocoded':  True,
               }
        self.assertPOST200(self.build_set_address_url(address.id), data=data)

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))

        geoaddress = geoaddresses[0]
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data)
        self.assertEqual(self.refresh(address).geoaddress, geoaddress)

        self.assertPOST404(self.build_set_address_url(address.id),
                           data={'latitude':  45.22454,
                                 'geocoded':  True,
                                }
                          )

        geoaddresses = GeoAddress.objects.all()
        self.assertEqual(1, len(geoaddresses))
        self.assertGeoAddress(geoaddresses[0], address=address, draggable=True, **data)

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_credentials(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons'))

        SetCredentials.objects.create(role=self.user.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        orga = create_orga(name='Orga 1', user=self.other_user)
        address = self.create_address(orga)

        self.assertPOST403(self.build_set_address_url(address.id),
                           data={'latitude':  45.22454,
                                 'longitude': -1.22121,
                                 'status':    GeoAddress.COMPLETE,
                                 'geocoded':  True,
                                }
                          )

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        self.assertPOST200(self.build_set_address_url(address.id),
                           data={'latitude':  45.22454,
                                 'longitude': -1.22121,
                                 'status':    GeoAddress.COMPLETE,
                                 'geocoded':  True,
                                }
                          )


@skipIfCustomOrganisation
@skipIfCustomAddress
class GetAddressesTestCase(GeoLocationBaseTestCase):
    GET_ADDRESSES_URL = reverse('geolocation__addresses')

    def build_get_addresses_url(self, efilter_pk):  # DEPRECATED # TODO: remove in Creme1.8
        return reverse('geolocation__addresses', args=(efilter_pk,))

    def test_get_addresses_empty_filter(self):
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(json_decode(response.content), {'addresses': []})

        address  = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_address(orga3, zipcode='01630', town=u'Péron')

        response = self.assertGET200(url)
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(address),
                                      address_as_dict(address2),
                                      address_as_dict(address3),
                                     ]
                                    )

    def test_get_addresses_empty_filter_legacy(self):  # TODO: remove in Creme1.8
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertDictEqual(json_decode(response.content), {'addresses': []})

        address  = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_address(orga3, zipcode='01630', town=u'Péron')

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(address),
                                      address_as_dict(address2),
                                      address_as_dict(address3),
                                     ]
                                    )

    @skipIfCustomContact
    def test_get_addresses_priority(self):
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        contact = Contact.objects.create(last_name='Contact 1', user=user)

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(json_decode(response.content), {'addresses': []})

        orga_address = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        self.create_shipping_address(orga1, zipcode='01190', town=u'Ozan')
        self.create_address(orga1, zipcode='01630', town=u'Péron')

        orga2_address = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        self.create_address(orga2, zipcode='01630', town=u'Péron')

        contact_address = self.create_address(contact, zipcode='01630', town=u'Péron')

        response = self.assertGET200(url)
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(contact_address),
                                      address_as_dict(orga_address),
                                      address_as_dict(orga2_address),
                                     ]
                                    )

    def test_get_addresses_first_other_address(self):
        user = self.login()

        orga = create_orga(name='Orga 1', user=user)

        orga_address = self.create_address(orga, zipcode='13012', town=u'Marseille')
        self.create_address(orga, zipcode='01190', town=u'Ozan')
        self.create_address(orga, zipcode='01630', town=u'Péron')

        response = self.assertGET200(self.GET_ADDRESSES_URL)
        self.assertDictEqual(json_decode(response.content),
                             {'addresses': [address_as_dict(orga_address)]}
                            )

    def test_get_addresses_invalid_filter(self):
        user = self.login()
        orga = create_orga(name='Orga 1', user=user)
        self.create_billing_address(orga, zipcode='13012', town=u'Marseille')
        self.assertGET404(self.GET_ADDRESSES_URL, data={'id': 'unknown'})

    def test_get_addresses_credentials(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons'))

        SetCredentials.objects.create(role=self.user.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        orga1 = create_orga(name='Orga 1', user=self.user)
        orga2 = create_orga(name='Orga 2', user=self.other_user)

        orga1_address = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        orga2_address = self.create_billing_address(orga2, zipcode='01190', town=u'Ozan')

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(json_decode(response.content), {'addresses': [address_as_dict(orga1_address)]})

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        response = self.assertGET200(url)
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(orga1_address),
                                      address_as_dict(orga2_address),
                                     ]
                                    )

    def test_get_addresses(self):
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        address1 = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town=u'Péron')

        efilter = EntityFilter.create('test-filter', 'Orga 1', Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='name', values=['Orga 1'],
                                                    ),
                                                ] 
                                     )

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(address1),
                                      address_as_dict(address2),
                                      address_as_dict(address3),
                                     ]
                                    )

        response = self.assertGET200(url, data={'id': efilter.pk})
        self.assertDictEqual(json_decode(response.content),
                             {'addresses': [address_as_dict(address1)]}
                            )

    def test_get_addresses_legacy(self):  # TODO: remove in Creme1.8
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        address1 = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town=u'Péron')

        efilter = EntityFilter.create('test-filter', 'Orga 1', Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='name', values=['Orga 1'],
                                                    ),
                                                ]
                                     )

        response = self.assertGET200(self.build_get_addresses_url(''))
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(address1),
                                      address_as_dict(address2),
                                      address_as_dict(address3),
                                     ]
                                    )

        response = self.assertGET200(self.build_get_addresses_url(efilter.pk))
        self.assertDictEqual(json_decode(response.content),
                             {'addresses': [address_as_dict(address1)]}
                            )

    def test_get_addresses_populate(self):
        user = self.login()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        address1 = self.create_billing_address(orga1, zipcode='13012', town=u'Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town=u'Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town=u'Péron')

        GeoAddress.objects.all().delete()
        self.assertEqual(0, GeoAddress.objects.count())

        response = self.assertGET200(self.GET_ADDRESSES_URL)
        self.assertListAddressAsDict(json_decode(response.content)['addresses'],
                                     [address_as_dict(address1),
                                      address_as_dict(address2),
                                      address_as_dict(address3),
                                     ]
                                    )

        self.assertEqual(3, GeoAddress.objects.count())


class GetNeighboursTestCase(GeoLocationBaseTestCase):
    GET_NEIGHBOURS_URL = reverse('geolocation__neighbours')

    def build_get_neighbours_url(self, source_id, filter_pk):   # DEPRECATED # TODO: remove in Creme1.8
        return reverse('geolocation__neighbours', args=(source_id, filter_pk))

    def populate_addresses(self, user):
        orga  = create_orga(name='A', user=user)
        orga2 = create_orga(name='B', user=user)
        orga3 = create_orga(name='C', user=user)
        orga4 = create_orga(name='D', user=user)

        create_baddr = self.create_billing_address
        self.MARSEILLE_LA_MAJOR    = create_baddr(orga,  address='La Major',         zipcode='13002', town=u'Marseille', geoloc=(43.299991, 5.364832))
        self.MARSEILLE_MAIRIE      = create_baddr(orga2, address='Mairie Marseille', zipcode='13002', town=u'Marseille', geoloc=(43.296524, 5.369821))
        self.MARSEILLE_ST_VICTOR   = create_baddr(orga3, address='St Victor',        zipcode='13007', town=u'Marseille', geoloc=(43.290347, 5.365572))
        self.MARSEILLE_COMMANDERIE = create_baddr(orga4, address='Commanderie',      zipcode='13011', town=u'Marseille', geoloc=(43.301963, 5.462410))

        orga5 = create_orga(name='E', user=user)
        self.AUBAGNE_MAIRIE = create_baddr(orga5, address='Maire Aubagne', zipcode='13400', town=u'Aubagne', geoloc=(43.295783, 5.565589))

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours(self):
        self.login()
        self.populate_addresses(self.user)

        url = self.GET_NEIGHBOURS_URL
        response = self.assertGET200(url, data={'address_id': self.MARSEILLE_MAIRIE.id})
        data = json_decode(response.content)
        self.assertEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

        response = self.assertGET200(url, data={'address_id': self.AUBAGNE_MAIRIE.id})
        self.assertDictEqual(json_decode(response.content),
                             {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                              'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE)],
                             }
                            )

        response = self.assertGET200(url, data={'address_id': self.MARSEILLE_COMMANDERIE.id, 'filter_id': ''})
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_MAIRIE),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.AUBAGNE_MAIRIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_legacy(self):  # TODO: remove in Creme1.8
        self.login()
        self.populate_addresses(self.user)

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, ''))
        data = json_decode(response.content)
        self.assertEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

        response = self.assertGET200(self.build_get_neighbours_url(self.AUBAGNE_MAIRIE.pk, ''))
        self.assertDictEqual(json_decode(response.content),
                             {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                              'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE)],
                             }
                            )

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_COMMANDERIE.pk, ''))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_MAIRIE),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.AUBAGNE_MAIRIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_distance(self):
        self.login()
        self.populate_addresses(self.user)

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'address_id': self.MARSEILLE_MAIRIE.id}
        response = self.assertGET200(url, data=dict(GET_data, distance=1000))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                     ]
                                    )

        response = self.assertGET200(url, data=dict(GET_data, distance=20000))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                      address_as_dict(self.AUBAGNE_MAIRIE),
                                     ]
                                    )

        response = self.assertGET200(url, data=dict(GET_data, distance='NaN'))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_filtered(self):
        user = self.login()
        self.populate_addresses(user)

        efilter = EntityFilter.create('test-filter', 'test', Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.EQUALS_NOT,
                                                        name='name', values=['C'],
                                                    ),
                                                 ]  # filter ST-VICTOR
                                     )

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'filter_id': efilter.id}
        response = self.assertGET200(url, data=dict(GET_data, address_id=self.MARSEILLE_MAIRIE.id))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

        response = self.assertGET200(url, data=dict(GET_data, address_id=self.AUBAGNE_MAIRIE.id))
        self.assertDictEqual(json_decode(response.content),
                             {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                              'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE)],
                             }
                            )

        response = self.assertGET200(url, data=dict(GET_data, address_id=self.MARSEILLE_COMMANDERIE.id))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_MAIRIE),
                                      address_as_dict(self.AUBAGNE_MAIRIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_filtered_legacy(self):  # TODO: remove in Creme1.8
        user = self.login()
        self.populate_addresses(user)

        efilter = EntityFilter.create('test-filter', 'test', Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.EQUALS_NOT,
                                                        name='name', values=['C'],
                                                    ),
                                                 ]  # filter ST-VICTOR
                                     )

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_MAIRIE.pk, efilter.pk))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

        response = self.assertGET200(self.build_get_neighbours_url(self.AUBAGNE_MAIRIE.pk, efilter.pk))
        self.assertDictEqual(json_decode(response.content),
                             {'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                              'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE)],
                             }
                            )

        response = self.assertGET200(self.build_get_neighbours_url(self.MARSEILLE_COMMANDERIE.pk, efilter.pk))
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_MAIRIE),
                                      address_as_dict(self.AUBAGNE_MAIRIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomAddress
    def test_get_neighbours_credentials(self):
        self.maxDiff = None

        user = self.login(is_superuser=False, allowed_apps=('creme_core', 'geolocation', 'persons'))

        SetCredentials.objects.create(role=self.role,
                                      ctype=ContentType.objects.get_for_model(Organisation),
                                      value=EntityCredentials._ALL_CREDS,
                                      set_type=SetCredentials.ESET_OWN,
                                     )

        self.populate_addresses(user)

        # Updating an address resets the position, so create a correct town.
        create_town(name='Marseille', zipcode='13002', country='FRANCE', latitude=43.296524, longitude=5.369821)

        self.MARSEILLE_LA_MAJOR.owner = self.other_user.linked_contact
        self.MARSEILLE_LA_MAJOR.save()

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'address_id': self.MARSEILLE_MAIRIE.id}

        # "la major" is filtered (owned by different user)
        response = self.assertGET200(url, data=GET_data)
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

        self.client.logout()
        self.client.login(username=self.other_user.username, password='test')

        response = self.assertGET200(url, data=GET_data)
        data = json_decode(response.content)
        self.assertDictEqual(data['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(data['addresses'],
                                     [address_as_dict(self.MARSEILLE_LA_MAJOR),
                                      address_as_dict(self.MARSEILLE_ST_VICTOR),
                                      address_as_dict(self.MARSEILLE_COMMANDERIE),
                                     ]
                                    )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_invalid_filter(self):
        user = self.login()
        self.populate_addresses(user)
        self.assertGET404(self.GET_NEIGHBOURS_URL, data={'address_id': self.MARSEILLE_MAIRIE.id, 'filter_id': 'unknown'})

    def test_get_neighbours_missing_address(self):
        self.login()
        self.assertGET404(self.build_get_neighbours_url(1024, ''))
        self.assertGET404(self.GET_NEIGHBOURS_URL, data={'address_id': 1024})
