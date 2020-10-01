from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import CremeUser
from creme.persons.models import Contact


class ContactTestCase(CremeAPITestCase):
    def test_create_contact(self):
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-contacts-list')
        data = {'user': user.id, 'last_name': "Creme"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        contact = Contact.objects.get(id=response.data['id'])
        self.assertEqual(contact.last_name, "Creme")
        self.assertEqual(contact.user, user)

    def test_list_contacts(self):
        self.assertEqual(Contact.objects.count(), 1)
        user = CremeUser.objects.create(username='test')
        Contact.objects.create(user=user)

        url = reverse('creme_api-contacts-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 3)
        self.assertEqual({*Contact.objects.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_contact(self):
        self.assertEqual(Contact.objects.count(), 1)
        contact = Contact.objects.get()

        url = reverse('creme_api-contacts-detail', args=[contact.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], contact.id)

    def test_update_contact(self):
        self.assertEqual(Contact.objects.count(), 1)
        contact = Contact.objects.get()
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-contacts-detail', args=[contact.id])
        data = {'user': user.id, 'last_name': "Smith"}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        contact.refresh_from_db()
        self.assertEqual(contact.last_name, "Smith")
        self.assertEqual(contact.user, user)

    def test_partial_update_contact(self):
        self.assertEqual(Contact.objects.count(), 1)
        contact = Contact.objects.get()
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-contacts-detail', args=[contact.id])
        data = {'user': user.id}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        contact.refresh_from_db()
        self.assertEqual(contact.last_name, "Creme")
        self.assertEqual(contact.user, user)

    def test_trash_contact(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user, is_deleted=False)

        url = reverse('creme_api-contacts-trash', args=[contact.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200, response.data)

        contact.refresh_from_db()
        self.assertTrue(contact.is_deleted)

    def test_restore_contact(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user, is_deleted=True)

        url = reverse('creme_api-contacts-restore', args=[contact.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200, response.data)

        contact.refresh_from_db()
        self.assertFalse(contact.is_deleted)

    def test_delete_contact(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)

        url = reverse('creme_api-contacts-detail', args=[contact.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204, response.data)

        self.assertFalse(Contact.objects.filter(id=contact.id).exists())
