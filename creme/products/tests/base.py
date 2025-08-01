from unittest import skipIf

from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.tests.views.base import MassImportBaseTestCaseMixin
from creme.documents import get_document_model
from creme.documents.tests.base import DocumentsTestCaseMixin

from .. import product_model_is_custom, service_model_is_custom

skip_product_tests = product_model_is_custom()
skip_service_tests = service_model_is_custom()


def skipIfCustomProduct(test_func):
    return skipIf(skip_product_tests, 'Custom Product model in use')(test_func)


def skipIfCustomService(test_func):
    return skipIf(skip_service_tests, 'Custom Service model in use')(test_func)


class _ProductsTestCase(MassImportBaseTestCaseMixin,
                        DocumentsTestCaseMixin,
                        CremeTestCase):
    EXTRA_CATEGORY_KEY = 'cform_extra-products_subcategory'

    def login_as_basic_user(self, creatable_model):
        user = self.login_as_standard(
            allowed_apps=['products', 'documents'],
            creatable_models=[creatable_model, get_document_model()],
        )
        self.add_credentials(user.role, all='!LINK', own='*')

        return user
