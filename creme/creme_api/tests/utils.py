from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework.fields import DateTimeField
from rest_framework.test import APITestCase

from creme.creme_api.api.authentication import TokenAuthentication
from creme.creme_api.models import Application, Token
from creme.creme_core.models import SetCredentials, UserRole
from creme.persons import get_contact_model, get_organisation_model

Contact = get_contact_model()
CremeUser = get_user_model()
Organisation = get_organisation_model()


class Factory:
    def user(self, **kwargs):
        data = {
            'username': 'john.doe',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@provider.com',
            'is_active': True,
            'is_superuser': True,
            'role': None,
        }
        data.update(**kwargs)
        return CremeUser.objects.create(**data)

    def user_data(self, **kwargs):
        data = {
            'username': "john.doe",
            'first_name': "John",
            'last_name': "Doe",
            'email': "john.doe@provider.com",
            'is_active': True,
            "is_superuser": True,
            'role': None,
        }
        data.update(**kwargs)
        return data

    def team(self, **kwargs):
        data = {
            'username': 'Team #1',
        }
        data.update(**kwargs)
        if 'name' in data:
            data['username'] = data.pop('name')
        data['is_team'] = True
        teammates = data.pop('teammates', [])

        team = CremeUser.objects.create(**data)
        team.teammates = teammates

        return team

    def contact(self, **kwargs):
        return Contact.objects.create(**kwargs)

    def role(self, **kwargs):
        contact_ct = ContentType.objects.get_for_model(Contact)
        orga_ct = ContentType.objects.get_for_model(Organisation)
        data = {
            'name': "Basic",
            'allowed_apps': ['creme_core', 'creme_api', 'persons'],
            'admin_4_apps': ['creme_core', 'creme_api'],
            'creatable_ctypes': [contact_ct.id, orga_ct.id],
            'exportable_ctypes': [contact_ct.id],
        }
        data.update(**kwargs)
        role = UserRole(name=data['name'])
        role.allowed_apps = data['allowed_apps']
        role.admin_4_apps = data['admin_4_apps']
        role.save()
        role.creatable_ctypes.set(data['creatable_ctypes'])
        role.exportable_ctypes.set(data['exportable_ctypes'])
        return role

    def credential(self, **kwargs):
        contact_ct = ContentType.objects.get_for_model(Contact)
        perms = {'can_view', 'can_change', 'can_delete', 'can_link', 'can_unlink'}
        data = {
            'set_type': SetCredentials.ESET_OWN,
            'ctype': contact_ct,
            'forbidden': False,
            'efilter': None,
            **{p: True for p in perms}
        }
        data.update(**kwargs)
        if 'role' not in data:
            data['role'] = self.role()
        value = {k: data.pop(k) for k in perms}
        creds = SetCredentials(**data)
        creds.set_value(**value)
        creds.save()
        return creds


class CremeAPITestCase(APITestCase):
    auto_login = True
    url_name = None
    method = None
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.application = Application.objects.create(name="APITestCase")
        cls.factory = Factory()

    def login(self, application):
        self.token = Token.objects.create(application=application)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"{TokenAuthentication.keyword} {self.token.code}"
        )

    def setUp(self) -> None:
        super().setUp()
        if self.auto_login:
            self.login(self.application)

    def assertValidationError(self, response, field_name, error_codes):
        self.assertEqual(response.status_code, 400)
        self.assertIn(field_name, response.data, response.data)
        codes = [error.code for error in response.data[field_name]]
        self.assertEqual(error_codes, codes, response.data)

    def assertValidationErrors(self, response, errors):
        self.assertEqual(response.status_code, 400)
        current_errors = {
            field_name: [error.code for error in errors]
            for (field_name, errors) in response.data.items()
        }
        self.assertEqual(current_errors, errors, response.data)

    def assertResponseEqual(self, response, status_code, data=None):
        self.assertEqual(response.status_code, status_code, response.data)
        if data is None:
            return
        if isinstance(data, dict):
            self.assertDictEqual(dict(response.data), data)
        elif isinstance(data, list):
            self.assertEqual(len(response.data['results']), len(data))
            for i, (obj1, obj2) in enumerate(zip(response.data['results'], data)):
                self.assertDictEqual(
                    dict(obj1), obj2, msg=f"Elements response.data['results'][{i}] differ.")
        else:
            self.assertEqual(response.data, data)

    @staticmethod
    def to_iso8601(value):
        return DateTimeField().to_representation(value)

    def make_request(self, *, to=None, data=None):
        assert self.url_name is not None
        assert self.method is not None
        args = [to] if to is not None else None
        url = reverse(self.url_name, args=args)
        method = getattr(self.client, self.method)
        return method(url, data=data, format='json')
