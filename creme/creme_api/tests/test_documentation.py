import yaml
from django.urls import reverse_lazy
from parameterized import parameterized

from creme import creme_api
from creme.creme_api.api.routes import router
from creme.creme_core.tests.base import CremeTestCase


class SchemaViewTestCase(CremeTestCase):
    url = reverse_lazy("creme_api__openapi_schema")

    def test_permissions__permission_denied(self):
        self.login(is_superuser=False, allowed_apps=("creme_core",))
        self.assertGET403(self.url)

    def test_permissions__allowed_app(self):
        self.login(is_superuser=False, allowed_apps=("creme_core", "creme_api"))
        self.assertGET200(self.url)

    def test_permissions__superuser(self):
        self.login(is_superuser=True, allowed_apps=("creme_core",))
        self.assertGET200(self.url)

    def test_context(self):
        self.login()
        response = self.assertGET200(self.url)
        self.assertEqual(response["content-type"], "application/vnd.oai.openapi")
        self.assertTemplateUsed(response, "creme_api/description.md")

        openapi_schema = yaml.safe_load(response.content)
        info = openapi_schema["info"]
        self.assertEqual(info["version"], creme_api.VERSION)
        self.assertTrue(info["title"])
        self.assertTrue(info["description"])

    @parameterized.expand([(endpoint,) for endpoint in router.resources_list])
    def test_all_endpoints_have_documentation(self, endpoint):
        self.login()
        response = self.assertGET200(self.url)
        openapi_schema = yaml.safe_load(response.content)

        errors = []
        for url, methods in openapi_schema["paths"].items():
            if endpoint not in url:
                continue
            errors.extend(
                [
                    (method, url)
                    for method, method_details in methods.items()
                    if not method_details.get("description")
                ]
            )

        self.assertFalse(errors, "Please document those endpoints.")


class DocumentationViewTestCase(CremeTestCase):
    url = reverse_lazy("creme_api__documentation")

    def test_permissions__permission_denied(self):
        self.login(is_superuser=False, allowed_apps=("creme_core",))
        self.assertGET403(self.url)

    def test_permissions__allowed_app(self):
        self.login(is_superuser=False, allowed_apps=("creme_core", "creme_api"))
        self.assertGET200(self.url)

    def test_permissions__superuser(self):
        self.login(is_superuser=True, allowed_apps=("creme_core",))
        self.assertGET200(self.url)

    def test_context(self):
        self.login()
        response = self.assertGET200(self.url)
        self.assertTemplateUsed(response, "creme_api/documentation.html")
        self.assertEqual(response.context["schema_url"], "creme_api__openapi_schema")
        self.assertEqual(
            response.context["creme_api__tokens_url"],
            "http://testserver/creme_api/tokens/",
        )
        self.assertEqual(response.context["token_type"], "Token")
