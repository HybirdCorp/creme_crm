from datetime import date

from django.utils.translation import gettext as _

from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons import get_contact_model

Contact = get_contact_model()


@Factory.register
def contact(factory, **kwargs):
    if 'user' not in kwargs:
        kwargs['user'] = factory.user()

    data = factory.contact_data(**kwargs)

    if 'civility' not in data:
        data['civility'] = factory.civility()

    if 'position' not in data:
        data['position'] = factory.position()

    if 'sector' not in data:
        data['sector'] = factory.sector()

    if 'billing_address' not in data:
        data['billing_address'] = factory.address_data()

    if 'shipping_address' not in data:
        data['shipping_address'] = factory.address_data()

    billing_address_data = data.pop('billing_address')
    shipping_address_data = data.pop('shipping_address')
    contact = Contact.objects.create(**data)
    if billing_address_data:
        contact.billing_address = factory.address(owner=contact, **billing_address_data)
    if shipping_address_data:
        contact.shipping_address = factory.address(owner=contact, **shipping_address_data)
    contact.save()
    return contact


@Factory.register
def contact_data(factory, **kwargs):
    if 'user' not in kwargs:
        kwargs['user'] = factory.user().id

    data = {
        'description': "Description",
        'last_name': "Dupont",
        'first_name': "Jean",
        'skype': "jean.dupont",
        'phone': "+330100000000",
        'mobile': "+330600000000",
        'fax': "+330100000001",
        'email': "jean.dupont@provider.com",
        'url_site': "https://www.jean-dupont.provider.com",
        'full_position': "Full position",
        'birthday': "2000-01-01",
    }
    data.update(**kwargs)
    return data


class CreateContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(response, {
            'last_name': ['required'],
            'user': ['required'],
        })

    def test_create_contact(self):
        user = self.factory.user()
        civility = self.factory.civility()
        position = self.factory.position()
        sector = self.factory.sector()
        data = self.factory.contact_data(
            user=user.id,
            civility=civility.id,
            position=position.id,
            sector=sector.id,
        )
        response = self.make_request(data=data, status_code=201)
        contact = Contact.objects.get(id=response.data['id'])
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': civility.id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': position.id,
            'sector': sector.id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': user.id,
        })
        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.user, user)
        self.assertEqual(contact.description, 'Description')
        self.assertEqual(contact.civility, civility)
        self.assertEqual(contact.position, position)
        self.assertEqual(contact.sector, sector)
        self.assertEqual(contact.last_name, 'Dupont')
        self.assertEqual(contact.first_name, 'Jean')
        self.assertEqual(contact.skype, 'jean.dupont')
        self.assertEqual(contact.phone, '+330100000000')
        self.assertEqual(contact.mobile, '+330600000000')
        self.assertEqual(contact.fax, '+330100000001')
        self.assertEqual(contact.email, 'jean.dupont@provider.com')
        self.assertEqual(contact.url_site, 'https://www.jean-dupont.provider.com')
        self.assertEqual(contact.full_position, 'Full position')
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)
        self.assertIsNone(contact.billing_address_id)
        self.assertIsNone(contact.shipping_address_id)

    def test_create_contact__with_addresses(self):
        billing_address_data = self.factory.address_data()
        shipping_address_data = self.factory.address_data()
        data = self.factory.contact_data(
            billing_address={**billing_address_data, 'name': "NOT USED"},
            shipping_address={**shipping_address_data, 'name': "NOT USED"},
        )
        response = self.make_request(data=data, status_code=201)
        contact = Contact.objects.get(id=response.data['id'])
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': None,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': None,
            'sector': None,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': data['user'],
            'billing_address': {
                'address': '1 Main Street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
            'shipping_address': {
                'address': '1 Main Street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })

        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.user_id, data['user'])
        self.assertEqual(contact.description, 'Description')
        self.assertEqual(contact.last_name, 'Dupont')
        self.assertEqual(contact.first_name, 'Jean')
        self.assertEqual(contact.skype, 'jean.dupont')
        self.assertEqual(contact.phone, '+330100000000')
        self.assertEqual(contact.mobile, '+330600000000')
        self.assertEqual(contact.fax, '+330100000001')
        self.assertEqual(contact.email, 'jean.dupont@provider.com')
        self.assertEqual(contact.url_site, 'https://www.jean-dupont.provider.com')
        self.assertEqual(contact.full_position, 'Full position')
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)

        billing_address = contact.billing_address
        self.assertEqual(billing_address.name, _('Billing address'))
        self.assertEqual(billing_address.address, billing_address_data['address'])
        self.assertEqual(billing_address.po_box, billing_address_data['po_box'])
        self.assertEqual(billing_address.zipcode, billing_address_data['zipcode'])
        self.assertEqual(billing_address.city, billing_address_data['city'])
        self.assertEqual(billing_address.department, billing_address_data['department'])
        self.assertEqual(billing_address.state, billing_address_data['state'])
        self.assertEqual(billing_address.country, billing_address_data['country'])
        self.assertEqual(billing_address.owner, contact)

        shipping_address = contact.shipping_address
        self.assertEqual(shipping_address.name, _('Shipping address'))
        self.assertEqual(shipping_address.address, shipping_address_data['address'])
        self.assertEqual(shipping_address.po_box, shipping_address_data['po_box'])
        self.assertEqual(shipping_address.zipcode, shipping_address_data['zipcode'])
        self.assertEqual(shipping_address.city, shipping_address_data['city'])
        self.assertEqual(shipping_address.department, shipping_address_data['department'])
        self.assertEqual(shipping_address.state, shipping_address_data['state'])
        self.assertEqual(shipping_address.country, shipping_address_data['country'])
        self.assertEqual(shipping_address.owner, contact)


class RetrieveContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-detail'
    method = 'get'

    def test_get_contact(self):
        contact = self.factory.contact(billing_address=None)
        response = self.make_request(to=contact.id, status_code=200)
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'shipping_address': {
                'address': '1 Main Street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })


class UpdateContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-detail'
    method = 'put'

    def test_validation__required(self):
        contact = self.factory.contact()
        response = self.make_request(to=contact.id, data={}, status_code=400)
        self.assertValidationErrors(response, {
            'last_name': ['required'],
            'user': ['required'],
        })

    def test_update_contact(self):
        contact = self.factory.contact(billing_address=None, civility=None)
        civility = self.factory.civility()
        sector = self.factory.sector()

        data = self.factory.contact_data(
            user=contact.user_id,
            civility=civility.id,
            position=None,
            sector=sector.id,
            last_name="Smith",
            first_name="Nick",
        )
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': civility.id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Nick',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Smith',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': None,
            'sector': sector.id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'shipping_address': {
                'address': '1 Main Street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })
        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.user_id, data['user'])
        self.assertEqual(contact.description, 'Description')
        self.assertEqual(contact.civility, civility)
        self.assertIsNone(contact.position)
        self.assertEqual(contact.sector, sector)
        self.assertEqual(contact.first_name, "Nick")
        self.assertEqual(contact.last_name, "Smith")
        self.assertEqual(contact.skype, 'jean.dupont')
        self.assertEqual(contact.phone, '+330100000000')
        self.assertEqual(contact.mobile, '+330600000000')
        self.assertEqual(contact.fax, '+330100000001')
        self.assertEqual(contact.email, 'jean.dupont@provider.com')
        self.assertEqual(contact.url_site, 'https://www.jean-dupont.provider.com')
        self.assertEqual(contact.full_position, 'Full position')
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)

    def test_update_contact__create_addresses(self):
        contact = self.factory.contact(billing_address=None, shipping_address=None)

        billing_address_data = self.factory.address_data(address='billing street')
        shipping_address_data = self.factory.address_data(address='shipping street')
        data = self.factory.contact_data(
            user=contact.user_id,
            billing_address=billing_address_data,
            shipping_address=shipping_address_data,
        )
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'billing_address': {
                'address': 'billing street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
            'shipping_address': {
                'address': 'shipping street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })
        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.user_id, data['user'])
        self.assertEqual(contact.description, 'Description')
        self.assertEqual(contact.first_name, "Jean")
        self.assertEqual(contact.last_name, "Dupont")
        self.assertEqual(contact.skype, 'jean.dupont')
        self.assertEqual(contact.phone, '+330100000000')
        self.assertEqual(contact.mobile, '+330600000000')
        self.assertEqual(contact.fax, '+330100000001')
        self.assertEqual(contact.email, 'jean.dupont@provider.com')
        self.assertEqual(contact.url_site, 'https://www.jean-dupont.provider.com')
        self.assertEqual(contact.full_position, 'Full position')
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)

        billing_address = contact.billing_address
        self.assertEqual(billing_address.name, _('Billing address'))
        self.assertEqual(billing_address.address, billing_address_data['address'])
        self.assertEqual(billing_address.po_box, billing_address_data['po_box'])
        self.assertEqual(billing_address.zipcode, billing_address_data['zipcode'])
        self.assertEqual(billing_address.city, billing_address_data['city'])
        self.assertEqual(billing_address.department, billing_address_data['department'])
        self.assertEqual(billing_address.state, billing_address_data['state'])
        self.assertEqual(billing_address.country, billing_address_data['country'])
        self.assertEqual(billing_address.owner, contact)

        shipping_address = contact.shipping_address
        self.assertEqual(shipping_address.name, _('Shipping address'))
        self.assertEqual(shipping_address.address, shipping_address_data['address'])
        self.assertEqual(shipping_address.po_box, shipping_address_data['po_box'])
        self.assertEqual(shipping_address.zipcode, shipping_address_data['zipcode'])
        self.assertEqual(shipping_address.city, shipping_address_data['city'])
        self.assertEqual(shipping_address.department, shipping_address_data['department'])
        self.assertEqual(shipping_address.state, shipping_address_data['state'])
        self.assertEqual(shipping_address.country, shipping_address_data['country'])
        self.assertEqual(shipping_address.owner, contact)

    def test_update_contact__update_addresses(self):
        contact = self.factory.contact()
        billing_address = contact.billing_address
        shipping_address = contact.shipping_address

        billing_address_data = self.factory.address_data(address='billing street')
        shipping_address_data = self.factory.address_data(address='shipping street')
        data = self.factory.contact_data(
            user=contact.user_id,
            billing_address=billing_address_data,
            shipping_address=shipping_address_data,
        )
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'billing_address': {
                'address': 'billing street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
            'shipping_address': {
                'address': 'shipping street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })

        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.user_id, contact.user_id)
        self.assertEqual(contact.description, 'Description')
        self.assertEqual(contact.first_name, "Jean")
        self.assertEqual(contact.last_name, "Dupont")
        self.assertEqual(contact.skype, 'jean.dupont')
        self.assertEqual(contact.phone, '+330100000000')
        self.assertEqual(contact.mobile, '+330600000000')
        self.assertEqual(contact.fax, '+330100000001')
        self.assertEqual(contact.email, 'jean.dupont@provider.com')
        self.assertEqual(contact.url_site, 'https://www.jean-dupont.provider.com')
        self.assertEqual(contact.full_position, 'Full position')
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)

        billing_address.refresh_from_db()
        self.assertEqual(billing_address.name, _('Billing address'))
        self.assertEqual(billing_address.address, billing_address_data['address'])
        self.assertEqual(billing_address.po_box, billing_address_data['po_box'])
        self.assertEqual(billing_address.zipcode, billing_address_data['zipcode'])
        self.assertEqual(billing_address.city, billing_address_data['city'])
        self.assertEqual(billing_address.department, billing_address_data['department'])
        self.assertEqual(billing_address.state, billing_address_data['state'])
        self.assertEqual(billing_address.country, billing_address_data['country'])
        self.assertEqual(billing_address.owner, contact)

        shipping_address.refresh_from_db()
        self.assertEqual(shipping_address.name, _('Shipping address'))
        self.assertEqual(shipping_address.address, shipping_address_data['address'])
        self.assertEqual(shipping_address.po_box, shipping_address_data['po_box'])
        self.assertEqual(shipping_address.zipcode, shipping_address_data['zipcode'])
        self.assertEqual(shipping_address.city, shipping_address_data['city'])
        self.assertEqual(shipping_address.department, shipping_address_data['department'])
        self.assertEqual(shipping_address.state, shipping_address_data['state'])
        self.assertEqual(shipping_address.country, shipping_address_data['country'])
        self.assertEqual(shipping_address.owner, contact)


class PartialUpdateContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-detail'
    method = 'patch'

    def test_partial_update_contact(self):
        contact = self.factory.contact(billing_address=None)
        data = {
            'first_name': "Nick",
            'last_name': "Smith",
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Nick',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Smith',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'shipping_address': {
                'address': '1 Main Street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })
        self.assertEqual(contact.first_name, "Nick")
        self.assertEqual(contact.last_name, "Smith")

    def test_partial_update_contact__create_addresses(self):
        contact = self.factory.contact(billing_address=None, shipping_address=None)

        data = {
            'billing_address': {
                'address': 'billing street',
            },
            'shipping_address': {
                'address': 'shipping street',
            },
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'billing_address': {
                'address': 'billing street',
                'city': '',
                'country': '',
                'department': '',
                'po_box': '',
                'state': '',
                'zipcode': '',
            },
            'shipping_address': {
                'address': 'shipping street',
                'city': '',
                'country': '',
                'department': '',
                'po_box': '',
                'state': '',
                'zipcode': '',
            },
        })

        billing_address = contact.billing_address
        self.assertEqual(billing_address.name, _('Billing address'))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "")
        self.assertEqual(billing_address.zipcode, "")
        self.assertEqual(billing_address.city, "")
        self.assertEqual(billing_address.department, "")
        self.assertEqual(billing_address.state, "")
        self.assertEqual(billing_address.country, "")
        self.assertEqual(billing_address.owner, contact)

        shipping_address = contact.shipping_address
        self.assertEqual(shipping_address.name, _('Shipping address'))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "")
        self.assertEqual(shipping_address.zipcode, "")
        self.assertEqual(shipping_address.city, "")
        self.assertEqual(shipping_address.department, "")
        self.assertEqual(shipping_address.state, "")
        self.assertEqual(shipping_address.country, "")
        self.assertEqual(shipping_address.owner, contact)

    def test_partial_update_contact__update_addresses(self):
        contact = self.factory.contact()
        billing_address = contact.billing_address
        shipping_address = contact.shipping_address

        data = {
            'billing_address': {
                'address': 'billing street',
            },
            'shipping_address': {
                'address': 'shipping street',
            },
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': '2000-01-01',
            'civility': contact.civility_id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': 'Description',
            'email': 'jean.dupont@provider.com',
            'fax': '+330100000001',
            'first_name': 'Jean',
            'full_position': 'Full position',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Dupont',
            'mobile': '+330600000000',
            'phone': '+330100000000',
            'position': contact.position_id,
            'sector': contact.sector_id,
            'skype': 'jean.dupont',
            'url_site': 'https://www.jean-dupont.provider.com',
            'user': contact.user_id,
            'billing_address': {
                'address': 'billing street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
            'shipping_address': {
                'address': 'shipping street',
                'city': 'City',
                'country': 'Country',
                'department': 'Dept',
                'po_box': 'PO123',
                'state': 'State',
                'zipcode': 'ZIP123',
            },
        })
        billing_address.refresh_from_db()
        self.assertEqual(billing_address.name, _('Billing address'))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "PO123")
        self.assertEqual(billing_address.zipcode, "ZIP123")
        self.assertEqual(billing_address.city, "City")
        self.assertEqual(billing_address.department, "Dept")
        self.assertEqual(billing_address.state, "State")
        self.assertEqual(billing_address.country, "Country")
        self.assertEqual(billing_address.owner, contact)
        shipping_address.refresh_from_db()
        self.assertEqual(shipping_address.name, _('Shipping address'))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, contact)


class ListContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-list'
    method = 'get'

    def test_list_contacts(self):
        fulbert = Contact.objects.get()
        contact = self.factory.contact(user=fulbert.user)
        self.assertEqual(Contact.objects.count(), 2, Contact.objects.all())

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(response, [
            {
                'id': fulbert.id,
                'birthday': None,
                'civility': None,
                'uuid': str(fulbert.uuid),
                'created': self.to_iso8601(fulbert.created),
                'modified': self.to_iso8601(fulbert.modified),
                'description': '',
                'email': fulbert.email,
                'fax': '',
                'first_name': 'Fulbert',
                'full_position': '',
                'is_deleted': False,
                'is_user': fulbert.is_user_id,
                'last_name': 'Creme',
                'mobile': '',
                'phone': '',
                'position': None,
                'sector': None,
                'skype': '',
                'url_site': '',
                'user': fulbert.user_id,
            },
            {
                'id': contact.id,
                'birthday': '2000-01-01',
                'civility': contact.civility_id,
                'uuid': str(contact.uuid),
                'created': self.to_iso8601(contact.created),
                'modified': self.to_iso8601(contact.modified),
                'description': 'Description',
                'email': 'jean.dupont@provider.com',
                'fax': '+330100000001',
                'first_name': 'Jean',
                'full_position': 'Full position',
                'is_deleted': False,
                'is_user': None,
                'last_name': 'Dupont',
                'mobile': '+330600000000',
                'phone': '+330100000000',
                'position': contact.position_id,
                'sector': contact.sector_id,
                'skype': 'jean.dupont',
                'url_site': 'https://www.jean-dupont.provider.com',
                'user': fulbert.user_id,
                'billing_address': {
                    'address': '1 Main Street',
                    'city': 'City',
                    'country': 'Country',
                    'department': 'Dept',
                    'po_box': 'PO123',
                    'state': 'State',
                    'zipcode': 'ZIP123',
                },
                'shipping_address': {
                    'address': '1 Main Street',
                    'city': 'City',
                    'country': 'Country',
                    'department': 'Dept',
                    'po_box': 'PO123',
                    'state': 'State',
                    'zipcode': 'ZIP123',
                },
            }
        ])


class TrashContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-trash'
    method = 'post'

    def test_trash_contact__protected(self):
        fulbert = Contact.objects.get()
        response = self.make_request(to=fulbert.id, status_code=422)
        self.assertEqual(response.data['detail'].code, 'protected')

    def test_trash_contact(self):
        contact = self.factory.contact()
        response = self.make_request(to=contact.id, status_code=200)

        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'is_deleted': True,
        })
        self.make_request(to=contact.id, status_code=200)


class RestoreContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-restore'
    method = 'post'

    def test_restore_contact(self):
        contact = self.factory.contact(is_deleted=True)
        contact.refresh_from_db()
        self.assertTrue(contact.is_deleted)

        response = self.make_request(to=contact.id, status_code=200)

        contact.refresh_from_db()
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'is_deleted': False,
        })
        self.make_request(to=contact.id, status_code=200)


class DeleteContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-detail'
    method = 'delete'

    def test_delete_contact__protected(self):
        fulbert = Contact.objects.get()
        response = self.make_request(to=fulbert.id, status_code=422)
        self.assertEqual(response.data['detail'].code, 'protected')

    def test_delete_contact(self):
        contact = self.factory.contact()
        self.make_request(to=contact.id, status_code=204)
        self.assertFalse(Contact.objects.filter(id=contact.id).exists())


class CloneContactTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-clone'
    method = 'post'

    def test_clone_contact(self):
        fulbert = Contact.objects.get()

        response = self.make_request(to=fulbert.id, status_code=201)
        contact = Contact.objects.get(id=response.data['id'])
        self.assertNotEqual(fulbert.id, contact.id)
        self.assertNotEqual(fulbert.uuid, contact.uuid)
        self.assertPayloadEqual(response, {
            'id': contact.id,
            'birthday': None,
            'civility': None,
            'uuid': str(contact.uuid),
            'created': self.to_iso8601(contact.created),
            'modified': self.to_iso8601(contact.modified),
            'description': '',
            'email': fulbert.email,
            'fax': '',
            'first_name': 'Fulbert',
            'full_position': '',
            'is_deleted': False,
            'is_user': None,
            'last_name': 'Creme',
            'mobile': '',
            'phone': '',
            'position': None,
            'sector': None,
            'skype': '',
            'url_site': '',
            'user': fulbert.user_id,
        })


class ListContactAddressesTestCase(CremeAPITestCase):
    url_name = 'creme_api__contacts-addresses'
    method = 'get'

    def test_delete_contact__protected(self):
        fulbert = Contact.objects.get()
        response = self.make_request(to=fulbert.id, status_code=422)
        self.assertEqual(response.data['detail'].code, 'protected')

    def test_delete_contact(self):
        contact = self.factory.contact()
        self.make_request(to=contact.id, status_code=204)
        self.assertFalse(Contact.objects.filter(id=contact.id).exists())
