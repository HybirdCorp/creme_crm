from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons.models import Position


@Factory.register
def position(factory, **kwargs):
    data = factory.position_data(**kwargs)
    return Position.objects.create(**data)


@Factory.register
def position_data(factory, **kwargs):
    kwargs.setdefault('title', 'Captain')
    return kwargs


class CreatePositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'title': ['required'],
        })

    def test_create_position(self):
        data = self.factory.position_data()
        response = self.make_request(data=data)
        position = Position.objects.get(id=response.data['id'])
        self.assertResponseEqual(response, 201, {
            'id': position.id,
            'title': 'Captain',
        })
        self.assertEqual(position.title, "Captain")


class RetrievePositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-detail'
    method = 'get'

    def test_retrieve_position(self):
        position = self.factory.position()
        response = self.make_request(to=position.id)
        self.assertResponseEqual(response, 200, {
            'id': position.id,
            'title': 'Captain',
        })


class UpdatePositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-detail'
    method = 'put'

    def test_update_position(self):
        position = self.factory.position()
        response = self.make_request(to=position.id, data={
            'title': "CAPTAIN",
        })
        self.assertResponseEqual(response, 200, {
            'id': position.id,
            'title': 'CAPTAIN',
        })
        position.refresh_from_db()
        self.assertEqual(position.title, "CAPTAIN")


class PartialUpdatePositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-detail'
    method = 'patch'

    def test_partial_update_position(self):
        position = self.factory.position()
        response = self.make_request(to=position.id, data={
            'title': 'CAPTAIN',
        })
        self.assertResponseEqual(response, 200, {
            'id': position.id,
            'title': 'CAPTAIN',
        })
        position.refresh_from_db()
        self.assertEqual(position.title, "CAPTAIN")


class ListPositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-list'
    method = 'get'

    def test_list_positions(self):
        Position.objects.all().delete()
        position1 = self.factory.position(title="1")
        position2 = self.factory.position(title="2")
        response = self.make_request()
        self.assertResponseEqual(response, 200, [
            {'id': position1.id, 'title': '1'},
            {'id': position2.id, 'title': '2'},
        ])


class DeletePositionTestCase(CremeAPITestCase):
    url_name = 'creme_api__positions-detail'
    method = 'delete'

    def test_delete_position(self):
        position = self.factory.position()
        response = self.make_request(to=position.id)
        self.assertResponseEqual(response, 204)
        self.assertFalse(Position.objects.filter(id=position.id).exists())
