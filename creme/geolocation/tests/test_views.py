from functools import partial

from django.urls import reverse

from creme.creme_core.core.entity_filter import condition_handler, operators
from creme.creme_core.models import EntityFilter, FakeInvoice
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from ..models import GeoAddress, Town
from ..utils import address_as_dict
from .base import Contact, GeoLocationBaseTestCase, Organisation

create_town = Town.objects.create
create_orga = Organisation.objects.create


class SetAddressInfoTestCase(GeoLocationBaseTestCase):
    SET_ADDRESS_URL = reverse('geolocation__set_address_info')

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info(self):
        user = self.login_as_root_and_get()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)
        self.assertEqual(1, GeoAddress.objects.count())

        data1 = {
            'latitude':  45.22454,
            'longitude': -1.22121,
            'status':    GeoAddress.Status.COMPLETE,
            'geocoded':  True,
        }
        url = self.SET_ADDRESS_URL
        self.assertGET405(url,  data={**data1, 'id': address.id})
        self.assertPOST200(url, data={**data1, 'id': address.id})

        geoaddress = self.get_alone_element(GeoAddress.objects.all())
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data1)
        self.assertEqual(self.refresh(address).geoaddress, geoaddress)

        data2 = {
            'latitude':  28.411,
            'longitude': 45.44,
            'status':    GeoAddress.Status.MANUAL,
            'geocoded':  True,
        }
        self.assertPOST200(url, data={**data2, 'id': address.id})

        geoaddress = self.get_alone_element(GeoAddress.objects.all())
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data2)

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_without_geoaddress(self):
        user = self.login_as_root_and_get()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)

        address.geoaddress.delete()
        self.assertEqual(0, GeoAddress.objects.count())

        data1 = {
            'latitude':  45.22454,
            'longitude': -1.22121,
            'status':    GeoAddress.Status.COMPLETE,
            'geocoded':  True,
        }
        url = self.SET_ADDRESS_URL
        self.assertPOST200(url, data={**data1, 'id': address.id})

        address = self.refresh(address)
        self.assertEqual(1, GeoAddress.objects.count())
        self.assertEqual(address.geoaddress, GeoAddress.objects.get())
        self.assertGeoAddress(
            GeoAddress.objects.get(), address=address, draggable=True, **data1
        )

        data2 = {
            'latitude':  28.411,
            'longitude': 45.44,
            'status':    GeoAddress.Status.COMPLETE,
            'geocoded':  True,
        }
        self.assertPOST200(url, data={**data2, 'id': address.id})

        geoaddress = self.get_alone_element(GeoAddress.objects.all())
        self.assertGeoAddress(
            geoaddress, address=address, draggable=True, **data2
        )

    def test_set_address_info_missing_address(self):
        self.login_as_root()

        self.assertFalse(GeoAddress.objects.all())
        self.assertPOST404(
            self.SET_ADDRESS_URL,
            data={
                'id':       '000',
                'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.Status.COMPLETE,
                'geocoded':  True,
            },
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_missing_argument(self):
        user = self.login_as_root_and_get()

        orga = create_orga(name='Orga 1', user=user)
        address = self.create_address(orga)

        data = {
            'latitude':  45.22454,
            'longitude': -1.22121,
            'status':    GeoAddress.Status.COMPLETE,
            'geocoded':  True,
        }
        self.assertPOST200(self.SET_ADDRESS_URL, data={**data, 'id': address.id})

        geoaddress = self.get_alone_element(GeoAddress.objects.all())
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data)
        self.assertEqual(self.refresh(address).geoaddress, geoaddress)

        self.assertPOST404(
            self.SET_ADDRESS_URL,
            data={
                'id':        address.id,
                'latitude':  45.22454,
                'geocoded':  True,
            },
        )

        geoaddress = self.get_alone_element(GeoAddress.objects.all())
        self.assertGeoAddress(geoaddress, address=address, draggable=True, **data)

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_set_address_info_credentials(self):
        user = self.login_as_standard(allowed_apps=('creme_core', 'geolocation', 'persons'))
        self.add_credentials(user.role, own='*', model=Organisation)

        orga = create_orga(name='Orga 1', user=self.get_root_user())
        address = self.create_address(orga)

        url = self.SET_ADDRESS_URL
        self.assertPOST403(
            url,
            data={
                'id':        address.id,
                'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.Status.COMPLETE,
                'geocoded':  True,
            },
        )

        self.client.logout()
        self.login_as_root()

        self.assertPOST200(
            url,
            data={
                'id':        address.id,
                'latitude':  45.22454,
                'longitude': -1.22121,
                'status':    GeoAddress.Status.COMPLETE,
                'geocoded':  True,
            },
        )


