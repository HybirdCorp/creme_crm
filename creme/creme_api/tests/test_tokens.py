from uuid import uuid4

from creme.creme_api.models import Token
from creme.creme_api.tests.utils import CremeAPITestCase


class TokensTestCase(CremeAPITestCase):
    auto_login = False
    url_name = 'creme_api__tokens-list'
    method = 'post'

    def test_create_token__missing(self):
        response = self.make_request(data={})
        self.assertValidationErrors(response, {
            'client_id': ['required'],
            'client_secret': ['required'],
        })

    def test_create_token__empty(self):
        data = {
            "client_id": "",  # trim
            "client_secret": "",
        }
        response = self.make_request(data=data)
        self.assertValidationErrors(response, {
            'client_id': ['invalid'],  # Must be a valid UUID.
            'client_secret': ['blank'],
        })

    def test_create_token__no_application(self):
        data = {
            "client_id": uuid4().hex,
            "client_secret": "Secret",
        }
        response = self.make_request(data=data)
        self.assertValidationErrors(response, {
            '': ['authentication_failure'],
        })

    def test_create_token(self):
        data = {
            "client_id": self.application.client_id,
            "client_secret": self.application._client_secret,
        }
        response = self.make_request(data=data)
        token = Token.objects.get(application=self.application)
        self.assertResponseEqual(response, 200, {"token": token.code})
