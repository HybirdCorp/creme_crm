from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase
from creme.creme_core.models import CremeUser
from creme.persons.models import Contact


class CremeUserTestCase(CremeAPITestCase):
    def test_create_team(self):
        url = reverse('creme_api-teams-list')
        data = {'username': "creme-user"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, 201, response.data)

        team = CremeUser.objects.get(id=response.data['id'])
        self.assertEqual(team.username, "creme-user")

    def test_list_users(self):
        CremeUser.objects.create(username='test1', is_team=True)
        CremeUser.objects.create(username='test2', is_team=True)
        teams = CremeUser.objects.filter(is_team=True)
        self.assertEqual(teams.count(), 2)

        url = reverse('creme_api-teams-list')
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        teams = CremeUser.objects.filter(is_team=True)
        self.assertEqual(len(response.data), teams.count())
        self.assertEqual({*teams.values_list('id', flat=True)},
                         {d['id'] for d in response.data})

    def test_get_team(self):
        team = CremeUser.objects.create(username='test', is_team=True)

        url = reverse('creme_api-teams-detail', args=[team.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['id'], team.id)

    def test_update_team(self):
        team = CremeUser.objects.create(username='test', is_team=True)

        url = reverse('creme_api-teams-detail', args=[team.id])
        data = {'username': "Sales"}
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        team.refresh_from_db()
        self.assertEqual(team.username, "Sales")

    def test_partial_update_team(self):
        team = CremeUser.objects.create(username='test', is_team=True)

        url = reverse('creme_api-teams-detail', args=[team.id])
        data = {'username': "Sales"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)

        team.refresh_from_db()
        self.assertEqual(team.username, "Sales")

    def test_delete_team(self):
        team1 = CremeUser.objects.create(username='test1', is_team=True)
        contact = Contact.objects.create(user=team1, last_name="TEST")
        team2 = CremeUser.objects.create(username='test2', is_team=True)

        url = reverse('creme_api-teams-detail', args=[team1.id])
        data = {'to_user': team2.id}
        response = self.client.delete(url, data, format='json')
        self.assertEqual(response.status_code, 204, response.data)

        contact.refresh_from_db()
        self.assertEqual(contact.user, team2)
