from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons.models import LegalForm

from .factories import LegalFormFactory


class CreateLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "title": ["required"],
            },
        )

    def test_create_legal_form(self):
        data = {"title": "Trust"}
        response = self.make_request(data=data, status_code=201)
        legal_form = LegalForm.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": legal_form.id,
                "title": "Trust",
            },
        )
        self.assertEqual(legal_form.title, "Trust")


class RetrieveLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-detail"
    method = "get"

    def test_retrieve_legal_form(self):
        legal_form = LegalFormFactory()
        response = self.make_request(to=legal_form.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": legal_form.id,
                "title": "Trust",
            },
        )


class UpdateLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-detail"
    method = "put"

    def test_update_legal_form(self):
        legal_form = LegalFormFactory()
        response = self.make_request(
            to=legal_form.id,
            data={
                "title": "Corporation",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": legal_form.id,
                "title": "Corporation",
            },
        )
        legal_form.refresh_from_db()
        self.assertEqual(legal_form.title, "Corporation")


class PartialUpdateLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-detail"
    method = "patch"

    def test_partial_update_legal_form(self):
        legal_form = LegalFormFactory()
        response = self.make_request(
            to=legal_form.id,
            data={
                "title": "Corporation",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": legal_form.id,
                "title": "Corporation",
            },
        )
        legal_form.refresh_from_db()
        self.assertEqual(legal_form.title, "Corporation")


class ListLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-list"
    method = "get"

    def test_list_legal_forms(self):
        LegalForm.objects.all().delete()
        legal_form1 = LegalFormFactory(title="1")
        legal_form2 = LegalFormFactory(title="2")
        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {"id": legal_form1.id, "title": "1"},
                {"id": legal_form2.id, "title": "2"},
            ],
        )


class DeleteLegalFormTestCase(CremeAPITestCase):
    url_name = "creme_api__legal_forms-detail"
    method = "delete"

    def test_delete_legal_form(self):
        legal_form = LegalFormFactory()
        self.make_request(to=legal_form.id, status_code=204)
        self.assertFalse(LegalForm.objects.filter(id=legal_form.id).exists())
