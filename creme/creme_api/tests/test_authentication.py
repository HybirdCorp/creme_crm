from django.urls import path, reverse_lazy
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated
from rest_framework.response import Response
from rest_framework.test import APITestCase, URLPatternsTestCase
from rest_framework.views import APIView

from creme.creme_api.api.authentication import TokenAuthentication
from creme.creme_api.models import Application, Token


class TestAuthenticationView(APIView):
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        return Response(data={'ok': True})


class TokenAuthenticationAPITestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path("test-authentication/",
             TestAuthenticationView.as_view(),
             name="api_tests__test-authentication")
    ]
    url = reverse_lazy("api_tests__test-authentication")

    def request(self):
        return self.client.get(self.url)

    def assert401(self, error_code=None):
        response = self.request()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        error_detail = response.data['detail']
        if error_code:
            code = error_code
            message = TokenAuthentication.errors[error_code]
        else:
            code = NotAuthenticated.default_code
            message = NotAuthenticated.default_detail

        self.assertEqual(error_detail.code, code)
        self.assertEqual(error_detail, message, error_detail)

    def test_authenticate01(self):
        self.assert401()

    def test_authenticate02(self):
        self.client.credentials(HTTP_AUTHORIZATION='')
        self.assert401()

    def test_authenticate03(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer')
        self.assert401()

    def test_authenticate04(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token')
        self.assert401(error_code='empty')

    def test_authenticate05(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token T1 T2')
        self.assert401(error_code='too_long')

    def test_authenticate06(self):
        self.client.credentials(HTTP_AUTHORIZATION=b'Token \xa1')
        self.assert401(error_code='encoding')

    def test_authenticate07(self):
        application = Application.objects.create(name="APITestCase")
        Token.objects.create(application=application)
        self.client.credentials(HTTP_AUTHORIZATION=b'Token TEST')
        self.assert401(error_code='invalid')

    def test_authenticate08(self):
        application = Application.objects.create(name="APITestCase", enabled=False)
        token = Token.objects.create(application=application)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.code}')
        self.assert401(error_code='invalid')

    def test_authenticate09(self):
        application = Application.objects.create(name="APITestCase")
        token = Token.objects.create(application=application, expires=timezone.now())
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.code}')
        self.assert401(error_code='expired')

    def test_authenticate10(self):
        application = Application.objects.create(name="APITestCase")
        token = Token.objects.create(application=application)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.code}')
        response = self.request()
        self.assertEqual(status.HTTP_200_OK, response.status_code)
        self.assertEqual({'ok': True}, response.data)
