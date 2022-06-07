from datetime import date

from django.utils.translation import gettext as _

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons import get_organisation_model

from .factories import (
    LegalFormFactory,
    OrganisationFactory,
    SectorFactory,
    StaffSizeFactory,
    UserFactory,
)

Organisation = get_organisation_model()

default_organisation_data = {
    "description": "Description",
    "name": "Creme Organisation",
    "phone": "+330100000000",
    "fax": "+330100000001",
    "email": "creme.organisation@provider.com",
    "url_site": "https://www.creme.organisation.provider.com",
    "capital": 50000,
    "annual_revenue": "1500000",
    "siren": "001001001001",
    "naf": "002002002002",
    "siret": "003003003003",
    "rcs": "004004004004",
    "tvaintra": "005005005005",
    "subject_to_vat": True,
    "creation_date": "2005-05-24",
    "sector": None,
    "legal_form": None,
    "staff_size": None,
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


class CreateOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "name": ["required"],
                "user": ["required"],
            },
        )

    def test_create_organisation(self):
        user = UserFactory()
        sector = SectorFactory()
        legal_form = LegalFormFactory()
        staff_size = StaffSizeFactory()
        data = {
            **default_organisation_data,
            "user": user.id,
            "sector": sector.id,
            "legal_form": legal_form.id,
            "staff_size": staff_size.id,
        }
        response = self.make_request(data=data, status_code=201)
        organisation = Organisation.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
            },
        )
        self.assertFalse(organisation.is_deleted)
        self.assertEqual(organisation.user, user)
        self.assertEqual(organisation.description, "Description")
        self.assertIsNone(organisation.billing_address)
        self.assertIsNone(organisation.shipping_address)
        self.assertEqual(organisation.name, "Creme Organisation")
        self.assertFalse(organisation.is_managed)
        self.assertEqual(organisation.phone, "+330100000000")
        self.assertEqual(organisation.fax, "+330100000001")
        self.assertEqual(organisation.email, "creme.organisation@provider.com")
        self.assertEqual(
            organisation.url_site, "https://www.creme.organisation.provider.com"
        )
        self.assertEqual(organisation.sector, sector)
        self.assertEqual(organisation.legal_form, legal_form)
        self.assertEqual(organisation.staff_size, staff_size)
        self.assertEqual(organisation.capital, 50000)
        self.assertEqual(organisation.annual_revenue, "1500000")
        self.assertEqual(organisation.siren, "001001001001")
        self.assertEqual(organisation.naf, "002002002002")
        self.assertEqual(organisation.siret, "003003003003")
        self.assertEqual(organisation.rcs, "004004004004")
        self.assertEqual(organisation.tvaintra, "005005005005")
        self.assertTrue(organisation.subject_to_vat)
        self.assertEqual(organisation.creation_date, date(2005, 5, 24))

    def test_create_organisation__managed_readonly(self):
        user = UserFactory()
        data = {
            **default_organisation_data,
            "user": user.id,
            "is_managed": True,
        }
        response = self.make_request(data=data, status_code=201)
        organisation = Organisation.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_managed": False,
                "is_deleted": False,
            },
        )
        self.assertFalse(organisation.is_managed)

    def test_create_organisation__with_addresses(self):
        user = UserFactory()
        data = {
            **default_organisation_data,
            "user": user.id,
            "billing_address": {**default_address_data, "name": "NOT DISPLAYED"},
            "shipping_address": {**default_address_data, "name": "NOT DISPLAYED"},
        }
        response = self.make_request(data=data, status_code=201)
        organisation = Organisation.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
                "billing_address": default_address_data,
                "shipping_address": default_address_data,
            },
        )

        billing_address = organisation.billing_address
        self.assertEqual(billing_address.name, _("Billing address"))
        self.assertEqual(billing_address.address, "1 Main Street")
        self.assertEqual(billing_address.po_box, "PO123")
        self.assertEqual(billing_address.zipcode, "ZIP123")
        self.assertEqual(billing_address.city, "City")
        self.assertEqual(billing_address.department, "Dept")
        self.assertEqual(billing_address.state, "State")
        self.assertEqual(billing_address.country, "Country")
        self.assertEqual(billing_address.owner, organisation)

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "1 Main Street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, organisation)


class RetrieveOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-detail"
    method = "get"

    def test_get_organisation(self):
        organisation = OrganisationFactory(shipping_address=True)
        response = self.make_request(to=organisation.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "description": "Description",
                "name": "Creme Organisation",
                "phone": "+330100000000",
                "fax": "+330100000001",
                "email": "creme.organisation@provider.com",
                "url_site": "https://www.creme.organisation.provider.com",
                "capital": 50000,
                "annual_revenue": "1500000",
                "siren": "001001001001",
                "naf": "002002002002",
                "siret": "003003003003",
                "rcs": "004004004004",
                "tvaintra": "005005005005",
                "subject_to_vat": True,
                "creation_date": "2005-05-24",
                "is_deleted": False,
                "is_managed": False,
                "sector": organisation.sector_id,
                "legal_form": organisation.legal_form_id,
                "staff_size": organisation.staff_size_id,
                "user": organisation.user_id,
                "shipping_address": default_address_data,
            },
        )


class UpdateOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-detail"
    method = "put"

    def test_validation__required(self):
        organisation = OrganisationFactory()
        response = self.make_request(to=organisation.id, data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "name": ["required"],
                "user": ["required"],
            },
        )

    def test_update_organisation(self):
        organisation = OrganisationFactory(shipping_address=True, sector=None)
        user = UserFactory()
        legal_form = LegalFormFactory()
        sector = SectorFactory()

        data = {
            **default_organisation_data,
            "user": user.id,
            "legal_form": legal_form.id,
            "staff_size": None,
            "sector": sector.id,
            "name": "A Creme Company",
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
                "shipping_address": default_address_data,
            },
        )
        self.assertFalse(organisation.is_deleted)
        self.assertEqual(organisation.user, organisation.user)
        self.assertEqual(organisation.description, "Description")
        self.assertIsNone(organisation.billing_address)
        self.assertEqual(organisation.name, "A Creme Company")
        self.assertFalse(organisation.is_managed)
        self.assertEqual(organisation.phone, "+330100000000")
        self.assertEqual(organisation.fax, "+330100000001")
        self.assertEqual(organisation.email, "creme.organisation@provider.com")
        self.assertEqual(
            organisation.url_site, "https://www.creme.organisation.provider.com"
        )
        self.assertEqual(organisation.sector, sector)
        self.assertEqual(organisation.legal_form, legal_form)
        self.assertIsNone(organisation.staff_size)
        self.assertEqual(organisation.capital, 50000)
        self.assertEqual(organisation.annual_revenue, "1500000")
        self.assertEqual(organisation.siren, "001001001001")
        self.assertEqual(organisation.naf, "002002002002")
        self.assertEqual(organisation.siret, "003003003003")
        self.assertEqual(organisation.rcs, "004004004004")
        self.assertEqual(organisation.tvaintra, "005005005005")
        self.assertTrue(organisation.subject_to_vat)
        self.assertEqual(organisation.creation_date, date(2005, 5, 24))

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "1 Main Street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, organisation)

    def test_update_organisation__create_addresses(self):
        organisation = OrganisationFactory()

        data = {
            **default_organisation_data,
            "user": organisation.user_id,
            "billing_address": {**default_address_data, "address": "billing street"},
            "shipping_address": {**default_address_data, "address": "shipping street"},
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
            },
        )
        self.assertFalse(organisation.is_deleted)
        self.assertEqual(organisation.user, organisation.user)
        self.assertEqual(organisation.description, "Description")
        self.assertEqual(organisation.name, "Creme Organisation")
        self.assertFalse(organisation.is_managed)
        self.assertEqual(organisation.phone, "+330100000000")
        self.assertEqual(organisation.fax, "+330100000001")
        self.assertEqual(organisation.email, "creme.organisation@provider.com")
        self.assertEqual(
            organisation.url_site, "https://www.creme.organisation.provider.com"
        )
        self.assertEqual(organisation.capital, 50000)
        self.assertEqual(organisation.annual_revenue, "1500000")
        self.assertEqual(organisation.siren, "001001001001")
        self.assertEqual(organisation.naf, "002002002002")
        self.assertEqual(organisation.siret, "003003003003")
        self.assertEqual(organisation.rcs, "004004004004")
        self.assertEqual(organisation.tvaintra, "005005005005")
        self.assertTrue(organisation.subject_to_vat)
        self.assertEqual(organisation.creation_date, date(2005, 5, 24))

        billing_address = organisation.billing_address
        self.assertEqual(billing_address.name, _("Billing address"))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "PO123")
        self.assertEqual(billing_address.zipcode, "ZIP123")
        self.assertEqual(billing_address.city, "City")
        self.assertEqual(billing_address.department, "Dept")
        self.assertEqual(billing_address.state, "State")
        self.assertEqual(billing_address.country, "Country")
        self.assertEqual(billing_address.owner, organisation)

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, organisation)

    def test_update_organisation__update_addresses(self):
        organisation = OrganisationFactory(billing_address=True, shipping_address=True)

        data = {
            **default_organisation_data,
            "user": organisation.user_id,
            "billing_address": {**default_address_data, "address": "billing street"},
            "shipping_address": {**default_address_data, "address": "shipping street"},
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
            },
        )

        self.assertFalse(organisation.is_deleted)
        self.assertEqual(organisation.user, organisation.user)
        self.assertEqual(organisation.description, "Description")
        self.assertEqual(organisation.name, "Creme Organisation")
        self.assertFalse(organisation.is_managed)
        self.assertEqual(organisation.phone, "+330100000000")
        self.assertEqual(organisation.fax, "+330100000001")
        self.assertEqual(organisation.email, "creme.organisation@provider.com")
        self.assertEqual(
            organisation.url_site, "https://www.creme.organisation.provider.com"
        )
        self.assertEqual(organisation.capital, 50000)
        self.assertEqual(organisation.annual_revenue, "1500000")
        self.assertEqual(organisation.siren, "001001001001")
        self.assertEqual(organisation.naf, "002002002002")
        self.assertEqual(organisation.siret, "003003003003")
        self.assertEqual(organisation.rcs, "004004004004")
        self.assertEqual(organisation.tvaintra, "005005005005")
        self.assertTrue(organisation.subject_to_vat)
        self.assertEqual(organisation.creation_date, date(2005, 5, 24))

        billing_address = organisation.billing_address
        self.assertEqual(billing_address.name, _("Billing address"))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "PO123")
        self.assertEqual(billing_address.zipcode, "ZIP123")
        self.assertEqual(billing_address.city, "City")
        self.assertEqual(billing_address.department, "Dept")
        self.assertEqual(billing_address.state, "State")
        self.assertEqual(billing_address.country, "Country")
        self.assertEqual(billing_address.owner, organisation)

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, organisation)


class PartialUpdateOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-detail"
    method = "patch"

    def test_partial_update_organisation(self):
        organisation = OrganisationFactory(
            shipping_address=True, legal_form=None, sector=None
        )
        legal_form = LegalFormFactory()
        sector = SectorFactory()
        data = {
            "legal_form": legal_form.id,
            "staff_size": None,
            "sector": sector.id,
            "name": "A Creme Company",
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_organisation_data,
                "id": organisation.id,
                "user": organisation.user_id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
                "is_managed": False,
                "shipping_address": default_address_data,
                **data,
            },
        )
        self.assertEqual(organisation.legal_form, legal_form)
        self.assertIsNone(organisation.staff_size)
        self.assertEqual(organisation.sector, sector)
        self.assertEqual(organisation.name, "A Creme Company")

    def test_partial_update_organisation__create_addresses(self):
        organisation = OrganisationFactory()

        data = {
            "billing_address": {
                "address": "billing street",
            },
            "shipping_address": {
                "address": "shipping street",
            },
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_organisation_data,
                "id": organisation.id,
                "user": organisation.user_id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "sector": organisation.sector_id,
                "legal_form": organisation.legal_form_id,
                "staff_size": organisation.staff_size_id,
                "is_deleted": False,
                "is_managed": False,
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

        billing_address = organisation.billing_address
        self.assertEqual(billing_address.name, _("Billing address"))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "")
        self.assertEqual(billing_address.zipcode, "")
        self.assertEqual(billing_address.city, "")
        self.assertEqual(billing_address.department, "")
        self.assertEqual(billing_address.state, "")
        self.assertEqual(billing_address.country, "")
        self.assertEqual(billing_address.owner, organisation)

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "")
        self.assertEqual(shipping_address.zipcode, "")
        self.assertEqual(shipping_address.city, "")
        self.assertEqual(shipping_address.department, "")
        self.assertEqual(shipping_address.state, "")
        self.assertEqual(shipping_address.country, "")
        self.assertEqual(shipping_address.owner, organisation)

    def test_partial_update_organisation__update_addresses(self):
        organisation = OrganisationFactory(billing_address=True, shipping_address=True)

        data = {
            "billing_address": {
                "address": "billing street",
            },
            "shipping_address": {
                "address": "shipping street",
            },
        }
        response = self.make_request(to=organisation.id, data=data, status_code=200)
        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                **default_organisation_data,
                "user": organisation.user_id,
                "id": organisation.id,
                "is_deleted": False,
                "is_managed": False,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "sector": organisation.sector_id,
                "legal_form": organisation.legal_form_id,
                "staff_size": organisation.staff_size_id,
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
        billing_address = organisation.billing_address
        self.assertEqual(billing_address.name, _("Billing address"))
        self.assertEqual(billing_address.address, "billing street")
        self.assertEqual(billing_address.po_box, "PO123")
        self.assertEqual(billing_address.zipcode, "ZIP123")
        self.assertEqual(billing_address.city, "City")
        self.assertEqual(billing_address.department, "Dept")
        self.assertEqual(billing_address.state, "State")
        self.assertEqual(billing_address.country, "Country")
        self.assertEqual(billing_address.owner, organisation)

        shipping_address = organisation.shipping_address
        self.assertEqual(shipping_address.name, _("Shipping address"))
        self.assertEqual(shipping_address.address, "shipping street")
        self.assertEqual(shipping_address.po_box, "PO123")
        self.assertEqual(shipping_address.zipcode, "ZIP123")
        self.assertEqual(shipping_address.city, "City")
        self.assertEqual(shipping_address.department, "Dept")
        self.assertEqual(shipping_address.state, "State")
        self.assertEqual(shipping_address.country, "Country")
        self.assertEqual(shipping_address.owner, organisation)


class ListOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-list"
    method = "get"

    def test_list_organisations(self):
        managed_organisation = Organisation.objects.get(is_managed=True)
        organisation = OrganisationFactory.create(
            billing_address=True, shipping_address=True
        )
        self.assertEqual(Organisation.objects.count(), 2, Organisation.objects.all())

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {
                    "id": managed_organisation.id,
                    "uuid": str(managed_organisation.uuid),
                    "created": self.to_iso8601(managed_organisation.created),
                    "modified": self.to_iso8601(managed_organisation.modified),
                    "user": managed_organisation.user_id,
                    "annual_revenue": "",
                    "capital": None,
                    "creation_date": None,
                    "description": "",
                    "email": "",
                    "fax": "",
                    "is_deleted": False,
                    "is_managed": True,
                    "legal_form": None,
                    "naf": "",
                    "name": _("ReplaceByYourSociety"),
                    "phone": "",
                    "rcs": "",
                    "sector": None,
                    "siren": "",
                    "siret": "",
                    "staff_size": None,
                    "subject_to_vat": True,
                    "tvaintra": "",
                    "url_site": "",
                },
                {
                    **default_organisation_data,
                    "id": organisation.id,
                    "uuid": str(organisation.uuid),
                    "created": self.to_iso8601(organisation.created),
                    "modified": self.to_iso8601(organisation.modified),
                    "user": organisation.user_id,
                    "is_deleted": False,
                    "is_managed": False,
                    "billing_address": default_address_data,
                    "shipping_address": default_address_data,
                    "legal_form": organisation.legal_form_id,
                    "sector": organisation.sector_id,
                    "staff_size": organisation.staff_size_id,
                },
            ],
        )


class TrashOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-trash"
    method = "post"

    def test_trash_organisation__protected(self):
        last_managed_organisation = Organisation.objects.get(is_managed=True)
        response = self.make_request(to=last_managed_organisation.id, status_code=422)
        self.assertEqual(response.data["detail"].code, "protected")

    def test_trash_organisation(self):
        organisation = OrganisationFactory()
        response = self.make_request(to=organisation.id, status_code=200)

        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": True,
            },
        )
        self.make_request(to=organisation.id, status_code=200)


class RestoreOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-restore"
    method = "post"

    def test_restore_organisation(self):
        organisation = OrganisationFactory(is_deleted=True)
        organisation.refresh_from_db()
        self.assertTrue(organisation.is_deleted)

        response = self.make_request(to=organisation.id, status_code=200)

        organisation.refresh_from_db()
        self.assertPayloadEqual(
            response,
            {
                "id": organisation.id,
                "uuid": str(organisation.uuid),
                "created": self.to_iso8601(organisation.created),
                "modified": self.to_iso8601(organisation.modified),
                "is_deleted": False,
            },
        )
        self.assertFalse(organisation.is_deleted)
        self.make_request(to=organisation.id, status_code=200)
        organisation.refresh_from_db()
        self.assertFalse(organisation.is_deleted)


class DeleteOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-detail"
    method = "delete"

    def test_delete_organisation__protected(self):
        last_managed_organisation = Organisation.objects.get(is_managed=True)
        response = self.make_request(to=last_managed_organisation.id, status_code=422)
        self.assertEqual(response.data["detail"].code, "protected")

    def test_delete_organisation(self):
        organisation = OrganisationFactory()
        self.make_request(to=organisation.id, status_code=204)
        self.assertFalse(Organisation.objects.filter(id=organisation.id).exists())


class CloneOrganisationTestCase(CremeAPITestCase):
    url_name = "creme_api__organisations-clone"
    method = "post"

    def test_clone_organisation(self):
        organisation = OrganisationFactory(shipping_address=True)

        response = self.make_request(to=organisation.id, status_code=201)
        cloned_organisation = Organisation.objects.get(id=response.data["id"])
        self.assertNotEqual(cloned_organisation.id, organisation.id)
        self.assertNotEqual(cloned_organisation.uuid, organisation.uuid)
        self.assertPayloadEqual(
            response,
            {
                **default_organisation_data,
                "id": cloned_organisation.id,
                "uuid": str(cloned_organisation.uuid),
                "created": self.to_iso8601(cloned_organisation.created),
                "modified": self.to_iso8601(cloned_organisation.modified),
                "is_deleted": False,
                "is_managed": False,
                "user": organisation.user_id,
                "sector": organisation.sector_id,
                "legal_form": organisation.legal_form_id,
                "staff_size": organisation.staff_size_id,
                "shipping_address": default_address_data,
            },
        )
