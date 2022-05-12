from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons.models import Civility

from .factories import CivilityFactory


class CreateCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "title": ["required"],
                "shortcut": ["required"],
            },
        )

    def test_create_civility(self):
        data = {"title": "Captain", "shortcut": "Cpt"}
        response = self.make_request(data=data, status_code=201)
        civility = Civility.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": civility.id,
                "title": "Captain",
                "shortcut": "Cpt",
            },
        )
        self.assertEqual(civility.title, "Captain")
        self.assertEqual(civility.shortcut, "Cpt")


class RetrieveCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-detail"
    method = "get"

    def test_retrieve_civility(self):
        civility = CivilityFactory()
        response = self.make_request(to=civility.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": civility.id,
                "title": "Captain",
                "shortcut": "Cpt",
            },
        )


class UpdateCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-detail"
    method = "put"

    def test_update_civility(self):
        civility = CivilityFactory()
        response = self.make_request(
            to=civility.id,
            data={
                "title": "CAPTAIN",
                "shortcut": "CAP",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": civility.id,
                "title": "CAPTAIN",
                "shortcut": "CAP",
            },
        )
        civility.refresh_from_db()
        self.assertEqual(civility.title, "CAPTAIN")
        self.assertEqual(civility.shortcut, "CAP")


class PartialUpdateCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-detail"
    method = "patch"

    def test_partial_update_civility(self):
        civility = CivilityFactory()
        response = self.make_request(
            to=civility.id,
            data={
                "shortcut": "CAP",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": civility.id,
                "title": "Captain",
                "shortcut": "CAP",
            },
        )
        civility.refresh_from_db()
        self.assertEqual(civility.title, "Captain")
        self.assertEqual(civility.shortcut, "CAP")


class ListCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-list"
    method = "get"

    def test_list_civilities(self):
        Civility.objects.all().delete()
        civility1 = CivilityFactory(title="1", shortcut="1")
        civility2 = CivilityFactory(title="2", shortcut="2")
        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {"id": civility1.id, "title": "1", "shortcut": "1"},
                {"id": civility2.id, "title": "2", "shortcut": "2"},
            ],
        )


class DeleteCivilityTestCase(CremeAPITestCase):
    url_name = "creme_api__civilities-detail"
    method = "delete"

    def test_delete_civility(self):
        civility = CivilityFactory()
        self.make_request(to=civility.id, status_code=204)
        self.assertFalse(Civility.objects.filter(id=civility.id).exists())
