from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import SetCredentials
from creme.persons import get_contact_model, get_organisation_model

from .factories import CredentialFactory, RoleFactory

CremeUser = get_user_model()
Contact = get_contact_model()
Organisation = get_organisation_model()


class CreateSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "role": ["required"],
                "set_type": ["required"],
                "ctype": ["required"],
                "can_view": ["required"],
                "can_change": ["required"],
                "can_delete": ["required"],
                "can_link": ["required"],
                "can_unlink": ["required"],
                "forbidden": ["required"],
            },
        )

    def test_create_setcredentials(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        role = RoleFactory()
        data = {
            "role": role.id,
            "set_type": SetCredentials.ESET_ALL,
            "ctype": contact_ct.id,
            "can_view": True,
            "can_change": True,
            "can_delete": False,
            "can_link": True,
            "can_unlink": True,
            "forbidden": False,
        }
        response = self.make_request(data=data, status_code=201)
        creds = SetCredentials.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": creds.id,
                "role": role.id,
                "set_type": SetCredentials.ESET_ALL,
                "ctype": contact_ct.id,
                "can_view": True,
                "can_change": True,
                "can_delete": False,
                "can_link": True,
                "can_unlink": True,
                "forbidden": False,
                "efilter": None,
            },
        )
        self.assertEqual(creds.role, role)
        self.assertEqual(creds.set_type, SetCredentials.ESET_ALL)
        self.assertEqual(creds.ctype, contact_ct)
        self.assertEqual(creds.value, 2 + 4 + 16 + 32)
        self.assertFalse(creds.forbidden)


class RetrieveSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-detail"
    method = "get"

    def test_retrieve_setcredentials(self):
        creds = CredentialFactory()
        response = self.make_request(to=creds.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": creds.id,
                "role": creds.role_id,
                "set_type": SetCredentials.ESET_OWN,
                "ctype": creds.ctype.id,
                "can_view": True,
                "can_change": True,
                "can_delete": True,
                "can_link": True,
                "can_unlink": True,
                "forbidden": False,
                "efilter": None,
            },
        )


class UpdateSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-detail"
    method = "put"

    def test_validation__required(self):
        creds = CredentialFactory()
        response = self.make_request(to=creds.id, data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "set_type": ["required"],
                "ctype": ["required"],
                "can_view": ["required"],
                "can_change": ["required"],
                "can_delete": ["required"],
                "can_link": ["required"],
                "can_unlink": ["required"],
                "forbidden": ["required"],
            },
        )

    def test_update_creds(self):
        orga_ct = ContentType.objects.get_for_model(Organisation)
        creds = CredentialFactory()
        role_id = creds.role_id
        data = {
            "role": 123456,
            "set_type": SetCredentials.ESET_ALL,
            "ctype": orga_ct.id,
            "can_view": True,
            "can_change": True,
            "can_delete": False,
            "can_link": True,
            "can_unlink": True,
            "forbidden": False,
        }
        response = self.make_request(to=creds.id, data=data, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": creds.id,
                "role": creds.role_id,
                "set_type": SetCredentials.ESET_ALL,
                "ctype": orga_ct.id,
                "can_view": True,
                "can_change": True,
                "can_delete": False,
                "can_link": True,
                "can_unlink": True,
                "forbidden": False,
                "efilter": None,
            },
        )
        creds.refresh_from_db()
        self.assertEqual(creds.role_id, role_id)
        self.assertEqual(creds.set_type, SetCredentials.ESET_ALL)
        self.assertEqual(creds.ctype, orga_ct)
        self.assertEqual(creds.value, 2 + 4 + 16 + 32)
        self.assertFalse(creds.forbidden)


class PartialUpdateSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-detail"
    method = "patch"

    def test_partial_update_creds(self):
        orga_ct = ContentType.objects.get_for_model(Organisation)
        creds = CredentialFactory()
        role_id = creds.role_id
        data = {
            "role": 123456,
            "set_type": SetCredentials.ESET_ALL,
            "ctype": orga_ct.id,
            "can_delete": False,
            "forbidden": False,
        }
        response = self.make_request(to=creds.id, data=data, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": creds.id,
                "role": creds.role_id,
                "set_type": SetCredentials.ESET_ALL,
                "ctype": orga_ct.id,
                "can_view": True,
                "can_change": True,
                "can_delete": False,
                "can_link": True,
                "can_unlink": True,
                "forbidden": False,
                "efilter": None,
            },
        )
        creds.refresh_from_db()
        self.assertEqual(creds.role_id, role_id)
        self.assertEqual(creds.set_type, SetCredentials.ESET_ALL)
        self.assertEqual(creds.ctype, orga_ct)
        self.assertEqual(creds.value, 2 + 4 + 16 + 32)
        self.assertFalse(creds.forbidden)


class ListSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-list"
    method = "get"

    def test_list_setcredentials(self):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        role = RoleFactory()
        creds1 = CredentialFactory(role=role, ctype=contact_ct)
        creds2 = CredentialFactory(role=role, ctype=orga_ct, can_delete=False)

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {
                    "id": creds1.id,
                    "role": role.id,
                    "set_type": SetCredentials.ESET_OWN,
                    "ctype": contact_ct.id,
                    "can_view": True,
                    "can_change": True,
                    "can_delete": True,
                    "can_link": True,
                    "can_unlink": True,
                    "forbidden": False,
                    "efilter": None,
                },
                {
                    "id": creds2.id,
                    "role": role.id,
                    "set_type": SetCredentials.ESET_OWN,
                    "ctype": orga_ct.id,
                    "can_view": True,
                    "can_change": True,
                    "can_delete": False,
                    "can_link": True,
                    "can_unlink": True,
                    "forbidden": False,
                    "efilter": None,
                },
            ],
        )


class DeleteSetCredentialTestCase(CremeAPITestCase):
    url_name = "creme_api__credentials-detail"
    method = "delete"

    def test_delete(self):
        creds = CredentialFactory()
        self.make_request(to=creds.id, status_code=204)
        self.assertFalse(SetCredentials.objects.filter(id=creds.id).exists())