@skipIfCustomOrganisation
@skipIfCustomAddress
class GetAddressesTestCase(GeoLocationBaseTestCase):
    GET_ADDRESSES_URL = reverse('geolocation__addresses')

    def test_get_addresses_empty_filter(self):
        user = self.login_as_root_and_get()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(response.json(), {'addresses': []})

        address1 = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town='Ozan')
        address3 = self.create_address(orga3, zipcode='01630', town='Péron')

        response = self.assertGET200(url)
        self.assertListAddressAsDict(
            response.json()['addresses'],
            address_as_dict(address1),
            address_as_dict(address2),
            address_as_dict(address3),
        )

    @skipIfCustomContact
    def test_get_addresses_priority(self):
        user = self.login_as_root_and_get()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        contact = Contact.objects.create(last_name='Contact 1', user=user)

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(response.json(), {'addresses': []})

        orga_address = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        self.create_shipping_address(orga1, zipcode='01190', town='Ozan')
        self.create_address(orga1, zipcode='01630', town='Péron')

        orga2_address = self.create_shipping_address(orga2, zipcode='01190', town='Ozan')
        self.create_address(orga2, zipcode='01630', town='Péron')

        contact_address = self.create_address(contact, zipcode='01630', town='Péron')

        response = self.assertGET200(url)
        self.assertListAddressAsDict(
            response.json()['addresses'],
            address_as_dict(contact_address),
            address_as_dict(orga_address),
            address_as_dict(orga2_address),
        )

    def test_get_addresses_first_other_address(self):
        user = self.login_as_root_and_get()

        orga = create_orga(name='Orga 1', user=user)

        orga_address = self.create_address(orga, zipcode='13012', town='Marseille')
        self.create_address(orga, zipcode='01190', town='Ozan')
        self.create_address(orga, zipcode='01630', town='Péron')

        response = self.assertGET200(self.GET_ADDRESSES_URL)
        self.assertDictEqual(
            response.json(), {'addresses': [address_as_dict(orga_address)]},
        )

    def test_get_addresses_invalid_filter(self):
        user = self.login_as_root_and_get()
        orga = create_orga(name='Orga 1', user=user)
        self.create_billing_address(orga, zipcode='13012', town='Marseille')
        self.assertGET404(self.GET_ADDRESSES_URL, data={'id': 'unknown'})

    def test_get_addresses_credentials(self):
        user = self.login_as_standard(allowed_apps=('creme_core', 'geolocation', 'persons'))
        self.add_credentials(user.role, own='*', model=Organisation)

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=self.get_root_user())

        orga1_address = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        orga2_address = self.create_billing_address(orga2, zipcode='01190', town='Ozan')

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertDictEqual(response.json(), {'addresses': [address_as_dict(orga1_address)]})

        self.client.logout()
        self.login_as_root()

        response = self.assertGET200(url)
        self.assertListAddressAsDict(
            response.json()['addresses'],
            address_as_dict(orga1_address),
            address_as_dict(orga2_address),
        )

    def test_get_addresses(self):
        user = self.login_as_root_and_get()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        address1 = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town='Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town='Péron')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'Orga 1', Organisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.EQUALS,
                    field_name='name', values=['Orga 1'],
                ),
            ],
        )

        url = self.GET_ADDRESSES_URL
        response = self.assertGET200(url)
        self.assertListAddressAsDict(
            response.json()['addresses'],
            address_as_dict(address1),
            address_as_dict(address2),
            address_as_dict(address3),
        )

        response = self.assertGET200(url, data={'id': efilter.pk})
        self.assertDictEqual(
            response.json(), {'addresses': [address_as_dict(address1)]},
        )

    def test_get_addresses_populate(self):
        user = self.login_as_root_and_get()

        orga1 = create_orga(name='Orga 1', user=user)
        orga2 = create_orga(name='Orga 2', user=user)
        orga3 = create_orga(name='Orga 3', user=user)

        address1 = self.create_billing_address(orga1, zipcode='13012', town='Marseille')
        address2 = self.create_shipping_address(orga2, zipcode='01190', town='Ozan')
        address3 = self.create_billing_address(orga3, zipcode='01630', town='Péron')

        GeoAddress.objects.all().delete()
        self.assertEqual(0, GeoAddress.objects.count())

        response = self.assertGET200(self.GET_ADDRESSES_URL)
        self.assertListAddressAsDict(
            response.json()['addresses'],
            address_as_dict(address1),
            address_as_dict(address2),
            address_as_dict(address3),
        )

        self.assertEqual(3, GeoAddress.objects.count())


