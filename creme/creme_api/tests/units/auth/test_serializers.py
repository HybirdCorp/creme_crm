from copy import copy

from django.contrib.auth import get_user_model

from creme.creme_api.api.auth.serializers import (
    PasswordSerializer,
    UserSerializer,
)
from creme.creme_api.tests.utils import SerializerTestCase
from creme.creme_core.models import UserRole

user_data = {
    "username": "CremeUser",
    'last_name': "CremeUser",
    'first_name': "CremeUser",
    'email': "CremeUser@organization.com",
    'is_active': True,
    'is_superuser': True,
    'role': None,
    'time_zone': "Europe/Paris",
    'theme': 'chantilly',
}

CremeUser = get_user_model()


class PasswordSerializerTestCase(SerializerTestCase):
    def test_password_validation(self):
        user = CremeUser.objects.create(
            username="76aa224e-056a",
            first_name="4816-ac3e",
            last_name="ffe6e2c0748c",
            email='df8e4b1a4f39@provider.com'
        )
        serializer = PasswordSerializer(user, data={'password': "76aa224e-056a"})
        self.assertSerializerError(serializer, 'password', 'password_too_similar')

        serializer = PasswordSerializer(user, data={'password': "4816-ac3e"})
        self.assertSerializerError(serializer, 'password', 'password_too_similar')

        serializer = PasswordSerializer(user, data={'password': "ffe6e2c0748c"})
        self.assertSerializerError(serializer, 'password', 'password_too_similar')

        serializer = PasswordSerializer(user, data={'password': "df8e4b1a4f39"})
        self.assertSerializerError(serializer, 'password', 'password_too_similar')

        serializer = PasswordSerializer(user, data={'password': "StrongPassword"})
        self.assertSerializerValid(serializer)

        user = serializer.save()
        self.assertTrue(user.check_password("StrongPassword"))


class UserSerializerTestCase(SerializerTestCase):
    def test_create(self):
        serializer = UserSerializer(data=user_data)
        self.assertSerializerValid(serializer)
        user = serializer.save()

        self.assertEqual(user.username, user_data['username'])
        self.assertEqual(user.last_name, user_data['last_name'])
        self.assertEqual(user.first_name, user_data['first_name'])
        self.assertEqual(user.email, user_data['email'])
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superuser)
        self.assertEqual(user.time_zone, user_data['time_zone'])
        self.assertEqual(user.theme, user_data['theme'])
        self.assertEqual(user.time_zone, user_data['time_zone'])

    def test_create__role_superuser(self):
        data = copy(user_data)
        role = UserRole.objects.create(name='Basic')
        data['role'] = role.id
        serializer = UserSerializer(data=data)
        self.assertSerializerError(serializer, 'non_field_errors', 'is_superuser_xor_role')
