from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import CremeUser
from creme.persons.models import Organisation


class OrganisationTestCase(CremeAPITestCase):
    def test_create_organisation(self):
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-organisations-list')
        data = {'user': user.id, 'name': "Hybird"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        organisation = Organisation.objects.get(id=response.data['id'])
        self.assertEqual(organisation.name, "Hybird")
        self.assertEqual(organisation.user, user)

    def test_list_organisations(self):
        self.assertEqual(Organisation.objects.count(), 1)
        user = CremeUser.objects.create(username='test')
        Organisation.objects.create(user=user)

        url = reverse('creme_api-organisations-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 2)
        self.assertEqual({*Organisation.objects.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_organisation(self):
        self.assertEqual(Organisation.objects.count(), 1)
        organisation = Organisation.objects.get()

        url = reverse('creme_api-organisations-detail', args=[organisation.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], organisation.id)

    def test_update_organisation(self):
        self.assertEqual(Organisation.objects.count(), 1)
        organisation = Organisation.objects.get()
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-organisations-detail', args=[organisation.id])
        data = {'user': user.id, 'name': "Hybird"}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        organisation.refresh_from_db()
        self.assertEqual(organisation.name, "Hybird")
        self.assertEqual(organisation.user, user)

    def test_partial_update_organisation(self):
        self.assertEqual(Organisation.objects.count(), 1)
        organisation = Organisation.objects.get()
        user = CremeUser.objects.create(username='test')

        url = reverse('creme_api-organisations-detail', args=[organisation.id])
        data = {'user': user.id}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        organisation.refresh_from_db()
        self.assertEqual(organisation.name, _("ReplaceByYourSociety"))
        self.assertEqual(organisation.user, user)

    def test_trash_organisation(self):
        user = CremeUser.objects.create(username='test')
        organisation = Organisation.objects.create(user=user, is_deleted=False)

        url = reverse('creme_api-organisations-trash', args=[organisation.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200, response.data)

        organisation.refresh_from_db()
        self.assertTrue(organisation.is_deleted)

    def test_restore_organisation(self):
        user = CremeUser.objects.create(username='test')
        organisation = Organisation.objects.create(user=user, is_deleted=True)

        url = reverse('creme_api-organisations-restore', args=[organisation.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200, response.data)

        organisation.refresh_from_db()
        self.assertFalse(organisation.is_deleted)

    def test_delete_organisation(self):
        user = CremeUser.objects.create(username='test')
        organisation = Organisation.objects.create(user=user)

        url = reverse('creme_api-organisations-detail', args=[organisation.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204, response.data)

        self.assertFalse(Organisation.objects.filter(id=organisation.id).exists())
