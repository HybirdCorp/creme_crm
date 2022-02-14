from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons.models import Sector


@Factory.register
def sector(factory, **kwargs):
    data = factory.sector_data(**kwargs)
    return Sector.objects.create(**data)


@Factory.register
def sector_data(factory, **kwargs):
    kwargs.setdefault('title', 'Industry')
    return kwargs


class CreateSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(response, {
            'title': ['required'],
        })

    def test_create_sector(self):
        data = self.factory.sector_data()
        response = self.make_request(data=data, status_code=201)
        sector = Sector.objects.get(id=response.data['id'])
        self.assertPayloadEqual(response, {
            'id': sector.id,
            'title': 'Industry',
        })
        self.assertEqual(sector.title, "Industry")


class RetrieveSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-detail'
    method = 'get'

    def test_retrieve_sector(self):
        sector = self.factory.sector()
        response = self.make_request(to=sector.id, status_code=200)
        self.assertPayloadEqual(response, {
            'id': sector.id,
            'title': 'Industry',
        })


class UpdateSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-detail'
    method = 'put'

    def test_update_sector(self):
        sector = self.factory.sector()
        response = self.make_request(to=sector.id, data={
            'title': "Agro",
        }, status_code=200)
        self.assertPayloadEqual(response, {
            'id': sector.id,
            'title': 'Agro',
        })
        sector.refresh_from_db()
        self.assertEqual(sector.title, "Agro")


class PartialUpdateSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-detail'
    method = 'patch'

    def test_partial_update_sector(self):
        sector = self.factory.sector()
        response = self.make_request(to=sector.id, data={
            'title': 'Agro',
        }, status_code=200)
        self.assertPayloadEqual(response, {
            'id': sector.id,
            'title': 'Agro',
        })
        sector.refresh_from_db()
        self.assertEqual(sector.title, "Agro")


class ListSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-list'
    method = 'get'

    def test_list_sectors(self):
        Sector.objects.all().delete()
        sector1 = self.factory.sector(title="1")
        sector2 = self.factory.sector(title="2")
        response = self.make_request(status_code=200)
        self.assertPayloadEqual(response, [
            {'id': sector1.id, 'title': '1'},
            {'id': sector2.id, 'title': '2'},
        ])


class DeleteSectorTestCase(CremeAPITestCase):
    url_name = 'creme_api__sectors-detail'
    method = 'delete'

    def test_delete_sector(self):
        sector = self.factory.sector()
        self.make_request(to=sector.id, status_code=204)
        self.assertFalse(Sector.objects.filter(id=sector.id).exists())
