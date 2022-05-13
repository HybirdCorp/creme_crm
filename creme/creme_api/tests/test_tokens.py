from uuid import uuid4

from creme.creme_api.models import Token
from creme.creme_api.tests.utils import CremeAPITestCase


class TokensTestCase(CremeAPITestCase):
    auto_login = False
    url_name = "creme_api__tokens-list"
    method = "post"

    def test_create_token__missing(self):
        response = self.make_request(data={}, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "application_id": ["required"],
                "application_secret": ["required"],
            },
        )

    def test_create_token__empty(self):
        data = {
            "application_id": "",  # trim
            "application_secret": "",
        }
        response = self.make_request(data=data, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "application_id": ["invalid"],  # Must be a valid UUID.
                "application_secret": ["blank"],
            },
        )

    def test_create_token__no_application(self):
        data = {
            "application_id": uuid4().hex,
            "application_secret": "Secret",
        }
        response = self.make_request(data=data, status_code=400)
        self.assertValidationErrors(
            response,
            {
                "": ["authentication_failure"],
            },
        )

    def test_create_token(self):
        data = {
            "application_id": self.application.application_id,
            "application_secret": self.application._application_secret,
        }
        response = self.make_request(data=data, status_code=200)
        token = Token.objects.get(application=self.application)
        self.assertPayloadEqual(response, {"token": token.code})
