from datetime import date

from django.utils.translation import gettext as _

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons import get_contact_model

from .factories import (
    CivilityFactory,
    ContactFactory,
    PositionFactory,
    SectorFactory,
    UserFactory,
)

Contact = get_contact_model()

default_contact_data = {
    "description": "Description",
    "first_name": "Jean",
    "last_name": "Dupont",
    "skype": "jean.dupont",
    "phone": "+330100000000",
    "mobile": "+330600000000",
    "fax": "+330100000001",
    "email": "jean.dupont@provider.com",
    "url_site": "https://www.jean.dupont.provider.com",
    "full_position": "Full position",
    "birthday": "2000-01-01",
    "civility": None,
    "position": None,
    "sector": None,
}

default_address_data = {
    "address": "1 Main Street",
    "po_box": "PO123",
    "zipcode": "ZIP123",
    "city": "City",
    "department": "Dept",
    "state": "State",
    "country": "Country",
}


class CreateContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "last_name": ["required"],
                "user": ["required"],
            },
        )

    def test_create_contact(self):
        user = UserFactory()
        civility = CivilityFactory()
        position = PositionFactory()
        sector = SectorFactory()
        data = {
            **default_contact_data,
            "user": user.id,
            "civility": civility.id,
            "position": position.id,
            "sector": sector.id,
        }
        response = self.make_request(data=data, status_code=201)
        contact = Contact.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
            },
        )
        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.description, "Description")
        self.assertEqual(contact.last_name, "Dupont")
        self.assertEqual(contact.first_name, "Jean")
        self.assertEqual(contact.skype, "jean.dupont")
        self.assertEqual(contact.phone, "+330100000000")
        self.assertEqual(contact.mobile, "+330600000000")
        self.assertEqual(contact.fax, "+330100000001")
        self.assertEqual(contact.email, "jean.dupont@provider.com")
        self.assertEqual(contact.url_site, "https://www.jean.dupont.provider.com")
        self.assertEqual(contact.full_position, "Full position")
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)
        self.assertEqual(contact.user, user)
        self.assertEqual(contact.civility, civility)
        self.assertEqual(contact.position, position)
        self.assertEqual(contact.sector, sector)
        self.assertIsNone(contact.billing_address_id)
        self.assertIsNone(contact.shipping_address_id)

    def test_create_contact__with_addresses(self):
        user = UserFactory()
        data = {
            **default_contact_data,
            "user": user.id,
            "billing_address": {**default_address_data, "name": "NOT DISPLAYED"},
            "shipping_address": {**default_address_data, "name": "NOT DISPLAYED"},
        }
        response = self.make_request(data=data, status_code=201)
        contact = Contact.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "billing_address": default_address_data,
                "shipping_address": default_address_data,
                "is_deleted": False,
                "is_user": None,
            },
        )

        self.assertEqual(contact.birthday, date(2000, 1, 1))
        self.assertEqual(contact.description, "Description")
        self.assertEqual(contact.last_name, "Dupont")
        self.assertEqual(contact.first_name, "Jean")
        self.assertEqual(contact.skype, "jean.dupont")
        self.assertEqual(contact.phone, "+330100000000")
        self.assertEqual(contact.mobile, "+330600000000")
        self.assertEqual(contact.fax, "+330100000001")
        self.assertEqual(contact.email, "jean.dupont@provider.com")
        self.assertEqual(contact.url_site, "https://www.jean.dupont.provider.com")
        self.assertEqual(contact.full_position, "Full position")
        self.assertFalse(contact.is_deleted)
        self.assertIsNone(contact.is_user)
        self.assertEqual(contact.user, user)
        self.assertIsNone(contact.civility)
        self.assertIsNone(contact.position)
        self.assertIsNone(contact.sector)

        self.assertEqual(contact.billing_address.name, _("Billing address"))
        self.assertEqual(contact.billing_address.address, "1 Main Street")
        self.assertEqual(contact.billing_address.po_box, "PO123")
        self.assertEqual(contact.billing_address.zipcode, "ZIP123")
        self.assertEqual(contact.billing_address.city, "City")
        self.assertEqual(contact.billing_address.department, "Dept")
        self.assertEqual(contact.billing_address.state, "State")
        self.assertEqual(contact.billing_address.country, "Country")
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertEqual(contact.shipping_address.name, _("Shipping address"))
        self.assertEqual(contact.shipping_address.address, "1 Main Street")
        self.assertEqual(contact.shipping_address.po_box, "PO123")
        self.assertEqual(contact.shipping_address.zipcode, "ZIP123")
        self.assertEqual(contact.shipping_address.city, "City")
        self.assertEqual(contact.shipping_address.department, "Dept")
        self.assertEqual(contact.shipping_address.state, "State")
        self.assertEqual(contact.shipping_address.country, "Country")
        self.assertEqual(contact.shipping_address.owner, contact)


class RetrieveContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-detail"
    method = "get"

    def test_get_contact(self):
        contact = ContactFactory(shipping_address=True)
        response = self.make_request(to=contact.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                **default_contact_data,
                "id": contact.id,
                "civility": contact.civility_id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
                "position": contact.position_id,
                "sector": contact.sector_id,
                "user": contact.user_id,
                "shipping_address": default_address_data,
            },
        )


class UpdateContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-detail"
    method = "put"

    def test_validation__required(self):
        contact = ContactFactory()
        response = self.make_request(to=contact.id, data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "last_name": ["required"],
                "user": ["required"],
            },
        )

    def test_update_contact(self):
        contact = ContactFactory(shipping_address=True, civility=None)
        civility = CivilityFactory()
        sector = SectorFactory()

        data = {
            **default_contact_data,
            "user": contact.user_id,
            "civility": civility.id,
            "position": None,
            "sector": sector.id,
            "last_name": "Smith",
            "first_name": "Nick",
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
                "shipping_address": default_address_data,
            },
        )

    def test_update_contact__create_addresses(self):
        contact = ContactFactory()

        data = {
            **default_contact_data,
            "user": contact.user_id,
            "billing_address": {**default_address_data, "address": "billing street"},
            "shipping_address": {**default_address_data, "address": "shipping street"},
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
            },
        )
        self.assertEqual(contact.billing_address.name, _("Billing address"))
        self.assertEqual(contact.billing_address.address, "billing street")
        self.assertEqual(contact.billing_address.po_box, "PO123")
        self.assertEqual(contact.billing_address.zipcode, "ZIP123")
        self.assertEqual(contact.billing_address.city, "City")
        self.assertEqual(contact.billing_address.department, "Dept")
        self.assertEqual(contact.billing_address.state, "State")
        self.assertEqual(contact.billing_address.country, "Country")
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertEqual(contact.shipping_address.name, _("Shipping address"))
        self.assertEqual(contact.shipping_address.address, "shipping street")
        self.assertEqual(contact.shipping_address.po_box, "PO123")
        self.assertEqual(contact.shipping_address.zipcode, "ZIP123")
        self.assertEqual(contact.shipping_address.city, "City")
        self.assertEqual(contact.shipping_address.department, "Dept")
        self.assertEqual(contact.shipping_address.state, "State")
        self.assertEqual(contact.shipping_address.country, "Country")
        self.assertEqual(contact.shipping_address.owner, contact)

    def test_update_contact__update_addresses(self):
        contact = ContactFactory(billing_address=True, shipping_address=True)

        data = {
            **default_contact_data,
            "user": contact.user_id,
            "billing_address": {**default_address_data, "address": "billing street"},
            "shipping_address": {**default_address_data, "address": "shipping street"},
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
            },
        )
        self.assertEqual(contact.billing_address.name, _("Billing address"))
        self.assertEqual(contact.billing_address.address, "billing street")
        self.assertEqual(contact.billing_address.po_box, "PO123")
        self.assertEqual(contact.billing_address.zipcode, "ZIP123")
        self.assertEqual(contact.billing_address.city, "City")
        self.assertEqual(contact.billing_address.department, "Dept")
        self.assertEqual(contact.billing_address.state, "State")
        self.assertEqual(contact.billing_address.country, "Country")
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertEqual(contact.shipping_address.name, _("Shipping address"))
        self.assertEqual(contact.shipping_address.address, "shipping street")
        self.assertEqual(contact.shipping_address.po_box, "PO123")
        self.assertEqual(contact.shipping_address.zipcode, "ZIP123")
        self.assertEqual(contact.shipping_address.city, "City")
        self.assertEqual(contact.shipping_address.department, "Dept")
        self.assertEqual(contact.shipping_address.state, "State")
        self.assertEqual(contact.shipping_address.country, "Country")
        self.assertEqual(contact.shipping_address.owner, contact)


class PartialUpdateContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-detail"
    method = "patch"

    def test_partial_update_contact(self):
        contact = ContactFactory(
            shipping_address=True, sector=None, civility=None, position=None
        )
        sector = SectorFactory()
        data = {"first_name": "Nick", "last_name": "Smith", "sector": sector.id}
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_contact_data,
                "id": contact.id,
                "user": contact.user_id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
                "shipping_address": default_address_data,
                **data,
            },
        )
        self.assertEqual(contact.first_name, "Nick")
        self.assertEqual(contact.last_name, "Smith")
        self.assertEqual(contact.sector, sector)

    def test_partial_update_contact__create_addresses(self):
        contact = ContactFactory(sector=None, civility=None, position=None)

        data = {
            "billing_address": {"address": "billing street"},
            "shipping_address": {"address": "shipping street"},
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_contact_data,
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
                "user": contact.user_id,
                "billing_address": {
                    "address": "billing street",
                    "city": "",
                    "country": "",
                    "department": "",
                    "po_box": "",
                    "state": "",
                    "zipcode": "",
                },
                "shipping_address": {
                    "address": "shipping street",
                    "city": "",
                    "country": "",
                    "department": "",
                    "po_box": "",
                    "state": "",
                    "zipcode": "",
                },
            },
        )

        self.assertEqual(contact.billing_address.name, _("Billing address"))
        self.assertEqual(contact.billing_address.address, "billing street")
        self.assertEqual(contact.billing_address.po_box, "")
        self.assertEqual(contact.billing_address.zipcode, "")
        self.assertEqual(contact.billing_address.city, "")
        self.assertEqual(contact.billing_address.department, "")
        self.assertEqual(contact.billing_address.state, "")
        self.assertEqual(contact.billing_address.country, "")
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertEqual(contact.shipping_address.name, _("Shipping address"))
        self.assertEqual(contact.shipping_address.address, "shipping street")
        self.assertEqual(contact.shipping_address.po_box, "")
        self.assertEqual(contact.shipping_address.zipcode, "")
        self.assertEqual(contact.shipping_address.city, "")
        self.assertEqual(contact.shipping_address.department, "")
        self.assertEqual(contact.shipping_address.state, "")
        self.assertEqual(contact.shipping_address.country, "")
        self.assertEqual(contact.shipping_address.owner, contact)

    def test_partial_update_contact__update_addresses(self):
        contact = ContactFactory(billing_address=True, shipping_address=True)

        data = {
            "billing_address": {
                "address": "billing street",
            },
            "shipping_address": {
                "address": "shipping street",
            },
        }
        response = self.make_request(to=contact.id, data=data, status_code=200)
        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_contact_data,
                "id": contact.id,
                "birthday": "2000-01-01",
                "civility": contact.civility_id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
                "is_user": None,
                "position": contact.position_id,
                "sector": contact.sector_id,
                "user": contact.user_id,
                "billing_address": {
                    **default_address_data,
                    "address": "billing street",
                },
                "shipping_address": {
                    **default_address_data,
                    "address": "shipping street",
                },
            },
        )
        self.assertEqual(contact.billing_address.name, _("Billing address"))
        self.assertEqual(contact.billing_address.address, "billing street")
        self.assertEqual(contact.billing_address.po_box, "PO123")
        self.assertEqual(contact.billing_address.zipcode, "ZIP123")
        self.assertEqual(contact.billing_address.city, "City")
        self.assertEqual(contact.billing_address.department, "Dept")
        self.assertEqual(contact.billing_address.state, "State")
        self.assertEqual(contact.billing_address.country, "Country")
        self.assertEqual(contact.billing_address.owner, contact)

        self.assertEqual(contact.shipping_address.name, _("Shipping address"))
        self.assertEqual(contact.shipping_address.address, "shipping street")
        self.assertEqual(contact.shipping_address.po_box, "PO123")
        self.assertEqual(contact.shipping_address.zipcode, "ZIP123")
        self.assertEqual(contact.shipping_address.city, "City")
        self.assertEqual(contact.shipping_address.department, "Dept")
        self.assertEqual(contact.shipping_address.state, "State")
        self.assertEqual(contact.shipping_address.country, "Country")
        self.assertEqual(contact.shipping_address.owner, contact)


class ListContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-list"
    method = "get"

    def test_list_contacts(self):
        fulbert = Contact.objects.get()
        contact = ContactFactory(
            user=fulbert.user, billing_address=True, shipping_address=True
        )
        self.assertEqual(Contact.objects.count(), 2, Contact.objects.all())

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {
                    "id": fulbert.id,
                    "birthday": None,
                    "civility": None,
                    "uuid": str(fulbert.uuid),
                    "created": self.to_iso8601(fulbert.created),
                    "modified": self.to_iso8601(fulbert.modified),
                    "description": "",
                    "email": fulbert.email,
                    "fax": "",
                    "first_name": "Fulbert",
                    "full_position": "",
                    "is_deleted": False,
                    "is_user": fulbert.is_user_id,
                    "last_name": "Creme",
                    "mobile": "",
                    "phone": "",
                    "position": None,
                    "sector": None,
                    "skype": "",
                    "url_site": "",
                    "user": fulbert.user_id,
                },
                {
                    **default_contact_data,
                    "id": contact.id,
                    "civility": contact.civility_id,
                    "uuid": str(contact.uuid),
                    "created": self.to_iso8601(contact.created),
                    "modified": self.to_iso8601(contact.modified),
                    "is_deleted": False,
                    "is_user": None,
                    "position": contact.position_id,
                    "sector": contact.sector_id,
                    "user": fulbert.user_id,
                    "billing_address": default_address_data,
                    "shipping_address": default_address_data,
                },
            ],
        )


class TrashContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-trash"
    method = "post"

    def test_trash_contact__protected(self):
        fulbert = Contact.objects.get()
        response = self.make_request(to=fulbert.id, status_code=422)
        self.assertEqual(response.data["detail"].code, "protected")

    def test_trash_contact(self):
        contact = ContactFactory()
        response = self.make_request(to=contact.id, status_code=200)

        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": True,
            },
        )
        self.make_request(to=contact.id, status_code=200)


class RestoreContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-restore"
    method = "post"

    def test_restore_contact(self):
        contact = ContactFactory(is_deleted=True)
        contact.refresh_from_db()
        self.assertTrue(contact.is_deleted)

        response = self.make_request(to=contact.id, status_code=200)

        contact.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                "id": contact.id,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "is_deleted": False,
            },
        )
        self.make_request(to=contact.id, status_code=200)


class DeleteContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-detail"
    method = "delete"

    def test_delete_contact__protected(self):
        fulbert = Contact.objects.get()
        response = self.make_request(to=fulbert.id, status_code=422)
        self.assertEqual(response.data["detail"].code, "protected")

    def test_delete_contact(self):
        contact = ContactFactory()
        self.make_request(to=contact.id, status_code=204)
        self.assertFalse(Contact.objects.filter(id=contact.id).exists())


class CloneContactTestCase(CremeAPITestCase):
    url_name = "creme_api__contacts-clone"
    method = "post"

    def test_clone_contact(self):
        fulbert = Contact.objects.get()

        response = self.make_request(to=fulbert.id, status_code=201)
        contact = Contact.objects.get(id=response.data["id"])
        self.assertNotEqual(fulbert.id, contact.id)
        self.assertNotEqual(fulbert.uuid, contact.uuid)
        self.assertPayloadEqual(
            response,
            {
                "id": contact.id,
                "birthday": None,
                "civility": None,
                "uuid": str(contact.uuid),
                "created": self.to_iso8601(contact.created),
                "modified": self.to_iso8601(contact.modified),
                "description": "",
                "email": fulbert.email,
                "fax": "",
                "first_name": "Fulbert",
                "full_position": "",
                "is_deleted": False,
                "is_user": None,
                "last_name": "Creme",
                "mobile": "",
                "phone": "",
                "position": None,
                "sector": None,
                "skype": "",
                "url_site": "",
                "user": fulbert.user_id,
            },
        )
