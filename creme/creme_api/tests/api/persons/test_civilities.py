from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.persons.models import Civility


class CivilityTestCase(CremeAPITestCase):
    def test_create_civility(self):
        url = reverse('creme_api-civilities-list')
        data = {'title': "Not your business", 'shortcut': "NYB"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        civility = Civility.objects.get(id=response.data['id'])
        self.assertEqual(civility.title, "Not your business")
        self.assertEqual(civility.shortcut, "NYB")

    def test_list_civilitys(self):
        self.assertEqual(Civility.objects.count(), 4)
        Civility.objects.create(**{'title': "Not your business", 'shortcut': "NYB"})

        url = reverse('creme_api-civilities-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 5)
        self.assertEqual({*Civility.objects.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_civility(self):
        self.assertEqual(Civility.objects.count(), 4)
        civility = Civility.objects.first()

        url = reverse('creme_api-civilities-detail', args=[civility.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], civility.id)

    def test_update_civility(self):
        self.assertEqual(Civility.objects.count(), 4)
        civility = Civility.objects.first()

        url = reverse('creme_api-civilities-detail', args=[civility.id])
        data = {'title': "Not your business", 'shortcut': "NYB"}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        civility.refresh_from_db()
        self.assertEqual(civility.title, "Not your business")
        self.assertEqual(civility.shortcut, "NYB")

    def test_partial_update_civility(self):
        self.assertEqual(Civility.objects.count(), 4)
        civility = Civility.objects.first()

        url = reverse('creme_api-civilities-detail', args=[civility.id])
        data = {'title': "Not your business"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        civility.refresh_from_db()
        self.assertEqual(civility.title, "Not your business")
        self.assertEqual(civility.shortcut, _("Mrs."))

    def test_delete_civility(self):
        self.assertEqual(Civility.objects.count(), 4)
        civility = Civility.objects.first()

        url = reverse('creme_api-civilities-detail', args=[civility.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204, response.data)

        self.assertFalse(Civility.objects.filter(id=civility.id).exists())
