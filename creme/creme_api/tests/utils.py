from rest_framework.test import APITestCase

from creme.creme_api.models import ApiKey


class CremeAPITestCase(APITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_key = ApiKey.objects.create(name="APITestCase")

    def setUp(self) -> None:
        super().setUp()
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.api_key.key)