class GetNeighboursTestCase(GeoLocationBaseTestCase):
    GET_NEIGHBOURS_URL = reverse('geolocation__neighbours')

    def populate_addresses(self, user):
        orga1 = create_orga(name='A', user=user)
        orga2 = create_orga(name='B', user=user)
        orga3 = create_orga(name='C', user=user)
        orga4 = create_orga(name='D', user=user)

        create_baddr = self.create_billing_address
        self.MARSEILLE_LA_MAJOR = create_baddr(
            orga1,  address='La Major', zipcode='13002', town='Marseille',
            geoloc=(43.299991, 5.364832),
        )
        self.MARSEILLE_MAIRIE = create_baddr(
            orga2, address='Mairie Marseille', zipcode='13002', town='Marseille',
            geoloc=(43.296524, 5.369821),
        )
        self.MARSEILLE_ST_VICTOR = create_baddr(
            orga3, address='St Victor', zipcode='13007', town='Marseille',
            geoloc=(43.290347, 5.365572),
        )
        self.MARSEILLE_COMMANDERIE = create_baddr(
            orga4, address='Commanderie', zipcode='13011', town='Marseille',
            geoloc=(43.301963, 5.462410),
        )

        orga5 = create_orga(name='E', user=user)
        self.AUBAGNE_MAIRIE = create_baddr(
            orga5, address='Mairie Aubagne', zipcode='13400', town='Aubagne',
            geoloc=(43.295783, 5.565589),
        )

    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomAddress
    def test_get_neighbours(self):
        "No filter -> all Contacts & Organisations."
        user = self.login_as_root_and_get()
        self.populate_addresses(user)

        create_contact = partial(Contact.objects.create, user=user)
        contact = create_contact(last_name='Contact 1')
        contact_address = self.create_billing_address(
            contact,
            address='Commanderie', zipcode='13011', town='Marseille',
            geoloc=(43.295784, 5.565590),
        )

        # Should not be used (deleted)
        deleted_contact = create_contact(last_name='Contact 2', is_deleted=True)
        self.create_billing_address(
            deleted_contact,
            address='Commanderie', zipcode='13011', town='Marseille',
            geoloc=(43.295786, 5.565595),
        )

        # Should not be used (not Contact/Organisation)
        invoice = FakeInvoice.objects.create(user=user, name='Invoice#1')
        self.create_billing_address(
            invoice,
            address='Commanderie', zipcode='13011', town='Marseille',
            geoloc=(43.295782, 5.565588),
        )

        url = self.GET_NEIGHBOURS_URL
        response1 = self.assertGET200(url, data={'address_id': self.MARSEILLE_MAIRIE.id})
        data1 = response1.json()
        self.assertEqual(data1['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data1['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
        )

        # ---
        response2 = self.assertGET200(url, data={'address_id': self.AUBAGNE_MAIRIE.id})
        data2 = response2.json()
        self.assertDictEqual(data2['source_address'], address_as_dict(self.AUBAGNE_MAIRIE))
        self.assertListAddressAsDict(
            data2['addresses'],
            address_as_dict(self.MARSEILLE_COMMANDERIE),
            address_as_dict(contact_address),
        )

        # ---
        response3 = self.assertGET200(
            url,
            data={'address_id': self.MARSEILLE_COMMANDERIE.id, 'filter_id': ''},
        )
        data3 = response3.json()
        self.assertDictEqual(data3['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE))
        self.assertListAddressAsDict(
            data3['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_MAIRIE),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.AUBAGNE_MAIRIE),
            address_as_dict(contact_address),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_distance(self):
        user = self.login_as_root_and_get()
        self.populate_addresses(user)

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'address_id': self.MARSEILLE_MAIRIE.id}
        response1 = self.assertGET200(url, data={**GET_data, 'distance': 1000})
        data1 = response1.json()
        self.assertDictEqual(data1['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data1['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
        )

        # ---
        response2 = self.assertGET200(url, data={**GET_data, 'distance': 20000})
        data2 = response2.json()
        self.assertDictEqual(data2['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data2['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
            address_as_dict(self.AUBAGNE_MAIRIE),
        )

        # ---
        response3 = self.assertGET200(url, data={**GET_data, 'distance': 'NaN'})
        data3 = response3.json()
        self.assertDictEqual(data3['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data3['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_filtered(self):
        user = self.login_as_root_and_get()
        self.populate_addresses(user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter', 'test', Organisation, is_custom=True,
            conditions=[
                condition_handler.RegularFieldConditionHandler.build_condition(
                    model=Organisation,
                    operator=operators.EQUALS_NOT,
                    field_name='name', values=['C'],
                ),
            ],  # filter ST-VICTOR
        )

        # Should not be used
        deleted_orga = create_orga(name='F', user=user, is_deleted=True)
        self.create_billing_address(
            deleted_orga,
            address='Commanderie', zipcode='13011', town='Marseille',
            geoloc=(43.301965, 5.462411),
        )

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'filter_id': efilter.id}
        response1 = self.assertGET200(
            url,
            data={**GET_data, 'address_id': self.MARSEILLE_MAIRIE.id},
        )
        data1 = response1.json()
        self.assertDictEqual(data1['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data1['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
        )

        # ---
        response2 = self.assertGET200(url, data={**GET_data, 'address_id': self.AUBAGNE_MAIRIE.id})
        self.assertDictEqual(
            response2.json(),
            {
                'source_address': address_as_dict(self.AUBAGNE_MAIRIE),
                'addresses': [address_as_dict(self.MARSEILLE_COMMANDERIE)],
            },
        )

        # ---
        response3 = self.assertGET200(
            url,
            data={**GET_data, 'address_id': self.MARSEILLE_COMMANDERIE.id},
        )
        data3 = response3.json()
        self.assertDictEqual(
            data3['source_address'], address_as_dict(self.MARSEILLE_COMMANDERIE),
        )
        self.assertListAddressAsDict(
            data3['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_MAIRIE),
            address_as_dict(self.AUBAGNE_MAIRIE),
        )

    @skipIfCustomOrganisation
    @skipIfCustomContact
    @skipIfCustomAddress
    def test_get_neighbours_credentials(self):
        self.maxDiff = None

        user = self.login_as_standard(
            allowed_apps=('creme_core', 'geolocation', 'persons'),
        )
        self.add_credentials(user.role, own='*', model=Organisation)

        self.populate_addresses(user)

        # Updating an address resets the position, so create a correct town.
        create_town(
            name='Marseille', zipcode='13002', country='FRANCE',
            latitude=43.296524, longitude=5.369821,
        )

        self.MARSEILLE_LA_MAJOR.owner = self.get_root_user().linked_contact
        self.MARSEILLE_LA_MAJOR.save()

        url = self.GET_NEIGHBOURS_URL
        GET_data = {'address_id': self.MARSEILLE_MAIRIE.id}

        # "la major" is filtered (owned by different user)
        response1 = self.assertGET200(url, data=GET_data)
        data1 = response1.json()
        self.assertDictEqual(data1['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data1['addresses'],
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
        )

        # ---
        self.client.logout()
        self.login_as_root()

        response2 = self.assertGET200(url, data=GET_data)
        data2 = response2.json()
        self.assertDictEqual(data2['source_address'], address_as_dict(self.MARSEILLE_MAIRIE))
        self.assertListAddressAsDict(
            data2['addresses'],
            address_as_dict(self.MARSEILLE_LA_MAJOR),
            address_as_dict(self.MARSEILLE_ST_VICTOR),
            address_as_dict(self.MARSEILLE_COMMANDERIE),
        )

    @skipIfCustomOrganisation
    @skipIfCustomAddress
    def test_get_neighbours_invalid_filter(self):
        user = self.login_as_root_and_get()
        self.populate_addresses(user)
        self.assertGET404(
            self.GET_NEIGHBOURS_URL,
            data={'address_id': self.MARSEILLE_MAIRIE.id, 'filter_id': 'unknown'},
        )

    def test_get_neighbours_missing_address(self):
        self.login_as_root()
        self.assertGET404(self.GET_NEIGHBOURS_URL, data={'address_id': self.UNUSED_PK})
