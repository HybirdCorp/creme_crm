import difflib
import pprint
from collections import OrderedDict

from django.urls import reverse
from rest_framework.fields import DateTimeField
from rest_framework.response import Response
from rest_framework.test import APITestCase

from creme.creme_api.api.authentication import TokenAuthentication
from creme.creme_api.models import Application, Token


def to_iso8601(value):
    return DateTimeField().to_representation(value)


class PrettyPrinter(pprint.PrettyPrinter):
    _dispatch = pprint.PrettyPrinter._dispatch
    _dispatch[OrderedDict.__repr__] = pprint.PrettyPrinter._pprint_dict


def pformat(obj):
    return PrettyPrinter(
        indent=2, width=80, depth=None, compact=False, sort_dicts=True
    ).pformat(obj)


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

    def _assertPayloadEqual(self, first, second):
        if first != second:
            first = self._prepare_payload(first)
            second = self._prepare_payload(second)
            diff = "\n".join(
                difflib.unified_diff(
                    pformat(first).splitlines(), pformat(second).splitlines()
                )
            )
            self.fail(f"Payload error:\n{diff}")

    def _prepare_payload(self, data):
        if isinstance(data, list):
            return [self._prepare_payload(obj) for obj in data]
        if isinstance(data, dict):
            return {key: self._prepare_payload(data[key]) for key in sorted(data)}
        return data

    def assertPayloadEqual(self, response, expected):
        self.assertIsInstance(response, Response, "First argument is not a Response")
        data = response.data
        if isinstance(expected, dict):
            self._assertPayloadEqual(expected, data)
        elif isinstance(expected, list):
            self.assertEqual(len(expected), len(data["results"]))
            self._assertPayloadEqual(expected, data["results"])
        else:
            self.assertEqual(response, expected)

    def make_request(self, *, to=None, data=None, status_code=None):
        assert self.url_name is not None
        assert self.method is not None
        args = [to] if to is not None else None
        url = reverse(self.url_name, args=args)
        method = getattr(self.client, self.method)
        response = method(url, data=data, format="json")
        self.assertEqual(response.status_code, status_code, response.data)
        return response

    def consume_list(self, data=None):
        assert self.url_name is not None and self.url_name.endswith("-list")
        assert self.method == "get"
        method = getattr(self.client, self.method)

        responses = []
        results = []
        url = reverse(self.url_name)
        while url:
            response = method(url, data=data, format="json")
            responses.append(response)
            results.extend(response.data["results"])
            url = response.data["next"]
        return responses, results
