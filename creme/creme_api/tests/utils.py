from rest_framework.test import APITestCase

from creme.creme_api.models import ApiKey
from creme.creme_core.tests.base import CremeTestCase


class CremeAPITestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key = ApiKey.objects.create(name="APITestCase")

    def setUp(self) -> None:
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key.key)


class SerializerTestCase(CremeTestCase):
    def assertSerializerValid(self, serializer):
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def assertSerializerError(self, serializer, field_name, *error_codes):
        self.assertFalse(serializer.is_valid())
        self.assertTrue(field_name in serializer.errors, serializer.errors.keys())
        codes = {error.code for error in serializer.errors[field_name]}
        self.assertEqual(set(error_codes), codes)
