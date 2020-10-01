from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import CremeUser
from creme.persons.models import Address, Contact


class AddressTestCase(CremeAPITestCase):

    def test_create_address(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)

        url = reverse('creme_api-addresses-list')
        data = {'owner': contact.id, 'name': "Hybird"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        address = Address.objects.get(id=response.data['id'])
        self.assertEqual(address.name, "Hybird")
        self.assertEqual(address.owner, contact)

    def test_list_addresss(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)
        Address.objects.create(owner=contact)
        Address.objects.create(owner=contact)

        url = reverse('creme_api-addresses-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({*Address.objects.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_address(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)
        address = Address.objects.create(owner=contact)

        url = reverse('creme_api-addresses-detail', args=[address.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], address.id)

    def test_update_address(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)
        address = Address.objects.create(owner=contact, name="HOME", address="1st")

        url = reverse('creme_api-addresses-detail', args=[address.id])
        data = {"name": "WORK", "owner": contact.id}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        address.refresh_from_db()
        self.assertEqual(address.name, "WORK")
        self.assertEqual(address.owner, contact)
        self.assertEqual(address.address, "1st")

    def test_partial_update_address(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)
        address = Address.objects.create(owner=contact, name="HOME", address="1st")

        url = reverse('creme_api-addresses-detail', args=[address.id])
        data = {"name": "WORK"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        address.refresh_from_db()
        self.assertEqual(address.name, "WORK")
        self.assertEqual(address.owner, contact)
        self.assertEqual(address.address, "1st")

    def test_delete_address(self):
        user = CremeUser.objects.create(username='test')
        contact = Contact.objects.create(user=user)
        address = Address.objects.create(owner=contact)

        url = reverse('creme_api-addresses-detail', args=[address.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204, response.data)

        self.assertFalse(Address.objects.filter(id=address.id).exists())
