import yaml
from django.urls import reverse_lazy

import creme.creme_api
from creme.creme_api.views import (
    documentation_description,
    documentation_title,
)
from creme.creme_core.tests.base import CremeTestCase


class SchemaViewTestCase(CremeTestCase):
    url = reverse_lazy('creme_api__openapi_schema')

    def test_permissions__permission_denied(self):
        self.login(is_superuser=False, allowed_apps=('creme_core',))
        self.assertGET403(self.url)

    def test_permissions__allowed_app(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'creme_api'))
        self.assertGET200(self.url)

    def test_permissions__superuser(self):
        self.login(is_superuser=True, allowed_apps=('creme_core',))
        self.assertGET200(self.url)

    def test_context(self):
        self.login()
        response = self.assertGET200(self.url)
        self.assertEqual(response['content-type'], 'application/vnd.oai.openapi')
        openapi_schema = yaml.safe_load(response.content)
        self.assertEqual(
            openapi_schema['info'],
            {'title': documentation_title,
             'version': creme.creme_api.VERSION,
             'description': documentation_description})


class DocumentationViewTestCase(CremeTestCase):
    url = reverse_lazy('creme_api__documentation')

    def test_permissions__permission_denied(self):
        self.login(is_superuser=False, allowed_apps=('creme_core',))
        self.assertGET403(self.url)

    def test_permissions__allowed_app(self):
        self.login(is_superuser=False, allowed_apps=('creme_core', 'creme_api'))
        self.assertGET200(self.url)

    def test_permissions__superuser(self):
        self.login(is_superuser=True, allowed_apps=('creme_core',))
        self.assertGET200(self.url)

    def test_context(self):
        self.login()
        response = self.assertGET200(self.url)
        self.assertTemplateUsed(response, 'creme_api/documentation.html')
        self.assertEqual(response.context["schema_url"], 'creme_api__openapi_schema')
        self.assertEqual(
            response.context["creme_api__tokens_url"], 'http://testserver/creme_api/tokens')
        self.assertEqual(response.context["token_type"], 'Token')
