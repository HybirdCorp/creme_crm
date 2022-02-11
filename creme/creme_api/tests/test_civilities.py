from creme.creme_api.tests.utils import CremeAPITestCase, Factory
from creme.persons.models import Civility


@Factory.register
def civility(factory, **kwargs):
    data = factory.civility_data(**kwargs)
    return Civility.objects.create(**data)


@Factory.register
def civility_data(factory, **kwargs):
    kwargs.setdefault('title', 'Captain')
    kwargs.setdefault('shortcut', 'Cpt')
    return kwargs


class CreateCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'title': ['required'],
            'shortcut': ['required'],
        })

    def test_create_civility(self):
        data = self.factory.civility_data()
        response = self.make_request(data=data)
        civility = Civility.objects.get(id=response.data['id'])
        self.assertResponseEqual(response, 201, {
            'id': civility.id,
            'title': 'Captain',
            'shortcut': 'Cpt',
        })
        self.assertEqual(civility.title, "Captain")
        self.assertEqual(civility.shortcut, "Cpt")


class RetrieveCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-detail'
    method = 'get'

    def test_retrieve_civility(self):
        civility = self.factory.civility()
        response = self.make_request(to=civility.id)
        self.assertResponseEqual(response, 200, {
            'id': civility.id,
            'title': 'Captain',
            'shortcut': 'Cpt',
        })


class UpdateCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-detail'
    method = 'put'

    def test_update_civility(self):
        civility = self.factory.civility()
        response = self.make_request(to=civility.id, data={
            'title': "CAPTAIN",
            'shortcut': "CAP",
        })
        self.assertResponseEqual(response, 200, {
            'id': civility.id,
            'title': 'CAPTAIN',
            'shortcut': 'CAP',
        })
        civility.refresh_from_db()
        self.assertEqual(civility.title, "CAPTAIN")
        self.assertEqual(civility.shortcut, "CAP")


class PartialUpdateCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-detail'
    method = 'patch'

    def test_partial_update_civility(self):
        civility = self.factory.civility()
        response = self.make_request(to=civility.id, data={
            'shortcut': "CAP",
        })
        self.assertResponseEqual(response, 200, {
            'id': civility.id,
            'title': 'Captain',
            'shortcut': 'CAP',
        })
        civility.refresh_from_db()
        self.assertEqual(civility.title, "Captain")
        self.assertEqual(civility.shortcut, "CAP")


class ListCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-list'
    method = 'get'

    def test_list_civilities(self):
        Civility.objects.all().delete()
        civility1 = self.factory.civility(title="1", shortcut="1")
        civility2 = self.factory.civility(title="2", shortcut="2")
        response = self.make_request()
        self.assertResponseEqual(response, 200, [
            {'id': civility1.id, 'title': '1', 'shortcut': '1'},
            {'id': civility2.id, 'title': '2', 'shortcut': '2'},
        ])


class DeleteCivilityTestCase(CremeAPITestCase):
    url_name = 'creme_api__civilities-detail'
    method = 'delete'

    def test_delete_civility(self):
        civility = self.factory.civility()
        response = self.make_request(to=civility.id)
        self.assertResponseEqual(response, 204)
        self.assertFalse(Civility.objects.filter(id=civility.id).exists())
