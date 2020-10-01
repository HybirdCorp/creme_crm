from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import CremeUser


class CremeUserTestCase(CremeAPITestCase):
    def test_create_user(self):
        url = reverse('creme_api-users-list')
        data = {'username': "creme-user"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)

        user = CremeUser.objects.get(id=response.data['id'])
        self.assertEqual(user.username, "creme-user")

    def test_list_users(self):
        CremeUser.objects.create(username='test')
        self.assertEqual(CremeUser.objects.count(), 2)

        url = reverse('creme_api-users-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        self.assertEqual(len(response.data), 2)
        self.assertEqual({*CremeUser.objects.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_user(self):
        user = CremeUser.objects.get()

        url = reverse('creme_api-users-detail', args=[user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], user.id)

    def test_update_user(self):
        self.assertEqual(CremeUser.objects.count(), 1)
        user = CremeUser.objects.get()

        url = reverse('creme_api-users-detail', args=[user.id])
        data = {'last_name': "Smith", 'username': "Nick"}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        user.refresh_from_db()
        self.assertEqual(user.last_name, "Smith")
        self.assertEqual(user.username, "Nick")

    def test_partial_update_user(self):
        self.assertEqual(CremeUser.objects.count(), 1)
        user = CremeUser.objects.get()

        url = reverse('creme_api-users-detail', args=[user.id])
        data = {'theme': "chantilly"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        user.refresh_from_db()
        self.assertEqual(user.theme, "chantilly")

    def test_delete_user(self):
        user1 = CremeUser.objects.create(username='test1')
        contact1 = user1.related_contact.get()
        user2 = CremeUser.objects.create(username='test2')

        url = reverse('creme_api-users-detail', args=[user1.id])
        data = {'to_user': user2.id}
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, 204, response.data)

        contact1.refresh_from_db()
        self.assertEqual(contact1.is_user, None)
        self.assertEqual(contact1.user, user2)
