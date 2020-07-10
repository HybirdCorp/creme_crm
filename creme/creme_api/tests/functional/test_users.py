from django.contrib.auth import get_user_model
from django.urls import reverse

from creme.creme_api.tests.utils import CremeAPITestCase

CremeUser = get_user_model()


class CreateUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-list'
    method = 'post'

    def test_validation__required(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'username': ['required'],
            'first_name': ['required'],
            'last_name': ['required'],
            'email': ['required'],
        })

    def test_validation__username_max_length(self):
        data = {'username': "a" * (CremeUser._meta.get_field('username').max_length + 1)}
        response = self.make_request(data=data)
        self.assertValidationError(response, 'username', ['max_length'])

    def test_validation__username_invalid_chars(self):
        data = {'username': "*********"}
        response = self.make_request(data=data)
        self.assertValidationError(response, 'username', ['invalid'])

    def test_validation__is_superuser_xor_role(self):
        role = self.factory.role()

        data = self.factory.user_data(is_superuser=False, role=None)
        response = self.make_request(data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

        data = self.factory.user_data(is_superuser=True, role=role.id)
        response = self.make_request(data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

    def test_create_superuser(self):
        data = self.factory.user_data(is_superuser=True, role=None)
        response = self.make_request(data=data)
        user = CremeUser.objects.get(id=response.data['id'])
        self.assertResponseEqual(response, 201, {
            'id': user.id,
            'username': 'john.doe',
            'last_name': 'Doe',
            'first_name': 'John',
            'email': 'john.doe@provider.com',
            'date_joined': self.to_iso8601(user.date_joined),
            'last_login': None,
            'is_active': True,
            'is_superuser': True,
            'role': None,
            'time_zone': 'Europe/Paris',
            'theme': 'icecream'
        })
        self.assertEqual(user.username, "john.doe")
        self.assertTrue(user.is_superuser)

    def test_create_user(self):
        role = self.factory.role()
        data = self.factory.user_data(is_superuser=False, role=role.id)
        response = self.make_request(data=data)
        user = CremeUser.objects.get(id=response.data['id'])
        self.assertResponseEqual(response, 201, {
            'id': user.id,
            'username': 'john.doe',
            'last_name': 'Doe',
            'first_name': 'John',
            'email': 'john.doe@provider.com',
            'date_joined': self.to_iso8601(user.date_joined),
            'last_login': None,
            'is_active': True,
            'is_superuser': False,
            'role': role.id,
            'time_zone': 'Europe/Paris',
            'theme': 'icecream'
        })
        self.assertEqual(user.username, "john.doe")


class RetrieveUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-detail'
    method = 'get'

    def test_get_user(self):
        user = self.factory.user()
        response = self.make_request(to=user.id)
        self.assertResponseEqual(response, 200, {
            'id': user.id,
            'username': user.username,
            'last_name': user.last_name,
            'first_name': user.first_name,
            'email': user.email,
            'date_joined': self.to_iso8601(user.date_joined),
            'last_login': None,
            'is_active': True,
            'is_superuser': True,
            'role': None,
            'time_zone': 'Europe/Paris',
            'theme': 'icecream'
        })


class UpdateUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-detail'
    method = 'put'

    def test_validation__required(self):
        user = self.factory.user()
        response = self.make_request(to=user.id, data={})
        self.assertValidationErrors(response, {
            'username': ['required'],
            'first_name': ['required'],
            'last_name': ['required'],
            'email': ['required'],
        })

    def test_validation__is_superuser_xor_role(self):
        role = self.factory.role()
        user = self.factory.user(is_superuser=True, role=None)

        data = self.factory.user_data(is_superuser=False, role=None)
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

        data = self.factory.user_data(is_superuser=True, role=role.id)
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

    def test_update_user(self):
        user = self.factory.user()

        data = self.factory.user_data(last_name="Smith", username="Nick")
        response = self.make_request(to=user.id, data=data)
        self.assertResponseEqual(response, 200, {
            'id': user.id,
            'username': 'Nick',
            'last_name': 'Smith',
            'first_name': 'John',
            'email': 'john.doe@provider.com',
            'date_joined': self.to_iso8601(user.date_joined),
            'last_login': None,
            'is_active': True,
            'is_superuser': True,
            'role': None,
            'time_zone': 'Europe/Paris',
            'theme': 'icecream'
        })
        user.refresh_from_db()
        self.assertEqual(user.username, "Nick")
        self.assertEqual(user.last_name, "Smith")


class PartialUpdateUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-detail'
    method = 'patch'

    def test_validation__is_superuser_xor_role__superuser(self):
        role = self.factory.role()
        user = self.factory.user(username='user1', is_superuser=True, role=None)

        data = {'role': role.id}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

        data = {'is_superuser': False}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

    def test_validation__is_superuser_xor_role__role(self):
        role = self.factory.role()
        user = self.factory.user(username='user2', is_superuser=False, role=role)

        data = {'role': None}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

        data = {'is_superuser': True}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, '', ['is_superuser_xor_role'])

    def test_partial_update_user(self):
        user = self.factory.user()
        data = {'theme': "chantilly"}
        response = self.make_request(to=user.id, data=data)
        self.assertResponseEqual(response, 200, {
            'id': user.id,
            'username': 'john.doe',
            'last_name': 'Doe',
            'first_name': 'John',
            'email': 'john.doe@provider.com',
            'date_joined': self.to_iso8601(user.date_joined),
            'last_login': None,
            'is_active': True,
            'is_superuser': True,
            'role': None,
            'time_zone': 'Europe/Paris',
            'theme': 'chantilly'
        })
        user.refresh_from_db()
        self.assertEqual(user.theme, "chantilly")


class ListUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-list'
    method = 'get'

    def test_list_users(self):
        fulbert = CremeUser.objects.get()
        user = self.factory.user(username="user", theme='chantilly')
        self.assertEqual(CremeUser.objects.count(), 2)

        response = self.make_request()
        self.assertResponseEqual(response, 200, [
            {
                'id': fulbert.id,
                'username': 'root',
                'last_name': 'Creme',
                'first_name': 'Fulbert',
                'email': fulbert.email,
                'date_joined': self.to_iso8601(fulbert.date_joined),
                'last_login': None,
                'is_active': True,
                'is_superuser': True,
                'role': None,
                'time_zone': 'Europe/Paris',
                'theme': 'icecream'
            },
            {
                'id': user.id,
                'username': 'user',
                'last_name': 'Doe',
                'first_name': 'John',
                'email': 'john.doe@provider.com',
                'date_joined': self.to_iso8601(user.date_joined),
                'last_login': None,
                'is_active': True,
                'is_superuser': True,
                'role': None,
                'time_zone': 'Europe/Paris',
                'theme': 'chantilly'
            },
        ])


class SetPasswordUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-set-password'
    method = 'post'

    def test_password_validation__required(self):
        user = self.factory.user()
        response = self.make_request(to=user.id, data={})
        self.assertValidationErrors(response, {
            'password': ['required']
        })

    def test_password_validation__blank(self):
        user = self.factory.user()

        data = {'password': ''}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, 'password', ['blank'])

    def test_password_validation__no_trim(self):
        user = self.factory.user()

        data = {'password': "  StrongPassword  "}
        response = self.make_request(to=user.id, data=data)
        self.assertResponseEqual(response, 200, {})

        user.refresh_from_db()
        self.assertTrue(user.check_password("  StrongPassword  "))

    def test_password_validation__similarity(self):
        user = self.factory.user(
            username="76aa224e-056a",
            first_name="4816-ac3e",
            last_name="ffe6e2c0748c",
            email='df8e4b1a4f39@provider.com'
        )

        data = {'password': user.username}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, 'password', ['password_too_similar'])

        data = {'password': user.first_name}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, 'password', ['password_too_similar'])

        data = {'password': user.last_name}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, 'password', ['password_too_similar'])

        data = {'password': user.email.split("@")[0]}
        response = self.make_request(to=user.id, data=data)
        self.assertValidationError(response, 'password', ['password_too_similar'])

    def test_set_password_user(self):
        user = self.factory.user()

        data = {'password': "StrongPassword"}
        response = self.make_request(to=user.id, data=data)
        self.assertResponseEqual(response, 200, {})

        user.refresh_from_db()
        self.assertTrue(user.check_password("StrongPassword"))


class DeleteUserTestCase(CremeAPITestCase):
    url_name = 'creme_api__users-delete'
    method = 'post'

    def test_delete(self):
        url = reverse('creme_api__users-detail', args=[1])
        response = self.client.delete(url, format='json')
        self.assertResponseEqual(response, 405)

    def test_validation__required(self):
        user = self.factory.user()
        response = self.make_request(to=user.id, data={})
        self.assertValidationErrors(response, {
            'transfer_to': ['required']
        })

    def test_delete_user(self):
        team = self.factory.team()
        user1 = self.factory.user(username='user1')
        user2 = self.factory.user(username='user2')
        contact = self.factory.contact(user=user2)

        data = {'transfer_to': user1.id}
        response = self.make_request(to=user2.id, data=data)
        self.assertResponseEqual(response, 204)

        self.assertFalse(CremeUser.objects.filter(username='user2').exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, user1)

        data = {'transfer_to': team.id}
        response = self.make_request(to=user1.id, data=data)
        self.assertResponseEqual(response, 204)

        self.assertFalse(CremeUser.objects.filter(username='user1').exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, team)
