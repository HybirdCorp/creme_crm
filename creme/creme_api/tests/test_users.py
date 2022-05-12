from django.contrib.auth import get_user_model

from creme.creme_api.tests.utils import CremeAPITestCase

from .factories import ContactFactory, RoleFactory, TeamFactory, UserFactory

CremeUser = get_user_model()


default_user_data = {
    "first_name": "John",
    "last_name": "Doe",
    "username": "john.doe",
    "email": "john.doe@provider.com",
    "is_active": True,
    "is_superuser": True,
    "role": None,
}


class CreateUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-list"
    method = "post"

    def test_validation__required(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "username": ["required"],
                "first_name": ["required"],
                "last_name": ["required"],
                "email": ["required"],
            },
        )

    def test_validation__username_max_length(self):
        data = {
            "username": "a" * (CremeUser._meta.get_field("username").max_length + 1)
        }
        response = self.make_request(data=data, status_code=400)
        self.assertValidationError(response, "username", ["max_length"])

    def test_validation__username_invalid_chars(self):
        data = {"username": "*********"}
        response = self.make_request(data=data, status_code=400)
        self.assertValidationError(response, "username", ["invalid"])

    def test_validation__is_superuser_xor_role(self):
        role = RoleFactory()

        data = {**default_user_data, "is_superuser": False, "role": None}
        response = self.make_request(data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

        data = {**default_user_data, "is_superuser": True, "role": role.id}
        response = self.make_request(data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

    def test_create_superuser(self):
        data = {**default_user_data, "is_superuser": True, "role": None}
        response = self.make_request(data=data, status_code=201)
        user = CremeUser.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": user.id,
                "username": "john.doe",
                "last_name": "Doe",
                "first_name": "John",
                "email": "john.doe@provider.com",
                "date_joined": self.to_iso8601(user.date_joined),
                "last_login": None,
                "is_active": True,
                "is_superuser": True,
                "role": None,
                "time_zone": "Europe/Paris",
                "theme": "icecream",
            },
        )
        self.assertEqual(user.username, "john.doe")
        self.assertTrue(user.is_superuser)

    def test_create_user(self):
        role = RoleFactory()
        data = {**default_user_data, "is_superuser": False, "role": role.id}
        response = self.make_request(data=data, status_code=201)
        user = CremeUser.objects.get(id=response.data["id"])
        self.assertPayloadEqual(
            response,
            {
                "id": user.id,
                "username": "john.doe",
                "last_name": "Doe",
                "first_name": "John",
                "email": "john.doe@provider.com",
                "date_joined": self.to_iso8601(user.date_joined),
                "last_login": None,
                "is_active": True,
                "is_superuser": False,
                "role": role.id,
                "time_zone": "Europe/Paris",
                "theme": "icecream",
            },
        )
        self.assertEqual(user.username, "john.doe")


class RetrieveUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-detail"
    method = "get"

    def test_get_user(self):
        user = UserFactory()
        response = self.make_request(to=user.id, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": user.id,
                "username": user.username,
                "last_name": user.last_name,
                "first_name": user.first_name,
                "email": user.email,
                "date_joined": self.to_iso8601(user.date_joined),
                "last_login": None,
                "is_active": True,
                "is_superuser": True,
                "role": None,
                "time_zone": "Europe/Paris",
                "theme": "icecream",
            },
        )


class UpdateUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-detail"
    method = "put"

    def test_validation__required(self):
        user = UserFactory()
        response = self.make_request(to=user.id, data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "username": ["required"],
                "first_name": ["required"],
                "last_name": ["required"],
                "email": ["required"],
            },
        )

    def test_validation__is_superuser_xor_role(self):
        role = RoleFactory()
        user = UserFactory(is_superuser=True, role=None)

        data = {**default_user_data, "is_superuser": False, "role": None}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

        data = {**default_user_data, "is_superuser": True, "role": role.id}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

    def test_update_user(self):
        user = UserFactory()

        data = {**default_user_data, "last_name": "Smith", "username": "Nick"}
        response = self.make_request(to=user.id, data=data, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                **data,
                "id": user.id,
                "date_joined": self.to_iso8601(user.date_joined),
                "last_login": None,
                "role": None,
                "time_zone": "Europe/Paris",
                "theme": "icecream",
            },
        )
        user.refresh_from_db()
        self.assertEqual(user.username, "Nick")
        self.assertEqual(user.last_name, "Smith")


class PartialUpdateUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-detail"
    method = "patch"

    def test_validation__is_superuser_xor_role__superuser(self):
        role = RoleFactory()
        user = UserFactory(username="user1", is_superuser=True, role=None)

        data = {"role": role.id}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

        data = {"is_superuser": False}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

    def test_validation__is_superuser_xor_role__role(self):
        role = RoleFactory()
        user = UserFactory(username="user2", is_superuser=False, role=role)

        data = {"role": None}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

        data = {"is_superuser": True}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "", ["is_superuser_xor_role"])

    def test_partial_update_user(self):
        user = UserFactory()
        data = {"theme": "chantilly"}
        response = self.make_request(to=user.id, data=data, status_code=200)
        self.assertPayloadEqual(
            response,
            {
                "id": user.id,
                "username": "john.doe",
                "last_name": "Doe",
                "first_name": "John",
                "email": "john.doe@provider.com",
                "date_joined": self.to_iso8601(user.date_joined),
                "last_login": None,
                "is_active": True,
                "is_superuser": True,
                "role": None,
                "time_zone": "Europe/Paris",
                "theme": "chantilly",
            },
        )
        user.refresh_from_db()
        self.assertEqual(user.theme, "chantilly")


class ListUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-list"
    method = "get"

    def test_list_users(self):
        fulbert = CremeUser.objects.get()
        user = UserFactory(username="user", theme="chantilly")
        self.assertEqual(CremeUser.objects.count(), 2)

        response = self.make_request(status_code=200)
        self.assertPayloadEqual(
            response,
            [
                {
                    "id": fulbert.id,
                    "username": "root",
                    "last_name": "Creme",
                    "first_name": "Fulbert",
                    "email": fulbert.email,
                    "date_joined": self.to_iso8601(fulbert.date_joined),
                    "last_login": None,
                    "is_active": True,
                    "is_superuser": True,
                    "role": None,
                    "time_zone": "Europe/Paris",
                    "theme": "icecream",
                },
                {
                    "id": user.id,
                    "username": "user",
                    "last_name": "Doe",
                    "first_name": "John",
                    "email": "john.doe@provider.com",
                    "date_joined": self.to_iso8601(user.date_joined),
                    "last_login": None,
                    "is_active": True,
                    "is_superuser": True,
                    "role": None,
                    "time_zone": "Europe/Paris",
                    "theme": "chantilly",
                },
            ],
        )


class SetPasswordUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-set-password"
    method = "post"

    def test_password_validation__required(self):
        user = UserFactory()
        response = self.make_request(to=user.id, data={}, status_code=400)
        self.assertValidationErrors(response, {"password": ["required"]})

    def test_password_validation__blank(self):
        user = UserFactory()

        data = {"password": ""}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "password", ["blank"])

    def test_password_validation__no_trim(self):
        user = UserFactory()

        data = {"password": "  StrongPassword  "}
        response = self.make_request(to=user.id, data=data, status_code=200)
        self.assertPayloadEqual(response, {})

        user.refresh_from_db()
        self.assertTrue(user.check_password("  StrongPassword  "))

    def test_password_validation__similarity(self):
        user = UserFactory(
            username="76aa224e-056a",
            first_name="4816-ac3e",
            last_name="ffe6e2c0748c",
            email="df8e4b1a4f39@provider.com",
        )

        data = {"password": user.username}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "password", ["password_too_similar"])

        data = {"password": user.first_name}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "password", ["password_too_similar"])

        data = {"password": user.last_name}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "password", ["password_too_similar"])

        data = {"password": user.email.split("@")[0]}
        response = self.make_request(to=user.id, data=data, status_code=400)
        self.assertValidationError(response, "password", ["password_too_similar"])

    def test_set_password_user(self):
        user = UserFactory()

        data = {"password": "StrongPassword"}
        response = self.make_request(to=user.id, data=data, status_code=200)
        self.assertPayloadEqual(response, {})

        user.refresh_from_db()
        self.assertTrue(user.check_password("StrongPassword"))


class DeleteUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-detail"
    method = "delete"

    def test_delete(self):
        user = UserFactory()
        self.make_request(to=user.id, data={}, status_code=405)


class PostDeleteUserTestCase(CremeAPITestCase):
    url_name = "creme_api__users-delete"
    method = "post"

    def test_validation__required(self):
        user = UserFactory()
        response = self.make_request(to=user.id, data={}, status_code=400)
        self.assertValidationErrors(response, {"transfer_to": ["required"]})

    def test_delete_user(self):
        team = TeamFactory()
        user1 = UserFactory(username="user1")
        user2 = UserFactory(username="user2")
        contact = ContactFactory(user=user2)

        data = {"transfer_to": user1.id}
        self.make_request(to=user2.id, data=data, status_code=204)

        self.assertFalse(CremeUser.objects.filter(username="user2").exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, user1)

        data = {"transfer_to": team.id}
        self.make_request(to=user1.id, data=data, status_code=204)

        self.assertFalse(CremeUser.objects.filter(username="user1").exists())
        contact.refresh_from_db()
        self.assertEqual(contact.user, team)
