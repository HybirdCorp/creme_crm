from django.urls import reverse
from rest_framework.fields import DateTimeField
from rest_framework.test import APITestCase

from creme.creme_api.api.authentication import TokenAuthentication
from creme.creme_api.models import Application, Token


class Factory:
    @classmethod
    def register(cls, func):
        if hasattr(cls, func.__name__):
            raise AttributeError(func.__name__)
        setattr(cls, func.__name__, classmethod(func))


def to_iso8601(value):
    return DateTimeField().to_representation(value)


class CremeAPITestCase(APITestCase):
    auto_login = True
    url_name = None
    method = None
    maxDiff = None
    to_iso8601 = staticmethod(to_iso8601)

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

    def make_request(self, *, to=None, data=None):
        assert self.url_name is not None
        assert self.method is not None
        args = [to] if to is not None else None
        url = reverse(self.url_name, args=args)
        method = getattr(self.client, self.method)
        return method(url, data=data, format='json')

    def consume_list(self, data=None):
        assert self.url_name is not None and self.url_name.endswith("-list")
        assert self.method == 'get'
        method = getattr(self.client, self.method)

        responses = []
        results = []
        url = reverse(self.url_name)
        while url:
            response = method(url, data=data, format='json')
            responses.append(response)
            results.extend(response.data['results'])
            url = response.data['next']
        return responses, results
