from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons.models import Position

from .factories import PositionFactory


class CreatePositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "title": ["required"],
            },
        )

    def test_create_position(self):
        data = {"title": "Captain"}
        response = self.make_request(data=data, status_code=201)
        position = Position.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": position.id,
                "title": "Captain",
            },
        )
        self.assertEqual(position.title, "Captain")


class RetrievePositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-detail"
    method = "get"

    def test_retrieve_position(self):
        position = PositionFactory()
        response = self.make_request(to=position.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": position.id,
                "title": "Captain",
            },
        )


class UpdatePositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-detail"
    method = "put"

    def test_update_position(self):
        position = PositionFactory()
        response = self.make_request(
            to=position.id,
            data={
                "title": "CAPTAIN",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": position.id,
                "title": "CAPTAIN",
            },
        )
        position.refresh_from_db()
        self.assertEqual(position.title, "CAPTAIN")


class PartialUpdatePositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-detail"
    method = "patch"

    def test_partial_update_position(self):
        position = PositionFactory()
        response = self.make_request(
            to=position.id,
            data={
                "title": "CAPTAIN",
            },
            status_code=200,
        )
        self.assertPayloadEqual(
            response,
            {
                "id": position.id,
                "title": "CAPTAIN",
            },
        )
        position.refresh_from_db()
        self.assertEqual(position.title, "CAPTAIN")


class ListPositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-list"
    method = "get"

    def test_list_positions(self):
        Position.objects.all().delete()
        position1 = PositionFactory(title="1")
        position2 = PositionFactory(title="2")
        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {"id": position1.id, "title": "1"},
                {"id": position2.id, "title": "2"},
            ],
        )


class DeletePositionTestCase(CremeAPITestCase):
    url_name = "creme_api__positions-detail"
    method = "delete"

    def test_delete_position(self):
        position = PositionFactory()
        self.make_request(to=position.id, status_code=204)
        self.assertFalse(Position.objects.filter(id=position.id).exists())
